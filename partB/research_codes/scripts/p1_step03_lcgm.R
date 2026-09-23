# p1_step03_lcgm.R  (PartB / 阶段一 - LCGM 潜在类别增长模型, 无类内随机效应)
# 依据 handbook §5.1（方案 2：轨迹建模仅 HRS 主 / ELSA 辅；CHARLS 不做轨迹）。
# 输入：output/p1_traj_{HRS,ELSA}[_ge3].csv（由 p1_step02 生成）
# 输出：output/p1_step03_lcgm_fitindices.csv
# 说明：eCRF 不插补；用极大似然处理缺失(MAR)。轨迹形状=time+time2（二次）。
#       类别数 k=1..7；报告 AIC/BIC/SABIC/entropy/各类人数/收敛码。
#       注：lcmm 不直接提供 BLRT/VLMR-LRT，需另法(见 handbook)。
suppressMessages(library(lcmm))
args <- commandArgs(trailingOnly = FALSE)
.f <- sub("^--file=", "", args[grep("^--file=", args)])
OUT <- if (length(.f)) file.path(dirname(normalizePath(.f)), "..", "output") else file.path("..", "output")
f1 <- ecrf ~ time + time2

entropy <- function(m) {
  prob <- as.matrix(m$pprob[, grep("^prob", names(m$pprob)), drop = FALSE])
  prob <- prob / rowSums(prob)
  ks <- ncol(prob)
  ll <- -sum(prob * log(prob + 1e-300))
  1 - ll / (nrow(prob) * log(ks))
}
sabic <- function(m, n) -2 * m$loglik + length(m$best) * log((n + 2) / 24)

run <- function(label, file, kmax = 7) {
  d <- read.csv(file.path(OUT, file))
  d$pid <- as.integer(d$pid)
  d$time2 <- d$time^2
  n <- length(unique(d$pid))
  res <- data.frame()
  m1 <- hlme(fixed = f1, random = ~ -1, subject = "pid", ng = 1, data = d, verbose = FALSE)
  res <- rbind(res, data.frame(k = 1, loglik = m1$loglik, npar = length(m1$best),
    AIC = m1$AIC, BIC = m1$BIC, SABIC = sabic(m1, n), entropy = NA,
    sizes = paste(as.integer(table(m1$pprob$class)), collapse = "/"), conv = m1$conv))
  for (k in 2:kmax) {
    cat("  ", label, "k =", k, "\n")
    mk <- gridsearch(rep = 1, maxiter = 30, minit = m1,
                     hlme(fixed = f1, mixture = f1, random = ~ -1,
                          subject = "pid", ng = k, data = d, verbose = FALSE))
    res <- rbind(res, data.frame(k = k, loglik = mk$loglik, npar = length(mk$best),
      AIC = mk$AIC, BIC = mk$BIC, SABIC = sabic(mk, n), entropy = round(entropy(mk), 3),
      sizes = paste(as.integer(table(mk$pprob$class)), collapse = "/"), conv = mk$conv))
  }
  cbind(sample = label, n = n, res)
}

allres <- rbind(
  run("HRS_ge2", "p1_traj_HRS.csv"),
  run("HRS_ge3", "p1_traj_HRS_ge3.csv"),
  run("ELSA_ge2", "p1_traj_ELSA.csv"),
  run("ELSA_ge3", "p1_traj_ELSA_ge3.csv")
)
write.csv(allres, file.path(OUT, "p1_step03_lcgm_fitindices.csv"), row.names = FALSE)
print(allres)
cat("DONE\n")
