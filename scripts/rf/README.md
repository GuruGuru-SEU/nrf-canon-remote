# openEMS 初步射频计算

本目录独立使用 uv 创建的 Python 3.13 环境，避免影响机械建模的 Python 3.14 环境。

```sh
uv venv --python 3.13 .tools/openems/.venv
uv pip install --python .tools/openems/.venv/bin/python pip setuptools setuptools-scm wheel cython numpy h5py matplotlib shapely scipy
```

本机按 [openEMS 官方源码安装指南](https://docs.openems.de/en/latest/install/clone-build-install.html) 编译 openEMS 0.37.0 / CSXCAD 0.7.0，安装前缀 `.tools/openems`。系统依赖使用 Homebrew 官方仓库的 cmake、boost、hdf5、cgal、vtk；TinyXML 使用上游安装脚本下载并校验的源码及补丁。原生安装目录不提交 Git。

构建扩展时启用该 uv 环境，将 `PATH` 的首项设为其 `bin`，`VIRTUAL_ENV` 设为环境绝对路径，执行 `update_openEMS.sh <安装前缀> --disable-GUI --njobs=8 --python --python-venv-mode=disable`。

```sh
.tools/openems/.venv/bin/python scripts/rf/simulate.py --name nominal --mesh .2
.tools/openems/.venv/bin/python scripts/rf/simulate.py --name refined --mesh .15
.tools/openems/.venv/bin/python scripts/rf/simulate.py --name eps40 --mesh .2 --eps 4.0
.tools/openems/.venv/bin/python scripts/rf/simulate.py --name housed --mesh .2 --shell-eps 2.8
.tools/openems/.venv/bin/python scripts/rf/match.py
node scripts/rf/build_report.mjs
```

仿真几何为 `reference/rf/pcb-20260923.json`。来源、坐标单位、材料假设和参考面写入该文件及每次运行的 metadata。`extract_geometry.py` 是原始快照提取脚本，原始工程快照只保留本地 `tmp`，不公开；已提取的几何足以重跑 `simulate.py`。

**模型边界**：提取两面实际 GND 铺铜、GND 焊盘/线/过孔、板框/安装孔、天线和天线侧馈线。过孔以实心导体近似；铜用 PEC 薄片；省略其他信号铜、阻焊和器件。天线形状来自同一 UUID 的前一天封装导出，放置位置与当日两焊盘核验。未经 Gerber 再次复核，不能称为最终制造模型。FR-4 Dk/Df 是假设值，不是 EDA 中未填写的 0。零件属性里的既有“仿真”备注不作为本次计算证据。

参考面在 **L220 的天线侧焊盘 `$1N324`**，C217 不装，C216/L220 及芯片侧铜不进入模型。端口从该焊盘跨板厚接到对面 GND。结果不代表 nRF52832 ANT 引脚阻抗，也不能据此删掉 Nordic 芯片端参考网络。直接按该结果综合的网络属于独立 50 Ω 天线匹配网络。

`--shell-eps` 是可选的假设外壳/浮置电池包络敏感性实验，未给出实际材料与装配验证前不用于最终选值。

完整说明见 [计算报告](../../output/rf/README.md)。`output/rf/solver-evidence.zip` 保留四组实际运行的日志与端口时域信号；`*.s1p` 是 50 Ω 参考的 Touchstone，`*.csv` 同时保存复阻抗与 S11。求解会产生小图元未使用的警告，已在报告中说明网格限制。`--post` 仅对本地已有运行的端口数据后处理，必须使用与原运行完全相同的几何 / 参数。
