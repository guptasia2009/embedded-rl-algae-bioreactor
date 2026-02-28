#sudo /home/siagupta/projects/IR/embeded-rl-algae-bioreactor/venv/bin/python main2.py
#nohup bash -c 'echo -e "1,2\n1\n1\n3" | sudo /home/siagupta/projects/IR/embeded-rl-algae-bioreactor/venv/bin/python main2.py' > main2_output.log 2>&1 &
import os
import csv
import time
import gymnasium as gym
import torch
from gymnasium import spaces
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from stable_baselines3 import PPO
from stable_baselines3.common.logger import configure
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.monitor import Monitor
from collections import deque

from do_sensor_reader import *
from led_controller import *
from servo_controller import *
from logger import log, set_source
set_source("RL")

# --- CONFIGURATION ---
LOG_DIR = "./bioreactor_system/"
MODEL_PATH = os.path.join(LOG_DIR, "bioreactor_model")
ONLINE_MODEL_PATH = os.path.join(LOG_DIR, "bioreactor_model_online")
DEPLOY_CSV = os.path.join(LOG_DIR, "deployment_history_RL_1.csv")
STATIC_CSV = os.path.join(LOG_DIR, "static_control_history.csv")
os.makedirs(LOG_DIR, exist_ok=True)

# LED pins
RL_LEDS     = [26, 27, 28]
STATIC_LEDS = [45, 46, 47]

# Static control settings
STATIC_LIGHT_INTENSITY = 75.0  # % — industry standard for Chlorella vulgaris

# Lights off from 10pm to 6am
LIGHTS_OFF_START = 22
LIGHTS_OFF_END   = 6


# ======================================================
# HARDWARE HOOKS
# ======================================================

def is_dark_period():
    hour = pd.Timestamp.now().hour
    return hour >= LIGHTS_OFF_START or hour < LIGHTS_OFF_END

def get_all_o2():
    """Read both probes at once. Returns (rl_o2, static_o2)."""
    raw = read_do()
    print("read_do(): " + str(raw))
    rl_o2     = float(raw[0])
    static_o2 = float(raw[1])
    return rl_o2, static_o2

def get_real_o2(readings):
    """Extract RL o2 from a pre-fetched readings tuple."""
    return readings[0]

def set_hardware_light(percentage):
    print(f"[HARDWARE] Setting RL light to {percentage:.2f}%")
    set_leds(RL_LEDS, percentage * 255 / 100)

def inject_hardware_nutrients(ml_amount):
    print(f"[HARDWARE] Injecting {ml_amount:.2f} ml nutrients")
    dispense(1, ml_amount)

def run_static_step(static_o2):
    """Set static light and log static DO. Called every RL step (30 min)."""
    timestamp = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    lights_off = is_dark_period()
    current_light = 0.0 if lights_off else STATIC_LIGHT_INTENSITY
    set_leds(STATIC_LEDS, current_light * 255 / 100)

    print(f"[STATIC][{timestamp}] O2: {static_o2:.2f} | Light: {current_light:.1f}% | Lights off: {lights_off}")
    log(f"[STATIC] O2: {static_o2:.2f} | Light: {current_light:.1f}% | Lights off: {lights_off}")

    with open(STATIC_CSV, mode='a', newline='') as f:
        csv.writer(f).writerow([
            timestamp,
            f"{current_light:.2f}",
            f"{static_o2:.2f}",
            str(lights_off)
        ])


# ======================================================
# SIMULATION ENVIRONMENT
# ======================================================

