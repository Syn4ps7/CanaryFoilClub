import os
import re
import ipaddress
import logging
import httpx
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / '.env')
logger = logging.getLogger(__name__)

EMAIL_BASE_URL = "https://integrations.emergentagent.com"
EMAIL_KEY = os.environ["EMERGENT_EMAIL_KEY"]
EMAIL_FROM_NAME = os.environ["EMAIL_FROM_NAME"]
OWNER_EMAIL = os.environ.get("OWNER_EMAIL")

_SHORTENERS = ("bit.ly", "tinyurl.com", "t.co", "is.gd", "cutt.ly", "goo.gl", "rebrand.ly")
_CRED_ASK = ("reply with your password", "reply with the code", "send your password", "cvv",
             "send us your password", "enter your password below", "confirm your card number",
             "your full card number", "seed phrase", "recovery phrase", "verify your card",
             "social security number", "confirm your bank details")
_HOSTISH = re.compile(r"\b(?:https?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})", re.I)


def _host_ok(host: str) -> bool:
    if not host or "xn--" in host:
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        pass
    return not any(host == s or host.endswith("." + s) for s in _SHORTENERS)


def _same_site(shown: str, real: str) -> bool:
    return shown == real or real.endswith("." + shown) or shown.endswith("." + real)


class _EmailScan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.urls, self.anchors = set(), [], []
        self._href, self._text = None, []

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag.lower())
        self.urls += [v for k, v in attrs if k.lower() in ("href", "src") and v]
        if tag.lower() == "a":
            self._href = dict((k.lower(), v) for k, v in attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((self._href, "".join(self._text)))
            self._href, self._text = None, []


def _assert_safe_email(subject: str, html: str) -> None:
    scan = _EmailScan()
    scan.feed(html)
    if scan.tags & {"form", "input", "textarea", "select"}:
        raise ValueError("No forms or input fields in email (G2)")
    body = f"{subject}\n{html}".lower()
    for p in _CRED_ASK:
        if p in body:
            raise ValueError(f"Email asks the recipient for credentials: {p!r} (G2)")
    for url in scan.urls:
        low = url.strip().lower()
        if low.startswith(("mailto:", "tel:", "cid:", "#")):
            continue
        if not low.startswith("https://"):
            raise ValueError(f"Email links/assets must be absolute https: {url!r} (G3)")
        host = urlparse(low).hostname or ""
        if not _host_ok(host) or urlparse(low).username is not None:
            raise ValueError(f"Shortened, numeric-host or credential-bearing URL: {url!r} (G3)")
    for href, text in scan.anchors:
        real = urlparse(href.strip().lower()).hostname or ""
        if not real:
            continue
        for m in _HOSTISH.finditer(text):
            if not _same_site(m.group(1).lower(), real):
                raise ValueError(f"Anchor text {m.group(1)!r} != real link host {real!r} (G3)")


async def send_email(*, to: str, subject: str, html: str, reply_to: str | None = None) -> str | None:
    _assert_safe_email(subject, html)
    payload = {"to": [to], "subject": subject, "html": html, "from_name": EMAIL_FROM_NAME}
    if reply_to:
        payload["contact_email"] = reply_to
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{EMAIL_BASE_URL}/api/v1/email/send",
            headers={"X-Email-Key": EMAIL_KEY},
            json=payload,
        )
    resp.raise_for_status()
    return resp.json().get("id")


EXPERIENCE_LABELS = {
    "discovery": "Discovery Session — 145 €",
    "duo": "Duo VIP Experience — 280 €",
    "drone": "Option Drone 4K — +50 €",
    "corporate": "Corporate Sunset (B2B) — 890 €",
    "testdrive": "Test Drive Fliteboard / Achat",
}


def _row(label: str, value: str) -> str:
    return (f'<tr><td style="padding:10px 0;border-bottom:1px solid #1e2f4a;font-family:Arial,sans-serif;'
            f'font-size:12px;letter-spacing:2px;text-transform:uppercase;color:#00c2cb;width:140px;'
            f'vertical-align:top">{escape(label)}</td>'
            f'<td style="padding:10px 0;border-bottom:1px solid #1e2f4a;font-family:Arial,sans-serif;'
            f'font-size:14px;color:#f8fafc">{value}</td></tr>')


