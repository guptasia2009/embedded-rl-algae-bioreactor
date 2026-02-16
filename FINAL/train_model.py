"""
Training Simulation for Bioreactor
"""

import numpy as np
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env
import config

''' Biological Functions '''

def nutrient_limitation(S, X):
    """Droop Model for nutrient limitation"""
    Q = S / (X + 1e-6)
    mu_N = np.maximum(0.0, 1 - config.Q_MIN / Q)
    return mu_N

def light_limitation(I, X):
    """Beer-Lambert law integrated over reactor depth"""
    if X < 1e-6:
        I_avg = I
    else:
        I_avg = I * (1 - np.exp(-config.K_LIGHT * X * config.REACTOR_DEPTH)) / \
                (config.K_LIGHT * X * config.REACTOR_DEPTH)
    mu_I = I_avg / (config.KI + I_avg)
    return mu_I

def growth_rate(X, S, I):
    """Calculate growth rate (no temperature dependence)"""
    mu = config.MU_MAX * nutrient_limitation(S, X) * light_limitation(I, X)
    dXdt = mu * X - config.K_DECAY * X
    return dXdt


''' Environment '''

class BioreactorEnv(gym.Env):
    """
    Bioreactor environment for training
    
    State: [nutrient, DO, DO_trend, light_level]
    Action: [nutrient_rate, led_intensity]
    """
    
    def __init__(self):
        super().__init__()
        
        # State space: [nutrient, DO, DO_trend, light]
        self.observation_space = spaces.Box(
            low=np.array(config.STATE_LOW, dtype=np.float32),
            high=np.array(config.STATE_HIGH, dtype=np.float32)
        )
        
        # Action space: [nutrient_rate, led_intensity]
        self.action_space = spaces.Box(
            low=np.array(config.ACTION_LOW, dtype=np.float32),
            high=np.array(config.ACTION_HIGH, dtype=np.float32)
        )
        
        self.reset()
    
    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        
        # Internal state
        self.X = config.X_INIT  # biomass
        self.S = config.S_INIT  # nutrient
        self.I = config.I_INIT  # light intensity (0-255 scale)
        self.time = 0
        
        # Budgets
        self.nutrient_budget = config.DAILY_NUTRIENT_BUDGET
        self.light_budget = config.DAILY_LIGHT_BUDGET
        self.light_on_hours_today = 0
        
        # DO tracking
        self.DO = 5.0
        self.do_history = [self.DO] * config.DO_HISTORY_LENGTH
        
        return self._get_obs(), {}
    
    def _get_obs(self):
        """Get observation: [nutrient, DO, DO_trend, light]"""
        # Calculate DO trend
        do_trend = 0.0
        if len(self.do_history) >= 2:
            n = min(len(self.do_history), 10)
            do_trend = (self.do_history[-1] - self.do_history[-n]) / n
            do_trend = np.clip(do_trend, -2.0, 2.0)
        
        return np.array([
            self.S,        # nutrient
            self.DO,       # dissolved oxygen
            do_trend,      # DO trend
            self.I         # light level (0-255)
        ], dtype=np.float32)
    
    def step(self, action):
        nutrient_a, light_a = action
        
        # Convert actions from [-1,1] to actual values
        nutrient_rate = (nutrient_a + 1) / 2 * config.MAX_NUTRIENT_RATE
        light_level = (light_a + 1) / 2 * config.MAX_LIGHT_INTENSITY
        
        # Time step
        dt = 1.0  # 1 hour
        
        # Resource usage
        nutrient_use = nutrient_rate * dt
        light_use = light_level * dt
        
        # Reset daily budgets every 24 hours
        if int(self.time) % 24 == 0 and self.time != 0:
            self.nutrient_budget = config.DAILY_NUTRIENT_BUDGET
            self.light_budget = config.DAILY_LIGHT_BUDGET
            self.light_on_hours_today = 0
        
        # Enforce 8-hour dark period
        # If light has been on for 16 hours, force it off
        if light_level > 10 and self.light_on_hours_today >= (24 - config.MIN_DARK_PERIOD):
            light_level = 0
            light_use = 0
        
        # Track light hours
        if light_level > 10:  # Consider "on" if brightness > 10
            self.light_on_hours_today += dt
        
        # Apply budget constraints
        if self.nutrient_budget <= 0:
            nutrient_rate = 0
            nutrient_use = 0
        
        if self.light_budget <= 0:
            light_level = 0
            light_use = 0
        
        self.nutrient_budget -= nutrient_use
        self.light_budget -= light_use
        
        # Update environment
        self.I = light_level
        self.S += nutrient_rate * dt
        
        # Growth (no temperature dependence)
        dX = growth_rate(self.X, self.S, self.I) * dt
        self.X += dX
        self.X = np.clip(self.X, 0.1, 10.0)
        
        # Nutrient consumption
        self.S -= max(dX, 0) * 0.5
        self.S = max(0, self.S)
        
        # DO production
        self.DO = 5.0 + max(dX, 0) * config.DO_YIELD * 2.0
        self.DO += np.random.randn() * 0.2  # Sensor noise
        self.DO = np.clip(self.DO, 0, 20)
        
        # Update DO history
        self.do_history.append(self.DO)
        if len(self.do_history) > 20:
            self.do_history.pop(0)
        
        # Reward is DO production (what we want to maximize)
        reward = max(dX, 0) * config.DO_YIELD
        
        # Penalty for exceeding dark period constraint
        if self.light_on_hours_today > (24 - config.MIN_DARK_PERIOD):
            reward -= 0.5  # Small penalty
        
        self.time += dt
        terminated = bool(self.time >= 500 or self.X <= 0.1)
        
        return self._get_obs(), reward, terminated, False, {}


