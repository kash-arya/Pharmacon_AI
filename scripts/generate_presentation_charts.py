#!/usr/bin/env python3
"""
Generate presentation-quality charts from cohort scaling history.
Outputs 300 DPI PNG figures into phase_reports/figures/ for PPTX slides.
"""

import os, sys, json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_PATH = os.path.join(REPO_ROOT, "phase_reports", "cohort_visualization_data.json")
FIG_DIR   = os.path.join(REPO_ROOT, "phase_reports", "figures")
os.makedirs(FIG_DIR, exist_ok=True)

with open(DATA_PATH) as f:
    data = json.load(f)["scaling_trajectory"]

cohorts = [d["cohort_label"] for d in data]
val_losses = [d["best_val_loss"] for d in data]
train_losses = [d["final_train_loss"] for d in data]
cer_generic = [d["generic_macro_cer"] for d in data]
cer_adapted = [d["adapted_macro_cer"] for d in data]
confirmed_pct = [d["safety_gate"]["confirmation_rate_pct"] for d in data]

plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
fig_dpi = 300

# 1. Loss Scaling Curve
plt.figure(figsize=(7, 4.5))
plt.plot(cohorts, val_losses, marker='o', linewidth=2.5, markersize=8, color='#d9534f', label='Best Validation Loss (Sealed Lines)')
plt.plot(cohorts, train_losses, marker='s', linewidth=2.0, markersize=7, color='#0275d8', linestyle='--', label='Final Training Loss')
for i, (v, t) in enumerate(zip(val_losses, train_losses)):
    plt.annotate(f"{v:.4f}", (i, v), textcoords="offset points", xytext=(0, 10), ha='center', fontweight='bold', color='#d9534f')
plt.title("Pharmacon Multi-Writer Loss Scaling Curve (N=1 to N=4)", fontsize=13, fontweight='bold', pad=12)
plt.xlabel("Cohort Size (Number of Writers)", fontsize=11, labelpad=8)
plt.ylabel("Cross-Entropy Loss", fontsize=11, labelpad=8)
plt.ylim(5.5, 8.0)
plt.legend(frameon=True, loc='upper right')
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "01_loss_scaling_curve.png"), dpi=fig_dpi)
plt.close()

# 2. CER Reduction Trajectory
fig, ax1 = plt.subplots(figsize=(7.5, 4.5))
x = range(len(cohorts))
width = 0.35
ax1.bar([i - width/2 for i in x], cer_generic, width, label='Generic Baseline CER', color='#adb5bd', edgecolor='#6c757d')
rects2 = ax1.bar([i + width/2 for i in x], cer_adapted, width, label='Adapted LoRA CER', color='#28a745', edgecolor='#1e7e34')
for r in rects2:
    h = r.get_height()
    ax1.annotate(f"{h:.4f}", (r.get_x() + r.get_width()/2, h), textcoords="offset points", xytext=(0, 4), ha='center', fontsize=9, fontweight='bold', color='#1e7e34')
ax1.set_ylabel("Macro Character Error Rate (CER)", fontsize=11)
ax1.set_xticks(x)
ax1.set_xticklabels(cohorts)
ax1.set_ylim(0, 1.45)
ax1.set_title("Generic vs Adapted Macro CER Reduction across Cohort Sizes", fontsize=12, fontweight='bold', pad=12)
ax1.axhline(0.80, color='red', linestyle=':', linewidth=1.5, label='0.80 Target Barrier')
ax1.legend(frameon=True, loc='upper right')
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "02_cer_reduction_trajectory.png"), dpi=fig_dpi)
plt.close()

# 3. Clinical Safety Gate Progression
plt.figure(figsize=(7, 4.5))
colors = ['#6c757d' if p < 10 else ('#17a2b8' if p < 40 else '#28a745') for p in confirmed_pct]
bars = plt.bar(cohorts, confirmed_pct, color=colors, edgecolor='#343a40', width=0.55)
for b in bars:
    h = b.get_height()
    plt.annotate(f"{h:.1f}%", (b.get_x() + b.get_width()/2, h), textcoords="offset points", xytext=(0, 6), ha='center', fontweight='bold', fontsize=10)
plt.title("Clinical Gate Promotion Rate (Abstain -> Confirmed Match)", fontsize=12, fontweight='bold', pad=12)
plt.ylabel("Lines Crossing Safety Gate (Threshold >= 0.60)", fontsize=11)
plt.xlabel("Cohort Expansion", fontsize=11, labelpad=8)
plt.ylim(0, max(confirmed_pct) * 1.25)
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "03_clinical_gate_progression.png"), dpi=fig_dpi)
plt.close()

# 4. Writer W01 Peer-Regularization Curve
w1_cers = [d["per_writer_adapted_cer"].get("W01") for d in data if "W01" in d["per_writer_adapted_cer"]]
plt.figure(figsize=(7, 4.2))
plt.plot(cohorts[:len(w1_cers)], w1_cers, marker='D', linewidth=2.5, markersize=8, color='#6f42c1', label='Writer W01 Adapted CER')
for i, c in enumerate(w1_cers):
    plt.annotate(f"{c:.4f}", (i, c), textcoords="offset points", xytext=(0, 10), ha='center', fontweight='bold', color='#6f42c1')
plt.title("Peer Regularization Effect: Writer W01 CER vs Cohort Scale", fontsize=12, fontweight='bold', pad=12)
plt.xlabel("Cohort Scale (Added Peer Handwritings)", fontsize=11, labelpad=8)
plt.ylabel("Writer W01 CER", fontsize=11)
plt.ylim(min(w1_cers) - 0.05, max(w1_cers) + 0.05)
plt.axhline(w1_cers[0], color='gray', linestyle='--', label=f'W01 Solo Model ({w1_cers[0]:.4f})')
plt.legend(frameon=True, loc='upper right')
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "04_w01_peer_regularization.png"), dpi=fig_dpi)
plt.close()

print(f"Generated 4 figures in: {FIG_DIR}")
