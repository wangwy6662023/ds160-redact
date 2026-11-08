# 第三方组件与许可声明

本项目使用以下开源组件。分发本工具时须保留本声明。

| 组件 | 用途 | 许可证 | 上游 |
|------|------|--------|------|
| PyMuPDF | PDF 页面渲染与图像提取 | AGPL-3.0 | https://github.com/pymupdf/PyMuPDF |
| RapidOCR (rapidocr-onnxruntime) | OCR 文字识别引擎 | Apache-2.0 | https://github.com/RapidAI/RapidOCR |
| PP-OCR 系列模型（RapidOCR 内置） | OCR 检测/识别模型权重 | Apache-2.0 | https://github.com/PaddlePaddle/PaddleOCR |
| onnxruntime | 模型推理运行时 | MIT | https://github.com/microsoft/onnxruntime |
| Pillow | 图像处理与马赛克 | HPND / MIT-CMU | https://github.com/python-pillow/Pillow |
| NumPy | 数组运算 | BSD-3-Clause | https://github.com/numpy/numpy |
| PyInstaller（仅构建期） | 打包可执行文件 | GPL-2.0-with-bootloader-exception | https://github.com/pyinstaller/pyinstaller |

说明：
- 本项目主许可证为 AGPL-3.0，主要因 PyMuPDF 的 copyleft 条款所致；本工具无任何网络服务形态，AGPL 的网络条款在本项目中不产生额外约束
- RapidOCR / PP-OCR / onnxruntime 为宽松许可证，不传染本项目许可选择；按要求保留许可与版权声明，且不得以上游商标名义宣传本产品
