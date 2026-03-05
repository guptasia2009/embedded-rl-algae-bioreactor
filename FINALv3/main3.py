# Updated from main2 to control 2 rl and 1 static bioreactor
#sudo /home/siagupta/projects/IR/embeded-rl-algae-bioreactor/venv/bin/python main3.py
#nohup bash -c 'echo -e "1,2,3\n1\n1\n1\n3" | sudo /home/siagupta/projects/IR/embeded-rl-algae-bioreactor/venv/bin/python main3.py' > main3_output.log 2>&1 &
import os
import csv
import time
import threading
import gymnasium as gym
import torch
from gymnasium import spaces
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from stable_baselines3 import PPO
from stable_baselines3.common.logger import configure
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.monitor import Monitor
from collections import deque

from do_sensor_reader import *
from led_controller import *
from servo_controller import *
from logger import log, set_source

# Suppress the [UNKNOWN] prefix — tags are written manually in each log call
set_source("")

# --- CONFIGURATION ---
LOG_DIR = "./bioreactor_system/"

MODEL_PATH        = os.path.join(LOG_DIR, "bioreactor_model")
ONLINE_MODEL_EXP2 = os.path.join(LOG_DIR, "bioreactor_model_online_exp2")
ONLINE_MODEL_EXP3 = os.path.join(LOG_DIR, "bioreactor_model_online_exp3")

CSV_EXP2    = os.path.join(LOG_DIR, "deployment_history_EXP2.csv")
CSV_EXP3    = os.path.join(LOG_DIR, "deployment_history_EXP3.csv")
CSV_CONTROL = os.path.join(LOG_DIR, "deployment_history_CONTROL2.csv")

os.makedirs(LOG_DIR, exist_ok=True)

# LED pins
EXP2_LEDS    = [25, 26, 27]
EXP3_LEDS    = [32, 33, 34]
CONTROL_LEDS = [38, 39, 40]

# DO probe index mapping
EXP2_PROBE    = 0
EXP3_PROBE    = 1
CONTROL_PROBE = 2

# Static control settings
STATIC_LIGHT_INTENSITY   = 75.0
STATIC_NUTRIENT_ML       = 2.0    # ml per injection
STATIC_NUTRIENT_INTERVAL = 43200  # 12 hours in seconds

# Lights off from 10pm to 6am
LIGHTS_OFF_START = 22
LIGHTS_OFF_END   = 6


# ======================================================
# HARDWARE HOOKS
# ======================================================

def is_dark_period():
    hour = pd.Timestamp.now().hour
    return hour >= LIGHTS_OFF_START or hour < LIGHTS_OFF_END

def get_all_o2():
    raw = read_do()
    print("read_do(): " + str(raw))
    return float(raw[EXP2_PROBE]), float(raw[EXP3_PROBE]), float(raw[CONTROL_PROBE])

def set_exp2_light(percentage):
    print(f"[EXP 2][HARDWARE] Setting light to {percentage:.2f}%")
    set_leds(EXP2_LEDS, percentage * 255 / 100)

def set_exp3_light(percentage):
    print(f"[EXP 3][HARDWARE] Setting light to {percentage:.2f}%")
    set_leds(EXP3_LEDS, percentage * 255 / 100)

def inject_exp2_nutrients(ml_amount):
    print(f"[EXP 2][HARDWARE] Injecting {ml_amount:.3f} ml nutrients")
    dispense(1, ml_amount)

def inject_exp3_nutrients(ml_amount):
    print(f"[EXP 3][HARDWARE] Injecting {ml_amount:.3f} ml nutrients")
    dispense(2, ml_amount)


# Static control state — tracks nutrient timing and injection count
_static_last_injection   = None
_static_injections_since_reset = 0
_static_lock = threading.Lock()

