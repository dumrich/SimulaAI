import os
import argparse
from typing import Callable, Optional
import asyncio
import gymnasium as gym
from stable_baselines3 import PPO
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv, VecNormalize
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback, BaseCallback
from stable_baselines3.common.utils import set_random_seed
import time

# ====== CONFIG ======
LOG_DIR_BASE = os.path.join(os.path.dirname(__file__), "..", "logs_custom_humanoid")


# ====== NEW: CUSTOM CALLBACK ======
class QueueCallback(BaseCallback):
    """
    A custom callback that puts episode data into an asyncio.Queue
    and checks for pause/reset signals.
    """
    def __init__(self, 
                 data_queue: asyncio.Queue,
                 run_event: asyncio.Event,
                 reset_event: asyncio.Event,
                 verbose=0):
        super().__init__(verbose)
        self.data_queue = data_queue
        self.run_event = run_event
        self.reset_event = reset_event
        self.episode_count = 0
    
    def _on_rollout_end(self) -> None:
        """
        Called at the end of each rollout.
        """
        new_episodes = [ep for ep in self.model.ep_info_buffer]
        if not new_episodes:
            return

        for ep_info in new_episodes:
            self.episode_count += 1
            reward = ep_info["r"]
            length = ep_info["l"]
            
            data = {
                "episode": self.episode_count,
                "reward": round(reward, 2),
                "length": int(length)
            }
            try:
                self.data_queue.put_nowait(data)
            except Exception as e:
                print(f"QueueCallback Error: {e}")

    def _on_step(self) -> bool:
        """
        Called on every step. Used to check for pause/reset.
        """
        # Check for pause
        if not self.run_event.is_set():
            print("[train.py] Pausing training...")
            while not self.run_event.is_set():
                time.sleep(1) # Wait 1s and check again
            print("[train.py] Resuming training...")
        
        # Check for reset
        if self.reset_event.is_set():
            print("[train.py] Resetting training...")
            # We will stop the learning. The WebSocket server will restart us.
            # This is simpler than resetting the model mid-run.
            self.data_queue.put_nowait({"status": "reset"})
            self.reset_event.clear() # Clear the flag
            return False # Returning False stops the .learn() loop
            
        return True


# ====== ENV FACTORY (Unchanged) ======
def make_humanoid_env(
    rank: int,
    seed: int,
    xml_path: str,
    render_mode: str | None = None,
) -> Callable[[], gym.Env]:
    """
    Factory for a single Humanoid-v5 env using a custom MuJoCo XML.
    """
    def _init() -> gym.Env:
        if not os.path.isfile(xml_path):
            raise FileNotFoundError(
                f"[HumanoidEnv rank={rank}] MuJoCo XML not found at: {xml_path}"
            )
        
        if os.path.getsize(xml_path) == 0:
            raise ValueError(f"XML file is empty: {xml_path}")

        try:
            env = gym.make(
                "Humanoid-v5",
                xml_file=xml_path,
                render_mode=render_mode,
            )
        except Exception as e:
            raise ValueError(f"Error creating gym env with XML {xml_path}: {e}")

        env = Monitor(env)
        env.reset(seed=seed + rank)
        return env

    return _init


# ====== TRAINING SETUP (Modified) ======
def build_vec_env(
    num_envs: int,
    seed: int,
    xml_path: str,
    render: bool = False,
    use_subproc: bool = True,
):
    set_random_seed(seed)
    render_mode = "human" if render and num_envs == 1 else None
    env_fns = [
        make_humanoid_env(rank=i, seed=seed, xml_path=xml_path, render_mode=render_mode)
        for i in range(num_envs)
    ]

    if num_envs > 1 and use_subproc:
        vec_env = SubprocVecEnv(env_fns)
    else:
        vec_env = DummyVecEnv(env_fns)

    run_log_dir = os.path.join(LOG_DIR_BASE, f"run_{int(time.time())}")
    os.makedirs(run_log_dir, exist_ok=True)
    
    vec_env = VecNormalize(
        vec_env,
        norm_obs=True,
        norm_reward=True,
        clip_obs=10.0,
        clip_reward=10.0,
    )
    return vec_env, run_log_dir


def build_callbacks(
    eval_env,
    log_dir: str,
    data_queue: Optional[asyncio.Queue] = None,
    run_event: Optional[asyncio.Event] = None,
    reset_event: Optional[asyncio.Event] = None,
):
    checkpoint_dir = os.path.join(log_dir, "checkpoints")
    eval_log_dir = os.path.join(log_dir, "eval")
    
    os.makedirs(checkpoint_dir, exist_ok=True)
    os.makedirs(eval_log_dir, exist_ok=True)

    callbacks = []
    
    callbacks.append(CheckpointCallback(
        save_freq=200_000 // eval_env.num_envs,
        save_path=checkpoint_dir,
        name_prefix="ppo_custom_humanoid",
        save_vecnormalize=True,
    ))

    callbacks.append(EvalCallback(
        eval_env,
        best_model_save_path=eval_log_dir,
        log_path=eval_log_dir,
        eval_freq=100_000 // eval_env.num_envs,
        n_eval_episodes=5,
        deterministic=True,
        render=False,
    ))
    
    if data_queue and run_event and reset_event:
        callbacks.append(QueueCallback(
            data_queue=data_queue,
            run_event=run_event,
            reset_event=reset_event
        ))

    return callbacks


