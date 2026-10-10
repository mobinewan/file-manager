"""搜索页面 + JSON API 路由。"""
from flask import Blueprint, render_template, request, jsonify, url_for
from flask_login import login_required

from .services import (
    search_manufacturers_by_query,
    products_for_manufacturer_by_query,
    product_certificate_summary,
    search_suggestions,
    _threshold_days,
)
from ..utils.date_utils import status_of, status_label, status_badge

search_bp = Blueprint("search", __name__, url_prefix="/search")


@search_bp.route("/")
@login_required
def search():
    q = request.args.get("q", "").strip()
    manufacturers = search_manufacturers_by_query(q) if q else []
    threshold = _threshold_days()
    # 为每个厂家预聚合其符合 q 的商品列表（厂家名匹配时返回该厂家全部商品）
    result = []
    for m in manufacturers:
        products = products_for_manufacturer_by_query(m.id, q)
        for p in products:
            p._cert_summary = product_certificate_summary(p, threshold)
        result.append({"manufacturer": m, "products": products})
    return render_template(
        "search/result.html",
        q=q,
        result=result,
        threshold=threshold,
        status_of=status_of,
        status_label=status_label,
        status_badge=status_badge,
    )


@search_bp.route("/api", methods=["GET"])
@login_required
def api_search():
    q = request.args.get("q", "").strip()
    return jsonify(search_suggestions(q))
