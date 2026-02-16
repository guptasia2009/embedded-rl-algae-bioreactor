"""
Servo Controller Module
Controls syring pumps using servos in the range of 3-7mL
"""

# Run the following line at start of session
# sudo pigpiod

import os
from gpiozero import Servo
from gpiozero.pins.pigpio import PiGPIOFactory
from time import sleep
from datetime import datetime
from pathlib import Path
from config import *

# Start pigpiod if command hasn't run
os.system('sudo systemctl start pigpiod 2>/dev/null')
sleep(1)

# Initialize servos
factory = PiGPIOFactory()
servo1 = Servo(SERVO_PINS[0], pin_factory=factory)
servo2 = Servo(SERVO_PINS[1], pin_factory=factory)
servo3 = Servo(SERVO_PINS[2], pin_factory=factory)

# Set all to starting position (7mL = -1.0)
servo1.value = -1.0
servo2.value = -1.0
servo3.value = -1.0
sleep(1)

# Setup logging
_log_file = None

def _get_log_file():
    # Gets or creates a log file
    global _log_file

    if _log_file is not None:
        return _log_file
    
    # Check if main has already created a log file
    existing_logs = sorted(Path('.').glob('bioreactor_log_*.csv'))
    
    if existing_logs:
        # Use the most recent log file
        _log_file = str(existing_logs[-1])
    else:
        # Create new log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        _log_file = f"bioreactor_log_{timestamp}.csv"
    
    return _log_file

def _log(message):
    # Write message to log file
    timestamp = datetime.now().isoformat()
    log_file = _get_log_file()
    
    with open(log_file, 'a') as f:
        f.write(f"{timestamp},{message}\n")

_log("INFO,Servos initialized")

def dispense(servo_num, ml_amount):
    """
    Dispense liquid from a servo
    
    Args:
        servo_num: 1, 2, or 3
        ml_amount: How much to dispense in mL
    """
    # Pick the servo
    if servo_num == 1:
        servo = servo1
    elif servo_num == 2:
        servo = servo2
    elif servo_num == 3:
        servo = servo3
    else:
        _log(f"ERROR,Invalid servo number {servo_num}")
        return
    
    # Get current position
    current_value = servo.value if servo.value is not None else -1.0
    
    # Convert position to mL: -1.0 = 7mL, +1.0 = 3mL
    # Formula: ml = 3 + (1 - position) * 2
    current_ml = 3.0 + (1.0 - current_value) * 2.0
    
    # Calculate new position
    new_ml = max(3.0, current_ml - ml_amount)
    
    # Convert mL back to position: position = 1 - 2*(ml-3)/4
    new_position = 1.0 - 2.0 * (new_ml - 3.0) / 4.0
    
    # Move servo
    servo.value = new_position
    sleep(0.5)
    
    actual_dispensed = current_ml - new_ml
    _log(f"DISPENSE,Servo {servo_num},{actual_dispensed:.2f}mL")

def reset_servo(servo_num):
    # Reset a servo to 7mL (-1.0 position)
    if servo_num == 1:
        servo1.value = -1.0
    elif servo_num == 2:
        servo2.value = -1.0
    elif servo_num == 3:
        servo3.value = -1.0
    
    sleep(0.5)
    _log(f"RESET,Servo {servo_num},7mL")

def reset_all():
    # Reset all servos to 7mL
    servo1.value = -1.0
    servo2.value = -1.0
    servo3.value = -1.0
    sleep(1)
    _log("RESET,All servos,7mL")


def detach_all():
    # Stop servo buzzing
    servo1.detach()
    servo2.detach()
    servo3.detach()
    _log("INFO,Servos detached")


def cleanup():
    # Close servos
    servo1.close()
    servo2.close()
    servo3.close()
    _log("INFO,Servos closed")