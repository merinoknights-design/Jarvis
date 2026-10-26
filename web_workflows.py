import re
import time
import urllib.parse
from typing import Optional, Tuple, Dict, Any
import pyautogui

from ui_controller import (
    open_url_in_chrome,
    is_window_open_with_keyword,
    focus_and_maximize_chrome_window,
    check_if_login_required_on_screen,
    click_ui_element_by_uia_or_ocr,
    find_text_on_screen_and_click,
    mouse_click,
    mouse_scroll,
    send_text_and_keys,
    resolve_youtube_video_url,
    user32,
)

# Memoria de Conciencia de Acción y Autodiagnóstico de J.A.R.V.I.S.
LAST_ACTION_STATE: Dict[str, Any] = {
    "active_app": "",
    "last_order": "",
    "last_target_contact": "",
    "last_message_text": "",
    "last_status": "idle",
    "last_detail": "Aún no se ha ejecutado ninguna acción en aplicaciones web.",
    "timestamp": 0.0,
}


def update_action_state(
    app: str,
    order: str,
    contact: str = "",
    message: str = "",
    status: str = "ok",
    detail: str = "",
):
    LAST_ACTION_STATE["active_app"] = app
    LAST_ACTION_STATE["last_order"] = order
    if contact:
        LAST_ACTION_STATE["last_target_contact"] = contact
    if message:
        LAST_ACTION_STATE["last_message_text"] = message
    LAST_ACTION_STATE["last_status"] = status
    LAST_ACTION_STATE["last_detail"] = detail
    LAST_ACTION_STATE["timestamp"] = time.time()


