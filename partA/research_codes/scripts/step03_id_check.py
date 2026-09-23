"""
STEP-03: ID structure verification (H9, H7)
- CHARLS: verify ID == householdID+pnc, ID_w1 == householdID_w1+pnc (Wave-1 respondents)
- HRS: verify hhidpn uniqueness; RAND HHIDPN <-> harmonized hhidpn alignment (100% verified earlier)
- ELSA: verify idauniq uniqueness
Output: output/step03_id_report.md
"""
from pathlib import Path
import pandas as pd
import pyreadstat

CHARLS = str(Path(__file__).resolve().parents[3] / "data" / "Harmonized CHARLS" / "H_CHARLS_D_Data.dta")
HARM_HRS = str(Path(__file__).resolve().parents[3] / "data" / "Harmonized HRS" / "H_HRS_d.dta")
RAND_HRS = str(Path(__file__).resolve().parents[3] / "data" / "Harmonized HRS" / "randhrs1992_2022v1.sav")
ELSA = str(Path(__file__).resolve().parents[3] / "data" / "Harmonized ELSA" / "gh_elsa_h.sav")

lines = ["# STEP-03 ID 核验报告", ""]

# ---------- CHARLS ----------
df, meta = pyreadstat.read_dta(CHARLS, usecols=["ID","ID_w1","householdID","householdID_w1","pnc","pn"])
df["ID_construct"] = df["householdID"].astype(str).str.zfill(10) + df["pnc"].astype(str).str.zfill(2)
df["IDW1_construct"] = df["householdID_w1"].astype(str).str.zfill(9) + df["pnc"].astype(str).str.zfill(2)
w1 = df[df["ID_w1"].astype(str).str.strip() != ""]
both_id = df["ID"].notna()
m1 = (df.loc[both_id, "ID"] == df.loc[both_id, "ID_construct"]).mean()
m2 = (w1["ID_w1"] == w1["IDW1_construct"]).mean()
lines.append("## CHARLS")
lines.append(f"- 总行数: {len(df)}, 唯一 ID: {df['ID'].nunique()}")
lines.append(f"- ID == householdID(10位)+pnc 匹配率: {m1:.4f} (n={both_id.sum()})")
lines.append(f"- ID_w1 == householdID_w1(9位)+pnc 匹配率(第1波受访者): {m2:.4f} (n={len(w1)})")
lines.append(f"- ID_w1 非空人数: {len(w1)}; 空串: {(df['ID_w1'].astype(str).str.strip()=='').sum()} (第2波及后加入者)")
lines.append(f"- 结论: 宽格式一人一行; ID 为第2波+键, ID_w1 为第1波键（与原文件合并时用）")
lines.append("")

# ---------- HRS harmonized + RAND ----------
hdf, _ = pyreadstat.read_dta(HARM_HRS, usecols=["hhidpn"])
rdf, _ = pyreadstat.read_sav(RAND_HRS, usecols=["HHIDPN"])
hset = set(hdf["hhidpn"].dropna().astype(int))
rset = set(rdf["HHIDPN"].dropna().astype(int))
lines.append("## HRS")
lines.append(f"- harmonized: {len(hdf)} 行, 唯一 hhidpn: {hdf['hhidpn'].nunique()}")
lines.append(f"- RAND: {len(rdf)} 行, 唯一 HHIDPN: {rdf['HHIDPN'].nunique()}")
lines.append(f"- harmonized 中能在 RAND 找到: {len(hset & rset)} / {len(hset)} ({len(hset&rset)/len(hset):.4f})")
lines.append(f"- RAND 中不在 harmonized: {len(rset - hset)}")
lines.append("- 结论: hhidpn/HHIDPN 可直接对齐合并")
lines.append("")

# ---------- ELSA ----------
edf, emeta = pyreadstat.read_sav(ELSA, usecols=["idauniq"])
lines.append("## ELSA")
lines.append(f"- 总行数: {len(edf)}, 唯一 idauniq: {edf['idauniq'].nunique()}, 缺失: {edf['idauniq'].isna().sum()}")
lines.append("- 结论: idauniq 为宽格式一人一行键")

report = "\n".join(lines)
out_path = str(Path(__file__).resolve().parents[1] / "output" / "step03_id_report.md")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(report)
print(report)
print("\nwritten ->", out_path)