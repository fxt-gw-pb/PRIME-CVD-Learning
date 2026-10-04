"""
pubplot —— 顶刊风格作图工具箱
================================

本项目所有图表（精讲笔记本、工程笔记本、命令行报告）都通过这个模块统一风格。**这个文件值得通读**：
每个设置旁边都写了"为什么这样设"，它本身就是一份可视化规范。

设计依据（提炼共同规范，而不是照抄某一张图）：
- 医学顶刊（NEJM / Lancet / JAMA / BMJ）的统计图惯例：
  KM 曲线下方附"风险人数表"；森林图"左表右图"对齐、对数轴、参考线 HR = 1；
  一定展示不确定性（95% CI）；用色克制。
- Nature 系的版面规范：单栏 89 mm、双栏 183 mm，**按印刷尺寸作图**，字号 5–8 pt。
- Okabe & Ito (2008) 的色盲友好配色；Tufte 的"数据墨水比"：删掉不传达数据的一切。

用法：
    from primecvd import pubplot as pp
    pp.setup()
    fig, ax = plt.subplots(figsize=pp.size(89, 60))   # 单栏：宽 89 mm × 高 60 mm
    ...
    pp.save(fig, "图名")                               # 同时导出 PNG（600 dpi）+ PDF（矢量）
"""
import logging
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

# 中文字体没有"粗体"字重时 matplotlib 会反复警告，这里静音（不影响显示）
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
logging.getLogger("fontTools").setLevel(logging.ERROR)      # 嵌入苹方字体时的无害提示

FIGURES = Path(__file__).resolve().parent.parent / "outputs" / "figures"

# =============================================================================
# 1. 尺寸：按"印刷尺寸"作图
# =============================================================================
# 先画一张大图再缩小，字号和线宽会跟着缩小到看不清。所以一开始就按最终尺寸画，
# 字号直接用 pt 设定，所见即所得。
MM = 1 / 25.4                     # 1 毫米 = 1/25.4 英寸（matplotlib 的尺寸单位是英寸）
SINGLE, ONE_HALF, DOUBLE = 89, 120, 183   # 单栏 / 1.5 栏 / 双栏宽度（mm）


def size(width_mm, height_mm):
    """把毫米换算成 matplotlib 需要的英寸：figsize=pp.size(89, 60)"""
    return (width_mm * MM, height_mm * MM)


# =============================================================================
# 2. 颜色：颜色编码"含义"，同一含义在所有图里都用同一种颜色
# =============================================================================
INK = "#1a1a1a"       # 文字和主要线条。纯黑 #000 在屏幕上略显生硬，近黑更柔和
GREY = "#6e6e6e"      # 次要信息：参考线、辅助文字、次要估计值
LIGHT = "#d4d4d4"     # 最弱的辅助元素：连接线、分隔线
ZEBRA = "#f3f3f3"     # 表格隔行底纹，帮助视线横向对齐
NEUTRAL = "#5b7a99"   # 只有一组数据时的颜色：低饱和的灰蓝，不喧宾夺主

# 二分类的语义配色（Okabe-Ito 色板，常见色盲类型下仍可区分）：
#   参照组 / 未暴露 / 未发生事件 → 冷色蓝；暴露组 / 发生事件 → 暖色朱红
# 避免"红-绿"搭配：约 8% 的男性是红绿色弱。
REFERENCE = "#0072B2"
EXPOSED = "#D55E00"

# 吸烟三分类：按暴露程度由冷到暖（从不 → 已戒 → 现在吸）
SMOKING = {"non": "#0072B2", "ex": "#E69F00", "current": "#D55E00"}

# IRSD 有序五分位：同一色相由深到浅（越贫困越深）。
# 有序变量要用"单色相渐变"，不要用彩虹色：彩虹色没有天然的顺序，读者无法凭颜色判断大小。
IRSD = {1: "#3f007d", 2: "#54278f", 3: "#6a51a3", 4: "#807dba", 5: "#9e9ac8"}

# =============================================================================
# 3. 全局风格
# =============================================================================
# 拉丁字母用 Arial（绝大多数期刊的要求），中文字符自动逐字回退到苹方 / 雅黑 / 思源黑体
FONTS = ["Arial", "Helvetica", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei",
         "Noto Sans CJK SC", "WenQuanYi Micro Hei", "DejaVu Sans"]


