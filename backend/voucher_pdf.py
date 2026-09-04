import io
from datetime import datetime
import qrcode
from reportlab.lib.pagesizes import A5, landscape
from reportlab.lib.colors import HexColor, white
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

ABYSS, PANEL, GLOW, GOLD, MUTED = HexColor("#050B14"), HexColor("#0F1C30"), HexColor("#00F0FF"), HexColor("#D4AF37"), HexColor("#94A3B8")

EXP = {
    "fr": {"discovery": "Discovery Session", "duo": "Duo VIP Experience"},
    "en": {"discovery": "Discovery Session", "duo": "Duo VIP Experience"},
    "es": {"discovery": "Discovery Session", "duo": "Duo VIP Experience"},
}
T = {
    "fr": {"gift": "BON CADEAU", "for": "Pour", "from": "De la part de", "exp": "Expérience", "value": "Valeur", "valid": "Valable jusqu'au",
           "how": "Pour réserver : saisissez ce code dans le formulaire de réservation sur le site.", "people": "pers.", "scan": "Scanner pour réserver"},
    "en": {"gift": "GIFT VOUCHER", "for": "For", "from": "From", "exp": "Experience", "value": "Value", "valid": "Valid until",
           "how": "To book: enter this code in the booking form on our website.", "people": "people", "scan": "Scan to book"},
    "es": {"gift": "BONO REGALO", "for": "Para", "from": "De parte de", "exp": "Experiencia", "value": "Valor", "valid": "Válido hasta",
           "how": "Para reservar: introduce este código en el formulario de reserva de la web.", "people": "pers.", "scan": "Escanea para reservar"},
}


def _wrap(text: str, width: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines[:3]


def build_voucher_pdf(v: dict, site_url: str) -> bytes:
    lang = v.get("lang") if v.get("lang") in T else "fr"
    s = T[lang]
    buf = io.BytesIO()
    W, H = landscape(A5)
    c = canvas.Canvas(buf, pagesize=(W, H))
    c.setTitle(f"Canary Foil Club — {s['gift']} {v['code']}")

    c.setFillColor(ABYSS)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(PANEL)
    c.roundRect(18, 18, W - 36, H - 36, 16, fill=1, stroke=0)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.2)
    c.roundRect(26, 26, W - 52, H - 52, 12, fill=0, stroke=1)
    c.setStrokeColor(GLOW)
    c.setLineWidth(2)
    c.line(44, H - 60, 120, H - 60)

    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(44, H - 48, f"C A N A R Y   F O I L   C L U B   ·   {s['gift']}")

    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 26)
    c.drawString(44, H - 98, EXP[lang].get(v["experience"], v["experience"]))
    c.setFillColor(MUTED)
    c.setFont("Helvetica-Oblique", 11)
    c.drawString(44, H - 116, f"eFoil · Costa Adeje, Tenerife · {v['participants']} {s['people']}")

    y = H - 152
    for label, value in [(s["for"], v["recipient_name"]), (s["from"], v["buyer_name"]),
                         (s["valid"], datetime.fromisoformat(v["expires_at"]).strftime("%d/%m/%Y") if v.get("expires_at") else "—")]:
        c.setFillColor(GLOW)
        c.setFont("Helvetica", 7.5)
        c.drawString(44, y, label.upper())
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(44, y - 16, value)
        y -= 40

    if v.get("message"):
        c.setFillColor(MUTED)
        c.setFont("Helvetica-Oblique", 10.5)
        for i, line in enumerate(_wrap(f"« {v['message']} »", 52)):
            c.drawString(44, y - 2 - i * 14, line)

    bx, by, bw, bh = W - 262, 96, 218, H - 176
    c.setFillColor(ABYSS)
    c.roundRect(bx, by, bw, bh, 12, fill=1, stroke=0)
    c.setStrokeColor(GOLD)
    c.setDash(4, 3)
    c.setLineWidth(1)
    c.roundRect(bx, by, bw, bh, 12, fill=0, stroke=1)
    c.setDash()

    c.setFillColor(GOLD)
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(bx + bw / 2, by + bh - 22, s["value"].upper())
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 34)
    c.drawCentredString(bx + bw / 2, by + bh - 56, f"{v['value']:.0f} €")

    c.setFillColor(GLOW)
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(bx + bw / 2, by + bh - 82, "CODE")
    c.setFillColor(white)
    c.setFont("Courier-Bold", 19)
    c.drawCentredString(bx + bw / 2, by + bh - 104, v["code"])

    qr = qrcode.QRCode(box_size=4, border=1)
    qr.add_data(f"{site_url.rstrip('/')}/?code={v['code']}")
    qr.make(fit=True)
    img = qr.make_image(fill_color="#050B14", back_color="white")
    qb = io.BytesIO()
    img.save(qb, format="PNG")
    qb.seek(0)
    qsize = 78
    c.drawImage(ImageReader(qb), bx + (bw - qsize) / 2, by + 26, qsize, qsize)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 7)
    c.drawCentredString(bx + bw / 2, by + 14, s["scan"])

    c.setFillColor(MUTED)
    c.setFont("Helvetica", 8)
    c.drawString(44, 52, s["how"])
    c.setFont("Helvetica", 7)
    c.drawString(44, 40, f"{site_url.replace('https://', '')}  ·  WhatsApp +34 600 000 000  ·  Canary Foil Club, Costa Adeje")

    c.showPage()
    c.save()
    return buf.getvalue()
