"""Charts for the README."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import fpa

ROOT = Path(__file__).resolve().parents[1]
CH = ROOT / "outputs" / "charts"; CH.mkdir(parents=True, exist_ok=True)
NAVY, TEAL, PINK, GREY, AMBER = "#1f3864", "#10b981", "#f43f5e", "#9aa5b1", "#f59e0b"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 150})

d, t, mvr, pv, p, oo, sc, _ = fpa.run()


def waterfall(ax, start_label, start, steps, end_label, title):
    labels = [start_label] + [s[0] for s in steps] + [end_label]
    run = start; xs = 0
    ax.bar(xs, start / 1000, color=NAVY); ax.text(xs, start / 1000, f"{start / 1000:,.0f}", ha="center", va="bottom", fontsize=8)
    for i, (lab, v) in enumerate(steps, start=1):
        bottom = run if v >= 0 else run + v
        ax.bar(i, abs(v) / 1000, bottom=bottom / 1000, color=TEAL if v >= 0 else PINK)
        ax.text(i, (run + max(v, 0)) / 1000, f"{v / 1000:+,.1f}", ha="center", va="bottom", fontsize=8)
        run += v
    ax.bar(len(steps) + 1, run / 1000, color=NAVY); ax.text(len(steps) + 1, run / 1000, f"{run / 1000:,.0f}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(range(len(labels)), labels, rotation=20, ha="right", fontsize=8)
    lo = min(start, run) / 1000
    ax.set_ylim(lo * 0.9, max(start, run) / 1000 * 1.04)
    ax.set_ylabel("AED m"); ax.set_title(title)


seg = t.set_index("segment")
fig, axes = plt.subplots(1, 2, figsize=(13, 4.6))
waterfall(axes[0], "FY2024", seg.rev_24.sum(), [(s, seg.loc[s, "rev_change"]) for s in seg.index], "FY2025", "Revenue bridge (AED m)")
steps = []
SHORT = {"International Express": "Intl Exp", "Domestic Express": "Dom Exp", "Freight Forwarding": "Freight", "Logistics": "Logistics"}
for s in fpa.SEGMENTS:
    steps.append((f"{SHORT[s]} vol", seg.loc[s, "gp_volume_effect"]))
    steps.append((f"{SHORT[s]} margin", seg.loc[s, "gp_margin_effect"]))
steps.append(("Other", seg.loc["Other / eliminations", "gp_change"]))
waterfall(axes[1], "FY2024", seg.gp_24.sum(), steps, "FY2025", "Gross-profit bridge: volume vs margin effects (AED m)")
axes[1].tick_params(axis="x", labelsize=7.5)
fig.tight_layout(); fig.savefig(CH / "01_bridges.png"); plt.close(fig)

s4 = t[t.segment != "Other / eliminations"]
fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
x = range(len(s4)); w = 0.38
axes[0].bar([i - w / 2 for i in x], s4.share_24_pct, w, color=GREY, label="FY2024")
axes[0].bar([i + w / 2 for i in x], s4.share_25_pct, w, color=TEAL, label="FY2025")
axes[0].set_xticks(list(x), s4.segment, fontsize=8); axes[0].set_ylabel("% of revenue"); axes[0].set_title("Revenue mix shift"); axes[0].legend(frameon=False)
axes[1].bar([i - w / 2 for i in x], s4.gm_24_pct, w, color=GREY, label="FY2024")
axes[1].bar([i + w / 2 for i in x], s4.gm_25_pct, w, color=NAVY, label="FY2025")
for i, (a, b) in enumerate(zip(s4.gm_24_pct, s4.gm_25_pct)):
    axes[1].text(i + w / 2, b + 0.5, f"{b:.1f}%", ha="center", fontsize=8)
axes[1].set_xticks(list(x), s4.segment, fontsize=8); axes[1].set_ylabel("Gross margin %"); axes[1].set_title("Gross margin by product"); axes[1].legend(frameon=False)
fig.tight_layout(); fig.savefig(CH / "02_mix_and_margins.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(7, 4))
cols = [PINK, NAVY, TEAL]
bars = ax.bar(sc.scenario, sc.normalized_ebit / 1000, color=cols)
ax.axhline(fpa.get(d, "Group", "normalized_ebit") / 1000, color=GREY, ls="--", label="FY2025 actual")
for b_, v, mgn in zip(bars, sc.normalized_ebit, sc.ebit_margin_pct):
    ax.text(b_.get_x() + b_.get_width() / 2, v / 1000 + 4, f"{v / 1000:,.0f}m ({mgn:.1f}%)", ha="center", fontsize=9)
ax.set_ylabel("Normalized EBIT, AED m"); ax.set_title("2026 scenarios (illustrative drivers)"); ax.legend(frameon=False)
fig.tight_layout(); fig.savefig(CH / "03_scenarios.png"); plt.close(fig)
print("charts:", sorted(p_.name for p_ in CH.glob("*.png")))
