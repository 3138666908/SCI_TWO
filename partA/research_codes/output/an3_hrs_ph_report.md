# AN-3 HRS PH 假设处理报告

## 1) 随访窗口截断 Cox（M3）——观察 eCRF 效应是否随时间衰减

### 窗口 ≤5 年  (n=2252, events=1096)
- group_mid: HR 0.807 (0.689-0.944), p=0.0075
- group_high: HR 0.534 (0.438-0.650), p=0.0000

### 窗口 ≤10 年  (n=2252, events=1544)
- group_mid: HR 0.797 (0.696-0.914), p=0.0011
- group_high: HR 0.516 (0.436-0.609), p=0.0000

### 窗口 完整随访  (n=2252, events=1659)
- group_mid: HR 0.789 (0.690-0.901), p=0.0005
- group_high: HR 0.503 (0.428-0.591), p=0.0000

## 2) 时间交互项（CoxTimeVaryingFitter，group × log(t)）
- person-period 行数: 3736; 事件总和校验不一致人数: 0
### 时间交互项结果
- group_mid: coef 4.6963 (se 0.1712), p=0.0000
- group_high: coef 4.9872 (se 0.1868), p=0.0000
- group_mid_x_logt: coef -2.9481 (se 0.0910), p=0.0000
- group_high_x_logt: coef -3.2761 (se 0.0959), p=0.0000
- age: coef 0.0132 (se 0.0032), p=0.0000
- female: coef 0.1383 (se 0.0516), p=0.0073
- marital: coef -0.0338 (se 0.0587), p=0.5645
- educ_hs: coef -0.1307 (se 0.0741), p=0.0777
- educ_college: coef -0.2727 (se 0.0832), p=0.0010
- smk_former: coef 0.0589 (se 0.0546), p=0.2803
- smk_current: coef 0.0643 (se 0.0809), p=0.4266
- drink: coef -0.1052 (se 0.0526), p=0.0455
- sbp: coef -0.0003 (se 0.0013), p=0.7941
### 交互项 p（检验 PH 是否随时间变化）
- group_mid_x_logt: p=0.0000  (<0.05 → 效应随时间显著变化)
- group_high_x_logt: p=0.0000  (<0.05 → 效应随时间显著变化)

## 3) 结论
- 看窗口 1 中 group_mid/group_high 的 HR 是否随随访窗口缩短而变强（效应衰减证据）。
- 若时间交互项 p<0.05，报告交互项以解释 PH 违反。
- 以 ≤10 年窗口作为稳健性复验：若 HR 仍 <1 且显著，则主结论成立。