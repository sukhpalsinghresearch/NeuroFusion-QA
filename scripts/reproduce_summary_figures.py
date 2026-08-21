"""Create an aggregate model-profile figure without opening subject-level data."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "results" / "frozen_summary.json"
OUTPUT = ROOT / "outputs" / "model_profile"


def main() -> None:
    payload = json.loads(SUMMARY.read_text(encoding="utf-8"))
    if payload.get("scope") != "development_only" or payload.get("protected_access_count") != 0:
        raise RuntimeError("aggregate release boundary is not satisfied")

    models = payload["models"]
    labels = ["Prevalence", "EEG", "fMRI", "Equal", "Quality gate", "Meta gate"]
    keys = ["prevalence", "eeg", "fmri", "equal_fusion", "quality_gate", "meta_gate"]
    auc = [models[key]["roc_auc"] for key in keys]
    ap = [models[key]["average_precision"] for key in keys]

    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
        "font.size": 10,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })
    fig, ax = plt.subplots(figsize=(7.2, 3.8), constrained_layout=True)
    y = range(len(labels))
    ax.scatter(auc, y, s=55, label="ROC AUC")
    ax.scatter(ap, y, s=55, marker="s", facecolors="none", label="Average precision")
    for row, (left, right) in enumerate(zip(auc, ap)):
        ax.plot([left, right], [row, row], color="#C7CED6", linewidth=1.2, zorder=0)
    ax.set_yticks(list(y), labels)
    ax.invert_yaxis()
    ax.set_xlabel("Score (higher is better)")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", color="#E5E7EB", linewidth=0.8)
    ax.legend(frameon=False, ncol=2, loc="lower center", bbox_to_anchor=(0.5, 1.0))

    OUTPUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT / "model_profile.pdf", bbox_inches="tight")
    fig.savefig(OUTPUT / "model_profile.svg", bbox_inches="tight")
    fig.savefig(OUTPUT / "model_profile.png", dpi=450, bbox_inches="tight")
    fig.savefig(OUTPUT / "model_profile.tiff", dpi=600, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
