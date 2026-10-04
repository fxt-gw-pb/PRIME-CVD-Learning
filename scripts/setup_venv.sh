#!/usr/bin/env bash
# 不用 conda 时的备选安装方式：在项目内建 .venv，安装依赖，下载官方数据并运行完整流水线。
# 推荐方式见 docs/01_environment.md（conda env create -f environment.yml）。
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m ipykernel install --user --name prime-cvd --display-name "Python (prime-cvd)"
.venv/bin/python run.py official
printf '\n完成。报告：outputs/official/report.html\n'
