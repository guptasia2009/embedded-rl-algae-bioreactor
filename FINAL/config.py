"""
Configuration File for Triple Bioreactor System
All hardware settings, biological constants, and control parameters
"""

# ============================================================================
# HARDWARE CONFIGURATION
# ============================================================================

# Servo Configuration
SERVO_PINS = [18, 13, 12]  # GPIO pins for servos (BCM numbering)

# LED Configuration
TOTAL_LEDS = 60            # Total LEDs on strip
LED_GPIO_PIN = 19          # GPIO pin for LED strip
LED_BRIGHTNESS = 128       # Default brightness (0-255)

# LED positions for each reactor (3 LEDs on, 3 LEDs gap)
# Starting from the end of the strip (LED 59 is the last)
REACTOR_1_LEDS = [57, 58, 59]  # Last 3 LEDs
REACTOR_2_LEDS = [51, 52, 53]  # 3 LEDs gap (54-56), then these 3
REACTOR_3_LEDS = [45, 46, 47]  # 3 LEDs gap (48-50), then these 3

# Number of Bioreactors
NUM_REACTORS = 3

# ============================================================================
# CONTROL PARAMETERS
# ============================================================================

# Timing
CONTROL_INTERVAL = 1800    # Control interval in seconds (30 minutes)
EXPERIMENT_DURATION = 120  # Total duration in hours (5 days)
DAILY_RESET_INTERVAL = 86400  # 24 hours in seconds

# Resource Budgets (per reactor, per 24 hours)
DAILY_NUTRIENT_BUDGET = 4.0  # mL per day (matches your F/2 dilution)
DAILY_LIGHT_BUDGET = 50000.0  # Arbitrary units for light energy
MIN_DARK_PERIOD = 8.0      # Minimum hours of darkness per day

# Control Limits
MAX_NUTRIENT_RATE = 1.0    # Maximum nutrient addition rate (mL/hour)
MAX_LIGHT_INTENSITY = 255  # Maximum LED brightness (0-255)

# ============================================================================
# BIOLOGICAL CONSTANTS (from your simulation)
# ============================================================================

# Growth parameters
MU_MAX = 0.06              # Maximum specific growth rate (1/hr)
KS = 0.5                   # Nutrient half-saturation constant
KI = 100.0                 # Light half-saturation constant
K_LIGHT = 0.01             # Light attenuation coefficient
K_DECAY = 0.004            # Base respiration rate

# Light limitation
REACTOR_DEPTH = 0.2        # Reactor depth in meters

# Nutrient model
Q_MIN = 0.05               # Minimal internal nutrient quota
U_XS = 0.5                 # Biomass yield on substrate

# Initial conditions
X_INIT = 1.0               # Initial biomass concentration
S_INIT = 5.0               # Initial nutrient concentration
I_INIT = 60.0              # Initial light intensity (arbitrary units)

# DO production
DO_YIELD = 1.0             # DO production per unit biomass growth

# ============================================================================
# STATE ESTIMATION PARAMETERS
# ============================================================================

DO_HISTORY_LENGTH = 10     # Number of DO readings to keep for trend calculation
BIOMASS_DECAY_RATE = 0.999 # Slow decay factor for biomass estimate
NUTRIENT_CONSUMPTION_RATE = 0.01  # Nutrient consumption per biomass unit

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

LOG_DIRECTORY = "./"       # Directory for log files
LOG_PREFIX = "bioreactor_log"  # Prefix for log filenames

# ============================================================================
# SAFETY LIMITS
# ============================================================================

MAX_NUTRIENT_TOTAL_PER_DAY = 10.0  # Absolute max per reactor (safety limit)
MAX_LIGHT_HOURS_PER_DAY = 24.0 - MIN_DARK_PERIOD  # Max light hours

# ============================================================================
# RL MODEL PARAMETERS
# ============================================================================

MODEL_PATH = "bioreactor_model.zip"  # Path to trained model
TRAINING_TIMESTEPS = 300_000         # Training duration
LEARNING_RATE = 3e-4
GAMMA = 0.99

# State space bounds
STATE_LOW = [0.0, 0.0, -2.0, 0.0]    # [nutrient, DO, DO_trend, light]
STATE_HIGH = [20.0, 20.0, 2.0, 255.0]

# Action space bounds  
ACTION_LOW = [-1.0, -1.0]            # [nutrient_rate, led_intensity]
ACTION_HIGH = [1.0, 1.0]

# ============================================================================
# DISPLAY SETTINGS
# ============================================================================

VERBOSE = True             # Print detailed status messages
SHOW_PLOTS = False         # Show matplotlib plots during training