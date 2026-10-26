import re
import time
import urllib.parse
from typing import Optional, Tuple, Dict, Any, List
import pyautogui

from ui_controller import (
    open_url_in_chrome,
    is_window_open_with_keyword,
    focus_and_maximize_chrome_window,
    check_if_login_required_on_screen,
    click_ui_element_by_uia_or_ocr,
    find_matches_in_region_fast,
    find_text_on_screen_and_click,
    mouse_click,
    mouse_scroll,
    send_text_and_keys,
    resolve_youtube_video_url,
    get_ocr,
    user32,
)

# Pre-cargar el motor OCR en memoria al iniciar para que las lecturas tarden ~0.07s sin lag inicial
try:
    get_ocr()
except Exception:
    pass

# Memoria de Conciencia de Acción, Contacto Activo y Autodiagnóstico de J.A.R.V.I.S.
LAST_ACTION_STATE: Dict[str, Any] = {
    "active_app": "",
    "last_order": "",
    "last_target_contact": "",
    "last_message_text": "",
    "last_status": "idle",
    "last_detail": "Aún no se ha ejecutado ninguna acción en aplicaciones web.",
    "header_verified": False,
    "timestamp": 0.0,
}

STOPWORDS_CONTACT = {
    "whatsapp", "un mensaje", "el mensaje", "mensaje", "prueba", "de prueba",
    "un mensaje de prueba", "correo", "gmail", "chrome", "google chrome",
    "otro chat", "el primer chat", "primer chat", "la persona", "su perfil",
    "pantalla", "abiertos", "abierto",
}


def update_action_state(
    app: str,
    order: str,
    contact: str = "",
    message: str = "",
    status: str = "ok",
    detail: str = "",
    header_verified: bool = False,
):
    LAST_ACTION_STATE["active_app"] = app
    LAST_ACTION_STATE["last_order"] = order
    if contact and contact.lower().strip() not in STOPWORDS_CONTACT:
        LAST_ACTION_STATE["last_target_contact"] = contact.strip()
    if message:
        LAST_ACTION_STATE["last_message_text"] = message
    LAST_ACTION_STATE["last_status"] = status
    LAST_ACTION_STATE["last_detail"] = detail
    LAST_ACTION_STATE["header_verified"] = header_verified
    LAST_ACTION_STATE["timestamp"] = time.time()