def run_control_step(control_o2):
    global _static_last_injection, _static_injections_since_reset

    timestamp = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    now = time.time()
    lights_off = is_dark_period()
    current_light = 0.0 if lights_off else STATIC_LIGHT_INTENSITY
    set_leds(CONTROL_LEDS, current_light * 255 / 100)

    with _static_lock:
        time_since_last = (now - _static_last_injection) if _static_last_injection is not None else STATIC_NUTRIENT_INTERVAL
        if time_since_last >= STATIC_NUTRIENT_INTERVAL:
            print(f"[CONTROL 2][HARDWARE] Injecting {STATIC_NUTRIENT_ML:.1f} ml nutrients")
            dispense(3, STATIC_NUTRIENT_ML)
            log(f"[CONTROL 2] Injected {STATIC_NUTRIENT_ML:.1f} ml nutrients")
            _static_last_injection = now
            _static_injections_since_reset += 1

            if _static_injections_since_reset >= 2:
                print("[CONTROL 2][HARDWARE] 4ml dispensed - resetting servo 3. Please refill syringe.")
                reset_servo(3)
                log("[CONTROL 2] Servo 3 reset after 4ml dispensed")
                _static_injections_since_reset = 0

    msg = f"O2: {control_o2:.2f} | Light: {current_light:.1f}% | Lights off: {lights_off}"
    print(f"[CONTROL 2][{timestamp}] {msg}")
    log(f"[CONTROL 2] {msg}")

    with open(CSV_CONTROL, mode='a', newline='') as f:
        csv.writer(f).writerow([
            timestamp,
            f"{current_light:.2f}",
            f"{control_o2:.2f}",
            str(lights_off)
        ])


# ======================================================
# SIMULATION ENVIRONMENT
# ======================================================

class BioreactorEnv(gym.Env):
    LIGHT_OFF_STEP_START = 72
    LIGHT_OFF_STEP_END   = 96

    def __init__(self, simulation_mode=True, max_steps=96, dt=0.25):
        super(BioreactorEnv, self).__init__()

        self.action_space = spaces.Box(
            low=np.array([0, 0]),
            high=np.array([100, 1]),
            dtype=np.float32
        )
        self.observation_space = spaces.Box(low=0, high=1, shape=(5,), dtype=np.float32)

        self.dt = dt
        self.steps_per_day = int(24 / dt)
        self.steps_per_half_day = int(12 / dt)
        self.max_steps = max_steps

        self.P_max, self.Ks_l, self.Ki_l, self.Kn_n = 150.0, 20.0, 80.0, 5.0
        self.mu_max, self.Ks_n, self.death_rate, self.biomass_max = 0.15, 3.0, 0.01, 2.0

        self.reset()

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.biomass = 0.1
        self.nutrient_level = 0.0
        self.daily_nutrient_budget = 4.0
        self.half_day_nutrient_used = 0.0
        self.step_count = 0
        self.o2_history = deque([10.0] * 10, maxlen=10)
        return self._get_observation(), {}

    def _get_observation(self):
        current_o2 = self.o2_history[-1]
        o2_avg = np.mean(list(self.o2_history))
        time_of_day = (self.step_count % self.steps_per_day) / self.steps_per_day

        if len(self.o2_history) >= 3:
            recent_o2 = list(self.o2_history)[-3:]
            o2_trend = (recent_o2[-1] - recent_o2[0]) / (len(recent_o2) - 1)
        else:
            o2_trend = 0.0

        o2_trend_norm = np.clip((o2_trend + 5.0) / 10.0, 0, 1)

        return np.array([
            current_o2 / 200.0,
            o2_trend_norm,
            o2_avg / 200.0,
            self.daily_nutrient_budget / 4.0,
            time_of_day
        ], dtype=np.float32)

    def step(self, action):
        light, nutri_req = action

        step_in_day = self.step_count % self.steps_per_day
        if self.LIGHT_OFF_STEP_START <= step_in_day < self.LIGHT_OFF_STEP_END:
            light = 0.0

        if self.step_count > 0 and self.step_count % self.steps_per_half_day == 0:
            self.half_day_nutrient_used = 0.0

        if self.step_count > 0 and self.step_count % self.steps_per_day == 0:
            self.daily_nutrient_budget = 4.0

        half_day_remaining = max(0.0, 2.0 - self.half_day_nutrient_used)
        actual_nutri = float(min(float(nutri_req), half_day_remaining, self.daily_nutrient_budget))

        self.daily_nutrient_budget = max(0.0, self.daily_nutrient_budget - actual_nutri)
        self.half_day_nutrient_used += actual_nutri

        self.nutrient_level = (self.nutrient_level + actual_nutri) * 0.95
        growth = self.mu_max * (self.nutrient_level / (self.nutrient_level + self.Ks_n + 1e-6))
        self.biomass = np.clip(self.biomass * (1 + (growth - self.death_rate) * self.dt), 0.01, self.biomass_max)

        light_eff = light / (light + self.Ks_l + (light**2 / self.Ki_l) + 1e-6)
        o2_rate = self.P_max * light_eff * (self.nutrient_level / (self.nutrient_level + self.Kn_n + 1e-6)) * (self.biomass / 0.5)

        new_o2 = self.o2_history[-1] + (o2_rate * self.dt * 0.1) + np.random.normal(0, 0.1)
        self.o2_history.append(new_o2)

        reward = (o2_rate / 5.0) - (light * 0.005)
        if o2_rate > 60:
            reward += 10.0

        self.step_count += 1
        done = self.step_count >= self.max_steps or self.biomass < 0.05

        info = {
            'o2_reading': new_o2,
            'biomass': self.biomass,
            'budget': self.daily_nutrient_budget,
            'half_day_used': self.half_day_nutrient_used,
            'o2_rate': o2_rate,
            'actual_nutri': actual_nutri,
            'light_forced_off': light == 0.0
        }
        return self._get_observation(), float(reward), False, done, info


