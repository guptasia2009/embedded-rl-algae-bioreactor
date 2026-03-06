# Note: must run command as sudo
from rpi_ws281x import PixelStrip, Color
from logger import log

# Global LED strip object
_strip = None

def initialize_leds(total_leds=60, gpio_pin=19, brightness=128):
    global _strip
    _strip = PixelStrip(total_leds, gpio_pin, 800000, 10, False, brightness, 1)
    _strip.begin()
    clear_all_leds()
    log(f"LED strip initialized: {total_leds} LEDs on GPIO {gpio_pin}")
    return _strip

def set_leds(led_list, intensity):
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
    global _strip
    if _strip is None:
        return
    
    for i in range(_strip.numPixels()):
        _strip.setPixelColor(i, Color(0, 0, 0))
    _strip.show()
    log("All LEDs cleared")

def clear_leds(led_list):
    set_leds(led_list, 0)

def get_strip():
    return _strip