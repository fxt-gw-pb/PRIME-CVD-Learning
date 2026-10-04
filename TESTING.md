# 实际验证记录

验证日期：2026-09-27。环境：macOS 26.6（arm64）、Python 3.11.16、conda 环境 `prime-cvd`；依赖版本见 `requirements-lock-tested.txt`。以下每一项都是在清空 `outputs/` 与 `data/processed/` 之后，从官方原始文件重新运行得到的。

## 已实际完成

| 检查 | 命令 | 结果 |
|---|---|---|
| 官方数据下载 | `python run.py download` | Asset1 v2（文件 67453365）与 Asset2（文件 62130498）下载成功，两者的提供者 MD5 均核验通过；来源记录见 `data/raw/manifest.json` |
| 自动化测试 | `python -m pytest -q` | 50 项通过，1 项跳过，0 项失败 |
| 完整流水线 | `python run.py all` | 官方 50,000 人：划分 35,000 / 7,500 / 7,500，训练内三折 CV、普通与 L2 Cox、验证评价、EMR 重建、单位敏感性实验、`outputs/official/report.html` |
| 学习笔记本 | `python scripts/execute_notebooks.py` | 17/17 在官方数据上执行通过，合计约 75 秒；摘要见 `outputs/notebook_execution.json` |
| 演示模式 | `python run.py --config configs/demo.json demo` | 5,000 人演示数据的完整流水线运行通过（验证后删除了输出） |
| 测试集封存 | 检查 `outputs/` | 没有 `test_evaluation.json` / `test_metrics.csv`，测试集未被打开 |
| 图像目视检查 | 逐张查看 | 精讲篇 9 张图、工程篇笔记本中的图和报告中的 8 张图：标签不重叠、不裁切，中文正常显示 |

唯一跳过的测试需要可选的 scikit-survival（附加数值交叉核验），核心实现不依赖它。

## 官方数据上的关键数值（验证集，n = 7,500）

Harrell C 0.875；截断 IPCW C 0.874；5 年 IPCW AUC 0.877；5 年 IPCW Brier 0.0273，相对训练集 KM 常数风险改进 29.3%；平均预测 5 年风险 4.05%，1 − KM(5) 为 4.03%。EMR 重建与 Asset1 对照：诊断、HbA1c、eGFR、SBP、IRSD、结局完全一致；BMI 中 10,000 个派生值的最大误差 0.63 kg/m²。详见 `docs/06_quality_and_limitations.md`。

## 数值交叉核对

- 工程篇 Cox 系数与 `statsmodels.PHReg` 一致（`test_cox_coefficients_match_statsmodels`）；KM 与 statsmodels 生存曲线一致；IPCW 有手算例子、无删失退化和边界情形测试。
- 精讲篇的 lifelines Cox（`step_size=0.5`）与 R 4.5.2 `survival::coxph` 在全部数据上的多变量 HR 一致到小数点后第 3 位（例：糖尿病 5.351，C 指数 0.8757）。

## 本次整合中修复并加了测试的问题

| 问题 | 修复 | 测试 |
|---|---|---|
| 下载器把 Asset1 版本 1 的文件 62102364 当作版本 2 锁定，元数据核验必然失败 | 改锁版本 2 的文件 67453365 | 实测下载与 MD5 核验 |
| 重建词典缺官方数据的 3 种诊断写法、约 15 种检验写法，流水线在官方数据上报错停止 | 补全全部 19 + 35 种写法 | `test_official_disease_labels_all_mapped`、`test_official_measure_labels_all_mapped` |
| 英尺英寸身高（`5'7"`）导致数值解析报错 | 新增 `feet_inches_to_cm`，含 `5'12"` 未进位写法 | `test_feet_inches_parsing_including_uncarried_inches` |
| BMI 单位列为空被当作未知单位；20% 只有身高体重的人没有 BMI | 空单位计数记录；由实测身高体重派生并写入 `BMI_source`，不从 Asset1 回填 | `test_bmi_derived_from_height_weight_and_labelled` |
| "HbA1c mmol/mol" 名称与单位列矛盾 | 以单位列为准（原逻辑已如此，补测试固定行为） | `test_hba1c_unit_column_wins_over_name` |
| — | 官方文件端到端重建并与 Asset1 逐项对照 | `test_official_files_reconstruct_against_asset1`（未下载官方数据时自动跳过） |

## 明确未完成的验证

- Windows 与 Linux 未实测。`.github/workflows/tests.yml` 在 Linux 上只运行测试（官方数据测试会因未下载而跳过）；Linux 需要安装中文字体，图中中文才能正常显示。
- 最终测试集没有打开，留给学习者在第 12 周完成，所以没有官方数据上的测试集性能。
- 性能指标没有 bootstrap 置信区间；没有正式的 PH 全局检验、竞争风险或外部验证（见 `docs/05_methods.md` 第 8 节）。
- 词典覆盖当前锁定版本的全部写法，不保证覆盖作者未来的新版本。

## 你可以复核

```bash
python -m pytest -q
python run.py all
python scripts/execute_notebooks.py
```
