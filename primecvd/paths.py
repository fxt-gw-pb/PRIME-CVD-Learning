"""精讲笔记本（w**a）共用的路径与保存工具。

笔记本里这样用：
    from primecvd import paths
    df = pd.read_csv(paths.ASSET1)              # 官方 Data Asset 1（由 python run.py download 下载并核验）
    paths.save_table(table, "表名")              # 保存到 outputs/tables/

精讲笔记本直接用 pd.read_csv 读原始文件，是为了学习 pandas；工程笔记本（w**b）用
primecvd.data.load_clean()，它会额外做字段、编码和来源校验。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"                 # 官方原始数据（只读，不要修改；来源记录见 manifest.json）
PROCESSED = ROOT / "data" / "processed"     # 精讲笔记本清洗后生成的数据
TABLES = ROOT / "outputs" / "tables"        # 精讲笔记本导出的表格
FIGURES = ROOT / "outputs" / "figures"      # 精讲笔记本导出的图（由 pubplot.save 写入）

ASSET1 = RAW / "asset1.csv"                 # = Figshare 上的 Data001_ReadyForCoxPH_v2(2026-08-12).csv
EMR_MASTER = RAW / "Data002_PatientEMR_MasterSummary_RE.csv"
EMR_DISEASES = RAW / "Data002_PatientEMR_ChronicDiseases_RE.csv"
EMR_MEASURES = RAW / "Data002_PatientEMR_MeasAndPath_RE.csv"

if not ASSET1.exists():
    raise FileNotFoundError(f"找不到 {ASSET1}。请先在项目根目录运行：python run.py download")


def save_table(table, name):
    """把表格保存为 CSV 到 outputs/tables/（utf-8-sig 编码，Excel 打开中文不乱码）。"""
    TABLES.mkdir(parents=True, exist_ok=True)
    path = TABLES / f"{name}.csv"
    table.to_csv(path, encoding="utf-8-sig")
    return path