def build_booking_email(b) -> tuple[str, str]:
    exp = EXPERIENCE_LABELS.get(b.experience, b.experience)
    subject = f"Nouvelle demande de réservation — {exp}"
    rows = "".join([
        _row("Expérience", escape(exp)),
        _row("Nom", escape(b.name)),
        _row("Email", f'<a href="mailto:{escape(b.email)}" style="color:#00f0ff">{escape(b.email)}</a>'),
        _row("Téléphone", f'<a href="tel:{escape(b.phone)}" style="color:#00f0ff">{escape(b.phone)}</a>'),
        _row("Date", escape(b.date)),
        _row("Participants", str(b.participants)),
        _row("Hôtel", escape(b.hotel or "—")),
        _row("Notes", escape(b.notes or "—")),
    ])
    html = (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'style="background:#050b14;padding:32px 16px"><tr><td align="center">'
        '<table role="presentation" width="560" cellpadding="0" cellspacing="0" '
        'style="background:#0f1c30;border:1px solid #1e2f4a;border-radius:16px;padding:32px">'
        '<tr><td>'
        '<p style="font-family:Arial,sans-serif;font-size:11px;letter-spacing:4px;color:#00f0ff;'
        'text-transform:uppercase;margin:0 0 8px">Canary Foil Club</p>'
        '<h1 style="font-family:Arial,sans-serif;font-size:22px;color:#f8fafc;margin:0 0 4px">'
        'Nouvelle demande de réservation</h1>'
        '<p style="font-family:Arial,sans-serif;font-size:13px;color:#94a3b8;margin:0 0 24px">'
        'Réponse VIP attendue sous 24h.</p>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rows}</table>'
        '<p style="font-family:Arial,sans-serif;font-size:11px;color:#64748b;margin:24px 0 0">'
        'Envoyé automatiquement par le site Canary Foil Club — Costa Adeje, Ténérife.</p>'
        '</td></tr></table></td></tr></table>'
    )
    return subject, html


async def notify_owner(booking) -> bool:
    if not OWNER_EMAIL:
        logger.warning("OWNER_EMAIL not set; skipping booking notification")
        return False
    try:
        subject, html = build_booking_email(booking)
        email_id = await send_email(to=OWNER_EMAIL, subject=subject, html=html, reply_to=booking.email)
        logger.info(f"Booking notification sent (id={email_id}) for booking {booking.id}")
        return True
    except Exception as e:
        logger.error(f"Booking notification failed for {booking.id}: {e}")
        return False


CLIENT_CONFIRM = {
    "fr": {
        "subject": "Votre demande de vol a bien été reçue",
        "title": "Merci {name}, à très vite sur l'eau.",
        "intro": "Votre demande est entre les mains de notre équipe VIP. Nous revenons vers vous sous 24h pour confirmer votre créneau et choisir le meilleur plan d'eau du jour à Costa Adeje.",
        "recap": "Votre demande",
        "lbl_experience": "Expérience",
        "lbl_date": "Date souhaitée",
        "lbl_participants": "Participants",
        "note": "Aucun paiement n'a été effectué. Le règlement sécurisé interviendra uniquement après confirmation de votre créneau.",
        "question": 'Une question ? Notre ligne WhatsApp VIP : <a href="tel:+34600000000" style="color:#00f0ff">+34 600 000 000</a>',
        "footer": "Canary Foil Club — Costa Adeje, Ténérife. Cet email confirme la réception de votre demande.",
    },
    "en": {
        "subject": "Your flight request has been received",
        "title": "Thank you {name}, see you on the water.",
        "intro": "Your request is with our VIP team. We'll get back to you within 24 hours to confirm your time slot and pick the day's calmest spot in Costa Adeje.",
        "recap": "Your request",
        "lbl_experience": "Experience",
        "lbl_date": "Preferred date",
        "lbl_participants": "Participants",
        "note": "No payment has been taken. Secure payment only happens once your slot is confirmed.",
        "question": 'Questions? Our VIP WhatsApp line: <a href="tel:+34600000000" style="color:#00f0ff">+34 600 000 000</a>',
        "footer": "Canary Foil Club — Costa Adeje, Tenerife. This email confirms receipt of your request.",
    },
    "es": {
        "subject": "Hemos recibido tu solicitud de vuelo",
        "title": "Gracias {name}, nos vemos en el agua.",
        "intro": "Tu solicitud está en manos de nuestro equipo VIP. Te contactaremos en 24h para confirmar tu horario y elegir el mejor spot del día en Costa Adeje.",
        "recap": "Tu solicitud",
        "lbl_experience": "Experiencia",
        "lbl_date": "Fecha deseada",
        "lbl_participants": "Participantes",
        "note": "No se ha realizado ningún pago. El pago seguro se efectuará solo tras confirmar tu horario.",
        "question": '¿Dudas? Nuestra línea VIP de WhatsApp: <a href="tel:+34600000000" style="color:#00f0ff">+34 600 000 000</a>',
        "footer": "Canary Foil Club — Costa Adeje, Tenerife. Este email confirma la recepción de tu solicitud.",
    },
}

