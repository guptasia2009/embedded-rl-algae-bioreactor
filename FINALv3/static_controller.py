#sudo /home/siagupta/projects/IR/embeded-rl-algae-bioreactor/venv/bin/python static_control.py
import os
import csv
import time
import pandas as pd

from do_sensor_reader import *
from led_controller import *
from logger import log, set_source
set_source("STATIC")

# --- CONFIGURATION ---
LOG_DIR = "./bioreactor_system/"
STATIC_CSV = os.path.join(LOG_DIR, "static_control_history.csv")
LIGHT_INTENSITY = 50.0          # % — industry standard for Chlorella vulgaris
READ_INTERVAL_SECONDS = 1800    # 30 minutes
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
            "Timestamp", "Light_Pct", "O2_Reading", "Lights_Off"
        ])

    print(f"[INFO] Static control running. Light: {LIGHT_INTENSITY}% | Logging to {STATIC_CSV}")
    print("[INFO] Reading DO every 30 minutes. Press Ctrl+C to stop.\n")

    try:
        while True:
            timestamp = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
            lights_off = is_dark_period()

            # Set light — off during dark period, fixed intensity otherwise
            current_light = 0.0 if lights_off else LIGHT_INTENSITY
            set_leds([45, 46, 47], current_light * 255 / 100)

            # Read DO sensor
            raw_o2 = read_do()
            o2 = float(raw_o2[0]) if isinstance(raw_o2, (list,)) else float(raw_o2)

            print(f"[{timestamp}] O2: {o2:.2f} | Light: {current_light:.1f}% | Lights off: {lights_off}")

            with open(STATIC_CSV, mode='a', newline='') as f:
                csv.writer(f).writerow([
                    timestamp,
                    f"{current_light:.2f}",
                    f"{o2:.2f}",
                    str(lights_off)
                ])

            time.sleep(READ_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        set_leds([26, 27, 28], 0)
        print("\n[INFO] Static control stopped. Lights off.")


if __name__ == "__main__":
    run()