def train_model():
    """Train the RL model"""
    print("="*70)
    print("TRAINING RL MODEL FOR TRIPLE BIOREACTOR")
    print("="*70)
    print("\nConfiguration:")
    print(f"  State: [nutrient, DO, DO_trend, light_level]")
    print(f"  Action: [nutrient_rate, led_intensity]")
    print(f"  Controls: Nutrient + LED (NO temperature)")
    print(f"  Dark period: {config.MIN_DARK_PERIOD} hours minimum")
    print(f"  Daily nutrient budget: {config.DAILY_NUTRIENT_BUDGET} mL")
    print("="*70 + "\n")
    
    # Create environment
    print("Creating environment...")
    env = BioreactorEnv()
    check_env(env)
    print("Environment validated\n")
    
    # Create model
    print("Initializing PPO model...")
    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        learning_rate=config.LEARNING_RATE,
        gamma=config.GAMMA,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        ent_coef=0.01,
    )
    
    print("\n" + "="*70)
    print(f"TRAINING FOR {config.TRAINING_TIMESTEPS:,} TIMESTEPS")
    print("This will take 15-25 minutes...")
    print("="*70 + "\n")
    
    # Train
    model.learn(total_timesteps=config.TRAINING_TIMESTEPS)
    
    # Save
    model.save(config.MODEL_PATH)
    
    print("\n" + "="*70)
    print("TRAINING COMPLETE")
    print("="*70)
    print(f"Model saved to: {config.MODEL_PATH}")
    
    # Test the model
    print("\n" + "="*70)
    print("TESTING TRAINED MODEL")
    print("="*70)
    
    test_scenarios = [
        ([5.0, 5.0, 0.0, 128.0], "Normal: medium nutrients, stable DO, medium light"),
        ([2.0, 3.0, -0.2, 128.0], "Low nutrients, DO declining, medium light"),
        ([8.0, 7.0, 0.5, 128.0], "High nutrients, DO rising, medium light"),
        ([5.0, 5.0, 0.0, 0.0], "Medium nutrients, stable, lights OFF"),
    ]
    
    print("\nModel predictions:\n")
    for state, description in test_scenarios:
        action, _ = model.predict(np.array(state, dtype=np.float32), deterministic=True)
        nutrient_rate = (action[0] + 1) / 2 * 100  # Convert to percentage
        led_intensity = (action[1] + 1) / 2 * 255  # Convert to 0-255
        
        print(f"{description}")
        print(f"  State: nutrient={state[0]:.1f}, DO={state[1]:.1f}, trend={state[2]:+.2f}, light={state[3]:.0f}")
        print(f"  Action: Nutrient={nutrient_rate:.0f}%, LED={led_intensity:.0f}/255")
        print()
    
    # Run full episode
    print("="*70)
    print("RUNNING FULL SIMULATION")
    print("="*70 + "\n")
    
    obs, _ = env.reset()
    total_reward = 0
    max_do = 0
    steps = 0
    
    while True:
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, _ = env.step(action)
        total_reward += reward
        max_do = max(max_do, obs[1])  # DO is index 1
        steps += 1
        
        if terminated or truncated:
            break
    
    print(f"Episode Results:")
    print(f"  Duration: {steps} hours")
    print(f"  Total DO production: {total_reward:.2f}")
    print(f"  Max DO: {max_do:.2f} mg/L")
    print(f"  Final nutrient: {obs[0]:.2f}")
    print(f"  Final biomass: {env.X:.2f}")
    
    print("\n" + "="*70)
    print("MODEL READY FOR DEPLOYMENT")


if __name__ == "__main__":
    train_model()