"""
AN-12 combo v4: three-cohort subgroup forest plot side-by-side.
Layout (per user):
  - Leftmost single column: Subgroups (only once).
  - Then 3 identical cohort blocks: | Events/n | [COHORT forest] | HR (95% CI) | P-interaction |
  - Cohort name (black, bold, uppercase) centered directly above the HR=1 reference line of its forest.
  - P-interaction spelled out. Tight gaps between Subgroups and Events/n; forests slightly compact.
  - Each cohort has its OWN Events/n column (fixed: previously only CHARLS showed counts).
Output: an12_forest_3cohorts.png/svg/pdf
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans", "Liberation Sans"]
plt.rcParams["svg.fonttype"] = "none"

OUT = str(Path(__file__).resolve().parents[1] / "output")
COHORTS = ["CHARLS", "HRS", "ELSA"]

def load(cohort):
    return pd.read_csv(OUT + rf"\an12_{cohort}_subgroup.csv").to_dict("records")

DATA = {c: load(c) for c in COHORTS}
rec0 = DATA["CHARLS"]

rows_disp = []
pint_map = {}
for r in rec0:
    g = r["subgroup"]
    if g not in pint_map:
        pint_map[g] = r.get("P-interaction display", "")
        rows_disp.append({"kind": "header", "group": g, "pint": pint_map[g]})
    rows_disp.append({"kind": "data", "group": g, "stratum": r["stratum"]})
M = len(rows_disp)
REC = {c: {(r["subgroup"], r["stratum"]): r for r in DATA[c]} for c in COHORTS}

def y_of(i):
    return M - 1 - i

TOP = M + 1.2
YLO, YHI = -0.8, M + 2.2

COL_TXT  = "#272727"
COL_REF  = "#767676"
COL_POINT = "#0F4D92"

fig_h = 2.4 + M * 0.40
fig = plt.figure(figsize=(16.5, fig_h))

# --- column plan: Sub | [Ev, forest, HR, Pint] x3 ---
w_sub = 4.2
w_ev  = 1.4
w_for = 3.1
w_hr  = 3.0
w_pin = 1.9
gap_main = 0.30          # between column groups
gap_in   = 0.18          # gap between Sub and first Events (smaller)

left_m, right_m, top_m, bot_m = 0.01, 0.99, 0.94, 0.05
avail = right_m - left_m
base_w = (w_sub + (w_ev + w_for + w_hr + w_pin) * 3)
# gaps: after sub=1*gap_in; after each ev=3*gap_main; after for/hr/pin=9*gap_in
total_gap = gap_in + 3*gap_main + 9*gap_in
total = base_w + total_gap
unit_w = avail / total

order = ["sub"] + [f"{pref}_{c}" for c in COHORTS for pref in ["ev", "for", "hr", "pin"]]
def wid(k):
    pre = k.split("_")[0]
    return {"sub": w_sub, "ev": w_ev, "for": w_for, "hr": w_hr, "pin": w_pin}[pre]
def gap_before(k):
    if k == "sub":
        return 0.0
    pre = k.split("_")[0]
    if pre == "ev":
        return gap_in   # tight before Events
    if pre == "for":
        return gap_main
    return gap_in

pos = {}
x = left_m
for k in order:
    pos[k] = (x, wid(k) * unit_w)
    # advance with the gap that precedes the NEXT column
    if k == "sub":
        x += wid(k) * unit_w + gap_in          # tight gap before first Events
    elif k.startswith("ev_"):
        x += wid(k) * unit_w + gap_main        # gap before next cohort's forest block
    elif k.startswith("for_"):
        x += wid(k) * unit_w + gap_in
    elif k.startswith("hr_"):
        x += wid(k) * unit_w + gap_in
    elif k.startswith("pin_"):
        x += wid(k) * unit_w + gap_main

def make_ax(x, w):
    return fig.add_axes([x, bot_m, w, top_m - bot_m])

ax_sub = make_ax(*pos["sub"])
f_ax = {}; h_ax = {}; p_ax = {}; e_ax = {}
for c in COHORTS:
    e_ax[c] = make_ax(*pos[f"ev_{c}"])
    f_ax[c] = make_ax(*pos[f"for_{c}"])
    h_ax[c] = make_ax(*pos[f"hr_{c}"])
    p_ax[c] = make_ax(*pos[f"pin_{c}"])

for ax in [ax_sub] + list(e_ax.values()) + list(f_ax.values()) + list(h_ax.values()) + list(p_ax.values()):
    ax.set_ylim(YLO, YHI)
    ax.set_xlim(0, 1)
    ax.axis("off")

# ---------- headers ----------
ax_sub.text(0.0, TOP, "Subgroups", ha="left", va="center", fontsize=10.5, fontweight="bold", color=COL_TXT)
for c in COHORTS:
    e_ax[c].text(0.5, TOP, "Events/n", ha="center", va="center", fontsize=10.5, fontweight="bold", color=COL_TXT)
    h_ax[c].text(0.5, TOP, "HR (95% CI)", ha="center", va="center", fontsize=10.5, fontweight="bold", color=COL_TXT)
    p_ax[c].text(0.5, TOP, "P-interaction", ha="center", va="center", fontsize=10.5, fontweight="bold", color=COL_TXT)

# ---------- rows ----------
for i, rd in enumerate(rows_disp):
    y = y_of(i)
    if rd["kind"] == "header":
        ax_sub.text(0.0, y, rd["group"], ha="left", va="center",
                    fontsize=11, fontweight="bold", color=COL_TXT)
        for c in COHORTS:
            pv = rd["pint"]
            p_ax[c].text(0.5, y, str(pv) if pv not in ("", None) else "-",
                         ha="center", va="center", fontsize=10, color=COL_TXT)
    else:
        ax_sub.text(0.0, y, "  " + rd["stratum"], ha="left", va="center", fontsize=9.5, color=COL_TXT)
        for c in COHORTS:
            r = REC[c].get((rd["group"], rd["stratum"]))
            if r is not None:
                e_ax[c].text(0.5, y, f"{int(r['events'])}/{int(r['n'])}",
                             ha="center", va="center", fontsize=9.5, color=COL_TXT)
            if r is not None and not pd.isna(r["HR"]):
                h_ax[c].text(0.5, y, f"{r['HR']:.2f} ({r['lo']:.2f}, {r['hi']:.2f})",
                             ha="center", va="center", fontsize=9.5, color=COL_TXT)

# ---------- forest panels ----------
for c in COHORTS:
    fa = f_ax[c]
    fa.set_xlim(np.log(0.1), np.log(3.0))
    fa.axvline(np.log(1.0), color=COL_REF, linestyle="--", lw=1.0, zorder=1)
    for rd in rows_disp:
        if rd["kind"] != "data":
            continue
        r = REC[c].get((rd["group"], rd["stratum"]))
        if r is None or pd.isna(r["HR"]):
            continue
        i_ = rows_disp.index(rd)
        y = y_of(i_)
        hr, lo, hi = r["HR"], max(r["lo"], 0.1), min(r["hi"], 3.0)
        fa.plot([np.log(lo), np.log(hi)], [y, y], color=COL_POINT, lw=2.0, zorder=2)
        fa.plot(np.log(hr), y, marker="o", ms=5, color=COL_POINT, zorder=3)
    fa.minorticks_off()
    fa.set_xticks([np.log(0.2), np.log(0.5), np.log(1.0), np.log(2.0)])
    fa.set_xticklabels(["0.2", "0.5", "1.0", "2.0"], fontsize=8)
    fa.tick_params(axis="y", left=False, labelleft=False)
    fa.tick_params(axis="x", labelsize=8)
    fa.spines["top"].set_visible(False)
    fa.spines["right"].set_visible(False)

    # cohort name (black bold) centered above the HR=1 line (log(1)=0), in data coords
    fa.text(np.log(1.0), TOP, c, ha="center", va="center",
            fontsize=13, fontweight="bold", color="#000000")

for ext in ["png", "svg", "pdf"]:
    fig.savefig(OUT + rf"\an12_forest_3cohorts.{ext}", dpi=200, bbox_inches=None)
plt.close(fig)
print("saved (v4) an12_forest_3cohorts.png/svg/pdf")