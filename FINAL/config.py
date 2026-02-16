"""
TEST Configuration - 30 minute quick test
Use this to verify everything works before running the real 5-day experiment
"""

# ============================================================================
# HARDWARE CONFIGURATION
# ============================================================================

# Servo Configuration
SERVO_PINS = [18, 13, 12]
SYRINGE_MIN_ML = 3.0
SYRINGE_MAX_ML = 7.0
SYRINGE_USABLE_VOLUME = 4.0

# LED Configuration
TOTAL_LEDS = 60
LED_GPIO_PIN = 19
LED_BRIGHTNESS = 128

# LED positions
REACTOR_1_LEDS = [57, 58, 59]
REACTOR_2_LEDS = [51, 52, 53]
REACTOR_3_LEDS = [45, 46, 47]

NUM_REACTORS = 3

# ============================================================================
# TEST CONTROL PARAMETERS
# ============================================================================

CONTROL_INTERVAL = 60       # 1 minute (instead of 30 min)
EXPERIMENT_DURATION = 0.5   # 30 minutes (instead of 120 hours)
DAILY_RESET_INTERVAL = 1800 # 30 min test reset (instead of 24 hours)

# Test budgets (scaled down for 30 min test)
DAILY_NUTRIENT_BUDGET = 4  # Small amount for testing
MIN_DARK_PERIOD = 0.25       # 15 min dark period minimum

# Limits
MAX_NUTRIENT_RATE = 1.0
MAX_LIGHT_INTENSITY = 255

# ============================================================================
# BIOLOGICAL CONSTANTS (same as real)
# ============================================================================

MU_MAX = 0.06
KS = 0.5
KI = 100.0
K_LIGHT = 0.01
K_DECAY = 0.004
REACTOR_DEPTH = 0.2
Q_MIN = 0.05

X_INIT = 1.0
S_INIT = 5.0
I_INIT = 60.0

DO_YIELD = 1.0

# ============================================================================
# STATE ESTIMATION (same as real)
# ============================================================================

DO_HISTORY_LENGTH = 10
BIOMASS_DECAY_RATE = 0.999

# ============================================================================
# RL MODEL (same as real)
# ============================================================================

MODEL_PATH = "bioreactor_model.zip"
TRAINING_TIMESTEPS = 300_000
LEARNING_RATE = 3e-4
GAMMA = 0.99

STATE_LOW = [0.0, 0.0, -2.0, 0.0]
STATE_HIGH = [20.0, 20.0, 2.0, 255.0]

ACTION_LOW = [-1.0, -1.0]
ACTION_HIGH = [1.0, 1.0]