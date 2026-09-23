"""
STEP-04a: CHARLS baseline extraction (Wave 1 = 2011-2012, baseline)
Selected variables (per handbook sections 6.x):
  ID           : person key (Wave2+ ID; used as analysis key)
  age          : r1agey                    (年龄>=45 纳入 D6)
  sex          : ragender                  (1=男 2=女)
  educ         : raeducl                   (3-tier, D10)
  marital      : r1mstat                   -> 已婚或有伴侣(1)=1 其他(0)=0  (D10)
  bmi          : r1mbmi                    实测
  waist        : r1mwaist cm               实测
  rhr          : r1pulse bpm               实测
  sbp          : r1systo mmHg              实测
  mvpa         : (r1vgact_c=1 & r1vgactx_c>=2) | (r1mdact_c=1 & r1mdactx_c>=2)  (D11)
  smoke_ever   : r1smokev
  smoke_now    : r1smoken
  drink        : r1drinkev                 (饮酒者=1 不饮酒=0, D10)
  hibp/diab/cancer/lung/heart/stroke : r1hibpe/r1diabe/r1cancre/r1lunge/r1hearte/r1stroke
  mobilsev_base: r1mobilsev (clinical; used to define baseline mobility status)
Missing: all retained (D7/D8). Wave1-3 PA half-sample missing kept as NaN.
Output: output/charls_baseline.csv + output/step04a_charls_report.md
"""
from pathlib import Path
import numpy as np
import pandas as pd
import pyreadstat

SRC = str(Path(__file__).resolve().parents[3] / "data" / "Harmonized CHARLS" / "H_CHARLS_D_Data.dta")
OUT = str(Path(__file__).resolve().parents[1] / "output")

cols = ["ID","ID_w1","ragender","raeducl","r1agey","r1mbmi","r1mheight","r1mweight","r1mwaist",
        "r1systo","r1pulse","r1vgact_c","r1vgactx_c","r1mdact_c","r1mdactx_c","r1smokev","r1smoken",
        "r1drinkev","r1drinkl","r1mstat","r1hibpe","r1diabe","r1cancre","r1lunge","r1hearte",
        "r1stroke","r1mobilsev","r1adlfive"]
df, meta = pyreadstat.read_dta(SRC, usecols=cols)
def to_num(s):
    return pd.to_numeric(s, errors="coerce")

out = pd.DataFrame()
out["pid"] = df["ID"]
out["cohort"] = "CHARLS"
out["age"] = to_num(df["r1agey"])
out["sex"] = to_num(df["ragender"])
out["educ"] = to_num(df["raeducl"])
# marital: 1=married 3=partnered -> 1; others(4,5,7,8) -> 0
m = to_num(df["r1mstat"])
# 1=married,3=partnered -> 1; others(4,5,7,8) -> 0
out["marital"] = pd.Series(np.where(m.isin([1, 3]), 1, 0), index=m.index)
out["marital"] = out["marital"].where(m.notna(), pd.NA)  # keep missing if mstat missing
# body (measured)
out["bmi"] = to_num(df["r1mbmi"])
out["height"] = to_num(df["r1mheight"])
out["weight"] = to_num(df["r1mweight"])
out["waist"] = to_num(df["r1mwaist"])
out["rhr"] = to_num(df["r1pulse"])
out["sbp"] = to_num(df["r1systo"])

# ---- D12/D13: exclude physiologically implausible values (set out-of-range to NaN) ----
n_before = {c: int(out[c].notna().sum()) for c in ["bmi","height","weight","waist","sbp"]}
out["bmi"]   = out["bmi"].where(out["bmi"].between(10, 60), pd.NA)
out["height"] = out["height"].where(out["height"].between(1.0, 2.2), pd.NA)
out["weight"] = out["weight"].where(out["weight"].between(30, 200), pd.NA)
out["waist"]  = out["waist"].where(out["waist"].between(40, 170), pd.NA)
out["sbp"]    = out["sbp"].where(out["sbp"].between(50, 260), pd.NA)
n_after = {c: int(out[c].notna().sum()) for c in n_before}
excluded = {c: n_before[c] - n_after[c] for c in n_before}
print("D12/D13 excluded counts:", excluded)
# MVPA (D11: weekly >=2) -- careful: NaN must stay NaN, not become False
vgc = to_num(df["r1vgact_c"]); vgx = to_num(df["r1vgactx_c"])
mdc = to_num(df["r1mdact_c"]); mdx = to_num(df["r1mdactx_c"])
vig_known = vgc.notna() & vgx.notna()
mod_known = mdc.notna() & mdx.notna()
vig_val = (vgc == 1) & (vgx >= 2)
mod_val = (mdc == 1) & (mdx >= 2)
def calc_mvpa(r):
    vk, mk = r["_vk"], r["_mk"]
    vv, mv = r["_vv"], r["_mv"]
    if vk and mk:
        return int(vv or mv)
    if vk:
        return int(vv)
    if mk:
        return int(mv)
    return pd.NA
