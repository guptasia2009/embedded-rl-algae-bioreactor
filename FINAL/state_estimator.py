"""
DO Sensor Reader Module
Reads from 3 Vernier GO Direct DO sensors
"""

import config

try:
    from gdx import gdx
    GDX_AVAILABLE = True
except ImportError:
    print("WARNING: gdx module not found - running in simulation mode")
    GDX_AVAILABLE = False


class DOSensorReader:
    """Reads dissolved oxygen from 3 sensors"""
    
    def __init__(self):
        """Initialize DO sensors"""
        self.num_sensors = config.NUM_REACTORS
        self.devices = []
        self.simulated = not GDX_AVAILABLE
        
        if self.simulated:
            print("⚠ Running in SIMULATION mode - no real DO sensors")
            return
        
        print("\nInitializing DO sensors...")
        
        try:
            # Open connection
            self.gdx_device = gdx()
            self.gdx_device.open(connection='usb')
            
            # Select all sensors
            self.gdx_device.select_sensors()
            self.gdx_device.start()
            
            # Get sensor info
            sensor_info = self.gdx_device.enabled_sensor_info()
            print(f"✓ DO sensors initialized: {sensor_info}")
            
        except Exception as e:
            print(f"⚠ Error initializing DO sensors: {e}")
            print("  Running in simulation mode")
            self.simulated = True
    
    def read_all(self):
        """
        Read DO from all sensors
        
        Returns:
            list: DO readings in mg/L for each reactor [R1, R2, R3]
                  Returns None for any failed readings
        """
        if self.simulated:
            # Return simulated values
            import numpy as np
            return [5.0 + np.random.randn() * 0.5 for _ in range(self.num_sensors)]
        
        try:
            measurements = self.gdx_device.read()
            
            if measurements is None or len(measurements) == 0:
                return [None] * self.num_sensors
            
            # Ensure we have 3 readings
            if len(measurements) < self.num_sensors:
                # Pad with None if missing sensors
                measurements = list(measurements) + [None] * (self.num_sensors - len(measurements))
            
            return measurements[:self.num_sensors]
            
        except Exception as e:
            print(f"⚠ Error reading DO sensors: {e}")
            return [None] * self.num_sensors
    
    def cleanup(self):
        """Clean up sensor resources"""
        if not self.simulated:
            try:
                self.gdx_device.stop()
                self.gdx_device.close()
                print("✓ DO sensors closed")
            except:
                pass


# Test code
if __name__ == "__main__":
    import time
    
    print("="*70)
    print("DO SENSOR READER TEST")
    print("="*70)
    
    try:
        # Initialize sensor
        sensor = DOSensorReader()
        
        # Read 5 times
        print("\nReading DO sensors (5 samples)...\n")
        for i in range(5):
            readings = sensor.read_all()
            print(f"Sample {i+1}:")
            for j, reading in enumerate(readings):
                if reading is not None:
                    print(f"  Reactor {j+1}: {reading:.2f} mg/L")
                else:
                    print(f"  Reactor {j+1}: No reading")
            time.sleep(2)
        
        print("\nTest complete!")
        
    except KeyboardInterrupt:
        print("\nInterrupted")
    finally:
        sensor.cleanup()