# ======================================================
# REAL HARDWARE ENVIRONMENTS
# ======================================================

class RealBioreactorEnvEXP2(BioreactorEnv):
    LIGHTS_OFF_START = 22
    LIGHTS_OFF_END   = 6

    def step(self, action):
        light, nutri_req = action

        current_hour = pd.Timestamp.now().hour
        lights_off = (current_hour >= self.LIGHTS_OFF_START or current_hour < self.LIGHTS_OFF_END)
        if lights_off:
            action = np.array([0.0, nutri_req], dtype=np.float32)

        obs, reward, terminated, truncated, info = super().step(action)

        exp2_o2, exp3_o2, control_o2 = get_all_o2()
        self.o2_history.append(exp2_o2)
        info['o2_reading'] = exp2_o2
        info['exp3_o2']    = exp3_o2
        info['control_o2'] = control_o2
        info['lights_off'] = lights_off

        obs = self._get_observation()
        return obs, reward, terminated, truncated, info


class RealBioreactorEnvEXP3(BioreactorEnv):
    LIGHTS_OFF_START = 22
    LIGHTS_OFF_END   = 6

    def step(self, action):
        light, nutri_req = action

        current_hour = pd.Timestamp.now().hour
        lights_off = (current_hour >= self.LIGHTS_OFF_START or current_hour < self.LIGHTS_OFF_END)
        if lights_off:
            action = np.array([0.0, nutri_req], dtype=np.float32)

        obs, reward, terminated, truncated, info = super().step(action)

        exp2_o2, exp3_o2, control_o2 = get_all_o2()
        self.o2_history.append(exp3_o2)
        info['o2_reading'] = exp3_o2
        info['control_o2'] = control_o2
        info['lights_off'] = lights_off

        obs = self._get_observation()
        return obs, reward, terminated, truncated, info


# ======================================================
# CALLBACKS
# ======================================================

class TrainingCallback(BaseCallback):
    def __init__(self, check_freq=5000, verbose=1):
        super(TrainingCallback, self).__init__(verbose)
        self.check_freq = check_freq
        self.best_mean_reward = -np.inf

    def _on_step(self) -> bool:
        if self.n_calls % self.check_freq == 0:
            if len(self.model.ep_info_buffer) > 0:
                mean_reward = np.mean([ep_info['r'] for ep_info in self.model.ep_info_buffer])
                if mean_reward > self.best_mean_reward:
                    self.best_mean_reward = mean_reward
                    print(f"Step {self.n_calls}: New best reward: {mean_reward:.2f}")
        return True


