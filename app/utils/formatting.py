"""Small display helpers."""
from config import settings as S


def pct(x, digits=0):
    return f"{x * 100:.{digits}f}%"


def pkr(x):
    return f"PKR {x:,.0f}"


def units(x):
    return f"{x:,.0f} kWh"


def badge(text, kind):
    """Coloured pill as HTML. kind: a key of RISK_COLORS or THEFT_COLORS."""
    color = {**S.RISK_COLORS, **S.THEFT_COLORS}.get(kind, "#4a6fa5")
    return (f"<span style='background:{color};color:white;padding:2px 10px;border-radius:999px;"
            f"font-size:0.8rem;font-weight:600'>{text}</span>")