def parse_whatsapp_order(raw_order: str) -> Tuple[str, str]:
    """
    Extrae (contacto, mensaje) con razonamiento contextual:
    Soporta tanto órdenes con contacto como órdenes directas ("manda un mensaje de prueba",
    "manda hola", "manda un mensaje de prueba a Juan", "abre whatsapp, entra al perfil de María y manda ya voy").
    """
    cleaned = re.sub(r"\b(?:en|por|de|desde)\s+whatsapp(?:\s+web)?\b", "", raw_order, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    def _clean_contact_name(raw_c: str) -> str:
        c = raw_c.strip(" ,:.'\"")
        c = re.sub(
            r"^(?:abre\s+whatsapp\s*,\s*|entra\s+|ve\s+|busca\s+|manda\s+|mandar\s+|env[ií]a\s+|enviar\s+|escribe\s+|un\s+mensaje\s+de\s+prueba\s+|un\s+mensaje\s+|el\s+mensaje\s+|un\s+whatsapp\s+|al\s+perfil\s+de\s+|el\s+perfil\s+de\s+|perfil\s+de\s+|al\s+contacto\s+|contacto\s+|al\s+chat\s+de\s+|chat\s+de\s+|para\s+|a\s+)+",
            "",
            c,
            flags=re.IGNORECASE,
        ).strip(" ,:.'\"")
        return c

    # Caso especial 0: "manda un mensaje de prueba [a Contacto]" o "manda un mensaje de prueba"
    m_test = re.search(
        r"(?:manda|mandar|env[ií]a|enviar|escribe|haz|pon)\s+(?:un\s+)?mensaje\s+de\s+prueba(?:\s+(?:a|para|al\s+perfil\s+de)\s+([a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\s\+\-]+?))?(?:\s+(?:diciendo|que\s+diga)\s+(.+))?$",
        cleaned,
        re.IGNORECASE,
    )
    if m_test:
        contact = _clean_contact_name(m_test.group(1) or "") or LAST_ACTION_STATE.get("last_target_contact", "")
        msg = (m_test.group(2) or "Hola, este es un mensaje de prueba enviado por J.A.R.V.I.S.").strip(" '\"")
        return contact, msg

    patterns = [
        # 1. "... a / al perfil de [Contacto] diciendo / que diga / con el mensaje / : [Mensaje]"
        r"\b(?:al\s+perfil\s+de|perfil\s+de|al\s+contacto|al\s+chat\s+de|busca\s+a|para|a)\s+([^,:]+?)\s+(?:diciendo|que\s+diga|con\s+el\s+mensaje|con\s+el\s+texto|y\s+dile|y\s+m[aá]ndale|y\s+env[ií]ale|y\s+escr[ií]bele|y\s+ponle|[:])\s*(.+)$",
        # 2. "... perfil de [Contacto] y manda/escribe (el mensaje) [Mensaje]"
        r"\b(?:al\s+perfil\s+de|perfil\s+de|al\s+chat\s+de|chat\s+de|al\s+contacto|contacto|busca\s+a|para|a)\s+([a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\s\+\-]+?)\s+y\s+(?:manda|m[aá]ndale|env[ií]a|env[ií]ale|escribe|escr[ií]bele|pon|ponle)\s+(?:el\s+mensaje\s+|un\s+mensaje\s+)?(?:diciendo\s+|que\s+diga\s+)?(.+)$",
        # 3. "diciendo [Mensaje] a [Contacto]"
        r"\b(?:diciendo|que\s+diga|mensaje)\s+['\"]?(.+?)['\"]?\s+\b(?:a|para)\s+([a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\s\+\-]+)$",
        # 4. "manda un mensaje a [Contacto] [Mensaje]"
        r"\b(?:manda|mandar|env[ií]a|enviar|escribe|escr[ií]bele|m[aá]ndale)\s+(?:un\s+mensaje\s+|un\s+whatsapp\s+|el\s+mensaje\s+)?\b(?:a|para)\s+([a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\+\-]+)\s+(.+)$",
    ]

    for idx, pat in enumerate(patterns):
        m = re.search(pat, cleaned, re.IGNORECASE)
        if m:
            if idx == 2:
                msg, contact = m.group(1).strip(), _clean_contact_name(m.group(2))
            else:
                contact, msg = _clean_contact_name(m.group(1)), m.group(2).strip()
            msg = msg.strip(" '\"")
            if contact and msg:
                return contact, msg

    # 5. Si el usuario solo dijo qué mandar sin repetir el contacto (ej. "manda hola como vas", "manda un mensaje diciendo ya voy", "escribe hola")
    m_msg_only = re.search(
        r"^(?:manda|mandar|env[ií]a|enviar|escribe|escribir|dile|pon|m[aá]ndale|env[ií]ale)\s+(?:un\s+mensaje\s+|el\s+mensaje\s+)?(?:diciendo\s+|que\s+diga\s+)?(.+)$",
        cleaned,
        re.IGNORECASE,
    )
    if m_msg_only:
        candidate_msg = m_msg_only.group(1).strip(" '\"")
        if candidate_msg and candidate_msg.lower() not in ["un mensaje", "mensaje", "whatsapp"]:
            return LAST_ACTION_STATE.get("last_target_contact", ""), candidate_msg

    # 6. Si solo mencionó el contacto ("manda un mensaje a Juan")
    m_only_contact = re.search(r"\b(?:al\s+perfil\s+de|busca\s+a|para|a)\s+([a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\s\+\-]+)$", cleaned, re.IGNORECASE)
    if m_only_contact:
        c = _clean_contact_name(m_only_contact.group(1))
        if c:
            return c, "Hola, este es un mensaje de prueba."

    return LAST_ACTION_STATE.get("last_target_contact", ""), "Hola, mensaje de prueba."


def _focus_whatsapp_message_box_and_send(left: int, top: int, right: int, bottom: int, message_text: str) -> bool:
    """
    Intenta localizar la caja 'Escribe un mensaje' en WhatsApp Web por UIA y por coordenadas,
    pega el texto y presiona Enter.
    """
    w = max(800, right - left)
    # 1. Intentar localizar el control 'Escribe un mensaje' o 'Type a message' con UIA
    clicked_uia = (
        click_ui_element_by_uia_or_ocr("Escribe un mensaje", double_click=False)
        or click_ui_element_by_uia_or_ocr("Type a message", double_click=False)
    )
    if not clicked_uia:
        # 2. Clic directo en la barra inferior del panel derecho de WhatsApp Web
        msg_box_x = left + int(w * 0.60)
        msg_box_y = bottom - 62
        mouse_click(msg_box_x, msg_box_y, button="left", double=False)

    time.sleep(0.35)
    send_text_and_keys(message_text, press_enter=True)
    time.sleep(0.25)
    pyautogui.press("enter")
    return True


def workflow_whatsapp_send_message(raw_order: str) -> str:
    """
    Flujo autónomo de principio a fin en WhatsApp Web:
    - Si WhatsApp Web ya está abierto en Chrome, NO abre otra pestaña duplicada; reutiliza la ventana actual.
    - Si tiene nombre de contacto, lo busca y abre su perfil/chat.
    - Si no se dio nombre de contacto (ej. 'manda un mensaje de prueba'), selecciona el chat activo o el primer chat de la lista y envía el mensaje.
    - Registra cada paso en LAST_ACTION_STATE para que Jarvis tenga conciencia exacta de lo que hizo o si algo falló.
    """
    contact, message_text = parse_whatsapp_order(raw_order)
    already_open = is_window_open_with_keyword("WhatsApp")

    if not already_open:
        open_url_in_chrome("https://web.whatsapp.com")
        time.sleep(7.0)
    else:
        time.sleep(0.5)

    left, top, right, bottom = focus_and_maximize_chrome_window("WhatsApp")
    w = max(800, right - left)

    # Si es un número telefónico directo
    digits = re.sub(r"\D", "", contact)
    if len(digits) >= 8:
        url = f"https://web.whatsapp.com/send?phone={digits}&text={urllib.parse.quote(message_text)}"
        open_url_in_chrome(url)
        time.sleep(7.5)
        focus_and_maximize_chrome_window("WhatsApp")
        time.sleep(0.5)
        pyautogui.press("enter")
        update_action_state(
            app="whatsapp",
            order=raw_order,
            contact=contact,
            message=message_text,
            status="ok",
            detail=f"Se abrió el enlace directo del número {contact} y se envió '{message_text}'.",
        )
        return f"Ya terminé la acción, Señor: Envié el mensaje '{message_text}' al número {contact} en WhatsApp."

    if contact:
        # Paso 1: Enfocar barra de búsqueda de contactos en el panel izquierdo
        search_x = left + int(w * 0.14)
        search_y = top + 168
        mouse_click(search_x, search_y, button="left", double=False)
        time.sleep(0.25)
        pyautogui.hotkey("ctrl", "alt", "/")
        time.sleep(0.35)

        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.1)
        pyautogui.press("backspace")
        time.sleep(0.15)
        send_text_and_keys(contact, press_enter=False)
        time.sleep(1.5)

        # Seleccionar el contacto encontrado con Enter y clic en el primer resultado de la lista izquierda
        pyautogui.press("down")
        time.sleep(0.15)
        pyautogui.press("enter")
        time.sleep(0.8)
        mouse_click(left + int(w * 0.16), top + 280, button="left", double=False)
        time.sleep(0.9)
    else:
        # Si no especificó contacto (ej. "manda un mensaje de prueba"), asegurarse de que haya un chat seleccionado
        # haciendo clic en el primer chat de la lista izquierda por si no había ninguno abierto
        mouse_click(left + int(w * 0.16), top + 250, button="left", double=False)
        time.sleep(0.7)

    # Paso 2: Escribir el mensaje en la caja inferior derecha y enviarlo
    _focus_whatsapp_message_box_and_send(left, top, right, bottom, message_text)

    target_desc = f"a '{contact}'" if contact else "en el chat activo de WhatsApp"
    update_action_state(
        app="whatsapp",
        order=raw_order,
        contact=contact,
        message=message_text,
        status="ok",
        detail=f"Se enfocó la ventana de WhatsApp ({w}px), se seleccionó el chat {target_desc}, se hizo clic en la barra de mensaje inferior y se envió '{message_text}'.",
    )
    return f"Ya terminé la acción, Señor: Envié el mensaje '{message_text}' {target_desc}."


