from datetime import datetime
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
    return _build_client_email(b, CLIENT_CONFIRM)


CLIENT_CONFIRMED = {
    "fr": {
        "subject": "Votre vol est confirmé",
        "title": "{name}, votre vol est confirmé.",
        "intro": "Excellente nouvelle : votre créneau est validé. Notre équipe vous attend au camp de base mobile à Costa Adeje. Prévoyez maillot, serviette et 10 minutes d'avance — combinaison, gilet et casque radio sont fournis.",
        "recap": "Votre réservation",
        "lbl_experience": "Expérience",
        "lbl_date": "Date",
        "lbl_slot": "Créneau",
        "lbl_participants": "Participants",
        "note": "Le lieu exact de rendez-vous vous sera communiqué la veille par WhatsApp selon les conditions de mer.",
        "question": 'Une question ? Notre ligne WhatsApp VIP : <a href="tel:+34600000000" style="color:#00f0ff">+34 600 000 000</a>',
        "footer": "Canary Foil Club — Costa Adeje, Ténérife. Cet email confirme votre réservation.",
    },
    "en": {
        "subject": "Your flight is confirmed",
        "title": "{name}, your flight is confirmed.",
        "intro": "Great news: your slot is locked in. Our team will welcome you at the mobile base camp in Costa Adeje. Bring swimwear, a towel and arrive 10 minutes early — wetsuit, impact vest and radio helmet are provided.",
        "recap": "Your booking",
        "lbl_experience": "Experience",
        "lbl_date": "Date",
        "lbl_slot": "Time slot",
        "lbl_participants": "Participants",
        "note": "The exact meeting point will be sent by WhatsApp the day before, depending on sea conditions.",
        "question": 'Questions? Our VIP WhatsApp line: <a href="tel:+34600000000" style="color:#00f0ff">+34 600 000 000</a>',
        "footer": "Canary Foil Club — Costa Adeje, Tenerife. This email confirms your booking.",
    },
    "es": {
        "subject": "Tu vuelo está confirmado",
        "title": "{name}, tu vuelo está confirmado.",
        "intro": "Buenas noticias: tu horario está reservado. Nuestro equipo te espera en el campamento base móvil de Costa Adeje. Trae bañador, toalla y llega 10 minutos antes — neopreno, chaleco y casco con radio incluidos.",
        "recap": "Tu reserva",
        "lbl_experience": "Experiencia",
        "lbl_date": "Fecha",
        "lbl_slot": "Horario",
        "lbl_participants": "Participantes",
        "note": "El punto de encuentro exacto se enviará por WhatsApp el día anterior según las condiciones del mar.",
        "question": '¿Dudas? Nuestra línea VIP de WhatsApp: <a href="tel:+34600000000" style="color:#00f0ff">+34 600 000 000</a>',
        "footer": "Canary Foil Club — Costa Adeje, Tenerife. Este email confirma tu reserva.",
    },
}


def _build_client_email(b, strings, extra_rows=None, slot_label=None, cta=None) -> tuple[str, str]:
    lang = b.lang if getattr(b, "lang", None) in strings else "fr"
    s = strings[lang]
    exp = CLIENT_EXP_LABELS[lang].get(b.experience, b.experience)
    subject = f"Canary Foil Club — {s['subject']}"
    rows = [_row(s["lbl_experience"], escape(exp)), _row(s["lbl_date"], escape(b.date))]
    if slot_label and "lbl_slot" in s:
        rows.append(_row(s["lbl_slot"], escape(slot_label)))
    rows.append(_row(s["lbl_participants"], str(b.participants)))
    for label, value in (extra_rows or []):
        rows.append(_row(label, escape(value)))
    rows = "".join(rows)
    cta_html = ""
    if cta:
        cta_html = (
            f'<p style="margin:28px 0 0;text-align:center"><a href="{escape(cta["url"])}" '
            f'style="display:inline-block;background:#00f0ff;color:#050b14;font-family:Arial,sans-serif;font-size:14px;'
            f'font-weight:bold;text-decoration:none;padding:14px 32px;border-radius:999px">{escape(cta["label"])}</a></p>'
        )
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
        f'{cta_html}'
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


