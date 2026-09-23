"""
AN-12b4: CHARLS subgroup forest plot (layout v4, final-candidate)
Fixes:
  1. Fixed uniform row spacing: each subgroup gets ONE header row + stratum rows; every row
     is exactly 1.0 unit tall in a shared y-grid -> no uneven gaps.
  2. P value column removed; only P-interaction shown (one per subgroup, on its header row).
  3. Forest x-tick labels plain (no scientific notation), slim set: 0.2, 0.5, 1.0, 2.0.
Columns: Subgroups | Events/n | HR (95% CI) [forest] | HR (95% CI) [text] | P-interaction
Output: an12_charls_subgroup_forest.png/.svg/.pdf
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans", "Liberation Sans"]
plt.rcParams["svg.fonttype"] = "none"

OUT = str(Path(__file__).resolve().parents[1] / "output")
df = pd.read_csv(OUT + r"\an12_charls_subgroup.csv")
rec = df.to_dict("records")

# ---- build display rows: header row per subgroup + stratum rows ----
rows_disp = []   # each: {'kind':'header'|'data','group':...,'stratum':...,'r':(rec or None),'pint':...}
pint_map = {}
for r in rec:
    g = r["subgroup"]
    if g not in pint_map:
        pint_map[g] = r.get("P-interaction display", "")
        rows_disp.append({"kind": "header", "group": g, "pint": pint_map[g]})
    rows_disp.append({"kind": "data", "group": g, "stratum": r["stratum"], "r": r})

M = len(rows_disp)
def y_of(i):            # top row index 0 -> highest y
    return M - 1 - i
TOP = M + 0.6
YLO, YHI = -0.8, M + 1.4

COL_BLUE = "#0F4D92"
COL_TXT  = "#272727"
COL_REF  = "#767676"

fig = plt.figure(figsize=(13.5, 9.5))
gs = fig.add_gridspec(1, 5, width_ratios=[4.0, 1.6, 3.2, 2.8, 1.7],
                      wspace=0.32, left=0.02, right=0.985, top=0.95, bottom=0.04)

ax_sub  = fig.add_subplot(gs[0]); ax_ev   = fig.add_subplot(gs[1])
ax_for  = fig.add_subplot(gs[2]); ax_hr   = fig.add_subplot(gs[3])
ax_pint = fig.add_subplot(gs[4])

for ax in [ax_sub, ax_ev, ax_for, ax_hr, ax_pint]:
    ax.set_ylim(YLO, YHI)
    ax.set_xlim(0, 1)
    ax.axis("off")

# headers
for ax, hdr, ha in [(ax_sub, "Subgroups", "left"),
                    (ax_ev, "Events/n", "center"),
                    (ax_for, "HR (95% CI)", "center"),
                    (ax_hr, "HR (95% CI)", "center"),
                    (ax_pint, "P-interaction", "center")]:
    x = 0.0 if ha == "left" else 0.5
    ax.text(x, TOP, hdr, ha=ha, va="center", fontsize=11, fontweight="bold", color=COL_TXT)

# rows (fixed uniform spacing because every row maps to consecutive integer y)
for i, rd in enumerate(rows_disp):
    y = y_of(i)
    if rd["kind"] == "header":
        ax_sub.text(0.0, y, rd["group"], ha="left", va="center",
                    fontsize=11.5, fontweight="bold", color=COL_TXT)
        ax_pint.text(0.5, y, str(rd["pint"]) if rd["pint"] not in ("", None) else "-",
                     ha="center", va="center", fontsize=10, color=COL_TXT)
    else:
        r = rd["r"]
        ax_sub.text(0.0, y, "  " + rd["stratum"], ha="left", va="center",
                    fontsize=10, color=COL_TXT)
        ax_ev.text(0.5, y, f"{int(r['events'])}/{int(r['n'])}", ha="center", va="center",
                   fontsize=10, color=COL_TXT)
        if not pd.isna(r["HR"]):
            ax_hr.text(0.5, y, f"{r['HR']:.2f} ({r['lo']:.2f}, {r['hi']:.2f})",
                       ha="center", va="center", fontsize=10, color=COL_TXT)

# forest
ax_for.axis("on")
ax_for.set_xscale("log")
ax_for.set_xlim(0.1, 3.0)
ax_for.axvline(1.0, color=COL_REF, linestyle="--", lw=1.1, zorder=1)
for i, rd in enumerate(rows_disp):
    if rd["kind"] != "data" or pd.isna(rd["r"]["HR"]):
        continue
    y = y_of(i)
    hr, lo, hi = rd["r"]["HR"], max(rd["r"]["lo"], 0.1), min(rd["r"]["hi"], 3.0)
    ax_for.plot([lo, hi], [y, y], color=COL_BLUE, lw=2.0, zorder=2)
    ax_for.plot(hr, y, marker="o", ms=6, color=COL_BLUE, zorder=3)
ax_for.set_yticks(list(range(M))[::-1])
ax_for.set_yticklabels([""] * M)
# plain tick labels, no scientific notation, no auto minor ticks overlap
ax_for.minorticks_off()
from matplotlib.ticker import ScalarFormatter
fmt = ScalarFormatter(useOffset=False)
fmt.set_scientific(False)
ax_for.xaxis.set_major_formatter(fmt)
for lbl in ["0.2", "0.5", "1.0", "2.0"]:
    pass
ax_for.set_xticks([0.2, 0.5, 1.0, 2.0])
ax_for.set_xticklabels(["0.2", "0.5", "1.0", "2.0"], fontsize=9)
ax_for.tick_params(axis="y", length=0)
for sp in ["top", "right", "left"]:
    ax_for.spines[sp].set_visible(False)

for ext in ["png", "svg", "pdf"]:
    fig.savefig(OUT + rf"\an12_charls_subgroup_forest.{ext}", dpi=300, bbox_inches="tight")
plt.close(fig)
print("saved (v4) an12_charls_subgroup_forest.png/svg/pdf")