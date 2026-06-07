"""
Unitree G1 traversal environment (MuJoCo Menagerie unitree_g1/g1.xml).

Replaces the earlier H1 env (see h1_env.py, retired). The G1 is a 29-DOF
humanoid, so observation/action dimensions are derived from the loaded model
rather than hard-coded: this env adapts automatically if the model changes.
"""
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

_XML_PATH = os.path.join(os.path.dirname(__file__), '../../mujoco_menagerie/unitree_g1/g1.xml')

# Reward weights from CLAUDE.md scoring rubric
_W = {
    'waypoint': 0.30,
    'gait': 0.25,
    'clearance': 0.20,
    'energy': 0.15,
    'completion': 0.10,
}

_DEFAULT_STANDING_HEIGHT = 0.79   # G1 pelvis height from the home keyframe
_MAX_STEPS = 1000
_WAYPOINT_RADIUS = 0.5            # metres — distance to count waypoint as reached
_DEFAULT_GOAL = np.array([5.0, 0.0])   # (x, z) target in world XZ plane
_OBSTACLE_PENALTY_RADIUS = 0.8   # metres — within this distance, apply penalty
_NUM_OBSTACLES = 2
_FALL_HEIGHT_FRACTION = 0.38     # pelvis below this fraction of standing → fallen


class _DynamicObstacle:
    """Pedestrian-like obstacle with bounded random walk in XZ plane."""

    def __init__(self, rng):
        angle = rng.uniform(0, 2 * np.pi)
        radius = rng.uniform(3.0, 8.0)
        self.pos = np.array([radius * np.cos(angle), radius * np.sin(angle)])
        speed = rng.uniform(0.3, 0.8)
        dir_angle = rng.uniform(0, 2 * np.pi)
        self.vel = speed * np.array([np.cos(dir_angle), np.sin(dir_angle)])
        self._rng = rng

    def step(self, dt=0.02):
        self.vel += self._rng.normal(0, 0.1, size=2)
        speed = np.linalg.norm(self.vel)
        if speed > 1.0:
            self.vel = self.vel / speed * 1.0
        elif speed < 0.2:
            self.vel = self.vel / (speed + 1e-6) * 0.2
        self.pos += self.vel * dt
        for i in range(2):
            if abs(self.pos[i]) > 10.0:
                self.vel[i] *= -1
                self.pos[i] = np.clip(self.pos[i], -10.0, 10.0)

    def world_pos(self):
        """Returns [x, y, z] with y=0.9 (pedestrian centre height)."""
        return [float(self.pos[0]), 0.9, float(self.pos[1])]


