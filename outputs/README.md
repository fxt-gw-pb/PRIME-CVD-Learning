# 运行结果（全部由代码生成，可以随时删除后重跑）

| 目录 / 文件 | 由谁生成 | 内容 |
|---|---|---|
| `figures/`、`tables/` | 精讲篇笔记本（w**a） | 顶刊风格的图（PNG 600 dpi + PDF）和表格（CSV） |
| `official/` | `python run.py all` | 命令行流水线：划分、模型、评价、重建审查、`report.html` |
| `notebooks_official/` | 工程篇笔记本（w**b 等） | 每周练习的中间结果 |
| `notebook_capstone_official/` | `w12_capstone.ipynb` | 第 12 周完整流程与报告 |
| `notebook_execution.json` | `scripts/execute_notebooks.py` | 最近一次批量执行的结果 |

原始数据不在这里（在 `data/raw/`）。测试集默认封存，只有显式执行 `python run.py finalize --unlock-test` 才会打开。