class HardwareStepCallbackEXP2(BaseCallback):
    def __init__(self, barrier_end, barrier_start, step_interval_seconds=1800, verbose=1):
        super(HardwareStepCallbackEXP2, self).__init__(verbose)
        self.barrier_end = barrier_end
        self.barrier_start = barrier_start
        self.step_interval_seconds = step_interval_seconds

    def _on_step(self) -> bool:
        action = self.locals['actions'][0]
        light_pct = float(action[0])
        info = self.locals['infos'][0]
        timestamp = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')

        run_control_step(info.get('control_o2', 0.0))

        if is_dark_period():
            light_pct = 0.0
        set_exp2_light(light_pct)

        actually_dispensed = info['actual_nutri']
        if actually_dispensed > 0.0:
            inject_exp2_nutrients(actually_dispensed)

        step_in_day = self.n_calls % 48
        if step_in_day == 47:
            print("[EXP 2][HARDWARE] End of day - resetting servo 1. Please refill syringe.")
            reset_servo(1)

        msg = (f"O2: {info['o2_reading']:.2f} | Light: {light_pct:.1f}% | "
               f"Dispensed: {actually_dispensed:.3f}ml | Budget: {info['budget']:.2f}ml | "
               f"Half-day used: {info['half_day_used']:.2f}ml | Lights off: {info.get('lights_off', False)}")
        print(f"[EXP 2][{timestamp}] {msg}")
        log(f"[EXP 2] {msg}")

        with open(CSV_EXP2, mode='a', newline='') as f:
            csv.writer(f).writerow([
                timestamp,
                f"{light_pct:.2f}",
                f"{actually_dispensed:.3f}",
                f"{info['o2_reading']:.2f}",
                f"{info['biomass']:.3f}",
                f"{info['budget']:.2f}",
                f"{info['half_day_used']:.2f}",
                str(info.get('lights_off', False))
            ])

        self.barrier_end.wait()
        time.sleep(self.step_interval_seconds)
        self.barrier_start.wait()
        return True


class HardwareStepCallbackEXP3(BaseCallback):
    def __init__(self, barrier_end, barrier_start, verbose=1):
        super(HardwareStepCallbackEXP3, self).__init__(verbose)
        self.barrier_end = barrier_end
        self.barrier_start = barrier_start

    def _on_step(self) -> bool:
        action = self.locals['actions'][0]
        light_pct = float(action[0])
        info = self.locals['infos'][0]
        timestamp = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')

        if is_dark_period():
            light_pct = 0.0
        set_exp3_light(light_pct)

        actually_dispensed = info['actual_nutri']
        if actually_dispensed > 0.0:
            inject_exp3_nutrients(actually_dispensed)

        step_in_day = self.n_calls % 48
        if step_in_day == 47:
            print("[EXP 3][HARDWARE] End of day - resetting servo 2. Please refill syringe.")
            reset_servo(2)

        msg = (f"O2: {info['o2_reading']:.2f} | Light: {light_pct:.1f}% | "
               f"Dispensed: {actually_dispensed:.3f}ml | Budget: {info['budget']:.2f}ml | "
               f"Half-day used: {info['half_day_used']:.2f}ml | Lights off: {info.get('lights_off', False)}")
        print(f"[EXP 3][{timestamp}] {msg}")
        log(f"[EXP 3] {msg}")

        with open(CSV_EXP3, mode='a', newline='') as f:
            csv.writer(f).writerow([
                timestamp,
                f"{light_pct:.2f}",
                f"{actually_dispensed:.3f}",
                f"{info['o2_reading']:.2f}",
                f"{info['biomass']:.3f}",
                f"{info['budget']:.2f}",
                f"{info['half_day_used']:.2f}",
                str(info.get('lights_off', False))
            ])

        self.barrier_end.wait()
        self.barrier_start.wait()
        return True


# ======================================================
# CORE FUNCTIONS
# ======================================================

def train():
    if os.path.exists(MODEL_PATH + ".zip"):
        os.remove(MODEL_PATH + ".zip")

    env = Monitor(BioreactorEnv(), LOG_DIR)
    new_logger = configure(LOG_DIR, ["stdout", "csv"])

    model = PPO(
        "MlpPolicy", env,
        learning_rate=0.0001,
        n_steps=4096,
        batch_size=128,
        n_epochs=15,
        gamma=0.99,
        ent_coef=0.03,
        device="cpu",
        verbose=1
    )
    model.set_logger(new_logger)

    callback = TrainingCallback()
    print("\n[INFO] Starting 200,000 step training...")
    model.learn(total_timesteps=200000, callback=callback)
    model.save(MODEL_PATH)
    print(f"\n[INFO] Base model saved to {MODEL_PATH}")