def setup():
    """应用顶刊风格的全局设置。每个笔记本开头调用一次。"""
    mpl.rcParams.update({
        # —— 字体与字号：终稿尺寸下 6–8 pt，全图只用一种无衬线字体 ——
        "font.family": FONTS,
        "font.size": 7,
        "axes.titlesize": 7.5,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",     # 标题左对齐（Nature 系惯例），和面板标号连成一行
        "axes.titlepad": 5,
        "axes.labelsize": 7,
        "xtick.labelsize": 6.5,
        "ytick.labelsize": 6.5,
        "legend.fontsize": 6.5,
        "legend.title_fontsize": 6.5,
        # —— 颜色：文字、坐标轴统一用近黑 ——
        "text.color": INK,
        "axes.labelcolor": INK,
        "axes.edgecolor": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        # —— 坐标轴：只留左、下两条轴线；刻度朝外，不和数据打架 ——
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.6,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.size": 2.5,
        "ytick.major.size": 2.5,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "axes.grid": False,               # 默认不要网格；确实需要读数时再单独加浅色网格
        # —— 线条和标记：线宽 ≥ 0.5 pt，缩小印刷后仍然可见 ——
        "lines.linewidth": 1.1,
        "lines.markersize": 3.5,
        "patch.linewidth": 0.4,
        "errorbar.capsize": 0,            # 顶刊的误差线通常不带"帽子"，更简洁
        "legend.frameon": False,
        "legend.handlelength": 1.6,
        "legend.borderaxespad": 0.3,
        # —— 输出：屏幕显示清晰；导出 600 dpi PNG + 字体可编辑的 PDF ——
        "figure.dpi": 170,
        "savefig.dpi": 600,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.03,
        "pdf.fonttype": 42,               # 嵌入 TrueType 字体：PDF 里的文字在 Illustrator 中仍可编辑
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "axes.prop_cycle": mpl.cycler(color=[REFERENCE, EXPOSED, "#009E73", "#E69F00"]),
    })


def save(fig, name, formats=("png", "pdf")):
    """导出到 outputs/figures/：PNG 用于预览和汇报，PDF（矢量）用于投稿。"""
    FIGURES.mkdir(parents=True, exist_ok=True)
    for ext in formats:
        fig.savefig(FIGURES / f"{name}.{ext}")
    return FIGURES / f"{name}.pdf"


# =============================================================================
# 4. 小工具
# =============================================================================
def panel_label(ax, letter, dx=-16, dy=5):
    """在子图左上角外侧加面板标号 A / B / C：粗体、比正文大，位置在所有面板上保持一致。"""
    ax.annotate(letter, xy=(0, 1), xycoords="axes fraction", xytext=(dx, dy),
                textcoords="offset points", fontsize=9, fontweight="bold",
                ha="right", va="bottom")


def percent_axis(ax, axis="y", decimals=0):
    """把 0–1 的比例显示成百分比刻度（0.05 → 5%）。decimals=None 表示按刻度间隔自动决定小数位"""
    fmt = mpl.ticker.PercentFormatter(xmax=1, decimals=decimals)
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(fmt)


def thousands_axis(ax, axis="y"):
    """大数字加千分位逗号（2000 → 2,000），读起来更快"""
    fmt = mpl.ticker.StrMethodFormatter("{x:,.0f}")
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(fmt)


def format_p(p):
    """P 值的规范写法：< 0.001，否则保留 2 位有效数字。
    （期刊常把 P 排成斜体；但 matplotlib 的斜体公式 $P$ 与中文混排会出现方块，这里用正体。）"""
    return "P < 0.001" if p < 0.001 else f"P = {p:.2g}"


def ref_line(ax, value, axis="x", label=None, label_pos=0.97, **kw):
    """临床阈值 / 无效应参考线：细、浅、虚线，放在数据层下面，不抢戏"""
    style = dict(color=GREY, lw=0.6, ls=(0, (3, 2)), zorder=0.5)
    style.update(kw)
    if axis == "x":
        ax.axvline(value, **style)
        if label:
            ax.text(value, label_pos, f" {label}", transform=ax.get_xaxis_transform(),
                    fontsize=6, color=GREY, va="top", ha="left")
    else:
        ax.axhline(value, **style)
        if label:
            ax.text(label_pos, value, label, transform=ax.get_yaxis_transform(),
                    fontsize=6, color=GREY, va="bottom", ha="right")


# =============================================================================
# 5. Kaplan-Meier 累积发病曲线 + 风险人数表
# =============================================================================
def km_figure(width_mm=ONE_HALF, curve_mm=62, n_groups=2, left_mm=20, right_mm=4):
    """
    创建"上方曲线 + 下方风险人数表"的画布，两部分共用同一条时间轴，严格上下对齐。

    用毫米精确排版：曲线区高 curve_mm，表格每组一行，表格和曲线之间留出 x 轴刻度和轴标题的位置。
    返回 (fig, ax_curve, ax_table)。
    """
    row_mm, gap_mm, top_mm, bottom_mm = 3.4, 12, 3, 1
    table_mm = (n_groups + 1) * row_mm              # +1 行留给表头"风险人数"
    width = width_mm - left_mm - right_mm
    height_mm = top_mm + curve_mm + gap_mm + table_mm + bottom_mm
    fig = plt.figure(figsize=size(width_mm, height_mm))
    W, H = width_mm, height_mm
    ax = fig.add_axes([left_mm / W, (bottom_mm + table_mm + gap_mm) / H, width / W, curve_mm / H])
    ax_tab = fig.add_axes([left_mm / W, bottom_mm / H, width / W, table_mm / H], sharex=ax)
    ax_tab.axis("off")
    return fig, ax, ax_tab


