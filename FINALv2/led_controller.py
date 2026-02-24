#!/usr/bin/env python3

"""
LED Controller Module
Controls individual LEDs and groups
"""

from rpi_ws281x import PixelStrip, Color
from logger import log

# Global LED strip object
_strip = None

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
    log(f"LED strip initialized: {total_leds} LEDs on GPIO {gpio_pin}")
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
        log("ERROR: LED strip not initialized")
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
    log(f"LEDs {led_list} set to intensity {intensity}")

def clear_all_leds():
    """Turn off all LEDs"""
    global _strip
    if _strip is None:
        return
    
    for i in range(_strip.numPixels()):
        _strip.setPixelColor(i, Color(0, 0, 0))
    _strip.show()
    log("All LEDs cleared")

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