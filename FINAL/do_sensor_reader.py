"""
DO Sensor Reader
"""

from logger import log
import time
try:
    from gdx import gdx as gdx_module
    GDX_AVAILABLE = True
except ImportError:
    gdx_module = None
    GDX_AVAILABLE = False

# Global sensor object
gdx = None

# Initialize sensors
if GDX_AVAILABLE:
    try:
        gdx = gdx_module.gdx()
        gdx.open(connection='usb')
        gdx.select_sensors()
        gdx.start(period=1000)
        time.sleep(4)
        sensor_info = gdx.enabled_sensor_info()
        log(f"DO sensors initialized: {sensor_info}")
    except Exception as e:
        log(f"ERROR: DO sensors failed to initialize,{e}")
        gdx = None
else:
    log("WARNING: gdx module not found,running in simulation mode")

def read_do():
    """
    Read DO from all sensors
    
    Returns:
        list: DO readings in mg/L [R1, R2, R3]
              Returns None for failed readings
    """
    if gdx is None:
        # Simulation mode
        import numpy as np
        return [5.0 + np.random.randn() * 0.5 for _ in range(3)]
    
    try:
        measurements = gdx.read()
        
        if measurements is None:
            log("WARNING: No DO readings received")
            return [None, None, None]
        
        # Ensure we have 3 values
        if len(measurements) < 3:
            measurements = list(measurements) + [None] * (3 - len(measurements))
        
        return measurements[:3]
        
    except Exception as e:
        log(f"ERROR: DO read failed,{e}")
        return [None, None, None]
    
def cleanup_do():
    """Close DO sensors"""
    if gdx is not None:
        try:
            gdx.stop()
            gdx.close()
            log("DO sensors closed")
        except:
            pass