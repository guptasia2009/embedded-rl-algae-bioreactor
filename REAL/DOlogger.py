"""
Triple DO Logger - Logs 3 DO sensors simultaneously
Logs dissolved oxygen from 3 Vernier GO Direct sensors every 60 seconds
"""

from datetime import datetime
import csv
import time
import sys

try:
    from gdx import gdx
    GDX_AVAILABLE = True
except ImportError:
    print("ERROR: gdx module not found")
    print("Install with: pip3 install gdx")
    sys.exit(1)

# Configuration
INTERVAL = 60  # seconds between readings
NUM_SENSORS = 3

def initialize_sensors(num_sensors=3):
    """Initialize multiple DO sensors"""
    devices = []
    sensor_names = []
    
    print(f"\nInitializing {num_sensors} DO sensors...")
    
    for i in range(num_sensors):
        try:
            print(f"  Connecting to sensor {i+1}...")
            device = gdx()
            device.open(connection='usb', device_to_open=i+1)
            device.select_sensors([1])  # Sensor 1 = DO Concentration
            device.start()
            
            headers = device.enabled_sensor_info()
            devices.append(device)
            sensor_names.append(f"Sensor_{i+1}_DO")
            
            print(f"  ✓ Sensor {i+1} initialized: {headers}")
            
        except Exception as e:
            print(f"  ⚠ Could not initialize sensor {i+1}: {e}")
            print(f"    Continuing with {len(devices)} sensor(s)...")
    
    if not devices:
        print("\nERROR: No sensors initialized!")
        print("\nTroubleshooting:")
        print("1. Check all USB connections")
        print("2. Ensure all sensors are powered on")
        print("3. Try unplugging and replugging USB cables")
        print("4. Run 'lsusb' to verify devices are detected")
        print("5. Try connecting sensors one at a time")
        sys.exit(1)
    
    print(f"\n✓ {len(devices)} sensor(s) initialized successfully")
    return devices, sensor_names

def create_log_file(sensor_names):
    """Create CSV log file with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"triple_do_log_{timestamp}.csv"
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        headers = ["timestamp", "elapsed_seconds"] + sensor_names
        writer.writerow(headers)
    
    print(f"✓ Logging to: {filename}")
    return filename

def read_all_sensors(devices):
    """Read from all sensors"""
    readings = []
    
    for i, device in enumerate(devices):
        try:
            measurements = device.read()
            if measurements and len(measurements) > 0:
                readings.append(measurements[0])
            else:
                readings.append(None)
        except Exception as e:
            print(f"  Error reading sensor {i+1}: {e}")
            readings.append(None)
    
    return readings

def log_reading(filename, readings, elapsed_seconds):
    """Append readings to log file"""
    timestamp = datetime.now().isoformat()
    
    with open(filename, 'a', newline='') as f:
        writer = csv.writer(f)
        row = [timestamp, elapsed_seconds] + readings
        writer.writerow(row)

def main():
    """Main logging loop"""
    print("="*70)
    print("TRIPLE DO LOGGING SYSTEM")
    print("="*70)
    print(f"Logging interval: {INTERVAL} seconds")
    print("Press Ctrl+C to stop")
    print("="*70)
    
    # Initialize sensors
    devices, sensor_names = initialize_sensors(NUM_SENSORS)
    num_active = len(devices)
    
    # Create log file
    log_file = create_log_file(sensor_names)
    
    # Print header
    print(f"\n{'Time':<20} ", end='')
    for i in range(num_active):
        print(f"{'R' + str(i+1) + ' DO (mg/L)':<15} ", end='')
    print(f"{'Elapsed':<12}")
    print("-" * (20 + 15 * num_active + 12))
    
    # Start logging
    start_time = time.time()
    reading_count = 0
    
    try:
        while True:
            # Read all sensors
            readings = read_all_sensors(devices)
            elapsed = time.time() - start_time
            
            # Log to file
            log_reading(log_file, readings, elapsed)
            
            # Print to console
            reading_count += 1
            time_str = datetime.now().strftime('%H:%M:%S')
            print(f"{time_str:<20} ", end='')
            
            for reading in readings:
                if reading is not None:
                    print(f"{reading:>11.2f}    ", end='')
                else:
                    print(f"{'N/A':>11}    ", end='')
            
            print(f"{elapsed:>8.0f}s")
            
            # Periodic summary
            if reading_count % 10 == 0:
                print(f"\n{reading_count} readings logged")
                print(f"{'Time':<20} ", end='')
                for i in range(num_active):
                    print(f"{'R' + str(i+1) + ' DO (mg/L)':<15} ", end='')
                print(f"{'Elapsed':<12}")
                print("-" * (20 + 15 * num_active + 12))
            
            # Wait for next interval
            time.sleep(INTERVAL)
    
    except KeyboardInterrupt:
        print("\n\nLogging stopped by user")
    
    except Exception as e:
        print(f"\n\nERROR: {e}")
    
    finally:
        # Cleanup
        print("\nShutting down sensors...")
        for i, device in enumerate(devices):
            try:
                device.stop()
                device.close()
                print(f"  ✓ Sensor {i+1} closed")
            except:
                pass
        
        print(f"\n✓ Logged {reading_count} readings")
        print(f"✓ Data saved to: {log_file}")
        
        print("\nYou can analyze the data with:")
        print(f"  import pandas as pd")
        print(f"  data = pd.read_csv('{log_file}')")
        print(f"  data.plot(x='elapsed_seconds', y=['Sensor_1_DO', 'Sensor_2_DO', 'Sensor_3_DO'])")

if __name__ == "__main__":
    main()