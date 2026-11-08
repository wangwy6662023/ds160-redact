# -*- coding: utf-8 -*-
"""DS-160 隐私脱敏工具（完全离线，无云服务）
用法: 双击运行（或 python ds160_redact.py）
自动扫描本工具所在文件夹下的 PDF 与截图（png/jpg/jpeg/bmp/webp），
脱敏后输出: PDF -> _redacted.pdf；截图 -> _redacted.png
原理: PyMuPDF 渲染页面 -> RapidOCR 定位 PII 字段值区域 -> 脱敏 -> 重组
"""
import sys, os, re, random
import numpy as np
try:
    import pymupdf    # PyMuPDF >= 1.24
except ImportError:
    import fitz as pymupdf    # PyMuPDF 1.21（Win7 兼容版）
from PIL import Image

DPI = 200
SCALE = DPI / 72.0
IMG_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}

# PII 标签匹配规则（正则，忽略大小写，匹配 label 文本 -> 该 label 对应的值涂黑）
PII_LABELS = [
    r"name provided", r"native alphabet", r"other name", r"telecode name",
    r"surname", r"given name", r"full name", r"family name", r"companion",
    r"^name\b",    # 同行人 Name (1)/(2) 等裸 Name 开头字段
    r"date of birth",
    r"national identification", r"social security", r"taxpayer",
    r"other nationality",
    r"phone", r"fax", r"email",
    r"social media identifier", r"platform identifier",
    r"address",    # 所有地址类字段；值内街道涂、城市/州保留（见续行逻辑）
    r"^postal zone",    # 邮编涂黑；城市/州省/国家保留
    r"passport", r"book number", r"issuance date", r"expiration date",
    r"application id", r"passport/travel document number",
    r"point of contact", r"contact person", r"organization name",
    r"previous u\.s\. visa", r"visa number", r"petition receipt",
    r"sevis", r"i-94", r"i-20", r"ds-2019",
    r"drivers license", r"driver's license number",
    r"additional phone", r"additional email",
    r"payer",
    # 职业、单位/学校名称、城市、州保留，仅处理详细地址（逗号前）
]
# 地址类字段：值可能折行（如 U.S. Contact Address 两行），需向下续行脱敏
ADDRESS_RX = re.compile(r"address|payer", re.IGNORECASE)
PII_RX = re.compile("|".join(PII_LABELS), re.IGNORECASE)

# 值为这些内容时跳过（非隐私，保留原样）
KEEP_VALUES = {"does not apply", "dna", "n/a", "no", "yes", "none", "not applicable"}
# 马赛克块大小（像素）
MOSAIC_BLOCK = 10


