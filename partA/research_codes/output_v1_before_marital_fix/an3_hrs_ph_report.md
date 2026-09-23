# AN-3 HRS PH 假设处理报告

## 1) 随访窗口截断 Cox（M3）——观察 eCRF 效应是否随时间衰减

### 窗口 ≤5 年  (n=2252, events=1096)
- group_mid: HR 0.809 (0.691-0.946), p=0.0081
- group_high: HR 0.534 (0.438-0.650), p=0.0000

### 窗口 ≤10 年  (n=2252, events=1544)
- group_mid: HR 0.799 (0.697-0.915), p=0.0012
- group_high: HR 0.516 (0.436-0.609), p=0.0000

### 窗口 完整随访  (n=2252, events=1659)
- group_mid: HR 0.790 (0.691-0.902), p=0.0005
- group_high: HR 0.503 (0.428-0.591), p=0.0000

## 2) 时间交互项（CoxTimeVaryingFitter，group × log(t)）
- person-period 行数: 3736; 事件总和校验不一致人数: 0
### 时间交互项结果
- group_mid: coef 4.7004 (se 0.1713), p=0.0000
- group_high: coef 4.9899 (se 0.1869), p=0.0000
- group_mid_x_logt: coef -2.9503 (se 0.0911), p=0.0000
- group_high_x_logt: coef -3.2765 (se 0.0959), p=0.0000
- age: coef 0.0131 (se 0.0032), p=0.0000
- female: coef 0.1371 (se 0.0514), p=0.0076
- marital: coef -0.0401 (se 0.0411), p=0.3283
- educ_hs: coef -0.1320 (se 0.0741), p=0.0749
- educ_college: coef -0.2746 (se 0.0832), p=0.0010
- smk_former: coef 0.0571 (se 0.0546), p=0.2964
- smk_current: coef 0.0662 (se 0.0807), p=0.4116
- drink: coef -0.1029 (se 0.0527), p=0.0508
- sbp: coef -0.0003 (se 0.0013), p=0.8217
### 交互项 p（检验 PH 是否随时间变化）
- group_mid_x_logt: p=0.0000  (<0.05 → 效应随时间显著变化)
- group_high_x_logt: p=0.0000  (<0.05 → 效应随时间显著变化)

## 3) 结论
- 看窗口 1 中 group_mid/group_high 的 HR 是否随随访窗口缩短而变强（效应衰减证据）。
- 若时间交互项 p<0.05，报告交互项以解释 PH 违反。
- 以 ≤10 年窗口作为稳健性复验：若 HR 仍 <1 且显著，则主结论成立。