def km_curve(ax, durations, events, label, color, t_max, ci=True, lw=1.2):
    """
    画一条 KM 累积发病率曲线（1 − 生存率），可选 95% CI 阴影。
    自己用 step 画，而不用 lifelines 自带的 plot：这样线宽、颜色、截断位置完全可控。
    """
    from lifelines import KaplanMeierFitter
    kmf = KaplanMeierFitter().fit(durations, events, label=label)
    cd = kmf.cumulative_density_.iloc[:, 0]
    band = kmf.confidence_interval_cumulative_density_
    keep = cd.index <= t_max
    t = np.append(cd.index[keep], t_max)             # 把最后一段台阶延伸到 t_max
    y = np.append(cd.values[keep], cd.values[keep][-1])
    ax.step(t, y, where="post", color=color, lw=lw, label=label, zorder=3)
    if ci:
        lo = np.append(band.iloc[:, 0].values[keep], band.iloc[:, 0].values[keep][-1])
        hi = np.append(band.iloc[:, 1].values[keep], band.iloc[:, 1].values[keep][-1])
        ax.fill_between(t, lo, hi, step="post", color=color, alpha=0.15, lw=0, zorder=2)
    return kmf


def risk_table(ax_tab, fitters, labels, colors, times, title="风险人数"):
    """
    在曲线下方画"风险人数表"（number at risk）：每个时间点还有多少人在被观察。
    这是医学期刊 KM 图的标配。读者据此判断曲线尾部是否可信：人数越少，曲线越不稳定。
    """
    n = len(fitters)
    ax_tab.set_ylim(n - 0.5, -1.3)                    # 第 0 行在最上面
    label_trans = mtransforms.blended_transform_factory(ax_tab.transAxes, ax_tab.transData)
    ax_tab.text(0, -1, title, transform=label_trans, fontsize=6.5, fontweight="bold",
                ha="left", va="center")
    for i, (kmf, label, color) in enumerate(zip(fitters, labels, colors)):
        durations = np.asarray(kmf.durations)
        for t in times:
            at_risk = int((durations >= t).sum())
            ax_tab.text(t, i, f"{at_risk:,}", ha="center", va="center", fontsize=6.3)
        # 组名写在表格左侧，用曲线的颜色，读者不用来回对照图例
        ax_tab.annotate(label, xy=(0, i), xycoords=label_trans, xytext=(-16, 0),
                        textcoords="offset points", ha="right", va="center",
                        fontsize=6.5, color=color, fontweight="bold")