async def notify_confirmed(booking, slot_label=None) -> bool:
    try:
        subject, html = _build_client_email(booking, CLIENT_CONFIRMED, slot_label=slot_label)
        email_id = await send_email(to=booking.email, subject=subject, html=html)
        logger.info(f"Client confirmed-email sent (id={email_id}) to {booking.email}")
        return True
    except Exception as e:
        logger.error(f"Client confirmed-email failed for {booking.id}: {e}")
        return False


CLIENT_REMINDER = {
    "fr": {
        "subject": "C'est demain — votre point de rendez-vous",
        "title": "{name}, rendez-vous demain sur l'eau.",
        "intro": "Selon les prévisions de vent et de houle, notre camp de base mobile sera installé au spot indiqué ci-dessous. Merci d'arriver 10 minutes avant votre créneau — combinaison, gilet et casque radio vous attendent.",
        "recap": "Votre rendez-vous",
        "lbl_experience": "Expérience",
        "lbl_date": "Date",
        "lbl_slot": "Heure",
        "lbl_participants": "Participants",
        "lbl_spot": "Point de RDV",
        "lbl_access": "Accès",
        "lbl_conditions": "Conditions",
        "note": "En cas de changement de dernière minute lié à la mer, nous vous prévenons par WhatsApp avant 8h. Pensez au maillot, à la serviette et à la crème solaire.",
        "question": 'Une question ? Notre ligne WhatsApp VIP : <a href="tel:+34600000000" style="color:#00f0ff">+34 600 000 000</a>',
        "footer": "Canary Foil Club — Costa Adeje, Ténérife. Rappel automatique la veille de votre session.",
    },
    "en": {
        "subject": "Tomorrow — your meeting point",
        "title": "{name}, see you on the water tomorrow.",
        "intro": "Based on tomorrow's wind and swell forecast, our mobile base camp will be set up at the spot below. Please arrive 10 minutes before your slot — wetsuit, impact vest and radio helmet are ready for you.",
        "recap": "Your meeting",
        "lbl_experience": "Experience",
        "lbl_date": "Date",
        "lbl_slot": "Time",
        "lbl_participants": "Participants",
        "lbl_spot": "Meeting point",
        "lbl_access": "Access",
        "lbl_conditions": "Conditions",
        "note": "If sea conditions force a last-minute change, we'll message you on WhatsApp before 8am. Bring swimwear, a towel and sunscreen.",
        "question": 'Questions? Our VIP WhatsApp line: <a href="tel:+34600000000" style="color:#00f0ff">+34 600 000 000</a>',
        "footer": "Canary Foil Club — Costa Adeje, Tenerife. Automatic reminder sent the day before your session.",
    },
    "es": {
        "subject": "Mañana — tu punto de encuentro",
        "title": "{name}, nos vemos mañana en el agua.",
        "intro": "Según la previsión de viento y oleaje, nuestro campamento base móvil estará en el spot indicado abajo. Llega 10 minutos antes de tu horario — neopreno, chaleco y casco con radio te esperan.",
        "recap": "Tu cita",
        "lbl_experience": "Experiencia",
        "lbl_date": "Fecha",
        "lbl_slot": "Hora",
        "lbl_participants": "Participantes",
        "lbl_spot": "Punto de encuentro",
        "lbl_access": "Acceso",
        "lbl_conditions": "Condiciones",
        "note": "Si el mar obliga a un cambio de último momento, te avisaremos por WhatsApp antes de las 8h. Trae bañador, toalla y protector solar.",
        "question": '¿Dudas? Nuestra línea VIP de WhatsApp: <a href="tel:+34600000000" style="color:#00f0ff">+34 600 000 000</a>',
        "footer": "Canary Foil Club — Costa Adeje, Tenerife. Recordatorio automático el día anterior a tu sesión.",
    },
}


