#!/usr/bin/env python3
"""
Simple WS2812B Test - Just lights up the strip in different colors
Perfect for quickly testing if everything is working
"""

import time
from rpi_ws281x import PixelStrip, Color

# Configure your strip
LED_COUNT = 60       # Change this to your strip's LED count
LED_PIN = 19         # GPIO 19
LED_BRIGHTNESS = 128 # 0-255 (start at 128 for safety)
LED_CHANNEL = 1
# Initialize strip
strip = PixelStrip(LED_COUNT, LED_PIN, 800000, 10, False, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()

print("Testing WS2812B on GPIO 19...")
print("Press Ctrl+C to stop\n")

try:
    # Test 1: All red
    print("Test 1: All RED")
    for i in range(LED_COUNT):
        strip.setPixelColor(i, Color(255, 0, 0))
    strip.show()
    time.sleep(2)
    
    # Test 2: All green
    print("Test 2: All GREEN")
    for i in range(LED_COUNT):
        strip.setPixelColor(i, Color(0, 255, 0))
    strip.show()
    time.sleep(2)
    
    # Test 3: All blue
    print("Test 3: All BLUE")
    for i in range(LED_COUNT):
        strip.setPixelColor(i, Color(0, 0, 255))
    strip.show()
    time.sleep(2)
    
    # Test 4: White
    print("Test 4: All WHITE")
    for i in range(LED_COUNT):
        strip.setPixelColor(i, Color(255, 255, 255))
    strip.show()
    time.sleep(2)
    
    # Test 5: Running light
    print("Test 5: Running light")
    for _ in range(2):
        for i in range(LED_COUNT):
            strip.setPixelColor(i, Color(0, 150, 255))
            strip.show()
            time.sleep(0.05)
            strip.setPixelColor(i, Color(0, 0, 0))
    
    print("\nAll tests complete!")
    
except KeyboardInterrupt:
    print("\nStopping...")

finally:
    # Turn off all LEDs
    print("Turning off LEDs...")
    for i in range(LED_COUNT):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()
    print("Done!")