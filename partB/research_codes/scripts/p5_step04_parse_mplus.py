"""p5_step04_parse_mplus.py —— 解析 mplus_p5/*.out，输出 p5_mplus_results.csv"""
from pathlib import Path
import os, re, glob
import pandas as pd

MP = str(Path(__file__).resolve().parents[1] / "mplus_p5")
OUT = str(Path(__file__).resolve().parents[1] / "output")


def num(txt, pat):
    m = re.search(pat, txt)
    return float(m.group(1)) if m else None


def parse(path):
    txt = open(path, encoding="utf-8", errors="replace").read()
    r = {"file": os.path.basename(path).replace(".out", "")}
    r["converged"] = int("THE MODEL ESTIMATION TERMINATED NORMALLY" in txt
                         or ("MODEL FIT INFORMATION" in txt and "*** ERROR" not in txt))
    r["nfree"] = num(txt, r"Number of Free Parameters\s+(\d+)")
    r["loglik"] = num(txt, r"H0 Value\s+(-?\d+\.\d+)")
    r["AIC"] = num(txt, r"Akaike \(AIC\)\s+(-?\d+\.\d+)")
    r["BIC"] = num(txt, r"Bayesian \(BIC\)\s+(-?\d+\.\d+)")
    r["SaBIC"] = num(txt, r"Sample-Size Adjusted BIC\s+(-?\d+\.\d+)")
    r["entropy"] = num(txt, r"Entropy\s+(-?\d+\.\d+)")
    r["vlmr_p"] = num(txt, r"VUONG-LO-MENDELL-RUBIN LIKELIHOOD RATIO TEST[\s\S]*?P-Value\s+(-?\d+\.\d+)")
    r["lmr_p"] = num(txt, r"LO-MENDELL-RUBIN ADJUSTED LRT TEST[\s\S]*?P-Value\s+(-?\d+\.\d+)")
    r["blrt_p"] = num(txt, r"PARAMETRIC BOOTSTRAPPED LIKELIHOOD RATIO TEST[\s\S]*?Approximate P-Value\s+(-?\d+\.\d+)")
    m = re.search(r"BASED ON THEIR MOST LIKELY LATENT CLASS MEMBERSHIP([\s\S]*?)(?:\n\s*\n\s*\n|CLASSIFICATION QUALITY)", txt)
    sizes = []
    if m:
        for line in m.group(1).splitlines():
            mm = re.match(r"\s*(\d+)\s+(\d+)\s+(\d+\.\d+)", line)
            if mm:
                sizes.append(int(mm.group(2)))
    r["sizes"] = "/".join(map(str, sizes)) if sizes else None
    r["k"] = len(sizes) if sizes else 1
    return r


rows = [parse(p) for p in sorted(glob.glob(os.path.join(MP, "*.out")))]
df = pd.DataFrame(rows)
cols = ["file", "k", "converged", "nfree", "loglik", "AIC", "BIC", "SaBIC", "entropy", "vlmr_p", "lmr_p", "blrt_p", "sizes"]
df = df[[c for c in cols if c in df.columns]]
df.to_csv(os.path.join(OUT, "p5_mplus_results.csv"), index=False, encoding="utf-8-sig")
print(df.to_string())