class BioreactorEnv(gym.Env):
    LIGHT_OFF_STEP_START = 72
    LIGHT_OFF_STEP_END   = 96

    def __init__(self, simulation_mode=True, max_steps=96, dt=0.25):
        super(BioreactorEnv, self).__init__()

        self.action_space = spaces.Box(
            low=np.array([0, 0]),
            high=np.array([100, 1]),
            dtype=np.float32
        )
        self.observation_space = spaces.Box(low=0, high=1, shape=(5,), dtype=np.float32)

        self.dt = dt
        self.steps_per_day = int(24 / dt)
        self.steps_per_half_day = int(12 / dt)
        self.max_steps = max_steps

        self.P_max, self.Ks_l, self.Ki_l, self.Kn_n = 150.0, 20.0, 80.0, 5.0
        self.mu_max, self.Ks_n, self.death_rate, self.biomass_max = 0.15, 3.0, 0.01, 2.0

        self.reset()

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.biomass = 0.1
        self.nutrient_level = 0.0
        self.daily_nutrient_budget = 4.0
        self.half_day_nutrient_used = 0.0
        self.step_count = 0
        self.o2_history = deque([10.0] * 10, maxlen=10)
        return self._get_observation(), {}

    def _get_observation(self):
        current_o2 = self.o2_history[-1]
        o2_avg = np.mean(list(self.o2_history))
        time_of_day = (self.step_count % self.steps_per_day) / self.steps_per_day

        if len(self.o2_history) >= 3:
            recent_o2 = list(self.o2_history)[-3:]
            o2_trend = (recent_o2[-1] - recent_o2[0]) / (len(recent_o2) - 1)
        else:
            o2_trend = 0.0

        o2_trend_norm = np.clip((o2_trend + 5.0) / 10.0, 0, 1)

        return np.array([
            current_o2 / 200.0,
            o2_trend_norm,
            o2_avg / 200.0,
            self.daily_nutrient_budget / 4.0,
            time_of_day
        ], dtype=np.float32)

    def step(self, action):
        light, nutri_req = action

        step_in_day = self.step_count % self.steps_per_day
        if self.LIGHT_OFF_STEP_START <= step_in_day < self.LIGHT_OFF_STEP_END:
            light = 0.0

        if self.step_count > 0 and self.step_count % self.steps_per_half_day == 0:
            self.half_day_nutrient_used = 0.0

        if self.step_count > 0 and self.step_count % self.steps_per_day == 0:
            self.daily_nutrient_budget = 4.0

        half_day_remaining = max(0.0, 2.0 - self.half_day_nutrient_used)
        actual_nutri = float(min(float(nutri_req), half_day_remaining, self.daily_nutrient_budget))

        self.daily_nutrient_budget = max(0.0, self.daily_nutrient_budget - actual_nutri)
        self.half_day_nutrient_used += actual_nutri

        self.nutrient_level = (self.nutrient_level + actual_nutri) * 0.95
        growth = self.mu_max * (self.nutrient_level / (self.nutrient_level + self.Ks_n + 1e-6))
        self.biomass = np.clip(self.biomass * (1 + (growth - self.death_rate) * self.dt), 0.01, self.biomass_max)

        light_eff = light / (light + self.Ks_l + (light**2 / self.Ki_l) + 1e-6)
        o2_rate = self.P_max * light_eff * (self.nutrient_level / (self.nutrient_level + self.Kn_n + 1e-6)) * (self.biomass / 0.5)

        new_o2 = self.o2_history[-1] + (o2_rate * self.dt * 0.1) + np.random.normal(0, 0.1)
        self.o2_history.append(new_o2)

        reward = (o2_rate / 5.0) - (light * 0.005)
        if o2_rate > 60:
            reward += 10.0

        self.step_count += 1
        done = self.step_count >= self.max_steps or self.biomass < 0.05

        info = {
            'o2_reading': new_o2,
            'biomass': self.biomass,
            'budget': self.daily_nutrient_budget,
            'half_day_used': self.half_day_nutrient_used,
            'o2_rate': o2_rate,
            'actual_nutri': actual_nutri,
            'light_forced_off': light == 0.0
        }
        return self._get_observation(), float(reward), False, done, info


# ======================================================
# REAL HARDWARE ENVIRONMENT
# ======================================================

class RealBioreactorEnv(BioreactorEnv):
    LIGHTS_OFF_START = 22
    LIGHTS_OFF_END   = 6

    def step(self, action):
        light, nutri_req = action

        current_hour = pd.Timestamp.now().hour
        lights_off = (current_hour >= self.LIGHTS_OFF_START or current_hour < self.LIGHTS_OFF_END)
        if lights_off:
            action = np.array([0.0, nutri_req], dtype=np.float32)

        obs, reward, terminated, truncated, info = super().step(action)

        # Read both probes at once — index 0 is RL, index 1 is static
        rl_o2, static_o2 = get_all_o2()
        self.o2_history.append(rl_o2)
        info['o2_reading'] = rl_o2
        info['static_o2']  = static_o2
        info['lights_off'] = lights_off

        obs = self._get_observation()
        return obs, reward, terminated, truncated, info


