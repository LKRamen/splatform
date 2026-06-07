import os
import numpy as np
import gymnasium as gym
from gymnasium import spaces
import mujoco

from src.training.rewards import (
    waypoint_efficiency_reward,
    gait_stability_reward,
    clearance_reward,
    energy_reward,
    completion_reward,
)

_XML_PATH = os.path.join(os.path.dirname(__file__), '../../mujoco_menagerie/unitree_h1/h1.xml')

# Reward weights from CLAUDE.md scoring rubric
_W = {
    'waypoint': 0.30,
    'gait':     0.25,
    'clearance': 0.20,
    'energy':   0.15,
    'completion': 0.10,
}

_STANDING_HEIGHT = 1.06   # initial pelvis height from keyframe
_MAX_STEPS = 1000
_WAYPOINT_RADIUS = 0.5    # metres — distance to count waypoint as reached
_DEFAULT_GOAL = np.array([5.0, 0.0])   # (x, z) target in world XZ plane
_OBSTACLE_PENALTY_RADIUS = 0.8  # metres — within this distance, apply penalty
_NUM_OBSTACLES = 2


class _DynamicObstacle:
    """Pedestrian-like obstacle with bounded random walk in XZ plane."""

    def __init__(self, rng):
        # Random start position within 3-10m from origin, avoiding spawn point
        angle = rng.uniform(0, 2 * np.pi)
        radius = rng.uniform(3.0, 8.0)
        self.pos = np.array([radius * np.cos(angle), radius * np.sin(angle)])
        speed = rng.uniform(0.3, 0.8)
        dir_angle = rng.uniform(0, 2 * np.pi)
        self.vel = speed * np.array([np.cos(dir_angle), np.sin(dir_angle)])
        self._rng = rng

    def step(self, dt=0.02):
        # Random direction drift
        self.vel += self._rng.normal(0, 0.1, size=2)
        speed = np.linalg.norm(self.vel)
        if speed > 1.0:
            self.vel = self.vel / speed * 1.0
        elif speed < 0.2:
            self.vel = self.vel / (speed + 1e-6) * 0.2
        self.pos += self.vel * dt
        # Bounce off scene boundary (±10m)
        for i in range(2):
            if abs(self.pos[i]) > 10.0:
                self.vel[i] *= -1
                self.pos[i] = np.clip(self.pos[i], -10.0, 10.0)

    def world_pos(self):
        """Returns [x, y, z] with y=0.9 (pedestrian centre height)."""
        return [float(self.pos[0]), 0.9, float(self.pos[1])]


