# 第三方来源与许可

PRIME-CVD由Nicholas I-Hsien Kuo、Marzia Hoque Tania、Blanca Gallego和Louisa Jorm等作者提供。本项目是另外编写的中文学习工程，不是作者官方发行的软件，也不暗示作者认可本项目。

作者的数据论文声明数据按Creative Commons Attribution 4.0提供。官方仓库许可与数据许可应分别理解；本项目不会把第三方数据重新许可为MIT。下载后的Figshare元数据会保存到data/raw，使用或再分发时应核对该版本许可并保留作者与DOI。

官方Data Asset1 DOI：10.6084/m9.figshare.31395765.v2；Data Asset2 DOI：10.6084/m9.figshare.31403028.v1。下载程序锁定Asset1版本2的文件67453365（Data001_ReadyForCoxPH_v2(2026-08-12).csv）与Asset2的文件62130498；早期QuickStart链接的62102364属于Asset1版本1。2026-09-27已下载并通过提供者MD5核验，来源记录见data/raw/manifest.json。data/raw中的官方文件按CC BY 4.0许可随本项目保存，使用或再分发时须保留作者署名与DOI。

`tests/fixtures/official_preview_5rows.csv` 是作者QuickStart显示输出的有限精度转录，来源与blob SHA见同目录README，已明确标注不是原文件。

`data/demo` 的生成代码与样本由本学习工程另外编写，用于测试，不是官方PRIME-CVD或作者数据的一部分。项目方法说明中的单位逆变换、公开患者ID规则和字段语义依据作者文档，已在references/sources.json中标明来源。

NumPy、pandas、SciPy、scikit-learn、statsmodels、lifelines、Matplotlib、Requests、Jupyter和pytest保留其各自的许可。本包不重新分发这些库的二进制、字体文件或作者论文全文。


`docs/figure_guide/before/` 中的图片是本项目早期版本自行绘制的图，用于润色前后对比，不是期刊或第三方图片。`primecvd/pubplot.py` 的配色取自 Okabe & Ito 的 Color Universal Design 色板与 ColorBrewer 的单色相渐变。