async def notify_reminder(booking, slot_label, spot, address, conditions) -> bool:
    lang = booking.lang if booking.lang in CLIENT_REMINDER else "fr"
    s = CLIENT_REMINDER[lang]
    extra = [(s["lbl_spot"], spot), (s["lbl_access"], address)]
    if conditions:
        extra.append((s["lbl_conditions"], conditions))
    try:
        subject, html = _build_client_email(booking, CLIENT_REMINDER, extra_rows=extra, slot_label=slot_label)
        email_id = await send_email(to=booking.email, subject=subject, html=html)
        logger.info(f"Client reminder sent (id={email_id}) to {booking.email}")
        return True
    except Exception as e:
        logger.error(f"Client reminder failed for {booking.id}: {e}")
        return False


CLIENT_REVIEW = {
    "fr": {
        "subject": "Comment s'est passé votre vol ?",
        "title": "{name}, merci d'avoir volé avec nous.",
        "intro": "Nous espérons que la sensation de glisse au-dessus de l'Atlantique vous accompagne encore. Un mot de votre part nous aide à faire découvrir l'eFoil à d'autres voyageurs — deux minutes suffisent.",
        "recap": "Votre session",
        "lbl_experience": "Expérience",
        "lbl_date": "Date",
        "lbl_participants": "Participants",
        "cta": "Laisser mon avis",
        "note": "Votre avis pourra être publié sur notre site avec votre prénom uniquement, après relecture par notre équipe.",
        "question": 'Envie de revoler ? Notre ligne WhatsApp VIP : <a href="tel:+34600000000" style="color:#00f0ff">+34 600 000 000</a>',
        "footer": "Canary Foil Club — Costa Adeje, Ténérife. Email envoyé le lendemain de votre session.",
    },
    "en": {
        "subject": "How was your flight?",
        "title": "{name}, thank you for flying with us.",
        "intro": "We hope the feeling of gliding above the Atlantic is still with you. A few words from you help other travellers discover eFoil — it only takes two minutes.",
        "recap": "Your session",
        "lbl_experience": "Experience",
        "lbl_date": "Date",
        "lbl_participants": "Participants",
        "cta": "Leave my review",
        "note": "Your review may be published on our website with your first name only, after review by our team.",
        "question": 'Want to fly again? Our VIP WhatsApp line: <a href="tel:+34600000000" style="color:#00f0ff">+34 600 000 000</a>',
        "footer": "Canary Foil Club — Costa Adeje, Tenerife. Sent the day after your session.",
    },
    "es": {
        "subject": "¿Cómo fue tu vuelo?",
        "title": "{name}, gracias por volar con nosotros.",
        "intro": "Esperamos que la sensación de deslizarte sobre el Atlántico siga contigo. Unas palabras tuyas ayudan a otros viajeros a descubrir el eFoil — solo dos minutos.",
        "recap": "Tu sesión",
        "lbl_experience": "Experiencia",
        "lbl_date": "Fecha",
        "lbl_participants": "Participantes",
        "cta": "Dejar mi opinión",
        "note": "Tu opinión podrá publicarse en nuestra web solo con tu nombre, tras revisión de nuestro equipo.",
        "question": '¿Quieres volver a volar? Nuestra línea VIP de WhatsApp: <a href="tel:+34600000000" style="color:#00f0ff">+34 600 000 000</a>',
        "footer": "Canary Foil Club — Costa Adeje, Tenerife. Enviado el día después de tu sesión.",
    },
}


async def notify_review_request(booking, review_url: str) -> bool:
    lang = booking.lang if booking.lang in CLIENT_REVIEW else "fr"
    try:
        subject, html = _build_client_email(booking, CLIENT_REVIEW, cta={"url": review_url, "label": CLIENT_REVIEW[lang]["cta"]})
        email_id = await send_email(to=booking.email, subject=subject, html=html)
        logger.info(f"Review request sent (id={email_id}) to {booking.email}")
        return True
    except Exception as e:
        logger.error(f"Review request failed for {booking.id}: {e}")
        return False


def _kpi(label: str, value: str, color: str = "#f8fafc") -> str:
    return (f'<td style="padding:14px;border:1px solid #1e2f4a;border-radius:12px;background:#0a1322;vertical-align:top">'
            f'<p style="font-family:Arial,sans-serif;font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#94a3b8;margin:0 0 6px">{escape(label)}</p>'
            f'<p style="font-family:Arial,sans-serif;font-size:22px;font-weight:bold;color:{color};margin:0">{escape(value)}</p></td>')


