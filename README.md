# PRIME-CVD 医学数据科学学习项目

用 **PRIME-CVD** 合成心血管队列（5 万人），在 12 周内从零学会一套完整的医学数据科学流程：读懂数据表 → 描述统计与可视化 → 回归 → 生存分析 → 预测模型评价 → 病历数据清洗 → 冻结、测试与复现报告。

> PRIME-CVD 由新南威尔士大学（UNSW）健康大数据研究中心发布，数据**完全是合成的**，不含任何真实病人，可以自由用于学习。分析结果**不能用于临床决策**，也不是真实的医学发现。

---

## 快速开始

```bash
cd ~/research/Prime-CVD
conda env create -f environment.yml          # 第一次：创建 prime-cvd 环境（已完成）
conda activate prime-cvd
python run.py download                        # 下载官方数据并核验 MD5（已完成）
```

然后在 VS Code 中打开 `notebooks/w01a_first_look.ipynb`，右上角选内核 **Python (prime-cvd)**，从上到下按 `Shift + Enter` 运行。所有笔记本都已在官方数据上运行过，保存了输出，可以先读再自己重跑。

不用 conda、Windows 安装和常见问题见 [docs/01_environment.md](docs/01_environment.md)。

---

## 12 周学习路线

有精讲篇的周，**先学 a（讲概念），再做 b（规范工程流程）**。详见 [docs/02_learning_plan_12_weeks.md](docs/02_learning_plan_12_weeks.md)。

| 周 | a · 精讲 | b · 工程实践 | 主题 |
|---|---|---|---|
| 1 | `w01a_first_look` | `w01b_data_literacy` | 读懂数据表、变量类型、删失 |
| 2 | `w02a_descriptive` | `w02b_eda` | Table 1、社会经济梯度、人年发病率 |
| 3 | | `w03_linear_regression` | 线性回归与统计解释 |
| 4 | | `w04_logistic_regression` | Logistic 分类、OR、AUROC |
| 5 | `w05a_km_basics` | `w05b_survival_and_censoring` | 删失、Kaplan-Meier、风险人数表 |
| 6 | `w06a_cox_regression` | `w06b_cox_model` | Cox、粗 HR 与调整 HR、混杂与中介 |
| 7 | | `w07_penalization_and_cv` | 岭惩罚、训练内交叉验证 |
| 8 | | `w08_survival_evaluation` | C 指数、IPCW、Brier、校准 |
| 9 | | `w09_relational_emr_and_sql` | 病历多表、主键外键、SQL |
| 10 | `w10a_emr_cleaning` | `w10b_reconstruction` | 术语映射、单位换算、队列重建与核对 |
| 11 | | `w11_subgroups_and_sensitivity` | 亚组、数据错误的受控实验 |
| 12 | | `w12_capstone` | 冻结方案、打开测试集、复现报告 |

- **a · 精讲**：手把手讲解，用全部 5 万人把道理讲清楚；每张图都按医学顶刊规范绘制，附"🎨 设计要点"和图注示范。
- **b · 工程实践**：按患者划分训练 / 验证 / 测试集，调用 `primecvd` 包中经过测试的函数，每一步都可复核、可复现；测试集要到第 12 周才打开。

---

## 目录结构

```
Prime-CVD/
├── README.md                    ← 你正在看的文件
├── AGENTS.md                    ← 给 AI 助手的项目规则
├── environment.yml              ← conda 环境（推荐）；requirements*.txt 为 pip 备选
├── run.py                       ← 命令行入口：download / all / finalize …
├── configs/                     ← official.json（默认）、demo.json（离线演示）
│
├── notebooks/                   ← ★ 17 份按周编号的学习笔记本
├── primecvd/                    ← 核心 Python 包
│   ├── data.py  splitting.py  features.py      读数与校验、患者级划分、特征编码
│   ├── survival.py  metrics.py  basics.py      Cox、生存评价指标、线性 / Logistic
│   ├── reconstruction.py                       病历三表重建
│   ├── pipeline.py  reporting.py  download.py  流水线、HTML 报告、官方数据下载
│   ├── pubplot.py                              ★ 顶刊风格作图工具箱（值得通读）
│   ├── plots.py                                报告用图
│   └── paths.py                                精讲篇用的路径
├── tests/                       ← 自动化测试（python -m pytest -q）
├── sql/                         ← 第 9 周的 SQL 示例
├── scripts/                     ← execute_notebooks.py（批量执行笔记本）、setup_venv.sh
│
├── data/
│   ├── raw/                     ← 官方数据（只读；来源与 MD5 见 manifest.json）
│   ├── demo/                    ← 5,000 人演示数据（另外生成，不是 PRIME-CVD，仅供离线测试）
│   └── processed/               ← 精讲篇清洗后的数据
├── outputs/                     ← 所有运行结果（可删除后重跑，见 outputs/README.md）
│   └── official/report.html     ← 命令行流水线的完整报告
│
├── docs/                        ← 学习文档（见下表）
└── references/sources.json      ← 数据与方法来源
```