CLIENT_EXP_LABELS = {
    "fr": EXPERIENCE_LABELS,
    "en": {
        "discovery": "Discovery Session — €145",
        "duo": "Duo VIP Experience — €280",
        "drone": "4K Drone Option — +€50",
        "corporate": "Corporate Sunset (B2B) — €890",
        "testdrive": "Fliteboard Test Drive / Purchase",
    },
    "es": {
        "discovery": "Sesión Discovery — 145 €",
        "duo": "Experiencia Duo VIP — 280 €",
        "drone": "Opción Dron 4K — +50 €",
        "corporate": "Corporate Sunset (B2B) — 890 €",
        "testdrive": "Test Drive Fliteboard / Compra",
    },
}


def build_client_confirmation_email(b) -> tuple[str, str]:
    lang = b.lang if getattr(b, "lang", None) in CLIENT_CONFIRM else "fr"
    s = CLIENT_CONFIRM[lang]
    exp = CLIENT_EXP_LABELS[lang].get(b.experience, b.experience)
    subject = f"Canary Foil Club — {s['subject']}"
    rows = "".join([
        _row(s["lbl_experience"], escape(exp)),
        _row(s["lbl_date"], escape(b.date)),
        _row(s["lbl_participants"], str(b.participants)),
    ])
    html = (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'style="background:#050b14;padding:32px 16px"><tr><td align="center">'
        '<table role="presentation" width="560" cellpadding="0" cellspacing="0" '
        'style="background:#0f1c30;border:1px solid #1e2f4a;border-radius:16px;padding:32px">'
        '<tr><td>'
        '<p style="font-family:Arial,sans-serif;font-size:11px;letter-spacing:4px;color:#00f0ff;'
        'text-transform:uppercase;margin:0 0 8px">Canary Foil Club — Costa Adeje</p>'
        f'<h1 style="font-family:Arial,sans-serif;font-size:22px;color:#f8fafc;margin:0 0 12px">'
        f'{escape(s["title"].format(name=b.name))}</h1>'
        f'<p style="font-family:Arial,sans-serif;font-size:14px;line-height:22px;color:#94a3b8;margin:0 0 24px">'
        f'{escape(s["intro"])}</p>'
        f'<p style="font-family:Arial,sans-serif;font-size:11px;letter-spacing:3px;color:#d4af37;'
        f'text-transform:uppercase;margin:0 0 8px">{escape(s["recap"])}</p>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rows}</table>'
        f'<p style="font-family:Arial,sans-serif;font-size:12px;line-height:20px;color:#64748b;margin:24px 0 0">'
        f'{escape(s["note"])}</p>'
        f'<p style="font-family:Arial,sans-serif;font-size:13px;color:#f8fafc;margin:20px 0 0">{s["question"]}</p>'
        f'<p style="font-family:Arial,sans-serif;font-size:11px;color:#64748b;margin:28px 0 0">'
        f'{escape(s["footer"])}</p>'
        '</td></tr></table></td></tr></table>'
    )
    return subject, html


async def notify_client(booking) -> bool:
    try:
        subject, html = build_client_confirmation_email(booking)
        email_id = await send_email(to=booking.email, subject=subject, html=html)
        logger.info(f"Client confirmation sent (id={email_id}) to {booking.email}")
        return True
    except Exception as e:
        logger.error(f"Client confirmation failed for {booking.id}: {e}")
        return False
