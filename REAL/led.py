#!/usr/bin/env python3
"""
LED Segment Controller Module
Easy-to-use module for controlling three independent LED segments
Perfect for research projects with multiple independent systems
"""

from rpi_ws281x import PixelStrip, Color

class LEDSegmentController:
    """Controller for three independent LED segments on a single strip"""
    
    def __init__(self, total_leds=60, gpio_pin=19, brightness=128, 
                 segment_1_leds=20, segment_2_leds=20, segment_3_leds=20):
        """
        Initialize the LED controller
        
        Args:
            total_leds: Total number of LEDs on the strip
            gpio_pin: GPIO pin number (default: 19)
            brightness: LED brightness 0-255 (default: 128)
            segment_1_leds: Number of LEDs in segment 1
            segment_2_leds: Number of LEDs in segment 2
            segment_3_leds: Number of LEDs in segment 3
        """
        self.total_leds = total_leds
        self.brightness = brightness
        
        # Calculate segment boundaries
        self.segment_1_start = 0
        self.segment_1_end = segment_1_leds
        
        self.segment_2_start = segment_1_leds
        self.segment_2_end = segment_1_leds + segment_2_leds
        
        self.segment_3_start = segment_1_leds + segment_2_leds
        self.segment_3_end = segment_1_leds + segment_2_leds + segment_3_leds
        
        # Initialize the LED strip
        self.strip = PixelStrip(total_leds, gpio_pin, 800000, 10, False, brightness, 1)
        self.strip.begin()
        
        # Turn off all LEDs initially
        self.clear_all()
    
    def set_segment_1(self, intensity):
        """
        Set segment 1 to white light with specified intensity
        
        Args:
            intensity: 0-255 (0=off, 255=full brightness)
        """
        self._set_segment(self.segment_1_start, self.segment_1_end, intensity, intensity, intensity)
    
    def set_segment_2(self, intensity):
        """
        Set segment 2 to white light with specified intensity
        
        Args:
            intensity: 0-255 (0=off, 255=full brightness)
        """
        self._set_segment(self.segment_2_start, self.segment_2_end, intensity, intensity, intensity)
    
    def set_segment_3(self, intensity):
        """
        Set segment 3 to white light with specified intensity
        
        Args:
            intensity: 0-255 (0=off, 255=full brightness)
        """
        self._set_segment(self.segment_3_start, self.segment_3_end, intensity, intensity, intensity)
    
    def set_all_segments(self, intensity1, intensity2, intensity3):
        """
        Set all three segments at once with different intensities
        
        Args:
            intensity1: Intensity for segment 1 (0-255)
            intensity2: Intensity for segment 2 (0-255)
            intensity3: Intensity for segment 3 (0-255)
        
        Example:
            controller.set_all_segments(255, 128, 64)  # Full, half, quarter brightness
        """
        self._set_segment(self.segment_1_start, self.segment_1_end, intensity1, intensity1, intensity1)
        self._set_segment(self.segment_2_start, self.segment_2_end, intensity2, intensity2, intensity2)
        self._set_segment(self.segment_3_start, self.segment_3_end, intensity3, intensity3, intensity3)
        self.strip.show()
    
    def _set_segment(self, start, end, r, g, b):
        """Internal method to set a segment's color"""
        color = Color(g, r, b)  # Note: Color() takes GRB order
        for i in range(start, end):
            self.strip.setPixelColor(i, color)
        self.strip.show()
    
    def clear_segment_1(self):
        """Turn off segment 1"""
        self.set_segment_1(0)
    
    def clear_segment_2(self):
        """Turn off segment 2"""
        self.set_segment_2(0)
    
    def clear_segment_3(self):
        """Turn off segment 3"""
        self.set_segment_3(0)
    
    def clear_all(self):
        """Turn off all LEDs"""
        for i in range(self.total_leds):
            self.strip.setPixelColor(i, Color(0, 0, 0))
        self.strip.show()
    
    def set_system_intensity(self, system_num, intensity):
        """
        Set a system's light intensity
        
        Args:
            system_num: 1, 2, or 3
            intensity: 0-255 (0=off, 255=full brightness)
                      Can also use preset strings:
                      - 'off' or 'inactive': 0
                      - 'low': 64
                      - 'medium': 128
                      - 'high': 192
                      - 'full' or 'max': 255
        
        Example:
            controller.set_system_intensity(1, 255)    # Full brightness
            controller.set_system_intensity(2, 128)    # Half brightness
            controller.set_system_intensity(3, 'low')  # Low preset
        """
        # Predefined intensity levels
        intensity_presets = {
            'off': 0,
            'inactive': 0,
            'low': 64,
            'medium': 128,
            'high': 192,
            'full': 255,
            'max': 255,
        }
        
        # Get intensity (either from preset or direct value)
        if isinstance(intensity, str):
            intensity_value = intensity_presets.get(intensity.lower(), 128)  # Default to medium
        else:
            intensity_value = max(0, min(255, int(intensity)))  # Clamp to 0-255
        
        # Set the appropriate segment
        if system_num == 1:
            self.set_segment_1(intensity_value)
        elif system_num == 2:
            self.set_segment_2(intensity_value)
        elif system_num == 3:
            self.set_segment_3(intensity_value)
    
    def get_segment_info(self):
        """Get information about segment configuration"""
        return {
            'segment_1': {'start': self.segment_1_start, 'end': self.segment_1_end, 'count': self.segment_1_end - self.segment_1_start},
            'segment_2': {'start': self.segment_2_start, 'end': self.segment_2_end, 'count': self.segment_2_end - self.segment_2_start},
            'segment_3': {'start': self.segment_3_start, 'end': self.segment_3_end, 'count': self.segment_3_end - self.segment_3_start},
        }


