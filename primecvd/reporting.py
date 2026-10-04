"""独立HTML报告，不依赖浏览器联网或第三方CDN。"""
from __future__ import annotations
import base64
import html
import json
from pathlib import Path
import pandas as pd
from .common import output_dir,provenance_label,write_json,environment


def generate_report(cfg):
    out=output_dir(cfg)
    pieces=[]
    for title,filename in [
        ("训练集基线特征 / Training-set summary","baseline_training.csv"),
        ("线性回归：收缩压","linear_coefficients.csv"),
        ("横断面糖尿病分类：OR","logistic_coefficients.csv"),
        ("训练集内三折交叉验证","cv_results.csv"),
        ("未惩罚Cox：临床单位HR","cox_coefficients.csv"),
        ("验证集生存模型评价","validation_metrics.csv"),
        ("验证集分组校准","calibration_valid.csv"),
        ("验证集亚组探索","subgroup_valid.csv"),
        ("病历重建对照核查","reconstruction_comparison.csv"),
        ("HbA1c单位错误的受控实验","unit_sensitivity_valid.csv"),
        ("显式解锁后的最终测试集","test_metrics.csv")]:
        p=out/"tables"/filename
        if p.exists():
            d=pd.read_csv(p)
            pieces.append(f"<section><h2>{html.escape(title)}</h2><div class='scroll'>{d.to_html(index=False,border=0,float_format=lambda x:f'{x:.5g}',escape=True)}</div></section>")
    for image in sorted((out/"figures").glob("*.png")):
        b64=base64.b64encode(image.read_bytes()).decode()
        pieces.append(f"<figure><img src='data:image/png;base64,{b64}' alt='{html.escape(image.stem)}'><figcaption>{html.escape(image.name)}</figcaption></figure>")
    status="测试集仍封存，当前结果仅来自训练/验证。"
    if (out/"test_evaluation.json").exists(): status="测试集已由显式命令打开；不得继续据此调整模型。"
    document=f"""<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PRIME-CVD 学习项目报告</title>
    <style>body{{font:16px/1.7 system-ui,sans-serif;margin:0;background:#f5f7fa;color:#172334}}main{{max-width:1150px;margin:40px auto;padding:32px;background:white}}h1{{line-height:1.25}}h2{{margin-top:2em;font-size:1.3em}}.banner{{border-left:6px solid #b57300;background:#fff3da;padding:18px}}.scroll{{overflow:auto}}table{{border-collapse:collapse;font-size:13px;width:100%}}td,th{{padding:9px;border-bottom:1px solid #d9e0e8;text-align:left}}img{{max-width:100%;height:auto}}figure{{margin:28px 0}}figcaption{{font-size:12px;color:#526070}}code{{background:#edf1f5;padding:3px 6px}}footer{{margin-top:50px;border-top:1px solid #ddd;padding-top:20px}}</style><main>
    <h1>医学数据科学学习项目<br>PRIME-CVD workflow</h1>
    <div class="banner"><strong>{html.escape(provenance_label(cfg))}</strong><p>{html.escape(status)}</p><p>本报告由实际运行自动生成。演示数据报告不能被引用为官方PRIME-CVD结果，更不是临床证据。</p></div>
    <p>配置：{html.escape(Path(cfg['_config_path']).name)}。主要任务为基线起{cfg['horizon_years']:g}年CVD风险。建模仅使用Asset1式干净表；病历重建是独立的数据工程练习，不作为外部验证。</p>
    <p>校准为训练集固定风险分组内的1−KM估计，CI为点态95%区间，不是模型风险的个人预测区间。标为sparse_or_unsupported的组应谨慎解释。边际IPCW需要独立删失假设。本项目未执行竞争风险、因果效应估计或临床部署验证。</p>
    {''.join(pieces)}
    <footer><h2>来源与方法入口</h2><p>数据作者：Nicholas I-Hsien Kuo、Marzia Hoque Tania、Blanca Gallego、Louisa Jorm。数据来源与许可见项目 references/sources.json 和 THIRD_PARTY_NOTICES.md。Cox使用statsmodels PHReg部分似然；删失评价的假设、实现和测试见docs/05_methods.md。</p><p>自动生成报告用于复核，不替代个人完成的研究问题、方法解释和局限讨论。</p></footer></main></html>"""
    (out/"report.html").write_text(document,encoding="utf-8")
    write_json(out/"environment.json",environment())
    return out/"report.html"
