"""Tax invoice PDF for an order (download from Order History or admin)."""
from io import BytesIO

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .models import SiteSettings

WINE = colors.HexColor('#a10000')
PINK = colors.HexColor('#fce7f3')
# Built-in PDF fonts have no ₹ sign, so amounts use "Rs."
rs = lambda v: f'Rs. {v:,.2f}'.replace('.00', '')
PAY = {'cod': 'Cash on Delivery', 'cashfree': 'Paid online (Cashfree)'}


def number(order):
    return f'AR-{timezone.localtime(order.created_at):%Y%m}-{str(order.id)[:8].upper()}'


def render(order):
    s = SiteSettings.current()
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
                            title=f'Invoice {number(order)}', author=s.name)
    st = getSampleStyleSheet()
    body = ParagraphStyle('b', parent=st['Normal'], fontSize=9.5, leading=13)
    small = ParagraphStyle('s', parent=body, fontSize=8.5, textColor=colors.HexColor('#6b7280'))
    head = ParagraphStyle('h', parent=body, fontName='Helvetica-Bold', fontSize=10.5)
    brand = ParagraphStyle('br', parent=body, fontName='Helvetica-Bold', fontSize=20, textColor=WINE, leading=24)
    a = order.address or {}
    seller = f'<b>{s.name}</b><br/>{s.address.replace(chr(10), "<br/>")}<br/>{s.phone} · {s.email}' + (f'<br/>GSTIN: {s.gstin}' if s.gstin else '')
    buyer = (f'<b>{a.get("name", "")}</b><br/>{a.get("line1", "")}{", " + a["line2"] if a.get("line2") else ""}<br/>'
             f'{a.get("city", "")}, {a.get("state", "")} {a.get("pincode", "")}<br/>{a.get("phone", "")} · {a.get("email", "")}')
    meta = (f'<b>Invoice no:</b> {number(order)}<br/><b>Order:</b> #{str(order.id)[:8].upper()}<br/>'
            f'<b>Date:</b> {timezone.localtime(order.created_at):%d %b %Y}<br/><b>Payment:</b> {PAY.get(order.payment_method, order.payment_method)}'
            + (f'<br/><b>Waybill (AWB):</b> {order.awb}' if order.awb else ''))
    parts = [
        Table([[Paragraph('Aiman Royale', brand), Paragraph('<b>TAX INVOICE</b>', ParagraphStyle('t', parent=head, alignment=2, fontSize=13, textColor=WINE))]],
              colWidths=[110 * mm, 68 * mm]),
        Spacer(1, 6),
        Table([[Paragraph('Sold by', head), Paragraph('Bill / Ship to', head), Paragraph('Details', head)],
               [Paragraph(seller, body), Paragraph(buyer, body), Paragraph(meta, body)]], colWidths=[62 * mm, 62 * mm, 54 * mm],
              style=[('VALIGN', (0, 0), (-1, -1), 'TOP'), ('BACKGROUND', (0, 0), (-1, 0), PINK), ('BOX', (0, 0), (-1, -1), .5, colors.HexColor('#f3c6d8')),
                     ('INNERGRID', (0, 0), (-1, -1), .3, colors.HexColor('#f3c6d8')), ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 6)]),
        Spacer(1, 10),
    ]
    rows = [['#', 'Item', 'Size / Colour', 'Qty', 'Unit price', 'Amount']]
    for n, i in enumerate(order.items.select_related('variant'), 1):
        rows.append([str(n), Paragraph(i.name, body), f'{i.variant.size} / {i.variant.colour}', str(i.quantity), rs(i.unit_price), rs(i.unit_price * i.quantity)])
    lines = [('Subtotal', order.subtotal)]
    if order.discount:
        lines.append(('Discount', -order.discount))
    lines.append(('Shipping', order.shipping))
    for label, v in lines:
        rows.append(['', '', '', '', label, rs(v) if v >= 0 else '- ' + rs(-v)])
    rows.append(['', '', '', '', 'Total', rs(order.total)])
    t = Table(rows, colWidths=[8 * mm, 72 * mm, 32 * mm, 12 * mm, 26 * mm, 28 * mm], repeatRows=1)
    last = len(rows) - 1
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), WINE), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
        ('LINEBELOW', (0, 0), (-1, last - len(lines) - 1), .3, colors.HexColor('#e5e7eb')),
        ('LINEABOVE', (4, last), (-1, last), .8, WINE), ('FONTNAME', (4, last), (-1, last), 'Helvetica-Bold'), ('FONTSIZE', (4, last), (-1, last), 10.5),
        ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    parts += [t, Spacer(1, 14),
              Paragraph('All prices are inclusive of applicable taxes.', small),
              Paragraph(f'Order status: {order.status.replace("_", " ").title()}' + (' · Cancelled on ' + f'{timezone.localtime(order.cancelled_at):%d %b %Y}' if order.cancelled_at else ''), small),
              Spacer(1, 18), Paragraph(f'Thank you for shopping with {s.name}.', body),
              Paragraph('This is a computer-generated invoice and does not require a signature.', small)]
    doc.build(parts)
    return buf.getvalue()
