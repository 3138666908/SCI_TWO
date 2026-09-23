# AN-7a 敏感性分析（SEN-1/2/3，Cox M3，分库，低 eCRF 参照）

## SEN-1 排除基线移动障碍者（= 主分析队列定义，重跑确认）
- CHARLS: n=1698, events=1118
- ELSA: n=2610, events=1653
- HRS: n=2252, events=1659

## SEN-2 排除基线癌症/肺病/CVD（CVD=heart 或 stroke）
- CHARLS: n=1451, events=920, 排除病人数=358
- ELSA: n=2159, events=1340, 排除病人数=563
- HRS: n=1669, events=1185, 排除病人数=615

## SEN-3 完整病例分析（模型变量无缺失）
- CHARLS: complete-case n=1698, events=1118
- ELSA: complete-case n=2610, events=1653
- HRS: complete-case n=2252, events=1659

## 结果表（HR 高/中 eCRF vs 低）
### SEN-1
- CHARLS mid: HR 0.741 (0.624-0.880), p=0.0006 (n=1698)
- CHARLS high: HR 0.744 (0.614-0.900), p=0.0023 (n=1698)
- ELSA mid: HR 0.818 (0.711-0.940), p=0.0047 (n=2610)
- ELSA high: HR 0.585 (0.494-0.692), p=0.0000 (n=2610)
- HRS mid: HR 0.789 (0.690-0.901), p=0.0005 (n=2252)
- HRS high: HR 0.503 (0.428-0.591), p=0.0000 (n=2252)
### SEN-2
- CHARLS mid: HR 0.759 (0.626-0.920), p=0.0050 (n=1451)
- CHARLS high: HR 0.741 (0.597-0.919), p=0.0063 (n=1451)
- ELSA mid: HR 0.794 (0.679-0.929), p=0.0039 (n=2159)
- ELSA high: HR 0.570 (0.474-0.686), p=0.0000 (n=2159)
- HRS mid: HR 0.787 (0.669-0.927), p=0.0041 (n=1669)
- HRS high: HR 0.502 (0.415-0.609), p=0.0000 (n=1669)
### SEN-3
- CHARLS mid: HR 0.741 (0.624-0.880), p=0.0006 (n=1698)
- CHARLS high: HR 0.744 (0.614-0.900), p=0.0023 (n=1698)
- ELSA mid: HR 0.818 (0.711-0.940), p=0.0047 (n=2610)
- ELSA high: HR 0.585 (0.494-0.692), p=0.0000 (n=2610)
- HRS mid: HR 0.789 (0.690-0.901), p=0.0005 (n=2252)
- HRS high: HR 0.503 (0.428-0.591), p=0.0000 (n=2252)