# Gerber 驱动的 openEMS 计算（2026-09-24）

当前几何来自用户提供的 `Gerber_nRF52832遥控器_2026-09-24.zip`，SHA-256 为 `3fc97f87b7eec812915d751c0682821ee30cdcd28201358806b40dc6174ed5ac`。不再使用前一天封装拼接天线。几何包含全部两面铜、PTH/NPTH；飞针文件只用于识别 L220 焊盘位置。原始 ZIP 保留本地，提取的 JSON 足以复算。没有原始 ZIP 时跳过下方 `extract_gerber.py`，直接使用仓库中的 JSON 运行求解。

独立 uv 环境使用 Python 3.13：

```sh
uv venv --python 3.13 .tools/openems/.venv
uv pip install --python .tools/openems/.venv/bin/python pip setuptools setuptools-scm wheel cython numpy h5py matplotlib shapely scipy gerbonara==1.6.3
```

本机按 [openEMS 官方指南](https://docs.openems.de/en/latest/install/clone-build-install.html) 编译 openEMS 0.37.0 / CSXCAD 0.7.0，安装前缀 `.tools/openems`。系统依赖为 Homebrew 的 cmake、boost、hdf5、cgal、vtk；原生安装不提交 Git。构建扩展时将该 uv 环境加入 PATH，设置 VIRTUAL_ENV，执行 `update_openEMS.sh <安装前缀> --disable-GUI --njobs=8 --python --python-venv-mode=disable`。

```sh
set -o pipefail
mkdir -p tmp
.tools/openems/.venv/bin/python scripts/rf/extract_gerber.py
.tools/openems/.venv/bin/python scripts/rf/simulate.py --name gerber-bare --mesh .2 2>&1 | tee tmp/rf-gerber-bare.log
.tools/openems/.venv/bin/python scripts/rf/simulate.py --name gerber-fine --mesh .15 2>&1 | tee tmp/rf-gerber-fine.log
.tools/openems/.venv/bin/python scripts/rf/simulate.py --name gerber-finer --mesh .1 2>&1 | tee tmp/rf-gerber-finer.log
.tools/openems/.venv/bin/python scripts/rf/simulate.py --name gerber-low-loss --mesh .15 --loss .013 2>&1 | tee tmp/rf-gerber-low-loss.log
.tools/openems/.venv/bin/python scripts/rf/simulate.py --name gerber-dk43 --mesh .15 --eps 4.3 2>&1 | tee tmp/rf-gerber-dk43.log
.tools/openems/.venv/bin/python scripts/rf/simulate.py --name gerber-housed --mesh .15 --shell-eps 2.8 2>&1 | tee tmp/rf-gerber-housed.log
.tools/openems/.venv/bin/python scripts/rf/analyze_gerber.py
node scripts/rf/build_report.mjs
```

运行名唯一对应几何和参数，不要对仍在运行的目录再次执行。`--post` 只后处理已有时域数据，必须使用相同参数。

默认板厚 1.6 mm，Dk=4.5，Df=0.02。材料来源及频率限制见 `reference/rf/materials-20260924.json`。Dk=4.5 是立创双层板公开典型值；Df=0.02 是其 1 MHz 通用值，不能声称为此订单 2.4 GHz 实测值。低损耗对照 Df=0.013 来自建滔 KB-6160 厚芯板 2 GHz 参数，未断言订单使用此料号。

50 Ω 集总端口位于 **L220 天线侧焊盘**，跨板厚连接对面地铜。电路元件不装，不包含射频芯片阻抗。C216/L220/C217 数值未嵌入 EM 模型。匹配综合同时扫描并联支路在负载端 / 输入端的两种理想 L 网络，仅适用于这个端口。不能直接套用到现板位号。

模型保留 Gerber 中细小铜间隙及独立焊盘的嵌套关系，但 FDTD 网格可能遗漏小图元，日志会记录警告。过孔按孔半径 + 25 µm 的实心导体近似，铜采用 PEC 片，阻焊开窗已解析但介质本身未纳入。省略元件负载、铜损、USB 金属、螺钉、人体；装壳组仅假设上下盖 εr=2.8、tanδ=0.01，并加入机械布局对应的浮置电池导体包络。

`gerber-solver-evidence.zip` 保存本轮所有求解日志、端口时域数据和参数。历史 `*-16` 及无后缀输出保留对照；它们不是最新 Gerber 结果。旧快照提取脚本 / 旧匹配脚本仅供历史复现，默认主流程以上述命令为准。
