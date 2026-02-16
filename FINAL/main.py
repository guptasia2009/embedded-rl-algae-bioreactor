"""
Main Bioreactor Control System
"""

import time
import csv
from datetime import datetime
from pathlib import Path
from stable_baselines3 import PPO

import config
from logger import log as write_log
from servo_controller import *
from led_controller import *
from do_sensor_reader import *
from state_estimator import *


def create_files():
    """Create log and CSV files"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    log_file = f"bioreactor_log_{timestamp}.txt"
    with open(log_file, 'w') as f:
        f.write(f"Bioreactor Log - {timestamp}\n\n")
    
    csv_file = f"bioreactor_data_{timestamp}.csv"
    headers = ["timestamp", "elapsed_hours"]
    for i in range(1, 4):
        headers.extend([
            f"r{i}_do", f"r{i}_nutrient_est", f"r{i}_do_trend", f"r{i}_light_level",
            f"r{i}_nutrient_added", f"r{i}_nutrient_used_today", f"r{i}_total_nutrients_added",
            f"r{i}_light_hours_today", f"r{i}_action_nutrient", f"r{i}_action_light"
        ])
    
    with open(csv_file, 'w', newline='') as f:
        csv.writer(f).writerow(headers)
    
    return log_file, csv_file


def log_to_file(log_file, message):
    """Write to log file"""
    with open(log_file, 'a') as f:
        f.write(f"{datetime.now().isoformat()} - {message}\n")


def save_data(csv_file, elapsed_hours, reactor_data):
    """Save data to CSV"""
    row = [datetime.now().isoformat(), elapsed_hours]
    for data in reactor_data:
        row.extend([
            data['do'], data['nutrient_est'], data['do_trend'], data['light_level'],
            data['nutrient_added'], data['nutrient_used_today'], data['total_nutrients_added'],
            data['light_hours_today'], data['action_nutrient'], data['action_light']
        ])
    
    with open(csv_file, 'a', newline='') as f:
        csv.writer(f).writerow(row)


def run_bioreactor(model_path="bioreactor_model.zip", duration_hours=120):
    """Main control loop"""
    
    # Load model
    if not Path(model_path).exists():
        print(f"ERROR: Model not found")
        return
    
    model = PPO.load(model_path)
    
    # Setup
    reactor_leds = [config.REACTOR_1_LEDS, config.REACTOR_2_LEDS, config.REACTOR_3_LEDS]
    nutrients_used_today = [0.0, 0.0, 0.0]
    total_nutrients_added = [0.0, 0.0, 0.0]
    light_on_hours_today = [0.0, 0.0, 0.0]
    last_24hr_reset = [time.time()] * 3
    
    # Create files
    log_file, csv_file = create_files()
    log_to_file(log_file, "Experiment started")
    
    start_time = time.time()
    last_control_time = start_time
    
    try:
        while True:
            current_time = time.time()
            elapsed_hours = (current_time - start_time) / 3600
            
            if elapsed_hours >= duration_hours:
                log_to_file(log_file, "Experiment complete")
                break
            
            if current_time - last_control_time >= config.CONTROL_INTERVAL:
                log_to_file(log_file, f"Control at {elapsed_hours:.1f}hrs")
                
                do_readings = read_do()
                reactor_data = []
                
                for i in range(1, 4):
                    # 24hr reset check
                    if current_time - last_24hr_reset[i-1] >= config.DAILY_RESET_INTERVAL:
                        log_to_file(log_file, f"R{i} 24hr reset")
                        reset_servo(i)
                        nutrients_used_today[i-1] = 0.0
                        light_on_hours_today[i-1] = 0.0
                        last_24hr_reset[i-1] = current_time
                    
                    # Get state and action
                    state = get_state(i)
                    action, _ = model.predict(state, deterministic=True)
                    nutrient_action, light_action = action
                    
                    # Convert actions
                    nutrient_rate = (nutrient_action + 1) / 2 * config.MAX_NUTRIENT_RATE
                    led_intensity = int((light_action + 1) / 2 * config.MAX_LIGHT_INTENSITY)
                    
                    interval_hours = config.CONTROL_INTERVAL / 3600
                    nutrient_ml = nutrient_rate * interval_hours
                    
                    # Budget checks
                    if nutrients_used_today[i-1] >= config.DAILY_NUTRIENT_BUDGET:
                        nutrient_ml = 0
                    
                    max_light_hours = 24 - config.MIN_DARK_PERIOD
                    if light_on_hours_today[i-1] >= max_light_hours and led_intensity > 10:
                        led_intensity = 0
                    
                    # Execute
                    actual_dispensed = 0.0
                    if nutrient_ml > 0.1:
                        dispense(i, nutrient_ml)
                        actual_dispensed = nutrient_ml
                        nutrients_used_today[i-1] += actual_dispensed
                        total_nutrients_added[i-1] += actual_dispensed
                    
                    set_leds(reactor_leds[i-1], led_intensity)
                    
                    if led_intensity > 10:
                        light_on_hours_today[i-1] += interval_hours
                    
                    # Update state
                    update_state(i, do_readings[i-1], actual_dispensed, led_intensity)
                    
                    # Store data
                    reactor_data.append({
                        'do': do_readings[i-1] if do_readings[i-1] else 0,
                        'nutrient_est': state[0],
                        'do_trend': state[2],
                        'light_level': led_intensity,
                        'nutrient_added': actual_dispensed,
                        'nutrient_used_today': nutrients_used_today[i-1],
                        'total_nutrients_added': total_nutrients_added[i-1],
                        'light_hours_today': light_on_hours_today[i-1],
                        'action_nutrient': nutrient_action,
                        'action_light': light_action
                    })
                
                save_data(csv_file, elapsed_hours, reactor_data)
                last_control_time = current_time
            
            time.sleep(10)
    
    except KeyboardInterrupt:
        log_to_file(log_file, "Stopped by user")
    
    finally:
        log_to_file(log_file, "Shutting down")
        clear_all_leds()
        detach_all()
        cleanup_do()
        cleanup()
        log_to_file(log_file, "Shutdown complete")
        print(f"Log: {log_file}")
        print(f"Data: {csv_file}")


if __name__ == "__main__":
    import sys
    initialize_leds()
    model_path = sys.argv[1] if len(sys.argv) > 1 else "bioreactor_model.zip"
    run_bioreactor(model_path=model_path, duration_hours=120)