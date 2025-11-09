import numpy as np
import os
import gymnasium as gym
from gymnasium.envs.mujoco import MujocoEnv
from gymnasium.utils import EzPickle

# Get the absolute path to the XML file (assuming it's in the same directory)

class HumanoidEnv(MujocoEnv, EzPickle):
    """
    This is the "glue code" that defines the rules of the game for your XML.
    """
    metadata = {
        "render_modes": [
            "human",
            "rgb_array",
            "depth_array",
        ],
        "render_fps": 67,
    }

    def __init__(self, path, **kwargs):
        # 1. DEFINE THE OBSERVATION SPACE
        # This must match the observation array returned by _get_obs()
        # We're using the official Humanoid-v5 observation space, which includes:
        # - qpos (joint positions, excluding root x/y)
        # - qvel (joint velocities)
        # - cinert (COM-based inertia)
        # - cvel (COM-based velocity)
        # - qfrc_actuator (actuator forces)
        # - cfrc_ext (external contact forces)
        # Total size: 348 elements
        observation_space = gym.spaces.Box(
            low=-np.inf, high=np.inf, shape=(348,), dtype=np.float64
        )

        # 2. CALL THE PARENT CONSTRUCTOR (MUJOCO_ENV)
        # This loads the XML, sets up the viewer, and defines the action space
        # from the <actuator> tags in the XML.
        super().__init__(
            model_path=MODEL_PATH,
            frame_skip=5, # Number of physics steps per env.step()
            observation_space=observation_space,
            **kwargs,
        )

        # 3. SET UP REWARD COMPONENTS
        self._healthy_reward = 5.0
        self._terminate_when_unhealthy = True
        self._control_cost_weight = 0.1
        
        # EzPickle is a helper for saving/loading the environment
        EzPickle.__init__(self, **kwargs)

    @property
    def is_healthy(self):
        """
        Defines when the humanoid is "alive".
        We check if the z-coordinate (height) is within a healthy range.
        """
        min_z, max_z = 1.0, 2.0
        # self.data.qpos[2] is the z-coordinate of the torso
        is_healthy = (self.data.qpos[2] >= min_z) and (self.data.qpos[2] <= max_z)
        return is_healthy

    def _get_obs(self):
        """
        This is the function that returns the observation array.
        It must match the 'observation_space' defined in __init__.
        """
        # Get all the sensor data from MuJoCo's `self.data` object
        position = self.data.qpos[2:]  # qpos without root x and y
        velocity = self.data.qvel
        com_inertia = self.data.cinert.flat
        com_velocity = self.data.cvel.flat
        actuator_forces = self.data.qfrc_actuator.flat
        external_contact_forces = self.data.cfrc_ext.flat

        # Concatenate them all into a single, flat array
        return np.concatenate(
            (
                position,
                velocity,
                com_inertia,
                com_velocity,
                actuator_forces,
                external_contact_forces,
            )
        )

    def step(self, action):
        """
        This is the main function of the environment.
        It takes an 'action', applies it to the simulation,
        and returns the next observation, reward, and done signals.
        """
        # 1. APPLY THE ACTION AND STEP THE SIMULATION
        self.do_simulation(action, self.frame_skip)

        # 2. CALCULATE THE REWARD
        
        # Reward for moving forward (x-velocity)
        # self.data.qvel[0] is the x-velocity of the torso
        forward_reward = self.data.qvel[0]
        
        # Reward for being "healthy" (alive)
        healthy_reward = self.is_healthy * self._healthy_reward
        
        # Penalty for using the motors (control cost)
        ctrl_cost = self._control_cost_weight * np.sum(np.square(self.data.ctrl))

        # Total reward
        reward = forward_reward + healthy_reward - ctrl_cost

        # 3. CHECK FOR TERMINATION
        # The episode ends if the robot is "unhealthy" (it fell)
        terminated = (not self.is_healthy) if self._terminate_when_unhealthy else False
        
        # Truncation signal (always False for this basic env)
        truncated = False

        # 4. GET THE NEW OBSERVATION
        observation = self._get_obs()

        # 5. RETURN THE STANDARD TUPLE
        # (info dict is for debugging, "x_position" is useful)
        info = {"x_position": self.data.qpos[0], "x_velocity": self.data.qvel[0]}
        
        return observation, reward, terminated, truncated, info

    def reset_model(self):
        """
        This function is called at the beginning of each new episode.
        It resets the robot's state to a random initial position.
        """
        # Reset joint positions and velocities to random values
        noise_low = -0.1
        noise_high = 0.1
        
        qpos = self.init_qpos + self.np_random.uniform(
            low=noise_low, high=noise_high, size=self.model.nq
        )
        qvel = self.init_qvel + self.np_random.uniform(
            low=noise_low, high=noise_high, size=self.model.nv
        )
        
        self.set_state(qpos, qvel)

        # Return the first observation of the new episode
        observation = self._get_obs()
        return observation

if __name__=="__main__":
    env = HumanoidEnv("")
