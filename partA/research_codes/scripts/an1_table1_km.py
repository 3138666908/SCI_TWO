"""
AN-1: Table 1 (descriptive by eCRF group) + KM curves + log-rank, per cohort.
Analysis sample: eCRF-complete cases (ecrf_group non-missing).
Cohorts analyzed separately.
Output:
  output/an1_table1_<cohort>.csv  (descriptive by ecrf_group)
  output/an1_table1_report.md
  output/an1_km_<cohort>.png      (KM curves)
  output/an1_km_report.md         (log-rank p-values + event counts)
"""
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from lifelines import KaplanMeierFitter
from lifelines.statistics import logrank_test

OUT = str(Path(__file__).resolve().parents[1] / "output")
plt.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False

df = pd.read_csv(OUT + r"\final_analysis_pooled.csv")
df = df[df["ecrf_group"].notna()].copy()
df["ecrf_group"] = df["ecrf_group"].astype(int)
df["followup_years"] = pd.to_numeric(df["followup_years"], errors="coerce")
df["mobility_event"] = pd.to_numeric(df["mobility_event"], errors="coerce")

group_labels = {1: "Low eCRF", 2: "Middle eCRF", 3: "High eCRF"}
cohort_order = ["CHARLS", "ELSA", "HRS"]

# ---------- Table 1 ----------
tbl = []
for cohort in cohort_order:
    sub = df[df["cohort"] == cohort]
    ns = sub.groupby("ecrf_group").size()

    def cont(g, var):
        gd = pd.to_numeric(sub[sub["ecrf_group"] == g][var], errors="coerce")
        return f"{gd.mean():.2f} ± {gd.std():.2f}" if gd.notna().any() else "NA"

    def pct(g, var):
        """binary 0/1 -> n (%) sharing 'yes' among those answered"""
        gd = pd.to_numeric(sub[sub["ecrf_group"] == g][var], errors="coerce")
        denom = gd.notna().sum()
        if denom == 0:
            return "NA"
        return f"{int(gd.eq(1).sum())} ({100 * gd.eq(1).sum() / denom:.1f}%)"

    def sex_label(g):
        gd = pd.to_numeric(sub[sub["ecrf_group"] == g]["sex"], errors="coerce")
        denom = gd.notna().sum()
        male = gd.eq(1).sum() if denom else 0
        return f"Male {male} ({100*male/denom:.1f}%)" if denom else "NA"

    def educ_label(g):
        gd = pd.to_numeric(sub[sub["ecrf_group"] == g]["educ"], errors="coerce")
        d = gd.dropna()
        if not len(d):
            return "NA"
        c1 = int((d == 1).sum()); c2 = int((d == 2).sum()); c3 = int((d == 3).sum())
        return f"belowHS {c1} ({100*c1/len(d):.1f}%) / HS {c2} ({100*c2/len(d):.1f}%) / college+ {c3} ({100*c3/len(d):.1f}%)"

    rows = []
    for var, label in [("N","N"),("age","Age, years (mean±SD)"),("---","Male"),
                       ("bmi","BMI kg/m2 (mean±SD)"),("waist","Waist cm (mean±SD)"),
                       ("rhr","Resting HR bpm (mean±SD)"),("sbp","SBP mmHg (mean±SD)"),
                       ("mvpa","MVPA ≥2/wk n(%)"),("marital","Married/partnered n(%)"),
                       ("drink","Drinker n(%)"),("hibp","Hypertension n(%)"),("diab","Diabetes n(%)"),
                       ("cancer","Cancer n(%)"),("lung","Lung disease n(%)"),("heart","Heart disease n(%)"),
                       ("stroke","Stroke n(%)")]:
        if var == "N":
            vals = [str(ns.get(1, 0)), str(ns.get(2, 0)), str(ns.get(3, 0))]
        elif var == "---":
            vals = [sex_label(1), sex_label(2), sex_label(3)]
        elif var in ("bmi","waist","rhr","sbp","age"):
            vals = [cont(1, var), cont(2, var), cont(3, var)]
        else:
            vals = [pct(1, var), pct(2, var), pct(3, var)]
        rows.append({"cohort": cohort, "var": label, "Low(Q1)": vals[0], "Middle(Q2-3)": vals[1], "High(Q4-5)": vals[2]})
    tbl += rows