# Example usage
if __name__ == "__main__":
    import time
    
    print("LED Segment Controller Test")
    print("=" * 50)
    
    # Create controller (20 LEDs per segment)
    controller = LEDSegmentController(total_leds=60, segment_1_leds=20, 
                                     segment_2_leds=20, segment_3_leds=20)
    
    # Print segment info
    info = controller.get_segment_info()
    print("\nSegment Configuration:")
    for seg_name, seg_info in info.items():
        print(f"  {seg_name}: LEDs {seg_info['start']}-{seg_info['end']-1} ({seg_info['count']} LEDs)")
    
    print("\nRunning tests...\n")
    
    try:
        # Test 1: Individual segments with different intensities
        print("Test 1: Setting individual segments to different intensities")
        controller.set_segment_1(255)  # Full brightness
        time.sleep(1)
        controller.set_segment_2(128)  # Half brightness
        time.sleep(1)
        controller.set_segment_3(64)   # Quarter brightness
        time.sleep(2)
        
        # Test 2: All at once with different intensities
        print("Test 2: Setting all segments at once")
        controller.set_all_segments(255, 128, 64)  # Full, half, quarter
        time.sleep(2)
        
        # Test 3: Intensity presets
        print("Test 3: Using intensity presets")
        controller.set_system_intensity(1, 'full')
        controller.set_system_intensity(2, 'medium')
        controller.set_system_intensity(3, 'low')
        time.sleep(3)
        
        print("Test 4: Ramping up intensity on all segments")
        for intensity in range(0, 256, 32):
            controller.set_all_segments(intensity, intensity, intensity)
            time.sleep(0.3)
        time.sleep(1)
        
        print("Test 5: Dimming down")
        for intensity in range(255, -1, -32):
            controller.set_all_segments(intensity, intensity, intensity)
            time.sleep(0.3)
        
        print("\nTests complete!")
        
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    
    finally:
        print("Clearing all LEDs...")
        controller.clear_all()
        print("Done!")