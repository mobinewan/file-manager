"""到期状态计算 + 看板聚合。"""
from datetime import date
from ..extensions import db
from ..models import (
    BusinessLicense, FoodLicense, ThirdPartyReport,
    Manufacturer, Setting,
)


def _threshold_days():
    s = Setting.query.first()
    return (s.default_threshold_days if s else 30) or 30


def summarize_expiry():
    """首页徽章汇总：返回 {expired, expiring_soon, total}"""
    threshold = _threshold_days()
    today = date.today()
    expired = 0
    expiring = 0
    items = collect_all_expiring(threshold, today)
    for it in items:
        if it["status"] == "expired":
            expired += 1
        elif it["status"] == "expiring_soon":
            expiring += 1
    return {
        "expired": expired,
        "expiring_soon": expiring,
        "total": len(items),
    }


def collect_all_expiring(threshold, today):
    """返回所有需关注的证件列表（仅 expired 与 expiring_soon）。"""
    items = []
    # 营业执照
    for bl in BusinessLicense.query.all():
        if bl.valid_until is None:
            continue
        days = (bl.valid_until - today).days
        if days < 0 or days <= threshold:
            items.append(_make_item(
                "营业执照", bl, bl.valid_until, days, threshold,
                owner=bl.manufacturer.name if bl.manufacturer else "",
                owner_url=("manufacturer.detail", {"manufacturer_id": bl.manufacturer_id}) if bl.manufacturer else None,
            ))
    # 食品经营许可证
    for fl in FoodLicense.query.all():
        if fl.valid_until is None:
            continue
        days = (fl.valid_until - today).days
        if days < 0 or days <= threshold:
            items.append(_make_item(
                "食品经营许可证", fl, fl.valid_until, days, threshold,
                owner=fl.manufacturer.name if fl.manufacturer else "",
                owner_url=("manufacturer.detail", {"manufacturer_id": fl.manufacturer_id}) if fl.manufacturer else None,
            ))
    # 第三方检验报告
    for tp in ThirdPartyReport.query.all():
        days = (tp.valid_until - today).days if tp.valid_until else None
        if days is None:
            continue
        if days < 0 or days <= threshold:
            owner_name = ""
            owner_url = None
            if tp.product:
                owner_name = f"{tp.manufacturer.name} / {tp.product.name}"
                owner_url = ("product.detail", {"product_id": tp.product_id})
            items.append(_make_item(
                "第三方检验报告", tp, tp.valid_until, days, threshold,
                owner=owner_name, owner_url=owner_url,
            ))
    # 出厂检验报告不再纳入到期预警（已取消保质期/到期日概念）
    return items


def _make_item(cert_type, obj, valid_until, days, threshold, owner="", owner_url=None):
    if days is None:
        status_val = "long_term"
    elif days < 0:
        status_val = "expired"
    elif days <= threshold:
        status_val = "expiring_soon"
    else:
        status_val = "normal"
    return {
        "cert_type": cert_type,
        "valid_until": valid_until,
        "days_remaining": days,
        "status": status_val,
        "owner": owner,
        "owner_url": owner_url,
        "cert_id": obj.id,
    }


def list_all_grouped():
    """按状态分组返回三档：已过期 / 即将到期 / 正常。"""
    threshold = _threshold_days()
    today = date.today()
    all_items = collect_all_expiring(threshold, today)
    # 同时也要列出正常档？仅展示需要关注的更合理
    expired = [it for it in all_items if it["status"] == "expired"]
    expiring = [it for it in all_items if it["status"] == "expiring_soon"]
    # 排序：剩余天数升序
    expired.sort(key=lambda x: x["days_remaining"])
    expiring.sort(key=lambda x: x["days_remaining"])
    return {
        "expired": expired,
        "expiring_soon": expiring,
        "threshold": threshold,
    }
