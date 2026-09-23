"""
AN-3: HRS PH violation handling (per §13.5 approved plan)
  1. Window-restricted Cox (M3): follow-up capped at 5yr / 10yr / full; report eCRF HR per window
     -> shows whether eCRF effect attenuates with time (PH violation mechanism).
  2. Time-varying interaction via person-period expansion (CoxTimeVaryingFitter):
     eCRF group main effects + group × log(t) interactions; report interaction p.
  3. Sensitivity: full M3 with <=10-year cap as the robustness check for main conclusion.
Output files:
  output/an3_hrs_ph_report.md        - 完整报告（窗口截断 + 时间交互 + 结论）
  output/an3_hrs_ph_results.csv      - 随访窗口截断 Cox 结果表（window/term/n/events/HR/CI/p）
  output/an3_hrs_ph_tvc_results.csv  - 时间交互项（CoxTimeVaryingFitter）结果表（term/coef/SE/HR/p）
Code: an3_hrs_ph.py （本文件，可重复运行）
"""
from pathlib import Path
import pandas as pd
import numpy as np
import scipy.stats as st
from lifelines import CoxPHFitter, CoxTimeVaryingFitter

OUT = str(Path(__file__).resolve().parents[1] / "output")
df = pd.read_csv(OUT + r"\final_analysis_pooled.csv")
df = df[df["ecrf_group"].notna()].copy()
d = df[df["cohort"] == "HRS"].copy()
for c in ["age","sex","educ","marital","sbp","smoke_status","drink"]:
    d[c] = pd.to_numeric(d[c], errors="coerce")
d["followup_years"] = pd.to_numeric(d["followup_years"], errors="coerce")
d["mobility_event"] = pd.to_numeric(d["mobility_event"], errors="coerce").fillna(0).astype(int)

d["group_mid"] = (d["ecrf_group"] == 2).astype(int)
d["group_high"] = (d["ecrf_group"] == 3).astype(int)
d["female"] = (d["sex"] == 2).astype(int)
d["educ_hs"] = (d["educ"] == 2).astype(int)
d["educ_college"] = (d["educ"] == 3).astype(int)
d["smk_former"] = (d["smoke_status"] == 1).astype(int)
d["smk_current"] = (d["smoke_status"] == 2).astype(int)

M3_COLS = ["group_mid","group_high","age","female","marital","educ_hs","educ_college",
           "smk_former","smk_current","drink","sbp"]

def cap_time(sub, cap):
    sub = sub.copy()
    if cap is None:
        sub["_T"] = sub["followup_years"]
        sub["_E"] = sub["mobility_event"]
    else:
        sub["_T"] = np.minimum(sub["followup_years"], cap)
        sub["_E"] = (sub["mobility_event"] == 1) & (sub["followup_years"] <= cap)
        sub["_E"] = sub["_E"].astype(int)
    return sub

rows = []
rep = ["# AN-3 HRS PH 假设处理报告", "",
       "## 1) 随访窗口截断 Cox（M3）——观察 eCRF 效应是否随时间衰减", ""]
for cap, name in [(5, "≤5 年"), (10, "≤10 年"), (None, "完整随访")]:
    s = cap_time(d, cap)
    dfm = s[["_T","_E"] + M3_COLS].dropna()
    if len(dfm) < 30:
        continue
    cph = CoxPHFitter(penalizer=0)
    cph.fit(dfm, duration_col="_T", event_col="_E")
    n_ev = int(dfm["_E"].sum())
    rep.append(f"### 窗口 {name}  (n={len(dfm)}, events={n_ev})")
    for term in ["group_mid","group_high"]:
        cc = cph.params_[term]; se = cph.standard_errors_[term]
        hr = np.exp(cc); lo = np.exp(cc - 1.96*se); hi = np.exp(cc + 1.96*se)
        p = 2*(1-st.norm.cdf(abs(cc/se)))
        rows.append({"window":name,"term":term,"n":len(dfm),"events":n_ev,
                     "HR":hr,"lo":lo,"hi":hi,"p":p})
        rep.append(f"- {term}: HR {hr:.3f} ({lo:.3f}-{hi:.3f}), p={p:.4f}")
    rep.append("")