def mosaic(img, rect):
    """区域马赛克化：缩小再放大（NEAREST），信息不可辨识"""
    x0, y0, x1, y1 = (max(int(round(v)), 0) for v in rect)
    x1 = min(x1, img.width); y1 = min(y1, img.height)
    w, h = x1 - x0, y1 - y0
    if w < 3 or h < 3:
        return
    bw, bh = max(w // MOSAIC_BLOCK, 1), max(h // MOSAIC_BLOCK, 1)
    small = img.crop((x0, y0, x1, y1)).resize((bw, bh), Image.BILINEAR)
    img.paste(small.resize((w, h), Image.NEAREST), (x0, y0))


def color_blocks(img, rect, block=16):
    """彩色色块覆盖（用于照片）：随机彩色方块拼贴，彻底遮挡"""
    x0, y0, x1, y1 = (max(int(round(v)), 0) for v in rect)
    x1 = min(x1, img.width); y1 = min(y1, img.height)
    pal = [(230, 57, 70), (29, 53, 87), (69, 123, 157), (56, 176, 0),
           (255, 195, 0), (255, 140, 105), (231, 111, 81), (42, 157, 143),
           (155, 93, 229), (0, 150, 199)]
    for by in range(y0, y1, block):
        for bx in range(x0, x1, block):
            img.paste(random.choice(pal),
                      (bx, by, min(bx + block, x1), min(by + block, y1)))
# label 匹配 PII 但内容非隐私的排除项（证件类型等）
KEEP_LABELS = re.compile(r"(document\s+type|^type\b|previous\s+u\.s\.\s+visa\s+type"
                         r"|city\s+where\s+issued|state/province\s+where\s+issued"
                         r"|^country\b|^city\b|^state/province|name\s+of\s+institution)", re.IGNORECASE)
# 日期类字段：只涂月日，保留年份
YEAR_LABELS = re.compile(r"(date of birth|issuance date|expiration date)", re.IGNORECASE)
YEAR_RX = re.compile(r"(?:19|20)\d{2}")
# App ID 样式（如 AA00FU3X49）
APPID_RX = re.compile(r"\bAA\d{2}[A-Z0-9]{5,8}\b")
# 界面元素不处理
UI_RX = re.compile(r"^(edit|print|打印|next|previous|sign|submit|review)", re.IGNORECASE)


def ocr_blocks(img, ocr):
    """RapidOCR -> [(x0,y0,x1,y1,text), ...] 像素坐标"""
    result, _ = ocr(np.asarray(img))
    blocks = []
    if result:
        for box, text, _conf in result:
            xs = [p[0] for p in box]; ys = [p[1] for p in box]
            blocks.append((min(xs), min(ys), max(xs), max(ys), text.strip()))
    return blocks


def is_label(text):
    t = text.strip().rstrip(":：")
    if KEEP_LABELS.search(t):
        return False
    return bool(PII_RX.search(t)) and not UI_RX.match(t)


def redact_page(page, ocr):
    """渲染单页 -> OCR -> 定位并涂黑 PII -> 返回 PIL Image"""
    pix = page.get_pixmap(dpi=DPI)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    blocks = ocr_blocks(img, ocr)
    n = 0

    # 1) PDF 内嵌照片（申请人头像）：彩色色块覆盖
    for xref, *_ in page.get_images(full=True):
        try:
            for r in page.get_image_rects(xref):
                w, h = r.width, r.height
                if 30 < w < 200 and 30 < h < 200:  # 头像尺寸特征
                    color_blocks(img, (r.x0*SCALE-3, r.y0*SCALE-3,
                                        r.x1*SCALE+3, r.y1*SCALE+3))
                    n += 1
        except Exception:
            pass

    # 2) 文本类 PII（label 值 + AppID）
    n += redact_text(img, blocks)
    return img, n


def redact_standalone(img, ocr):
    """独立图片（系统截图）：OCR + 文本脱敏（无内嵌照片处理）
    小图或极端长宽比（如裁剪局部）先垫白底画布再识别，处理后裁回原区域输出"""
    if img.width < 900 or img.height < 200 or img.width / max(img.height, 1) > 4:
        pad_w, pad_h = max(img.width, 1200), max(img.height, 500)
        x_off, y_off = 30, max((pad_h - img.height) // 2, 20)
        canvas = Image.new('RGB', (pad_w, pad_h), 'white')
        canvas.paste(img, (x_off, y_off))
        blocks = ocr_blocks(canvas, ocr)
        n = redact_text(canvas, blocks)
        img = canvas.crop((x_off, y_off, x_off + img.width, y_off + img.height))
        return img, n
    blocks = ocr_blocks(img, ocr)
    n = redact_text(img, blocks)
    return img, n


def redact_text(img, blocks):
    """label->值 匹配 + AppID 马赛克，返回处理数"""
    n = 0
    # 第一遍：建立 label->值 映射，推断值列 x0 中位数（用于值漏检兜底）
    pairs, vxs = [], []
    for i, b in enumerate(blocks):
        if not is_label(b[4]):
            continue
        lx0, ly0, lx1, ly1, text = b
        row_cy = (ly0 + ly1) / 2
        row_h = ly1 - ly0
        vals = []
        for c in blocks:
            cx0, cy0, cx1, cy1, ct = c
            if c is b:
                continue
            if c[4] and c[4].strip().rstrip(":") == text:
                continue
            cy = (cy0 + cy1) / 2
            if abs(cy - row_cy) < row_h * 0.7 and cx0 > lx1 - 5:
                vals.append(c)
        pairs.append(((lx0, ly0, lx1, ly1, text), vals))
        vxs.extend(v[0] for v in vals)
    vx_med = sorted(vxs)[len(vxs) // 2] if vxs else None

    for (lx0, ly0, lx1, ly1, text), vals in pairs:
        if not vals:
            # label 与值 OCR 合并在同一块（如 "Family Name: ZHANG"）：马赛克冒号后的值部分
            # 要求 label 词后紧跟冒号（字段行特征），避免误伤 "Passport Information" 等页面标题
            m = PII_RX.search(text)
            tail = text[m.end():] if m else ""
            if (m and tail.lstrip().startswith((":", "："))
                    and tail.lstrip(" :：,").strip()):
                w = lx1 - lx0
                sx = lx0 + (m.end() / max(len(text), 1)) * w
                mosaic(img, (sx - 2, ly0 - 3, lx1 + 4, ly1 + 3))
                n += 1
            elif m and vx_med and text.rstrip().endswith((":", "：")):
                # 值被 OCR 漏检（如极短值 "2"）：从 label 右边界到值列末端兜底马赛克
                mosaic(img, (lx1 + 4, ly0 - 3, vx_med + 420, ly1 + 3))
                n += 1
            continue  # 无同右侧值（可能是纯 label 换行）
        joined = " ".join(v[4] for v in vals)
        if joined.strip().lower().rstrip(".") in KEEP_VALUES:
            continue  # DOES NOT APPLY 等保留
        keep_year = bool(YEAR_LABELS.search(text))
        addr_mode = bool(ADDRESS_RX.search(text)) and not keep_year
        # 地址类字段：先收集续行值（如 U.S. Contact Address 折行），再决定各行处理
        conts = []
        if addr_mode and vals:
            last = max(vals, key=lambda v: (v[3], v[0]))
            row_h_ref = ly1 - ly0
            for _ in range(4):  # 最多 4 行续行
                nxt = None
                for c in blocks:
                    cx0, cy0, cx1, cy1, ct = c
                    if (not ct or is_label(ct) or ct.rstrip().endswith((":", "："))
                            or re.match(r"^[^:：]{1,40}[:：]\s*\S", ct)):
                        continue  # label 行 / label:值 合并块都是新字段行，不是续行
                    if (abs(cx0 - last[0]) < 250 and 0 <= cy0 - last[3] < row_h_ref * 1.1
                            and ct.strip().lower().rstrip(".") not in KEEP_VALUES):
                        # 左侧同排有 label 文本（如 "City:"）→ 新字段行，停止续行
                        if any(t[4] and t is not c and t[2] < cx0 - 20
                               and abs((t[1] + t[3]) / 2 - (cy0 + cy1) / 2) < (cy1 - cy0) * 0.7
                               for t in blocks):
                            break
                        if nxt is None or cy0 < nxt[1]:
                            nxt = c
                if nxt is None:
                    break
                conts.append(nxt)
                last = nxt
        for v in sorted(vals, key=lambda v: v[0]):
            vx0, vy0, vx1, vy1, vtext = v
            if keep_year:
                m = YEAR_RX.search(vtext)
                if m:
                    # 按字符比例定位年份像素位置，马赛克年份前后内容、保留年份
                    w = vx1 - vx0
                    pre_x = vx0 + (m.start() / max(len(vtext), 1)) * w
                    post_x = vx0 + (m.end() / max(len(vtext), 1)) * w
                    if m.start() > 0:
                        mosaic(img, (vx0-4, vy0-3, pre_x+2, vy1+3))
                    if vtext[m.end():].strip(" .,-"):
                        mosaic(img, (post_x-2, vy0-3, vx1+4, vy1+3))
                    n += 1
                    continue
            if addr_mode and not conts and "," in vtext:
                # 单行地址值：只涂第一个逗号前的详细地址，保留后面的城市/州
                w = vx1 - vx0
                comma_x = vx0 + (vtext.index(",") / max(len(vtext), 1)) * w
                if comma_x - vx0 > 8:
                    mosaic(img, (vx0-4, vy0-3, comma_x, vy1+3))
                    n += 1
                continue
            mosaic(img, (vx0-4, vy0-3, vx1+4, vy1+3))
            n += 1
        if conts:
            # 续行除末行外整行涂；末行含逗号视为 "城市, 州" 保留
            for c in conts[:-1]:
                mosaic(img, (c[0]-4, c[1]-3, c[2]+4, c[3]+3))
                n += 1
            if "," not in conts[-1][4]:
                mosaic(img, (conts[-1][0]-4, conts[-1][1]-3,
                             conts[-1][2]+4, conts[-1][3]+3))
                n += 1

    # App ID（红色编号，独立文本）
    for b in blocks:
        if APPID_RX.search(b[4]):
            mosaic(img, (b[0]-4, b[1]-3, b[2]+4, b[3]+3))
            n += 1

    return n


def main():
    # 工具所在文件夹（exe 打包后取 exe 所在目录，脚本运行取脚本目录）
    if getattr(sys, "frozen", False):
        workdir = os.path.dirname(sys.executable)
    else:
        workdir = os.path.dirname(os.path.abspath(__file__))
    print(f"扫描文件夹: {workdir}")

    exts = IMG_EXTS | {".pdf"}
    files = [f for f in os.listdir(workdir)
             if os.path.splitext(f)[1].lower() in exts
             and "_redacted" not in f
             and not f.startswith("~$")]
    if not files:
        print("未找到可处理的 PDF/截图。把要脱敏的文件放到本工具所在文件夹后再运行。")
        return

    # 输出统一放到独立子文件夹，便于查找
    out_dir = os.path.join(workdir, "脱敏材料")
    os.makedirs(out_dir, exist_ok=True)

    from rapidocr_onnxruntime import RapidOCR
    ocr = RapidOCR()
    grand = 0
    for f in sorted(files):
        path = os.path.join(workdir, f)
        base, ext = os.path.splitext(f)
        try:
            if ext.lower() == ".pdf":
                doc = pymupdf.open(path)
                pages, total = [], 0
                for i, page in enumerate(doc):
                    img, n = redact_page(page, ocr)
                    total += n
                    pages.append(img)
                    print(f"[{f}] 第{i+1}页 脱敏 {n} 处")
                p_pdf = os.path.join(out_dir, f"{base}_redacted.pdf")
                pages[0].save(p_pdf, save_all=True,
                              append_images=pages[1:] if len(pages) > 1 else [],
                              resolution=DPI)
                print(f"[{f}] 脱敏 {total} 处 -> 脱敏材料/{base}_redacted.pdf")
                grand += total
            else:
                img = Image.open(path).convert("RGB")
                img, n = redact_standalone(img, ocr)
                out = os.path.join(out_dir, f"{base}_redacted.png")
                img.save(out)
                grand += n
                print(f"[{f}] 脱敏 {n} 处 -> 脱敏材料/{base}_redacted.png")
        except Exception as e:
            print(f"[{f}] 处理失败: {e}")
    print(f"\n完成：{len(files)} 个文件，共脱敏 {grand} 处隐私内容")


if __name__ == "__main__":
    main()
    try:
        input("\n按回车键退出...")
    except (EOFError, SyntaxError):
        pass
