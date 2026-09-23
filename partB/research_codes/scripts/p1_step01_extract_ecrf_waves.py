"""
p1_step01_extract_ecrf_waves.py  (PartB / 阶段一 - 数据准备)

目的
  从源数据 data 重算逐波次 eCRF，仅针对 pooled 整合版(final_analysis_pooled.csv)的 17,696 人。
  只提取"可测波次"（eCRF 需 bmi+waist+pulse 同时可得）：
    CHARLS : W1/W2/W3 -> 2011/2013/2015
    ELSA   : W2/W4/W6 -> 2004/2008/2012
    HRS    : W8..W14  -> 2006..2018

规则（与 partA step08_ecrf.py 一致）
  eCRF 公式：男 21.2870 + age*0.1654 - age^2*0.0023 - bmi*0.2318 - waist*0.0337
                       - rhr*0.0390 + mvpa*0.6351 - smoke_now*0.4263
             女 14.7873 + age*0.1159 - age^2*0.0017 - bmi*0.1534 - waist*0.0085
                       - rhr*0.0364 + mvpa*0.5987 - smoke_now*0.2994
  D12/D13 过滤：bmi∈[10,60]，waist∈[40,170]（越界置缺失）
  6 项输入齐全才计算 eCRF；否则 ecrf=NaN，行保留（供轨迹模型按缺失处理）。
  MVPA 定义按各库 PartA 口径；sex: 1=男 2=女。

输出
  partB\\data\\ecrf_long_CHARLS.xlsx / ecrf_long_ELSA.xlsx / ecrf_long_HRS.xlsx
  列：pid, cohort, wave, wave_year, age, sex, bmi, waist, rhr, mvpa, smoke_now, ecrf
  报告：partB\\research_codes\\output\\p1_step01_extract_report.md
"""
from pathlib import Path
import numpy as np
import pandas as pd
import pyreadstat

DATA = str(Path(__file__).resolve().parents[2] / "data")
OUT = str(Path(__file__).resolve().parents[1] / "output")
SRC = str(Path(__file__).resolve().parents[3] / "data")
CHRLS_SRC = SRC + r"\Harmonized CHARLS\H_CHARLS_D_Data.dta"
ELSA_SRC = SRC + r"\Harmonized ELSA\gh_elsa_h.sav"
HRS_HARM = SRC + r"\Harmonized HRS\H_HRS_d.dta"
RAND_SRC = SRC + r"\Harmonized HRS\randhrs1992_2022v1.sav"

WAVES = {
    "CHARLS": {1: 2011, 2: 2013, 3: 2015},
    "ELSA": {2: 2004, 4: 2008, 6: 2012},
    "HRS": {8: 2006, 9: 2008, 10: 2010, 11: 2012, 12: 2014, 13: 2016, 14: 2018},
}
COLS = ["pid", "cohort", "wave", "wave_year", "age", "sex",
        "bmi", "waist", "rhr", "mvpa", "smoke_now", "ecrf"]


def to_num(s):
    return pd.to_numeric(s, errors="coerce")


def apply_range(s, lo, hi):
    return s.where(s.between(lo, hi), np.nan)


def mvpa_dual(vg_known, vg_val, md_known, md_val):
    vg_known = vg_known.fillna(False).astype(bool)
    md_known = md_known.fillna(False).astype(bool)
    vg_val = vg_val.fillna(False).astype(bool)
    md_val = md_val.fillna(False).astype(bool)
    out = pd.Series(np.nan, index=vg_known.index, dtype="float")
    both = vg_known & md_known
    ov = vg_known & ~md_known
    om = md_known & ~vg_known
    out[both] = (vg_val | md_val)[both].astype(float)
    out[ov] = vg_val[ov].astype(float)
    out[om] = md_val[om].astype(float)
    return out


def ecrf_calc(d):
    age = to_num(d["age"]); bmi = to_num(d["bmi"]); waist = to_num(d["waist"])
    rhr = to_num(d["rhr"]); mvpa = to_num(d["mvpa"]); smk = to_num(d["smoke_now"])
    sex = to_num(d["sex"])
    ecrf = pd.Series(np.nan, index=d.index, dtype="float")
    ok = age.notna() & bmi.notna() & waist.notna() & rhr.notna() & mvpa.notna() & smk.notna()
    m = ok & (sex == 1)
    f = ok & (sex == 2)
    ecrf[m] = (21.2870 + age[m] * 0.1654 - (age[m] ** 2) * 0.0023 - bmi[m] * 0.2318
               - waist[m] * 0.0337 - rhr[m] * 0.0390 + mvpa[m] * 0.6351 - smk[m] * 0.4263)
    ecrf[f] = (14.7873 + age[f] * 0.1159 - (age[f] ** 2) * 0.0017 - bmi[f] * 0.1534
               - waist[f] * 0.0085 - rhr[f] * 0.0364 + mvpa[f] * 0.5987 - smk[f] * 0.2994)
    return ecrf


