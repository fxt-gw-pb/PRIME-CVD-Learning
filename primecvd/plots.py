"""流水线报告用图：统一使用 pubplot 的顶刊风格（字体、尺寸、语义配色），单图单文件。
文件名与函数签名保持不变，reporting.py 会把 figures/ 下的全部 PNG 嵌入报告。
中文字体按 pubplot.FONTS 顺序回退；Linux 上需要安装 Noto Sans CJK 等中文字体。
"""
from __future__ import annotations
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from . import pubplot as pp

pp.setup()

TERM_LABELS = {
    "Age_per10": "年龄（每 10 岁）", "BMI_per5": "BMI（每 5 kg/m²）", "HbA1c_per1": "HbA1c（每 1%）",
    "eGFR_per10": "eGFR（每 10 单位）", "SBP_per10": "收缩压（每 10 mmHg）", "diabetes": "糖尿病",
    "CKD": "慢性肾病", "AF": "房颤", "IRSD_1_vs5": "IRSD 1 最贫困 vs 5", "IRSD_2_vs5": "IRSD 2 vs 5",
    "IRSD_3_vs5": "IRSD 3 vs 5", "IRSD_4_vs5": "IRSD 4 vs 5", "smoking_ex_vs_non": "已戒烟 vs 从不",
    "smoking_current_vs_non": "现在吸烟 vs 从不",
}


def save(fig, path):
    fig.savefig(path)
    fig.savefig(path.with_suffix(".pdf"))      # 同时导出矢量 PDF，便于投稿或排版
    plt.close(fig)


def draw_eda(train, folder):
    # 训练集连续变量分布：一张三联图，按印刷尺寸绘制
    specs = [("Age", "年龄（岁）"), ("BMI", "BMI（kg/m²）"), ("SBP", "收缩压（mmHg）")]
    for col, label in specs:
        fig, ax = plt.subplots(figsize=pp.size(pp.SINGLE, 58))
        ax.hist(train[col], bins=40, color=pp.NEUTRAL, lw=0)
        med = train[col].median()
        ax.axvline(med, color=pp.INK, lw=0.6)
        ax.text(1, 1.02, f"训练集 n = {len(train):,}；中位数 {med:.1f}", transform=ax.transAxes,
                ha="right", va="bottom", fontsize=6, color=pp.GREY)
        ax.set(xlabel=label, ylabel="人数")
        pp.thousands_axis(ax)
        save(fig, folder / f"distribution_{col}.png")

    # 吸烟状态：柱状图用长度编码，纵轴必须从 0 开始
    counts = train.smoking_status.value_counts().reindex(["non", "ex", "current"]).fillna(0)
    fig, ax = plt.subplots(figsize=pp.size(pp.SINGLE, 58))
    x = np.arange(3)
    ax.bar(x, counts.to_numpy(), width=0.6, color=[pp.SMOKING[k] for k in counts.index])
    for xi, n in zip(x, counts):
        ax.annotate(f"{int(n):,}\n{n / len(train):.1%}", (xi, n), xytext=(0, 2), textcoords="offset points",
                    ha="center", va="bottom", fontsize=6)
    ax.set_xticks(x, ["从不吸烟", "已戒烟", "现在吸烟"])
    ax.set_ylim(0, counts.max() * 1.25)
    ax.set_ylabel("人数"); pp.thousands_axis(ax)
    save(fig, folder / "smoking.png")

    # KM 累积发病率 + 风险人数表（训练集，按糖尿病分组）
    t_max = float(min(6, np.floor(train.cvd_time.max())))
    times = list(range(int(t_max) + 1))
    fig, ax, ax_tab = pp.km_figure(width_mm=pp.ONE_HALF, curve_mm=56, n_groups=2)
    fitters = []
    for dm, label, color in [(0, "无糖尿病", pp.REFERENCE), (1, "糖尿病", pp.EXPOSED)]:
        d = train[train.diabetes == dm]
        fitters.append(pp.km_curve(ax, d.cvd_time, d.cvd_event, label, color, t_max=t_max))
    ax.set_xlim(0, t_max); ax.set_xticks(times); pp.percent_axis(ax)
    ax.set_ylim(0, None)
    ax.set(xlabel="随访时间（年）", ylabel="累积发病率")
    ax.legend(loc="upper left")
    pp.risk_table(ax_tab, fitters, ["无糖尿病", "糖尿病"], [pp.REFERENCE, pp.EXPOSED], times)
    save(fig, folder / "kaplan_meier.png")


