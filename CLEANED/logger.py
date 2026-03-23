# LOGGER
from datetime import datetime
from pathlib import Path

_log_file = None
_source = ""

def set_source(source):
    global _source
    _source = source

def get_log_file():
    global _log_file
    
    if _log_file is not None:
        return _log_file
    
    # Check if main has already created a log file
    existing_logs = sorted(Path('.').glob('bioreactor_log*.txt'))
    
    if existing_logs:
        # Use the most recent log file
        _log_file = str(existing_logs[-1])
    else:
        # Create new log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        _log_file = f"bioreactor_log{timestamp}.txt"
    
    return _log_file

def log(message):
    timestamp = datetime.now().isoformat()
    log_file = get_log_file()
    
    with open(log_file, 'a') as f:
        f.write(f"{timestamp} - {message}\n")