tbl_df = pd.DataFrame(tbl)
tbl_df.to_csv(OUT + r"\an1_table1.csv", index=False, encoding="utf-8-sig")

# ---------- KM ----------
km_report = ["# AN-1 KM + log-rank 报告（按库，eCRF 三组）", ""]
fig, axes = plt.subplots(1, 3, figsize=(18, 5))
for ax, cohort in zip(axes, cohort_order):
    sub = df[df["cohort"] == cohort]
    km_report.append(f"## {cohort}   (n={len(sub)})")
    kmf = KaplanMeierFitter()
    for g in [1, 2, 3]:
        gd = sub[sub["ecrf_group"] == g]
        T = gd["followup_years"].fillna(gd["followup_years"].max())
        E = gd["mobility_event"].fillna(0).astype(int)
        kmf.fit(T, E, label=group_labels[g])
        kmf.plot_survival_function(ax=ax)
        ev = int(E.sum())
        cens = int((E == 0).sum())
        km_report.append(f"- {group_labels[g]}: n={len(gd)}, events={ev}, censored={cens}")
    # log-rank (pairwise vs low; plus global)
    g1 = sub[sub["ecrf_group"]==1]; g2 = sub[sub["ecrf_group"]==2]; g3 = sub[sub["ecrf_group"]==3]
    def lr(a, b, name):
        T1=a["followup_years"].fillna(a["followup_years"].max()); E1=a["mobility_event"].fillna(0).astype(int)
        T2=b["followup_years"].fillna(b["followup_years"].max()); E2=b["mobility_event"].fillna(0).astype(int)
        res = logrank_test(T1, T2, E1, E2)
        return res.p_value
    p21 = lr(g1, g2, "mid"); p31 = lr(g1, g3, "high")
    km_report.append(f"- log-rank p (low vs middle) = {p21:.4f}")
    km_report.append(f"- log-rank p (low vs high)   = {p31:.4f}")
    ax.set_title(f"{cohort} (n={len(sub)})")
    ax.set_xlabel("Follow-up (years)")
    ax.set_ylabel("Survival (no mobility limitation)")
    ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(OUT + r"\an1_km_by_cohort.png", dpi=150)
km_report.append("")
km_report.append("图已存: an1_km_by_cohort.png")

with open(OUT + r"\an1_km_report.md", "w", encoding="utf-8") as f:
    f.write("\n".join(km_report))

# pooled global log-rank across groups within each cohort for concise summary
summary = ["# AN-1 汇总", ""]
for cohort in cohort_order:
    sub = df[df["cohort"]==cohort]
    # global log-rank across 3 groups via lifelines pairwise (statement)
    g1 = sub[sub["ecrf_group"]==1]; g2 = sub[sub["ecrf_group"]==2]; g3 = sub[sub["ecrf_group"]==3]
    def lr(a,b):
        T1=a["followup_years"].fillna(a["followup_years"].max()); E1=a["mobility_event"].fillna(0).astype(int)
        T2=b["followup_years"].fillna(b["followup_years"].max()); E2=b["mobility_event"].fillna(0).astype(int)
        return logrank_test(T1,T2,E1,E2).p_value
    summary.append(f"{cohort}: p(low-mid)={lr(g1,g2):.4f}, p(low-high)={lr(g1,g3):.4f}, p(mid-high)={lr(g2,g3):.4f}")
with open(OUT + r"\an1_summary.md", "w", encoding="utf-8") as f:
    f.write("\n".join(summary))
print("\n".join(summary))
print("TABLE1 rows:", len(tbl_df))