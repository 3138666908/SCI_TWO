"""
STEP-11: Merge & quality check
- Concatenate ecrf_<db>.csv (analysis sample with eCRF + group + outcome) into one pooled dataset.
- Standardize column set; drop redundant raw-id dup columns; ensure comparable coding already in place.
- Output quality report: missing rate, distributions, duplicates, cross-db alignment.
Output: output/final_analysis_pooled.csv + output/step11_quality_report.md
"""
from pathlib import Path
import pandas as pd
import numpy as np

OUT = str(Path(__file__).resolve().parents[1] / "output")

dbs = {}
cols_union = None
for db in ["CHARLS","ELSA","HRS"]:
    d = pd.read_csv(OUT + rf"\ecrf_{db}.csv")
    d = d.rename(columns=lambda c: c.strip().lower())
    # ensure consistent key col
    d = d.rename(columns={"hhidpn":"pid","idauniq":"pid","ID":"pid"})
    if "pid" not in d.columns:
        d["pid"] = d.index.astype(str)
    dbs[db] = d
    if cols_union is None:
        cols_union = set(d.columns)
    else:
        cols_union = cols_union.union(d.columns)

pooled = pd.concat(dbs.values(), ignore_index=True, sort=False)
# enforce consistent types
for c in pooled.columns:
    if c in ["pid","cohort"]:
        continue
    try:
        pooled[c] = pd.to_numeric(pooled[c], errors="coerce")
    except Exception:
        pass
pooled["cohort"] = pooled["cohort"].astype(str).str.strip()
pooled["pid"] = pooled["pid"].astype(str).str.strip()

# dedupe check
dup = pooled.duplicated(subset=["pid","cohort"]).sum()
pooled.to_csv(OUT + r"\final_analysis_pooled.csv", index=False, encoding="utf-8-sig")

keep = ["pid","cohort","sex","age","educ","marital","bmi","waist","rhr","sbp","mvpa",
        "smoke_status","drink","hibp","diab","cancer","lung","heart","stroke",
        "ecrf","ecrf_group","mobilsev_base","mobility_event","followup_years"]
present_keep = [c for c in keep if c in pooled.columns]
missing_keep = [c for c in keep if c not in pooled.columns]

rep = ["# STEP-11 合并与质量检查报告", "",
       f"- 三库合计行数: {len(pooled)}",
       f"- 各库样本量: {pooled.groupby('cohort').size().to_dict()}",
       f"- 重复 (pid,cohort): {dup}",
       f"- 期望统一列 {len(keep)} 个；缺少: {missing_keep}",
       "",
       "## 三库各列非缺失计数", "",
       "| var | CHARLS | ELSA | HRS |", "|---|---|---|---|"]
order = present_keep
for c in order:
    row = []
    for db in ["CHARLS","ELSA","HRS"]:
        sub = pooled[pooled["cohort"]==db]
        n = int(sub[c].notna().sum()) if c in sub.columns else 0
        row.append(str(n))
    rep.append(f"| {c} | {' | '.join(row)} |")
rep.append("")
rep.append("## 统一列缺失率（合并后）")
rep.append("")
rep.append("| var | non-missing | missing | missing% |")
rep.append("|---|---|---|---|")
for c in order:
    n = pooled[c].notna().sum()
    pct = round(100 * pooled[c].isna().mean(), 1)
    rep.append(f"| {c} | {int(n)} | {int(pooled[c].isna().sum())} | {pct}% |")
rep.append("")
rep.append("## ecrf_group 分布（三库）")
rep.append(pooled["ecrf_group"].value_counts(dropna=False).sort_index().to_string())
rep.append("")
rep.append("## 结局分布（mobility_event）")
rep.append(pooled["mobility_event"].value_counts(dropna=False).sort_index().to_string())
rep.append("")
rep.append("## eCRF 描述（按库）")
rep.append(pooled.groupby("cohort")["ecrf"].describe().to_string())

with open(OUT + r"\step11_quality_report.md", "w", encoding="utf-8") as f:
    f.write("\n".join(rep))
print("pooled written:", len(pooled))
print("dup:", dup)
print("keep missing:", missing_keep)