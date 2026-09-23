# STEP-03 ID 核验报告

## CHARLS
- 总行数: 25586, 唯一 ID: 25586
- ID == householdID(10位)+pnc 匹配率: 1.0000 (n=25586)
- ID_w1 == householdID_w1(9位)+pnc 匹配率(第1波受访者): 1.0000 (n=17708)
- ID_w1 非空人数: 17708; 空串: 7878 (第2波及后加入者)
- 结论: 宽格式一人一行; ID 为第2波+键, ID_w1 为第1波键（与原文件合并时用）

## HRS
- harmonized: 42406 行, 唯一 hhidpn: 42406
- RAND: 45234 行, 唯一 HHIDPN: 45234
- harmonized 中能在 RAND 找到: 42405 / 42406 (1.0000)
- RAND 中不在 harmonized: 2829
- 结论: hhidpn/HHIDPN 可直接对齐合并

## ELSA
- 总行数: 21679, 唯一 idauniq: 21679, 缺失: 0
- 结论: idauniq 为宽格式一人一行键