class G1TraversalEnv(gym.Env):
    """Unitree G1 traversal env wrapping MuJoCo Menagerie g1.xml."""

    metadata = {'render_modes': []}

    def __init__(self, waypoints=None):
        super().__init__()
        self.model = mujoco.MjModel.from_xml_path(_XML_PATH)
        self.data = mujoco.MjData(self.model)

        # Dimensions derived from the model: nu actuated joints, free base
        # occupies qpos[:7] / qvel[:6].
        self.n_joints = self.model.nu
        obs_dim = self.n_joints * 2 + 3 + 3 + 2 + 1  # pos+vel + lin_vel + grav + goal_vec + goal_dist

        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(obs_dim,), dtype=np.float32
        )
        self.action_space = spaces.Box(
            low=-1.0, high=1.0, shape=(self.n_joints,), dtype=np.float32
        )

        # Standing pelvis height from the home keyframe (fallback to default).
        if self.model.nkey > 0:
            self._standing_height = float(self.model.key_qpos[0][2])
        else:
            self._standing_height = _DEFAULT_STANDING_HEIGHT

        self._default_waypoints = waypoints if waypoints is not None else [_DEFAULT_GOAL.copy()]
        self.waypoints = list(self._default_waypoints)
        self._waypoint_idx = 0
        self._step_count = 0
        self._prev_dist = None
        self._prev_action = np.zeros(self.n_joints)
        self._reached_all = False
        self._rng = np.random.default_rng()
        self._obstacles = [_DynamicObstacle(self._rng) for _ in range(_NUM_OBSTACLES)]

        # Cache joint limits for action scaling (skip the free base joint).
        jnt_range = self.model.jnt_range[1:]
        self._jnt_lo = jnt_range[:, 0].copy()
        self._jnt_hi = jnt_range[:, 1].copy()

    def set_waypoints(self, waypoints):
        self.waypoints = list(waypoints)

    def home_pose_action(self):
        """Action in [-1,1] that commands the home keyframe joint pose.

        Used as a stand-in policy when no trained checkpoint exists, so the
        robot holds a stable standing stance instead of flailing on random
        torques.
        """
        mid = (self._jnt_lo + self._jnt_hi) * 0.5
        half = (self._jnt_hi - self._jnt_lo) * 0.5
        half = np.where(half == 0, 1.0, half)
        if self.model.nkey > 0:
            target = self.model.key_qpos[0][7:7 + self.n_joints]
        else:
            target = mid
        return np.clip((target - mid) / half, -1.0, 1.0).astype(np.float32)

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        mujoco.mj_resetData(self.model, self.data)
        if self.model.nkey > 0:
            mujoco.mj_resetDataKeyframe(self.model, self.data, 0)
        mujoco.mj_forward(self.model, self.data)

        self.waypoints = list(self._default_waypoints)
        self._waypoint_idx = 0
        self._step_count = 0
        self._prev_action = np.zeros(self.n_joints)
        self._reached_all = False
        self._obstacles = [_DynamicObstacle(self._rng) for _ in range(_NUM_OBSTACLES)]
        self._prev_dist = self._goal_dist()
        return self._get_obs(), {}

    def preview_step(self):
        """Kinematic standing preview for when no trained policy exists.

        Holds the home standing stance and glides the base toward the active
        waypoint (no dynamics), so the untrained robot looks upright and
        purposeful instead of collapsing under random torques. Returns the
        same (obs, reward, terminated, truncated, info) tuple as step().
        """
        self._step_count += 1
        base = self.data.qpos[:2].copy()
        goal = self._goal_xy()
        to_goal = goal - base
        dist = float(np.linalg.norm(to_goal))

        qpos = self.model.key_qpos[0].copy() if self.model.nkey > 0 else self.data.qpos.copy()
        if dist > _WAYPOINT_RADIUS:
            direction = to_goal / (dist + 1e-9)
            base = base + direction * min(0.8 * 0.02, dist)   # ~0.8 m/s glide
            heading = float(np.arctan2(direction[1], direction[0]))
        else:
            heading = self._heading()
            if self._waypoint_idx < len(self.waypoints) - 1:
                self._waypoint_idx += 1
            else:
                self._reached_all = True

        qpos[0], qpos[1] = base[0], base[1]
        qpos[2] = self._standing_height
        qpos[3:7] = [np.cos(heading / 2), 0.0, 0.0, np.sin(heading / 2)]  # yaw about up
        self.data.qpos[:] = qpos
        self.data.qvel[:] = 0.0
        mujoco.mj_forward(self.model, self.data)

        for obs in self._obstacles:
            obs.step()

        r_gait = gait_stability_reward(qpos[2], self._standing_height, qpos[3:7])
        info = {
            'scores': {
                'waypoint': 0.0, 'gait': float(r_gait), 'clearance': 1.0,
                'energy': 0.0, 'completion': float(self._reached_all),
                'total': float(r_gait),
            },
            'position': self.data.qpos[:3].tolist(),
            'heading': self._heading(),
            'obstacles': [o.world_pos() for o in self._obstacles],
        }
        terminated = self._reached_all
        truncated = self._step_count >= _MAX_STEPS
        return self._get_obs(), 0.0, terminated, truncated, info

    def step(self, action):
        action = np.clip(action, -1.0, 1.0)

        # Scale [-1,1] to joint position targets.
        mid = (self._jnt_lo + self._jnt_hi) * 0.5
        half = (self._jnt_hi - self._jnt_lo) * 0.5
        self.data.ctrl[:] = mid + action * half

        mujoco.mj_step(self.model, self.data)
        self._step_count += 1

        for obs in self._obstacles:
            obs.step()

        pelvis_z = self.data.qpos[2]

        dist = self._goal_dist()
        if dist < _WAYPOINT_RADIUS:
            if self._waypoint_idx < len(self.waypoints) - 1:
                self._waypoint_idx += 1
                self._prev_dist = self._goal_dist()
            else:
                self._reached_all = True

        r_waypoint = waypoint_efficiency_reward(dist, self._prev_dist, self._step_count)
        r_gait = gait_stability_reward(pelvis_z, self._standing_height, self.data.qpos[3:7])
        r_clearance = clearance_reward(self.data, self.model)
        r_energy = energy_reward(self.data.actuator_force)
        r_complete = completion_reward(self._reached_all)

        robot_xz = np.array([self.data.qpos[0], self.data.qpos[1]])
        r_obstacle = 0.0
        for obs in self._obstacles:
            d = float(np.linalg.norm(robot_xz - obs.pos))
            if d < _OBSTACLE_PENALTY_RADIUS:
                r_obstacle -= (1.0 - d / _OBSTACLE_PENALTY_RADIUS)

        reward = (
            _W['waypoint'] * r_waypoint +
            _W['gait'] * r_gait +
            _W['clearance'] * r_clearance +
            _W['energy'] * r_energy +
            _W['completion'] * r_complete +
            0.15 * r_obstacle
        )

        self._prev_dist = dist
        self._prev_action = action.copy()

        terminated = self._is_terminated()
        truncated = self._step_count >= _MAX_STEPS

        info = {
            'scores': {
                'waypoint': float(r_waypoint),
                'gait': float(r_gait),
                'clearance': float(r_clearance),
                'energy': float(r_energy),
                'completion': float(r_complete),
                'total': float(reward),
            },
            'position': self.data.qpos[:3].tolist(),
            'heading': self._heading(),
            'obstacles': [obs.world_pos() for obs in self._obstacles],
        }
        return self._get_obs(), float(reward), terminated, truncated, info

    # ------------------------------------------------------------------
    def _get_obs(self):
        qpos = self.data.qpos
        qvel = self.data.qvel
        n = self.n_joints

        joint_pos = qpos[7:7 + n].astype(np.float32)
        joint_vel = qvel[6:6 + n].astype(np.float32)
        lin_vel = qvel[0:3].astype(np.float32)
        proj_grav = self._projected_gravity().astype(np.float32)
        goal_vec = self._goal_vector().astype(np.float32)
        goal_dist = np.array([self._goal_dist()], dtype=np.float32)
        return np.concatenate([joint_pos, joint_vel, lin_vel, proj_grav, goal_vec, goal_dist])

    def _projected_gravity(self):
        """Gravity vector (0,0,-1) rotated into pelvis body frame."""
        w, x, y, z = self.data.qpos[3:7]
        gx = -2 * (x * z + w * y)
        gy = -2 * (y * z - w * x)
        gz = -(1 - 2 * (x * x + y * y))
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
        return diff / dist

    def _heading(self):
        """Yaw angle in radians from quaternion."""
        w, x, y, z = self.data.qpos[3:7]
        return float(np.arctan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z)))

    def _is_terminated(self):
        if self._reached_all:
            return True
        pelvis_z = self.data.qpos[2]
        if pelvis_z < self._standing_height * _FALL_HEIGHT_FRACTION:
            return True
        pg = self._projected_gravity()
        if abs(pg[0]) > 0.8 or abs(pg[1]) > 0.8:
            return True
        return False