def _load_model(online_path, label):
    if os.path.exists(online_path + ".zip"):
        print(f"[INFO] [{label}] Resuming from previous online model...")
        return online_path
    elif os.path.exists(MODEL_PATH + ".zip"):
        print(f"[INFO] [{label}] Starting from base trained model...")
        return MODEL_PATH
    else:
        return None


def _setup_model(load_path, env):
    model = PPO.load(load_path, env=env)
    model.n_steps = 48
    model.batch_size = 16
    model._last_obs = None
    model._setup_learn(total_timesteps=10_000_000, callback=None, reset_num_timesteps=False)
    # Explicitly rebuild rollout buffer at n_steps=48 to fix AssertionError
    from stable_baselines3.common.buffers import RolloutBuffer
    model.rollout_buffer = RolloutBuffer(
        model.n_steps,
        model.observation_space,
        model.action_space,
        device=model.device,
        gamma=model.gamma,
        gae_lambda=model.gae_lambda,
        n_envs=model.n_envs,
    )
    return model


def _pretrain_from_csv(model, csv_path, label):
    # Reconstruct observations and rewards from historical CSV data
    # and run PPO gradient updates before live deployment begins.
    if not os.path.exists(csv_path):
        print(f"[INFO] [{label}] No historical CSV found, skipping pretrain.")
        return

    try:
        df = pd.read_csv(csv_path, header=0)
        df.columns = ["Timestamp", "Light_Pct", "Nutri_ml", "O2_Reading",
                      "Biomass", "Daily_Budget_Left", "Half_Day_Used", "Lights_Off"]
        df = df.dropna().reset_index(drop=True)

        if len(df) < 48:
            print(f"[INFO] [{label}] Not enough rows for a full pretrain batch, skipping.")
            return

        print(f"[INFO] [{label}] Pretraining from {len(df)} historical rows...")

        o2_vals     = df["O2_Reading"].values.astype(np.float32)
        light_vals  = df["Light_Pct"].values.astype(np.float32)
        nutri_vals  = df["Nutri_ml"].values.astype(np.float32)
        budget_vals = df["Daily_Budget_Left"].values.astype(np.float32)

        observations, actions, rewards = [], [], []

        for i in range(len(df)):
            # Reconstruct full observation vector
            o2_window   = o2_vals[max(0, i-2):i+1]
            o2_trend    = (o2_window[-1] - o2_window[0]) / max(len(o2_window) - 1, 1)
            o2_avg      = np.mean(o2_vals[max(0, i-9):i+1])
            time_of_day = (i % 48) / 48.0
            o2_trend_norm = np.clip((o2_trend + 5.0) / 10.0, 0, 1)

            obs = np.array([
                o2_vals[i] / 200.0,
                o2_trend_norm,
                o2_avg / 200.0,
                budget_vals[i] / 4.0,
                time_of_day
            ], dtype=np.float32)

            action = np.array([light_vals[i], nutri_vals[i]], dtype=np.float32)

            # Recompute reward using same formula as training
            light_eff = light_vals[i] / (light_vals[i] + 20.0 + (light_vals[i]**2 / 80.0) + 1e-6)
            nutri      = nutri_vals[i]
            o2_rate    = 150.0 * light_eff * (nutri / (nutri + 5.0 + 1e-6))
            reward     = (o2_rate / 5.0) - (light_vals[i] * 0.005)
            if o2_rate > 60:
                reward += 10.0

            observations.append(obs)
            actions.append(action)
            rewards.append(float(reward))

        # Run gradient updates in 48-step batches
        n_batches = len(observations) // 48
        for b in range(n_batches):
            obs_batch = np.array(observations[b*48:(b+1)*48])
            act_batch = np.array(actions[b*48:(b+1)*48])
            rew_batch = np.array(rewards[b*48:(b+1)*48])

            buf = model.rollout_buffer
            buf.reset()
            for j in range(48):
                obs_t = torch.tensor(obs_batch[j:j+1], dtype=torch.float32).to(model.device)
                with torch.no_grad():
                    val      = model.policy.predict_values(obs_t)
                    dist     = model.policy.get_distribution(obs_t)
                    act_t    = torch.tensor(act_batch[j:j+1], dtype=torch.float32).to(model.device)
                    log_prob = dist.log_prob(act_t)

                buf.add(
                    obs_batch[j:j+1],
                    act_batch[j:j+1],
                    np.array([rew_batch[j]]),
                    np.array([j < 47], dtype=np.float32),
                    val,
                    log_prob
                )

            last_obs_t = torch.tensor(obs_batch[-1:], dtype=torch.float32).to(model.device)
            with torch.no_grad():
                last_val = model.policy.predict_values(last_obs_t)
            buf.compute_returns_and_advantage(last_values=last_val, dones=np.array([False]))
            model.train()

        print(f"[INFO] [{label}] Pretrained on {n_batches} batches.")

    except Exception as e:
        import traceback
        print(f"[WARNING] [{label}] Pretrain failed: {e}")
        traceback.print_exc()
        print(f"[INFO] [{label}] Continuing without pretrain.")