def build_weekly_report_email(r: dict) -> tuple[str, str]:
    eur = lambda v: f"{v:,.0f} €".replace(",", " ")
    subject = f"Bilan hebdo — semaine du {r['week_label']} : {eur(r['revenue'])} · {r['sessions']} sessions"
    kpis = "".join([
        _kpi("Chiffre d'affaires", eur(r["revenue"]), "#00f0ff"),
        _kpi("Sessions", str(r["sessions"])),
        _kpi("Occupation", f"{r['occupancy']} %"),
        _kpi("Commissions", eur(r["commissions"]), "#d4af37"),
    ])
    def _day_line(d):
        if d["sessions"] == 0:
            return "Jour creux", "#f59e0b"
        return f"{d['sessions']} session(s) · {eur(d['revenue'])} · {d['occupancy']} %", "#94a3b8"

    def _line_row(label, text, color):
        return (f'<tr><td style="padding:8px 0;border-bottom:1px solid #1e2f4a;font-family:Arial,sans-serif;font-size:13px;color:#f8fafc;text-transform:capitalize">{escape(label)}</td>'
                f'<td style="padding:8px 0;border-bottom:1px solid #1e2f4a;font-family:Arial,sans-serif;font-size:13px;color:{color};text-align:right">{escape(text)}</td></tr>')

    day_rows = "".join(_line_row(d["label"], *_day_line(d)) for d in r["days"])
    offers = "".join(_row(k, escape(eur(v))) for k, v in r["by_offer"].items())
    def _next_line(d):
        if d["sessions"] + d["pending"] == 0:
            return "Libre — à remplir", "#f59e0b"
        return f"{d['sessions']} confirmée(s) · {d['pending']} en attente", "#94a3b8"

    next_rows = "".join(_line_row(d["label"], *_next_line(d)) for d in r["next_days"])
    html = (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#050b14;padding:32px 16px"><tr><td align="center">'
        '<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background:#0f1c30;border:1px solid #1e2f4a;border-radius:16px;padding:32px"><tr><td>'
        '<p style="font-family:Arial,sans-serif;font-size:11px;letter-spacing:4px;color:#00f0ff;text-transform:uppercase;margin:0 0 8px">Canary Foil Club — Bilan hebdomadaire</p>'
        f'<h1 style="font-family:Arial,sans-serif;font-size:22px;color:#f8fafc;margin:0 0 6px">Semaine du {escape(r["week_label"])}</h1>'
        f'<p style="font-family:Arial,sans-serif;font-size:13px;color:#94a3b8;margin:0 0 24px">{r["empty_days"]} jour(s) creux · {r["pending_total"]} demande(s) en attente à traiter · note moyenne {r["avg_rating"] or "—"}/5 ({r["reviews"]} avis)</p>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="8"><tr>{kpis}</tr></table>'
        '<p style="font-family:Arial,sans-serif;font-size:11px;letter-spacing:3px;color:#d4af37;text-transform:uppercase;margin:24px 0 8px">Jour par jour</p>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{day_rows}</table>'
        '<p style="font-family:Arial,sans-serif;font-size:11px;letter-spacing:3px;color:#d4af37;text-transform:uppercase;margin:24px 0 8px">CA par offre</p>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{offers}</table>'
        '<p style="font-family:Arial,sans-serif;font-size:11px;letter-spacing:3px;color:#d4af37;text-transform:uppercase;margin:24px 0 8px">Semaine à venir</p>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{next_rows}</table>'
        '<p style="font-family:Arial,sans-serif;font-size:11px;color:#64748b;margin:28px 0 0">Envoyé automatiquement chaque lundi matin par le dashboard Canary Foil Club.</p>'
        '</td></tr></table></td></tr></table>'
    )
    return subject, html


async def send_weekly_report(report: dict, to: str | None = None) -> bool:
    recipient = to or OWNER_EMAIL
    if not recipient:
        logger.warning("OWNER_EMAIL not set; skipping weekly report")
        return False
    try:
        subject, html = build_weekly_report_email(report)
        email_id = await send_email(to=recipient, subject=subject, html=html)
        logger.info(f"Weekly report sent (id={email_id}) to {recipient}")
        return True
    except Exception as e:
        logger.error(f"Weekly report failed: {e}")
        return False


