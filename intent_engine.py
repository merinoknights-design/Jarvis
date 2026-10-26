import re
from typing import Dict, Any, Optional

# Estado de contexto reciente para que Jarvis recuerde de qué venía hablando el usuario
SESSION_CONTEXT = {
    "last_intent": None,
    "last_app": None,
    "last_song": None,
    "last_topic": None,
}


def clean_wake_words(text: str) -> str:
    cleaned = re.sub(
        r"^(hey\s+jarvis|oye\s+jarvis|hola\s+jarvis|jarvis|por\s+favor\s+jarvis)[\s,\.:!]*",
        "",
        text.strip(),
        flags=re.IGNORECASE,
    ).strip()
    cleaned = re.sub(r"[\s,]*(por\s+favor|jarvis|gracias)$", "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned or text.strip()


def classify_user_intent(raw_message: str) -> Dict[str, Any]:
    """
    Motor de Razonamiento con Criterio Propio y Memoria de Conversación:
    Diferencia con precisión cuándo el usuario pide reproducir música real vs. cuándo está
    dando órdenes de mensajería (WhatsApp/Gmail), corrigiendo un error o conversando de un tema.
    """
    cleaned = clean_wake_words(raw_message)
    low = cleaned.lower()

    scores = {
        "PLAY_SPOTIFY": 0,
        "PLAY_YOUTUBE": 0,
        "MEDIA_CONTROL": 0,
        "UI_CLICK_SCROLL_TYPE": 0,
        "CAD_MODEL_OR_ASM": 0,
        "OPEN_APP_OR_FOLDER": 0,
        "GITHUB_SYNC": 0,
        "CONVERSATION_OR_QUESTION": 0,
    }

    # Palabras que indican que el usuario está hablando de un chat, mensaje, error o conversación (NUNCA de una canción)
    non_music_context_words = [
        "whatsapp", "mensaje", "chat", "david", "correo", "gmail", "borrador",
        "comentario", "comenta", "prueba", "escribe", "escríbele", "escribele",
        "dile", "manda", "mandar", "mándale", "mandale", "envía", "envia", "enviar",
        "conversación", "conversacion", "tema de conversación", "tema de conversacion",
        "hablando", "error", "veo", "encontró", "encontro", "encuentra", "buscó", "busco",
        "rectifica", "rectifícalo", "rectificalo", "criterio", "memoria", "preguntando",
        "solid edge", "boceto", "extrusión", "protrusión", "redondeo", "mm", "pieza",
        "canva", "drive", "outlook", "instagram", "discord",
    ]
    has_non_music_context = any(w in low for w in non_music_context_words)

    # =========================================================================
    # CICLO 1: EVALUACIÓN DE REPRODUCCIÓN DE MÚSICA Y CANCIONES (SPOTIFY / YOUTUBE)
    # =========================================================================
    music_verbs_pattern = r"^(pon|ponme|ponte|coloca|colócame|reproduce|reproducir|suena|haz\s+sonar|escuchar|quiero\s+escuchar|vamos\s+a\s+escuchar|toca|play)\b"
    # Nota: NUNCA incluir palabras ambiguas como "tema" (usado en "tema de conversación")
    music_nouns = ["canción", "cancion", "música", "musica", "rolita", "álbum", "album", "playlist", "spotify"]
    question_starters = [
        "qué es", "que es", "qué significa", "que significa", "por qué", "por que",
        "cómo se", "como se", "cuándo", "cuando", "quién es", "quien es",
        "definición de", "definicion de", "explícame", "explicame", "otra vez", "todavía", "todavia",
        "necesito que", "no veo", "no lo", "dijo que",
    ]

    is_question_or_complaint = any(low.startswith(q) for q in question_starters) or ("?" in low and not re.search(music_verbs_pattern, low))

    if not is_question_or_complaint and not has_non_music_context:
        if re.search(music_verbs_pattern, low):
            if "youtube" in low:
                scores["PLAY_YOUTUBE"] += 95
            else:
                scores["PLAY_SPOTIFY"] += 90

        for mn in music_nouns:
            if mn in low:
                if "youtube" in low:
                    scores["PLAY_YOUTUBE"] += 60
                else:
                    scores["PLAY_SPOTIFY"] += 60

    # Si pide explícitamente Spotify con verbo de reproducción ("abre spotify y pon X" o "reproduce X en spotify")
    if "spotify" in low and any(v in low for v in ["pon ", "ponme ", "reproduce ", "escuchar ", "coloca "]):
        scores["PLAY_SPOTIFY"] += 100

    # =========================================================================
    # CICLO 2: EVALUACIÓN DE CONTROL DE INTERFAZ (CLICS, SCROLL, TECLADO)
    # =========================================================================
    if re.search(r"\b(doble\s+clic|clic\s+derecho|haz\s+clic|da\s+clic|dale\s+clic|clic\s+en|click\s+en|oprime|presiona\s+el\s+bot[oó]n)\b", low):
        scores["UI_CLICK_SCROLL_TYPE"] += 100
    if any(w in low for w in ["scroll", "baja la página", "sube la página", "desplaza abajo", "desplaza arriba"]):
        scores["UI_CLICK_SCROLL_TYPE"] += 100
    if re.search(r"^(escribe|escribir|comenta|comentar|redacta|digita)\b", low) and "whatsapp" not in low and "david" not in low:
        scores["UI_CLICK_SCROLL_TYPE"] += 100

    # =========================================================================
    # CICLO 3: EVALUACIÓN DE CONTROLES MULTIMEDIA (PAUSA, SIGUIENTE, VOLUMEN)
    # =========================================================================
    if any(w in low for w in [
        "pausa la música", "pausa la musica", "pausar música", "reanuda la música", "siguiente canción",
        "siguiente cancion", "cambia de canción", "canción anterior", "sube el volumen",
        "baja el volumen", "silencia el audio", "mutea"
    ]):
        scores["MEDIA_CONTROL"] += 100

    # =========================================================================
    # CICLO 4: EVALUACIÓN DE INGENIERÍA CAD 3D (SOLID EDGE 2026)
    # =========================================================================
    cad_keywords = ["solid edge", "solidedge", "brida", "soporte en l", "eje escalonado", "ensambla", "ensamblaje", "modela el plano", "pasa el pdf a solid edge"]
    if any(ck in low for ck in cad_keywords):
        scores["CAD_MODEL_OR_ASM"] += 100
    elif any(v in low for v in ["modela ", "crea una pieza", "crea una placa", "crea un eje", "crea un cilindro", "diseña una pieza"]) and any(d in low for d in ["mm", "diámetro", "diametro", "espesor", "agujero", "redondeo"]):
        scores["CAD_MODEL_OR_ASM"] += 95

    # =========================================================================
    # CICLO 5: EVALUACIÓN DE Decisión Final por Puntaje Máximo
    # =========================================================================
    best_intent = max(scores, key=scores.get)
    best_score = scores[best_intent]

    if best_score < 50:
        best_intent = "CONVERSATION_OR_QUESTION"

    song_name = ""
    if best_intent in ["PLAY_SPOTIFY", "PLAY_YOUTUBE"]:
        temp = cleaned
        temp = re.sub(
            r"^(?:abre\s+spotify\s+y\s+|entra\s+a\s+spotify\s+y\s+|en\s+spotify\s+)?(?:ponme|ponte|pon|coloca|colócame|reproduce|reproducir|haz\s+sonar|suena|quiero\s+escuchar|escuchar|toca|play|busca)\s+",
            "",
            temp,
            flags=re.IGNORECASE,
        ).strip()
        temp = re.sub(
            r"^(?:la\s+canci[oó]n|el\s+tema|la\s+pista|la\s+m[uú]sica|el\s+video|algo\s+de)\s+(?:llamad[oa]\s+|que\s+se\s+llama\s+)?",
            "",
            temp,
            flags=re.IGNORECASE,
        ).strip()
        temp = re.sub(r"\s+(?:en\s+spotify|por\s+spotify|de\s+spotify|en\s+youtube|por\s+favor)$", "", temp, flags=re.IGNORECASE).strip()
        song_name = temp.strip("'\"")

    SESSION_CONTEXT["last_intent"] = best_intent
    if song_name:
        SESSION_CONTEXT["last_song"] = song_name

    return {
        "intent": best_intent,
        "confidence": best_score,
        "cleaned_text": cleaned,
        "song_query": song_name,
        "scores": scores,
    }