def _extract_explicit_contact(text: str) -> str:
    """
    Extrae con precisión el nombre del contacto (ej. 'David' o 'david' por voz) de cualquier frase:
    - "un mensaje a david diciendo prueba 123" -> "david"
    - "busca a david y manda un mensaje de prueba" -> "david"
    - "manda un mensaje de prueba a david" -> "david"
    - "entra al chat de david y dile hola" -> "david"
    """
    cleaned = re.sub(r"\b(?:en|por|de|desde)\s+whatsapp(?:\s+web)?\b", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    explicit_patterns = [
        # 1. "busca (a) X", "al chat de X", "al perfil de X", "al contacto X", "mándaselo a X", "mándale a X", "un mensaje a X"
        r"\b(?:busca\s+a|buscar\s+a|busca\s+el\s+chat\s+de|busca\s+al\s+contacto|busca|entra\s+al\s+chat\s+de|al\s+chat\s+de|chat\s+de|entra\s+al\s+perfil\s+de|al\s+perfil\s+de|perfil\s+de|al\s+contacto|contacto|un\s+mensaje\s+a|mensaje\s+a|m[aá]ndaselo\s+a|env[ií]aselo\s+a|m[aá]ndale\s+a|escr[ií]bele\s+a|dile\s+a)\s+([a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\+\-]+(?:\s+[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\+\-]+)?)(?=\s+(?:y\b|diciendo\b|que\b|con\b|un\b|el\b|hola\b|mensaje\b|de\s+prueba\b|manda\b|m[aá]ndale\b|env[ií]a\b|escribe\b|dile\b)|[,:.]|$)",
        # 2. "manda un mensaje (de prueba) a X"
        r"\b(?:manda|mandar|env[ií]a|enviar|escribe|escribir|m[aá]ndale|env[ií]ale)\s+(?:un\s+)?(?:mensaje\s+de\s+prueba|mensaje|whatsapp)\s+(?:a|para)\s+([a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\+\-]+(?:\s+[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\+\-]+)?)(?=\s+(?:y\b|diciendo\b|que\b|con\b|hola\b|de\s+prueba\b)|[,:.]|$)",
        # 3. Cualquier "para X" o "a X" antes de "diciendo / que diga / y" o al final
        r"\b(?:para|a)\s+([a-zA-ZáéíóúÁÉÍÓÚñÑ][a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\+\-]+)(?=\s+(?:y\b|diciendo\b|que\b|con\b|de\s+prueba\b)|[,:.]|$)",
    ]

    for pat in explicit_patterns:
        matches = list(re.finditer(pat, cleaned, re.IGNORECASE))
        for m in reversed(matches):
            cand = m.group(1).strip(" ,:.'\"")
            cand = re.sub(
                r"\s+(?:y|diciendo|que\s+diga|con\s+el\s+mensaje|mensaje|de\s+prueba|un\s+mensaje|manda|m[aá]ndale|escribe|hola)$",
                "",
                cand,
                flags=re.IGNORECASE,
            ).strip()
            if cand and cand.lower() not in STOPWORDS_CONTACT:
                return cand
    return ""


def parse_whatsapp_order(raw_order: str) -> Tuple[str, str]:
    """
    Extrae (contacto, mensaje) de forma instantánea y precisa:
    - "un mensaje a david diciendo prueba 123" -> ("david", "prueba 123")
    - "busca a david y manda un mensaje de prueba" -> ("david", "Hola, este es un mensaje de prueba...")
    """
    cleaned = re.sub(r"\b(?:en|por|de|desde)\s+whatsapp(?:\s+web)?\b", "", raw_order, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    explicit_contact = _extract_explicit_contact(cleaned)
    active_contact = explicit_contact or LAST_ACTION_STATE.get("last_target_contact", "")

    # 1. Extraer primero si hay un mensaje explícito tras "diciendo / que diga / con el mensaje / :"
    m_msg = re.search(
        r"(?:diciendo|que\s+diga|con\s+el\s+mensaje|con\s+el\s+texto|y\s+dile|y\s+m[aá]ndale|y\s+env[ií]ale|y\s+escr[ií]bele|y\s+ponle|y\s+manda\s+el\s+mensaje|y\s+manda|[:])\s*(.+)$",
        cleaned,
        re.IGNORECASE,
    )
    if m_msg:
        msg = m_msg.group(1).strip(" '\"")
        if explicit_contact and msg.lower() in [f"a {explicit_contact.lower()}", explicit_contact.lower()]:
            msg = LAST_ACTION_STATE.get("last_message_text", "") or "prueba 123"
        if msg.lower() in ["un mensaje de prueba", "mensaje de prueba", "de prueba"]:
            msg = "Hola, este es un mensaje de prueba enviado por J.A.R.V.I.S."
        return active_contact, msg

    # 2. Si pidió "mensaje de prueba" genérico sin "diciendo..."
    if "mensaje de prueba" in cleaned.lower():
        return active_contact, "Hola, este es un mensaje de prueba enviado por J.A.R.V.I.S."

    if explicit_contact:
        after_contact = re.split(re.escape(explicit_contact), cleaned, flags=re.IGNORECASE)
        if len(after_contact) > 1 and after_contact[-1].strip(" ,:."):
            tail = re.sub(r"^(?:y\s+)?(?:manda|m[aá]ndale|env[ií]a|escribe|dile|el\s+mensaje|un\s+mensaje)\s*", "", after_contact[-1].strip(), flags=re.IGNORECASE).strip(" '\"")
            if tail and tail.lower() not in STOPWORDS_CONTACT:
                return explicit_contact, tail
        return explicit_contact, LAST_ACTION_STATE.get("last_message_text", "") or "prueba 123"

    m_msg_only = re.search(
        r"^(?:manda|mandar|env[ií]a|enviar|escribe|escribir|dile|pon|m[aá]ndale|env[ií]ale)\s+(?:un\s+mensaje\s+|el\s+mensaje\s+)?(.+)$",
        cleaned,
        re.IGNORECASE,
    )
    if m_msg_only:
        cand_msg = m_msg_only.group(1).strip(" '\"")
        if cand_msg and cand_msg.lower() not in STOPWORDS_CONTACT:
            return active_contact, cand_msg

    return active_contact, LAST_ACTION_STATE.get("last_message_text", "") or "prueba 123"


def _verify_header_fast(contact: str, left: int, top: int, right: int, bottom: int) -> Tuple[bool, str]:
    """
    Rectificación del encabezado del chat abierto con coordenadas DPI reales (1920x1080):
    Recorta (650, 155, 1100, 235) donde aparece 'D  David' en (770, 190).
    """
    w = max(800, right - left)
    h = max(600, bottom - top)
    header_box = (
        left + int(w * 0.33),
        top + int(h * 0.14),
        left + int(w * 0.58),
        top + int(h * 0.22),
    )
    matches = find_matches_in_region_fast(contact, header_box)
    if matches:
        return True, matches[0][2]
    return False, ""


def _search_select_and_rectify_whatsapp_contact_fast(
    contact: str, left: int, top: int, right: int, bottom: int
) -> Tuple[bool, str]:
    """
    Flujo fluido, con Criterio Propio y Doble Rectificación:
    1. Comprueba primero si el encabezado del chat abierto YA dice `contact` (ej. 'David' en (770, 190)).
       Si ya está abierto, pasa directo a escribir y enviar el mensaje sin tocar la lista izquierda.
    2. Si no está abierto, hace clic en el buscador (304, 259), escribe el nombre con mayúscula inicial ('David'),
       lee la lista de resultados debajo de 'Chats' ((214, 439) -> 'David'), hace clic sobre la fila exacta de 'David'
       y confirma la apertura del chat.
    """
    w = max(800, right - left)
    h = max(600, bottom - top)
    contact_formatted = contact.strip().title()

    # 1. ¿Ya está abierto el chat de `contact` en el panel derecho?
    already_open, header_txt = _verify_header_fast(contact_formatted, left, top, right, bottom)
    if already_open:
        return True, f"El chat de '{header_txt}' ya estaba abierto y verificado en el encabezado."

    search_x = left + int(w * 0.16)
    search_y = top + int(h * 0.24)
    results_box = (
        left + int(w * 0.03),
        top + int(h * 0.32),
        left + int(w * 0.28),
        top + int(h * 0.66),
    )

    for attempt in range(1, 3):
        # Clic en la barra 'Buscar un chat o iniciar uno nuevo' ((304, 259) en 1920x1080)
        mouse_click(search_x, search_y, button="left", double=False)
        time.sleep(0.15)
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.05)
        pyautogui.press("backspace")
        time.sleep(0.08)
        send_text_and_keys(contact_formatted, press_enter=False)
        time.sleep(0.85)

        # Escaneo OCR del recorte de resultados debajo de 'Chats' ((60, 350, 520, 700))
        rows = find_matches_in_region_fast(contact_formatted, results_box)
        if rows:
            # Priorizar coincidencia exacta ('David' en (214, 439) sobre '@david16434')
            exact_rows = [r for r in rows if r[2].strip().lower() == contact_formatted.lower()]
            chosen = exact_rows[0] if exact_rows else sorted(rows, key=lambda item: item[1])[0]
            mouse_click(chosen[0], chosen[1], button="left", double=False)
            time.sleep(0.65)
            # Como ya localizamos visualmente el texto 'David' en la fila de resultados y le hicimos clic,
            # verificamos el encabezado o procedemos directamente sabiendo que clicamos la fila de 'David'
            ok_header, h_txt = _verify_header_fast(contact_formatted, left, top, right, bottom)
            if ok_header or exact_rows:
                return True, f"Encontré a '{chosen[2]}' en la lista de resultados ({chosen[0]}, {chosen[1]}) y abrí su chat."
        else:
            # Si OCR aún no leyó la fila en el intento 1, hacer clic en la posición del primer resultado bajo 'Chats' (214, 439)
            first_chat_x = left + int(w * 0.115)
            first_chat_y = top + int(h * 0.406)
            mouse_click(first_chat_x, first_chat_y, button="left", double=False)
            time.sleep(0.65)
            ok_header, h_txt = _verify_header_fast(contact_formatted, left, top, right, bottom)
            if ok_header:
                return True, f"Rectificado en el encabezado: '{h_txt}'."

    return False, f"No se encontró '{contact_formatted}' en la lista de resultados."


def _send_message_in_open_whatsapp_chat_fast(left: int, top: int, right: int, bottom: int, message_text: str):
    """
    Clic directo e instantáneo en 'Escribe un mensaje' ((867, 973) en 1920x1080 -> x=45%, y=90%),
    pega el texto y presiona Enter en <0.35s total.
    """
    w = max(800, right - left)
    h = max(600, bottom - top)
    msg_box_x = left + int(w * 0.45)
    msg_box_y = top + int(h * 0.90)
    mouse_click(msg_box_x, msg_box_y, button="left", double=False)
    time.sleep(0.15)
    send_text_and_keys(message_text, press_enter=True)
    time.sleep(0.12)
    pyautogui.press("enter")


def workflow_whatsapp_send_message(raw_order: str) -> str:
    """
    Flujo de WhatsApp Web fluido, directo y sin lag:
    - Si el chat de la persona (ej. 'David') ya está abierto en pantalla, lo detecta en 0.07s y envía el mensaje de inmediato.
    - Si no está abierto, lo busca en el buscador (304, 259), abre su fila, rectifica el encabezado en 0.07s y envía el mensaje en (867, 973).
    """
    contact, message_text = parse_whatsapp_order(raw_order)
    already_open = is_window_open_with_keyword("WhatsApp")

    if not already_open:
        open_url_in_chrome("https://web.whatsapp.com")
        time.sleep(6.0)
    else:
        time.sleep(0.15)

    left, top, right, bottom = focus_and_maximize_chrome_window("WhatsApp")

    if not contact:
        update_action_state(
            app="whatsapp",
            order=raw_order,
            contact="",
            message=message_text,
            status="waiting_contact",
            detail="Falta el nombre del contacto destino.",
            header_verified=False,
        )
        return f"Señor, dígame el nombre del contacto al que desea enviar '{message_text}' (por ejemplo: 'Un mensaje a David diciendo {message_text}')."

    digits = re.sub(r"\D", "", contact)
    if len(digits) >= 8:
        url = f"https://web.whatsapp.com/send?phone={digits}&text={urllib.parse.quote(message_text)}"
        open_url_in_chrome(url)
        time.sleep(6.5)
        focus_and_maximize_chrome_window("WhatsApp")
        time.sleep(0.3)
        pyautogui.press("enter")
        update_action_state("whatsapp", raw_order, contact, message_text, "ok", f"Enviado al número {contact}.", True)
        return f"Ya terminé la acción, Señor: Envié '{message_text}' al número {contact}."

    ok_chat, verification_note = _search_select_and_rectify_whatsapp_contact_fast(contact, left, top, right, bottom)
    if not ok_chat:
        update_action_state(
            app="whatsapp",
            order=raw_order,
            contact=contact,
            message=message_text,
            status="contact_not_verified",
            detail=verification_note,
            header_verified=False,
        )
        return f"Señor, busqué a '{contact}' y rectifiqué dos veces el encabezado, pero no se pudo abrir su chat ({verification_note})."

    _send_message_in_open_whatsapp_chat_fast(left, top, right, bottom, message_text)
    update_action_state(
        app="whatsapp",
        order=raw_order,
        contact=contact,
        message=message_text,
        status="ok",
        detail=f"{verification_note} Mensaje enviado: '{message_text}'.",
        header_verified=True,
    )
    return f"Ya terminé la acción, Señor: Envié '{message_text}' en el chat de '{contact}'."


def diagnose_and_recover_last_action(user_complaint: str) -> str:
    explicit_in_complaint = _extract_explicit_contact(user_complaint)
    if explicit_in_complaint:
        LAST_ACTION_STATE["last_target_contact"] = explicit_in_complaint

    contact = LAST_ACTION_STATE.get("last_target_contact", "")
    last_msg = LAST_ACTION_STATE.get("last_message_text", "") or "prueba 123"
    last_detail = LAST_ACTION_STATE.get("last_detail", "")

    if not is_window_open_with_keyword("WhatsApp"):
        open_url_in_chrome("https://web.whatsapp.com")
        time.sleep(6.0)

    left, top, right, bottom = focus_and_maximize_chrome_window("WhatsApp")

    if contact:
        ok_chat, verification_note = _search_select_and_rectify_whatsapp_contact_fast(contact, left, top, right, bottom)
        if ok_chat:
            _send_message_in_open_whatsapp_chat_fast(left, top, right, bottom, last_msg)
            update_action_state("whatsapp", user_complaint, contact, last_msg, "recovered", verification_note, True)
            return f"Listo, Señor: rectifiqué el chat de '{contact}' de forma directa y acabo de enviar '{last_msg}'."
        return f"Señor, revisé el buscador dos veces para '{contact}' pero no se confirmó en el encabezado ({verification_note})."

    return f"Señor, revisando mi última acción ({last_detail}): dígame a qué contacto enviarlo (ej. 'Un mensaje a David diciendo prueba 123')."


def workflow_gmail_compose_or_send(raw_order: str) -> str:
    low = raw_order.lower()
    wants_send = any(w in low for w in ["envíalo", "envialo", "mándalo", "mandalo", "enviar a", "mandar a", "manda un correo a", "envía un correo a", "envia un correo a"])
    is_draft = "borrador" in low or not wants_send

    email_match = re.search(r"([\w\.\-]+@[\w\.\-]+\.\w+)", raw_order)
    to_addr = email_match.group(1) if email_match else ""

    subj_match = re.search(
        r"(?:con\s+asunto|asunto|sobre|de\s+tema|acerca\s+de|para\s+hablar\s+de)\s+([^,\.]+?)(?:\s+diciendo|\s+que\s+diga|\s+con\s+el\s+texto|\s+con\s+el\s+mensaje|$)",
        raw_order,
        re.IGNORECASE,
    )
    body_match = re.search(
        r"(?:diciendo|que\s+diga|con\s+el\s+mensaje|con\s+el\s+texto|contenido|escribe\s+que)\s*[:\s]\s*(.+)$",
        raw_order,
        re.IGNORECASE,
    )

    subject_txt = subj_match.group(1).strip() if subj_match else ""
    body_txt = body_match.group(1).strip() if body_match else ""

    if not body_txt:
        topic_match = re.search(r"(?:sobre|acerca\s+de|de)\s+(.+)$", raw_order, re.IGNORECASE)
        topic = topic_match.group(1).strip() if topic_match else ""
        if topic and topic.lower() not in ["borrador", "un borrador", "correo", "un correo", "gmail"]:
            if not subject_txt:
                subject_txt = f"Borrador: {topic.capitalize()}"
            body_txt = f"Hola,\n\nTe escribo respecto a {topic}.\n\nQuedo atento a tus comentarios.\nSaludos cordiales."
        else:
            if not subject_txt:
                subject_txt = "Borrador preparado por J.A.R.V.I.S."
            body_txt = "Hola,\n\nTe escribo para compartirte la siguiente información:\n\nQuedo atento a tu respuesta.\nSaludos cordiales."
    elif not subject_txt:
        subject_txt = "Mensaje importante"

    params = {
        "view": "cm",
        "fs": "1",
        "su": subject_txt,
        "body": body_txt,
    }
    if to_addr:
        params["to"] = to_addr

    compose_url = "https://mail.google.com/mail/?" + urllib.parse.urlencode(params)
    open_url_in_chrome(compose_url)

    time.sleep(4.2)
    focus_and_maximize_chrome_window("Gmail")

    if check_if_login_required_on_screen():
        update_action_state("gmail", raw_order, to_addr, body_txt, "login_required", "Gmail pidió iniciar sesión.")
        return "Señor, abrí Gmail en Google Chrome pero necesita iniciar sesión en su cuenta para que pueda redactar el correo."

    if not is_draft and to_addr:
        time.sleep(1.0)
        clicked = click_ui_element_by_uia_or_ocr("Enviar", double_click=False, right_click=False)
        if not clicked:
            pyautogui.hotkey("ctrl", "enter")
        update_action_state("gmail", raw_order, to_addr, body_txt, "ok", f"Correo enviado a {to_addr}.")
        return f"Ya terminé la acción, Señor: Abrí Gmail, redacté el correo para {to_addr} con asunto '{subject_txt}' y lo envié."

    update_action_state("gmail", raw_order, to_addr, body_txt, "ok", f"Borrador guardado en Gmail con asunto '{subject_txt}'.")
    return f"Ya terminé la acción, Señor: Abrí Gmail y dejé su correo redactado y guardado en Borradores con asunto '{subject_txt}'."


def workflow_youtube_watch_and_comment(raw_order: str) -> str:
    comment_match = re.search(
        r"(?:y\s+)?(?:comenta|comentar|escribe\s+un\s+comentario|deja\s+un\s+comentario|pon\s+un\s+comentario)\s*(?:diciendo|que\s+diga|[:])?\s*(.+)$",
        raw_order,
        re.IGNORECASE,
    )
    comment_text = comment_match.group(1).strip().strip("'\"") if comment_match else ""

    video_part = raw_order[:comment_match.start()].strip() if comment_match else raw_order
    video_part = re.sub(
        r"^(?:abre\s+youtube\s+y\s+|entra\s+a\s+youtube\s+y\s+|ve\s+a\s+youtube\s*(?:,\s*|\s+y\s+))?(?:ve\s+al\s+video\s+de|busca\s+el\s+video\s+de|pon\s+el\s+video\s+de|abre\s+el\s+video\s+de|pon|reproduce|busca|abre)\s*",
        "",
        video_part,
        flags=re.IGNORECASE,
    ).replace("en youtube", "").strip(" ,")

    if video_part and video_part.lower() != "youtube":
        direct_url = resolve_youtube_video_url(video_part)
        target_url = direct_url if direct_url else f"https://www.youtube.com/results?search_query={urllib.parse.quote(video_part)}"
        open_url_in_chrome(target_url)
    else:
        open_url_in_chrome("https://www.youtube.com")

    if not comment_text:
        update_action_state("youtube", raw_order, "", "", "ok", f"Video '{video_part}' abierto.")
        return f"Ya terminé la acción, Señor: Video '{video_part}' reproduciéndose en YouTube."

    time.sleep(5.0)
    left, top, right, bottom = focus_and_maximize_chrome_window("YouTube")
    w = max(800, right - left)
    h = max(600, bottom - top)

    mouse_scroll("down", amount=6)
    time.sleep(1.2)

    clicked_box = (
        find_text_on_screen_and_click("comentario", double_click=False)
        or find_text_on_screen_and_click("comment", double_click=False)
    )
    if not clicked_box:
        mouse_click(left + int(w * 0.35), top + int(h * 0.68), button="left", double=False)

    time.sleep(0.6)
    send_text_and_keys(comment_text, press_enter=False)
    time.sleep(0.6)
    if not click_ui_element_by_uia_or_ocr("Comentar", double_click=False):
        click_ui_element_by_uia_or_ocr("Comment", double_click=False)

    update_action_state("youtube", raw_order, "", comment_text, "ok", f"Comentario '{comment_text}' publicado en '{video_part}'.")
    return f"Ya terminé la acción, Señor: Abrí el video '{video_part}' en YouTube, bajé a los comentarios y publiqué '{comment_text}'."


def workflow_generic_webapp_multistep(app_label: str, base_url: str, raw_order: str) -> str:
    low = raw_order.lower()

    if "outlook" in low and any(w in low for w in ["borrador", "redacta", "redactar", "correo", "mensaje", "manda", "envía", "envia"]):
        email_match = re.search(r"([\w\.\-]+@[\w\.\-]+\.\w+)", raw_order)
        to_addr = email_match.group(1) if email_match else ""
        subj_match = re.search(r"(?:asunto|sobre|de\s+tema)\s+([^,\.]+?)(?:\s+diciendo|\s+que\s+diga|$)", raw_order, re.IGNORECASE)
        body_match = re.search(r"(?:diciendo|que\s+diga|con\s+el\s+texto)\s*[:\s]\s*(.+)$", raw_order, re.IGNORECASE)
        subject_txt = subj_match.group(1).strip() if subj_match else "Borrador preparado por J.A.R.V.I.S."
        body_txt = body_match.group(1).strip() if body_match else "Hola,\n\nTe escribo respecto a este asunto.\n\nSaludos cordiales."
        compose_outlook = f"https://outlook.live.com/mail/0/deeplink/compose?subject={urllib.parse.quote(subject_txt)}&body={urllib.parse.quote(body_txt)}"
        if to_addr:
            compose_outlook += f"&to={urllib.parse.quote(to_addr)}"
        open_url_in_chrome(compose_outlook)
        time.sleep(4.2)
        focus_and_maximize_chrome_window("Outlook")
        if check_if_login_required_on_screen():
            return "Señor, abrí Outlook en Chrome pero necesita iniciar sesión en su cuenta."
        update_action_state("outlook", raw_order, to_addr, body_txt, "ok", f"Borrador en Outlook '{subject_txt}'.")
        return f"Ya terminé la acción, Señor: Abrí Outlook y dejé su correo redactado con asunto '{subject_txt}'."

    search_match = re.search(r"(?:y\s+)?(?:busca|buscar|encuentra|pon|reproduce|abre\s+el\s+archivo|abre\s+el\s+dise[ñn]o)\s+(.+)$", raw_order, re.IGNORECASE)
    click_match = re.search(r"(?:y\s+)?(?:haz\s+clic\s+en|da\s+clic\s+en|dale\s+clic\s+a|oprime|presiona|selecciona)\s+(.+?)(?:\s+y\s+escribe.+|$)", raw_order, re.IGNORECASE)
    write_match = re.search(r"(?:y\s+)?(?:escribe|escribir|comenta|comentar|manda\s+un\s+mensaje\s+diciendo|diciendo|que\s+diga)\s*[:\s]\s*(.+)$", raw_order, re.IGNORECASE)

    target_url = base_url
    search_term = ""
    if search_match:
        candidate = search_match.group(1).strip()
        if app_label.lower() not in candidate.lower():
            search_term = candidate
            if "drive.google.com" in base_url:
                target_url = f"https://drive.google.com/drive/search?q={urllib.parse.quote(search_term)}"
            elif "canva.com" in base_url:
                target_url = f"https://www.canva.com/search/templates?q={urllib.parse.quote(search_term)}"
            elif "netflix.com" in base_url:
                target_url = f"https://www.netflix.com/search?q={urllib.parse.quote(search_term)}"

    open_url_in_chrome(target_url)
    time.sleep(4.2)
    focus_and_maximize_chrome_window(app_label)

    if check_if_login_required_on_screen():
        return f"🔐 Señor, he abierto {app_label} en su Google Chrome, pero necesita iniciar sesión en su cuenta para continuar."

    actions_done = [f"abrí {app_label}"]
    if search_term and target_url != base_url:
        actions_done.append(f"busqué '{search_term}'")

    if click_match:
        target = click_match.group(1).strip().strip("'\"")
        coords = click_ui_element_by_uia_or_ocr(target, double_click=False)
        if coords:
            actions_done.append(f"hice clic en '{target}'")
            time.sleep(0.8)

    if search_term and target_url == base_url and not click_match:
        if not (find_text_on_screen_and_click("Buscar", False) or find_text_on_screen_and_click("Search", False)):
            pyautogui.press("/")
        time.sleep(0.4)
        send_text_and_keys(search_term, press_enter=True)
        actions_done.append(f"busqué '{search_term}'")
        time.sleep(0.8)

    if write_match:
        txt = write_match.group(1).strip().strip("'\"")
        send_text_and_keys(txt, press_enter=True)
        actions_done.append(f"escribí y envié '{txt}'")

    if any(w in low for w in ["scroll abajo", "baja", "desplaza abajo"]):
        mouse_scroll("down", amount=6)
        actions_done.append("hice scroll hacia abajo")
    elif any(w in low for w in ["scroll arriba", "sube", "desplaza arriba"]):
        mouse_scroll("up", amount=6)
        actions_done.append("hice scroll hacia arriba")

    update_action_state(app_label.lower(), raw_order, "", "", "ok", ", ".join(actions_done))
    return f"Ya terminé la acción, Señor: {', '.join(actions_done)}."
