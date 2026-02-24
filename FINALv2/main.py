#sudo /home/siagupta/projects/IR/embeded-rl-algae-bioreactor/venv/bin/python main.py
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

# --- CONFIGURATION ---
LOG_DIR = "./bioreactor_system/"
MODEL_PATH = os.path.join(LOG_DIR, "bioreactor_model")
DEPLOY_CSV = os.path.join(LOG_DIR, "deployment_history.csv")
os.makedirs(LOG_DIR, exist_ok=True)

# ======================================================
# --- HARDWARE HOOKS (Replace with real Pi code) ---
# ======================================================

def get_real_o2():
    print("Get_real_o2: " + str(read_do()))
    return read_do()

def set_hardware_light(percentage):
    print(f"   >>> [HARDWARE] Setting light to {percentage:.2f}%")
    set_leds([26, 27, 28], percentage * 255 / 100)

def inject_hardware_nutrients(ml_amount):
    print(f"   >>> [HARDWARE] Injecting {ml_amount:.2f} ml nutrients")

# ======================================================
# --- REALISTIC BIOREACTOR ENVIRONMENT ---
# ======================================================

class BioreactorEnv(gym.Env):
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
        self.max_steps = max_steps
        
        # Biology parameters
        self.P_max, self.Ks_l, self.Ki_l, self.Kn_n = 150.0, 20.0, 80.0, 5.0
        self.mu_max, self.Ks_n, self.death_rate, self.biomass_max = 0.15, 3.0, 0.01, 2.0
        
        self.reset()
        
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.biomass = 0.1
        self.nutrient_level = 0.0
        self.daily_nutrient_budget = 5.0
        self.step_count = 0
        self.o2_history = deque([10.0] * 10, maxlen=10)
        return self._get_observation(), {}

    def _get_observation(self):
        current_o2 = self.o2_history[-1]
        o2_avg = np.mean(list(self.o2_history))
        time_of_day = (self.step_count % self.steps_per_day) / self.steps_per_day
        
        # Calculate O2 trend (slope over recent readings) - CRITICAL FIX!
        if len(self.o2_history) >= 3:
            recent_o2 = list(self.o2_history)[-3:]  # Last 3 readings
            o2_trend = (recent_o2[-1] - recent_o2[0]) / (len(recent_o2) - 1)
        else:
            o2_trend = 0.0
        
        # Normalize trend to [0, 1] (assuming trend range of -5 to +5 mg/L per step)
        o2_trend_norm = np.clip((o2_trend + 5.0) / 10.0, 0, 1)
        
        return np.array([
            current_o2 / 200.0,
            o2_trend_norm,  # ✅ FIXED: Now calculates actual O2 trend!
            o2_avg / 200.0,
            self.daily_nutrient_budget / 5.0,
            time_of_day
        ], dtype=np.float32)

    def step(self, action):
        light, nutri_req = action
        # Capping the injection to exactly 1ml if the AI requests it, 
        # and ensuring it doesn't exceed the daily budget
        if nutri_req >= 0.5: # Threshold to decide to inject
            actual_nutri = min(1.0, self.daily_nutrient_budget) 
        else:
            actual_nutri = 0.0        
            self.daily_nutrient_budget -= actual_nutri
        
        if self.step_count % self.steps_per_day == 0 and self.step_count > 0:
            self.daily_nutrient_budget = 5.0
            
        self.nutrient_level = (self.nutrient_level + actual_nutri) * 0.95
        growth = self.mu_max * (self.nutrient_level / (self.nutrient_level + self.Ks_n + 1e-6))
        self.biomass = np.clip(self.biomass * (1 + (growth - self.death_rate) * self.dt), 0.01, self.biomass_max)
        
        light_eff = light / (light + self.Ks_l + (light**2 / self.Ki_l) + 1e-6)
        o2_rate = self.P_max * light_eff * (self.nutrient_level / (self.nutrient_level + self.Kn_n + 1e-6)) * (self.biomass / 0.5)
        
        new_o2 = self.o2_history[-1] + (o2_rate * self.dt * 0.1) + np.random.normal(0, 0.1)
        self.o2_history.append(new_o2)
        
        # Reward Logic
        reward = (o2_rate / 5.0) - (light * 0.005)
        if o2_rate > 60: reward += 10.0 
        
        self.step_count += 1
        done = self.step_count >= self.max_steps or self.biomass < 0.05
        
        info = {'o2_reading': new_o2, 'biomass': self.biomass, 'budget': self.daily_nutrient_budget, 'o2_rate': o2_rate}
        return self._get_observation(), float(reward), False, done, info

