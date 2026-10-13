"""OCR识别服务：使用PaddleOCR识别证件内容并提取关键信息。

支持证件类型：
- 营业执照
- 食品经营许可证
- 第三方检验报告
- 出厂检验报告
"""
import os
import io
import re
from datetime import date, timedelta

# 延迟导入，避免在没有OCR环境时报错
try:
    from paddleocr import PaddleOCR
    _ocr_instance = None
except ImportError:
    _ocr_instance = None


def get_ocr_instance():
    """获取单例OCR实例（懒加载）。"""
    global _ocr_instance
    if _ocr_instance is None:
        try:
            _ocr_instance = PaddleOCR(
                use_angle_cls=True,
                lang="ch",
                show_log=False,
                use_gpu=False,
            )
        except Exception as e:
            raise RuntimeError(f"初始化OCR引擎失败: {e}")
    return _ocr_instance


def recognize_image(image_bytes):
    """识别图片中的文本。

    Args:
        image_bytes: 图片字节数据

    Returns:
        list: 识别结果列表，每项为 [[x1,y1,x2,y2,...], (text, confidence)]
    """
    try:
        ocr = get_ocr_instance()
        result = ocr.ocr(io.BytesIO(image_bytes), cls=True)
        return result[0] if result else []
    except Exception as e:
        raise RuntimeError(f"OCR识别失败: {e}")


def extract_text_from_pdf(pdf_bytes):
    """从PDF中提取文本（需要PDF转换为图片）。"""
    try:
        import fitz
    except ImportError:
        return None

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        texts = []
        for page_num in range(min(len(doc), 3)):
            page = doc[page_num]
            text = page.get_text()
            if text.strip():
                texts.append(text)
        doc.close()
        return "\n".join(texts)
    except Exception:
        return None


def extract_text_from_image(image_bytes):
    """从图片提取OCR文本。"""
    try:
        result = recognize_image(image_bytes)
        if not result:
            return ""
        texts = [line[1][0] for line in result if line[1][0].strip()]
        return " ".join(texts)
    except Exception:
        return ""


def parse_cert_type(text):
    """解析证件类型。"""
    if not text:
        return None

    text_lower = text.lower()

    if any(kw in text for kw in ["营业执照", "执照", "营业执照副本"]):
        return "business_license"
    if "business license" in text_lower or "businesslicence" in text_lower:
        return "business_license"

    if any(kw in text for kw in ["食品经营许可证", "食品经营许可证", "食品证"]):
        return "food_license"
    if "food license" in text_lower or "food licence" in text_lower:
        return "food_license"

    if any(kw in text for kw in ["第三方检验报告", "第三方检验", "检验报告", "检测报告", "质检报告"]):
        return "third_party"
    if "test report" in text_lower or "inspection report" in text_lower:
        return "third_party"

    if any(kw in text for kw in ["出厂检验报告", "出厂检验", "厂检报告", "产品质量检验"]):
        return "factory"
    if "factory report" in text_lower or "production report" in text_lower:
        return "factory"

    return None


def extract_dates(text):
    """从文本中提取日期。"""
    dates = {
        "valid_until": None,
        "issue_date": None,
        "test_date": None,
        "production_date": None,
    }

    if not text:
        return dates

    date_patterns = [
        r"(\d{4})年(\d{1,2})月(\d{1,2})日",
        r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})",
        r"有效期至[:：]\s*(\d{4})年(\d{1,2})月(\d{1,2})日",
        r"有效期至[:：]\s*(\d{4})[-/](\d{1,2})[-/](\d{1,2})",
        r"发证日期[:：]\s*(\d{4})年(\d{1,2})月(\d{1,2})日",
        r"发证日期[:：]\s*(\d{4})[-/](\d{1,2})[-/](\d{1,2})",
        r"检验日期[:：]\s*(\d{4})年(\d{1,2})月(\d{1,2})日",
        r"检验日期[:：]\s*(\d{4})[-/](\d{1,2})[-/](\d{1,2})",
        r"生产日期[:：]\s*(\d{4})年(\d{1,2})月(\d{1,2})日",
        r"生产日期[:：]\s*(\d{4})[-/](\d{1,2})[-/](\d{1,2})",
    ]

    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            year, month, day = match.groups()
            date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            context_start = max(0, match.start()-15)
            context_end = min(len(text), match.end()+20)
            context = text[context_start:context_end]

            if "有效" in context or "有效期" in context:
                dates["valid_until"] = date_str
            elif "发证" in context:
                dates["issue_date"] = date_str
            elif "检验" in context:
                dates["test_date"] = date_str
            elif "生产" in context:
                dates["production_date"] = date_str
            else:
                dates["valid_until"] = date_str

    return dates