# ======================================================
# CALLBACKS
# ======================================================

class TrainingCallback(BaseCallback):
    def __init__(self, check_freq=5000, verbose=1):
        super(TrainingCallback, self).__init__(verbose)
        self.check_freq = check_freq
        self.best_mean_reward = -np.inf

    def _on_step(self) -> bool:
        if self.n_calls % self.check_freq == 0:
            if len(self.model.ep_info_buffer) > 0:
                mean_reward = np.mean([ep_info['r'] for ep_info in self.model.ep_info_buffer])
                if mean_reward > self.best_mean_reward:
                    self.best_mean_reward = mean_reward
                    print(f"Step {self.n_calls}: New best reward: {mean_reward:.2f}")
        return True


class HardwareStepCallback(BaseCallback):
    def __init__(self, step_interval_seconds=1800, verbose=1):
        super(HardwareStepCallback, self).__init__(verbose)
        self.step_interval_seconds = step_interval_seconds

    def _on_step(self) -> bool:
        action = self.locals['actions'][0]
        light_pct = float(action[0])
        info = self.locals['infos'][0]
        timestamp = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')

        # --- STATIC STEP FIRST ---
        run_static_step(info.get('static_o2', 0.0))

        # --- RL STEP ---
        if is_dark_period():
            light_pct = 0.0
        set_hardware_light(light_pct)

        actually_dispensed = info['actual_nutri']
        if actually_dispensed > 0.0:
            inject_hardware_nutrients(actually_dispensed)

        step_in_day = self.n_calls % 48
        if step_in_day == 47:
            print("[HARDWARE] End of day - resetting servo. Please refill syringe.")
            reset_servo(1)

        print(f"[RL][{timestamp}] O2: {info['o2_reading']:.2f} | Light: {light_pct:.1f}% | "
              f"Dispensed: {actually_dispensed:.3f}ml | Budget: {info['budget']:.2f}ml | "
              f"Half-day used: {info['half_day_used']:.2f}ml | Lights off: {info.get('lights_off', False)}")

        log(f"[RL] O2: {info['o2_reading']:.2f} | Light: {light_pct:.1f}% | "
            f"Dispensed: {actually_dispensed:.3f}ml | Budget: {info['budget']:.2f}ml | "
            f"Lights off: {info.get('lights_off', False)}")

        with open(DEPLOY_CSV, mode='a', newline='') as f:
            csv.writer(f).writerow([
                timestamp,
                f"{light_pct:.2f}",
                f"{actually_dispensed:.3f}",
                f"{info['o2_reading']:.2f}",
                f"{info['biomass']:.3f}",
                f"{info['budget']:.2f}",
                f"{info['half_day_used']:.2f}",
                str(info.get('lights_off', False))
            ])

        time.sleep(self.step_interval_seconds)
        return True


# ======================================================
# CORE FUNCTIONS
# ======================================================

def train():
    if os.path.exists(MODEL_PATH + ".zip"):
        os.remove(MODEL_PATH + ".zip")

    env = Monitor(BioreactorEnv(), LOG_DIR)
    new_logger = configure(LOG_DIR, ["stdout", "csv"])

    model = PPO(
        "MlpPolicy", env,
        learning_rate=0.0001,
        n_steps=4096,
        batch_size=128,
        n_epochs=15,
        gamma=0.99,
        ent_coef=0.03,
        device="cpu",
        verbose=1
    )
    model.set_logger(new_logger)

    callback = TrainingCallback()
    print("\n[INFO] Starting 200,000 step training...")
    model.learn(total_timesteps=200000, callback=callback)
    model.save(MODEL_PATH)
    print(f"\n[INFO] Model saved to {MODEL_PATH}")


