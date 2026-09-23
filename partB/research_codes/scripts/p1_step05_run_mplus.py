"""
p1_step05_run_mplus.py  (PartB / 阶段一 - Mplus 批量拟合)

依据 handbook §5.1（方案 2）与研究者 2026-09-19 决定：
  - HRS：比较 linear/quadratic/cubic 后择优；ELSA：linear。
  - k=1..6；遇 BLRT/VLMR-LRT 转不显著即停（后续阶段判断）。
  - LCGM 先（类内无随机效应, 增长因子方差固定为0），GMM 后（类内随机效应）。
用法：
  python p1_step05_run_mplus.py form     # 功能形式选择(k=1, LGCM)
  python p1_step05_run_mplus.py lcga     # LCGA 类别枚举 k=1..6
  python p1_step05_run_mplus.py gmm      # GMM 类别枚举 k=1..6
  python p1_step05_run_mplus.py pilot    # 单模型测试
输出：research_codes/mplus/*.inp 与 *.out
"""
from pathlib import Path
import os
import subprocess
import sys
import time

MP = str(Path(__file__).resolve().parents[1] / "mplus")
EXE = os.environ.get("MPLUS_EXE", "Mplus.exe")
SEED = 20260919
STARTS = "300 50"
LRTBOOT = 100

TIMES = {"HRS": [0, 4, 8, 12], "ELSA": [0, 4, 8]}
DATA = {"HRS": "data/HRS.dat", "HRS_ge3": "data/HRS_ge3.dat",
        "ELSA": "data/ELSA.dat", "ELSA_ge3": "data/ELSA_ge3.dat"}


def growth(form, n, times):
    L = ["  i BY " + " ".join("y%d@1" % (j + 1) for j in range(n)) + ";",
         "  s BY " + " ".join("y%d@%d" % (j + 1, times[j]) for j in range(n)) + ";"]
    if form in ("quad", "cub"):
        L.append("  q BY " + " ".join("y%d@%d" % (j + 1, times[j] ** 2) for j in range(n)) + ";")
    if form == "cub":
        L.append("  c BY " + " ".join("y%d@%d" % (j + 1, times[j] ** 3) for j in range(n)) + ";")
    return L


def build_inp(sample, k, cls, form, name=None, save=False):
    cohort = "HRS" if sample.startswith("HRS") else "ELSA"
    times = TIMES[cohort]
    n = len(times)
    title = "%s k=%d %s %s" % (sample, k, cls, form)
    L = ["TITLE: %s;" % title,
         "DATA: FILE IS %s;" % DATA[sample],
         "VARIABLE:",
         "  NAMES ARE id " + " ".join("y%d" % (i + 1) for i in range(n)) + ";",
         "  USEV = " + " ".join("y%d" % (i + 1) for i in range(n)) + ";",
         "  MISSING = ALL (-999);",
         "  IDVARIABLE = id;"]
    if k >= 2:
        L.append("  CLASSES = c(%d);" % k)
    L.append("ANALYSIS: TYPE = %s;" % ("MIXTURE" if k >= 2 else "GENERAL"))
    L.append("  STARTS = %s;" % (STARTS if k >= 2 else "1"))
    if k >= 2:
        L.append("  LRTBOOTSTRAP = %d;" % LRTBOOT)
    L.append("  PROCESSORS = 4;")
    L.append("MODEL:")
    if k >= 2:
        L.append("  %OVERALL%")
    L += growth(form, n, times)
    if cls == "lcga":
        fixes = "i@0 s@0 " + ("q@0 " if form in ("quad", "cub") else "") + \
                ("c@0 " if form == "cub" else "")
        L.append("  " + fixes.strip() + ";")
    if cls in ("lcga", "gmm"):
        L.append("  y1-y%d (res);" % n)
    if k >= 2:
        L.append("OUTPUT: TECH11 TECH14;")
    if save and name:
        L.append("SAVEDATA:")
        L.append("  FILE = %s_cprob.dat;" % name)
        L.append("  SAVE = CPROB;")
    return "\n".join(L) + "\n"


def jobs_for(stage):
    J = []
    if stage == "pilot":
        J.append(("pilot_hq_k2", "HRS", 2, "lcga", "quad"))
    elif stage == "form":
        for form in ["lin", "quad"]:
            J.append(("form_HRS_%s_k1" % form, "HRS", 1, "lgcm", form))
    elif stage == "form_ge3":
        for form in ["lin", "quad"]:
            J.append(("form_HRSge3_%s_k1" % form, "HRS_ge3", 1, "lgcm", form))
    elif stage == "lcga":
        for sample, form in [("HRS", HRS_FORM), ("ELSA", "lin")]:
            for k in range(1, 7):
                J.append(("lcga_%s_%s_k%d" % (sample, form, k), sample, k, "lcga", form))
    elif stage == "gmm_final":
        for sample in ["HRS", "ELSA"]:
            for k in [3, 4, 5]:
                J.append(("gmm_%s_lin_k%d" % (sample, k), sample, k, "gmm", "lin"))
    elif stage == "final":
        for sample in ["HRS", "ELSA"]:
            J.append(("final_lcga_%s_k4" % sample, sample, 4, "lcga", "lin"))
    elif stage == "elsa_more":
        ks = [int(x) for x in os.environ.get("ELSA_KS", "7,8,9,10").split(",")]
        for k in ks:
            J.append(("lcga_ELSA_lin_k%d" % k, "ELSA", k, "lcga", "lin"))
    elif stage == "gmm":
        for sample, form in [("HRS", HRS_FORM), ("ELSA", "lin")]:
            for k in range(1, 7):
                J.append(("gmm_%s_%s_k%d" % (sample, form, k), sample, k, "gmm", form))
    return J


HRS_FORM = os.environ.get("HRS_FORM", "quad")

if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "pilot"
    jobs = jobs_for(stage)
    print("STAGE=%s  jobs=%d" % (stage, len(jobs)))
    for name, sample, k, cls, form in jobs:
        inp = os.path.join(MP, name + ".inp")
        with open(inp, "w", encoding="utf-8") as f:
            f.write(build_inp(sample, k, cls, form, name=name, save=(stage == "final")))
        t0 = time.time()
        r = subprocess.run([EXE, name + ".inp"], cwd=MP,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        el = time.time() - t0
        out = os.path.join(MP, name + ".out")
        ok = os.path.exists(out)
        tag = "?"
        if ok:
            txt = open(out, encoding="utf-8", errors="replace").read()
            okmt = ("MODEL ESTIMATION TERMINATED NORMALLY" in txt
                    or ("MODEL FIT INFORMATION" in txt and "*** ERROR" not in txt))
            tag = "OK" if okmt else "FAIL"
        print("  %-28s %-4s %6.1fs" % (name, tag, el))
    print("DONE", stage)