VOUCHER_EMAIL = {
    "fr": {
        "subject": "Votre bon cadeau eFoil est prêt",
        "title": "{name}, votre bon cadeau est activé.",
        "intro": "Merci pour votre confiance. Voici le code à transmettre à la personne de votre choix : il suffit de le saisir dans le formulaire de réservation du site pour offrir ce vol au-dessus de l'Atlantique.",
        "lbl_code": "Code cadeau",
        "lbl_for": "Pour",
        "lbl_experience": "Expérience",
        "lbl_value": "Valeur",
        "lbl_valid": "Valable jusqu'au",
        "lbl_message": "Votre message",
        "note": "Le bon cadeau est utilisable une seule fois, pour une réservation sur le site Canary Foil Club, selon disponibilités et conditions de mer.",
        "question": 'Une question ? Notre ligne WhatsApp VIP : <a href="tel:+34600000000" style="color:#00f0ff">+34 600 000 000</a>',
        "footer": "Canary Foil Club — Costa Adeje, Ténérife. Bon cadeau nominatif.",
    },
    "en": {
        "subject": "Your eFoil gift voucher is ready",
        "title": "{name}, your gift voucher is active.",
        "intro": "Thank you for your trust. Here is the code to pass on to the lucky one: they simply enter it in the booking form on our website to enjoy this flight above the Atlantic.",
        "lbl_code": "Gift code",
        "lbl_for": "For",
        "lbl_experience": "Experience",
        "lbl_value": "Value",
        "lbl_valid": "Valid until",
        "lbl_message": "Your message",
        "note": "The voucher can be used once, for a booking on the Canary Foil Club website, subject to availability and sea conditions.",
        "question": 'Questions? Our VIP WhatsApp line: <a href="tel:+34600000000" style="color:#00f0ff">+34 600 000 000</a>',
        "footer": "Canary Foil Club — Costa Adeje, Tenerife. Personal gift voucher.",
    },
    "es": {
        "subject": "Tu bono regalo eFoil está listo",
        "title": "{name}, tu bono regalo está activado.",
        "intro": "Gracias por tu confianza. Aquí tienes el código para la persona elegida: solo tiene que introducirlo en el formulario de reserva de la web para disfrutar de este vuelo sobre el Atlántico.",
        "lbl_code": "Código regalo",
        "lbl_for": "Para",
        "lbl_experience": "Experiencia",
        "lbl_value": "Valor",
        "lbl_valid": "Válido hasta",
        "lbl_message": "Tu mensaje",
        "note": "El bono se puede usar una sola vez, para una reserva en la web de Canary Foil Club, según disponibilidad y condiciones del mar.",
        "question": '¿Dudas? Nuestra línea VIP de WhatsApp: <a href="tel:+34600000000" style="color:#00f0ff">+34 600 000 000</a>',
        "footer": "Canary Foil Club — Costa Adeje, Tenerife. Bono regalo nominativo.",
    },
}


