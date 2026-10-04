# 数据字典与来源审查

两份数据描述**同一批 50,000 名模拟成年人**（心血管病一级预防人群）。数据完全是合成的，没有真实病人。研究基线为 2017 年 1 月；结局为随访期间首次发生的心血管事件。参数来自澳大利亚统计局（ABS）、澳大利亚卫生与福利研究所（AIHW）的公开统计和已发表的流行病学效应量。

本文描述下载器锁定的文件版本（见 `primecvd/download.py` 与 `data/raw/manifest.json`）。数据作者发布新版本时，先看实际列名、行数、术语和 manifest，再更新本页。

| 资产 | Figshare 文件 | 本地文件 | 提供者 MD5 |
|---|---|---|---|
| Asset1 v2（2026-08-12） | 67453365 `Data001_ReadyForCoxPH_v2(2026-08-12).csv` | `data/raw/asset1.csv` | `d378958d5dcfbbefdb7fe6d22c5bbbed` |
| Asset2 v1 | 62130498 `Data002_PatientEMR_Zipped.zip` | `data/raw/asset2_original.zip` 及解压出的 3 个 CSV | `5d736b75f956eaa1f0c9b53ac79bebd5` |

---

## Asset1：基线一人一行

50,000 行、12 列，**无缺失值**。

| 字段 | 中文解释 | 类型与单位 | 本项目用途 | 备注 |
|---|---|---|---|---|
| IRSD_quintile | 地区社会经济劣势指数五分位 | 1–5；**1 最贫困，5 最富裕** | 类别变量，以 5 为参考 | 是地区指标，不是个人收入 |
| Age | 基线年龄 | 连续，岁，18–90 | 预测变量；HR 按每 10 岁 | 18 岁处 280 人、90 岁处 30 人为截断堆积 |
| smoking_status | 基线吸烟状态 | non / ex / current | 以 non 为参考 | 73% / 17% / 10% |
| BMI | 体重指数 | kg/m²，15–52.8 | 预测变量；HR 按每 5 单位 | 15.0 处 197 人为截断堆积 |
| diabetes | 基线糖尿病 | 0/1 | 预测变量；也是第 4 周横断面分类的结局 | 患病率 7.4% |
| CKD | 慢性肾病 | 0/1 | 预测变量 | 患病率 0.7% |
| AF | 房颤 | 0/1 | 预测变量 | 患病率 0.7% |
| HbA1c | 糖化血红蛋白 | %（NGSP） | 预测变量；HR 按每 1 个百分点 | 右偏 |
| eGFR | 估算肾小球滤过率 | mL/min/1.73m² | 预测变量；HR 按每 10 单位 | 越低肾功能越差 |
| SBP | 收缩压 | mmHg | 预测变量；HR 按每 10 mmHg；第 3 周线性回归的结局 | |
| cvd_event | 随访期间观察到 CVD 事件 | 1 = 事件，0 = 删失 | 生存结局，**不作为预测变量** | 2,009 例（4.0%） |
| cvd_time | 事件或删失前的观察时间 | 年，0–7.3 | 与事件标志联合使用 | |

`source_row_index`、`Patient_ID` 是 `load_clean()` 读入后添加的辅助字段，不改变官方源文件。跨资产核对用的公式为 `(source_row_index**2 − 77)*3 + 500`，来自作者的派生代码，只适用于这个版本的数据。

---

## Asset2：三张关系型表

由 Asset1 **故意"弄脏"**得到，用于练习数据清洗。三张表通过 `Patient_ID` 关联。每个 CSV 的第一列是没有名字的行号，精讲篇用 `pd.read_csv(..., index_col=0)`，工程篇的 `load_emr()` 会自动去掉。

### ① PatientMasterSummary（主表，50,000 行，一人一行）

| 字段 | 含义 | 注意事项 |
|---|---|---|
| Patient_ID | 病人 ID | 不连续、跨度很大；行顺序与 Asset1 一致 |
| Age_At_2024 | **2024 年**的年龄 | 按作者规则，基线年龄 = 该值 − 7，含两位小数的舍入误差 |
| SMOKING_STATUS | 吸烟状态 | **缺失 5,727 人（11%）** |
| IRSD_Quintile | IRSD 五分位 | 与 Asset1 相同 |
| CVD_Event | 是否发生 CVD 事件 | 与 Asset1 相同 |
| CVD_Time | 事件或删失的**年-月** | 所有未发生事件者统一为 `2022-12`（数据截止月份） |

