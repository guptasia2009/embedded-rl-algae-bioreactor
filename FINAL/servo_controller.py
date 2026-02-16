"""
Servo Controller Module
Controls syringe pumps via servos with limited range (3-7mL)
sudo pigpiod
"""

import time
import numpy as np
from gpiozero import Servo
from gpiozero.pins.pigpio import PiGPIOFactory
import config

class ServoSyringeController:
    """Controls a single servo-driven syringe pump"""
    
    def __init__(self, pin, reactor_id):
        """
        Initialize servo controller
        
        Args:
            pin: GPIO pin number
            reactor_id: Reactor identifier (1, 2, or 3)
        """
        self.pin = pin
        self.reactor_id = reactor_id
        self.min_ml = config.SYRINGE_MIN_ML
        self.max_ml = config.SYRINGE_MAX_ML
        self.usable_volume = config.SYRINGE_USABLE_VOLUME
        self.current_position = self.max_ml  # Start at 7mL
        
        # Initialize servo with hardware PWM
        factory = PiGPIOFactory()
        self.servo = Servo(pin, pin_factory=factory)
        
        # Move to starting position
        self.reset_to_full()
        
    def reset_to_full(self):
        """Reset servo to 7mL position (ready for refill)"""
        self.set_position(self.max_ml)
        time.sleep(1)
        if config.VERBOSE:
            print(f"  Reactor {self.reactor_id}: Servo reset to {self.max_ml}mL position")
    
    def set_position(self, ml_position):
        """
        Move servo to specified mL position on syringe
        
        Args:
            ml_position: Target position in mL (3.0 to 7.0)
        """
        ml_position = np.clip(ml_position, self.min_ml, self.max_ml)
        
        # Convert mL to servo value (-1 to +1)
        # 7mL → -1.0 (full)
        # 3mL → +1.0 (empty)
        position_fraction = (ml_position - self.min_ml) / (self.max_ml - self.min_ml)
        servo_value = 1 - 2 * position_fraction
        
        self.servo.value = servo_value
        self.current_position = ml_position
        time.sleep(0.5)
    
    def dispense(self, ml_amount):
        """
        Dispense specified amount of liquid
        
        Args:
            ml_amount: Amount to dispense in mL
            
        Returns:
            actual_dispensed: Amount actually dispensed (may be less if limited)
        """
        ml_amount = abs(ml_amount)
        new_position = max(self.min_ml, self.current_position - ml_amount)
        actual_dispensed = self.current_position - new_position
        
        if actual_dispensed > 0:
            self.set_position(new_position)
        
        return actual_dispensed
    
    def get_remaining_volume(self):
        """Get how much liquid can still be dispensed"""
        return self.current_position - self.min_ml
    
    def detach(self):
        """Detach servo to prevent buzzing"""
        self.servo.detach()
    
    def cleanup(self):
        """Clean up servo resources"""
        self.servo.close()


class TripleServoController:
    """Controls all 3 servo syringe pumps"""
    
    def __init__(self):
        """Initialize all 3 servos"""
        print("\nInitializing servo controllers...")
        self.servos = []
        
        for i, pin in enumerate(config.SERVO_PINS):
            servo = ServoSyringeController(pin, reactor_id=i+1)
            self.servos.append(servo)
            print(f"✓ Reactor {i+1} servo on GPIO {pin}")
        
        print(f"  Usable volume per syringe: {config.SYRINGE_USABLE_VOLUME}mL")
    
    def dispense(self, reactor_id, ml_amount):
        """
        Dispense from specific reactor
        
        Args:
            reactor_id: 1, 2, or 3
            ml_amount: Amount to dispense in mL
            
        Returns:
            actual_dispensed: Amount actually dispensed
        """
        if 1 <= reactor_id <= config.NUM_REACTORS:
            return self.servos[reactor_id - 1].dispense(ml_amount)
        return 0.0
    
    def reset_servo(self, reactor_id):
        """Reset specific reactor's servo to full position"""
        if 1 <= reactor_id <= config.NUM_REACTORS:
            self.servos[reactor_id - 1].reset_to_full()
    
    def reset_all_servos(self):
        """Reset all servos to full position"""
        print("\nResetting all servos to full position...")
        for servo in self.servos:
            servo.reset_to_full()
    
    def get_remaining_volume(self, reactor_id):
        """Get remaining volume for specific reactor"""
        if 1 <= reactor_id <= config.NUM_REACTORS:
            return self.servos[reactor_id - 1].get_remaining_volume()
        return 0.0
    
    def get_all_remaining_volumes(self):
        """Get remaining volumes for all reactors"""
        return [servo.get_remaining_volume() for servo in self.servos]
    
    def detach_all(self):
        """Detach all servos to prevent buzzing"""
        for servo in self.servos:
            servo.detach()
    
    def cleanup(self):
        """Clean up all servo resources"""
        for servo in self.servos:
            servo.cleanup()


# Test code
if __name__ == "__main__":
    import os
    
    print("="*70)
    print("SERVO CONTROLLER TEST")
    print("="*70)
    
    # Start pigpiod
    os.system('sudo systemctl start pigpiod 2>/dev/null')
    time.sleep(1)
    
    try:
        # Initialize controllers
        controller = TripleServoController()
        
        # Test dispensing
        print("\nTest: Dispensing 0.5mL from each reactor")
        for i in range(1, 4):
            dispensed = controller.dispense(i, 2)
            remaining = controller.get_remaining_volume(i)
            print(f"  Reactor {i}: Dispensed {dispensed:.2f}mL, {remaining:.2f}mL remaining")
        
        time.sleep(2)
        
        # Test reset
        print("\nTest: Resetting all servos")
        controller.reset_all_servos()
        
        print("\nTest complete!")
        
    except KeyboardInterrupt:
        print("\nInterrupted")
    finally:
        controller.cleanup()
        print("Cleanup complete")