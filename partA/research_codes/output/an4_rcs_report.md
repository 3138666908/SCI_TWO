# AN-4 RCS 剂量-反应分析报告（模型3调整，参照=中位eCRF）

## CHARLS  (n=1698)
- knots(5/35/65/95%): [np.float64(7.79), np.float64(9.86), np.float64(11.89), np.float64(13.94)]
- 参照 eCRF = 中位数 = 10.64
- 样条项联合显著性检验：
- 总样条 Wald: chi2=11.92, p=7.66e-03
- 非线性项 Wald: chi2=0.97, p=0.6150
## ELSA  (n=2610)
- knots(5/35/65/95%): [np.float64(6.46), np.float64(8.77), np.float64(10.17), np.float64(12.64)]
- 参照 eCRF = 中位数 = 9.42
- 样条项联合显著性检验：
- 总样条 Wald: chi2=79.55, p=3.83e-17
- 非线性项 Wald: chi2=0.90, p=0.6367
## HRS  (n=2252)
- knots(5/35/65/95%): [np.float64(5.9), np.float64(8.18), np.float64(9.7), np.float64(12.11)]
- 参照 eCRF = 中位数 = 8.93
- 样条项联合显著性检验：
- 总样条 Wald: chi2=85.36, p=2.17e-18
- 非线性项 Wald: chi2=5.43, p=0.0661