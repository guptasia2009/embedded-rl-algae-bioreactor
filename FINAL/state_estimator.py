"""
State Estimator Module
It estimates bioreactor state from sensor readings
State: [nutrient_est, DO, DO_trend, light_level]
"""

import numpy as np
import config

# State tracking for each reactor
nutrient_estimates = [config.S_INIT, config.S_INIT, config.S_INIT]
biomass_estimates = [config.X_INIT, config.X_INIT, config.X_INIT]
do_histories = [[], [], []]
last_dos = [None, None, None]
current_lights = [config.I_INIT, config.I_INIT, config.I_INIT]

def update_state(reactor_num, do_reading, nutrient_added, light_level):
    """
    Update state for a reactor
    
    Args:
        reactor_num: 1, 2, or 3
        do_reading: Current DO in mg/L (or None)
        nutrient_added: mL added
        light_level: LED intensity 0-255
    """
    i = reactor_num - 1  # Convert to 0-indexed
    
    # Update light
    current_lights[i] = light_level
    
    # Update DO history
    if do_reading is not None:
        do_histories[i].append(do_reading)
        if len(do_histories[i]) > config.DO_HISTORY_LENGTH:
            do_histories[i].pop(0)
        last_dos[i] = do_reading
    
    # Estimate biomass from DO production
    if len(do_histories[i]) >= 2:
        recent_do = do_histories[i][-1]
        older_do = do_histories[i][0] if len(do_histories[i]) < 10 else do_histories[i][-10]
        do_change = recent_do - older_do
        
        if do_change > 0:
            biomass_estimates[i] *= (1.0 + do_change * 0.01)
    
    # Update nutrient (just track total added, no consumption)
    nutrient_estimates[i] += nutrient_added
    
    # Slow biomass decay
    biomass_estimates[i] *= config.BIOMASS_DECAY_RATE


def get_state(reactor_num):
    """
    Get state for RL model
    
    Args:
        reactor_num: 1, 2, or 3
    
    Returns:
        numpy array: [nutrient_est, DO, DO_trend, light_level]
    """
    i = reactor_num - 1
    
    # Get DO value
    do_value = last_dos[i] if last_dos[i] is not None else config.S_INIT
    
    # Calculate DO trend
    do_trend = 0.0
    if len(do_histories[i]) >= 2:
        n = min(len(do_histories[i]), 10)
        do_trend = (do_histories[i][-1] - do_histories[i][-n]) / n
        do_trend = np.clip(do_trend, -2.0, 2.0)
    
    return np.array([
        nutrient_estimates[i],
        do_value,
        do_trend,
        current_lights[i]
    ], dtype=np.float32)


def get_biomass(reactor_num):
    """Get biomass estimate for a reactor"""
    return biomass_estimates[reactor_num - 1]


def get_nutrient(reactor_num):
    """Get nutrient estimate for a reactor"""
    return nutrient_estimates[reactor_num - 1]