# ======================================================
# --- TRAINING CALLBACK ---
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
                    print(f"Step {self.n_calls}: New High Reward: {mean_reward:.2f}")
        return True

# ======================================================
# --- CORE FUNCTIONS ---
# ======================================================

def train():
    if os.path.exists(MODEL_PATH + ".zip"): os.remove(MODEL_PATH + ".zip")
    
    env = Monitor(BioreactorEnv(), LOG_DIR)
    new_logger = configure(LOG_DIR, ["stdout", "csv"])
    
    # Updated parameters for stability and sensor noise
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
    
    callback = TrainingCallback() # FIXED: Initializing the callback
    print("\n[INFO] Starting 200,000 step Training...")
    model.learn(total_timesteps=200000, callback=callback)
    model.save(MODEL_PATH)

def deploy_to_reactor():
    initialize_leds()
    if not os.path.exists(MODEL_PATH + ".zip"):
        print("[ERROR] No model found. Train first.")
        return
    
    print("\n🚀 DEPLOYING AI TO HARDWARE (Live Mode)")
    
    model = PPO.load(MODEL_PATH)
    env = BioreactorEnv()
    obs, _ = env.reset()
    
    # Initialize CSV with Headers
    with open(DEPLOY_CSV, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Light_Pct", "Nutri_ml", "O2_Reading", "Biomass"])

    try:
        while True:
            action, _ = model.predict(obs, deterministic=True)
            light_pct, nutri_ml = action
            
            set_hardware_light(light_pct)
            if nutri_ml > 0.1: inject_hardware_nutrients(nutri_ml)
            
            obs, _, _, done, info = env.step(action)
            
            # Log Data to CSV
            timestamp = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(DEPLOY_CSV, mode='a', newline='') as f:
                csv.writer(f).writerow([timestamp, f"{light_pct:.2f}", f"{nutri_ml:.2f}", f"{info['o2_reading']:.2f}", f"{info['biomass']:.3f}"])
            
            print(f"[{timestamp}] O2: {info['o2_reading']:.2f} | Action: Light={light_pct:.1f}% Nutri={nutri_ml:.2f}ml")
            
            if done: break
            time.sleep(0.1 * 60) # 15-minute real-world interval
            
    except KeyboardInterrupt:
        print("\n🛑 Safety shutdown initiated.")
        set_hardware_light(0)
def run_safety_demo():
    """
    Enhanced Safety Demo: Shows real-time health and state indicators
    """
    if not os.path.exists(MODEL_PATH + ".zip"):
        print("[ERROR] No trained model found. Please run training (Option 1) first.")
        return

    model = PPO.load(MODEL_PATH)
    env = BioreactorEnv()
    obs, _ = env.reset()

    print("\n" + "="*95)
    print(f"{'STEP':<5} | {'LIGHT %':<8} | {'NUTRI ml':<9} | {'O2 LEVEL':<9} | {'BIOMASS':<8} | {'HEALTH STATUS'}")
    print("-" * 95)

    for i in range(20):
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)
        
        # Calculate Health Indicators
        biomass = info['biomass']
        o2_rate = info['o2_rate']
        budget = info['budget']
        
        # Logic to determine Health Status string
        if biomass < 0.06:
            status = "⚠️ CRITICAL (Near Death)"
        elif o2_rate > 100:
            status = "🚀 EXCELLENT (Peak Photosynthesis)"
        elif o2_rate > 40:
            status = "✅ STABLE (Healthy Growth)"
        elif budget < 0.5:
            status = "🟡 HUNGRY (Low Nutrient Budget)"
        else:
            status = "💤 DORMANT/STARTUP"

        print(f"{i+1:<5} | {action[0]:<8.1f} | {action[1]:<9.2f} | "
              f"{info['o2_reading']:<9.2f} | {biomass:<8.3f} | {status}")

        if terminated:
            print("-" * 95)
            print("❌ BIO-REACTOR CRASHED: Biomass dropped below safety threshold.")
            break
    
    print("="*95)
    print(f"Final Summary -> Total O2 Produced: {info['o2_reading'] - 10:.2f} mg/L increase")
    print(f"Remaining Nutrient Budget for the Day: {info['budget']:.2f} ml")



def main():
    while True:
        print("\n--- BIO-AI CONTROL CENTER ---")
        print("1: Train AI (200k steps)")
        print("2: RUN HEALTH & SAFETY DEMO") # Updated label
        print("3: DEPLOY TO HARDWARE (Run) ⚠️")
        print("4: Exit")
        choice = input("Select: ")
        if choice == '1': train()
        elif choice == '2': run_safety_demo()
        elif choice == '3': deploy_to_reactor()
        elif choice == '4': break

if __name__ == "__main__":
    main()