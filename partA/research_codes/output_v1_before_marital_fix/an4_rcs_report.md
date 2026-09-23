# AN-4 RCS 剂量-反应分析报告（模型3调整，参照=中位eCRF）

## CHARLS  (n=1698)
- knots(5/35/65/95%): [np.float64(7.79), np.float64(9.86), np.float64(11.89), np.float64(13.94)]
- 参照 eCRF = 中位数 = 10.64
- 样条项联合显著性检验：
- 总样条 Wald: chi2=12.32, p=0.0064
- 非线性项 Wald: chi2=1.18, p=0.5553
## ELSA  (n=2610)
- knots(5/35/65/95%): [np.float64(6.46), np.float64(8.77), np.float64(10.17), np.float64(12.64)]
- 参照 eCRF = 中位数 = 9.42
- 样条项联合显著性检验：
- 总样条 Wald: chi2=79.54, p=0.0000
- 非线性项 Wald: chi2=0.91, p=0.6345
## HRS  (n=2252)
- knots(5/35/65/95%): [np.float64(5.9), np.float64(8.18), np.float64(9.7), np.float64(12.11)]
- 参照 eCRF = 中位数 = 8.93
- 样条项联合显著性检验：
- 总样条 Wald: chi2=85.39, p=0.0000
- 非线性项 Wald: chi2=5.50, p=0.0640