# =============================================================================
# 6. 森林图："左表右图"，三线表风格
# =============================================================================
def forest_plot(rows, columns, xlim, ticks, xlabel="风险比（95% CI，对数刻度）",
                arrows=("风险更低", "风险更高"), width_mm=DOUBLE, row_mm=4.3,
                label_mm=50, plot_mm=62, secondary_label=None, primary_label=None):
    """
    画一张医学期刊风格的森林图。

    rows：每一行是一个字典
        {"label": 文本, "kind": "header" | "ref" | "est",
         "hr": 调整 HR, "lo": 下限, "hi": 上限,           # kind == "est" 时需要
         "hr2": 第二个估计（例如粗 HR，可选）, "lo2": ..., "hi2": ...,
         其他键: 右侧表格各列要显示的文本}
    columns：右侧文本列 [(列标题, 字典里的键, 该列左边缘距图左侧的毫米数, 对齐方式), ...]

    设计要点：
    - 左边文字、中间图形、右边数字共用同一行，视线能横向扫过（"表图对齐"）
    - 横轴用对数刻度：HR = 0.5 和 HR = 2 离参考线 1 一样远，保护和危害对称
    - 三线表：只保留顶线、表头下线、底线，没有竖线（期刊表格规范）
    - 隔行浅灰底纹帮助对齐；分组小标题加粗
    """
    n = len(rows)
    height_mm = (n + 1.6) * row_mm + 16            # 行 + 表头 + 下方坐标轴区
    fig = plt.figure(figsize=size(width_mm, height_mm))
    W, H = width_mm, height_mm
    bottom_mm = 16
    ax = fig.add_axes([label_mm / W, bottom_mm / H, plot_mm / W, n * row_mm / H])
    ax.set_ylim(n - 0.5, -0.5)
    ax.set_xscale("log")
    ax.set_xlim(*xlim)
    ax.set_xticks(ticks, [f"{t:g}" for t in ticks])
    ax.xaxis.set_minor_locator(mpl.ticker.NullLocator())
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_visible(False)       # 底线由三线表的"底线"充当，避免两条线叠在一起
    ax.set_facecolor("none")                     # 透明背景，让隔行底纹穿过图形区
    ax.set_yticks([])

    # 横向坐标：x 用"整张图的比例"，y 用"数据行号"，这样文字能精确落在每一行上
    row_trans = mtransforms.blended_transform_factory(fig.transFigure, ax.transData)

    def x_fig(mm):
        return mm / W

    # 隔行底纹（只给数据行，跳过分组标题）
    shade = False
    for i, r in enumerate(rows):
        if r["kind"] == "header":
            shade = False
            continue
        if shade:
            fig.add_artist(Rectangle((x_fig(2), i - 0.5), x_fig(W - 4), 1, transform=row_trans,
                                     facecolor=ZEBRA, edgecolor="none", zorder=0))
        shade = not shade

    # 参考线 HR = 1
    ax.axvline(1, color=GREY, lw=0.6, ls=(0, (3, 2)), zorder=1)

    for i, r in enumerate(rows):
        indent = 0 if r["kind"] == "header" else 3
        ax.text(x_fig(2 + indent), i, r["label"], transform=row_trans, va="center", ha="left",
                fontsize=6.8, fontweight="bold" if r["kind"] == "header" else "normal")
        for _, key, x_mm, ha in columns:
            if key in r:
                ax.text(x_fig(x_mm), i, r[key], transform=row_trans, va="center", ha=ha,
                        fontsize=6.6, color=r.get(f"{key}_color", INK))
        if r["kind"] != "est":
            continue
        has_two = "hr2" in r
        if has_two:                                  # 次要估计（如粗 HR）：灰色空心圆，放在下半行
            y2 = i + 0.18
            ax.plot([r["lo2"], r["hi2"]], [y2, y2], color=GREY, lw=0.8, zorder=2,
                    solid_capstyle="butt")
            ax.plot(r["hr2"], y2, "o", ms=3.2, mfc="white", mec=GREY, mew=0.8, zorder=3)
        y1 = i - 0.18 if has_two else i                # 主要估计（调整 HR）：黑色实心方块
        ax.plot([r["lo"], r["hi"]], [y1, y1], color=INK, lw=1.0, zorder=4, solid_capstyle="butt")
        ax.plot(r["hr"], y1, "s", ms=3.6, color=INK, zorder=5)

    # 三线表：顶线、表头下线、底线（没有竖线）
    header_y = -1.25
    for y, lw in [(header_y - 0.75, 0.8), (-0.62, 0.5), (n - 0.5, 0.8)]:
        fig.add_artist(Line2D([x_fig(2), x_fig(W - 2)], [y, y], transform=row_trans,
                              color=INK, lw=lw))
    ax.text(x_fig(2), header_y, "变量", transform=row_trans, fontweight="bold",
            va="center", ha="left", fontsize=6.8)
    for title, _, x_mm, ha in columns:
        ax.text(x_fig(x_mm), header_y, title, transform=row_trans, fontweight="bold",
                va="center", ha=ha, fontsize=6.8)

    # 横轴下方：轴标题 + "风险更低 ← | → 风险更高"
    ax.set_xlabel(xlabel, labelpad=3)
    ax.annotate(f"← {arrows[0]}", xy=(1, 0), xycoords=("data", "axes fraction"),
                xytext=(-4, -30), textcoords="offset points", ha="right", va="top",
                fontsize=6.3, color=GREY)
    ax.annotate(f"{arrows[1]} →", xy=(1, 0), xycoords=("data", "axes fraction"),
                xytext=(4, -30), textcoords="offset points", ha="left", va="top",
                fontsize=6.3, color=GREY)

    # 图例：两种标记分别代表什么
    if primary_label or secondary_label:
        handles = [Line2D([], [], color=INK, marker="s", ms=3.6, lw=1.0, label=primary_label)]
        if secondary_label:
            handles.append(Line2D([], [], color=GREY, marker="o", ms=3.2, mfc="white",
                                  mew=0.8, lw=0.8, label=secondary_label))
        # 放在左下角（标签列下方的空白处），不遮挡任何数据
        fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(x_fig(2), 2 * MM / (H * MM)),
                   bbox_transform=fig.transFigure, fontsize=6.3, handlelength=2.2,
                   borderaxespad=0, labelspacing=0.5)
    return fig, ax
