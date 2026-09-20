# 电气设计参考资料

核对日期：2026-09-17。本目录收录首次文字原理图使用的厂商资料，版权归各原作者。工程设计见 [原理图 v0.1](../../output/electrical/原理图-v0.1.md)。采购来源和设计选型不同：目录中有资料，不代表该器件已经采购。

## Nordic

| 资料 | 原始来源 | 本地文件／用途 |
| --- | --- | --- |
| nRF52832 QFAx Reference Layout v1.1 | [Nordic 官方 ZIP](https://nsscprodmedia.blob.core.windows.net/prod/software-and-other-downloads/reference-layouts/nrf52832qfaxreflayoutv11.zip) | [QFAA DC/DC 原理图](nrf52832_qfaa_dcdc_schematic.pdf)、[QFAA DC/DC PCB](nrf52832_qfaa_dcdc_pcb.pdf)，从官方压缩包提取，未改动 |
| Product Specification：引脚 | [Pin assignments](https://docs.nordicsemi.com/r/bundle/ps_nrf52832/page/pin.html) | QFN48 的脚号、VDD、VSS、DEC 与 GPIO |
| Product Specification：参考电路 | [Reference circuitry](https://docs.nordicsemi.com/r/bundle/ps_nrf52832/page/ref_circuitry.html) | 3.9 nH / 0.8 pF RF 网络、DC/DC 和去耦 BOM |
| Product Specification：时钟 | [CLOCK](https://docs.nordicsemi.com/r/bundle/ps_nrf52832/page/clock.html) | 晶体负载、引脚电容、ESR、精度要求 |
| Product Specification：ADC | [SAADC](https://docs.nordicsemi.com/r/bundle/ps_nrf52832/page/saadc.html) | 电池分压的采集时间与输入范围 |
| Product Specification：GPIO | [GPIO](https://docs.nordicsemi.com/r/bundle/ps_nrf52832/page/gpio.html) | RGB 直驱采用 H0S1；驱动电流、低电平压降与初始化配置 |
| Errata 138 | [Rev.3 anomaly 138](https://docs.nordicsemi.com/r/bundle/errata_nrf52832_rev3/page/err/nrf52832/rev3/latest/anomaly_832_138.html) | P0.25/P0.26 的参考电容处理 |
| PCB 指南 | [nRF52832 Specific PCB Guidelines](https://devzone.nordicsemi.com/guides/hardware-design-test-and-measuring/b/nrf5x/posts/nrf52832-specific-pcb-guidelines) | 补充解释 DEC2 的封装差异、C13/C14 和局部布局；该页面标为旧指南，结合当前规格及官方参考文件使用 |

## 库存器件资料

| 物料 | 文件 | 来源／核对内容 |
| --- | --- | --- |
| C52212029 / NH-B1515RGBA-GF | [PDF](NH-B1515RGBA-GF.pdf) | [国星厂商 PDF，立创托管](https://atta.szlcsc.com/upload/public/pdf/source/20251030/EECF4F56E4F8547E9265236F0C1AEE5B.pdf)；第 6 页引脚，2 共阳、1 红、3 蓝、4 绿 |
| C2925419 / KH-2012-HM1 | [PDF](KH-2012-HM1.pdf) | [金航标官网 PDF](https://www.kinghelm.net/upload/file/20240619/KH-2012-HM1.pdf)；第 2 页焊盘与净空，1 INPUT、2 NC；第 3 页示例板和匹配 |
| C49208527 / MSTP4054-42 | [PDF](MSTP4054-42.pdf) | [美森科厂商 PDF，立创托管](https://atta.szlcsc.com/upload/public/pdf/source/20250701/DF15CD7DF13D43087D35725B366D9DAB.pdf)；引脚、电流公式、充电终止条件 |
| C82942 / ME6211C33M5G-N | [PDF](ME6211.pdf) | [微盟 ME6211 系列 PDF，立创托管](https://atta.szlcsc.com/upload/public/pdf/source/20170918/C82942_1505727073070976520.pdf)；SOT23-5 的 C 系列引脚及 C33 电气参数；首页与 C33 表静态电流存在差异，按较高值预算 |
| C2891732 / SI2302 | [PDF](SI2302.pdf) | [永裕泰厂商 PDF，立创托管](https://atta.szlcsc.com/upload/public/pdf/source/20260225/4C26798752F14A6C8689DB8E1FD76F36.pdf)；N-MOS，1G/2S/3D，低压栅极驱动规格 |
| C54427949 / YE32MDBCD2X | [系列 PDF](YE32MDBCD2X.pdf) | [雅晶鑫系列 PDF，立创托管](https://atta.szlcsc.com/upload/public/pdf/source/20260323/688CCC4499BA77041AC465C19328DD85.pdf)；1/3 晶体、2/4 GND。完整料号的 32 MHz / 10 pF 见库存记录与[对应商品](https://item.szlcsc.com/57752896.html)，通用 PDF 未单独列出该订购后缀 |
| C18209174 / KFC3276812520T | [PDF](KFC3276812520T.pdf) | [凯越翔厂商 PDF，立创托管](https://datasheet.lcsc.com/datasheet/pdf/f310e2e4c21d4f7a5e8427f5db47ddd3.pdf?productCode=C18209174)；CL=12.5 pF、32.768 kHz、ESR 最大 70 kΩ |
| C411950 / SCL1608S100KSP，**不选用** | 系列数据来源 | [顺翔诺 SCL 系列 PDF，立创托管](https://datasheet.lcsc.com/lcsc/2304140030_Sunltech-Tech-SCL1608Q3R3KSP_C411948.pdf)；链接所属 SKU 是同系列其他感值，需读表内 **SCL1608S100KSP** 行；额定电流 3 mA，不能当作 Nordic 参考电路要求的 ≥50 mA 电感 |

USB-C 与普通轻触开关的库资料继续使用 [component-models](../component-models/README.md)。中心开关使用 [K2-1831SL-A4SW-01 厂商图纸](../../output/review/k2-1831sl-datasheet.pdf)，以图中的 a/b/c 触点标记核对封装。

## 本版新增选件依据

- [AO3401A，AOS 厂商规格](https://www.aosmd.com/pdfs/datasheet/AO3401A.pdf)（[本地 PDF](AO3401A.pdf)）：P-MOS 电池通路，不能以库存 SI2302 N-MOS 代替。
- [BAT54H，Nexperia 厂商规格](https://assets.nexperia.com/documents/data-sheet/BAT54H.pdf)：SOD123F 肖特基，用于 USB→VSYS；只通过系统电流。
- [MLZ1608M100WT000，TDK 厂商页面](https://product.tdk.com/en/search/inductor/inductor/smd/info?part_no=MLZ1608M100WT000)：10 µH、0603、电感变化额定电流 90 mA。

RF 的 3.9 nH 和 0.8 pF 按 Nordic QFN48 参考 BOM 新增采购，完整厂商料号尚未锁定；天线匹配预留元件待实板调试。没有把库存近似值标成已验证替代件。