def deploy_to_reactor():
    initialize_leds()

    # Write static CSV header
    with open(STATIC_CSV, mode='w', newline='') as f:
        csv.writer(f).writerow(["Timestamp", "Light_Pct", "O2_Reading", "Lights_Off"])

    if os.path.exists(ONLINE_MODEL_PATH + ".zip"):
        load_path = ONLINE_MODEL_PATH
        print("\n[INFO] Resuming from previous online model...")
    elif os.path.exists(MODEL_PATH + ".zip"):
        load_path = MODEL_PATH
        print("\n[INFO] Starting from base trained model...")
    else:
        print("[ERROR] No model found. Run training (Option 1) first.")
        return

    print("[INFO] Deploying to hardware with continual learning enabled.")

    real_env = Monitor(RealBioreactorEnv(), LOG_DIR)
    model = PPO.load(load_path, env=real_env)

    model.n_steps = 48
    model.batch_size = 16
    model._last_obs = None
    model._setup_learn(total_timesteps=100000, callback=None, reset_num_timesteps=False)

    online_logger = configure(LOG_DIR, ["stdout", "csv"])
    model.set_logger(online_logger)

    with open(DEPLOY_CSV, mode='w', newline='') as f:
        csv.writer(f).writerow([
            "Timestamp", "Light_Pct", "Nutri_ml", "O2_Reading",
            "Biomass", "Daily_Budget_Left", "Half_Day_Used", "Lights_Off"
        ])

    print(f"[INFO] Logging RL to {DEPLOY_CSV}")
    print(f"[INFO] Logging static to {STATIC_CSV}")
    print("[INFO] Press Ctrl+C to stop and save.")
    print("[INFO] Making a decision every 30 minutes.\n")

    try:
        model.learn(
            total_timesteps=100000,
            callback=[TrainingCallback(check_freq=48), HardwareStepCallback(step_interval_seconds=1800)],
            reset_num_timesteps=False
        )
        model.save(ONLINE_MODEL_PATH)
        print(f"\n[INFO] Online model saved to {ONLINE_MODEL_PATH}")

    except KeyboardInterrupt:
        print("\n[INFO] Shutdown signal received. Saving model...")
        model.save(ONLINE_MODEL_PATH)
        set_hardware_light(0)
        set_leds(STATIC_LEDS, 0)
        print(f"[INFO] Model saved to {ONLINE_MODEL_PATH}")


def run_safety_demo():
    if not os.path.exists(MODEL_PATH + ".zip"):
        print("[ERROR] No trained model found. Run training (Option 1) first.")
        return

    load_path = ONLINE_MODEL_PATH if os.path.exists(ONLINE_MODEL_PATH + ".zip") else MODEL_PATH
    model = PPO.load(load_path)
    env = BioreactorEnv()
    obs, _ = env.reset()

    print("\n" + "="*110)
    print(f"{'STEP':<5} | {'LIGHT %':<8} | {'NUTRI ml':<9} | {'O2 LEVEL':<9} | {'BIOMASS':<8} | {'BUDGET LEFT':<12} | {'HEALTH STATUS'}")
    print("-" * 110)

    for i in range(20):
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)

        biomass = info['biomass']
        o2_rate = info['o2_rate']
        budget  = info['budget']

        if biomass < 0.06:
            status = "CRITICAL (near death)"
        elif o2_rate > 100:
            status = "EXCELLENT (peak photosynthesis)"
        elif o2_rate > 40:
            status = "STABLE (healthy growth)"
        elif budget < 0.5:
            status = "LOW NUTRIENTS"
        else:
            status = "DORMANT / STARTUP"

        print(f"{i+1:<5} | {action[0]:<8.1f} | {action[1]:<9.2f} | "
              f"{info['o2_reading']:<9.2f} | {biomass:<8.3f} | {budget:<12.2f} | {status}")

        if terminated:
            print("-" * 110)
            print("[STOPPED] Biomass dropped below safety threshold.")
            break

    print("=" * 110)
    print(f"O2 change: {info['o2_reading'] - 10:.2f} mg/L")
    print(f"Daily nutrient budget remaining: {info['budget']:.2f} ml")
    print(f"Half-day nutrient used: {info['half_day_used']:.2f} ml")


def main():
    while True:
        print("\n--- BIOREACTOR CONTROL ---")
        print("1: Train model (200k steps, simulation)")
        print("2: Run safety demo")
        print("3: Deploy to hardware (continual learning)")
        print("4: Exit")
        choice = input("Select: ")
        if   choice == '1': train()
        elif choice == '2': run_safety_demo()
        elif choice == '3': deploy_to_reactor()
        elif choice == '4': break

if __name__ == "__main__":
    main()