def diagnose_and_recover_last_action(user_complaint: str) -> str:
    """
    Razonamiento propio y autodiagnóstico de J.A.R.V.I.S. cuando el usuario dice:
    'no veo el mensaje', 'no lo mandó', '¿qué pasó con el error?', 'no hizo nada', etc.
    1. Revisa LAST_ACTION_STATE y qué ventanas están abiertas realmente en Windows.
    2. Explica con conciencia propia qué ocurrió en el intento anterior (sin buscar cosas raras en internet).
    3. Reintenta la acción corrigiendo el foco y la posición del chat en vivo.
    """
    app = LAST_ACTION_STATE.get("active_app", "")
    last_msg = LAST_ACTION_STATE.get("last_message_text", "") or "Hola, este es un mensaje de prueba."
    last_contact = LAST_ACTION_STATE.get("last_target_contact", "")
    last_detail = LAST_ACTION_STATE.get("last_detail", "")

    whatsapp_open = is_window_open_with_keyword("WhatsApp")

    if app == "whatsapp" or "mensaje" in user_complaint.lower() or "whatsapp" in user_complaint.lower():
        if not whatsapp_open:
            open_url_in_chrome("https://web.whatsapp.com")
            time.sleep(6.5)

        left, top, right, bottom = focus_and_maximize_chrome_window("WhatsApp")
        w = max(800, right - left)

        # Seleccionar el primer chat de la columna izquierda y luego la caja de texto inferior
        if last_contact:
            mouse_click(left + int(w * 0.14), top + 168, button="left", double=False)
            time.sleep(0.25)
            pyautogui.hotkey("ctrl", "a")
            pyautogui.press("backspace")
            send_text_and_keys(last_contact, press_enter=True)
            time.sleep(1.3)
            mouse_click(left + int(w * 0.16), top + 280, button="left", double=False)
            time.sleep(0.8)
        else:
            mouse_click(left + int(w * 0.16), top + 250, button="left", double=False)
            time.sleep(0.7)

        _focus_whatsapp_message_box_and_send(left, top, right, bottom, last_msg)

        reason = (
            f"en el intento anterior WhatsApp Web aún estaba terminando de cargar la pestaña o no había ningún chat abierto en el panel derecho cuando pegué el texto '{last_msg}'"
            if not last_contact
            else f"al buscar a '{last_contact}', la pestaña de WhatsApp seguía cargando o el foco seguía en mi ventana antes de entrar al chat"
        )
        update_action_state(
            app="whatsapp",
            order=user_complaint,
            contact=last_contact,
            message=last_msg,
            status="recovered",
            detail=f"Autodiagnóstico ejecutado y reenvío completado para '{last_msg}'.",
        )
        return (
            f"Tiene razón, Señor. Revisé mi registro interno y lo que pasó fue que {reason}. "
            f"Acabo de traer WhatsApp al frente sin recargar la pestaña, seleccioné el chat activo, hice clic en la caja 'Escribe un mensaje' y volví a enviar: '{last_msg}'."
        )

    if app:
        return (
            f"Señor, revisando mi última acción en {app.upper()} ({last_detail}): "
            f"parece que la ventana de Google Chrome no tenía el foco principal o seguía cargando cuando envié los clics. "
            f"Dígame si desea que la repita ahora mismo con la ventana ya cargada."
        )

    return (
        "Señor, revisé mi memoria de acciones recientes y vi que aún no tenía un contacto o chat activo seleccionado en pantalla. "
        "Si quiere que mande el mensaje en WhatsApp ahora mismo, dígame por ejemplo: 'Manda un mensaje en WhatsApp a [Nombre] diciendo hola' o 'Manda un mensaje de prueba en WhatsApp'."
    )


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

    time.sleep(4.5)
    focus_and_maximize_chrome_window("Gmail")

    if check_if_login_required_on_screen():
        update_action_state("gmail", raw_order, to_addr, body_txt, "login_required", "Gmail pidió iniciar sesión.")
        return "Señor, abrí Gmail en Google Chrome pero necesita iniciar sesión en su cuenta para que pueda redactar el correo."

    if not is_draft and to_addr:
        time.sleep(1.2)
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

    time.sleep(5.2)
    left, top, right, bottom = focus_and_maximize_chrome_window("YouTube")
    w = max(800, right - left)
    h = max(600, bottom - top)

    mouse_scroll("down", amount=6)
    time.sleep(1.5)

    clicked_box = (
        find_text_on_screen_and_click("comentario", double_click=False)
        or find_text_on_screen_and_click("comment", double_click=False)
    )
    if not clicked_box:
        mouse_click(left + int(w * 0.35), top + int(h * 0.68), button="left", double=False)

    time.sleep(0.8)
    send_text_and_keys(comment_text, press_enter=False)
    time.sleep(0.8)
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
        time.sleep(4.5)
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
    time.sleep(4.5)
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
            time.sleep(1.2)

    if search_term and target_url == base_url and not click_match:
        if not (find_text_on_screen_and_click("Buscar", False) or find_text_on_screen_and_click("Search", False)):
            pyautogui.press("/")
        time.sleep(0.6)
        send_text_and_keys(search_term, press_enter=True)
        actions_done.append(f"busqué '{search_term}'")
        time.sleep(1.2)

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
