import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
import matplotlib.patheffects as pe

# ── DATA ──────────────────────────────────────────────────────────────────────
import os, sys

csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'progress.csv')
if not os.path.exists(csv_path):
    print(f"ERROR: progress.csv not found at {csv_path}")
    sys.exit(1)

# Try tab then comma separator, print columns if keys not found
df_progress = pd.read_csv(csv_path, sep=None, engine='python')
df_progress.columns = df_progress.columns.str.strip()

ts_col  = next((c for c in df_progress.columns if 'total_timesteps' in c), None)
rew_col = next((c for c in df_progress.columns if 'ep_rew_mean' in c), None)

if ts_col is None or rew_col is None:
    print("Available columns:", df_progress.columns.tolist())
    sys.exit(1)

df_progress = df_progress.dropna(subset=[ts_col, rew_col])
timesteps = (df_progress[ts_col].values / 1000).tolist()
rewards   = df_progress[rew_col].values.tolist()

# ── TRAINING CURVE ─────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 4.5))
fig.patch.set_facecolor('#0f1117')
ax.set_facecolor('#0f1117')

# Gradient fill under curve
ax.fill_between(timesteps, rewards, alpha=0.15, color='#2dd4bf')

# Smoothed line
from numpy.polynomial.polynomial import polyfit
smooth_x = np.linspace(min(timesteps), max(timesteps), 300)
coeffs = polyfit(timesteps, rewards, 6)
smooth_y = np.polyval(list(reversed(coeffs)), smooth_x)

ax.plot(timesteps, rewards, color='#2dd4bf', alpha=0.3, linewidth=1)
ax.plot(smooth_x, smooth_y, color='#2dd4bf', linewidth=2.5,
        path_effects=[pe.Stroke(linewidth=4, foreground='#2dd4bf', alpha=0.2), pe.Normal()])

# Convergence annotation
ax.axvline(x=130, color='#f59e0b', linewidth=1.2, linestyle='--', alpha=0.7)
ax.text(132, 5, 'Policy converges\n~130k steps', color='#f59e0b',
        fontsize=8, va='bottom', fontfamily='monospace')

# Start / end callouts
ax.annotate(f'Start\n{rewards[0]:.1f}', xy=(timesteps[0], rewards[0]),
            xytext=(15, 8), color='#94a3b8', fontsize=8,
            arrowprops=dict(arrowstyle='->', color='#94a3b8', lw=0.8))
ax.annotate(f'Final\n{rewards[-1]:.1f}', xy=(timesteps[-1], rewards[-1]),
            xytext=(165, 22), color='#2dd4bf', fontsize=8, fontweight='bold',
            arrowprops=dict(arrowstyle='->', color='#2dd4bf', lw=0.8))

ax.set_xlabel('Timesteps (thousands)', color='#94a3b8', fontsize=10)
ax.set_ylabel('Mean Episode Reward', color='#94a3b8', fontsize=10)
ax.set_title('PPO Training Convergence', color='white', fontsize=13, fontweight='bold', pad=12)

ax.tick_params(colors='#64748b', labelsize=8)
for spine in ax.spines.values():
    spine.set_edgecolor('#1e293b')
ax.grid(color='#1e293b', linewidth=0.5, alpha=0.8)

plt.tight_layout()
out_dir = os.path.dirname(os.path.abspath(__file__))
plt.savefig(os.path.join(out_dir, 'training_curve.png'), dpi=200,
            bbox_inches='tight', facecolor='#0f1117')
plt.close()
print("Training curve saved")

# ── NEURAL NETWORK DIAGRAM ────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 5.5))
fig.patch.set_facecolor('#0f1117')
ax.set_facecolor('#0f1117')
ax.set_xlim(0, 10)
ax.set_ylim(0, 6)
ax.axis('off')

TEAL   = '#2dd4bf'
AMBER  = '#f59e0b'
PURPLE = '#a78bfa'
GRAY   = '#94a3b8'
BG     = '#1e293b'

def draw_node(ax, x, y, color, radius=0.22):
    circle = plt.Circle((x, y), radius, color=color, zorder=3)
    ax.add_patch(circle)
    # glow
    glow = plt.Circle((x, y), radius+0.08, color=color, alpha=0.15, zorder=2)
    ax.add_patch(glow)

def draw_layer(ax, x, ys, color):
    for y in ys:
        draw_node(ax, x, y, color)

def draw_connections(ax, x1, ys1, x2, ys2, color='#1e293b', alpha=0.5):
    for y1 in ys1:
        for y2 in ys2:
            ax.plot([x1+0.22, x2-0.22], [y1, y2],
                    color=color, alpha=alpha, linewidth=0.6, zorder=1)

# Layer x positions
lx = [1.5, 3.5, 5.5, 7.5, 9.0]

# Input layer — 5 nodes
input_ys  = [1.0, 1.9, 2.9, 3.9, 4.9]
hidden1_ys = np.linspace(0.8, 5.1, 8).tolist()
hidden2_ys = np.linspace(0.8, 5.1, 8).tolist()
output_ys  = [2.2, 3.8]

draw_connections(ax, lx[0], input_ys,   lx[1], hidden1_ys, TEAL,   0.15)
draw_connections(ax, lx[1], hidden1_ys, lx[2], hidden2_ys, PURPLE, 0.12)
draw_connections(ax, lx[2], hidden2_ys, lx[3], output_ys,  AMBER,  0.2)

draw_layer(ax, lx[0], input_ys,   TEAL)
draw_layer(ax, lx[1], hidden1_ys, PURPLE)
draw_layer(ax, lx[2], hidden2_ys, PURPLE)
draw_layer(ax, lx[3], output_ys,  AMBER)

# Input labels
input_labels = ['DO Level', 'DO Trend', 'DO Average', 'Nutrient Budget', 'Time of Day']
for y, label in zip(input_ys, input_labels):
    ax.text(lx[0]-0.35, y, label, color=TEAL, fontsize=7.5,
            ha='right', va='center', fontfamily='monospace')

# Output labels
output_labels = ['LED Intensity\n(0–100%)', 'Nutrient Injection\n(0–1 ml)']
for y, label in zip(output_ys, output_labels):
    ax.text(lx[3]+0.35, y, label, color=AMBER, fontsize=7.5,
            ha='left', va='center', fontfamily='monospace')

# Layer labels
ax.text(lx[0], 5.6, 'INPUT\n(5)', color=TEAL,   fontsize=8, ha='center', fontweight='bold')
ax.text(lx[1], 5.6, 'HIDDEN\n(64)', color=PURPLE, fontsize=8, ha='center', fontweight='bold')
ax.text(lx[2], 5.6, 'HIDDEN\n(64)', color=PURPLE, fontsize=8, ha='center', fontweight='bold')
ax.text(lx[3], 5.6, 'OUTPUT\n(2)', color=AMBER,  fontsize=8, ha='center', fontweight='bold')

ax.set_title('PPO Policy Network Architecture  ·  MLP  ·  ReLU activations',
             color='white', fontsize=11, fontweight='bold', pad=10)

# Tanh note on output
ax.text(lx[3], 0.3, 'Tanh + rescale', color='#64748b', fontsize=7, ha='center')

plt.tight_layout()
plt.savefig(os.path.join(out_dir, 'nn_diagram.png'), dpi=200,
            bbox_inches='tight', facecolor='#0f1117')
plt.close()
print("NN diagram saved")