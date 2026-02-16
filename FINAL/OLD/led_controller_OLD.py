"""
LED Controller Module
Simple function-based control for individual LEDs or groups
"""

from rpi_ws281x import PixelStrip, Color

# Global LED strip object (initialized once)
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
    print(f"✓ LED strip initialized: {total_leds} LEDs on GPIO {gpio_pin}")
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

def set_reactor_leds(reactor_num, led_indices, intensity):
    """
    Set LEDs for a specific reactor
    
    Args:
        reactor_num: Reactor number (1, 2, or 3) - just for logging
        led_indices: List of LED indices for this reactor
        intensity: Brightness 0-255
    
    Example:
        set_reactor_leds(1, [57, 58, 59], 255)
        set_reactor_leds(2, [51, 52, 53], 128)
    """
    set_leds(led_indices, intensity)

def clear_all_leds():
    """Turn off all LEDs"""
    global _strip
    if _strip is None:
        return
    
    for i in range(_strip.numPixels()):
        _strip.setPixelColor(i, Color(0, 0, 0))
    _strip.show()

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


# Example usage
if __name__ == "__main__":
    import time
    
    print("LED Controller Test")
    print("=" * 60)
    
    # Initialize
    initialize_leds(total_leds=60, gpio_pin=19)
    
    # Define reactor LED positions
    # With 3 LEDs on, 3 LEDs gap between reactors
    REACTOR_1_LEDS = [55, 56, 57]  # Last 3 LEDs
    REACTOR_2_LEDS = [50, 51, 52]  # 3 LEDs gap, then these 3
    REACTOR_3_LEDS = [44, 45, 46]  # 3 LEDs gap, then these 3
    REACTOR_4_LEDS = [37, 38, 39]
    REACTOR_5_LEDS = [31, 32, 33]
    REACTOR_6_LEDS = [25, 26, 27]

    print("\nReactor LED Configuration:")
    print(f"  Reactor 1: LEDs {REACTOR_1_LEDS}")
    print(f"  Reactor 2: LEDs {REACTOR_2_LEDS}")
    print(f"  Reactor 3: LEDs {REACTOR_3_LEDS}")
    
    print("\nRunning tests...\n")
    
    try:
        '''
        # Test 1: Turn on each reactor individually
        print("Test 1: Individual reactors at different intensities")
        set_reactor_leds(1, REACTOR_1_LEDS, 255)
        print("  Reactor 1: Full brightness")
        time.sleep(1)
        
        set_reactor_leds(2, REACTOR_2_LEDS, 128)
        print("  Reactor 2: Half brightness")
        time.sleep(1)
        
        set_reactor_leds(3, REACTOR_3_LEDS, 64)
        print("  Reactor 3: Quarter brightness")
        time.sleep(2)
        '''
        # Test 2: All at once
        print("\nTest 2: All reactors at full brightness")
        set_leds(REACTOR_1_LEDS, 255)
        set_leds(REACTOR_2_LEDS, 255)
        set_leds(REACTOR_3_LEDS, 255)
        set_leds(REACTOR_4_LEDS, 255)
        set_leds(REACTOR_5_LEDS, 255)
        set_leds(REACTOR_6_LEDS, 255)
        time.sleep(10)
        '''
        # Test 3: Ramp up
        print("\nTest 3: Ramping up all reactors")
        for intensity in range(0, 256, 32):
            set_leds(REACTOR_1_LEDS + REACTOR_2_LEDS + REACTOR_3_LEDS, intensity)
            time.sleep(0.3)
        time.sleep(1)
        
        # Test 4: Individual control
        print("\nTest 4: Independent control")
        for i in range(5):
            set_leds(REACTOR_1_LEDS, 255 if i % 2 == 0 else 0)
            set_leds(REACTOR_2_LEDS, 128)
            set_leds(REACTOR_3_LEDS, 255 if i % 2 == 1 else 0)
            time.sleep(0.5)
        '''
        print("\nTests complete!")
        
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    
    finally:
        print("Clearing all LEDs...")
        clear_all_leds()
        print("Done!")