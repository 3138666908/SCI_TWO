"""
Table 1 baseline characteristics of study population
Population: eCRF-complete sample (n=7,885: HRS 2,334 / ELSA 3,093 / CHARLS 2,458)
Layout: Variables | HRS | ELSA | CHARLS | P-value
Continuous: mean (SD), ANOVA across the 3 cohorts
Categorical: n (%), chi-square across the 3 cohorts
CVD = heart==1 OR stroke==1
Output: output/table1_baseline_chars.csv + table1_baseline_chars.md
"""
from pathlib import Path
import pandas as pd
import numpy as np
import scipy.stats as st

OUT = str(Path(__file__).resolve().parents[1] / "output")
df = pd.read_csv(OUT + r"\final_analysis_pooled.csv")
df = df[df["ecrf_group"].notna()].copy()
cohort_order = ["HRS", "ELSA", "CHARLS"]
for c in ["age","sex","educ","marital","bmi","waist","rhr","sbp","mvpa","smoke_status",
          "drink","hibp","diab","cancer","lung","heart","stroke","ecrf"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
df["CVD"] = ((df["heart"] == 1) | (df["stroke"] == 1)).astype(float)
df.loc[df[["heart","stroke"]].isna().all(axis=1), "CVD"] = np.nan

rows = []

def cont(var, label, unit):
    r = {"Variables": label}
    vals = {}
    for co in cohort_order:
        v = df[df["cohort"]==co][var].dropna()
        r[co] = f"{v.mean():.1f} ({v.std():.1f})" if len(v) else "NA"
        vals[co] = v
    # ANOVA
    groups = [vals[c].dropna().astype(float) for c in cohort_order]
    groups = [g for g in groups if len(g) > 0]
    if len(groups) >= 2:
        f, p = st.f_oneway(*groups)
        r["P-value"] = f"{p:.3f}" if p >= 0.001 else "<0.001"
        # handle NaN in ANOVA (should be none in eCRF-complete samples for age etc.)
    else:
        r["P-value"] = "-"
    return r

def cat(var, label, yes_level=1, no_label=None):
    """cell: n (%) where var==yes_level; % among non-missing"""
    r = {"Variables": label}
    table = []
    for co in cohort_order:
        v = df[df["cohort"]==co][var]
        v = pd.to_numeric(v, errors="coerce")
        n_yes = int((v==yes_level).sum())
        n_nonmiss = int(v.notna().sum())
        pct = 100*n_yes/n_nonmiss if n_nonmiss else np.nan
        r[co] = f"{n_yes} ({pct:.1f}%)"
        table.append(v)
    # chi-square across cohorts (2x3: yes/no x cohort)
    mat = []
    for co in cohort_order:
        v = pd.to_numeric(df[df["cohort"]==co][var], errors="coerce").dropna()
        n_yes = int((v==yes_level).sum())
        n_no = int((v!=yes_level).sum())
        mat.append([n_yes, n_no])
    mat = np.array(mat)
    if (mat.sum(axis=1) > 0).all() and (mat.sum(axis=0) > 0).all():
        chi2, p, dof, exp = st.chi2_contingency(mat)
        r["P-value"] = f"{p:.3f}" if p >= 0.001 else "<0.001"
    else:
        r["P-value"] = "-"
    return r

def smoke(col, label, level):
    """categorical cell: n (%) where col==level, among non-missing"""
    r = {"Variables": label}
    mat = []
    for co in cohort_order:
        v = pd.to_numeric(df[df["cohort"]==co][col], errors="coerce").dropna()
        n = int((v==level).sum()); total = int(v.notna().sum())
        r[co] = f"{n} ({100*n/total:.1f}%)" if total else "NA"
        mat.append([n, int((v!=level).sum())])
    mat = np.array(mat)
    if (mat.sum(axis=1) > 0).all() and (mat.sum(axis=0) > 0).all():
        chi2, p, dof, exp = st.chi2_contingency(mat)
        r["P-value"] = f"{p:.3f}" if p >= 0.001 else "<0.001"
    else:
        r["P-value"] = "-"
    return r

def educ(label, level):
    return smoke("educ", label, level)

# N
n_row = {"Variables": "Number"}
for co in cohort_order:
    n_row[co] = str(len(df[df["cohort"]==co]))
n_row["P-value"] = "-"
rows.append(n_row)

rows.append(cont("ecrf", "eCRF, mean (SD), MET", "MET"))
rows.append(cont("age", "Age, mean (SD), years", "years"))
# Sex
r = {"Variables": "Sex, n (%)"}
for co in cohort_order:
    v = pd.to_numeric(df[df["cohort"]==co]["sex"], errors="coerce")
    nm = v.notna().sum()
    n_m = int((v==1).sum()); n_f = int((v==2).sum())
    r[co] = f"{n_m} male / {n_f} female" if nm==n_m+n_f else "NA"
r["P-value"] = "-"
rows.append(r)
male = smoke("sex", "  Male", 1)
rows.append(male)
r_f = {"Variables": "  Female"}
mat=[]
for co in cohort_order:
    v = pd.to_numeric(df[df["cohort"]==co]["sex"], errors="coerce").dropna()
    n= (v==2).sum(); tot=v.notna().sum()
    r_f[co]=f"{int(n)} ({100*n/tot:.1f}%)" if tot else "NA"
    mat.append([int((v==2).sum()), int((v!=2).sum())])
mat=np.array(mat)
if (mat.sum(axis=1)>0).all() and (mat.sum(axis=0)>0).all():
    chi2,p,_,_= st.chi2_contingency(mat); r_f["P-value"]= f"{p:.3f}" if p>=0.001 else "<0.001"
else:
    r_f["P-value"]="-"
rows.append(r_f)

# Marital status
rows.append({"Variables":"Marital status, n (%)","P-value":"-"})
rows.append(smoke("marital", "  Married or partnered", 1))
rows.append(smoke("marital", "  Other marital status", 0))

# Education
rows.append({"Variables":"Education, n (%)","P-value":"-"})
rows.append(educ("  Below high school", 1))
rows.append(educ("  High school", 2))
rows.append(educ("  College or above", 3))

# Smoking
rows.append({"Variables":"Smoking status, n (%)","P-value":"-"})
rows.append(smoke("smoke_status", "  Never", 0))
rows.append(smoke("smoke_status", "  Former", 1))
rows.append(smoke("smoke_status", "  Current", 2))

# Alcohol
rows.append({"Variables":"Alcohol consumption, n (%)","P-value":"-"})
rows.append(smoke("drink", "  No", 0))
rows.append(smoke("drink", "  Yes", 1))

# Physical activity
rows.append({"Variables":"Physical activity, n (%)","P-value":"-"})
rows.append(smoke("mvpa", "  Moderate-to-vigorous", 1))
rows.append(smoke("mvpa", "  Others", 0))

# Body measures
rows.append(cont("bmi", "BMI, mean (SD), kg/m2", "kg/m2"))
rows.append(cont("waist", "WC, mean (SD), cm", "cm"))
rows.append(cont("rhr", "rHR, mean (SD), bpm", "bpm"))
rows.append(cont("sbp", "SBP, mean (SD), mmHg", "mmHg"))

# CVD / diseases
rows.append(cat("hibp", "Hypertension, n (%)", 1))
rows.append(cat("diab", "Diabetes, n (%)", 1))
rows.append(cat("cancer", "Cancer, n (%)", 1))
rows.append(cat("lung", "Lung disease, n (%)", 1))
rows.append(cat("CVD", "CVD, n (%)", 1))

# eCRF score (same as eCRF row per request)
rows.append(cont("ecrf", "eCRF score, mean (SD)", ""))

tbl = pd.DataFrame(rows)
tbl.to_csv(OUT + r"\table1_baseline_chars.csv", index=False, encoding="utf-8-sig")

md = ["| Variables | HRS (n=2334) | ELSA (n=3093) | CHARLS (n=2458) | P-value |", "|---|---|---|---|---|"]
for _, r in tbl.iterrows():
    md.append(f"| {r['Variables']} | {r['HRS']} | {r['ELSA']} | {r['CHARLS']} | {r['P-value']} |")
with open(OUT + r"\table1_baseline_chars.md", "w", encoding="utf-8") as f:
    f.write("\n".join(md))
print("\n".join(md))