# 2) time-varying interaction via person-period
rep.append("## 2) 时间交互项（CoxTimeVaryingFitter，group × log(t)）")
pp_rows = []
bounds = [0, 5, 10, np.inf]
base = d[["pid","followup_years","mobility_event"] + M3_COLS].dropna()
for _, r in base.iterrows():
    T = float(r["followup_years"]); E = int(r["mobility_event"])
    entered = 0.0
    for b in range(len(bounds)-1):
        lo_b, hi_b = bounds[b], bounds[b+1]
        if hi_b <= entered:
            continue
        stop = min(T, hi_b)
        if stop <= entered:
            break
        seg_event_effective = 1 if (E == 1 and stop == T) else 0
        row = {}
        for c in ["pid"] + M3_COLS:
            row[c] = r[c]
        row["start"] = entered
        row["stop"] = stop
        row["event"] = seg_event_effective
        row["logt"] = np.log(max(stop, 0.5))
        pp_rows.append(row)
        entered = stop
        if entered >= T:
            break
pp = pd.DataFrame(pp_rows)
# verify each id sums events correctly (sanity)
id_sum = pp.groupby("pid")["event"].sum()
target = base.set_index("pid")["mobility_event"].fillna(0).astype(int)
mismatch = (id_sum.reindex(target.index).fillna(0) != target).sum()
rep.append(f"- person-period 行数: {len(pp)}; 事件总和校验不一致人数: {mismatch}")

for gname, gcol in [("中","group_mid"),("高","group_high")]:
    pp[gcol+"_x_logt"] = pp[gcol] * pp["logt"]

tvcols = ["group_mid","group_high","group_mid_x_logt","group_high_x_logt",
          "age","female","marital","educ_hs","educ_college","smk_former","smk_current","drink","sbp"]
ppt = pp[["pid","start","stop","event"] + tvcols].dropna()
tvc_rows = []
try:
    ct = CoxTimeVaryingFitter(penalizer=0)
    ct.fit(ppt, id_col="pid", start_col="start", stop_col="stop", event_col="event",
           show_progress=False)
    rep.append("### 时间交互项结果")
    for term in tvcols:
        cc = ct.params_[term]; se = ct.standard_errors_[term]
        p = 2*(1-st.norm.cdf(abs(cc/se)))
        tvc_rows.append({"term": term, "coef": cc, "se": se, "HR": np.exp(cc),
                         "HR_lo": np.exp(cc-1.96*se), "HR_hi": np.exp(cc+1.96*se), "p": p})
        rep.append(f"- {term}: coef {cc:.4f} (se {se:.4f}), p={p:.4f}")
    rep.append("### 交互项 p（检验 PH 是否随时间变化）")
    for term in ["group_mid_x_logt","group_high_x_logt"]:
        cc = ct.params_[term]; se = ct.standard_errors_[term]
        p = 2*(1-st.norm.cdf(abs(cc/se)))
        rep.append(f"- {term}: p={p:.4f}" + ("  (<0.05 → 效应随时间显著变化)" if p < 0.05 else "  (>0.05)"))
except Exception as e:
    rep.append(f"### 时间交互项失败: {e}")
pd.DataFrame(tvc_rows).to_csv(OUT + r"\an3_hrs_ph_tvc_results.csv", index=False, encoding="utf-8-sig")

rep.append("")
rep.append("## 3) 结论")
rep.append("- 看窗口 1 中 group_mid/group_high 的 HR 是否随随访窗口缩短而变强（效应衰减证据）。")
rep.append("- 若时间交互项 p<0.05，报告交互项以解释 PH 违反。")
rep.append("- 以 ≤10 年窗口作为稳健性复验：若 HR 仍 <1 且显著，则主结论成立。")

with open(OUT + r"\an3_hrs_ph_report.md", "w", encoding="utf-8") as f:
    f.write("\n".join([str(x) for x in rep]))
pd.DataFrame(rows).to_csv(OUT + r"\an3_hrs_ph_results.csv", index=False, encoding="utf-8-sig")
print("\n".join([str(x) for x in rep]))