"""批量上传：文件名解析 + 自动创建厂家/商品 + 证件入库。

文件名格式（分隔符支持 - 、 __ 、 # 、 — 、 _ ）：
    厂家名-商品名-规格-类别-证件类型[-日期]

证件类型关键字（任一即可）：
    营业执照/执照/business      -> 营业执照
    食品经营许可证/食品证/food   -> 食品经营许可证
    第三方检验报告/第三方/third  -> 第三方检验报告
    出厂检验报告/出厂/厂检/factory -> 出厂检验报告

厂家级证件只需：厂家名-证件类型
单品级证件需要：厂家名-商品名-...-证件类型

日期为可选末段，格式 YYYY-MM-DD：
    - 第三方检验报告：作为有效期至（未提供则默认上传日+365天）
    - 出厂检验报告：作为检验日期（未提供则默认当天）
    - 厂家级证件：作为有效期至（未提供则视为长期）
"""
import os
import io
import re
import zipfile
from datetime import date, timedelta

from flask import current_app
from werkzeug.datastructures import FileStorage

from ..extensions import db
from ..models import (
    Manufacturer, Product, BusinessLicense, FoodLicense,
    ThirdPartyReport, FactoryReport,
)
from ..utils.file_storage import save_upload
from ..utils.date_utils import parse_date


# 证件类型关键字（长的在前，避免短词误匹配）
CERT_TYPE_KEYWORDS = [
    ("third_party", ["第三方检验报告", "第三方检验", "第三方", "检验报告", "third"]),
    ("business_license", ["营业执照", "执照", "business", "yingye"]),
    ("food_license", ["食品经营许可证", "食品经营", "食品证", "食品许可", "food", "shipin"]),
    ("factory", ["出厂检验报告", "出厂检验", "出厂", "厂检", "factory"]),
]

SEPARATORS = ["-", "__", "#", "—", "_"]

DATE_RE = re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}$")


def detect_cert_type(text):
    """从一段文本中识别证件类型。"""
    text = text.lower()
    for ctype, keywords in CERT_TYPE_KEYWORDS:
        for kw in keywords:
            if kw.lower() in text:
                return ctype
    return None


def parse_filename(filename):
    """解析文件名，返回 dict 或 None。

    返回字段：manufacturer_name, product_name, spec, category, cert_type, date_str
    """
    name = os.path.splitext(filename)[0].strip()
    if not name:
        return None

    best = None
    for sep in SEPARATORS:
        if sep not in name:
            continue
        parts = [p.strip() for p in name.split(sep) if p.strip()]
        result = _try_parse_parts(parts)
        if result:
            # 优先使用分段更少（更明确）的解析
            if best is None or len(parts) < best[0]:
                best = (len(parts), result)
    # 若没有分隔符，尝试把整体作为"厂家名+证件类型"
    if best is None:
        result = _try_parse_parts([name])
        if result:
            best = (1, result)
    return best[1] if best else None


def _try_parse_parts(parts):
    if not parts:
        return None
    # 末段是否为日期
    date_str = None
    if DATE_RE.match(parts[-1]):
        date_str = parts[-1]
        parts = parts[:-1]
    if not parts:
        return None

    # 末段是否为证件类型
    cert_type = detect_cert_type(parts[-1])
    if cert_type:
        parts = parts[:-1]
    else:
        # 尝试在所有段中识别
        full = " ".join(parts)
        cert_type = detect_cert_type(full)
        if not cert_type:
            return None

    if not parts:
        return None

    if cert_type in ("business_license", "food_license"):
        # 厂家级：只取厂家名
        manufacturer_name = parts[0]
        if not manufacturer_name:
            return None
        return {
            "manufacturer_name": manufacturer_name,
            "product_name": None,
            "spec": None,
            "category": None,
            "cert_type": cert_type,
            "date_str": date_str,
        }
    else:
        # 单品级：需要厂家名 + 商品名
        if len(parts) < 2:
            return None
        manufacturer_name = parts[0]
        product_name = parts[1]
        spec = parts[2] if len(parts) > 2 else None
        category = parts[3] if len(parts) > 3 else None
        if not manufacturer_name or not product_name:
            return None
        return {
            "manufacturer_name": manufacturer_name,
            "product_name": product_name,
            "spec": spec,
            "category": category,
            "cert_type": cert_type,
            "date_str": date_str,
        }


