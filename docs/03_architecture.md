# 项目架构与运行契约

```text
固定官方文件ID ── download.py ── data/raw + 来源manifest
明确选择demo ─── demo.py ────── data/demo + DEMO标识
                                │
                           data.py模式校验
                                │
                      splitting.py患者级固定划分
                  ┌─────────────┼─────────────┐
                train         valid          test（封存）
                  │             │                │
      每个训练折拟合features.py  │                │
                  │             │                │
      survival.py普通/岭Cox      │                │
                  │             │                │
      训练内CV选择alpha ───── metrics.py评价       │
                  │             │                │
            frozen_spec.json ────────── 显式解锁与完整性检查
                  │                              │
             JSON模型                         最终评价
                  └────────── reporting.py ──────┘

Asset2三表 ── reconstruction.py ── 重建表/单位规则/差异审查
                                      │
                   仅作同一合成人群核对，不是独立外部验证
```

## 模块职责

`paths.py`：精讲篇（w**a）共用的数据与输出路径。

`pubplot.py`：顶刊风格作图工具箱：字体、印刷尺寸、语义配色、KM 图与风险人数表、"左表右图"森林图。精讲篇和 `plots.py` 都通过它统一风格，设计说明见 `docs/10_visualization_guide.md`。

`plots.py`：流水线报告用图（分布、KM、森林图、校准、PH 探索），全部调用 `pubplot`。


`data.py`：模式、结局、编码、患者唯一性校验。保留源行索引，按作者公开规则形成跨资产核对用ID。

`features.py`：允许变量白名单；按事先规定临床单位编码；训练集拟合插补中位数和标准化参数；明确参考组。遇到训练集中未出现而新数据出现的类别会报错，不静默映射为参考组。

`survival.py`：statsmodels部分似然与SciPy优化，纯L2目标函数、右连续Breslow基线、概率预测、HR表和可读JSON模型。

`metrics.py`：KM、边际反向KM删失模型、IPCW、C-index、Brier、AUC和校准。通过手算、极端情形及成熟库对照测试。可选scikit-survival对照测试在本次环境跳过。

`pipeline.py`：明确的执行次序、文件来源、训练内模型选择、冻结与测试护栏。

`reconstruction.py`：疾病词典、测量词典（覆盖官方 Asset2 的 19 种诊断写法和 35 种检验写法）、单位转换（HbA1c mmol/mol、英尺英寸身高）、由实测身高体重派生 BMI 并标注来源、重复/孤立患者检查，保留不可恢复信息。测量表含干净的Measure字段时可用作显式记录的后备提示。

## 不变量

raw不覆盖；demo不自动替代official；同一患者不跨集合；结局和标识不入预测特征；测试集不参与调参；预处理不在全队列拟合；所有输出带数据来源；不确定的单位/术语不静默丢弃；临床结论不从测试夹具推出。

模型选择只依据训练内CV平均五年IPCW Brier。验证集用于报告和学习，不参与当前自动选择规则。最终模型仍用70%训练集拟合，没有在训练+验证上再训练；这是为了保持教学过程容易追踪，并非声称它是唯一正确的数据利用方式。

## 笔记本与输出

`notebooks/w**a_*.ipynb` 为精讲篇：直接读 `data/raw` 的原始 CSV（`primecvd.paths`），用 lifelines 讲解 KM 与 Cox，图表导出到 `outputs/figures/`（PNG + PDF）、表格到 `outputs/tables/`、清洗结果到 `data/processed/`。

`notebooks/w**b_*.ipynb` 及单篇周为工程篇：通过 `load_clean()` / `prepare()` 读数据，按患者划分，调用本包的建模和评价函数，结果写入 `outputs/notebooks_official/`；第 12 周写入 `outputs/notebook_capstone_official/`。命令行流水线写入 `outputs/official/`。

`scripts/execute_notebooks.py` 按周次原地执行全部笔记本，摘要写入 `outputs/notebook_execution.json`。

## 主要文件契约

`split_manifest.json`：数据哈希、划分种子/比例、划分文件哈希。
`frozen_spec.json`：配置、数据、划分、已选模型和校准边界的哈希与选择规则。
`test_evaluation.json`：测试已经被打开的事实与最终结果。
`report.html`：可离线浏览的汇总报告，图片内嵌，无外部CDN。
