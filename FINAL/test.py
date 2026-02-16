import time
import csv
from datetime import datetime
from pathlib import Path
from stable_baselines3 import PPO

import config
from state_estimator import *

model_path="bioreactor_model.zip"
model = PPO.load(model_path)

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