"""
STEP-04b: HRS baseline extraction (Wave 8 = 2006, baseline)
Merges harmonized (H_HRS_d.dta) + RAND HRS Longitudinal (randhrs1992_2022v1.sav) on hhidpn.
Sources per handbook §7:
  harmonized : bmi(r8mbmi), height(r8mheight), weight(r8mweight), waist(r8mwaist),
               pulse(r8pulse->rhr), sbp(r8systo), mobilsev_base(r8mobilsev), adl_base
  RAND       : age(R8AGEY_E), sex(RAGENDER), educ(RAEDUC->3group per D10), marital(R8MSTAT),
               smoke_ever(R8SMOKEV), smoke_now(R8SMOKEN), drink(R8DRINK),
               PA(R8VGACTX/R8MDACTX -> MVPA per D11),
               diseases(R8HIBPE/R8DIABE/R8CANCRE/R8LUNGE/R8HEARTE/R8STROKE)
D6 age>=45. D12 ranges applied to bmi/height/weight/waist (waist cm from RAND inches*2.54).
Output: output/hrs_baseline.csv + output/step04b_hrs_report.md
"""
from pathlib import Path
import numpy as np
import pandas as pd
import pyreadstat

HARM = str(Path(__file__).resolve().parents[3] / "data" / "Harmonized HRS" / "H_HRS_d.dta")
RAND = str(Path(__file__).resolve().parents[3] / "data" / "Harmonized HRS" / "randhrs1992_2022v1.sav")
OUT = str(Path(__file__).resolve().parents[1] / "output")

hcols = ["hhidpn","r8mbmi","r8mheight","r8mweight","r8mwaist","r8pulse","r8systo",
         "r8mobilsev","r8adlfive"]
hd, _ = pyreadstat.read_dta(HARM, usecols=hcols)
hd["hhidpn"] = hd["hhidpn"].astype(int)

rcols = ["HHIDPN","R8AGEY_E","RAGENDER","RAEDUC","R8MSTAT","R8SMOKEV","R8SMOKEN","R8DRINK",
         "R8VGACTX","R8MDACTX","R8PMWGHT","R8PMHGHT","R8PMBMI","R8PMWAIST","R8BPSYS",
         "R8HIBPE","R8DIABE","R8CANCRE","R8LUNGE","R8HEARTE","R8STROKE"]
rd, _ = pyreadstat.read_sav(RAND, usecols=rcols)
rd["hhidpn"] = rd["HHIDPN"].astype(int)

df = pd.merge(rd, hd, on="hhidpn", how="inner", validate="one_to_one")

def to_num(s):
    return pd.to_numeric(s, errors="coerce")

out = pd.DataFrame()
out["pid"] = df["hhidpn"]
out["cohort"] = "HRS"
out["age"] = to_num(df["R8AGEY_E"])
out["sex"] = to_num(df["RAGENDER"])
# education: RAEDUC 5 -> 3 (D10). 1=LtHS->1(高中以下); 2 GED/3 HS grad/4 some college ->2(高中); 5 college+->3
e = to_num(df["RAEDUC"])
out["educ"] = None
out["educ"] = e.map({1:1, 2:2, 3:2, 4:2, 5:3})
# marital: 1 married,2 married spouse absent,3 partnered ->1 ; others(4,5,6,7,8)->0
m = to_num(df["R8MSTAT"])
out["marital"] = pd.Series(np.where(m.isin([1,2,3]), 1, 0), index=m.index)
out["marital"] = out["marital"].where(m.notna(), pd.NA)
# body measures (from RAND PM; harmonized equivalent identical; use RAND PMWGHT/HGHT, PMBMI, PMWAIST*2.54)
out["bmi"] = to_num(df["R8PMBMI"])
out["height"] = to_num(df["R8PMHGHT"])
out["weight"] = to_num(df["R8PMWGHT"])
out["waist"] = to_num(df["R8PMWAIST"]) * 2.54
out["rhr"] = to_num(df["r8pulse"])
out["sbp"] = to_num(df["R8BPSYS"])

