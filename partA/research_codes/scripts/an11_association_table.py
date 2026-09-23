"""
AN-11: Association table: eCRF vs new-onset mobility limitation
Per cohort: eCRF per 1-SD (continuous, standardized within cohort), eCRF categories
(low ref / moderate / high), P for trend (for each model).
Models: M1 unadjusted; M2 +age+sex; M3 +marital+education+smoking+drinking+SBP.
Events/n reported for every row except P for trend.
Output: output/an11_association_table.csv + .md
"""
from pathlib import Path
import pandas as pd
import numpy as np
import scipy.stats as st
from lifelines import CoxPHFitter

OUT = str(Path(__file__).resolve().parents[1] / "output")
df = pd.read_csv(OUT + r"\final_analysis_pooled.csv")
df = df[df["ecrf_group"].notna()].copy()
for c in ["age","sex","educ","marital","sbp","smoke_status","drink","ecrf","followup_years","mobility_event"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
df["mobility_event"] = df["mobility_event"].fillna(0).astype(int)
df["ecrf_group"] = df["ecrf_group"].astype(int)

def prep(d):
    d = d.copy()
    d["female"] = (d["sex"]==2).astype(int)
    d["educ_hs"] = (d["educ"]==2).astype(int)
    d["educ_college"] = (d["educ"]==3).astype(int)
    d["smk_former"] = (d["smoke_status"]==1).astype(int)
    d["smk_current"] = (d["smoke_status"]==2).astype(int)
    d["g_mid"] = (d["ecrf_group"]==2).astype(int)
    d["g_high"] = (d["ecrf_group"]==3).astype(int)
    d["ecrf_sd"] = (d["ecrf"] - d["ecrf"].mean()) / d["ecrf"].std()
    d["g_trend"] = d["ecrf_group"].astype(float)
    return d

COV2 = ["age","female"]
COV3 = ["age","female","marital","educ_hs","educ_college","smk_former","smk_current","drink","sbp"]

def fit(dfm, expo_cols):
    cph = CoxPHFitter(penalizer=0)
    cph.fit(dfm, duration_col="followup_years", event_col="mobility_event")
    return cph

def cell(cph, term):
    cc = cph.params_[term]; se = cph.standard_errors_[term]
    hr = np.exp(cc); lo = np.exp(cc-1.96*se); hi = np.exp(cc+1.96*se)
    p = 2*(1-st.norm.cdf(abs(cc/se)))
    return hr, lo, hi, p

def fmt(hr, lo, hi):
    return f"{hr:.2f} ({lo:.2f}-{hi:.2f})"

def pfmt(p):
    return "<0.001" if p < 0.001 else f"{p:.3f}"

def en(d_sub):
    """events/n for a (sub)sample"""
    d2 = d_sub.dropna(subset=["followup_years"])
    return f"{int(d2['mobility_event'].sum())}/{len(d2)}"

rows = []
for co in ["CHARLS","ELSA","HRS"]:
    d = prep(df[df["cohort"]==co])
    rows.append({"cohort":co,"variable":"__header__","Events/n":"", "M1":"","M1_p":"","M2":"","M2_p":"","M3":"","M3_p":""})

    # ---------- eCRF per 1-SD ----------
    r = {"cohort":co,"variable":"eCRF per 1-SD","Events/n":en(d)}
    dfm1 = d[["followup_years","mobility_event","ecrf_sd"]].dropna()
    dfm2 = d[["followup_years","mobility_event","ecrf_sd"]+COV2].dropna()
    dfm3 = d[["followup_years","mobility_event","ecrf_sd"]+COV3].dropna()
    for cph, mm in [(fit(dfm1,["ecrf_sd"]),"M1"),(fit(dfm2,["ecrf_sd"]+COV2),"M2"),(fit(dfm3,["ecrf_sd"]+COV3),"M3")]:
        hr,lo,hi,p = cell(cph,"ecrf_sd"); r[mm]=fmt(hr,lo,hi); r[mm+"_p"]=pfmt(p)
    rows.append(r)

    # ---------- eCRF categories ----------
    # events/n per category (eCRF-complete, with follow-up)
    gsub = d.dropna(subset=["followup_years"])
    for g, lab in [(1,"Low eCRF level"),(2,"Moderate eCRF level"),(3,"High eCRF level")]:
        gg = gsub[gsub["ecrf_group"]==g]
        r = {"cohort":co,"variable":lab,"Events/n":en(gg)}
        if g == 1:
            r.update({"M1":"Reference","M1_p":"-","M2":"Reference","M2_p":"-","M3":"Reference","M3_p":"-"})
        else:
            term = "g_mid" if g==2 else "g_high"
            cdfm1 = d[["followup_years","mobility_event","g_mid","g_high"]].dropna()
            cdfm2 = d[["followup_years","mobility_event","g_mid","g_high"]+COV2].dropna()
            cdfm3 = d[["followup_years","mobility_event","g_mid","g_high"]+COV3].dropna()
            for cph, mm in [(fit(cdfm1,["g_mid","g_high"]),"M1"),(fit(cdfm2,["g_mid","g_high"]+COV2),"M2"),(fit(cdfm3,["g_mid","g_high"]+COV3),"M3")]:
                hr,lo,hi,p = cell(cph,term); r[mm]=fmt(hr,lo,hi); r[mm+"_p"]=pfmt(p)
        rows.append(r)

    # ---------- P for trend (each model) ----------
    r = {"cohort":co,"variable":"P for trend","Events/n":""}
    dfmt1 = d[["followup_years","mobility_event","g_trend"]].dropna()
    dfmt2 = d[["followup_years","mobility_event","g_trend"]+COV2].dropna()
    dfmt3 = d[["followup_years","mobility_event","g_trend"]+COV3].dropna()
    for cph, mm in [(fit(dfmt1,["g_trend"]),"M1"),(fit(dfmt2,["g_trend"]+COV2),"M2"),(fit(dfmt3,["g_trend"]+COV3),"M3")]:
        hr,lo,hi,p = cell(cph,"g_trend"); r[mm]=""; r[mm+"_p"]=pfmt(p)
    rows.append(r)
    rows.append({"cohort":co,"variable":"","Events/n":"","M1":"","M1_p":"","M2":"","M2_p":"","M3":"","M3_p":""})

tbl = pd.DataFrame(rows)
tbl.to_csv(OUT + r"\an11_association_table.csv", index=False, encoding="utf-8-sig")

md = ["| Cohort | Variable | Events/n | Model 1 HR (95% CI) | P | Model 2 HR (95% CI) | P | Model 3 HR (95% CI) | P |",
      "|---|---|---|---|---|---|---|---|---|"]
cur = None
first_in_block = True
for _, r in tbl.iterrows():
    if r["variable"] == "__header__":
        cur = r["cohort"]
        first_in_block = True
        continue
    if r["variable"] == "":
        md.append("|  |  |  |  |  |  |  |  |  |")
        first_in_block = True
        continue
    co_disp = cur if first_in_block else ""
    first_in_block = False
    md.append(f"| {co_disp} | {r['variable']} | {r['Events/n']} | "
              f"{r.get('M1','')} | {r.get('M1_p','')} | {r.get('M2','')} | {r.get('M2_p','')} | "
              f"{r.get('M3','')} | {r.get('M3_p','')} |")
with open(OUT + r"\an11_association_table.md","w",encoding="utf-8") as f:
    f.write("\n".join(md))
print("\n".join(md))