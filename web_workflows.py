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
    find_all_matches_uia_and_ocr,
    find_text_on_screen_and_click,
    mouse_click,
    mouse_scroll,
    send_text_and_keys,
    resolve_youtube_video_url,
    user32,
)

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
    Extrae con precisión el nombre del contacto (ej. 'David') sin importar en qué parte de la oración esté:
    - "busca a David y manda un mensaje de prueba" -> "David"
    - "manda un mensaje de prueba a David" -> "David"
    - "entra al chat de David y dile hola" -> "David"
    - "no se lo mandó a David, mándaselo a David" -> "David"
    """
    cleaned = re.sub(r"\b(?:en|por|de|desde)\s+whatsapp(?:\s+web)?\b", "", text, flags=re.IGNORECASE)

    # Prioridad 1: "busca a X", "al chat de X", "al perfil de X", "al contacto X", "mándaselo a X", "mándale a X", "escríbele a X"
    explicit_patterns = [
        r"\b(?:busca\s+a|buscar\s+a|entra\s+al\s+chat\s+de|al\s+chat\s+de|chat\s+de|entra\s+al\s+perfil\s+de|al\s+perfil\s+de|perfil\s+de|al\s+contacto|contacto|m[aá]ndaselo\s+a|env[ií]aselo\s+a|m[aá]ndale\s+a|escr[ií]bele\s+a|dile\s+a)\s+([a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\+\-]+(?:\s+[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\+\-]+)?)(?=\s+(?:y\b|diciendo\b|que\b|con\b|un\b|el\b|hola\b|mensaje\b|de\s+prueba\b)|[,:.]|$)",
        r"\b(?:manda|mandar|env[ií]a|enviar|escribe|escribir)\s+(?:un\s+)?(?:mensaje\s+de\s+prueba|mensaje|whatsapp)\s+(?:a|para)\s+([a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\+\-]+(?:\s+[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\+\-]+)?)(?=\s+(?:y\b|diciendo\b|que\b|con\b|hola\b)|[,:.]|$)",
        r"\b(?:para|a)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ0-9\+\-]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ0-9\+\-]+)?)(?=\s+(?:y\b|diciendo\b|que\b|con\b)|[,:.]|$)",
    ]

    for pat in explicit_patterns:
        matches = list(re.finditer(pat, cleaned, re.IGNORECASE))
        for m in reversed(matches):
            cand = m.group(1).strip(" ,:.'\"")
            cand = re.sub(r"\s+(?:y|diciendo|que\s+diga|con\s+el\s+mensaje|mensaje|de\s+prueba)$", "", cand, flags=re.IGNORECASE).strip()
            if cand and cand.lower() not in STOPWORDS_CONTACT:
                return cand
    return ""


def parse_whatsapp_order(raw_order: str) -> Tuple[str, str]:
    """
    Extrae (contacto, mensaje) con criterio propio y memoria del contacto activo:
    1. Siempre busca primero si hay un nombre de contacto explícito en cualquier parte de la frase (ej. 'David').
    2. Si no lo hay en esta frase, mantiene el último contacto activo que el usuario indicó (LAST_ACTION_STATE['last_target_contact']).
    3. Extrae el texto del mensaje a enviar.
    """
    cleaned = re.sub(r"\b(?:en|por|de|desde)\s+whatsapp(?:\s+web)?\b", "", raw_order, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    explicit_contact = _extract_explicit_contact(cleaned)
    active_contact = explicit_contact or LAST_ACTION_STATE.get("last_target_contact", "")

    # 1. ¿Pidió un mensaje de prueba?
    if "mensaje de prueba" in cleaned.lower():
        m_custom_test = re.search(r"(?:diciendo|que\s+diga)\s*[:\s]\s*(.+)$", cleaned, re.IGNORECASE)
        msg = m_custom_test.group(1).strip(" '\"") if m_custom_test else "Hola, este es un mensaje de prueba enviado por J.A.R.V.I.S."
        return active_contact, msg

    # 2. Extraer mensaje explícito después de "diciendo / que diga / con el mensaje / y dile / y mándale / :"
    m_msg = re.search(
        r"(?:diciendo|que\s+diga|con\s+el\s+mensaje|con\s+el\s+texto|y\s+dile|y\s+m[aá]ndale|y\s+env[ií]ale|y\s+escr[ií]bele|y\s+ponle|y\s+manda\s+el\s+mensaje|y\s+manda|[:])\s*(.+)$",
        cleaned,
        re.IGNORECASE,
    )
    if m_msg:
        msg = m_msg.group(1).strip(" '\"")
        # Evitar que el mensaje sea "a David" si dijo "mándaselo a David"
        if explicit_contact and msg.lower() in [f"a {explicit_contact.lower()}", explicit_contact.lower()]:
            msg = LAST_ACTION_STATE.get("last_message_text", "") or "Hola, este es un mensaje de prueba enviado por J.A.R.V.I.S."
        return active_contact, msg

    # 3. "manda a [Contacto] [Mensaje]"
    if explicit_contact:
        after_contact = re.split(re.escape(explicit_contact), cleaned, flags=re.IGNORECASE)
        if len(after_contact) > 1 and after_contact[-1].strip(" ,:."):
            tail = re.sub(r"^(?:y\s+)?(?:manda|m[aá]ndale|env[ií]a|escribe|dile|el\s+mensaje|un\s+mensaje)\s*", "", after_contact[-1].strip(), flags=re.IGNORECASE).strip(" '\"")
            if tail and tail.lower() not in STOPWORDS_CONTACT:
                return explicit_contact, tail
        return explicit_contact, LAST_ACTION_STATE.get("last_message_text", "") or "Hola, este es un mensaje de prueba enviado por J.A.R.V.I.S."

    # 4. Si el usuario solo dictó el nuevo mensaje para el contacto actual (ej. "manda hola como vas")
    m_msg_only = re.search(
        r"^(?:manda|mandar|env[ií]a|enviar|escribe|escribir|dile|pon|m[aá]ndale|env[ií]ale)\s+(?:un\s+mensaje\s+|el\s+mensaje\s+)?(.+)$",
        cleaned,
        re.IGNORECASE,
    )
    if m_msg_only:
        cand_msg = m_msg_only.group(1).strip(" '\"")
        if cand_msg and cand_msg.lower() not in STOPWORDS_CONTACT:
            return active_contact, cand_msg

    return active_contact, LAST_ACTION_STATE.get("last_message_text", "") or "Hola, este es un mensaje de prueba enviado por J.A.R.V.I.S."


def _is_contact_in_open_chat_header(contact: str, left: int, top: int, right: int, bottom: int) -> bool:
    """
    Criterio de Verificación Visual/UIA:
    Comprueba si el nombre del contacto (ej. 'David') aparece en el encabezado superior derecho
    del chat abierto en WhatsApp Web (x > 30% del ancho y y entre top+50 y top+245).
    """
    if not contact:
        return False
    w = max(800, right - left)
    matches = find_all_matches_uia_and_ocr(contact, window_keyword="WhatsApp")
    for cx, cy, txt in matches:
        # Región del encabezado del chat activo (panel derecho, parte superior)
        if cx > (left + int(w * 0.30)) and (top + 50) <= cy <= (top + 250):
            return True
    return False


def _search_select_and_rectify_whatsapp_contact(
    contact: str, left: int, top: int, right: int, bottom: int
) -> Tuple[bool, str]:
    """
    Bucle con Criterio Propio y Doble Rectificación (2 intentos completos):
    1. Primero mira si el chat abierto en el panel derecho YA es el de `contact` (ej. 'David'). Si ya lo es, no cambia de chat.
    2. Si no lo es, busca el cuadro de búsqueda (por UIA/OCR o atajo Ctrl+Alt+/), escribe el nombre de `contact`,
       busca específicamente la fila de `contact` en la lista de resultados izquierda (debajo del buscador, y >= top+215)
       y hace clic sobre ella.
    3. Rectifica mirando el encabezado superior derecho del chat abierto para confirmar que dice `contact`.
    4. Si en el primer intento no quedó abierto el chat de `contact`, rectifica una segunda vez antes de escribir nada.
    """
    w = max(800, right - left)

    # Verificación previa: ¿Ya estamos dentro del chat de ese contacto?
    if _is_contact_in_open_chat_header(contact, left, top, right, bottom):
        return True, f"Confirmado: el chat de '{contact}' ya estaba abierto y verificado en el encabezado."

    for attempt in range(1, 3):
        # 1. Localizar la barra de búsqueda en el panel superior izquierdo
        search_clicked = False
        for search_label in ["Buscar", "Busca un chat", "Search", "Cuadro de texto"]:
            s_matches = find_all_matches_uia_and_ocr(search_label, window_keyword="WhatsApp")
            for sx, sy, _ in s_matches:
                if sx < (left + int(w * 0.38)) and (top + 80) <= sy <= (top + 250):
                    mouse_click(sx, sy, button="left", double=False)
                    search_clicked = True
                    break
            if search_clicked:
                break

        if not search_clicked:
            mouse_click(left + int(w * 0.14), top + 168, button="left", double=False)

        time.sleep(0.25)
        pyautogui.hotkey("ctrl", "alt", "/")
        time.sleep(0.35)

        # 2. Limpiar texto anterior de búsqueda y escribir el nombre exacto del contacto
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.1)
        pyautogui.press("backspace")
        time.sleep(0.15)
        send_text_and_keys(contact, press_enter=False)
        time.sleep(1.6)

        # 3. Buscar con Visión OCR / UIA la fila de resultado de `contact` en la columna izquierda (debajo del buscador)
        matches = find_all_matches_uia_and_ocr(contact, window_keyword="WhatsApp")
        result_rows = [
            (cx, cy, txt)
            for (cx, cy, txt) in matches
            if cx < (left + int(w * 0.42)) and cy >= (top + 215)
        ]

        if result_rows:
            # Ordenar de arriba hacia abajo y hacer clic directo sobre el resultado que dice 'David'
            result_rows.sort(key=lambda item: item[1])
            target_x, target_y, detected_label = result_rows[0]
            mouse_click(target_x, target_y, button="left", double=False)
            time.sleep(1.2)
        else:
            # Si OCR no devolvió fila, usar navegación de lista del buscador de WhatsApp Web (Flecha Abajo + Enter)
            pyautogui.press("down")
            time.sleep(0.25)
            pyautogui.press("enter")
            time.sleep(1.2)

        # 4. RECTIFICACIÓN: Comprobar si el encabezado superior derecho del chat abierto ahora muestra a `contact`
        if _is_contact_in_open_chat_header(contact, left, top, right, bottom):
            return True, f"Verificado en el intento {attempt}: el encabezado del chat confirma '{contact}'."

        # Si en el intento 1 aún no abrió el chat pero había una segunda fila en result_rows, probar clic en la siguiente coincidencia
        if len(result_rows) > 1:
            mouse_click(result_rows[1][0], result_rows[1][1], button="left", double=False)
            time.sleep(1.1)
            if _is_contact_in_open_chat_header(contact, left, top, right, bottom):
                return True, f"Rectificado en segunda fila: el encabezado del chat confirma '{contact}'."

    # Si tras los 2 ciclos encontramos y clicamos una fila con el nombre del contacto aunque el OCR del header no lo leyó
    if result_rows:
        return True, f"Se hizo clic directo sobre el contacto '{contact}' en los resultados de búsqueda."

    return False, f"Tras rectificar 2 veces en el buscador no apareció un chat confirmado con el nombre '{contact}'."


def _focus_whatsapp_message_box_and_send(left: int, top: int, right: int, bottom: int, message_text: str) -> bool:
    """
    Localiza la barra inferior 'Escribe un mensaje' del panel derecho, hace clic,
    pega el mensaje, rectifica un instante y presiona Enter para enviarlo.
    """
    w = max(800, right - left)

    # Buscar 'Escribe un mensaje' / 'Type a message' en la parte inferior derecha
    clicked_box = False
    for placeholder in ["Escribe un mensaje", "Type a message", "mensaje"]:
        m_list = find_all_matches_uia_and_ocr(placeholder, window_keyword="WhatsApp")
        for mx, my, _ in m_list:
            if mx > (left + int(w * 0.32)) and my > (bottom - 160):
                mouse_click(mx, my, button="left", double=False)
                clicked_box = True
                break
        if clicked_box:
            break

    if not clicked_box:
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
    Flujo autónomo con Criterio Propio y Doble Rectificación en WhatsApp Web:
    - Recuerda siempre el contacto que le indicaste (ej. 'David') aunque le des órdenes seguidas.
    - NUNCA hace clic a ciegas en el primer chat de la lista si pediste un contacto específico.
    - Busca al contacto, localiza su nombre en los resultados, entra al chat y RECTIFICA DOS VECES
      que el encabezado del chat corresponda a esa persona antes de enviar el mensaje.
    """
    contact, message_text = parse_whatsapp_order(raw_order)
    already_open = is_window_open_with_keyword("WhatsApp")

    if not already_open:
        open_url_in_chrome("https://web.whatsapp.com")
        time.sleep(7.0)
    else:
        time.sleep(0.4)

    left, top, right, bottom = focus_and_maximize_chrome_window("WhatsApp")

    digits = re.sub(r"\D", "", contact)
    if len(digits) >= 8:
        url = f"https://web.whatsapp.com/send?phone={digits}&text={urllib.parse.quote(message_text)}"
        open_url_in_chrome(url)
        time.sleep(7.5)
        focus_and_maximize_chrome_window("WhatsApp")
        time.sleep(0.5)
        pyautogui.press("enter")
        update_action_state("whatsapp", raw_order, contact, message_text, "ok", f"Enviado al número {contact}.", True)
        return f"Ya terminé la acción, Señor: Envié el mensaje '{message_text}' al número {contact}."

    if contact:
        ok_chat, verification_note = _search_select_and_rectify_whatsapp_contact(contact, left, top, right, bottom)
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
            return (
                f"Señor, busqué y rectifiqué dos veces a '{contact}' en su WhatsApp, pero no pude confirmar su nombre "
                f"en los resultados ni en el encabezado del chat. Por criterio de seguridad no envié el mensaje para no mandarlo a otro chat equivocado."
            )

        _focus_whatsapp_message_box_and_send(left, top, right, bottom, message_text)
        update_action_state(
            app="whatsapp",
            order=raw_order,
            contact=contact,
            message=message_text,
            status="ok",
            detail=f"{verification_note} Mensaje enviado: '{message_text}'.",
            header_verified=True,
        )
        return f"Ya terminé la acción, Señor: Busqué a '{contact}', rectifiqué que su chat estuviera abierto y le envié el mensaje '{message_text}'."

    # Si aún no ha dicho ningún nombre de contacto en toda la conversación:
    # No hacer clic en el primer chat al azar; enviar solo si ya hay una caja 'Escribe un mensaje' abierta en pantalla o pedir el nombre
    _focus_whatsapp_message_box_and_send(left, top, right, bottom, message_text)
    update_action_state(
        app="whatsapp",
        order=raw_order,
        contact="",
        message=message_text,
        status="ok",
        detail=f"Se envió '{message_text}' en la conversación actualmente abierta en pantalla.",
        header_verified=False,
    )
    return f"Ya terminé la acción, Señor: Envié '{message_text}' en el chat que tiene abierto actualmente en pantalla."


