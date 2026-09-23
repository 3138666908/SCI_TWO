"""p5_step09_flowchart.py —— PartB ML 分析流程图（示意型，论文用；双栏 183 mm）"""
from pathlib import Path
import os
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
    "svg.fonttype": "none", "pdf.fonttype": 42, "font.size": 7,
})
FIG = str(Path(__file__).resolve().parents[2] / "figures")
os.makedirs(FIG, exist_ok=True)

C_IN = "#F7C9A6"; C_PROC = "#FBE7A5"; C_KEY = "#CFE6C9"
C_DATA = "#F6D3B0"; C_ML = "#BFD7EA"; C_MET = "#DADADA"
EC = "#5A5A5A"

fig, ax = plt.subplots(figsize=(7.2, 4.3))
ax.set_xlim(0, 100); ax.set_ylim(0, 60); ax.axis("off")


def box(x, y, w, h, text, fc, fs=5.9, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.4",
                                linewidth=0.9, edgecolor=EC, facecolor=fc))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, fontweight="bold" if bold else "normal", linespacing=1.4)


def arrow(x1, y1, x2, y2):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", lw=1.0, color="#3A3A3A"))


# top branch: predictor
box(2, 47, 18, 9, "Baseline population\nvariables (2011)", C_IN)
box(23, 48.5, 12, 6, "Data cleaning", C_PROC)
box(38, 47, 18, 9, "Predictor:\nbaseline eCRF", C_KEY, bold=True)

# bottom branch: outcome
box(2, 12, 18, 9, "Mobility limitation\nper wave (0–7)", C_IN)
box(23, 13.5, 12, 6, "LCGM → GMM*", C_PROC)
box(38, 12, 18, 9, "Mobility limitation\ntrajectory classes", C_KEY, bold=True)

# merge
box(60, 25, 15, 10, "Analysis dataset\n(eCRF + class)", C_DATA)
box(79, 26.5, 14, 7, "70% / 30%\nstratified split", C_DATA)

# ML
box(79, 40, 19, 8, "Training (70%):\nRandom Forest", C_ML)
box(79, 15, 19, 8, "Testing (30%):\napply model", C_ML)
box(79, 2, 19, 9, "Metrics: Accuracy,\nAUC, Sensitivity, PPV", C_MET)

# arrows
arrow(20, 51.5, 23, 51.5)
arrow(35, 51.5, 38, 51.5)
arrow(20, 16.5, 23, 16.5)
arrow(35, 16.5, 38, 16.5)
arrow(47, 47, 62, 35)
arrow(47, 21, 62, 25)
arrow(75, 30, 79, 30)
arrow(82, 33.5, 82, 40)          # split -> train
arrow(80.5, 26.5, 80.5, 23)      # split -> test
arrow(96, 40, 96, 23)            # trained model -> test
arrow(88.5, 15, 88.5, 11)        # test -> metrics

ax.text(2, 58, "PartB machine-learning flow: baseline eCRF → incident mobility-limitation trajectory class",
        fontsize=8.2, fontweight="bold")

note = (
    "*LCGM/GMM fitted for class enumeration; GMM gave\n"
    "non-positive-definite (Heywood/boundary) solutions,\n"
    "so LCGA was retained (CHARLS 3 / ELSA 3 / HRS 2 classes).\n"
    "Trajectory built on the 70% training set only; the 30%\n"
    "test set was assigned by posterior probabilities (no leakage).\n"
    "A single model (Random Forest) suffices for a single\n"
    "continuous predictor (eCRF); no 1000× repetition was done."
)
ax.text(2, 8.5, note, fontsize=5.0, color="#4A4A4A", va="top", linespacing=1.35)

B = os.path.join(FIG, "p5_ml_flowchart")
fig.savefig(B + ".png", dpi=300, bbox_inches="tight")
fig.savefig(B + ".tiff", dpi=600, bbox_inches="tight")
fig.savefig(B + ".svg", bbox_inches="tight")
fig.savefig(B + ".pdf", bbox_inches="tight")
print("saved", B + ".png")
