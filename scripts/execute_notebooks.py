#!/usr/bin/env python3
"""按周次顺序执行全部学习笔记本，输出直接保存在笔记本里，执行摘要写入 outputs/notebook_execution.json。

用法（在项目根目录）：
    python scripts/execute_notebooks.py                 # 全部 17 份
    python scripts/execute_notebooks.py --only w05 w06  # 只执行文件名以这些前缀开头的笔记本

笔记本默认 MODE="official"，需要先运行 python run.py download。
w12_capstone 会运行完整流水线（不打开测试集），耗时最长。
"""
from pathlib import Path
import argparse
import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from primecvd.common import write_json, sha256


def main():
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", nargs="+", help="仅执行指定文件名前缀，例如 --only w05 w06")
    parser.add_argument("--kernel", default="prime-cvd", help="Jupyter 内核名（默认 prime-cvd）")
    parser.add_argument("--timeout", type=int, default=900, help="单个代码格的超时秒数")
    args = parser.parse_args()

    paths = sorted((ROOT / "notebooks").glob("w*.ipynb"))
    if args.only:
        paths = [p for p in paths if any(p.name.startswith(prefix) for prefix in args.only)]
        if not paths: parser.error("没有匹配的笔记本")
    summary_path = ROOT / "outputs" / "notebook_execution.json"
    previous = {}
    if args.only and summary_path.exists():
        previous = {r["notebook"]: r for r in json.loads(summary_path.read_text(encoding="utf-8"))["results"]}

    results = []
    for path in paths:
        start = time.monotonic()
        row = {"notebook": path.name}
        try:
            nb = nbformat.read(path, as_version=4)
            client = NotebookClient(nb, timeout=args.timeout, kernel_name=args.kernel,
                                    resources={"metadata": {"path": str(path.parent)}}, allow_errors=False)
            client.execute()
            nbformat.write(nb, path)
            row.update(status="passed", seconds=round(time.monotonic() - start, 1), sha256_after=sha256(path))
        except Exception as exc:
            row.update(status="failed", seconds=round(time.monotonic() - start, 1),
                       error=f"{type(exc).__name__}: {exc}"[:2000], traceback=traceback.format_exc()[-4000:])
        print(f"{row['status']:6s} {row['seconds']:7.1f}s  {path.name}", flush=True)
        results.append(row)

    merged = {**previous, **{r["notebook"]: r for r in results}}
    write_json(summary_path, {"executed_at_utc": datetime.now(timezone.utc).isoformat(), "kernel": args.kernel,
                              "results": [merged[k] for k in sorted(merged)]})
    failed = [r for r in results if r["status"] != "passed"]
    print(f"\n{len(results) - len(failed)}/{len(results)} 通过；摘要：{summary_path.relative_to(ROOT)}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
