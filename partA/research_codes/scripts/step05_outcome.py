"""
STEP-05: Follow-up / outcome extraction (new-onset mobility limitation)
Outcome (D5): 7-item mobility mobilsev>=1
Cohort: age>=45 at baseline (D6) AND baseline mobilsev==0 (no baseline mobility limitation).
- Follow each baseline participant through later waves.
- First wave with mobilsev>=1 (non-missing) => event, FU time = wave_year - baseline_year.
- Otherwise censored at last observed wave (last non-missing mobilsev), FU = that year - baseline_year.
Wave years:
  CHARLS: W1=2011, W2=2013, W3=2015, W4=2018
  ELSA  : W2=2004 ... W9=2018 (every 2 yrs)
  HRS   : W8=2006 ... W14=2018 (every 2 yrs)
Reads raw harmonized data for follow-up mobilsev; baseline from step04 CSVs.
Output: output/step05_<db>_outcome.csv + output/step05_<db>_report.md
"""
from pathlib import Path
import pandas as pd
import pyreadstat

OUT = str(Path(__file__).resolve().parents[1] / "output")

def load_mobil(name, path, kind, cols):
    if kind == "dta":
        df, meta = pyreadstat.read_dta(path, usecols=cols)
    else:
        df, meta = pyreadstat.read_sav(path, usecols=cols)
    return df

def build(db, src_csv, pid_raw, base_mobil, follow_map, kind, cb_path):
    base = pd.read_csv(src_csv)
    base["pid"] = base["pid"].astype(str).str.strip()
    # baseline cohort: age>=45 AND baseline mobilsev==0
    base_age = pd.to_numeric(base["age"], errors="coerce")
    base_mob = pd.to_numeric(base[base_mobil], errors="coerce")
    cohort = (base_age >= 45) & (base_mob == 0)
    base_cohort = base[cohort].copy()
    # load follow-up mobilsev from raw harmonized data
    follow_cols = list(follow_map.values())
    raw = load_mobil(db, cb_path, kind, [pid_raw] + follow_cols)
    raw["pid"] = raw[pid_raw].astype(str).str.strip()
    raw = raw.drop_duplicates(subset=["pid"], keep="first")
    merged = base_cohort.merge(raw, on="pid", how="left", validate="one_to_one")
    baseline_year = list(follow_map.keys())[0]
    years = sorted(follow_map.keys())
    events = []
    for r in merged.index:
        ev, fu, lastw = 0, float("nan"), -1
        for y in years[1:]:
            col = follow_map[y]
            m = pd.to_numeric(pd.Series([merged.loc[r, col]]), errors="coerce").iloc[0]
            if pd.notna(m):
                lastw = y
                if m >= 1:
                    ev, fu = 1, float(y - baseline_year)
                    break
        if ev == 0 and lastw >= 0:
            fu = float(lastw - baseline_year)
        events.append((ev, fu, lastw))
    out = pd.DataFrame(events, columns=["mobility_event", "followup_years", "last_obs_wave"],
                       index=merged.index)
    out["pid"] = merged["pid"].astype(str).str.strip()
    # re-attach baseline key vars for the cohort (age, sex, mobilsev_base, etc.)
    out = pd.merge(out, merged.drop(columns=[c for c in merged.columns if c in follow_map.values()]),
                   on="pid", how="left", validate="one_to_one")
    out.to_csv(OUT + rf"\step05_{db}_outcome.csv", index=False, encoding="utf-8-sig")
    n_cohort = len(out)
    n_ev = int((out["mobility_event"] == 1).sum())
    n_cens = int((out["mobility_event"] == 0).sum())
    fu_y = pd.to_numeric(out["followup_years"], errors="coerce")
    rep = [f"# STEP-05 {db} 结局提取报告", "",
           f"- 基线队列（age>=45 且 mobilsev_base==0）: {n_cohort}",
           f"- 新发事件（随访 mobilsev>=1 首次出现）: {n_ev}",
           f"- 删失（随访期内未出现或无后续观测）: {n_cens}",
           f"- 随访时间(年) 中位数: {fu_y.median() if fu_y.notna().any() else 'NA'}; IQR: {fu_y.quantile(0.25) if fu_y.notna().any() else 'NA'} ~ {fu_y.quantile(0.75) if fu_y.notna().any() else 'NA'}",
           f"- 随访时间最小值/最大值: {fu_y.min() if fu_y.notna().any() else 'NA'} / {fu_y.max() if fu_y.notna().any() else 'NA'}",
           "", "## 随访时间分布（年）", "",]
    rep += fu_y.value_counts().sort_index().to_string().splitlines()
    with open(OUT + rf"\step05_{db}_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(rep))
    print(f"[{db}] cohort={n_cohort} event={n_ev} censor={n_cens}")
    return out

CHARLS_SRC = str(Path(__file__).resolve().parents[3] / "data" / "Harmonized CHARLS" / "H_CHARLS_D_Data.dta")
build("CHARLS", OUT + r"\charls_baseline.csv", "ID", "mobilsev_base",
      {2011:"r1mobilsev", 2013:"r2mobilsev", 2015:"r3mobilsev", 2018:"r4mobilsev"},
      "dta", CHARLS_SRC)

ELSA_SRC = str(Path(__file__).resolve().parents[3] / "data" / "Harmonized ELSA" / "gh_elsa_h.sav")
e_follow = {2004:"r2mobilsev", 2006:"r3mobilsev", 2008:"r4mobilsev", 2010:"r5mobilsev",
            2012:"r6mobilsev", 2014:"r7mobilsev", 2016:"r8mobilsev", 2018:"r9mobilsev"}
build("ELSA", OUT + r"\elsa_baseline.csv", "idauniq", "mobilsev_base", e_follow,
      "sav", ELSA_SRC)

HRS_SRC = str(Path(__file__).resolve().parents[3] / "data" / "Harmonized HRS" / "H_HRS_d.dta")
h_follow = {2006:"r8mobilsev", 2008:"r9mobilsev", 2010:"r10mobilsev", 2012:"r11mobilsev",
            2014:"r12mobilsev", 2016:"r13mobilsev", 2018:"r14mobilsev"}
build("HRS", OUT + r"\hrs_baseline.csv", "hhidpn", "mobilsev_base", h_follow,
      "dta", HRS_SRC)
print("ALL STEP-05 DONE")