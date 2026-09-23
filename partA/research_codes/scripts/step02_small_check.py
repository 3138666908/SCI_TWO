"""
STEP-02: Small-sample load & variable verification (H9)
Loads 5 rows per database, confirms every study variable exists with expected type/range.
Output: output/step02_check_<db>.md
"""
from pathlib import Path
import pandas as pd
import pyreadstat

OUT = str(Path(__file__).resolve().parents[1] / "output")

def check_db(name, path, kind, cols_expected, out_md):
    if kind == "dta":
        df, meta = pyreadstat.read_dta(path, usecols=cols_expected, row_limit=5)
    else:
        df, meta = pyreadstat.read_sav(path, usecols=cols_expected, row_limit=5)
    lines = [f"# STEP-02 小样本核对: {name}", ""]
    lines.append(f"- 读取行数(小样本): {len(df)}")
    present = [c for c in cols_expected if c in df.columns]
    missing = [c for c in cols_expected if c not in df.columns]
    lines.append(f"- 期望变量 {len(cols_expected)} 个；存在 {len(present)}，缺失 {len(missing)}")
    if missing:
        lines.append(f"- **缺失: {missing}**")
    lines.append("")
    lines.append("| 变量 | 类型 | 前5行值 |")
    lines.append("|---|---|---|")
    for c in present:
        t = str(df[c].dtype)
        vals = df[c].tolist()
        lines.append(f"| {c} | {t} | {vals} |")
    txt = "\n".join(lines)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(txt)
    print(f"=== {name} done; present={len(present)} missing={missing}")

cc = ["ID","ragender","raeducl","raeduc_c","r1agey","r1mbmi","r1mheight","r1mweight","r1mwaist",
      "r1systo","r1pulse","r1vgact_c","r1vgactx_c","r1mdact_c","r1mdactx_c","r1smokev","r1smoken",
      "r1drinkev","r1mstat","r1hibpe","r1diabe","r1cancre","r1lunge","r1hearte","r1stroke","r1mobilsev","r1adlfive"]
check_db("CHARLS", str(Path(__file__).resolve().parents[3] / "data" / "Harmonized CHARLS" / "H_CHARLS_D_Data.dta"), "dta", cc,
         OUT + r"\step02_check_CHARLS.md")

hc = ["hhidpn","raeducl","r8mbmi","r8mwaist","r8pulse","r8systo","r8mobilsev","r8adlfive"]
check_db("HRS(har)", str(Path(__file__).resolve().parents[3] / "data" / "Harmonized HRS" / "H_HRS_d.dta"), "dta", hc,
         OUT + r"\step02_check_HRS_har.md")

rc = ["HHIDPN","RAGENDER","R8AGEY_E","RAEDUC","R8MSTAT","R8SMOKEV","R8SMOKEN","R8DRINK",
      "R8VGACTX","R8MDACTX","R8PMBMI","R8PMWAIST","R8BPSYS","R8HIBPE","R8DIABE","R8CANCRE",
      "R8LUNGE","R8HEARTE","R8STROKE"]
check_db("HRS(RAND)", str(Path(__file__).resolve().parents[3] / "data" / "Harmonized HRS" / "randhrs1992_2022v1.sav"), "sav", rc,
         OUT + r"\step02_check_HRS_rand.md")

ec = ["idauniq","ragender","raeducl","r2agey","r2mbmi","r2mheight","r2mweight","r2mwaist",
      "r2systo","r2pulse","r2vgactx_e","r2mdactx_e","r2smokev","r2smoken","r2drink","r2mstat",
      "r2hibpe","r2diabe","r2cancre","r2lunge","r2hearte","r2stroke","r2mobilsev","r2adlfive"]
check_db("ELSA", str(Path(__file__).resolve().parents[3] / "data" / "Harmonized ELSA" / "gh_elsa_h.sav"), "sav", ec,
         OUT + r"\step02_check_ELSA.md")

print("ALL STEP-02 CHECK DONE")