def build_voucher_email(v: dict) -> tuple[str, str]:
    lang = v.get("lang") if v.get("lang") in VOUCHER_EMAIL else "fr"
    s = VOUCHER_EMAIL[lang]
    exp = CLIENT_EXP_LABELS[lang].get(v["experience"], v["experience"])
    valid = datetime.fromisoformat(v["expires_at"]).strftime("%d/%m/%Y") if v.get("expires_at") else "—"
    rows = [
        _row(s["lbl_for"], escape(v["recipient_name"])),
        _row(s["lbl_experience"], escape(f"{exp} · {v['participants']} pers.")),
        _row(s["lbl_value"], escape(f"{v['value']:.0f} €")),
        _row(s["lbl_valid"], escape(valid)),
    ]
    if v.get("message"):
        rows.append(_row(s["lbl_message"], escape(v["message"])))
    html = (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#050b14;padding:32px 16px"><tr><td align="center">'
        '<table role="presentation" width="560" cellpadding="0" cellspacing="0" style="background:#0f1c30;border:1px solid #1e2f4a;border-radius:16px;padding:32px"><tr><td>'
        '<p style="font-family:Arial,sans-serif;font-size:11px;letter-spacing:4px;color:#d4af37;text-transform:uppercase;margin:0 0 8px">Canary Foil Club — Gift</p>'
        f'<h1 style="font-family:Arial,sans-serif;font-size:22px;color:#f8fafc;margin:0 0 12px">{escape(s["title"].format(name=v["buyer_name"]))}</h1>'
        f'<p style="font-family:Arial,sans-serif;font-size:14px;line-height:22px;color:#94a3b8;margin:0 0 24px">{escape(s["intro"])}</p>'
        f'<p style="font-family:Arial,sans-serif;font-size:11px;letter-spacing:3px;color:#00f0ff;text-transform:uppercase;margin:0 0 8px;text-align:center">{escape(s["lbl_code"])}</p>'
        f'<p style="font-family:Courier New,monospace;font-size:28px;letter-spacing:4px;font-weight:bold;color:#f8fafc;background:#0a1322;border:1px dashed #d4af37;border-radius:12px;padding:18px;text-align:center;margin:0 0 24px">{escape(v["code"])}</p>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{"".join(rows)}</table>'
        f'<p style="font-family:Arial,sans-serif;font-size:12px;line-height:20px;color:#64748b;margin:24px 0 0">{escape(s["note"])}</p>'
        f'<p style="font-family:Arial,sans-serif;font-size:13px;color:#f8fafc;margin:20px 0 0">{s["question"]}</p>'
        f'<p style="font-family:Arial,sans-serif;font-size:11px;color:#64748b;margin:28px 0 0">{escape(s["footer"])}</p>'
        '</td></tr></table></td></tr></table>'
    )
    return f"Canary Foil Club — {s['subject']}", html


async def notify_voucher_buyer(v: dict) -> bool:
    try:
        subject, html = build_voucher_email(v)
        email_id = await send_email(to=v["buyer_email"], subject=subject, html=html)
        logger.info(f"Voucher email sent (id={email_id}) to {v['buyer_email']} code={v['code']}")
        return True
    except Exception as e:
        logger.error(f"Voucher email failed for {v['id']}: {e}")
        return False


async def notify_owner_voucher(v: dict) -> bool:
    if not OWNER_EMAIL:
        return False
    exp = EXPERIENCE_LABELS.get(v["experience"], v["experience"])
    rows = "".join([
        _row("Code", escape(v["code"])),
        _row("Acheteur", escape(v["buyer_name"])),
        _row("Email", f'<a href="mailto:{escape(v["buyer_email"])}" style="color:#00f0ff">{escape(v["buyer_email"])}</a>'),
        _row("Pour", escape(v["recipient_name"])),
        _row("Expérience", escape(f"{exp} · {v['participants']} pers.")),
        _row("Valeur", escape(f"{v['value']:.0f} €")),
        _row("Message", escape(v.get("message") or "—")),
    ])
    html = (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#050b14;padding:32px 16px"><tr><td align="center">'
        '<table role="presentation" width="560" cellpadding="0" cellspacing="0" style="background:#0f1c30;border:1px solid #1e2f4a;border-radius:16px;padding:32px"><tr><td>'
        '<p style="font-family:Arial,sans-serif;font-size:11px;letter-spacing:4px;color:#d4af37;text-transform:uppercase;margin:0 0 8px">Canary Foil Club</p>'
        '<h1 style="font-family:Arial,sans-serif;font-size:22px;color:#f8fafc;margin:0 0 4px">Nouvelle demande de bon cadeau</h1>'
        '<p style="font-family:Arial,sans-serif;font-size:13px;color:#94a3b8;margin:0 0 24px">À activer depuis le dashboard une fois le paiement reçu — l\'acheteur recevra alors son code par email.</p>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rows}</table>'
        '</td></tr></table></td></tr></table>'
    )
    try:
        await send_email(to=OWNER_EMAIL, subject=f"Bon cadeau demandé — {v['value']:.0f} € ({v['buyer_name']})", html=html, reply_to=v["buyer_email"])
        return True
    except Exception as e:
        logger.error(f"Owner voucher notification failed: {e}")
        return False