**为什么这样组织？** 原始数据只读，派生数据另存；代码写成可测试的包，笔记本负责讲解和练习；所有结果都能从原始文件重新生成。

---

## 文档

| 文档 | 内容 |
|---|---|
| [00 项目章程](docs/00_project_charter.md) | 学什么、做到什么程度、不做什么 |
| [01 环境与启动](docs/01_environment.md) | 安装、字体、常见问题 |
| [02 12 周学习路线](docs/02_learning_plan_12_weeks.md) | 每周入口、任务、验收成果、易犯错误 |
| [03 项目架构](docs/03_architecture.md) | 模块职责、数据流、不变量 |
| [04 数据字典](docs/04_data_dictionary.md) | 每个字段、官方数据的全部写法与单位、必须保留的限制 |
| [05 方法](docs/05_methods.md) | 预处理、Cox、IPCW、评价指标、BMI 派生 |
| [06 质量与局限](docs/06_quality_and_limitations.md) | 已实测的内容与结果、未验证的内容 |
| [07 练习与答案](docs/07_exercises_and_answers.md) | 先做练习再看 |
| [08 结项报告模板](docs/08_final_report_template.md) | 第 12 周用 |
| [09 与 AI 协作](docs/09_agent_working_prompt.md) | 让 AI 帮你学，而不是替你做 |
| [10 可视化指南](docs/10_visualization_guide.md) | 顶刊作图的八条原则、9 张图的润色前后对比、12 个自查问题 |

---

## 命令行

```bash
python run.py download                            # 下载官方数据
python run.py all                                 # 划分 → 训练 → 验证 → 重建 → 报告（约 1 分钟）
python run.py finalize --unlock-test              # 第 12 周：打开测试集（只能一次）
python run.py --config configs/demo.json demo     # 离线演示（不是 PRIME-CVD）
python -m pytest -q                               # 自动化测试
python scripts/execute_notebooks.py               # 按周执行全部笔记本
```

---

## 几个值得期待的发现（先剧透，学完再回来看）

- 糖尿病的**粗 HR ≈ 22**，调整其他因素后降到 **≈ 5.4**（w06a）
- 社会经济劣势（IRSD）只调整年龄时 HR ≈ 1.3，调整全部变量后 ≈ 1.0：它的作用几乎全部通过吸烟、肥胖、糖尿病等中介途径实现（w06a）
- 病历里吸烟状态"未知"的人，**实际上全部是从不吸烟者**：缺失不是随机的（w10a）
- 用统一截止月份构造的随访时间平均**高估约 1 年**（w10a）
- 故意漏掉 HbA1c 单位换算，平均预测风险从 4.1% **翻倍**到 8.3%（w11、`outputs/official/report.html`）
- 验证集 C 指数 0.875，预测 5 年风险 4.05%，实际观察 4.03%（w08、报告）

## ⚠️ 已知的技术坑

- **lifelines 的 Cox 可能"静默"出错**：效应很强时（例如糖尿病），默认的牛顿法步长会发散，**不报错**就返回 HR ≈ 0。精讲篇统一设置 `fit_options={"step_size": 0.5}`，结果已与 R `survival::coxph` 核对。w06a 的 5.2 节专门演示了这个问题。工程篇使用基于 statsmodels 的实现。
- **下载器锁定 Asset1 版本 2（文件 67453365）**。早期 QuickStart 链接的文件 62102364 属于版本 1，病历表是由版本 2 生成的。

---

## 项目来源

本项目整合了两部分工作：一是 4 份手把手精讲笔记本与顶刊风格作图工具（现为 w**a 与 `pubplot.py`）；二是一套工程化学习框架，包括 `primecvd` 包、测试、12 周工程笔记本和方法文档。后者原本只在演示数据上运行过；整合时修正了官方文件版本的锁定，把重建词典扩展到官方数据的全部写法，并完成了官方数据上的端到端验证。

## 引用与许可

> Kuo NI-H, Tania MH, Gallego B, Jorm LR. PRIME-CVD: Paired Synthetic Cohort and Structured EMR-Style Data Assets for Education in Cardiovascular Risk Modelling. *Scientific Data* (2026). doi:10.1038/s41597-026-08352-3
>
> 预印本：PRIME-CVD: A Parametrically Rendered Informatics Medical Environment for Education in Cardiovascular Risk Modelling. arXiv:2603.19299

数据：CC BY 4.0（保留作者署名与 DOI）。本项目代码：MIT（见 `LICENSE`）。第三方说明见 `THIRD_PARTY_NOTICES.md`。