out["_vk"] = vig_known; out["_mk"] = mod_known
out["_vv"] = vig_val; out["_mv"] = mod_val
out["mvpa"] = out.apply(calc_mvpa, axis=1)
out.drop(columns=["_vk", "_mk", "_vv", "_mv"], inplace=True)
# smoking
out["smoke_ever"] = to_num(df["r1smokev"])
out["smoke_now"] = to_num(df["r1smoken"])
# drinking
out["drink"] = to_num(df["r1drinkev"])
# chronic disease
for src, dst in [("r1hibpe","hibp"),("r1diabe","diab"),("r1cancre","cancer"),
                 ("r1lunge","lung"),("r1hearte","heart"),("r1stroke","stroke")]:
    out[dst] = to_num(df[src])
# baseline mobility (7-item, D5)
out["mobilsev_base"] = to_num(df["r1mobilsev"])
out["adl_base"] = to_num(df["r1adlfive"])

# age>=45 (D6)
out["age_ge45"] = (out["age"] >= 45)

out.to_csv(OUT + r"\charls_baseline.csv", index=False, encoding="utf-8-sig")

# report
rep = ["# STEP-04a CHARLS 基线提取报告", "",
       f"- 总行数: {len(out)}",
       f"- 基线年龄≥45 的人数: {int(out['age_ge45'].sum())} (缺失年龄: {int(out['age'].isna().sum())})",
       "", "## 各变量缺失数与分布", "",
       "| 变量 | 非缺失 n | 缺失 n | 唯一值/范围 |", "|---|---|---|---|"]
for c in out.columns:
    s = out[c]
    nm = s.notna().sum()
    miss = s.isna().sum()
    if c in ("channel",): pass
    if s.dtype.kind in "fi":
        rng = f"{s.min():g} ~ {s.max():g}" if nm else "-"
    else:
        u = s.dropna().unique()
        rng = str(sorted(u)[:12])
    rep.append(f"| {c} | {nm} | {miss} | {rng} |")

# D12/D13 excluded report
rep.append("## D12/D13 体格测量异常值剔除（合理生理范围）")
rep.append(f"- BMI∈[10,60]: 剔除前 {n_before['bmi']} → 剔除后 {n_after['bmi']}，剔除 {excluded['bmi']}")
rep.append(f"- 身高∈[1.0,2.2]: 剔除前 {n_before['height']} → 剔除后 {n_after['height']}，剔除 {excluded['height']}")
rep.append(f"- 体重∈[30,200]: 剔除前 {n_before['weight']} → 剔除后 {n_after['weight']}，剔除 {excluded['weight']}")
rep.append(f"- 腰围∈[40,170]: 剔除前 {n_before['waist']} → 剔除后 {n_after['waist']}，剔除 {excluded['waist']}")
rep.append(f"- SBP∈[50,260]: 剔除前 {n_before['sbp']} → 剔除后 {n_after['sbp']}，剔除 {excluded['sbp']}")
rep.append("")

# mvpa distribution
rep.append("")
rep.append("## MVPA 分布（含缺失）")
rep.append(f"- MVPA=0: {int((out['mvpa']==0).sum())} | MVPA=1: {int((out['mvpa']==1).sum())} | 缺失: {int(out['mvpa'].isna().sum())}")
rep.append("")
rep.append("## 建议纳入(基线有年龄且>=45)样本量: " + str(int(out['age_ge45'].sum())))

with open(OUT + r"\step04a_charls_report.md", "w", encoding="utf-8") as f:
    f.write("\n".join(rep))
print("CHARLS baseline written; n=", len(out), " age>=45:", int(out["age_ge45"].sum()))
print("MVPA 0/1/miss:", int((out['mvpa']==0).sum()), int((out['mvpa']==1).sum()), int(out['mvpa'].isna().sum()))