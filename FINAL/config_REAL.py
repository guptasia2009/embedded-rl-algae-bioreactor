"""
Configuration File for Triple Bioreactor System
"""

# ============================================================================
# HARDWARE CONFIGURATION
# ============================================================================

# Servo Configuration
SERVO_PINS = [18, 13, 12]
SYRINGE_MIN_ML = 3.0
SYRINGE_MAX_ML = 7.0
SYRINGE_USABLE_VOLUME = 4.0  # 7mL - 3mL

# LED Configuration
TOTAL_LEDS = 60
LED_GPIO_PIN = 19
LED_BRIGHTNESS = 128

# LED positions (3 LEDs per reactor, 3 LED gap between)
REACTOR_1_LEDS = [57, 58, 59]
REACTOR_2_LEDS = [51, 52, 53]
REACTOR_3_LEDS = [45, 46, 47]

NUM_REACTORS = 3

# ============================================================================
# CONTROL PARAMETERS
# ============================================================================

CONTROL_INTERVAL = 1800     # 30 minutes
EXPERIMENT_DURATION = 120   # 5 days
DAILY_RESET_INTERVAL = 86400  # 24 hours

# Budgets
DAILY_NUTRIENT_BUDGET = 4.0  # mL per day
MIN_DARK_PERIOD = 12.0       # hours (UTEX Chlorella vulgaris: 12:12 cycle)

# Limits
MAX_NUTRIENT_RATE = 1.0      # mL/hour
MAX_LIGHT_INTENSITY = 255

# ============================================================================
# BIOLOGICAL CONSTANTS
# ============================================================================

MU_MAX = 0.06
KS = 0.5
KI = 100.0
K_LIGHT = 0.01
K_DECAY = 0.004
REACTOR_DEPTH = 0.2
Q_MIN = 0.05

# Initial conditions
X_INIT = 1.0
S_INIT = 5.0
I_INIT = 60.0

DO_YIELD = 1.0

# ============================================================================
# STATE ESTIMATION
# ============================================================================

DO_HISTORY_LENGTH = 10
BIOMASS_DECAY_RATE = 0.999

# ============================================================================
# RL MODEL
# ============================================================================

MODEL_PATH = "bioreactor_model.zip"
TRAINING_TIMESTEPS = 300_000
LEARNING_RATE = 3e-4
GAMMA = 0.99

# State: [nutrient_est, DO, DO_trend, light_level]
STATE_LOW = [0.0, 0.0, -2.0, 0.0]
STATE_HIGH = [20.0, 20.0, 2.0, 255.0]

# Action: [nutrient_rate, led_intensity]
ACTION_LOW = [-1.0, -1.0]
ACTION_HIGH = [1.0, 1.0]