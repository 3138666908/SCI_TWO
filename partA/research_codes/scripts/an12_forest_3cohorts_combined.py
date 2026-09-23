"""
AN-12 combined subgroup forest plot (CHARLS / HRS / ELSA side by side).

Layout:
  Subgroups (kept ONCE) | [ Events/n | HR(95%CI) forest | HR(95%CI) text | P-interaction ] x3

Reads : figures/an12_<COHORT>_subgroup.csv
Writes: figures/an12_subgroup_forest_3cohorts.png/.svg/.pdf
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Rectangle
from matplotlib.ticker import FixedLocator, FuncFormatter, NullFormatter

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Arial", "Helvetica", "DejaVu Sans", "Liberation Sans"]
plt.rcParams["svg.fonttype"] = "none"

FIGDIR = str(Path(__file__).resolve().parents[1] / "figures")
COHORTS = ["CHARLS", "HRS", "ELSA"]

COL_TXT  = "#272727"
COL_HEAD = "#111111"
COL_BLUE = "#0F4D92"
COL_REF  = "#767676"
COL_SEP  = "#D9D9D9"
COL_BAND = "#F2F5F8"

DATA = {c: pd.read_csv(rf"{FIGDIR}\an12_{c}_subgroup.csv",
                       dtype={"P-interaction display": "string"}).to_dict("records") for c in COHORTS}

rows, seen = [], set()
for r in DATA[COHORTS[0]]:
    g = r["subgroup"]
    if g not in seen:
        seen.add(g)
        rows.append({"kind": "header", "group": g})
    rows.append({"kind": "data", "group": g, "stratum": r["stratum"]})
N = len(rows)
REC = {c: {(r["subgroup"], r["stratum"]): r for r in DATA[c]} for c in COHORTS}

PINT = {}
for c in COHORTS:
    m = {}
    for r in DATA[c]:
        pv = r.get("P-interaction display", "")
        if r["subgroup"] not in m and pd.notna(pv) and str(pv) != "":
            m[r["subgroup"]] = pv
    PINT[c] = m

ROW_H, BOT, TOP_PAD = 0.28, 0.44, 0.82
H_HDR, GAP_G = ROW_H * 1.45, ROW_H * 0.55
XMIN, XMAX = 0.08, 4.6


def row_h(rd):
    return H_HDR if rd["kind"] == "header" else ROW_H


offset, tops = [], []
acc = 0.0
for i, rd in enumerate(rows):
    if i > 0 and rd["kind"] == "header":
        acc += GAP_G
    tops.append(acc)
    offset.append(acc + row_h(rd) / 2)
    acc += row_h(rd)
H_DATA = acc
H = BOT + H_DATA + TOP_PAD
TOP_DATA = BOT + H_DATA


def y_inch(i):
    return TOP_DATA - offset[i]


LM, RM = 0.14, 0.14
w_sub, w_ev, w_for, w_hr, w_pin = 2.35, 1.10, 2.05, 1.90, 0.95
g_in, g_blk = 0.09, 0.45

pos, x = {}, LM
pos["sub"] = (x, w_sub)
x += w_sub + g_in
for bi, c in enumerate(COHORTS):
    if bi > 0:
        x += g_blk
    for pre, w in [("ev", w_ev), ("for", w_for), ("hr", w_hr), ("pin", w_pin)]:
        pos[f"{pre}_{c}"] = (x, w)
        x += w + (g_blk if pre == "pin" else g_in)
W = x - g_blk + RM
W_L, W_R = LM, W - RM

fig = plt.figure(figsize=(W, H), facecolor="white")
bg = fig.add_axes([0, 0, 1, 1], zorder=0)
bg.set_xlim(0, W)
bg.set_ylim(0, H)
bg.axis("off")

axt = {"sub": fig.add_axes([pos["sub"][0] / W, 0, w_sub / W, 1], zorder=2)}
axf = {}
for c in COHORTS:
    for pre, w in [("ev", w_ev), ("hr", w_hr), ("pin", w_pin)]:
        axt[f"{pre}_{c}"] = fig.add_axes([pos[f"{pre}_{c}"][0] / W, 0, w / W, 1], zorder=2)
    axf[c] = fig.add_axes([pos[f"for_{c}"][0] / W, BOT / H, w_for / W, H_DATA / H], zorder=2)

for ax in axt.values():
    ax.set_ylim(0, H)
    ax.set_xlim(0, 1)
    ax.axis("off")


def xc(pre, c):
    return pos[f"{pre}_{c}"][0] + pos[f"{pre}_{c}"][1] / 2


grp_idx = [i for i, r in enumerate(rows) if r["kind"] == "header"]
grp_span = [(i, grp_idx[k + 1] - 1 if k + 1 < len(grp_idx) else N - 1) for k, i in enumerate(grp_idx)]
for k, (i0, i1) in enumerate(grp_span):
    if k % 2 == 1:
        ytop = y_inch(i0) + row_h(rows[i0]) / 2 + GAP_G
        ybot = y_inch(i1) - row_h(rows[i1]) / 2
        bg.add_patch(Rectangle((W_L, ybot), W_R - W_L, ytop - ybot,
                               facecolor=COL_BAND, edgecolor="none", zorder=0))

for c in COHORTS[:-1]:
    xs = pos[f"pin_{c}"][0] + w_pin + g_blk / 2
    bg.plot([xs, xs], [BOT - 0.10, TOP_DATA + 0.06], color=COL_SEP, lw=0.8, zorder=1)

y_subhead = TOP_DATA + 0.38

bg.text(pos["sub"][0], y_subhead, "Subgroups", ha="left", va="center",
        fontsize=10, fontweight="bold", color=COL_HEAD)
for c in COHORTS:
    fa = axf[c]
    fa.set_xscale("log")
    fa.set_xlim(XMIN, XMAX)
    fa.set_ylim(BOT, TOP_DATA)
    fa.axvline(1.0, color=COL_REF, ls="--", lw=1.0, zorder=1)
    fa.minorticks_off()
    fa.xaxis.set_major_locator(FixedLocator([0.2, 0.5, 1.0, 2.0, 4.0]))
    fa.xaxis.set_major_formatter(FuncFormatter(lambda v, p: f"{v:g}"))
    fa.xaxis.set_minor_formatter(NullFormatter())
    fa.set_xticklabels(["0.2", "0.5", "1.0", "2.0", "4.0"], fontsize=7.5)
    fa.tick_params(axis="x", length=3, width=0.8, color=COL_REF, pad=2)
    fa.tick_params(axis="y", left=False, labelleft=False)
    for sp in ["top", "right", "left"]:
        fa.spines[sp].set_visible(False)
    fa.spines["bottom"].set_color(COL_REF)
    fa.spines["bottom"].set_linewidth(0.8)
    bg.text(xc("ev", c), y_subhead, "Events/n", ha="center", va="center",
            fontsize=8.8, fontweight="bold", color=COL_HEAD)
    bg.text(xc("for", c), y_subhead, c, ha="center", va="center",
            fontsize=10.5, fontweight="bold", color=COL_HEAD)
    bg.text(xc("hr", c), y_subhead, "HR (95% CI)", ha="center", va="center",
            fontsize=8.8, fontweight="bold", color=COL_HEAD)
    bg.text(xc("pin", c), y_subhead, "P-interaction", ha="center", va="center",
            fontsize=8.8, fontweight="bold", color=COL_HEAD)

for i, rd in enumerate(rows):
    y = y_inch(i)
    if rd["kind"] == "header":
        axt["sub"].text(0.0, y, rd["group"], ha="left", va="center",
                        fontsize=10, fontweight="bold", color=COL_HEAD)
        for c in COHORTS:
            pv = PINT[c].get(rd["group"], "")
            axt[f"pin_{c}"].text(0.5, y, str(pv) if pv not in ("", None) else "-",
                                 ha="center", va="center", fontsize=8.5, color=COL_TXT)
        continue
    axt["sub"].text(0.07, y, rd["stratum"], ha="left", va="center",
                    fontsize=8.5, color=COL_TXT)
    for c in COHORTS:
        r = REC[c].get((rd["group"], rd["stratum"]))
        if r is None:
            continue
        axt[f"ev_{c}"].text(0.5, y, f"{int(r['events'])}/{int(r['n'])}",
                            ha="center", va="center", fontsize=8.5, color=COL_TXT)
        if pd.isna(r["HR"]):
            continue
        axt[f"hr_{c}"].text(0.5, y, f"{r['HR']:.2f} ({r['lo']:.2f}, {r['hi']:.2f})",
                            ha="center", va="center", fontsize=8.5, color=COL_TXT)
        hr, xlo, xhi = r["HR"], r["lo"], r["hi"]
        fa = axf[c]
        fa.plot([xlo, xhi], [y, y], color=COL_BLUE, lw=1.2, solid_capstyle="butt", zorder=2)
        for xcap in (xlo, xhi):
            fa.plot([xcap, xcap], [y - ROW_H * 0.24, y + ROW_H * 0.24],
                    color=COL_BLUE, lw=1.2, solid_capstyle="butt", zorder=2)
        fa.plot(hr, y, marker="o", ms=4.6, mfc=COL_BLUE, mec=COL_BLUE, zorder=4)

for ext in ["png", "svg", "pdf"]:
    fig.savefig(rf"{FIGDIR}\an12_subgroup_forest_3cohorts.{ext}", dpi=300, facecolor="white")
plt.close(fig)
print("saved an12_subgroup_forest_3cohorts.png/.svg/.pdf")
