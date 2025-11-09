import os
import argparse
from typing import Callable

import gymnasium as gym
from stable_baselines3 import PPO
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv, VecNormalize
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback
from stable_baselines3.common.utils import set_random_seed


# ====== CONFIG ======

# Point this to YOUR custom humanoid.xml
DEFAULT_CUSTOM_XML_PATH = os.path.join(
    os.path.dirname(__file__),
    "mujoco",
    "mjspecs",
    "humanoid.xml",
)

LOG_DIR = "./logs_custom_humanoid"
CHECKPOINT_DIR = os.path.join(LOG_DIR, "checkpoints")
EVAL_LOG_DIR = os.path.join(LOG_DIR, "eval")


# ====== ENV FACTORY ======

def make_humanoid_env(
    rank: int,
    seed: int,
    xml_path: str,
    render_mode: str | None = None,
) -> Callable[[], gym.Env]:
    """
    Factory for a single Humanoid-v5 env using a custom MuJoCo XML.

    Uses built-in Humanoid-v5 reward/termination logic; only swaps the model.
    """

    def _init() -> gym.Env:
        # Validate XML early with a clear error
        if not os.path.isfile(xml_path):
            raise FileNotFoundError(
                f"[HumanoidEnv rank={rank}] MuJoCo XML not found at: {xml_path}"
            )

        # Gymnasium Humanoid-v5 accepts xml_file=... (same pattern as Hopper/Ant v5)
        env = gym.make(
            "Humanoid-v5",
            xml_file=xml_path,
            # You can optionally override defaults here if you want:
            # forward_reward_weight=1.0,
            # ctrl_cost_weight=0.1,
            # healthy_reward=5.0,
            # terminate_when_unhealthy=True,
            # reset_noise_scale=1e-2,
            # exclude_current_positions_from_observation=True,
            render_mode=render_mode,
        )

        # Wrap with Monitor for episode stats
        env = Monitor(env)

        # Seed this individual env
        env.reset(seed=seed + rank)
        return env

    return _init


# ====== TRAINING SETUP ======

def build_vec_env(
    num_envs: int,
    seed: int,
    xml_path: str,
    render: bool = False,
    use_subproc: bool = True,
):
    """
    Create a vectorized environment with VecNormalize.
    """

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

    # Normalize observations and rewards (standard for Mujoco tasks)
    vec_env = VecNormalize(
        vec_env,
        norm_obs=True,
        norm_reward=True,
        clip_obs=10.0,
        clip_reward=10.0,
    )

    return vec_env


def build_callbacks(eval_env, checkpoint_dir: str, eval_log_dir: str):
    os.makedirs(checkpoint_dir, exist_ok=True)
    os.makedirs(eval_log_dir, exist_ok=True)

    checkpoint_callback = CheckpointCallback(
        save_freq=200_000 // eval_env.num_envs,  # adjust vs n_steps
        save_path=checkpoint_dir,
        name_prefix="ppo_custom_humanoid",
        save_replay_buffer=False,
        save_vecnormalize=True,
    )

    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=eval_log_dir,
        log_path=eval_log_dir,
        eval_freq=100_000 // eval_env.num_envs,
        n_eval_episodes=5,
        deterministic=True,
        render=False,
    )

    return [checkpoint_callback, eval_callback]


# ====== MAIN TRAIN FUNCTION ======

def train(
    xml_path: str = DEFAULT_CUSTOM_XML_PATH,
    total_timesteps: int = 5_000_000,
    num_envs: int = 8,
    seed: int = 42,
    learning_rate: float = 3e-4,
    batch_size: int = 64,
    n_steps: int = 2048,
):

    # --- Training envs ---
    train_env = build_vec_env(
        num_envs=num_envs,
        seed=seed,
        xml_path=xml_path,
        render=False,
        use_subproc=True,
    )

    # --- Separate eval env (no subproc; fewer envs) ---
    eval_env = build_vec_env(
        num_envs=1,
        seed=seed + 10_000,
        xml_path=xml_path,
        render=False,
        use_subproc=False,
    )

    callbacks = build_callbacks(eval_env, CHECKPOINT_DIR, EVAL_LOG_DIR)

    # --- PPO model ---
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
        tensorboard_log=LOG_DIR,
        verbose=1,
    )

    # --- Train ---
    model.learn(
        total_timesteps=total_timesteps,
        callback=callbacks,
        progress_bar=True,
    )

    # Save final model + VecNormalize stats
    model.save(os.path.join(LOG_DIR, "ppo_custom_humanoid_final"))
    train_env.save(os.path.join(LOG_DIR, "vecnormalize_final.pkl"))

    # Clean up
    train_env.close()
    eval_env.close()


# ====== RENDER / TEST POLICY ======

def enjoy(
    xml_path: str = DEFAULT_CUSTOM_XML_PATH,
    model_path: str = os.path.join(LOG_DIR, "ppo_custom_humanoid_final.zip"),
    vecnorm_path: str = os.path.join(LOG_DIR, "vecnormalize_final.pkl"),
    seed: int = 123,
    episodes: int = 5,
):
    """
    Load a trained policy and roll it out with rendering.
    """

    if not os.path.isfile(model_path):
        raise FileNotFoundError(f"Model not found at {model_path}")

    # Single env with render
    env = build_vec_env(
        num_envs=1,
        seed=seed,
        xml_path=xml_path,
        render=True,
        use_subproc=False,
    )

    # Load VecNormalize stats
    if os.path.isfile(vecnorm_path):
        env.load(vecnorm_path)

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


# ====== CLI ======

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--xml",
        type=str,
        default=DEFAULT_CUSTOM_XML_PATH,
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

    if args.enjoy:
        enjoy(xml_path=args.xml)
    else:
        train(
            xml_path=args.xml,
            total_timesteps=args.timesteps,
            num_envs=args.num_envs,
            seed=args.seed,
        )