def wave_df(pid, wave, age, sex, bmi, waist, rhr, mvpa, smoke_now):
    d = pd.DataFrame({"pid": pid, "wave": wave, "age": age, "sex": sex,
                      "bmi": bmi, "waist": waist, "rhr": rhr,
                      "mvpa": mvpa, "smoke_now": smoke_now})
    d["ecrf"] = ecrf_calc(d)
    return d


def build_charls():
    waves = WAVES["CHARLS"]
    cols = ["ID", "ragender"]
    for w in waves:
        cols += ["r%dagey" % w, "r%dmbmi" % w, "r%dmwaist" % w, "r%dpulse" % w,
                 "r%dvgact_c" % w, "r%dvgactx_c" % w, "r%dmdact_c" % w,
                 "r%dmdactx_c" % w, "r%dsmoken" % w]
    df, _ = pyreadstat.read_dta(CHRLS_SRC, usecols=cols)
    pid = to_num(df["ID"]).astype("Int64")
    sex = to_num(df["ragender"])
    frames = []
    for w, y in waves.items():
        vgc = to_num(df["r%dvgact_c" % w]); vgx = to_num(df["r%dvgactx_c" % w])
        mdc = to_num(df["r%dmdact_c" % w]); mdx = to_num(df["r%dmdactx_c" % w])
        mvpa = mvpa_dual(vgc.notna() & vgx.notna(), (vgc == 1) & (vgx >= 2),
                         mdc.notna() & mdx.notna(), (mdc == 1) & (mdx >= 2))
        frames.append(wave_df(pid, w,
                              to_num(df["r%dagey" % w]),
                              sex,
                              apply_range(to_num(df["r%dmbmi" % w]), 10, 60),
                              apply_range(to_num(df["r%dmwaist" % w]), 40, 170),
                              to_num(df["r%dpulse" % w]),
                              mvpa,
                              to_num(df["r%dsmoken" % w])))
    return pd.concat(frames, ignore_index=True)


def build_elsa():
    waves = WAVES["ELSA"]
    cols = ["idauniq", "ragender"]
    for w in waves:
        cols += ["r%dagey" % w, "r%dmbmi" % w, "r%dmwaist" % w, "r%dpulse" % w,
                 "r%dvgactx_e" % w, "r%dmdactx_e" % w, "r%dsmoken" % w]
    df, _ = pyreadstat.read_sav(ELSA_SRC, usecols=cols)
    pid = to_num(df["idauniq"]).astype("Int64")
    sex = to_num(df["ragender"])
    frames = []
    for w, y in waves.items():
        vg = to_num(df["r%dvgactx_e" % w]); md = to_num(df["r%dmdactx_e" % w])
        mvpa = mvpa_dual(vg.notna(), (vg == 2), md.notna(), (md == 2))
        frames.append(wave_df(pid, w,
                              to_num(df["r%dagey" % w]),
                              sex,
                              apply_range(to_num(df["r%dmbmi" % w]), 10, 60),
                              apply_range(to_num(df["r%dmwaist" % w]), 40, 170),
                              to_num(df["r%dpulse" % w]),
                              mvpa,
                              to_num(df["r%dsmoken" % w])))
    return pd.concat(frames, ignore_index=True)


def build_hrs():
    waves = WAVES["HRS"]
    hcols = ["hhidpn"] + ["r%dpulse" % w for w in waves]
    hd, _ = pyreadstat.read_dta(HRS_HARM, usecols=hcols)
    hd["pid"] = to_num(hd["hhidpn"]).astype("Int64")
    rcols = ["HHIDPN", "RAGENDER"]
    for w in waves:
        rcols += ["R%dAGEY_E" % w, "R%dPMBMI" % w, "R%dPMWAIST" % w,
                  "R%dVGACTX" % w, "R%dMDACTX" % w, "R%dSMOKEN" % w]
    rd, _ = pyreadstat.read_sav(RAND_SRC, usecols=rcols)
    rd["pid"] = to_num(rd["HHIDPN"]).astype("Int64")
    df = hd.merge(rd, on="pid", how="inner")
    sex = to_num(df["RAGENDER"])
    frames = []
    for w, y in waves.items():
        vg = to_num(df["R%dVGACTX" % w]); md = to_num(df["R%dMDACTX" % w])
        mvpa = mvpa_dual(vg.notna(), vg.isin([1, 2]), md.notna(), md.isin([1, 2]))
        frames.append(wave_df(df["pid"], w,
                              to_num(df["R%dAGEY_E" % w]),
                              sex,
                              apply_range(to_num(df["R%dPMBMI" % w]), 10, 60),
                              apply_range(to_num(df["R%dPMWAIST" % w]) * 2.54, 40, 170),
                              to_num(df["r%dpulse" % w]),
                              mvpa,
                              to_num(df["R%dSMOKEN" % w])))
    return pd.concat(frames, ignore_index=True)


