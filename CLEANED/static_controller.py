# STATIC CONTROLLER
# sudo /home/siagupta/projects/IR/embeded-rl-algae-bioreactor/venv/bin/python static_controller.py
import os
import csv
import time
import pandas as pd

from led_controller import *

# Configuration
LOG_DIR = "./bioreactor_system/"
STATIC_CSV = os.path.join(LOG_DIR, "static_control_history.csv")
LIGHT_INTENSITY = 75.0          
LOG_INTERVAL_SECONDS = 1800     
os.makedirs(LOG_DIR, exist_ok=True)

# Lights off from 10pm to 6am
LIGHTS_OFF_START = 22
LIGHTS_OFF_END   = 6


def is_dark_period():
    hour = pd.Timestamp.now().hour
    return hour >= LIGHTS_OFF_START or hour < LIGHTS_OFF_END


def run():
    initialize_leds()

    # Write CSV header
    with open(STATIC_CSV, mode='w', newline='') as f:
        csv.writer(f).writerow([
            "Timestamp", "Light_Pct", "Lights_Off"
        ])

    print(f"[INFO] Static control running. Light: {LIGHT_INTENSITY}% | Logging to {STATIC_CSV}")
    print("[INFO] Logging every 30 minutes. Press Ctrl+C to stop.\n")

    try:
        while True:
            timestamp = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
            lights_off = is_dark_period()

            current_light = 0.0 if lights_off else LIGHT_INTENSITY
            set_leds([26, 27, 28], current_light * 255 / 100)

            print(f"[{timestamp}] Light: {current_light:.1f}% | Lights off: {lights_off}")

            with open(STATIC_CSV, mode='a', newline='') as f:
                csv.writer(f).writerow([
                    timestamp,
                    f"{current_light:.2f}",
                    str(lights_off)
                ])

            time.sleep(LOG_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        set_leds([26, 27, 28], 0)
        print("\n[INFO] Static control stopped. Lights off.")


if __name__ == "__main__":
    run()