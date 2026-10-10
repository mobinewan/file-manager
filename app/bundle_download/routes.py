"""打包下载：按商品名 + 生产日期搜索 → 勾选 → 打包 ZIP。

ZIP 结构示例：
  海天酱油-酿造有限公司/        ← 厂家名
    营业执照_xxx.pdf
    食品经营许可证_xxx.pdf
    海天酱油-生抽500ml/           ← 商品名-规格
      第三方检验报告_xxx.pdf
      出厂检验报告_批次A_2026-09-21.pdf
      出厂检验报告_批次B_2026-10-01.pdf
"""
import io
import os
import zipfile
from datetime import date
from flask import Blueprint, render_template, request, abort, send_file, current_app
from flask_login import login_required

from ..extensions import db
from ..models import (
    Product, Manufacturer,
    BusinessLicense, FoodLicense, ThirdPartyReport, FactoryReport,
)
from ..utils.date_utils import parse_date

bundle_bp = Blueprint("bundle", __name__, url_prefix="/bundle")


def _safe_name(s):
    """清理文件名中的非法字符。"""
    if not s:
        return "unnamed"
    bad = '<>:"/\\|?*\n\r\t'
    for c in bad:
        s = s.replace(c, "_")
    return s.strip().strip(".") or "unnamed"


def _pick_factory_reports(product_id, production_date):
    """按生产日期（可选）过滤厂检报告；若给了日期则精确匹配，否则返回全部。"""
    q = FactoryReport.query.filter_by(product_id=product_id)
    if production_date:
        q = q.filter(FactoryReport.production_date == production_date)
    return q.order_by(FactoryReport.production_date.desc(), FactoryReport.id.desc()).all()


def _pick_third_party_reports(product_id):
    """返回某商品的全部第三方检验报告（按检验日期降序）。"""
    return (
        ThirdPartyReport.query.filter_by(product_id=product_id)
        .order_by(ThirdPartyReport.test_date.desc())
        .all()
    )


@bundle_bp.route("/", methods=["GET"])
@login_required
def index():
    """打包下载搜索页：按商品名模糊 + 生产日期过滤厂检。"""
    q = request.args.get("q", "").strip()
    production_date_str = request.args.get("production_date", "").strip()
    production_date = parse_date(production_date_str)

    products = []
    if q:
        like = f"%{q}%"
        products = (
            Product.query.filter(Product.name.like(like))
            .order_by(Product.name)
            .all()
        )
    # 为每个商品附带：关联厂家信息、匹配的厂检报告、全部第三方报告
    for p in products:
        p._matched_fc = _pick_factory_reports(p.id, production_date)
        p._all_tp = _pick_third_party_reports(p.id)

    return render_template(
        "bundle/index.html",
        q=q,
        production_date=production_date_str,
        products=products,
    )


@bundle_bp.route("/download", methods=["POST"])
@login_required
def download():
    """打包下载：接收 checkbox 列表 items=<product_id>-<factory_report_id 或 'all_tp'>。"""
    items = request.form.getlist("items")  # ["5-3", "5-all_tp", "7-all_tp", "7-8"]

    # 解析选中项：按 product_id 分组
    groups = {}  # product_id -> {"fc_ids": set, "tp_all": bool}
    for item in items:
        if "-" not in item:
            continue
        try:
            pid, rid = item.split("-", 1)
            pid = int(pid)
        except ValueError:
            continue
        groups.setdefault(pid, {"fc_ids": set(), "tp_all": False})
        if rid == "all_tp":
            groups[pid]["tp_all"] = True
        else:
            try:
                groups[pid]["fc_ids"].add(int(rid))
            except ValueError:
                continue

    if not groups:
        abort(400, description="未选择任何条目")

    # 收集实际要打包的文件
    upload_root = current_app.config["UPLOAD_FOLDER"]
    file_entries = []  # (zip_path, abs_path, original_name)

    for pid, sel in groups.items():
        product = db.session.get(Product, pid)
        if not product:
            continue
        m = product.manufacturer
        m_label = _safe_name(m.name if m else "unknown_mfr")
        p_label = _safe_name(product.name + (f"-{product.spec}" if product.spec else ""))
        product_dir = f"{m_label}/{p_label}"

        # 厂家级证件：每个唯一厂家的 BL/FL 只打一份，放到厂家根目录
        if m:
            if m.business_license:
                file_entries.append((
                    f"{m_label}/营业执照_{_safe_name(m.business_license.license_no or '无编号')}.pdf",
                    os.path.join(upload_root, m.business_license.file_path),
                ))
            if m.food_license:
                file_entries.append((
                    f"{m_label}/食品经营许可证_{_safe_name(m.food_license.license_no or '无编号')}.pdf",
                    os.path.join(upload_root, m.food_license.file_path),
                ))

        # 第三方报告
        if sel["tp_all"]:
            tps = (
                ThirdPartyReport.query.filter_by(product_id=pid)
                .order_by(ThirdPartyReport.test_date.desc())
                .all()
            )
            for tp in tps:
                label = _safe_name(tp.report_no or tp.testing_org or "第三方检验报告")
                ext = os.path.splitext(tp.file_name)[1] or ".pdf"
                file_entries.append((
                    f"{product_dir}/第三方检验报告_{label}{ext}",
                    os.path.join(upload_root, tp.file_path),
                ))

        # 选中的厂检
        for fc_id in sel["fc_ids"]:
            fc = db.session.get(FactoryReport, fc_id)
            if not fc or fc.product_id != pid:
                continue
            label_parts = ["出厂检验报告"]
            if fc.batch_no:
                label_parts.append(_safe_name(fc.batch_no))
            if fc.production_date:
                label_parts.append(str(fc.production_date))
            label = "_".join(label_parts)
            ext = os.path.splitext(fc.file_name)[1] or ".pdf"
            file_entries.append((
                f"{product_dir}/{label}{ext}",
                os.path.join(upload_root, fc.file_path),
            ))

    # 生成 ZIP
    buf = io.BytesIO()
    used_names = set()

    def dedupe(zip_path):
        if zip_path not in used_names:
            used_names.add(zip_path)
            return zip_path
        base, ext = os.path.splitext(zip_path)
        i = 2
        while True:
            cand = f"{base} ({i}){ext}"
            if cand not in used_names:
                used_names.add(cand)
                return cand
            i += 1

    # 过滤掉不存在的文件
    valid_entries = [(zp, ap) for zp, ap in file_entries if os.path.exists(ap)]
    if not valid_entries:
        abort(400, description="所选证件文件均不存在，无法打包")

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for zip_path, abs_path in valid_entries:
            zf.write(abs_path, dedupe(zip_path))

    buf.seek(0)
    stamp = date.today().isoformat()
    filename = f"证件_打包下载_{stamp}.zip"
    return send_file(
        buf,
        mimetype="application/zip",
        as_attachment=True,
        download_name=filename,
    )
