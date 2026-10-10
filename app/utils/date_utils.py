"""日期与有效期状态分类工具。"""
from datetime import date, datetime, timedelta


def parse_date(value):
    """字符串/日期统一转 date。"""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                continue
    return None


def days_remaining(valid_until, today=None):
    """剩余天数。None 视为长期有效返回 None。"""
    if valid_until is None:
        return None
    today = today or date.today()
    return (valid_until - today).days


def status_of(valid_until, threshold_days, today=None):
    """返回状态字符串：long_term / normal / expiring_soon / expired。"""
    if valid_until is None:
        return "long_term"
    days = days_remaining(valid_until, today)
    if days < 0:
        return "expired"
    if days <= threshold_days:
        return "expiring_soon"
    return "normal"


STATUS_LABELS = {
    "long_term": "长期有效",
    "normal": "正常",
    "expiring_soon": "即将到期",
    "expired": "已过期",
    "missing": "缺失",
}

STATUS_BADGES = {
    "long_term": "bg-secondary",
    "normal": "bg-success",
    "expiring_soon": "bg-warning text-dark",
    "expired": "bg-danger",
    "missing": "bg-dark",
}


def status_badge(status):
    return STATUS_BADGES.get(status, "bg-secondary")


def status_label(status):
    return STATUS_LABELS.get(status, status)
