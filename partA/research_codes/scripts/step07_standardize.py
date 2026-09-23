"""
STEP-07: Coding standardization (D10) on analytic samples from STEP-05.
Derives:
  smoke_status : 0=never(从不) 1=former(曾) 2=current(当前)
                 (ever=0 -> never; ever=1 & now=1 -> current; ever=1 & now=0 -> former)
  drink        : already 0/1
  marital      : already 0/1 (married/partnered=1)
  educ         : already 1/2/3 (高中以下/高中/大学及以上)
  mvpa         : already 0/1
  bmi_cat      : WHO 4-cat [1 underweight <18.5, 2 normal 18.5-<25, 3 overweight 25-<30, 4 obese >=30]
Note: keeps all missing as missing (D7/D8). Flags any logically contradictory smoke combo.
Output: output/analysis_<db>.csv + output/step07_<db>_report.md
"""
from pathlib import Path
import pandas as pd

OUT = str(Path(__file__).resolve().parents[1] / "output")

def process(db):
    d = pd.read_csv(OUT + rf"\step05_{db}_outcome.csv")
    # drop duplicate raw-id columns
    dup_ids = {"CHARLS":"ID","ELSA":"idauniq","HRS":"hhidpn"}
    if dup_ids[db] in d.columns:
        d = d.drop(columns=[dup_ids[db]])
    d = d.drop(columns=[c for c in d.columns if c.lower() in ("_merge",)])

    ever = pd.to_numeric(d["smoke_ever"], errors="coerce")
    now  = pd.to_numeric(d["smoke_now"], errors="coerce")

    smoke = pd.Series(pd.NA, index=d.index, dtype="Int64")
    flag = pd.Series(False, index=d.index)
    # contradictory: never-smoker but now=1 (should not logically happen)
    contradictory = (ever == 0) & (now == 1)
    smoke[ever == 0] = 0            # never
    smoke[(ever == 1) & (now == 1)] = 2   # current
    smoke[(ever == 1) & (now == 0)] = 1   # former
    flag[contradictory] = True
    d["smoke_status"] = smoke
    d["smoke_flag_contradict"] = flag

    bmi = pd.to_numeric(d["bmi"], errors="coerce")
    bmi_cat = pd.Series(pd.NA, index=d.index, dtype="Int64")
    bmi_cat[bmi < 18.5] = 1
    bmi_cat[(bmi >= 18.5) & (bmi < 25)] = 2
    bmi_cat[(bmi >= 25) & (bmi < 30)] = 3
    bmi_cat[bmi >= 30] = 4
    d["bmi_cat"] = bmi_cat

    d.to_csv(OUT + rf"\analysis_{db}.csv", index=False, encoding="utf-8-sig")

    rep = [f"# STEP-07 {db} 标准化报告", "",
           f"- 分析样本 n = {len(d)}",
           "", "## smoke_status 分布", "",
           d["smoke_status"].value_counts(dropna=False).sort_index().to_string(),
           "", "## 矛盾组合（ever=0 & now=1）人数: ", str(int(flag.sum())), "",
           "## bmi_cat 分布", "",
           d["bmi_cat"].value_counts(dropna=False).sort_index().to_string(),
           "", "## 关键变量缺失率", "",
           "| var | non-missing | missing |", "|---|---|---|"]
    for c in ["age","sex","educ","marital","bmi","waist","rhr","mvpa","smoke_status","drink",
              "hibp","diab","cancer","lung","heart","stroke","mobilsev_base","followup_years"]:
        rep.append(f"| {c} | {int(d[c].notna().sum())} | {int(d[c].isna().sum())} |")
    with open(OUT + rf"\step07_{db}_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(rep))
    print(f"[{db}] n={len(d)} smoke never/former/current:",
          int((d['smoke_status']==0).sum()), int((d['smoke_status']==1).sum()), int((d['smoke_status']==2).sum()),
          "| contradictory:", int(flag.sum()))

for db in ["CHARLS","ELSA","HRS"]:
    process(db)
print("ALL STEP-07 DONE")