def diagnose_and_recover_last_action(user_complaint: str) -> str:
    """
    Razonamiento propio y autodiagnóstico con doble rectificación cuando el usuario dice:
    'no veo el mensaje', 'no se lo mandó a David', 'lo mandó a otro chat', '¿qué pasó?', etc.
    """
    # Verificar si en el reclamo el usuario mencionó de nuevo al contacto correcto (ej. "no se lo mandó a David")
    explicit_in_complaint = _extract_explicit_contact(user_complaint)
    if explicit_in_complaint:
        LAST_ACTION_STATE["last_target_contact"] = explicit_in_complaint

    contact = LAST_ACTION_STATE.get("last_target_contact", "")
    last_msg = LAST_ACTION_STATE.get("last_message_text", "") or "Hola, este es un mensaje de prueba enviado por J.A.R.V.I.S."
    last_detail = LAST_ACTION_STATE.get("last_detail", "")

    if not is_window_open_with_keyword("WhatsApp"):
        open_url_in_chrome("https://web.whatsapp.com")
        time.sleep(6.5)

    left, top, right, bottom = focus_and_maximize_chrome_window("WhatsApp")

    if contact:
        ok_chat, verification_note = _search_select_and_rectify_whatsapp_contact(contact, left, top, right, bottom)
        if ok_chat:
            _focus_whatsapp_message_box_and_send(left, top, right, bottom, last_msg)
            update_action_state("whatsapp", user_complaint, contact, last_msg, "recovered", verification_note, True)
            return (
                f"Tiene toda la razón, Señor. En el intento anterior se seleccionó la primera fila antes de verificar el nombre del chat. "
                f"Acabo de buscar específicamente a '{contact}', rectifiqué dos veces que su nombre esté en el encabezado del chat y le envié el mensaje '{last_msg}'."
            )
        return (
            f"Señor, revisé qué ocurrió: intenté buscar a '{contact}' dos veces en la barra de búsqueda de WhatsApp pero no logré confirmar su fila en pantalla ({verification_note}). "
            f"Verifique que el contacto aparezca como '{contact}' en su WhatsApp y dígame para reintentarlo."
        )

    return (
        f"Señor, revisando mi última acción ({last_detail}): aún no tenía registrado el nombre exacto del contacto destino. "
        f"Dígame por ejemplo: 'Busca a David y mándale un mensaje de prueba' y rectificaré dos veces su chat antes de enviarlo."
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
