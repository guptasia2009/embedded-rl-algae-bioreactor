"""
Hardware Test Script
Tests each component individually before running full system
"""

import RPi.GPIO as GPIO
import time
import sys

# GPIO Pin Assignments
SERVO_PIN = 17
LED_PIN = 23
HEATER_PIN = 24

def test_servo():
    """Test servo motor movement"""
    print("\n" + "="*60)
    print("TESTING SERVO MOTOR")
    print("="*60)
    
    GPIO.setup(SERVO_PIN, GPIO.OUT)
    pwm = GPIO.PWM(SERVO_PIN, 50)
    pwm.start(0)
    
    try:
        print("\nMoving servo through range...")
        print("Watch the servo - it should move smoothly")
        
        for duty in [2.5, 5.0, 7.5, 10.0, 12.5]:
            print(f"  Duty cycle: {duty}%")
            pwm.ChangeDutyCycle(duty)
            time.sleep(1.5)
        
        # Return to middle
        pwm.ChangeDutyCycle(7.5)
        print("  Returned to middle position")
        
        print("\n✓ Servo test complete")
        print("Did the servo move smoothly? (y/n): ", end='')
        response = input().strip().lower()
        
        if response != 'y':
            print("⚠ Check servo wiring and power supply")
            return False
        
        return True
        
    finally:
        pwm.stop()

def test_led():
    """Test LED control"""
    print("\n" + "="*60)
    print("TESTING LED CONTROL")
    print("="*60)
    
    GPIO.setup(LED_PIN, GPIO.OUT)
    
    try:
        print("\nLED will blink 3 times...")
        print("Watch your LED - it should turn on and off")
        
        for i in range(3):
            print(f"  Blink {i+1}/3")
            GPIO.output(LED_PIN, GPIO.HIGH)
            print("    ON")
            time.sleep(2)
            GPIO.output(LED_PIN, GPIO.LOW)
            print("    OFF")
            time.sleep(1)
        
        print("\n✓ LED test complete")
        print("Did the LED blink 3 times? (y/n): ", end='')
        response = input().strip().lower()
        
        if response != 'y':
            print("⚠ Check LED wiring and relay connection")
            return False
        
        return True
        
    finally:
        GPIO.output(LED_PIN, GPIO.LOW)

def test_heater():
    """Test heater control (with safety confirmation)"""
    print("\n" + "="*60)
    print("TESTING HEATER CONTROL")
    print("="*60)
    
    print("\n⚠ WARNING: This will activate the heater!")
    print("Make sure:")
    print("  - Heater is in water/culture")
    print("  - Temperature sensor is working")
    print("  - You're ready to monitor temperature")
    print("\nContinue with heater test? (yes/no): ", end='')
    response = input().strip().lower()
    
    if response != 'yes':
        print("Heater test skipped")
        return True
    
    GPIO.setup(HEATER_PIN, GPIO.OUT)
    
    try:
        print("\nHeater will turn ON for 10 seconds...")
        print("Monitor temperature carefully!")
        
        GPIO.output(HEATER_PIN, GPIO.HIGH)
        print("⚡ HEATER ON")
        
        for i in range(10, 0, -1):
            print(f"  {i} seconds remaining...")
            time.sleep(1)
        
        GPIO.output(HEATER_PIN, GPIO.LOW)
        print("✓ HEATER OFF")
        
        print("\nDid the heater turn on? (y/n): ", end='')
        response = input().strip().lower()
        
        if response != 'y':
            print("⚠ Check heater wiring and relay connection")
            return False
        
        return True
        
    finally:
        GPIO.output(HEATER_PIN, GPIO.LOW)

def test_temperature_sensor():
    """Test DS18B20 temperature sensor"""
    print("\n" + "="*60)
    print("TESTING TEMPERATURE SENSOR")
    print("="*60)
    
    try:
        import glob
        import os
        
        # Enable 1-wire
        os.system('modprobe w1-gpio 2>/dev/null')
        os.system('modprobe w1-therm 2>/dev/null')
        
        # Find sensor
        devices = glob.glob('/sys/bus/w1/devices/28-*')
        
        if not devices:
            print("\n✗ No DS18B20 sensor found")
            print("Check:")
            print("  - Sensor wiring (Red=3.3V, Black=GND, Yellow=GPIO4)")
            print("  - 4.7kΩ pullup resistor between data and 3.3V")
            print("  - 1-wire enabled in /boot/config.txt")
            return False
        
        sensor_path = devices[0] + '/w1_slave'
        print(f"\n✓ Sensor found: {devices[0]}")
        
        # Read temperature
        print("\nReading temperature (3 samples)...")
        for i in range(3):
            with open(sensor_path, 'r') as f:
                lines = f.readlines()
            
            if lines[0].strip()[-3:] != 'YES':
                print(f"  Sample {i+1}: CRC error")
                continue
            
            temp_pos = lines[1].find('t=')
            if temp_pos != -1:
                temp_c = float(lines[1][temp_pos+2:]) / 1000.0
                print(f"  Sample {i+1}: {temp_c:.2f}°C")
            
            time.sleep(1)
        
        print("\n✓ Temperature sensor working")
        return True
        
    except Exception as e:
        print(f"\n✗ Error testing temperature sensor: {e}")
        return False

def test_do_sensor():
    """Test Vernier DO sensor"""
    print("\n" + "="*60)
    print("TESTING DO SENSOR")
    print("="*60)
    
    try:
        from gdx import gdx
        
        print("\nInitializing DO sensor...")
        gdx_device = gdx()
        gdx_device.open(connection='usb')
        gdx_device.select_sensors([1])
        gdx_device.start()
        
        print("✓ DO sensor connected")
        print("\nReading DO (5 samples)...")
        
        for i in range(5):
            measurements = gdx_device.read()
            if measurements:
                print(f"  Sample {i+1}: {measurements[0]:.2f} mg/L")
            else:
                print(f"  Sample {i+1}: No data")
            time.sleep(1)
        
        gdx_device.stop()
        gdx_device.close()
        
        print("\n✓ DO sensor working")
        return True
        
    except ImportError:
        print("\n✗ gdx module not installed")
        print("Install with: pip3 install gdx")
        return False
    except Exception as e:
        print(f"\n✗ Error testing DO sensor: {e}")
        print("Check:")
        print("  - USB connection")
        print("  - Sensor is powered on")
        print("  - Run 'lsusb' to verify device detected")
        return False

def main():
    """Run all hardware tests"""
    print("="*60)
    print("BIOREACTOR HARDWARE TEST SUITE")
    print("="*60)
    print("\nThis will test each hardware component individually")
    print("Make sure all components are connected before starting")
    print("\nPress Enter to continue or Ctrl+C to cancel...")
    input()
    
    # Initialize GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    results = {}
    
    try:
        # Test each component
        results['servo'] = test_servo()
        #results['led'] = test_led()
        #results['heater'] = test_heater()
        #results['temp_sensor'] = test_temperature_sensor()
        #results['do_sensor'] = test_do_sensor()
        
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
    
    finally:
        GPIO.cleanup()
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for component, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{component:15s}: {status}")
    
    print("="*60)
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 All tests passed! Hardware is ready.")
        print("\nNext steps:")
        print("1. Run servo_calibration.py to calibrate syringe pump")
        print("2. Run bioreactor_control.py to start the system")
    else:
        print("\n⚠ Some tests failed. Fix issues before running main system.")
        print("\nRefer to SETUP_GUIDE.md for troubleshooting")
    
    print()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        GPIO.cleanup()
        sys.exit(1)