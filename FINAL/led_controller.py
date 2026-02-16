#!/usr/bin/env python3

"""
LED Controller Module
Controls individual LEDs and groups
"""

from rpi_ws281x import PixelStrip, Color
from datetime import datetime
from pathlib import Path

# Global LED strip object
_strip = None
_log_file = None

def _get_log_file():
    """
    Get or create log file
    """
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
    """
    Write message to log file
    """
    timestamp = datetime.now().isoformat()
    log_file = _get_log_file()
    
    with open(log_file, 'a') as f:
        f.write(f"{timestamp},{message}\n")

def initialize_leds(total_leds=60, gpio_pin=19, brightness=128):
    """
    Initialize the LED strip
    
    Args:
        total_leds: Total number of LEDs on the strip
        gpio_pin: GPIO pin number (default: 19)
        brightness: Global brightness 0-255 (default: 128)
    
    Returns:
        The LED strip object
    """
    global _strip
    _strip = PixelStrip(total_leds, gpio_pin, 800000, 10, False, brightness, 1)
    _strip.begin()
    clear_all_leds()
    _log(f"INFO,LED strip initialized,{total_leds} LEDs on GPIO {gpio_pin}")
    return _strip

def set_leds(led_list, intensity):
    """
    Set specific LEDs to a white intensity
    
    Args:
        led_list: List of LED indices to control, e.g., [57, 58, 59]
                  Can also be a single int, e.g., 57
        intensity: Brightness 0-255 (0=off, 255=full)
    
    Example:
        set_leds([57, 58, 59], 255)  # Turn on LEDs 57-59 at full brightness
        set_leds(57, 128)             # Turn on LED 57 at half brightness
        set_leds([54, 55, 56], 0)    # Turn off LEDs 54-56
    """
    global _strip
    if _strip is None:
        _log("ERROR,LED strip not initialized")
        raise RuntimeError("LED strip not initialized. Call initialize_leds() first.")
    
    # Handle single LED
    if isinstance(led_list, int):
        led_list = [led_list]
    
    # Clamp intensity
    intensity = max(0, min(255, int(intensity)))
    color = Color(intensity, intensity, intensity)  # White = RGB all equal (but GRB order)
    
    for led_num in led_list:
        if 0 <= led_num < _strip.numPixels():
            _strip.setPixelColor(led_num, color)
    
    _strip.show()
    _log(f"LED_SET,LEDs {led_list},intensity {intensity}")

def clear_all_leds():
    """Turn off all LEDs"""
    global _strip
    if _strip is None:
        return
    
    for i in range(_strip.numPixels()):
        _strip.setPixelColor(i, Color(0, 0, 0))
    _strip.show()
    _log("INFO,All LEDs cleared")

def clear_leds(led_list):
    """
    Turn off specific LEDs
    
    Args:
        led_list: List of LED indices to turn off
    """
    set_leds(led_list, 0)

def get_strip():
    """Get the global LED strip object"""
    return _strip