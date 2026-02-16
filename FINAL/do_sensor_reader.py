"""
DO Sensor Reader
"""

from datetime import datetime
from pathlib import Path

try:
    from gdx import gdx as gdx_module
    GDX_AVAILABLE = True
except ImportError:
    GDX_AVAILABLE = False

# Global sensor object
gdx = None
_log_file = None

def _get_log_file():
    """Get or create log file"""
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
    """Write message to log file"""
    timestamp = datetime.now().isoformat()
    log_file = _get_log_file()
    
    with open(log_file, 'a') as f:
        f.write(f"{timestamp},{message}\n")

# Initialize sensors
if GDX_AVAILABLE:
    try:
        gdx = gdx_module()
        gdx.open(connection='usb')
        gdx.select_sensors()
        gdx.start()
        sensor_info = gdx.enabled_sensor_info()
        _log(f"INFO,DO sensors initialized,{sensor_info}")
    except Exception as e:
        _log(f"ERROR,DO sensors failed to initialize,{e}")
        gdx = None
else:
    _log("WARNING,gdx module not found,running in simulation mode")

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
            _log("WARNING,No DO readings received")
            return [None, None, None]
        
        # Ensure we have 3 values
        if len(measurements) < 3:
            measurements = list(measurements) + [None] * (3 - len(measurements))
        
        return measurements[:3]
        
    except Exception as e:
        _log(f"ERROR,DO read failed,{e}")
        return [None, None, None]
    
def cleanup_do():
    """Close DO sensors"""
    if gdx is not None:
        try:
            gdx.stop()
            gdx.close()
            _log("INFO,DO sensors closed")
        except:
            pass