# nRF52832 Canon remote — mechanical study v0.7

打开 **[在线 3D 预览](https://guruguru-seu.github.io/nrf-canon-remote/preview.html)**，可直接分享这个链接。

也可下载 `output/preview.html` 后用浏览器离线打开，详见 [机械设计说明](output/设计说明.md)。

机身为 **78 × 43 × 17.35 mm**：保留四向圆环、中心两段键和下方三个圆键，删除长条键及底部五个矩形键。中心开关采用 **K2-1831SL-A4SW-01**，其余七个开关采用 TS-1101-C-W。外壳、PCB 外形、固定孔、USB-C 板舌与开孔配套重建；软包电池候选为 EEMB LP402535 / 320 mAh。

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
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
npm ci
.venv/bin/python scripts/build_models.py
npm run build
npm run check:preview
```

布局及开关尺寸统一定义于 `scripts/layout.json`。建模脚本使用 trimesh / manifold，出现非封闭、非连通实体或已检查部件穿透时会终止导出。浏览器检查使用已安装的 Google Chrome，包含离线加载、视图、两段键运动、STL 导出和移动屏幕排版。

尚未实物验证按键手感、打印公差、螺纹强度、导光混色及 USB 线缆包胶空间；详细尺寸与假设见设计说明。

## GitHub Pages 发布

推送 `main` 分支中的预览或模型更新后，GitHub Actions 自动发布 GitHub Pages。网站根目录和 `/preview.html` 均可打开预览，`/models/` 下提供模型下载。部署过程发布已生成的文件。

修改布局或建模代码后，先执行上面的重建和检查命令，再提交并推送 `scripts/` 与 `output/` 的更新。也可在 Actions 页面手动运行发布工作流。

原始采购订单含个人收货信息，不上传到公开仓库；所用物料见 [公开物料信息](reference/jlc-orders/README.md)。本地虚拟环境、依赖缓存和历史试验文件同样不提交。
