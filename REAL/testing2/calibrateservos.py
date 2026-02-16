"""
Triple Servo Test Script
Tests all 3 servos individually and together
Based on your gpiozero code
"""

import os
from gpiozero import Servo
from gpiozero.pins.pigpio import PiGPIOFactory
from time import sleep
import sys

# GPIO pins for servos
SERVO_PINS = [18, 13, 12]

def test_single_servo(pin, servo_id):
    """Test a single servo"""
    print(f"\n{'='*60}")
    print(f"Testing Servo {servo_id} on GPIO {pin}")
    print(f"{'='*60}")
    
    factory = PiGPIOFactory()
    servo = Servo(pin, pin_factory=factory)
    
    try:
        print("\nMoving through positions:")
        positions = [-1.0, -0.5, 0.0, 0.5, 1.0, 0.0]
        position_names = ["Full Left", "Mid-Left", "Center", "Mid-Right", "Full Right", "Center"]
        
        for pos, name in zip(positions, position_names):
            print(f"  → {name:12s} (value: {pos:+.1f})")
            servo.value = pos
            sleep(1.5)
        
        # Detach to prevent buzzing
        servo.detach()
        print("  → Detached (no buzz)")
        
        print(f"\n✓ Servo {servo_id} test complete")
        print("Did the servo move smoothly? (y/n): ", end='')
        response = input().strip().lower()
        
        return response == 'y'
        
    finally:
        servo.close()

def test_all_servos_sync():
    """Test all 3 servos moving in sync"""
    print(f"\n{'='*60}")
    print("Testing All 3 Servos in Sync")
    print(f"{'='*60}")
    
    factory = PiGPIOFactory()
    servos = [Servo(pin, pin_factory=factory) for pin in SERVO_PINS]
    
    try:
        print("\nSynchronized sweep test:")
        print("All servos should move together...")
        
        def slow_sweep(start=-1.0, end=1.0, step=0.2, delay=1):
            """Moves all servos slowly from start to end position"""
            curr = start
            print(f"  Sweeping from {start} to {end}...")
            
            while curr <= end:
                for i, servo in enumerate(servos):
                    servo.value = curr
                print(f"    Position: {curr:+.1f}")
                curr += step
                sleep(delay)
            
            # Detach all
            for servo in servos:
                servo.detach()
            print("  All servos detached")
        
        slow_sweep()
        print("\n✓ Synchronized sweep complete")
        
        print("Did all servos move together smoothly? (y/n): ", end='')
        response = input().strip().lower()
        
        return response == 'y'
        
    finally:
        for servo in servos:
            servo.close()

