"""
STEP-04c: ELSA baseline extraction (Wave 2 = 2004-2005, baseline)
Variables (handbook §8):
  id_uniq  : idauniq
  age      : r2agey            (>=45, D6)
  sex      : ragender
  educ     : raeducl           (3-tier, D10)
  marital  : r2mstat           (married/partnered=1 -> D10)
  bmi      : r2mbmi (nurse measured; W2 is nurse wave)
  height   : r2mheight
  weight   : r2mweight
  waist    : r2mwaist
  rhr      : r2pulse
  sbp      : r2systo
  mvpa     : (r2vgactx_e=2 | r2mdactx_e=2)  (D11 weekly>=2)
  smoke_ever : r2smokev   smoke_now: r2smoken
  drink    : r2drink
  diseases : r2hibpe/diabe/cancre/lunge/hearte/stroke
  mobilsev_base : r2mobilsev ; adl_base: r2adlfive
D12 ranges applied.
Output: output/elsa_baseline.csv + output/step04c_elsa_report.md
"""
from pathlib import Path
import numpy as np
import pandas as pd
import pyreadstat

SRC = str(Path(__file__).resolve().parents[3] / "data" / "Harmonized ELSA" / "gh_elsa_h.sav")
OUT = str(Path(__file__).resolve().parents[1] / "output")

cols = ["idauniq","ragender","raeducl","r2agey","r2mbmi","r2mheight","r2mweight","r2mwaist",
        "r2systo","r2pulse","r2vgactx_e","r2mdactx_e","r2smokev","r2smoken","r2drink","r2mstat",
        "r2hibpe","r2diabe","r2cancre","r2lunge","r2hearte","r2stroke","r2mobilsev","r2adlfive"]
df, meta = pyreadstat.read_sav(SRC, usecols=cols)
def to_num(s):
    return pd.to_numeric(s, errors="coerce")

out = pd.DataFrame()
out["pid"] = df["idauniq"]
out["cohort"] = "ELSA"
out["age"] = to_num(df["r2agey"])
out["sex"] = to_num(df["ragender"])
out["educ"] = to_num(df["raeducl"])
m = to_num(df["r2mstat"])
out["marital"] = pd.Series(np.where(m.isin([1, 3]), 1, 0), index=m.index)
out["marital"] = out["marital"].where(m.notna(), pd.NA)
out["bmi"] = to_num(df["r2mbmi"])
out["height"] = to_num(df["r2mheight"])
out["weight"] = to_num(df["r2mweight"])
out["waist"] = to_num(df["r2mwaist"])
out["rhr"] = to_num(df["r2pulse"])
out["sbp"] = to_num(df["r2systo"])

# D12/D13 exclusion
n_before = {c: int(out[c].notna().sum()) for c in ["bmi","height","weight","waist","sbp"]}
out["bmi"] = out["bmi"].where(out["bmi"].between(10, 60), pd.NA)
out["height"] = out["height"].where(out["height"].between(1.0, 2.2), pd.NA)
out["weight"] = out["weight"].where(out["weight"].between(30, 200), pd.NA)
out["waist"] = out["waist"].where(out["waist"].between(40, 170), pd.NA)
out["sbp"]   = out["sbp"].where(out["sbp"].between(50, 260), pd.NA)
n_after = {c: int(out[c].notna().sum()) for c in n_before}
excluded = {c: n_before[c] - n_after[c] for c in n_before}
print("D12/D13 excluded:", excluded)

# MVPA (D11): vgactx_e=2 (more than once per week)
vg = to_num(df["r2vgactx_e"]); md = to_num(df["r2mdactx_e"])
vg_known = vg.notna(); md_known = md.notna()
vg_val = (vg == 2); md_val = (md == 2)
def mvpa(r):
    vk, mk = r["_vk"], r["_mk"]
    vv, mv = r["_vv"], r["_mv"]
    if vk and mk: return int(vv or mv)
    if vk: return int(vv)
    if mk: return int(mv)
    return pd.NA
out["_vk"]=vg_known; out["_mk"]=md_known; out["_vv"]=vg_val; out["_mv"]=md_val
out["mvpa"] = out.apply(mvpa, axis=1)
out.drop(columns=["_vk","_mk","_vv","_mv"], inplace=True)

out["smoke_ever"] = to_num(df["r2smokev"])
out["smoke_now"]  = to_num(df["r2smoken"])
out["drink"]      = to_num(df["r2drink"])
for src,dst in [("r2hibpe","hibp"),("r2diabe","diab"),("r2cancre","cancer"),
                ("r2lunge","lung"),("r2hearte","heart"),("r2stroke","stroke")]:
    out[dst] = to_num(df[src])
out["mobilsev_base"] = to_num(df["r2mobilsev"])
out["adl_base"]      = to_num(df["r2adlfive"])
out["age_ge45"] = (out["age"] >= 45)

out.to_csv(OUT + r"\elsa_baseline.csv", index=False, encoding="utf-8-sig")

rep = ["# STEP-04c ELSA 基线提取报告", "",
       f"- 总行数: {len(out)}",
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
for c,x in [("bmi",excluded['bmi']),("height",excluded['height']),
            ("weight",excluded['weight']),("waist",excluded['waist']),("sbp",excluded['sbp'])]:
    rep.append(f"- {c}: 剔除 {x}（{n_before[c]} -> {n_after[c]}）")
rep.append("")
rep.append("## MVPA")
rep.append(f"- MVPA=0: {int((out['mvpa']==0).sum())} | MVPA=1: {int((out['mvpa']==1).sum())} | 缺失: {int(out['mvpa'].isna().sum())}")

with open(OUT + r"\step04c_elsa_report.md", "w", encoding="utf-8") as f:
    f.write("\n".join(rep))
print("ELSA baseline written; n=", len(out), " age>=45:", int(out["age_ge45"].sum()))
print("MVPA 0/1/miss:", int((out['mvpa']==0).sum()), int((out['mvpa']==1).sum()), int(out['mvpa'].isna().sum()))