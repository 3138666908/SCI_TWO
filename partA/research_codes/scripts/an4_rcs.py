"""
AN-4: RCS (restricted cubic spline) dose-response of eCRF -> mobility limitation
Model 3 covariates, reference = eCRF median, 4 knots at 5/35/65/95 percentiles.
Builds RCS design columns per cohort, fits Cox, computes HR curve vs median with 95% CI.
Output: an4_rcs_<cohort>.png (HR curve), an4_rcs_results.csv, an4_rcs_report.md
"""
from pathlib import Path
import pandas as pd
import numpy as np
import scipy.stats as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from lifelines import CoxPHFitter

OUT = str(Path(__file__).resolve().parents[1] / "output")
plt.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False

df = pd.read_csv(OUT + r"\final_analysis_pooled.csv")
df = df[df["ecrf_group"].notna()].copy()
for c in ["age","sex","educ","marital","sbp","smoke_status","drink"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
df["followup_years"] = pd.to_numeric(df["followup_years"], errors="coerce")
df["mobility_event"] = pd.to_numeric(df["mobility_event"], errors="coerce").fillna(0).astype(int)

def rcs_basis(x, knots):
    """restricted cubic spline basis (Harrell). Returns matrix [x, X1..Xk-2]."""
    k = np.asarray(knots, dtype=float)
    x = np.asarray(x, dtype=float)
    K = len(k)
    res = np.zeros((len(x), K - 1))
    res[:, 0] = x
    for j in range(1, K - 2 + 1):  # j=1..K-2
        idx = j - 1
        hj = np.clip(x - k[idx], 0, None) ** 3 \
             - np.clip(x - k[K - 2], 0, None) ** 3 * ((k[K-1] - k[idx]) / (k[K-1] - k[K-2])) \
             + np.clip(x - k[K - 1], 0, None) ** 3 * ((k[K-2] - k[idx]) / (k[K-1] - k[K-2]))
        res[:, j] = hj
    return res

cohort_order = ["CHARLS", "ELSA", "HRS"]
allres = []
rep = ["# AN-4 RCS 剂量-反应分析报告（模型3调整，参照=中位eCRF）", ""]
fig, axes = plt.subplots(1, 3, figsize=(18, 5))

for ax, cohort in zip(axes, cohort_order):
    d = df[df["cohort"] == cohort].copy()
    d["female"] = (d["sex"] == 2).astype(int)
    d["educ_hs"] = (d["educ"] == 2).astype(int)
    d["educ_college"] = (d["educ"] == 3).astype(int)
    d["smk_former"] = (d["smoke_status"] == 1).astype(int)
    d["smk_current"] = (d["smoke_status"] == 2).astype(int)
    covs = ["age", "female", "marital", "educ_hs", "educ_college", "smk_former",
            "smk_current", "drink", "sbp"]
    d = d[d["ecrf"].notna()].copy()
    ecrf = d["ecrf"].astype(float)
    knots = np.nanpercentile(ecrf, [5, 35, 65, 95])
    B = rcs_basis(ecrf.values, knots)
    for j in range(B.shape[1]):
        d[f"rcs{j}"] = B[:, j]
    cols = [f"rcs{j}" for j in range(B.shape[1])] + covs
    dfm = d[["followup_years", "mobility_event"] + cols].dropna()
    if len(dfm) < 60:
        rep.append(f"## {cohort}: 样本不足({len(dfm)})")
        continue
    cph = CoxPHFitter(penalizer=0)
    cph.fit(dfm, duration_col="followup_years", event_col="mobility_event")
    bvec = cph.params_
    covm = cph.variance_matrix_

    ref = float(np.nanmedian(ecrf))
    xgrid = np.linspace(np.nanpercentile(ecrf, 1), np.nanpercentile(ecrf, 99), 60)
    Bref = rcs_basis(np.array([ref]), knots)[0]
    Bgrid = rcs_basis(xgrid, knots)
    # HR relative to median: only rcs* terms differ
    terms = [f"rcs{j}" for j in range(B.shape[1])]
    # center design at ref
    dB = Bgrid - Bref
    beta_rcs = np.array([bvec[t] for t in terms])
    lo_hi = dB @ beta_rcs  # log HR
    hr = np.exp(lo_hi)
    # variance of log HR
    var_rcs = np.diag(covm.loc[terms, terms])
    var_lo_hi = np.sum((dB ** 2) * var_rcs, axis=1)
    lo = np.exp(lo_hi - 1.96 * np.sqrt(var_lo_hi))
    hi = np.exp(lo_hi + 1.96 * np.sqrt(var_lo_hi))

    ax.plot(xgrid, hr, color="tab:red", lw=2, label=f"{cohort}")
    ax.fill_between(xgrid, lo, hi, color="tab:red", alpha=0.15)
    ax.axhline(1.0, color="grey", lw=1, ls="--")
    ax.axvline(ref, color="grey", lw=1, ls=":")
    ax.set_title(f"{cohort} (n={len(dfm)})")
    ax.set_xlabel("eCRF (METs)")
    ax.set_ylabel("HR (95% CI) vs median")
    ax.set_ylim(0.1, 3.5)

    rep.append(f"## {cohort}  (n={len(dfm)})")
    rep.append(f"- knots(5/35/65/95%): {[round(x,2) for x in knots]}")
    rep.append(f"- 参照 eCRF = 中位数 = {ref:.2f}")
    rep.append("- 样条项联合显著性检验：")
    # Wald joint test of rcs1..rcsk-2 (nonlinear terms) and overall
    terms_nl = terms[1:]  # exclude linear x? keep: linear is rcs0
    cov_c = covm.loc[terms, terms].values
    b_c = np.array([bvec[t] for t in terms])
    joint = b_c @ np.linalg.pinv(cov_c) @ b_c
    p_joint = st.chi2.sf(joint, len(b_c))
    b_nl = np.array([bvec[t] for t in terms_nl])
    cov_nl = covm.loc[terms_nl, terms_nl].values
    if len(terms_nl) > 0:
        joint_nl = b_nl @ np.linalg.pinv(cov_nl) @ b_nl
        p_nl = st.chi2.sf(joint_nl, len(terms_nl))
    else:
        p_nl = np.nan
    rep.append(f"- 总样条 Wald: chi2={joint:.2f}, p={p_joint:.2e}")
    rep.append(f"- 非线性项 Wald: chi2={joint_nl:.2f}, p={p_nl:.4f}")
    allres.append({"cohort": cohort, "n": len(dfm), "median_ecrf": ref,
                   "joint_p": p_joint, "nonlinear_p": p_nl,
                   "x": xgrid.tolist(), "hr": hr.tolist(),
                   "lo": lo.tolist(), "hi": hi.tolist()})
fig.tight_layout()
fig.savefig(OUT + r"\an4_rcs_by_cohort.png", dpi=150)
pd.DataFrame(allres).to_csv(OUT + r"\an4_rcs_results.csv", index=False, encoding="utf-8-sig")
with open(OUT + r"\an4_rcs_report.md", "w", encoding="utf-8") as f:
    f.write("\n".join(rep))
print("\n".join(rep))
print("saved an4_rcs_by_cohort.png")