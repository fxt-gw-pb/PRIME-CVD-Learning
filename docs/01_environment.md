# 环境与启动

## 推荐的最少工具

conda（Anaconda 或 Miniconda）、终端，以及 VS Code 或 JupyterLab 其中之一。本项目不需要 GitHub 令牌，不连接医院系统，不上传任何数据。不要把真实患者文件放进这个教学项目后公开分享。

## 方式一：conda（推荐，已实测）

在项目根目录执行：

```bash
conda env create -f environment.yml          # 创建 prime-cvd 环境
conda activate prime-cvd
python -m ipykernel install --user --name prime-cvd --display-name "Python (prime-cvd)"   # 注册内核（一次）
python run.py doctor                          # 查看版本
python run.py download                        # 下载官方数据并核验（约 11 MB）
python -m pytest -q                           # 可选：确认一切正常
```

然后打开笔记本：

- **VS Code**：打开 `notebooks/w01a_first_look.ipynb`，右上角 **Select Kernel** → **Python (prime-cvd)**
- **JupyterLab**：`jupyter lab notebooks/`

## 方式二：pip + venv

```bash
bash scripts/setup_venv.sh        # 建 .venv、安装依赖、注册内核、下载数据并运行完整流水线
```

Windows PowerShell 不必改变系统执行策略，直接调用虚拟环境里的解释器：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m ipykernel install --user --name prime-cvd
.\.venv\Scripts\python.exe run.py download
.\.venv\Scripts\python.exe -m jupyterlab
```

## 中文字体

图里的中文按 `primecvd/pubplot.py` 中 `FONTS` 的顺序自动回退：macOS 用苹方，Windows 用微软雅黑，Linux 需要安装思源黑体（如 `sudo apt install fonts-noto-cjk`）。找不到任何中文字体时，中文会显示成方块，但不影响计算。

## 版本与可重复性

`environment.yml` 与 `requirements.txt` 给出兼容范围；`requirements-lock-tested.txt` 记录实际测试时的版本（macOS arm64、Python 3.11.16）。换用其他版本时，先运行 `python -m pytest -q`，再运行 `python scripts/execute_notebooks.py`。Windows 与 Linux 没有实测。

## 常见问题

`FileNotFoundError / 官方manifest不存在`：还没下载官方数据。运行 `python run.py download`。程序不会偷偷用演示数据代替。

`Figshare无法连接`：检查本机能否打开官方数据链接，以及 Python 进程是否用了正确的网络设置。下载器支持 `HTTPS_PROXY` 环境变量；不要把代理密码写进提交到仓库的配置。不需要关闭 TLS 证书验证。

`No module named ...`：终端和笔记本用的不是同一个环境。在 VS Code 里确认内核是 **Python (prime-cvd)**，或用 `python run.py doctor` 比较版本。

`未知术语/单位/患者重复`：这不是应该忽略的报错。先审查源数据和词典，再更新映射或聚合规则，同时记录依据、补充测试。不要用"删掉报错行"的方式得到漂亮的结果。

`测试集已打开`：阅读已保存的结果。之后的方法修改都属于探索；最终确认需要新的保留样本，删除锁文件不能解决问题。

`离线环境`：设 `MODE = "demo"`（工程篇）或使用 `python run.py --config configs/demo.json demo` 运行演示数据。演示数据不是 PRIME-CVD，结果不能当作官方结果；精讲篇只支持官方数据。