def _init_csv(path, headers):
    if not os.path.exists(path):
        with open(path, mode='w', newline='') as f:
            csv.writer(f).writerow(headers)


def deploy_to_reactor():
    global _static_last_injection, _static_injections_since_reset

    initialize_leds()

    # Only create CSV files if they don't already exist — preserves historical data
    _init_csv(CSV_CONTROL, ["Timestamp", "Light_Pct", "O2_Reading", "Lights_Off"])
    _init_csv(CSV_EXP2, ["Timestamp", "Light_Pct", "Nutri_ml", "O2_Reading",
                          "Biomass", "Daily_Budget_Left", "Half_Day_Used", "Lights_Off"])
    _init_csv(CSV_EXP3, ["Timestamp", "Light_Pct", "Nutri_ml", "O2_Reading",
                          "Biomass", "Daily_Budget_Left", "Half_Day_Used", "Lights_Off"])

    load_exp2 = _load_model(ONLINE_MODEL_EXP2, "EXP 2")
    load_exp3 = _load_model(ONLINE_MODEL_EXP3, "EXP 3")

    if not load_exp2 or not load_exp3:
        print("[ERROR] No model found. Run training (Option 1) first.")
        return

    print("[INFO] Deploying EXP 2 and EXP 3 with continual learning enabled.")

    env_exp2 = Monitor(RealBioreactorEnvEXP2(), LOG_DIR)
    env_exp3 = Monitor(RealBioreactorEnvEXP3(), LOG_DIR)

    model_exp2 = _setup_model(load_exp2, env_exp2)
    model_exp3 = _setup_model(load_exp3, env_exp3)

    model_exp2.set_logger(configure(LOG_DIR, ["stdout", "csv"]))
    model_exp3.set_logger(configure(LOG_DIR, ["stdout", "csv"]))

    # Pretrain from historical CSV data before live deployment
    _pretrain_from_csv(model_exp2, CSV_EXP2, "EXP 2")
    _pretrain_from_csv(model_exp3, CSV_EXP3, "EXP 3")

    print(f"[INFO] Logging EXP 2 to {CSV_EXP2}")
    print(f"[INFO] Logging EXP 3 to {CSV_EXP3}")
    print(f"[INFO] Logging CONTROL 2 to {CSV_CONTROL}")
    print("[INFO] Press Ctrl+C to stop and save.")
    print("[INFO] Making decisions every 30 minutes.\n")

    barrier_end   = threading.Barrier(2)
    barrier_start = threading.Barrier(2)
    stop_event    = threading.Event()

    def run_exp2():
        try:
            model_exp2.learn(
                total_timesteps=10_000_000,
                callback=[
                    TrainingCallback(check_freq=48),
                    HardwareStepCallbackEXP2(barrier_end=barrier_end, barrier_start=barrier_start, step_interval_seconds=1800)
                ],
                reset_num_timesteps=False
            )
            model_exp2.save(ONLINE_MODEL_EXP2)
            print(f"\n[INFO] EXP 2 model saved to {ONLINE_MODEL_EXP2}")
        except Exception as e:
            import traceback
            print(f"[ERROR] EXP 2 thread crashed: {e}")
            traceback.print_exc()
        finally:
            stop_event.set()

    def run_exp3():
        try:
            model_exp3.learn(
                total_timesteps=10_000_000,
                callback=[
                    TrainingCallback(check_freq=48),
                    HardwareStepCallbackEXP3(barrier_end=barrier_end, barrier_start=barrier_start)
                ],
                reset_num_timesteps=False
            )
            model_exp3.save(ONLINE_MODEL_EXP3)
            print(f"\n[INFO] EXP 3 model saved to {ONLINE_MODEL_EXP3}")
        except Exception as e:
            import traceback
            print(f"[ERROR] EXP 3 thread crashed: {e}")
            traceback.print_exc()
        finally:
            stop_event.set()

    t2 = threading.Thread(target=run_exp2, daemon=True)
    t3 = threading.Thread(target=run_exp3, daemon=True)
    t2.start()
    t3.start()

    try:
        stop_event.wait()
    except KeyboardInterrupt:
        print("\n[INFO] Shutdown signal received. Saving models...")
        model_exp2.save(ONLINE_MODEL_EXP2)
        model_exp3.save(ONLINE_MODEL_EXP3)
        set_leds(EXP2_LEDS, 0)
        set_leds(EXP3_LEDS, 0)
        set_leds(CONTROL_LEDS, 0)
        print(f"[INFO] EXP 2 model saved to {ONLINE_MODEL_EXP2}")
        print(f"[INFO] EXP 3 model saved to {ONLINE_MODEL_EXP3}")


