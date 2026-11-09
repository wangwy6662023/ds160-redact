# DS-160 隐私脱敏工具

**把 DS-160 确认页拖进来，个人信息自动打码——完全离线运行，你的签证材料不会离开你的电脑。**

申请美签时，你想把 DS-160 确认页发到论坛求助、给中介或AI优化表格内容——但那上面全是你的姓名、护照号、电话、地址、出生日期。手动打码费时费力还容易漏。这个工具自动识别并打码这些隐私字段，让你放心分享。

## 为什么可以放心

- **零网络请求**：代码里没有任何联网调用。断网照样用，欢迎拔网线验证，也欢迎用防火墙/抓包工具审计
- **纯本地处理**：文件从磁盘读入 → 内存中打码 → 写回磁盘，全程不出本机
- **代码全开源**（AGPL-3.0）：OCR 引擎用的 [RapidOCR](https://github.com/RapidAI/RapidOCR)（Apache-2.0），PDF 渲染用 [PyMuPDF](https://github.com/pymupdf/PyMuPDF)（AGPL-3.0），全部可审计
- **无需安装、无需注册**：下载即用，不弹广告，不打扰

## 功能

- 支持 **PDF 确认页**与**截图**（png/jpg/jpeg/bmp/webp）
- 自动识别并马赛克：姓名（含电码/曾用名）、出生日期、证件号、护照号、电话/传真/邮箱、社媒账号、地址、SEVIS/I-94/I-20 编号、Application ID（红色编号）等 40+ 类字段
- **申请人照片**自动覆盖（彩色色块，不可还原）
- 智能保留：日期保留年份、地址保留城市/州、`Does Not Apply` 等空值原样保留——脱敏后的页面依然可读、可用于核对
- 处理结果输出到独立的「脱敏材料」子文件夹，原文件不动

## 使用

### Windows

1. 到 [Releases](../../releases) 下载 `DS160-Redact-Win.zip`，解压
2. 把要脱敏的 PDF/截图放到 exe 同一文件夹
3. 双击运行，结果在「脱敏材料」子文件夹里

### macOS

1. 下载 `DS160-Redact-Mac-Universal.zip`，解压（如果解压出来还是 zip，再解压一次，最终得到三个文件）
2. 三个文件拷到要处理的文件所在文件夹
3. 双击 `DS160脱敏工具.command`（自动识别 Intel / Apple 芯片）
4. 首次双击被拦截是正常的安全限制：右键 →「打开」→「打开」；如提示"已损坏"，终端执行 `xattr -cr <拖入文件>` 后再双击

### 国内网盘下载（不用翻墙）

| 文件 | 链接 | 提取码 |
|------|------|--------|
| `DS160-Redact-Win.zip` | [百度网盘](https://pan.baidu.com/s/1_IU5jEiV6UcTvpUuXgRo6w?pwd=b6t5) | `b6t5` |
| `DS160-Redact-Mac-Universal.zip` | [百度网盘](https://pan.baidu.com/s/1zK7es_jRnROBHeWaiMsXkQ?pwd=rf9r) | `rf9r` |

### 从源码运行（任意平台）

```bash
pip install -r requirements.txt
python ds160_redact.py
```

## 工作原理

```
PDF/截图 → PyMuPDF 渲染成图像 → RapidOCR(PP-OCR 模型) 定位文字
→ 按 DS-160 字段名匹配隐私项 → 定位字段值区域 → 马赛克/色块覆盖 → 重组输出
```

字段匹配基于 DS-160 各审阅页的实际字段布局（Personal / Address / Phone / Passport / US Contact 等），并处理了折行地址、label 与值 OCR 合并、值漏检兜底等真实场景。

## ⚠️ 重要提醒

- **输出结果请人工复核一遍再公开分享。** OCR 识别存在极小概率漏检，工具是「辅助脱敏」不是「保证脱敏」
- 本工具与美领馆、美国国务院无关，非官方工具，不构成任何法律建议
- 请只处理你本人或已获授权的文件

## 许可证

本项目以 **AGPL-3.0** 授权（依赖 PyMuPDF 的 AGPL 条款），商用、修改、分发均可，须遵守 AGPL 义务（分发时提供源码）。第三方组件许可详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 贡献

欢迎提 Issue / PR：新增字段规则、误伤/漏检案例、新平台打包脚本。提交 PR 即表示同意贡献内容以 AGPL-3.0 授权本项目。
