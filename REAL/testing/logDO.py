from gdx import gdx
from datetime import datetime
import csv
import time

# Interval in seconds (1 minute)
INTERVAL = 60  

# Initialize GDX
gdx_device = gdx.gdx()
gdx_device.open(connection='usb')

# Automatically select sensor 1 (DO Concentration)
# Pass a list with the sensor number
gdx_device.select_sensors([1])
gdx_device.start()

# Get column headers (sensor names)
column_headers = gdx_device.enabled_sensor_info()
print("Logging sensors:", column_headers)

# Open CSV file (append mode)
with open("do_log.csv", "a", newline="") as f:
    writer = csv.writer(f)
    # Write header if file is empty
    f.seek(0, 2)
    if f.tell() == 0:
        writer.writerow(["Timestamp"] + column_headers)

    try:
        while True:
            # Read sensor data
            measurements = gdx_device.read()
            if measurements is None:
                print("No data received. Skipping this interval.")
            else:
                timestamp = datetime.now().isoformat()
                writer.writerow([timestamp] + measurements)
                f.flush()
                print(timestamp, measurements)
            
            # Wait for next interval
            time.sleep(INTERVAL)

    except KeyboardInterrupt:
        print("Logging stopped by user")

# Stop and close device
gdx_device.stop()
gdx_device.close()
