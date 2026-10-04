"""Template helpers for the FragranSoul storefront."""

from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def rupees(value):
    """Format an amount as Indian Rupees, e.g. 125000 -> ₹1,25,000."""
    if value is None or value == "":
        return ""

    amount = Decimal(value).quantize(Decimal("0.01"))
    whole, _, paise = f"{abs(amount):.2f}".partition(".")

    # Indian grouping: the last three digits, then groups of two.
    head, tail = whole[:-3], whole[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    text = ",".join(groups + [tail])

    if paise != "00":
        text = f"{text}.{paise}"
    sign = "-" if amount < 0 else ""
    return f"{sign}₹{text}"
