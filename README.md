# nRF52832 Canon remote — mechanical study v0.11

打开 **[在线 3D 预览](https://guruguru-seu.github.io/nrf-canon-remote/preview.html)**，可直接分享这个链接。

也可下载 `output/preview.html` 后用浏览器离线打开，详见 [机械设计说明](output/设计说明.md)。

机身为 **78 × 43 × 17.35 mm**：保留四向圆环、中心两段键和下方三个圆键，删除长条键及底部五个矩形键。中心开关采用 **K2-1831SL-A4SW-01**，其余七个开关采用 TS-1101-C-W。外壳、PCB 外形、固定孔、USB-C 板舌与开孔配套重建；软包电池候选为 EEMB LP402535 / 320 mAh。

USB-C 选用淘宝自购的 **HX TYPE-C 6P QTWT（6Pin 全贴）**，对应立创 C18357553，按当前 PCB 改为底面安装。USB-C、TS-1101-C-W 和 RGB 的预览使用嘉立创下载模型，原始文件与来源见 [器件模型记录](reference/component-models/README.md)。中心两段开关采用界面显示角度 180°，仍按厂家图纸建模；nRF52832 与电池为外形包络。U600 底部声学端口增加 Ø1.2 mm 外壳声孔与 Ø2.2 mm 内侧 relief。

v0.10 修正 USB-C 底面安装的翻转：焊脚朝 PCB，母座主体朝背盖，焊盘同步翻转。恢复参考外壳 USB 端两侧的上盖楔形卡扣和下盖凹槽，托筋避开固定焊耳。中心开关的两个定位孔也随 180° 方向旋转；模型碰撞检查不再豁免 USB / 外壳或开关 / PCB 穿插。预览新增“USB-C 端部配合”和“端部上盖卡扣”。

v0.11 按 2026-09-23 Chrome 最终 PCB 将上方 Ø2.3 孔移至 (14,28)，上下盖螺柱与沉孔同步。按当前叠层采用 1.0 mm 板厚，保持按键面高度，相应调整底面 USB-C 和托台。USB 模型使用实际焊盘核验原点偏移。

2026-09-23 增加 **[openEMS 天线初步计算报告](https://guruguru-seu.github.io/nrf-canon-remote/rf/antenna-20260923.html)**，包含实际 PCB 地铜与印制 IFA、四组仿真、阻抗 / S11 和匹配候选。现 PCB 使用印制天线，下面 v0.1 电气草案中的陶瓷天线与部分元件值已不是最终 PCB 版本。RF 结果有材料、几何和端口近似，不能直接作为量产匹配 BOM；[复算方法](scripts/rf/README.md)与数据一并提供。

新增 **[文字原理图 v0.1](output/electrical/原理图-v0.1.md)**：包含 nRF52832 最小系统、9 路按键信号、RGB 驱动、USB／电池供电与充电、4Pin SWD、陶瓷天线、库存 BOM 和布局注释。依据见 [电气参考资料](reference/electrical/README.md)。目前为待转绘和验证的电路草案，不含 EDA 原理图工程、PCB 铜层布局或固件；新增电路器件尚未回填到 3D 模型。

用于分享审阅的 HTML 页面：**[7 页原理图图纸](https://guruguru-seu.github.io/nrf-canon-remote/electrical/schematic-drawing-v0.1.html)**、**[原理图说明](https://guruguru-seu.github.io/nrf-canon-remote/electrical/schematic-v0.1.html)**、**[完整 BOM](https://guruguru-seu.github.io/nrf-canon-remote/electrical/bom-v0.1.html)**。图纸用 Schemdraw 绘制，支持切页、缩放、位号定位和 SVG 下载，每页附连接与 layout 注释；网站首页不增加文档入口。

图纸逐器件标注 `JLC C…` 物料编号，可在嘉立创EDA直接搜索；60 个元件对应 27 种立创物料。RGB 已改为共阳接 VDD、三个 GPIO 经各自限流电阻低有效直驱。未核实或待选型的器件、DNP 和 PCB 自带焊盘分别注明。物料编号与完整 BOM 一致；2026-09-19 新核实的四项供应商链接见 BOM，采购状态仍为待采购。

2026-09-20 按已有开发板用值更新晶振负载：HF、LF 每侧各一颗 12 pF（C210～C213，C45359894），后续电容顺延为 C214～C218；旧／新位号对照见文字原理图 3.2 节。

按键采用 GPIO 直连触点到地，开启内部上拉并由固件去抖；删除 R300～R308、C300～C308 共 18 个元件，半按与全按各自保留独立输入。

3D 预览为机械模型。参考键帽保留形状并平移、修改顶柱；下盖恢复参考工程的梯形截面（43 mm 收至背面 35 mm）；PCB 左上、右上角设 R5 四分之一圆凹口，下盖增加配合定位凸台和托台；采用右上、下左右三点固定。RGB 与导光结构整体下移 5 mm。原始 140 mm 参考模型保留在预览的“原型对照”中。

## 输出

- `output/electrical/原理图-v0.1.md`：可转绘的文字原理图、引脚分配、BOM 和 layout 原则。
- `output/electrical/BOM-v0.1.md`：按电路部分拆分的完整 BOM，包含已有／待采购状态和用途。
- `output/electrical/*.html`：可独立浏览及发布到 Pages 的原理图与 BOM 页面。
- `output/electrical/schematic-assets/*.svg`：7 页矢量电路图，覆盖全部默认装配物料、DNP、测试点和 MCU 48 脚 + EP。
- `output/electrical/schematic-manifest.json`、`schematic-checks.json`：绘图连接数据与检查记录；不是 EDA 网表，也不代表通过 EDA ERC。
- `output/preview.html`：模型及 Three.js 全部内嵌，双击离线打开。支持装配、爆炸、剖切、透明、梯形端面、PCB 板形、角部配合、USB 特写、中心键半按/全按及 STL 下载。
- `output/models/remote_assembly.3mf`：含电子件占位的完整装配。
- `output/models/printable_parts.3mf`：上下盖、五个键帽、导光件，共八件。
- `output/models/*.stl`：各部件，保持装配坐标，单位 mm。
- `output/models/pcb_outline.dxf`、`pcb_outline.svg`：板框、三个安装孔及中心开关的两个定位孔。
- `output/review/`：几何/浏览器检查、截图及尺寸依据。

## 重建与检查

```sh
uv sync --locked
npm ci
uv run python scripts/build_models.py
uv run python scripts/check_exports.py
npm run build
npm run check:preview
```

Python 3.14 与 `.venv` 由 uv 管理，依赖定义于 `pyproject.toml`，精确版本锁定于 `uv.lock`。新增 Python 依赖使用 `uv add 包名`；`requirements.txt` 为兼容 pip 的导出文件，可用 `uv export --no-hashes --no-dev -o requirements.txt` 更新。

更新电气 Markdown 后，运行 `npm run build:docs` 重新导出两份 HTML。构建使用本机 Google Chrome 将 Mermaid 框图渲染为 SVG；最终 HTML 无外部运行时依赖，不需要重新构建机械模型。

图形原理图的连接数据位于 `scripts/electrical_circuit.py`，绘图代码位于 `scripts/draw_schematics.py`。更新电路时同时更新文字原理图、BOM 和连接数据，然后运行：

```sh
npm run build:schematics
npm run check:schematics
```

物料编号及无编号原因维护在 `electrical_circuit.py` 的 `JLC_GROUPS` / `NO_JLC` 中。构建检查每页的器件标注覆盖，校验脚本比对 BOM 编号并确认 SVG 中实际显示了各条标注。

检查覆盖 75 个 BOM 位号/焊盘位置、65 件默认装配物料、41 件电阻/电容/电感的数值、49 个 MCU 引脚、9 路按键直连、3 路 RGB 直驱，以及图中全部 215 个端子的实际连线。浏览器检查包含文字重叠/裁切、移动页面、切页、缩放和位号定位；这些属于文档与绘图一致性检查，不能替代电气 ERC 和样机测试。网页可离线浏览，SVG 下载依赖同目录的 `schematic-assets/`。

布局及开关尺寸统一定义于 `scripts/layout.json`。建模脚本使用 trimesh / manifold，打印件出现非封闭、非连通实体或已检查部件穿透时会终止导出；库模型的检查方式与例外在器件模型记录中列明。浏览器检查使用已安装的 Google Chrome，包含离线加载、视图、两段键运动、STL 导出和移动屏幕排版。

尚未实物验证按键手感、打印公差、螺纹强度、导光混色及 USB 线缆包胶空间；详细尺寸与假设见设计说明。

## GitHub Pages 发布

推送 `main` 分支中的预览、模型或电气 HTML 更新后，GitHub Actions 自动发布 GitHub Pages。网站根目录和 `/preview.html` 均可打开预览，`/models/` 下提供模型下载，`/electrical/` 下提供文档直链。部署过程发布已生成的文件。

修改布局或建模代码后，先执行上面的重建和检查命令，再提交并推送 `scripts/` 与 `output/` 的更新。也可在 Actions 页面手动运行发布工作流。

原始采购订单含个人收货信息，不上传到公开仓库；所用物料见 [公开物料信息](reference/jlc-orders/README.md)。本地虚拟环境、依赖缓存和历史试验文件同样不提交。