def extract_manufacturer(text):
    """从文本中提取厂家名称。"""
    if not text:
        return None

    patterns = [
        r"名\s*称[:：]\s*([^\n\r]{2,50})",
        r"公司名称[:：]\s*([^\n\r]{2,50})",
        r"企业名\s*称[:：]\s*([^\n\r]{2,50})",
        r"商\s*号[:：]\s*([^\n\r]{2,50})",
        r"经\s*营\s*者[:：]\s*([^\n\r]{2,50})",
        r"委托人[:：]\s*([^\n\r]{2,50})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            name = match.group(1).strip()
            for suffix in ["有限公司", "有限责任公司", "股份有限公司", "厂", "店", "中心", "经营部"]:
                name = name.replace(suffix, "").strip()
            if len(name) >= 2:
                return name

    return None


def extract_product_name(text):
    """从文本中提取产品名称。"""
    if not text:
        return None

    patterns = [
        r"产\s*品\s*名\s*称[:：]\s*([^\n\r]{2,50})",
        r"商品名称[:：]\s*([^\n\r]{2,50})",
        r"项目名称[:：]\s*([^\n\r]{2,50})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            name = match.group(1).strip()
            if len(name) >= 2:
                return name

    return None


def parse_ocr_result(text):
    """解析OCR结果，提取结构化信息。"""
    result = {
        "cert_type": None,
        "manufacturer": None,
        "product_name": None,
        "valid_until": None,
        "test_date": None,
        "production_date": None,
        "raw_text": text,
    }

    if not text:
        return result

    result["cert_type"] = parse_cert_type(text)
    dates = extract_dates(text)
    result.update(dates)
    result["manufacturer"] = extract_manufacturer(text)
    result["product_name"] = extract_product_name(text)

    if not result["manufacturer"]:
        first_line = text.strip().split("\n")[0].strip()
        if len(first_line) >= 2 and len(first_line) <= 50:
            exclude_keywords = ["检验", "报告", "日期", "编号", "地址", "电话"]
            if not any(kw in first_line for kw in exclude_keywords):
                result["manufacturer"] = first_line

    return result


def ocr_upload(file_bytes, filename=None):
    """对上传的文件进行OCR识别。"""
    result = {
        "success": False,
        "filename": filename or "unknown",
        "cert_type": None,
        "manufacturer": None,
        "product_name": None,
        "valid_until": None,
        "test_date": None,
        "production_date": None,
        "raw_text": "",
    }

    try:
        ext = os.path.splitext(filename or "")[1].lower()
        text = ""

        if ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]:
            text = extract_text_from_image(file_bytes)
        elif ext == ".pdf":
            text = extract_text_from_pdf(file_bytes)
            if not text or len(text) < 10:
                try:
                    import fitz
                    doc = fitz.open(stream=file_bytes, filetype="pdf")
                    texts = []
                    for page_num in range(min(len(doc), 3)):
                        page = doc[page_num]
                        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                        texts.append(extract_text_from_image(pix.tobytes("png")))
                    doc.close()
                    text = "\n".join(texts)
                except Exception:
                    pass

        if not text:
            result["error"] = "无法提取文本内容"
            return result

        result["raw_text"] = text
        parsed = parse_ocr_result(text)
        result.update(parsed)
        result["success"] = True

        return result

    except Exception as e:
        result["error"] = str(e)
        return result