def calibrate_servo(pin, servo_id):
    """Interactive calibration for a single servo"""
    print(f"\n{'='*60}")
    print(f"Calibrating Servo {servo_id} on GPIO {pin}")
    print(f"{'='*60}")
    print("\n⚠️  IMPORTANT: This syringe has LIMITED RANGE")
    print("Your servo can only move the plunger between 3mL and 7mL marks")
    print("We need to find which servo values correspond to these positions.")
    print()
    print("Commands:")
    print("  - Enter a number from -1.0 to 1.0 to move servo")
    print("  - '7' to mark when plunger is at 7mL mark (MAX usable)")
    print("  - '3' to mark when plunger is at 3mL mark (MIN usable)")
    print("  - 'q' to quit")
    print()
    
    factory = PiGPIOFactory()
    servo = Servo(pin, pin_factory=factory)
    
    ml_7_value = None  # Servo value when at 7mL mark
    ml_3_value = None  # Servo value when at 3mL mark
    current_value = -1.0  # Start at -1 instead of 0
    
    servo.value = current_value
    sleep(1)
    print(f"Starting at position: {current_value}")
    print("Watch the syringe plunger position on the mL markings!")
    sleep(0.5)
    
    try:
        while True:
            cmd = input(f"\nCommand (current servo: {current_value:+.2f}): ").strip().lower()
            
            if cmd == 'q':
                break
            elif cmd == '7':
                ml_7_value = current_value
                print(f"✓ 7mL mark position saved: servo = {ml_7_value:+.2f}")
            elif cmd == '3':
                ml_3_value = current_value
                print(f"✓ 3mL mark position saved: servo = {ml_3_value:+.2f}")
            else:
                try:
                    value = float(cmd)
                    if value < -1.0 or value > 1.0:
                        print("ERROR: Value must be between -1.0 and 1.0")
                        continue
                    
                    servo.value = value
                    current_value = value
                    print(f"  → Moved to {value:+.2f}")
                    print(f"  → Look at syringe: What mL mark is the plunger at?")
                    sleep(0.5)
                    
                except ValueError:
                    print("ERROR: Invalid command")
        
        servo.detach()
        
        if ml_7_value is not None and ml_3_value is not None:
            print(f"\nCalibration results for Servo {servo_id}:")
            print(f"  7mL mark (MAX): {ml_7_value:+.2f}")
            print(f"  3mL mark (MIN): {ml_3_value:+.2f}")
            print(f"  Usable range: 4mL")
            
            with open(f'servo{servo_id}_calibration.txt', 'w') as f:
                f.write(f"Servo {servo_id} (GPIO {pin}):\n")
                f.write(f"7mL_POSITION = {ml_7_value}\n")
                f.write(f"3mL_POSITION = {ml_3_value}\n")
                f.write(f"USABLE_VOLUME = 4.0mL\n")
                f.write(f"\nThe code already handles this range!\n")
                f.write(f"It maps servo {ml_7_value} to {ml_3_value} → 7mL to 3mL\n")
            
            print(f"\n✓ Saved to servo{servo_id}_calibration.txt")
            print(f"\nGood news: The code already expects servo to control 3-7mL range!")
            print(f"It will automatically map:")
            print(f"  Servo -1.0 → 7mL (most liquid available)")
            print(f"  Servo +1.0 → 3mL (least liquid, most dispensed)")
        else:
            print("\n⚠️  Incomplete calibration - mark both 3mL and 7mL positions")
        
    finally:
        servo.close()

def main():
    """Main test menu"""
    # Start pigpio daemon
    print("Starting pigpio daemon...")
    os.system('sudo systemctl start pigpiod 2>/dev/null')
    sleep(1)
    
    print("="*60)
    print("TRIPLE SERVO TEST SUITE")
    print("="*60)
    print("\nThis will test your 3 servo motors")
    print(f"GPIO Pins: {SERVO_PINS}")
    print("\nMenu:")
    print("  1. Test each servo individually")
    print("  2. Test all servos in sync")
    print("  3. Calibrate servo 1")
    print("  4. Calibrate servo 2")
    print("  5. Calibrate servo 3")
    print("  6. Run all tests")
    print("  q. Quit")
    print("="*60)
    
    while True:
        choice = input("\nSelect option: ").strip().lower()
        
        if choice == 'q':
            break
        elif choice == '1':
            for i, pin in enumerate(SERVO_PINS):
                test_single_servo(pin, i+1)
        elif choice == '2':
            test_all_servos_sync()
        elif choice == '3':
            calibrate_servo(SERVO_PINS[0], 1)
        elif choice == '4':
            calibrate_servo(SERVO_PINS[1], 2)
        elif choice == '5':
            calibrate_servo(SERVO_PINS[2], 3)
        elif choice == '6':
            print("\nRunning all tests...")
            results = []
            for i, pin in enumerate(SERVO_PINS):
                results.append(test_single_servo(pin, i+1))
            results.append(test_all_servos_sync())
            
            print(f"\n{'='*60}")
            print("TEST SUMMARY")
            print(f"{'='*60}")
            for i, result in enumerate(results[:-1]):
                status = "✓ PASS" if result else "✗ FAIL"
                print(f"Servo {i+1}:        {status}")
            status = "✓ PASS" if results[-1] else "✗ FAIL"
            print(f"Sync test:     {status}")
            
            if all(results):
                print("\n🎉 All servos working correctly!")
            else:
                print("\n⚠ Some servos need attention")
        else:
            print("Invalid option")
    
    print("\nExiting...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)