class H1TraversalEnv(gym.Env):
    """Unitree H1 traversal env wrapping MuJoCo Menagerie h1.xml."""

    metadata = {'render_modes': []}

    def __init__(self, waypoints=None):
        super().__init__()
        self.model = mujoco.MjModel.from_xml_path(_XML_PATH)
        self.data = mujoco.MjData(self.model)

        # 47-dim obs: joint_pos(19)+joint_vel(19)+lin_vel(3)+proj_grav(3)+goal_vec(2)+goal_dist(1)
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(47,), dtype=np.float32
        )
        # 19-dim action: joint position targets in [-1, 1] (scaled to joint range)
        self.action_space = spaces.Box(
            low=-1.0, high=1.0, shape=(19,), dtype=np.float32
        )

        self._default_waypoints = waypoints if waypoints is not None else [_DEFAULT_GOAL.copy()]
        self.waypoints = list(self._default_waypoints)
        self._waypoint_idx = 0
        self._step_count = 0
        self._prev_dist = None
        self._torso_heights = []
        self._prev_action = np.zeros(19)
        self._reached_all = False
        self._rng = np.random.default_rng()
        self._obstacles = [_DynamicObstacle(self._rng) for _ in range(_NUM_OBSTACLES)]

        # Cache joint limits for action scaling
        jnt_range = self.model.jnt_range[1:]   # skip free joint (index 0)
        self._jnt_lo = jnt_range[:, 0].copy()
        self._jnt_hi = jnt_range[:, 1].copy()

    def set_waypoints(self, waypoints):
        self.waypoints = list(waypoints)

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        mujoco.mj_resetData(self.model, self.data)
        # Stand the robot up using the home keyframe if available
        if self.model.nkey > 0:
            mujoco.mj_resetDataKeyframe(self.model, self.data, 0)
        mujoco.mj_forward(self.model, self.data)

        self.waypoints = list(self._default_waypoints)
        self._waypoint_idx = 0
        self._step_count = 0
        self._torso_heights = []
        self._prev_action = np.zeros(19)
        self._reached_all = False
        self._obstacles = [_DynamicObstacle(self._rng) for _ in range(_NUM_OBSTACLES)]
        self._prev_dist = self._goal_dist()
        return self._get_obs(), {}

    def step(self, action):
        action = np.clip(action, -1.0, 1.0)

        # Scale [-1,1] to joint position targets
        mid = (self._jnt_lo + self._jnt_hi) * 0.5
        half = (self._jnt_hi - self._jnt_lo) * 0.5
        pos_target = mid + action * half

        # Set actuator controls (position targets)
        self.data.ctrl[:] = pos_target

        mujoco.mj_step(self.model, self.data)
        self._step_count += 1

        # Step dynamic obstacles
        for obs in self._obstacles:
            obs.step()

        # Track torso height for gait stability
        pelvis_z = self.data.qpos[2]
        self._torso_heights.append(pelvis_z)

        # Check waypoint progress
        dist = self._goal_dist()
        if dist < _WAYPOINT_RADIUS:
            if self._waypoint_idx < len(self.waypoints) - 1:
                self._waypoint_idx += 1
                self._prev_dist = self._goal_dist()
            else:
                self._reached_all = True

        # Compute individual rewards
        r_waypoint  = waypoint_efficiency_reward(dist, self._prev_dist, self._step_count)
        r_gait      = gait_stability_reward(pelvis_z, _STANDING_HEIGHT, self.data.qpos[3:7])
        r_clearance = clearance_reward(self.data, self.model)
        r_energy    = energy_reward(self.data.actuator_force)
        r_complete  = completion_reward(self._reached_all)

        # Obstacle avoidance penalty — penalise proximity to dynamic pedestrians
        robot_xz = np.array([self.data.qpos[0], self.data.qpos[1]])
        r_obstacle = 0.0
        for obs in self._obstacles:
            d = float(np.linalg.norm(robot_xz - obs.pos))
            if d < _OBSTACLE_PENALTY_RADIUS:
                r_obstacle -= (1.0 - d / _OBSTACLE_PENALTY_RADIUS)

        reward = (
            _W['waypoint']    * r_waypoint  +
            _W['gait']        * r_gait      +
            _W['clearance']   * r_clearance +
            _W['energy']      * r_energy    +
            _W['completion']  * r_complete  +
            0.15              * r_obstacle
        )

        self._prev_dist = dist
        self._prev_action = action.copy()

        terminated = self._is_terminated()
        truncated  = self._step_count >= _MAX_STEPS

        info = {
            'scores': {
                'waypoint':   float(r_waypoint),
                'gait':       float(r_gait),
                'clearance':  float(r_clearance),
                'energy':     float(r_energy),
                'completion': float(r_complete),
                'total':      float(reward),
            },
            'position':  self.data.qpos[:3].tolist(),
            'heading':   self._heading(),
            'obstacles': [obs.world_pos() for obs in self._obstacles],
        }
        return self._get_obs(), float(reward), terminated, truncated, info

    # ------------------------------------------------------------------
    def _get_obs(self):
        qpos = self.data.qpos
        qvel = self.data.qvel

        joint_pos  = qpos[7:26].astype(np.float32)          # 19
        joint_vel  = qvel[6:25].astype(np.float32)           # 19
        lin_vel    = qvel[0:3].astype(np.float32)            # 3
        proj_grav  = self._projected_gravity().astype(np.float32)  # 3
        goal_vec   = self._goal_vector().astype(np.float32)  # 2
        goal_dist  = np.array([self._goal_dist()], dtype=np.float32)  # 1
        return np.concatenate([joint_pos, joint_vel, lin_vel, proj_grav, goal_vec, goal_dist])

    def _projected_gravity(self):
        """Gravity vector (0,0,-1) rotated into pelvis body frame."""
        quat = self.data.qpos[3:7]  # w,x,y,z
        w, x, y, z = quat
        # Rotate world-down (0,0,-1) into body frame via inverse quaternion
        # R^T * v where R is rotation from body to world
        gx = -2*(x*z + w*y)
        gy = -2*(y*z - w*x)
        gz = -(1 - 2*(x*x + y*y))
        return np.array([gx, gy, gz])

    def _goal_xy(self):
        if self._waypoint_idx < len(self.waypoints):
            wp = self.waypoints[self._waypoint_idx]
            return np.array([wp[0], wp[1]], dtype=np.float64)
        return np.array(_DEFAULT_GOAL, dtype=np.float64)

    def _goal_dist(self):
        pos_xy = np.array([self.data.qpos[0], self.data.qpos[1]])
        return float(np.linalg.norm(self._goal_xy() - pos_xy))

    def _goal_vector(self):
        pos_xy = np.array([self.data.qpos[0], self.data.qpos[1]])
        diff = self._goal_xy() - pos_xy
        dist = np.linalg.norm(diff) + 1e-6
        return diff / dist   # unit vector

    def _heading(self):
        """Yaw angle in radians from quaternion."""
        quat = self.data.qpos[3:7]
        w, x, y, z = quat
        return float(np.arctan2(2*(w*z + x*y), 1 - 2*(y*y + z*z)))

    def _is_terminated(self):
        if self._reached_all:
            return True
        # Fallen — pelvis too low or too tilted
        pelvis_z = self.data.qpos[2]
        if pelvis_z < 0.4:
            return True
        # Torso pitch/roll excessive — projected gravity x or y component too large
        pg = self._projected_gravity()
        if abs(pg[0]) > 0.8 or abs(pg[1]) > 0.8:
            return True
        return False