def main():
    pooled = pd.read_csv(DATA + r"\final_analysis_pooled.csv",
                         usecols=["pid", "cohort", "ecrf"])
    pooled["pid"] = to_num(pooled["pid"]).astype("Int64")
    print("pooled n =", len(pooled))

    builders = {"CHARLS": build_charls, "ELSA": build_elsa, "HRS": build_hrs}
    rep = ["# p1_step01 逐波 eCRF 提取报告", ""]
    rep.append("- 输入：`data`（源数据）+ `final_analysis_pooled.csv`（人员名单）")
    rep.append("- 输出：`partB\\data\\ecrf_long_<cohort>.xlsx`")
    rep.append("- 规则：eCRF 公式同 partA step08；bmi∈[10,60]、waist∈[40,170]；6 项齐全才算 eCRF")
    rep.append("")

    for cohort, bf in builders.items():
        pool_pids = pooled.loc[pooled["cohort"] == cohort, "pid"]
        ext = bf()
        ext = ext[ext["pid"].isin(set(pool_pids))]
        waves = WAVES[cohort]

        frames = []
        for w, y in waves.items():
            frames.append(pd.DataFrame({"pid": pool_pids, "cohort": cohort,
                                        "wave": w, "wave_year": y}))
        tmpl = pd.concat(frames, ignore_index=True)
        out = tmpl.merge(ext, on=["pid", "wave"], how="left")
        out = out[COLS].sort_values(["pid", "wave"]).reset_index(drop=True)
        out["ecrf"] = pd.to_numeric(out["ecrf"], errors="coerce")

        path = DATA + r"\ecrf_long_%s.xlsx" % cohort
        out.to_excel(path, index=False)

        rep.append("## %s" % cohort)
        rep.append("- pooled 人数：%d；源数据中匹配到：%d" %
                   (len(pool_pids), int(out.loc[out["age"].notna() |
                                                out["ecrf"].notna(), "pid"].nunique())))
        rep.append("- 输出总行数：%d（人数 × 波次）" % len(out))
        rep.append("")
        rep.append("| wave | year | 行数 | eCRF 非缺失 | eCRF 缺失 | eCRF 均值±SD | eCRF 范围 |")
        rep.append("|---|---|---|---|---|---|---|")
        for w, y in waves.items():
            s = out.loc[out["wave"] == w, "ecrf"]
            nn = int(s.notna().sum())
            rng = ("%.2f ~ %.2f" % (s.min(), s.max())) if nn else "-"
            ms = ("%.2f ± %.2f" % (s.mean(), s.std())) if nn else "-"
            rep.append("| W%d | %d | %d | %d | %d | %s | %s |" %
                       (w, y, len(s), nn, int(s.isna().sum()), ms, rng))
        rep.append("")

    # baseline cross-check vs pooled ecrf
    rep.append("## 基线波 eCRF 与 pooled 一致性核对")
    rep.append("")
    rep.append("| cohort | 基线波 | 两边均非缺失 n | 平均绝对差 | 最大绝对差 | 相关系数 |")
    rep.append("|---|---|---|---|---|---|")
    base_wave = {"CHARLS": 1, "ELSA": 2, "HRS": 8}
    for cohort, w in base_wave.items():
        p = pooled[pooled["cohort"] == cohort][["pid", "ecrf"]].rename(columns={"ecrf": "ecrf_pooled"})
        f = DATA + r"\ecrf_long_%s.xlsx" % cohort
        x = pd.read_excel(f)
        x = x[x["wave"] == w][["pid", "ecrf"]].rename(columns={"ecrf": "ecrf_ext"})
        m = p.merge(x, on="pid", how="inner")
        m = m[m["ecrf_pooled"].notna() & m["ecrf_ext"].notna()]
        if len(m):
            diff = (m["ecrf_pooled"] - m["ecrf_ext"]).abs()
            rep.append("| %s | W%d | %d | %.4f | %.4f | %.6f |" %
                       (cohort, w, len(m), diff.mean(), diff.max(),
                        m["ecrf_pooled"].corr(m["ecrf_ext"])))
        else:
            rep.append("| %s | W%d | 0 | - | - | - |" % (cohort, w))
    rep.append("")
    rep.append("> 注：基线波两边用相同公式与输入，应完全一致（差异应≈0）。")

    with open(OUT + r"\p1_step01_extract_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(rep))
    print("DONE")


if __name__ == "__main__":
    main()
