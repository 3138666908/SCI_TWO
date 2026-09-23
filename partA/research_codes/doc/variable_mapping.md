# 变量字典与来源对照表（STEP-01 交付物）

> 本文件是契约性核对表：`最终列名 ← 原始变量`。任何变量定义变化都必须回写本表并请研究者确认。

## 三库统一最终列定义（D10）

| 最终列 | 定义 | 编码 |
|---|---|---|
| pid | 库内唯一人 ID | CHARLS=ID; HRS=hhidpn; ELSA=idauniq |
| cohort | 队列 | CHARLS/ELSA/HRS |
| sex | 性别 | 1=男，2=女（harmonized 一致） |
| age | 基线年龄 | 岁；≥45 纳入（D6） |
| educ | 教育（三分类） | 1=高中以下，2=高中，3=大学及以上（D10） |
| marital | 婚姻（二分） | 1=已婚或有伴侣，0=其他（D10） |
| bmi | 实测 BMI | kg/m²；D12 范围[10,60] |
| waist | 实测腰围 | cm；D12 范围[40,170] |
| rhr | 静息心率(脉搏) | bpm |
| sbp | 收缩压 | mmHg；D13 范围[50,260] |
| mvpa | 中高强度身体活动 | 1=每周≥2次，0=否则（D11） |
| smoke_status | 吸烟三分类 | 0=从不，1=曾经，2=当前（D10） |
| drink | 饮酒 | 1=饮酒者，0=不饮酒（D10） |
| hibp/diab/cancer/lung/heart/stroke | 医生诊断病史 | 0/1 |
| ecrf | eCRF（METs） | 连续（STEP-08 公式） |
| ecrf_group | eCRF 三组 | 1=低(Q1)，2=中(Q2-Q3)，3=高(Q4-Q5)（D9） |
| mobilsev_base | 基线 7-item mobility | 0–7 |
| mobility_event | 新发移动障碍 | 0=删失/未发生，1=随访期发生（D5） |
| followup_years | 随访时间 | 年（波次差） |

## CHARLS → 最终列映射

| 原始变量 | 源 | 最终列 | 备注 |
|---|---|---|---|
| ID | harmonized | pid | 见 handbook §5.2 |
| r1agey | harmonized | age | |
| ragender | harmonized | sex | |
| raeducl | harmonized | educ | 3 级直接用 |
| r1mstat | harmonized | marital | 1,3→1；4,5,7,8→0 |
| r1mbmi | harmonized | bmi | |
| r1mwaist | harmonized | waist | |
| r1pulse | harmonized | rhr | |
| r1systo | harmonized | sbp | |
| r1vgact_c/x_c, r1mdact_c/x_c | harmonized | mvpa | 每周≥2 次；第1–3波半样本缺失 |
| r1smokev, r1smoken | harmonized | smoke_status | ever=0→0; ever=1&now=1→2; ever=1&now=0→1 |
| r1drinkev | harmonized | drink | |
| r1hibpe 等 | harmonized | 慢病史 | |
| r1mobilsev | harmonized | mobilsev_base | |
| r2–r4 mobilsev | harmonized | 结局 | W2=2013, W3=2015, W4=2018 |

## HRS → 最终列映射

| 原始变量 | 源 | 最终列 | 备注 |
|---|---|---|---|
| hhidpn / HHIDPN | har/RAND | pid | 100% 对齐（§2.1b） |
| R8AGEY_E | RAND | age | W8 |
| RAGENDER | RAND | sex | |
| RAEDUC | RAND | educ | 映射 1→1, 2/3/4→2, 5→3 |
| R8MSTAT | RAND | marital | 1,2,3→1；4–8→0 |
| R8PMBMI | RAND | bmi | |
| R8PMWAIST | RAND | waist | 英寸×2.54→cm |
| r8pulse | harmonized | rhr | |
| R8BPSYS | RAND | sbp | |
| R8VGACTX/MDACTX | RAND | mvpa | ∈{1每天,2>1次/周}→1 |
| R8SMOKEV/R8SMOKEN | RAND | smoke_status | |
| R8DRINK | RAND | drink | |
| R8HIBPE 等 | RAND | 慢病史 | |
| r8mobilsev | harmonized | mobilsev_base | |
| r9–r14 mobilsev | harmonized | 结局 | 2008→2018 |

## ELSA → 最终列映射

| 原始变量 | 源 | 最终列 | 备注 |
|---|---|---|---|
| idauniq | harmonized | pid | |
| r2agey | harmonized | age | |
| ragender | harmonized | sex | |
| raeducl | harmonized | educ | 3 级 |
| r2mstat | harmonized | marital | 1,3→1；其余→0 |
| r2mbmi | harmonized | bmi | 护士波 W2 |
| r2mwaist | harmonized | waist | |
| r2pulse | harmonized | rhr | |
| r2systo | harmonized | sbp | |
| r2vgactx_e/mdactx_e | harmonized | mvpa | =2→1 |
| r2smokev/r2smoken | harmonized | smoke_status | |
| r2drink | harmonized | drink | |
| r2hibpe 等 | harmonized | 慢病史 | |
| r2mobilsev | harmonized | mobilsev_base | |
| r3–r9 mobilsev | harmonized | 结局 | 2006→2018 |