def run_safety_demo():
    if not os.path.exists(MODEL_PATH + ".zip"):
        print("[ERROR] No trained model found. Run training (Option 1) first.")
        return

    load_path = ONLINE_MODEL_EXP2 if os.path.exists(ONLINE_MODEL_EXP2 + ".zip") else MODEL_PATH
    model = PPO.load(load_path)
    env = BioreactorEnv()
    obs, _ = env.reset()

    print("\n" + "="*110)
    print(f"{'STEP':<5} | {'LIGHT %':<8} | {'NUTRI ml':<9} | {'O2 LEVEL':<9} | {'BIOMASS':<8} | {'BUDGET LEFT':<12} | {'HEALTH STATUS'}")
    print("-" * 110)

    for i in range(20):
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)

        biomass = info['biomass']
        o2_rate = info['o2_rate']
        budget  = info['budget']

        if biomass < 0.06:
            status = "CRITICAL (near death)"
        elif o2_rate > 100:
            status = "EXCELLENT (peak photosynthesis)"
        elif o2_rate > 40:
            status = "STABLE (healthy growth)"
        elif budget < 0.5:
            status = "LOW NUTRIENTS"
        else:
            status = "DORMANT / STARTUP"

        print(f"{i+1:<5} | {action[0]:<8.1f} | {action[1]:<9.2f} | "
              f"{info['o2_reading']:<9.2f} | {biomass:<8.3f} | {budget:<12.2f} | {status}")

        if terminated:
            print("-" * 110)
            print("[STOPPED] Biomass dropped below safety threshold.")
            break

    print("=" * 110)
    print(f"O2 change: {info['o2_reading'] - 10:.2f} mg/L")
    print(f"Daily nutrient budget remaining: {info['budget']:.2f} ml")
    print(f"Half-day nutrient used: {info['half_day_used']:.2f} ml")


def main():
    while True:
        print("\n--- BIOREACTOR CONTROL ---")
        print("1: Train model (200k steps, simulation)")
        print("2: Run safety demo")
        print("3: Deploy to hardware (EXP 2 + EXP 3 + CONTROL 2)")
        print("4: Exit")
        choice = input("Select: ")
        if   choice == '1': train()
        elif choice == '2': run_safety_demo()
        elif choice == '3': deploy_to_reactor()
        elif choice == '4': break

if __name__ == "__main__":
    main()