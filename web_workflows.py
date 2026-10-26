import re
import time
import urllib.parse
from typing import Optional, Tuple
import pyautogui

from ui_controller import (
    open_url_in_chrome,
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


def parse_whatsapp_order(raw_order: str) -> Tuple[str, str]:
    """
    Extrae (contacto, mensaje) de cualquier frase natural en español:
    - "manda un mensaje en whatsapp a Juan diciendo hola"
    - "abre whatsapp, entra al perfil de María y manda el mensaje ya llegué"
    - "escríbele a Carlos por whatsapp qué más pues"
    - "manda un whatsapp a Mamá: bendición"
    """
    cleaned = re.sub(r"\b(?:en|por|de|desde)\s+whatsapp(?:\s+web)?\b", "", raw_order, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"^(?:abre\s+whatsapp\s*(?:,\s*|\s+y\s+)?)", "", cleaned, flags=re.IGNORECASE).strip()

    patterns = [
        # 1. "... a [Contacto] diciendo / que diga / con el mensaje / : [Mensaje]"
        r"(?:a|para|al\s+contacto|al\s+perfil\s+de|al\s+chat\s+de|busca\s+a)\s+([^,:]+?)\s+(?:diciendo|que\s+diga|con\s+el\s+mensaje|con\s+el\s+texto|y\s+dile|y\s+m[aá]ndale|y\s+env[ií]ale|y\s+escr[ií]bele|y\s+ponle|[:])\s*(.+)$",
        # 2. "... perfil de [Contacto] y manda/escribe (el mensaje) [Mensaje]"
        r"(?:perfil\s+de|chat\s+de|contacto|busca\s+a|a)\s+([a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\s\+\-]+?)\s+y\s+(?:manda|m[aá]ndale|env[ií]a|env[ií]ale|escribe|escr[ií]bele|pon|ponle)\s+(?:el\s+mensaje\s+|un\s+mensaje\s+)?(?:diciendo\s+|que\s+diga\s+)?(.+)$",
        # 3. "diciendo [Mensaje] a [Contacto]"
        r"(?:diciendo|que\s+diga|mensaje)\s+['\"]?(.+?)['\"]?\s+(?:a|para)\s+([a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\s\+\-]+)$",
        # 4. "manda un mensaje a [Contacto] [Mensaje]" (1 a 3 palabras de contacto seguidas del mensaje)
        r"(?:manda|mandar|env[ií]a|enviar|escribe|escr[ií]bele|m[aá]ndale)\s+(?:un\s+mensaje\s+|un\s+whatsapp\s+|el\s+mensaje\s+)?(?:a|para)\s+([a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\+\-]+(?:\s+[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\+\-]+)?)\s+(.+)$",
    ]

    for idx, pat in enumerate(patterns):
        m = re.search(pat, cleaned, re.IGNORECASE)
        if m:
            if idx == 2:
                msg, contact = m.group(1).strip(), m.group(2).strip()
            else:
                contact, msg = m.group(1).strip(), m.group(2).strip()
            contact = re.sub(r"\b(?:en|por)\s+whatsapp\b", "", contact, flags=re.IGNORECASE).strip(" ,:.'\"")
            msg = msg.strip(" '\"")
            if contact and msg:
                return contact, msg

    # Si solo mencionó el contacto sin cuerpo de mensaje (ej. "manda un mensaje en whatsapp a Juan")
    m_only_contact = re.search(r"(?:a|para|al\s+perfil\s+de|busca\s+a)\s+([a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\s\+\-]+)$", cleaned, re.IGNORECASE)
    if m_only_contact:
        c = m_only_contact.group(1).strip(" ,:.'\"")
        return c, "Hola"

    return "", ""


def workflow_gmail_compose_or_send(raw_order: str) -> str:
    """
    Flujo autónomo de principio a fin en Gmail:
    1. Extrae destinatario (si lo hay), asunto y cuerpo del mensaje (o genera un borrador inteligente según el tema pedido).
    2. Abre directamente el editor de redacción de Gmail en Chrome (?view=cm&fs=1...).
    3. Verifica inicio de sesión; si pide enviar con destinatario lo envía, si es borrador lo deja redactado y guardado en Borradores.
    """
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
        return "Señor, abrí Gmail en Google Chrome pero necesita iniciar sesión en su cuenta para que pueda redactar el correo."

    if not is_draft and to_addr:
        time.sleep(1.2)
        clicked = click_ui_element_by_uia_or_ocr("Enviar", double_click=False, right_click=False)
        if not clicked:
            pyautogui.hotkey("ctrl", "enter")
        return f"Ya terminé la acción, Señor: Abrí Gmail, redacté el correo para {to_addr} con asunto '{subject_txt}' y lo envié."

    return f"Ya terminé la acción, Señor: Abrí Gmail y dejé su correo redactado y guardado en Borradores con asunto '{subject_txt}'."


def workflow_whatsapp_send_message(raw_order: str) -> str:
    """
    Flujo autónomo de principio a fin en WhatsApp Web (a prueba de fallos):
    1. Extrae contacto y mensaje de cualquier frase natural.
    2. Abre WhatsApp Web en Google Chrome y trae la ventana de Chrome al frente maximizada.
    3. Enfoca el buscador de contactos (combinando atajo nativo Ctrl+Alt+/, UIA y coordenadas del panel izquierdo).
    4. Escribe el contacto, entra a su chat, enfoca la barra de mensaje inferior, pega el texto y presiona Enter.
    """
    contact, message_text = parse_whatsapp_order(raw_order)

    if not contact:
        open_url_in_chrome("https://web.whatsapp.com")
        time.sleep(4.5)
        focus_and_maximize_chrome_window("WhatsApp")
        return "WhatsApp Web abierto en su Google Chrome, Señor."

    digits = re.sub(r"\D", "", contact)
    if len(digits) >= 8:
        url = f"https://web.whatsapp.com/send?phone={digits}&text={urllib.parse.quote(message_text)}"
        open_url_in_chrome(url)
        time.sleep(7.5)
        focus_and_maximize_chrome_window("WhatsApp")
        time.sleep(0.5)
        pyautogui.press("enter")
        return f"Ya terminé la acción, Señor: Abrí WhatsApp, entré al chat de {contact} y envié el mensaje '{message_text}'."

    open_url_in_chrome("https://web.whatsapp.com")
    time.sleep(7.0)
    left, top, right, bottom = focus_and_maximize_chrome_window("WhatsApp")
    w = max(800, right - left)
    h = max(600, bottom - top)

    # Paso 1: Enfocar la barra de búsqueda de chats en WhatsApp Web
    # Intentar atajo oficial de WhatsApp Web (Ctrl + Alt + /) y clic en la barra de búsqueda izquierda
    search_x = left + int(w * 0.14)
    search_y = top + 168
    mouse_click(search_x, search_y, button="left", double=False)
    time.sleep(0.25)
    pyautogui.hotkey("ctrl", "alt", "/")
    time.sleep(0.35)

    # Limpiar cualquier búsqueda previa, escribir el nombre del contacto y esperar resultados
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    pyautogui.press("backspace")
    time.sleep(0.15)
    send_text_and_keys(contact, press_enter=False)
    time.sleep(1.4)

    # Paso 2: Abrir el primer contacto encontrado (Enter o clic en el primer resultado de la lista izquierda)
    pyautogui.press("enter")
    time.sleep(0.9)

    # Por seguridad, hacer clic también sobre el primer resultado del listado izquierdo (y = top + 285)
    first_result_x = left + int(w * 0.15)
    first_result_y = top + 285
    mouse_click(first_result_x, first_result_y, button="left", double=False)
    time.sleep(0.9)

    # Paso 3: Hacer clic en la caja de texto "Escribe un mensaje" en la parte inferior derecha del chat
    msg_box_x = left + int(w * 0.60)
    msg_box_y = bottom - 62
    mouse_click(msg_box_x, msg_box_y, button="left", double=False)
    time.sleep(0.35)

    # Paso 4: Escribir el mensaje y presionar Enter para enviarlo
    send_text_and_keys(message_text, press_enter=True)
    time.sleep(0.25)
    pyautogui.press("enter")

    return f"Ya terminé la acción, Señor: Abrí WhatsApp, busqué a '{contact}', entré a su perfil y envié el mensaje '{message_text}'."


def workflow_youtube_watch_and_comment(raw_order: str) -> str:
    """
    Flujo autónomo de principio a fin en YouTube:
    1. Busca y abre el video directo en Chrome.
    2. Si el usuario pidió escribir un comentario, hace scroll a la caja de comentarios,
       hace clic, escribe el comentario y oprime Comentar.
    """
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

    return f"Ya terminé la acción, Señor: Abrí el video '{video_part}' en YouTube, bajé a los comentarios y publiqué '{comment_text}'."


def workflow_generic_webapp_multistep(app_label: str, base_url: str, raw_order: str) -> str:
    """
    Flujo autónomo unificado para Canva, Drive, Outlook, Instagram, Netflix, Discord o cualquier web.
    """
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

    return f"Ya terminé la acción, Señor: {', '.join(actions_done)}."
