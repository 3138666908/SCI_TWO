# SCI_TWO

Part A 与 Part B 的分析代码、数据与结果。

## 目录结构

```
partA/
  research_codes/scripts/   分析脚本（全部使用相对路径，可直接运行）
  research_codes/output/    中间结果与最终分析数据 final_analysis_pooled.csv
  data_final_backup/        最终分析数据备份
partB/
  research_codes/scripts/   分析脚本（全部使用相对路径，可直接运行）
  research_codes/output/    分析输出
  research_codes/mplus*/    Mplus 输入/输出
  data/                     Part B 输入数据
  figures/                  图件
```

## 环境

```
pip install -r requirements.txt
```

## 运行方式

所有脚本中的输入/输出路径均相对于脚本文件自身，下载后无需修改任何路径：

```
py partA/research_codes/scripts/an2_cox.py
py partB/research_codes/scripts/p4_step01_decomposition.py
```

## 关于原始数据

`partA` 的 `step02`–`step05`、`partB` 的 `p1_step01`、`p5_step01` 等
“从原始 Harmonized 数据重建”的脚本，需要仓库根目录下的 `data/`
（`Harmonized CHARLS`、`Harmonized HRS`、`Harmonized ELSA`）。
该原始数据受使用协议限制，未包含在本仓库中。
其余脚本基于仓库内已包含的处理后数据即可直接运行。

## 关于 Mplus

`p1_step05_run_mplus.py` 与 `p5_step03_run_mplus.py` 需要 Mplus。
默认调用 PATH 中的 `Mplus.exe`，也可用环境变量 `MPLUS_EXE` 指定完整路径：

```
set MPLUS_EXE=D:\Mplus8\Mplus.exe
```
