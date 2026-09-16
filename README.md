# nRF52832 Canon remote — mechanical study v0.8

打开 **[在线 3D 预览](https://guruguru-seu.github.io/nrf-canon-remote/preview.html)**，可直接分享这个链接。

也可下载 `output/preview.html` 后用浏览器离线打开，详见 [机械设计说明](output/设计说明.md)。

机身为 **78 × 43 × 17.35 mm**：保留四向圆环、中心两段键和下方三个圆键，删除长条键及底部五个矩形键。中心开关采用 **K2-1831SL-A4SW-01**，其余七个开关采用 TS-1101-C-W。外壳、PCB 外形、固定孔、USB-C 板舌与开孔配套重建；软包电池候选为 EEMB LP402535 / 320 mAh。

USB-C 选用淘宝自购的 **HX TYPE-C 6P QTWT（6Pin 全贴）**，对应立创 C18357553。USB-C、TS-1101-C-W 和 RGB 的预览使用嘉立创下载模型，原始文件与来源见 [器件模型记录](reference/component-models/README.md)。中心两段开关仍按厂家图纸建模，nRF52832 与电池为外形包络。

这是机械模型，不含原理图、PCB 铜层布局或固件。参考键帽保留形状并平移、修改顶柱；下盖恢复参考工程的梯形截面（43 mm 收至背面 35 mm）；PCB 左上、右上角设 R5 四分之一圆凹口，下盖增加配合定位凸台和托台；采用上中、下左右三点固定。RGB 与导光结构整体下移 5 mm。原始 140 mm 参考模型保留在预览的“原型对照”中。

## 输出

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

布局及开关尺寸统一定义于 `scripts/layout.json`。建模脚本使用 trimesh / manifold，打印件出现非封闭、非连通实体或已检查部件穿透时会终止导出；库模型的检查方式与例外在器件模型记录中列明。浏览器检查使用已安装的 Google Chrome，包含离线加载、视图、两段键运动、STL 导出和移动屏幕排版。

尚未实物验证按键手感、打印公差、螺纹强度、导光混色及 USB 线缆包胶空间；详细尺寸与假设见设计说明。

## GitHub Pages 发布

推送 `main` 分支中的预览或模型更新后，GitHub Actions 自动发布 GitHub Pages。网站根目录和 `/preview.html` 均可打开预览，`/models/` 下提供模型下载。部署过程发布已生成的文件。

修改布局或建模代码后，先执行上面的重建和检查命令，再提交并推送 `scripts/` 与 `output/` 的更新。也可在 Actions 页面手动运行发布工作流。

原始采购订单含个人收货信息，不上传到公开仓库；所用物料见 [公开物料信息](reference/jlc-orders/README.md)。本地虚拟环境、依赖缓存和历史试验文件同样不提交。
