"""Deterministic Spanish institutional templates; no external content or network calls."""
from dataclasses import dataclass
from datetime import datetime
from html import escape
from urllib.parse import urlsplit


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    text: str
    html: str


def _label(value: str) -> str:
    value = value.strip()
    if not value or len(value) > 120 or any(ord(c) < 32 for c in value):
        raise ValueError("Invalid template label")
    return value


def _date(value: datetime) -> str:
    if value.utcoffset() is None:
        raise ValueError("Timezone-aware date required")
    return value.isoformat(sep=" ", timespec="minutes")


def _render(subject: str, lines: list[str], url: str | None = None) -> RenderedEmail:
    text = "\n\n".join(lines)
    html = '<html lang="es"><body>' + "".join("<p>" + escape(line) + "</p>" for line in lines)
    if url:
        text += "\n\nAcceder a la reunión: " + url
        html += '<p><a href="' + escape(url, quote=True) + '">Acceder a la reunión</a></p>'
    return RenderedEmail(subject, text, html + "</body></html>")


def zoom_invitation(*, session: str, starts_at: datetime, join_url: str) -> RenderedEmail:
    session = _label(session)
    parsed = urlsplit(join_url)
    if (parsed.scheme != "https" or not parsed.hostname
            or not (parsed.hostname == "zoom.us" or parsed.hostname.endswith(".zoom.us"))
            or parsed.username or parsed.password or any(ord(c) <= 32 for c in join_url)
            or parsed.port not in (None, 443)):
        raise ValueError("Invalid Zoom join URL")
    if not parsed.path.startswith("/j/"):
        raise ValueError("Expected participant join link")
    return _render("Invitación: " + session, [
        "Te invitamos a la sesión " + session + ".",
        "Fecha y hora: " + _date(starts_at),
        "Accede únicamente si eres destinatario autorizado.",
    ], join_url)


def academic_reminder(*, activity: str, due_at: datetime) -> RenderedEmail:
    activity = _label(activity)
    return _render("Recordatorio: " + activity, [
        "Te recordamos la actividad " + activity + ".",
        "Fecha y hora: " + _date(due_at),
        "Consulta EduGest para más información.",
    ])


def academic_notification(*, topic: str) -> RenderedEmail:
    topic = _label(topic)
    return _render("Aviso académico: " + topic, [
        "Hay una actualización relacionada con " + topic + ".",
        "Consulta EduGest para conocer los detalles.",
    ])
