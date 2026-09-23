"""
STEP-08: eCRF calculation (sex-specific formulas from research plan §4.2)
  Male:   21.2870 + age*0.1654 - age2*0.0023 - bmi*0.2318 - waist*0.0337 - rhr*0.0390 + mvpa*0.6351 - smoking*0.4263
  Female: 14.7873 + age*0.1159 - age2*0.0017 - bmi*0.1534 - waist*0.0085 - rhr*0.0364 + mvpa*0.5987 - smoking*0.2994
where smoking = current smoking indicator (0/1). sex: 1=men 2=women (harmonized coding).
Only computed when all 6 inputs present; otherwise missing (kept for MICE).
Also writes per-db hand-check table (first 200 rows with inputs).
Output: output/ecrf_<db>.csv + output/step08_<db>_report.md
"""
from pathlib import Path
import pandas as pd

OUT = str(Path(__file__).resolve().parents[1] / "output")

def calc(db):
    d = pd.read_csv(OUT + rf"\analysis_{db}.csv")
    age = pd.to_numeric(d["age"], errors="coerce")
    bmi = pd.to_numeric(d["bmi"], errors="coerce")
    waist = pd.to_numeric(d["waist"], errors="coerce")
    rhr = pd.to_numeric(d["rhr"], errors="coerce")
    mvpa = pd.to_numeric(d["mvpa"], errors="coerce")
    smoke_now = pd.to_numeric(d["smoke_now"], errors="coerce")
    sex = pd.to_numeric(d["sex"], errors="coerce")

    ecrf = pd.Series(float("nan"), index=d.index)
    male = sex == 1
    female = sex == 2
    ok_m = age.notna() & bmi.notna() & waist.notna() & rhr.notna() & mvpa.notna() & smoke_now.notna() & male
    ok_f = age.notna() & bmi.notna() & waist.notna() & rhr.notna() & mvpa.notna() & smoke_now.notna() & female
    smk = smoke_now.fillna(0)  # only used where smoke_now nonmissing via ok_ masks
    ecrf[ok_m] = (21.2870 + age[ok_m]*0.1654 - (age[ok_m]**2)*0.0023 - bmi[ok_m]*0.2318
                  - waist[ok_m]*0.0337 - rhr[ok_m]*0.0390 + mvpa[ok_m]*0.6351 - smk[ok_m]*0.4263)
    ecrf[ok_f] = (14.7873 + age[ok_f]*0.1159 - (age[ok_f]**2)*0.0017 - bmi[ok_f]*0.1534
                  - waist[ok_f]*0.0085 - rhr[ok_f]*0.0364 + mvpa[ok_f]*0.5987 - smk[ok_f]*0.2994)
    d["ecrf"] = ecrf
    d.to_csv(OUT + rf"\ecrf_{db}.csv", index=False, encoding="utf-8-sig")

    # hand-check table
    check = d.loc[ecrf.notna(), ["pid","sex","age","bmi","waist","rhr","mvpa","smoke_now","ecrf"]]
    check = check.head(200)
    check.to_csv(OUT + rf"\step08_{db}_handcheck.csv", index=False, encoding="utf-8-sig")

    n_calc = int(ecrf.notna().sum())
    rep = [f"# STEP-08 {db} eCRF 计算报告", "",
           f"- 分析样本 n = {len(d)}",
           f"- 成功计算 eCRF: {n_calc}（所有 6 项输入齐全）",
           f"- 因缺输入未计算: {int(ecrf.isna().sum())}",
           f"- eCRF 范围: {ecrf.min():.2f} ~ {ecrf.max():.2f}（若可计算）",
           f"- eCRF 均值 ± SD: {ecrf.mean():.2f} ± {ecrf.std():.2f}（若可计算）",
           "",
           "前 200 行手算抽验表存于 step08_<db>_handcheck.csv（研究者可随机抽取手算核对）",
           "",
           "## eCRF 各输入缺失计数", "",
           "| 输入 | 非缺失 | 缺失 |", "|---|---|---|"]
    for c in ["age","bmi","waist","rhr","mvpa","smoke_now","sex"]:
        rep.append(f"| {c} | {int(d[c].notna().sum())} | {int(d[c].isna().sum())} |")
    with open(OUT + rf"\step08_{db}_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(rep))
    print(f"[{db}] n_calc={n_calc}/{len(d)}  ecrf range {ecrf.min():.2f}~{ecrf.max():.2f}")

for db in ["CHARLS","ELSA","HRS"]:
    calc(db)
print("ALL STEP-08 DONE")