#!/usr/bin/env python3
"""
Simple White Light Intensity Test
Tests three segments with variable white light intensity
"""

import time
from rpi_ws281x import PixelStrip, Color

# Configure your strip
LED_COUNT = 60       # Total number of LEDs
LED_PIN = 19         # GPIO 19
LED_BRIGHTNESS = 255 # Max brightness capability
LED_CHANNEL = 1

# Define three segments (20 LEDs each)
SEGMENT_1_START = 0
SEGMENT_1_END = 20

SEGMENT_2_START = 20
SEGMENT_2_END = 40

SEGMENT_3_START = 40
SEGMENT_3_END = 60

# Initialize strip
strip = PixelStrip(LED_COUNT, LED_PIN, 800000, 10, False, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()

def set_segment_intensity(segment_start, segment_end, intensity):
    """Set a segment to white light with specified intensity (0-255)"""
    color = Color(intensity, intensity, intensity)
    for i in range(segment_start, segment_end):
        strip.setPixelColor(i, color)
    strip.show()

def set_all_intensities(intensity1, intensity2, intensity3):
    """Set all three segments to different white light intensities"""
    # Segment 1
    for i in range(SEGMENT_1_START, SEGMENT_1_END):
        strip.setPixelColor(i, Color(intensity1, intensity1, intensity1))
    # Segment 2
    for i in range(SEGMENT_2_START, SEGMENT_2_END):
        strip.setPixelColor(i, Color(intensity2, intensity2, intensity2))
    # Segment 3
    for i in range(SEGMENT_3_START, SEGMENT_3_END):
        strip.setPixelColor(i, Color(intensity3, intensity3, intensity3))
    strip.show()

def clear_all():
    """Turn off all LEDs"""
    for i in range(LED_COUNT):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()

print("White Light Intensity Test - Three Segments")
print(f"Segment 1: LEDs {SEGMENT_1_START}-{SEGMENT_1_END-1}")
print(f"Segment 2: LEDs {SEGMENT_2_START}-{SEGMENT_2_END-1}")
print(f"Segment 3: LEDs {SEGMENT_3_START}-{SEGMENT_3_END-1}")
print("Press Ctrl+C to stop\n")

try:
    # Test 1: Individual segments at different intensities
    print("Test 1: Different intensities for each segment")
    print("  Segment 1: Full brightness (255)")
    set_segment_intensity(SEGMENT_1_START, SEGMENT_1_END, 255)
    time.sleep(2)
    
    print("  Segment 2: Half brightness (128)")
    set_segment_intensity(SEGMENT_2_START, SEGMENT_2_END, 128)
    time.sleep(2)
    
    print("  Segment 3: Quarter brightness (64)")
    set_segment_intensity(SEGMENT_3_START, SEGMENT_3_END, 64)
    time.sleep(2)
    
    # Test 2: All segments at once
    print("\nTest 2: All segments with different intensities")
    set_all_intensities(255, 128, 64)
    time.sleep(3)
    
    # Test 3: Ramping up intensity
    print("\nTest 3: Ramping up all segments")
    for intensity in range(0, 256, 16):
        set_all_intensities(intensity, intensity, intensity)
        time.sleep(0.1)
    time.sleep(1)
    
    # Test 4: Individual control - simulating growth phases
    print("\nTest 4: Simulating different growth phases")
    print("  Phase 1: High, Medium, Low")
    set_all_intensities(255, 128, 64)
    time.sleep(2)
    
    print("  Phase 2: Medium, High, Medium")
    set_all_intensities(128, 255, 128)
    time.sleep(2)
    
    print("  Phase 3: Low, Low, High")
    set_all_intensities(64, 64, 255)
    time.sleep(2)
    
    print("  Phase 4: All maximum")
    set_all_intensities(255, 255, 255)
    time.sleep(2)
    
    # Test 5: Smooth dimming
    print("\nTest 5: Smooth dimming")
    for intensity in range(255, -1, -8):
        set_all_intensities(intensity, intensity, intensity)
        time.sleep(0.05)
    
    print("\nAll tests complete!")

except KeyboardInterrupt:
    print("\n\nStopping...")

finally:
    print("Turning off all LEDs...")
    clear_all()
    print("Done!")
    