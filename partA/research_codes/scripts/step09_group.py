"""
STEP-09: eCRF grouping by sex-stratified quintiles (D9)
- Within each sex (1=male, 2=female), compute quintile cut-points of eCRF.
- Assign: Q1=low(1), Q2-Q3=medium(2), Q4-Q5=high(3).
- Grouping only among those with eCRF computed.
Output: output/ecrf_<db>.csv adds ecrf_group + output/step09_<db>_report.md
"""
from pathlib import Path
import pandas as pd
import numpy as np
from scipy import stats

OUT = str(Path(__file__).resolve().parents[1] / "output")

def group_db(db):
    d = pd.read_csv(OUT + rf"\ecrf_{db}.csv")
    sex = pd.to_numeric(d["sex"], errors="coerce")
    ecrf = pd.to_numeric(d["ecrf"], errors="coerce")
    group = pd.Series(pd.NA, index=d.index, dtype="Int64")
    cuts = {}
    for s, sname in [(1,"male"),(2,"female")]:
        vals = ecrf[sex == s]
        vals = vals.dropna()
        if len(vals) >= 5:
            q = np.nanpercentile(vals, [20,40,60,80])
            cuts[sname] = q
            g = pd.cut(vals, [-np.inf, q[0], q[2], np.inf], labels=[1,2,3], right=False)
            g = pd.Series(g.values, index=vals.index).astype("Int64")
            lidx = g.index[g.notna()]
            group.loc[lidx] = g.loc[lidx]
        else:
            cuts[sname] = None
            print(f"[{db}] warning: too few {sname} with eCRF")
    d["ecrf_group"] = group
    d.to_csv(OUT + rf"\ecrf_{db}.csv", index=False, encoding="utf-8-sig")

    rep = [f"# STEP-09 {db} eCRF 分组（按性别分层五分位，D9）", ""]
    for s, sn in [(1,"男性"),(2,"女性")]:
        if cuts[("male" if s==1 else "female")] is not None:
            q = cuts[("male" if s==1 else "female")]
            rep.append(f"## {sn} 五分位切点（eCRF）: Q1<{q[0]:.2f}, Q2<{q[1]:.2f}, Q3<{q[2]:.2f}, Q4<{q[3]:.2f}")
            rep.append("")
            v = d[d["sex"]==s]["ecrf_group"]
            rep.append(v.value_counts(dropna=False).sort_index().to_string())
            rep.append("")
    rep.append("## 三组汇总（两性合并）")
    rep.append(d["ecrf_group"].value_counts(dropna=False).sort_index().to_string())
    rep.append("")
    rep.append(f"### 未分组（无 eCRF）人数: {int(d['ecrf_group'].isna().sum())}")
    with open(OUT + rf"\step09_{db}_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(rep))
    print(f"[{db}] group counts (1/2/3/NA):",
          int((d['ecrf_group']==1).sum()), int((d['ecrf_group']==2).sum()),
          int((d['ecrf_group']==3).sum()), int(d['ecrf_group'].isna().sum()))

for db in ["CHARLS","ELSA","HRS"]:
    group_db(db)
print("ALL STEP-09 DONE")