# D12/D13 exclusion
n_before = {c: int(out[c].notna().sum()) for c in ["bmi","height","weight","waist","sbp"]}
out["bmi"]   = out["bmi"].where(out["bmi"].between(10, 60), pd.NA)
out["height"] = out["height"].where(out["height"].between(1.0, 2.2), pd.NA)
out["weight"] = out["weight"].where(out["weight"].between(30, 200), pd.NA)
out["waist"]  = out["waist"].where(out["waist"].between(40, 170), pd.NA)
out["sbp"]    = out["sbp"].where(out["sbp"].between(50, 260), pd.NA)
n_after = {c: int(out[c].notna().sum()) for c in n_before}
excluded = {c: n_before[c] - n_after[c] for c in n_before}
print("D12/D13 excluded:", excluded)

# MVPA (D11): VGACTX/MDACTX in {1(every day),2(>1/wk)} = weekly>=2
vg = to_num(df["R8VGACTX"]); md = to_num(df["R8MDACTX"])
vg_known = vg.notna(); md_known = md.notna()
vg_val = vg.isin([1,2]); md_val = md.isin([1,2])
def mvpa(r):
    vk, mk = r["_vk"], r["_mk"]
    vv, mv = r["_vv"], r["_mv"]
    if vk and mk:
        return int(vv or mv)
    if vk:
        return int(vv)
    if mk:
        return int(mv)
    return pd.NA
out["_vk"]=vg_known; out["_mk"]=md_known; out["_vv"]=vg_val; out["_mv"]=md_val
out["mvpa"] = out.apply(mvpa, axis=1)
out.drop(columns=["_vk","_mk","_vv","_mv"], inplace=True)

# smoking / drinking
out["smoke_ever"] = to_num(df["R8SMOKEV"])
out["smoke_now"]  = to_num(df["R8SMOKEN"])
out["drink"]      = to_num(df["R8DRINK"])
# diseases
for src,dst in [("R8HIBPE","hibp"),("R8DIABE","diab"),("R8CANCRE","cancer"),
                ("R8LUNGE","lung"),("R8HEARTE","heart"),("R8STROKE","stroke")]:
    out[dst] = to_num(df[src])
# baseline mobility
out["mobilsev_base"] = to_num(df["r8mobilsev"])
out["adl_base"]      = to_num(df["r8adlfive"])
out["age_ge45"] = (out["age"] >= 45)

out.to_csv(OUT + r"\hrs_baseline.csv", index=False, encoding="utf-8-sig")

rep = ["# STEP-04b HRS 基线提取报告", "",
       f"- 合并后行数: {len(out)}",
       f"- 基线年龄≥45: {int(out['age_ge45'].sum())} (缺失年龄: {int(out['age'].isna().sum())})",
       "", "## 各变量缺失数与分布", "",
       "| 变量 | 非缺失 n | 缺失 n | 范围/取值 |", "|---|---|---|---|"]
for c in out.columns:
    s = out[c]; nm = s.notna().sum()
    if s.dtype.kind in "fi":
        rng = f"{s.min():g} ~ {s.max():g}" if nm else "-"
    else:
        rng = str(sorted(s.dropna().unique())[:12])
    rep.append(f"| {c} | {nm} | {int(s.isna().sum())} | {rng} |")
rep.append("")
rep.append("## D12/D13 剔除")
for c,cb,ca,x in [("bmi",n_before['bmi'],n_after['bmi'],excluded['bmi']),
                  ("height",n_before['height'],n_after['height'],excluded['height']),
                  ("weight",n_before['weight'],n_after['weight'],excluded['weight']),
                  ("waist",n_before['waist'],n_after['waist'],excluded['waist']),
                  ("sbp",n_before['sbp'],n_after['sbp'],excluded['sbp'])]:
    rep.append(f"- {c}: {cb} -> {ca}, 剔除 {x}")
rep.append("")
rep.append("## MVPA")
rep.append(f"- MVPA=0: {int((out['mvpa']==0).sum())} | MVPA=1: {int((out['mvpa']==1).sum())} | 缺失: {int(out['mvpa'].isna().sum())}")

with open(OUT + r"\step04b_hrs_report.md", "w", encoding="utf-8") as f:
    f.write("\n".join(rep))
print("HRS baseline written; n=", len(out), " age>=45:", int(out["age_ge45"].sum()))
print("MVPA 0/1/miss:", int((out['mvpa']==0).sum()), int((out['mvpa']==1).sum()), int(out['mvpa'].isna().sum()))