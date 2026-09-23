"""
p5_step03_run_mplus.py  (PartB 修订版 / 第一步：移动障碍轨迹建模 LCGM→GMM)

数据：mplus_p5/data/<cohort>_train.dat（宽表，连续 mobilsev 0-7，缺失 -999）
用法：
  py p5_step03_run_mplus.py form            # k=1，线性 vs 二次（每队列）
  py p5_step03_run_mplus.py lcga            # LCGA k=1..K（form 由 FORM 指定）
  py p5_step03_run_mplus.py gmm
  py p5_step03_run_mplus.py one <jobname>...
环境变量 HRS? -> FORM / KMAX
"""
from pathlib import Path
import os, sys, json, subprocess, time

MP = str(Path(__file__).resolve().parents[1] / "mplus_p5")
EXE = os.environ.get("MPLUS_EXE", "Mplus.exe")
STARTS = "300 50"
LRTBOOT = 100
COHORTS = ["CHARLS", "ELSA", "HRS"]
KMAX = int(os.environ.get("KMAX", "5"))
FORMS = {"CHARLS": "lin", "ELSA": "quad", "HRS": "quad"}


def times(coh):
    return json.load(open(os.path.join(MP, "times_%s.json" % coh)))["times"]


def growth(form, times):
    n = len(times)
    L = ["  i BY " + " ".join("y%d@1" % (j + 1) for j in range(n)) + ";",
         "  s BY " + " ".join("y%d@%d" % (j + 1, times[j]) for j in range(n)) + ";"]
    if form in ("quad", "cub"):
        L.append("  q BY " + " ".join("y%d@%d" % (j + 1, times[j] ** 2) for j in range(n)) + ";")
    if form == "cub":
        L.append("  c BY " + " ".join("y%d@%d" % (j + 1, times[j] ** 3) for j in range(n)) + ";")
    return L


def build_inp(coh, k, cls, form, name=None):
    ts = times(coh)
    n = len(ts)
    L = ["TITLE: %s k=%d %s %s;" % (coh, k, cls, form),
         "DATA: FILE IS data/%s_train.dat;" % coh,
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
    L += growth(form, ts)
    if cls in ("lcga", "final"):
        fix = "i@0 s@0 " + ("q@0 " if form in ("quad", "cub") else "") + ("c@0 " if form == "cub" else "")
        L.append("  " + fix.strip() + ";")
    L.append("  y1-y%d (res);" % n)
    if k >= 2:
        L.append("OUTPUT: TECH11 TECH14;")
    if cls in ("final", "fgmm"):
        L.append("SAVEDATA: FILE = %s_cprob.dat; SAVE = CPROB; FORMAT = FREE;" % (name or ("fin_" + coh)))
    return "\n".join(L) + "\n"


def jobs_for(stage, args):
    J = []
    if stage == "form":
        for c in COHORTS:
            for f in ["lin", "quad"]:
                J.append(("form_%s_%s_k1" % (c, f), c, 1, "lgcm", f))
    elif stage == "lcga":
        for c in COHORTS:
            for k in range(1, KMAX + 1):
                J.append(("lcga_%s_%s_k%d" % (c, FORMS[c], k), c, k, "lcga", FORMS[c]))
    elif stage == "gmm":
        for c in COHORTS:
            for k in range(1, KMAX + 1):
                J.append(("gmm_%s_%s_k%d" % (c, FORMS[c], k), c, k, "gmm", FORMS[c]))
    elif stage == "final":
        for c, k in [("CHARLS", 3), ("ELSA", 3), ("HRS", 2)]:
            J.append(("final_%s" % c, c, k, "final", FORMS[c]))
    elif stage == "cmp":
        for c, k in [("CHARLS", 3), ("ELSA", 3), ("HRS", 2)]:
            J.append(("cmp_lcga_%s" % c, c, k, "final", FORMS[c]))
            J.append(("cmp_gmm_%s" % c, c, k, "fgmm", FORMS[c]))
    elif stage == "one":
        for a in args:
            # a = <cls>_<cohort>_<form>_k<k>
            cls, c, f, kk = a.split("_")
            J.append((a, c, int(kk[1:]), cls, f))
    return J


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "form"
    jobs = jobs_for(stage, sys.argv[2:])
    print("stage=%s jobs=%d" % (stage, len(jobs)))
    for name, c, k, cls, form in jobs:
        with open(os.path.join(MP, name + ".inp"), "w", encoding="utf-8") as f:
            f.write(build_inp(c, k, cls, form, name=name))
        t0 = time.time()
        subprocess.run([EXE, name + ".inp"], cwd=MP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        out = os.path.join(MP, name + ".out")
        tag = "?"
        if os.path.exists(out):
            txt = open(out, encoding="utf-8", errors="replace").read()
            ok = ("MODEL ESTIMATION TERMINATED NORMALLY" in txt
                  or ("MODEL FIT INFORMATION" in txt and "*** ERROR" not in txt))
            tag = "OK" if ok else "FAIL"
        print("  %-26s %-4s %6.1fs" % (name, tag, time.time() - t0), flush=True)
    print("DONE", stage)
