# 官方源文件目录（只读）

由 `python run.py download` 从 Figshare 下载，**不要手工修改或替换这里的文件**。

| 文件 | 内容 |
|---|---|
| `asset1.csv` | Data Asset 1 v2 = Figshare 文件 67453365 `Data001_ReadyForCoxPH_v2(2026-08-12).csv` |
| `asset2_original.zip` | Data Asset 2 = Figshare 文件 62130498 `Data002_PatientEMR_Zipped.zip` |
| `Data002_PatientEMR_*.csv` | 从 zip 中安全解压的三张病历表 |
| `manifest.json` / `DOWNLOAD_STATUS.json` | 下载时间、URL、本地 SHA-256、提供者 MD5 核验结果、解压文件哈希 |
| `asset*_figshare_metadata.json` | 下载时保存的 Figshare 元数据（含许可 CC BY 4.0） |

程序会用 manifest 里的哈希核对文件；文件被改动后，`prepare` 和 `load_emr` 会拒绝运行。需要重新下载时：`python run.py download --force-download`。

数据由 Nicholas I-Hsien Kuo、Marzia Hoque Tania、Blanca Gallego、Louisa Jorm 提供，许可 CC BY 4.0，见 `../../THIRD_PARTY_NOTICES.md`。
