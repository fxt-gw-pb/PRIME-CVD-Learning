#!/usr/bin/env python3
"""项目统一入口：python run.py --help。默认official，绝不静默降级到demo。"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from primecvd.common import load_config,data_dir,environment,provenance_label


def main(argv=None):
    p=argparse.ArgumentParser(description="PRIME-CVD 医学数据科学学习工程")
    p.add_argument("--config",default="configs/official.json",help="相对项目根目录的JSON配置")
    p.add_argument("command",choices=["doctor","download","prepare","train","reconstruct","report","all","demo","finalize","official"])
    p.add_argument("--unlock-test",action="store_true",help="显式打开最终测试集，仅用于finalize")
    p.add_argument("--force-download",action="store_true",help="重新下载官方源文件")
    args=p.parse_args(argv); cfg=load_config(args.config)
    print(provenance_label(cfg),flush=True)
    if args.command=="doctor": print(json.dumps(environment(),indent=2,ensure_ascii=False)); return 0
    if args.command in {"download","official"}:
        if cfg["mode"]!="official": raise ValueError("下载只能用于official配置。")
        from primecvd.download import download_official
        download_official(data_dir(cfg),force=args.force_download)
        print("官方文件已下载并完成结构/本地哈希记录。提供者MD5状态见manifest。",flush=True)
        if args.command=="download": return 0
    if args.command=="demo":
        if cfg["mode"]!="demo": raise ValueError("必须显式指定 --config configs/demo.json，演示数据不是官方数据。")
        from primecvd.demo import create_demo
        if not (data_dir(cfg)/"manifest.json").exists(): create_demo(data_dir(cfg))
    from primecvd.pipeline import prepare,train_models,reconstruct_emr,run_all,finalize
    from primecvd.reporting import generate_report
    actions={"prepare":prepare,"train":train_models,"reconstruct":reconstruct_emr,"report":generate_report,
             "all":run_all,"official":run_all,"demo":run_all}
    if args.command=="finalize": result=finalize(cfg,unlock_test=args.unlock_test)
    else: result=actions[args.command](cfg)
    if isinstance(result,Path): print(f"结果报告：{result}",flush=True)
    else: print("完成。",flush=True)
    return 0

if __name__=="__main__":
    try: sys.exit(main())
    except (OSError,ValueError,RuntimeError) as exc:
        print(f"\nERROR: {exc}",file=sys.stderr); sys.exit(1)