def draw_forest(table, folder):
    """未惩罚 Cox 的 HR 森林图（训练集）。"""
    if "ci_low" not in table: return
    rows = []
    for r in table.itertuples():
        rows.append({"label": TERM_LABELS.get(r.term, r.term), "kind": "est", "hr": r.HR, "lo": r.ci_low,
                     "hi": r.ci_high, "ci": f"{r.HR:.2f} ({r.ci_low:.2f}–{r.ci_high:.2f})",
                     "p": "<0.001" if r.p_value < 0.001 else (f"{r.p_value:.3f}" if r.p_value < 0.01 else f"{r.p_value:.2f}")})
    lo = min(0.5, float(table.ci_low.min()) * 0.9)
    hi = max(2.0, float(table.ci_high.max()) * 1.1)
    ticks = [t for t in (0.25, 0.5, 1, 2, 4, 8, 16) if lo <= t <= hi]
    fig, _ = pp.forest_plot(rows, [("HR（95% CI）", "ci", 128, "left"), ("P 值", "p", 157, "right")],
                            xlim=(lo, hi), ticks=ticks, width_mm=160, label_mm=46, plot_mm=62,
                            xlabel="风险比（点态 95% CI，对数刻度）")
    save(fig, folder / "cox_forest.png")


def draw_calibration(table, folder, name="calibration_valid.png", title=None):
    """分组校准：训练集预测定分组边界，组内比较平均预测风险与 1−KM(5)。"""
    fig, ax = plt.subplots(figsize=pp.size(pp.SINGLE, 80))
    d = table[table.KM_risk.notna()]
    high = max(float(d.mean_prediction.max()) if len(d) else .1, float(d.KM_risk.max()) if len(d) else .1)
    ci = d[d.ci_low.notna() & d.ci_high.notna()]
    if len(ci): high = max(high, float(ci.ci_high.max()))
    high = min(1, max(.08, high * 1.10))
    ax.plot([0, high], [0, high], color=pp.GREY, lw=0.6, ls=(0, (3, 2)), zorder=0)
    ax.text(high * 0.97, high * 0.97, "完美校准", rotation=45, ha="right", va="bottom", fontsize=6, color=pp.GREY,
            rotation_mode="anchor", transform_rotates_text=True)
    if len(ci):
        ax.vlines(ci.mean_prediction, ci.ci_low, ci.ci_high, color=pp.NEUTRAL, lw=1.0, zorder=2)
    sparse = d.get("sparse_or_unsupported", False)
    ax.plot(d.mean_prediction, d.KM_risk, "o", color=pp.NEUTRAL, ms=4.5, zorder=3, label="风险组（训练集定边界）")
    if hasattr(sparse, "any") and sparse.any():
        s = d[sparse]
        ax.plot(s.mean_prediction, s.KM_risk, "o", mfc="white", mec=pp.EXPOSED, ms=4.5, zorder=4, label="事件过少 / 随访不足")
    ax.set(xlim=(0, high), ylim=(0, high), xlabel="平均预测 5 年风险", ylabel="观察风险：1 − KM(5)")
    # 刻度落在 1/2/5 的整齐步长上，小数位由格式器自动决定（避免把 2.5% 显示成"2%"）
    for axis in (ax.xaxis, ax.yaxis):
        axis.set_major_locator(matplotlib.ticker.MaxNLocator(5, steps=[1, 2, 5, 10]))
    decimals = 0 if high >= 0.05 else None            # 范围 ≥ 5% 时刻度都是整数百分比
    pp.percent_axis(ax, "x", decimals=decimals); pp.percent_axis(ax, "y", decimals=decimals)
    ax.set_aspect("equal")
    ax.legend(loc="upper left", fontsize=6)
    if title: ax.set_title(title)
    save(fig, folder / name)


def draw_ph(residuals, folder):
    """年龄的 Schoenfeld 残差随 log 事件时间的探索图（不是正式 PH 检验）。"""
    age = next((c for c in residuals if c.startswith("Age_")), None)
    if age is None: return
    fig, ax = plt.subplots(figsize=pp.size(pp.ONE_HALF, 62))
    x = np.log(residuals.event_time)
    ax.scatter(x, residuals[age], s=4, alpha=.25, color=pp.NEUTRAL, lw=0, rasterized=True)
    bins = np.linspace(x.min(), x.max(), 9); groups = np.digitize(x, bins)
    xx = []; yy = []
    for g in np.unique(groups):
        m = groups == g
        if m.sum() >= 5: xx.append(x[m].mean()); yy.append(residuals.loc[m, age].mean())
    ax.plot(xx, yy, "o-", color=pp.EXPOSED, ms=3.5, lw=1.1, label="分箱均值")
    pp.ref_line(ax, 0, axis="y")
    ax.set(xlabel="log(事件时间)", ylabel="未缩放 Schoenfeld 残差（年龄）")
    ax.text(0.98, 0.97, "探索性诊断，不是正式 PH 检验", transform=ax.transAxes, ha="right", va="top",
            fontsize=6, color=pp.GREY)
    ax.legend(loc="lower left")
    save(fig, folder / "ph_diagnostic_age.png")