### ② PatientChronicDiseases（慢病诊断表，4,417 行）

只有**有诊断的人**才有记录，一种病一行（146 人有两种及以上）。字段：Patient_ID、Category（诊断名称）、Date（诊断年-月，2012-01 至 2016-12，都在基线之前）。

| 标准疾病 | 原始写法（共 19 种） |
|---|---|
| 糖尿病 | Diabetes, T2DM, ICD10: E11, ICD9:250, High glucose, High blood sugar |
| 慢性肾病 | CKD, Chronic kidney disease, ICD10: N18, ICD9: 585, Renal insufficiency, Chronic renal failure, CRF |
| 房颤 | AF, Atrial fibrillation, AFib, A-fib, ICD10: I48, ICD9: 427.31 |

### ③ PatientMeasAndPath（检验 / 测量表，210,000 行，长表）

字段：Patient_ID、Value、Description、Date、Unit。每人 4–5 行，每人每项只有一条记录。

| 标准指标 | 写法数 | 写法举例 | 单位问题 |
|---|---|---|---|
| HbA1c | 10 | HbA1c, HBA1C, A1C, HbAlc（字母 l）, HA1C, LOINC: 4548-4, Glycated hemoglobin, HbA1c mmol/mol | 95% 为 %，5% 为 mmol/mol；**% = mmol/mol ÷ 10.929 + 2.15**。名为 "HbA1c mmol/mol" 的记录大多数单位其实是 %，以 Unit 列为准 |
| eGFR | 10 | eGFR, EGFR, GFR, GFR-e, e GFR, Estimated GFR, eGFR (mL/min/1.73m²) | 统一为 mL/min/1.73m² |
| SBP | 12 | SBP, Systolic BP, SyBP, Syst BP, BP_sys, Blood Pressure – Systolic | 统一为 mmHg |
| BMI | 1 | BMI | 40,000 人（80%）直接记录；**Unit 列为空** |
| Height / Weight | 各 1 | Height, Weight | 另外 10,000 人（20%）只有身高和体重；其中 1,000 条身高为英尺英寸（如 `5'7"`，也有 `5'12"` 这样未进位的写法），`Value` 因此是文本类型 |

`primecvd/reconstruction.py` 的词典收录了上面全部写法，`tests/test_model_and_reconstruction.py` 逐一测试。

---

## 必须保留的限制

**年龄**：按作者模拟规则由 2024 年龄减 7，带两位小数的舍入误差；不要把它当成真实病历中已核实的时间对齐方式。

**吸烟缺失**：保留为 `unknown`。第 10 周 a 的核对显示，这些"未知"在 Asset1 中全部是从不吸烟者，但这是只有合成数据才能看到的答案。不能把"我们知道这份模拟数据怎样制造缺失"迁移成"真实 EMR 的缺失都等于不吸烟"。

**无诊断记录编码为 0**：依赖这个模拟生成器"有病才有记录"的构造。真实 EMR 中没有记录不等于没有疾病。

**高血糖类写法**："High glucose"、"High blood sugar" 按作者派生代码归为糖尿病。真实 EMR 中一次高血糖记录不等于糖尿病诊断。

**HbA1c 换算**：按作者代码 `百分比 = mmol/mol / 10.929 + 2.15` 做逆变换，用于复核这份数据，不作为临床换算建议。

**BMI**：优先使用直接记录值；没有记录时，用同一病历中的实测身高体重按 BMI = 体重 / 身高² 派生，来源写在 `BMI_source` 列（`recorded` / `derived_from_height_weight` / `unavailable`）。派生值带有身高、体重舍入造成的误差（最大约 0.63 kg/m²）。**不从 Asset1 回填。**

**随访时间**：未发生事件者的 CVD_Time 被统一设为 2022-12，无法恢复 Asset1 中每个人原有的随访长度。用统一月份构造的删失时间平均高估约 1 年（第 10 周 a，7.2 节）。工程篇只保存标为"非原始"的月份中点变量，主要生存模型不使用它。

**日期**：是模拟的记录形式，不直接提供真实的疾病发生顺序。测量出现重复时要先定义规则，本项目不会擅自选择"最近一次"或直接取均值。

**同一人群**：Asset2 与 Asset1 是同一批合成人员的两种表示，**不是外部验证**。

来源：[S1] 作者 QuickStart 与仓库；[S2] 数据论文附录 B/C；作者的 Data Asset 2 派生代码。可追溯记录见 `references/sources.json`。
