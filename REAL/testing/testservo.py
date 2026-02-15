# sudo pigpiod
import os
from gpiozero import Servo
from gpiozero.pins.pigpio import PiGPIOFactory
from time import sleep

# 1. Start the hardware daemon if it's not running
#os.system('sudo systemctl start pigpiod')

# 2. Use the hardware clock factory to stop the shaking
factory = PiGPIOFactory()
servo1 = Servo(18, pin_factory=factory)
servo2 = Servo(13, pin_factory=factory)
servo3 = Servo(12, pin_factory=factory)

def slow_sweep(start=-1.0, end=-1.0, step=0.2, delay=1):
    """Moves the servo slowly from start to end position."""
    curr = start
    print(f"Sweeping from {start} to {end}...")
    
    while curr <= end:
        servo1.value = curr
        servo2.value = curr
        servo3.value = curr
        curr += step
        sleep(delay)
    
    # Relax the motor so it doesn't buzz at the finish line
    servo1.detach()
    servo2.detach()
    servo3.detach()

try:
    # Run the sweep
    slow_sweep()
    print("Sweep complete!")

except KeyboardInterrupt:
    print("\nStopping...")
finally:
    servo1.close()
    servo2.close()
    servo3.close()