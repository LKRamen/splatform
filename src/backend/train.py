"""
Train H1TraversalEnv with SB3 PPO.
Saves checkpoints at 10k, 30k, 60k steps.
Usage: python src/backend/train.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback, BaseCallback
from stable_baselines3.common.env_util import make_vec_env
from src.backend.h1_env import H1TraversalEnv

CHECKPOINT_DIR = os.path.join(os.path.dirname(__file__), 'checkpoints')
os.makedirs(CHECKPOINT_DIR, exist_ok=True)

TOTAL_STEPS = 60_000
PRINT_EVERY = 2_000


class RewardLogCallback(BaseCallback):
    def __init__(self):
        super().__init__()
        self._ep_rewards = []
        self._last_print = 0

    def _on_step(self):
        infos = self.locals.get('infos', [])
        for info in infos:
            if 'episode' in info:
                self._ep_rewards.append(info['episode']['r'])
        steps = self.num_timesteps
        if steps - self._last_print >= PRINT_EVERY and self._ep_rewards:
            mean_r = sum(self._ep_rewards[-20:]) / min(len(self._ep_rewards), 20)
            print(f'  step {steps:6d}  mean_ep_reward: {mean_r:.3f}')
            self._last_print = steps
        return True


def train():
    env = make_vec_env(H1TraversalEnv, n_envs=1)

    model = PPO(
        'MlpPolicy', env,
        learning_rate=3e-4,
        n_steps=512,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        verbose=0,
    )

    # Save at 10k, 30k, 60k
    ckpt_cb = CheckpointCallback(
        save_freq=10_000,
        save_path=CHECKPOINT_DIR,
        name_prefix='policy',
        verbose=0,
    )
    reward_cb = RewardLogCallback()

    print(f'Training PPO on H1TraversalEnv for {TOTAL_STEPS:,} steps...')
    model.learn(total_timesteps=TOTAL_STEPS, callback=[ckpt_cb, reward_cb])

    # Save final versioned checkpoints
    for src_name, dst_name in [
        ('policy_10000_steps.zip', 'v1.zip'),
        ('policy_30000_steps.zip', 'v2.zip'),
        ('policy_60000_steps.zip', 'v3.zip'),
    ]:
        src = os.path.join(CHECKPOINT_DIR, src_name)
        dst = os.path.join(CHECKPOINT_DIR, dst_name)
        if os.path.exists(src) and not os.path.exists(dst):
            os.rename(src, dst)

    # Also save the final model as v3 if the 60k checkpoint didn't get created
    final_path = os.path.join(CHECKPOINT_DIR, 'v3.zip')
    if not os.path.exists(final_path):
        model.save(final_path.replace('.zip', ''))

    print('Done. Checkpoints saved to', CHECKPOINT_DIR)
    env.close()


if __name__ == '__main__':
    train()
