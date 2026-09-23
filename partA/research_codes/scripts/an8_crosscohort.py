"""
AN-8: Cross-cohort summary (森林图数据 + 各主分析/敏感性对比)
Combines main Cox M3 + SEN-1/2/3 + SEN-4 MICE for high/low eCRF per cohort.
Output: an8_crosscohort_summary.md + an8_forest.png
"""
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = str(Path(__file__).resolve().parents[1] / "output")
plt.rcParams["font.sans-serif"] = ["SimHei","DejaVu Sans","Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False

rows = []
# main Cox M3 from an2_cox.csv
main = pd.read_csv(OUT + r"\an2_cox.csv")
for co in ["CHARLS","ELSA","HRS"]:
    for term,lab in [("group_mid","mid"),("group_high","high")]:
        r = main[(main["cohort"]==co)&(main["model"]=="M3")&(main["term"]==term)]
        if len(r):
            r=r.iloc[0]
            rows.append({"analysis":"主分析M3","cohort":co,"term":lab,"HR":r["exp(coef)"],
                         "lo":r["exp(coef) lower 95%"],"hi":r["exp(coef) upper 95%"],"p":r["p"]})
# sensitivity
s = pd.read_csv(OUT + r"\an7_sensitivity123.csv")
for _,r in s.iterrows():
    rows.append({"analysis":r["analysis"],"cohort":r["cohort"],"term":r["term"],
                 "HR":r["HR"],"lo":r["lo"],"hi":r["hi"],"p":r["p"]})
# MICE
mi = pd.read_csv(OUT + r"\an7_mice_results.csv")
for _,r in mi.iterrows():
    term = "high" if "高" in str(r["term"]) else ("mid" if "中" in str(r["term"]) else r["term"])
    rows.append({"analysis":"SEN-4 MICE","cohort":r["cohort"],"term":term,
                 "HR":r["HR"],"lo":r["lo"],"hi":r["hi"],"p":r["p"]})
res = pd.DataFrame(rows)
res.to_csv(OUT + r"\an8_crosscohort_summary.csv", index=False, encoding="utf-8-sig")

# text summary
rep = ["# AN-8 跨库汇总（高/中 eCRF vs 低，各分析）", ""]
for an in res["analysis"].unique():
    rep.append(f"## {an}")
    for co in ["CHARLS","ELSA","HRS"]:
        sub = res[(res["analysis"]==an)&(res["cohort"]==co)&(res["term"]=="high")]
        if len(sub):
            r=sub.iloc[0]
            rep.append(f"- {co} 高 vs 低: HR {r['HR']:.3f} ({r['lo']:.3f}-{r['hi']:.3f}), p={r['p']:.4f}")
    rep.append("")
with open(OUT + r"\an8_crosscohort_summary.md","w",encoding="utf-8") as f:
    f.write("\n".join(rep))

# forest plot (high vs low across analyses/cohorts)
fig, ax = plt.subplots(figsize=(9, 8))
an_list = ["主分析M3","SEN-1","SEN-2","SEN-3","SEN-4 MICE"]
y = 0; yticks=[]; ylabels=[]
colors={"CHARLS":"tab:red","ELSA":"tab:blue","HRS":"tab:green"}
for an in an_list:
    for co in ["CHARLS","ELSA","HRS"]:
        sub = res[(res["analysis"]==an)&(res["cohort"]==co)&(res["term"]=="high")]
        if len(sub):
            r=sub.iloc[0]
            ax.errorbar(r["HR"], y, xerr=[[r["HR"]-r["lo"]],[r["hi"]-r["HR"]]],
                        fmt="o", color=colors[co], capsize=3, ms=5)
            yticks.append(y); ylabels.append(f"{co}")
            y += 1
    y += 1
ax.axvline(1.0, color="grey", ls="--", lw=1)
ax.set_yticks(yticks); ax.set_yticklabels(ylabels, fontsize=8)
ax.invert_yaxis()
ax.set_xlabel("HR (high vs low eCRF), 95% CI")
ax.set_title("敏感性分析汇总：高 vs 低 eCRF（森林图）")
fig.tight_layout(); fig.savefig(OUT + r"\an8_forest.png", dpi=150)
print("\n".join(rep))
print("saved an8_crosscohort_summary.csv / an8_forest.png")