# ====== MAIN TRAIN FUNCTION (Modified) ======
def train(
    xml_path: str,
    data_queue: Optional[asyncio.Queue] = None,
    run_event: Optional[asyncio.Event] = None,
    reset_event: Optional[asyncio.Event] = None,
    total_timesteps: int = 5_000_000,
    num_envs: int = 8,
    seed: int = 42,
    learning_rate: float = 3e-4,
    batch_size: int = 64,
    n_steps: int = 2048,
):
    print(f"\n[train.py] Starting training on: {xml_path}")
    print(f"[train.py] Total timesteps: {total_timesteps}")

    train_env, run_log_dir = build_vec_env(
        num_envs=num_envs,
        seed=seed,
        xml_path=xml_path,
        render=False,
        use_subproc=True,
    )

    eval_env, _ = build_vec_env(
        num_envs=1,
        seed=seed + 10_000,
        xml_path=xml_path,
        render=False,
        use_subproc=False,
    )

    callbacks = build_callbacks(
        eval_env, 
        run_log_dir, 
        data_queue, 
        run_event, 
        reset_event
    ) 

    model = PPO(
        policy="MlpPolicy",
        env=train_env,
        learning_rate=learning_rate,
        n_steps=n_steps,
        batch_size=batch_size,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.0,
        vf_coef=0.5,
        max_grad_norm=0.5,
        tensorboard_log=run_log_dir,
        verbose=1,
    )

    print("[train.py] PPO model built. Starting learning...")
    
    try:
        model.learn(
            total_timesteps=total_timesteps,
            callback=callbacks,
            progress_bar=True,
        )
        print("[train.py] Training complete.")
        
        if data_queue:
            data_queue.put_nowait({"status": "complete"})

    except Exception as e:
        print(f"[train.py] Error during training: {e}")
        if data_queue:
            data_queue.put_nowait({"error": str(e)})
    finally:
        model.save(os.path.join(run_log_dir, "ppo_custom_humanoid_final"))
        train_env.save(os.path.join(run_log_dir, "vecnormalize_final.pkl"))
        print(f"[train.py] Final model saved to {run_log_dir}")
        
        train_env.close()
        eval_env.close()
        print("[train.py] Environments closed.")


# (The 'enjoy' and 'CLI' functions are unchanged)
def enjoy(
    xml_path: str = DEFAULT_CUSTOM_XML_PATH,
    model_path: str = os.path.join(LOG_DIR_BASE, "ppo_custom_humanoid_final.zip"),
    vecnorm_path: str = os.path.join(LOG_DIR_BASE, "vecnormalize_final.pkl"),
    seed: int = 123,
    episodes: int = 5,
):
    if not os.path.isfile(model_path):
        raise FileNotFoundError(f"Model not found at {model_path}")
    if not os.path.isfile(vecnorm_path):
        raise FileNotFoundError(f"VecNormalize stats not found at {vecnorm_path}")

    env, _ = build_vec_env(
        num_envs=1,
        seed=seed,
        xml_path=xml_path,
        render=True,
        use_subproc=False,
    )

    env = VecNormalize.load(vecnorm_path, env)
    # We unwrap the VecNormalize wrapper to get to the underlying Monitor
    # and set its render_mode
    env.unwrapped.envs[0].render_mode = "human"
    env.training = False # Don't update running stats
    env.norm_reward = False # Don't normalize reward

    model = PPO.load(model_path, env=env)

    for ep in range(episodes):
        obs, info = env.reset()
        done = False
        truncated = False
        ep_reward = 0.0

        while not (done or truncated):
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, done, truncated, info = env.step(action)
            ep_reward += float(reward)

        print(f"[ENJOY] Episode {ep+1}: reward={ep_reward:.2f}")

    env.close()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--xml",
        type=str,
        default=None, # Default to None, will be set by train()
        help="Path to custom humanoid.xml",
    )
    parser.add_argument(
        "--timesteps",
        type=int,
        default=5_000_000,
        help="Total training timesteps",
    )
    parser.add_argument(
        "--num-envs",
        type=int,
        default=8,
        help="Number of parallel environments",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
    )
    parser.add_argument(
        "--enjoy",
        action="store_true",
        help="Run a render rollout with the trained model instead of training",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    xml_to_run = args.xml or DEFAULT_CUSTOM_XML_PATH

    if args.enjoy:
        enjoy(xml_path=xml_to_run)
    else:
        train(
            xml_path=xml_to_run,
            data_queue=None,
            run_event=asyncio.Event(), # Create dummy event
            reset_event=asyncio.Event(), # Create dummy event
            total_timesteps=args.timesteps,
            num_envs=args.num_envs,
            seed=args.seed,
        )