def process_single_file(file_storage, original_filename, file_content=None):
    """处理单个文件：解析文件名 → 自动创建厂家/商品 → 保存证件。

    返回 dict：{filename, status, message, manufacturer, product, cert_type, file_content}
    """
    # 保存原始文件内容（如果还没保存）
    if file_content is None:
        try:
            file_storage.stream.seek(0)
            file_content = file_storage.stream.read()
            file_storage.stream.seek(0)
        except Exception:
            file_content = None

    parsed = parse_filename(original_filename)
    if not parsed:
        return _err(original_filename, "文件名格式无法识别，请按 厂家名-商品名-规格-类别-证件类型 命名", file_content=file_content)

    cert_type = parsed["cert_type"]
    date_val = parse_date(parsed["date_str"])

    try:
        # 获取或创建厂家
        m = Manufacturer.query.filter_by(name=parsed["manufacturer_name"]).first()
        manufacturer_created = False
        if not m:
            m = Manufacturer(name=parsed["manufacturer_name"])
            db.session.add(m)
            db.session.flush()
            manufacturer_created = True

        if cert_type == "business_license":
            rel, original = save_upload(file_storage, "LICENSE_SUBDIR")
            if not rel:
                db.session.rollback()
                return _err(original_filename, "文件保存失败（类型不支持）", file_content=file_content)
            if m.business_license:
                m.business_license.file_path = rel
                m.business_license.file_name = original
                m.business_license.valid_until = date_val
            else:
                m.business_license = BusinessLicense(
                    file_path=rel, file_name=original, valid_until=date_val,
                )
            db.session.commit()
            return _ok(original_filename, "营业执照", m, None, manufacturer_created)

        if cert_type == "food_license":
            rel, original = save_upload(file_storage, "LICENSE_SUBDIR")
            if not rel:
                db.session.rollback()
                return _err(original_filename, "文件保存失败（类型不支持）", file_content=file_content)
            if m.food_license:
                m.food_license.file_path = rel
                m.food_license.file_name = original
                m.food_license.valid_until = date_val
            else:
                m.food_license = FoodLicense(
                    file_path=rel, file_name=original, valid_until=date_val,
                )
            db.session.commit()
            return _ok(original_filename, "食品经营许可证", m, None, manufacturer_created)

        # 单品级证件：获取或创建商品
        spec = parsed["spec"]
        category = parsed["category"]
        p = Product.query.filter_by(
            manufacturer_id=m.id, name=parsed["product_name"], spec=spec or None,
        ).first()
        product_created = False
        if not p:
            p = Product(
                manufacturer_id=m.id,
                name=parsed["product_name"],
                spec=spec or None,
                category=category or None,
            )
            db.session.add(p)
            db.session.flush()
            product_created = True

        if cert_type == "third_party":
            rel, original = save_upload(file_storage, "THIRD_PARTY_SUBDIR")
            if not rel:
                db.session.rollback()
                return _err(original_filename, "文件保存失败（类型不支持）", file_content=file_content)
            valid_until = date_val or (date.today() + timedelta(days=365))
            r = ThirdPartyReport(
                product_id=p.id,
                manufacturer_id=m.id,
                test_date=date_val,
                valid_until=valid_until,
                file_path=rel,
                file_name=original,
            )
            db.session.add(r)
            db.session.commit()
            return _ok(original_filename, "第三方检验报告", m, p, manufacturer_created, product_created)

        if cert_type == "factory":
            rel, original = save_upload(file_storage, "FACTORY_SUBDIR")
            if not rel:
                db.session.rollback()
                return _err(original_filename, "文件保存失败（类型不支持）", file_content=file_content)
            # 厂检不再有保质期/到期日概念，仅记录生产与检验日期
            production_date = date_val or date.today()
            test_date = production_date  # 检验日期默认同生产日期
            r = FactoryReport(
                product_id=p.id,
                manufacturer_id=m.id,
                production_date=production_date,
                test_date=test_date,
                valid_until=production_date,  # 兼容列，reminder 已跳过厂检
                file_path=rel,
                file_name=original,
            )
            db.session.add(r)
            db.session.commit()
            return _ok(original_filename, "出厂检验报告", m, p, manufacturer_created, product_created)

        db.session.rollback()
        return _err(original_filename, "未知证件类型", file_content=file_content)
    except Exception as e:
        db.session.rollback()
        return _err(original_filename, f"处理异常：{e}", file_content=file_content)


def _ok(filename, cert_type, manufacturer, product, manufacturer_created=False, product_created=False):
    msg = f"已上传{cert_type}"
    extras = []
    if manufacturer_created:
        extras.append("自动创建厂家")
    if product_created:
        extras.append("自动创建商品")
    if extras:
        msg += "（" + "、".join(extras) + "）"
    return {
        "filename": filename,
        "status": "success",
        "message": msg,
        "cert_type": cert_type,
        "manufacturer": manufacturer.name,
        "product": product.name if product else None,
    }


def _err(filename, message, file_content=None):
    result = {"filename": filename, "status": "error", "message": message}
    if file_content is not None:
        result["file_content"] = file_content
    return result


def process_zip(file_storage):
    """解压 ZIP 并逐个处理文件。返回结果列表。"""
    results = []
    data = file_storage.read()
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        return [_err(file_storage.filename, "不是有效的 ZIP 压缩包")]

    allowed = current_app.config["ALLOWED_EXTENSIONS"]
    for info in zf.infolist():
        if info.is_dir():
            continue
        # 跳过 macOS 元数据与隐藏文件
        if "__MACOSX" in info.filename or os.path.basename(info.filename).startswith("."):
            continue
        filename = os.path.basename(info.filename)
        if not filename:
            continue
        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        if ext not in allowed:
            results.append({
                "filename": filename,
                "status": "skipped",
                "message": f"不支持的文件类型 .{ext}",
            })
            continue
        try:
            file_data = zf.read(info)
            fs = FileStorage(stream=io.BytesIO(file_data), filename=filename)
            results.append(process_single_file(fs, filename))
        except Exception as e:
            results.append(_err(filename, f"读取失败：{e}"))
    zf.close()
    return results


def process_files(file_list):
    """处理多个上传文件（非 zip）。"""
    results = []
    for f in file_list:
        if not f or not f.filename:
            continue
        results.append(process_single_file(f, f.filename))
    return results
