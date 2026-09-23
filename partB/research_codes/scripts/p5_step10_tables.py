"""p5_step10_tables.py —— 生成 LCGM/GMM 轨迹模型择优表（按给定格式）"""
from pathlib import Path
import os
import pandas as pd

OUT = str(Path(__file__).resolve().parents[1] / "output")
FORM = {"CHARLS": "lin", "ELSA": "quad", "HRS": "quad"}
df = pd.read_csv(os.path.join(OUT, "p5_mplus_results.csv"))


def pval(x):
    if pd.isna(x):
        return "-"
    return "<.001" if x < 0.001 else ("%.3f" % x).lstrip("0")


def minprop(sizes):
    if not isinstance(sizes, str) or "/" not in sizes:
        return "-"
    v = [int(x) for x in sizes.split("/")]
    return ("%.3f" % (min(v) / sum(v))).lstrip("0")


all_md = []
for coh in ["CHARLS", "ELSA", "HRS"]:
    lines = ["### %s (form=%s)" % (coh, FORM[coh]), "",
             "| 模型 | SABIC | 熵 | VLMR-LRT p值 | BLRT p值 | 最小类别 |",
             "|---|---|---|---|---|---|"]
    for cls, lab in [("lcga", "LCGM"), ("gmm", "GMM")]:
        lines.append("| **%s** |  |  |  |  |  |" % lab)
        for k in range(2, 6):
            f = "%s_%s_%s_k%d" % (cls, coh.lower(), FORM[coh], k)
            r = df[df["file"] == f]
            if len(r) == 0:
                continue
            r = r.iloc[0]
            ent = "-" if pd.isna(r["entropy"]) else ("%.3f" % r["entropy"]).lstrip("0")
            lines.append("| %s%d | %.3f | %s | %s | %s | %s |" %
                         (lab, k, r["SaBIC"], ent, pval(r["vlmr_p"]),
                          pval(r["blrt_p"]), minprop(r["sizes"])))
    lines.append("")
    all_md += lines

txt = "\n".join(all_md)
with open(os.path.join(OUT, "p5_traj_model_selection.md"), "w", encoding="utf-8") as fh:
    fh.write(txt)

# ---- CSV（合并三队列；数值+格式化两版） ----
rows = []
for coh in ["CHARLS", "ELSA", "HRS"]:
    for cls, lab in [("lcga", "LCGM"), ("gmm", "GMM")]:
        for k in range(2, 6):
            f = "%s_%s_%s_k%d" % (cls, coh.lower(), FORM[coh], k)
            r = df[df["file"] == f]
            if len(r) == 0:
                continue
            r = r.iloc[0]
            mp = None
            if isinstance(r["sizes"], str) and "/" in r["sizes"]:
                v = [int(x) for x in r["sizes"].split("/")]
                mp = min(v) / sum(v)
            rows.append({"cohort": coh, "family": lab, "model": "%s%d" % (lab, k), "k": k,
                         "SABIC": round(r["SaBIC"], 3),
                         "entropy": None if pd.isna(r["entropy"]) else round(r["entropy"], 3),
                         "VLMR_LRT_p": None if pd.isna(r["vlmr_p"]) else round(r["vlmr_p"], 4),
                         "BLRT_p": None if pd.isna(r["blrt_p"]) else round(r["blrt_p"], 4),
                         "min_class_prop": None if mp is None else round(mp, 3)})
pd.DataFrame(rows).to_csv(os.path.join(OUT, "p5_traj_model_selection.csv"),
                          index=False, encoding="utf-8-sig")
print(txt)
print("SAVED csv:", os.path.join(OUT, "p5_traj_model_selection.csv"))
print("DONE")
