# Arquitectura de Jarvis (verificada el 2026-10-28)

## Contenido
1. Dónde vive y cómo arranca
2. Flujo de una orden
3. Órdenes del chat que tocan Solid Edge (y sus trampas)
4. Endpoints HTTP
5. Módulos CAD y para qué sirve cada uno
6. Carpetas de entrada y salida
7. Reiniciar el servidor
8. Configuración y respaldos
9. Publicar una actualización

---

## 1. Dónde vive y cómo arranca

- Código: `C:\Jarvis\`. **No es un repositorio git** (hay `.gitignore` y `git_sync.py`, pero no hay `.git`).
- Python: `C:\Jarvis\venv\Scripts\python.exe`, CPython 3.11 de 64 bits gestionado por `uv`, con pywin32, FastAPI, uvicorn, httpx, pypdf, rapidocr, pyautogui y pywinauto (`requirements.txt`).
- Solid Edge 2026 (versión interna 226.00): `<SE>\Program\Edge.exe`, ProgID `SolidEdge.Application`. El nombre del proceso es `Edge.exe`; no lo confundas con el navegador Microsoft Edge (`msedge.exe`).
- Arranque normal: `iniciar_jarvis.bat` → `JarvisApp.pyw`, que levanta Ollama si existe, lanza `server.py` sin ventana y abre la interfaz en Chrome como aplicación (`--app=http://127.0.0.1:7777`).
- Servidor: FastAPI + uvicorn en `127.0.0.1:7777`; la interfaz es `ui/index.html`.

## 2. Flujo de una orden

```
POST /api/chat {message}
  └─ ¿la orden trae varias tareas? (" y además ", " y luego ", "; ", " y pon/abre/crea/modela")
       → se parte y cada parte va al cerebro; de la 2ª en adelante, en segundo plano
  └─ instant_conversational_and_action_brain(msg)      ← enrutado por PALABRAS CLAVE, en orden
       └─ intent_engine.classify_user_intent (puntúa música, apps, CAD, conversación)
       └─ primer atajo que coincide → ejecuta → responde
  └─ si ningún atajo coincide → conversación con Gemini (si hay clave) u Ollama local
```

Las tareas largas pasan por `task_manager.execute_smart_task` (un hilo). Con `notify_on_complete=True`, el resultado se publica en `/api/notifications`, un buzón **de un solo lector** que se vacía al leerlo.

## 3. Órdenes del chat que tocan Solid Edge

Se evalúan **en este orden** dentro de `instant_conversational_and_action_brain` (`server.py`):

| # | Disparador (contiene…) | Qué hace | Trampas |
|---|---|---|---|
| 0 | "sí", "si ", "dale", "hazlo", "sigue", "ok hazlo", "confirmo"… **y** hay planos pendientes (`pending_cad_plans`) | Modela cada plano pendiente con `execute_universal_cad_plan` → `Documents\Proyectos_SolidEdge\<nombre>.par` | Un "sí" o "sigue" casual, con un plano subido antes, lanza el modelado. |
| 1 | "cardan"/"cardán" + verbo (ensambla, arma, fase N, siguiente, sigue, completo, prueba de giro, estado, verifica) | `cardan_orden()`: ejecuta `cardan\ensamblar_cardan.py --fase N` o `prueba_giro.py` en segundo plano | Sin verbo (p. ej. "¿qué es un cardán?") no hace nada y va a la conversación. |
| 2 | "parcial", "todas las piezas", "motor de pistón", "ensamble del motor", pistón+biela | `generate_full_piston_engine_project()` (proyecto fijo de 3 piezas + ensamble + ZIP) | Proyecto de un parcial viejo con medidas fijas; su ensamble no tiene relaciones reales. |
| 3 | "guía de modelamiento", "pieza_mecanica", R150+R130 | `build_pieza_mecanica_piston()` (pieza fija) | Pieza codificada a mano para una guía concreta. |
| 4 | "ensambla las piezas", "ensamblar piezas", "crea un ensamblaje" | Si no hay ≥2 piezas recientes, **pregunta** cuáles (parche 2026-10-28); si las hay, las inserta en fila **sin relaciones** | No es un ensamble funcional; lo dice en la respuesta. |
| 5 | "modela el plano", "pasa el pdf a solid edge", "modela este pdf", "construye el plano" (tras subir un archivo) | Texto del archivo → `parse_natural_language_or_drawing_to_cad_plan` (regex) → plantilla | El regex toma los primeros números que encuentra y rellena huecos con valores por defecto. **No sirve para planos reales.** |
| 2.5 | "abre/abrir/inicia/lanza" + ("solid edge" o una ruta .par/.asm/.psm/.dft) y sin verbo de crear | Tarea `abrir` de la API de agentes: abre sin crear ni guardar (JRV-06) | — |
| 6 | Verbo de crear ("modela", "crea", "diseña", "construye"…) + "solid edge", o "modela/crea una pieza/brida/eje…" + "mm/diámetro/largo/agujero…" | `generate_custom_solid_part(texto)` en segundo plano (o el conjunto "v8") | Plantillas rígidas con medidas por defecto: no la uses para planos reales. Desde JRV-06 ya no basta con mencionar "solid edge". |

Las rutas de Gmail, WhatsApp, YouTube, Spotify, clics por OCR, etc. vienen después y no tocan CAD.

**Subida de archivos** (`/api/upload`, botón 📎): el archivo se copia a `C:\Jarvis\uploads\` y se analiza. Un `.par`/`.asm`/`.psm`/`.dft` **se abre en Solid Edge** para contar sus operaciones (y queda abierto). Un `.par` o `.step` pasa a "piezas recientes". Un PDF o imagen se intenta convertir en plan con Gemini (y si no, con OCR + regex) y queda **pendiente**, a la espera de un "sí".

## 4. Endpoints HTTP

| Método y ruta | Uso |
|---|---|
| `GET /` | Interfaz. |
| `GET /api/agente/acciones` · `POST /api/agente/ejecutar` · `GET /api/agente/tarea/{id}` · `GET /api/agente/tareas` | **API de agentes** (JRV-01/02, 2026-10-28): órdenes en JSON, tareas consultables. Ver SKILL.md y `api_jarvis.md` §6. |
| `POST /api/chat` `{"message": str, "use_search": bool}` | Orden o conversación. Devuelve `{"reply", "tool_used"}`. |
| `POST /api/upload` (multipart `file`, `prompt`) · `POST /api/upload_multiple` (`files`) | Subir archivos. |
| `POST /api/cad/model_pending` | Modela los planos pendientes. |
| `GET /api/notifications` | Resultados de tareas en segundo plano (**se vacía al leer**). |
| `GET /api/status` · `GET /api/telemetry` | Estado y telemetría (CPU, RAM, batería). |
| `POST /api/reset` | Borra el historial de conversación. |
| `POST /api/shutdown` | Apaga el servidor. |
| `POST /api/tts` · `POST /api/transcribe` · `GET/POST /api/gemini/config` | Voz y clave de Gemini. |

## 5. Módulos CAD

| Archivo | Para qué | Estado |
|---|---|---|
| `se_com_seguro.py` | **Capa COM segura** (parche 2026-10-28): conectar sin matar Edge.exe, `reintentar` cuando SE está ocupado, `guardar_nuevo`/`ruta_libre`, `quitar_fijo`, `describir` caras, `matriz`, `estado_ensamble`, `Bitacora`, `huellas`. | ✅ base de todo lo nuevo |
| `cardan\ensamblar_cardan.py` | Receta del Cardán por fases 1–5 (geometría por reglas, preposicionado, validación y verificación). Clases reutilizables: `Geo` (bridas, horquilla, cruz, perno, tuerca), `Pose`, `Ensamble` (coincidir, alinear_eje, receta_B, receta_C, revisar). | ✅ probado |
| `cardan\prueba_giro.py` | Prueba cinemática: gira la entrada por pasos y verifica la cadena; cierra **sin guardar**. | ✅ probado |
| `cardan\inspeccionar_piezas.py` | Vuelca las caras de cada pieza a `cardan\inspeccion\<pieza>.json` (ensamble temporal sin guardar). | ✅ |
| `cad_atomic_lib.py` | Primitivas de pieza: documento ordenado, boceto en plano 1/2/3, líneas, círculos, arcos, cerrar perfil, protrusión, vaciado, vaciado por revolución, redondeos por filtro de aristas, estado de operación, propiedades físicas. | ⚠️ útil; `get_model_physical_properties` lee mal la caja envolvente |
| `cad_engine.py` | Plantillas de pieza (`build_revolved_part`, `build_flange_coupling_part`, `build_prismatic_machined_part`, pistón), parser regex y ensamble genérico sin relaciones. | ⚠️ plantillas rígidas |
| `universal_cad_builder.py` | Constructor de pieza ordenada a partir de una lista de operaciones. | ⚠️ ligado al proyecto del pistón |
| `cad_validator.py` | Salud del modelo (estados de operación), verificación contra el plano, exportación STEP/PNG. | ⚠️ caja envolvente siempre 0 (lee la lista y no el retorno) |
| `file_analyzer.py` | Análisis de archivos subidos; Gemini para planos. | ⚠️ JSON del prompt mal formado; nombres de modelo y tiempo de espera de 8 s sin verificar |
| `final_state_manager.py` | Presentación final (vista isométrica, traer SE al frente), guardar sin cerrar. | — |
| `build_*`, `test_*`, `verify_*`, `regression_test_suite.py` | Scripts de proyectos anteriores (pistón, brazo). | Referencia histórica |
| `task_manager.py` | Hilos de tareas y buzón de notificaciones (parche: los errores ya no se pierden). | ✅ |
| `intent_engine.py` | Clasificador de intención por puntuación de palabras. | — |

## 6. Carpetas

| Qué | Dónde |
|---|---|
| Piezas de entrada del Cardán | `%USERPROFILE%\Downloads\CAD Cardan\` (8 `.par` + `PLANO.pdf`) |
| Salidas de Jarvis (`PROJECTS_ROOT`) | `%USERPROFILE%\Documents\Proyectos_SolidEdge\` → `Cardan\`, `Piezas_Personalizadas\`, `Desde_Planos_PDF\`, `Ensamblajes\` |
| Cardán oficial | `...\Proyectos_SolidEdge\Cardan\` → `Cardan.asm`, `bitacora_cardan.csv`, `cardan_estado.json`, `verificacion_final.json`, `prueba_giro.json` |
| Archivos subidos | `C:\Jarvis\uploads\` |
| Respaldos | `C:\Jarvis_respaldos\<fecha>_<tema>\` |
| Inspección de caras | `C:\Jarvis\cardan\inspeccion\` · huellas de `.par`: `C:\Jarvis\cardan\huellas_par_ANTES.csv` |

## 7. Reiniciar el servidor (tras cambiar código)

```powershell
$old = (Get-NetTCPConnection -LocalPort 7777 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1).OwningProcess
if ($old) { Stop-Process -Id $old -Force; Start-Sleep -Milliseconds 800 }
Start-Process -FilePath "C:\Jarvis\venv\Scripts\python.exe" -ArgumentList "C:\Jarvis\server.py" -WorkingDirectory "C:\Jarvis" -WindowStyle Hidden
# esperar a que responda
for ($i=0; $i -lt 40; $i++) { try { if ((Invoke-WebRequest -UseBasicParsing http://127.0.0.1:7777/api/status -TimeoutSec 2).StatusCode -eq 200) { "OK"; break } } catch {}; Start-Sleep -Milliseconds 500 }
```

Antes de reiniciar, compila: `python -m py_compile server.py` (y los módulos tocados). La ventana de Jarvis del usuario se reconecta sola.

## 8. Configuración y respaldos

- `config\jarvis_cad_config.json`: unidades mm, modo ordenado, `cerrar_al_terminar: false`, `modo_aprobacion: auto`, reintentos 3, tolerancias.
- `config\mcp_config.json`: servidores MCP heredados de otra máquina (rutas `C:\Users\User\…` que no existen aquí). La clave de Brave vive en `.env` desde JRV-61; la vieja sigue en el historial público de git, así que hay que cambiarla.
- Respaldo previo al blindaje: `C:\Jarvis_respaldos\2026-10-28_pre_blindaje\`.
- La orden "actualízate" descarga `github.com/merinoknights-design/Jarvis` aparte y solo compara (JRV-60); en versiones anteriores a este parche lo descomprimía **encima** de `C:\Jarvis`. "Sube actualización" hace `git add .` y push a `main`: no la uses.

## 9. Publicar una actualización

El repositorio `merinoknights-design/Jarvis` es **público** y su dueño es el autor original. Todo lo que se suba lo puede ver cualquiera.

1. Haz los cambios en `C:\Jarvis` y pasa la regresión.
2. Clona el repositorio en una carpeta temporal nueva y crea una rama `actualizacion-AAAA-MM-DD` sobre `main`.
3. Empaqueta: `python -I -X utf8 C:\Jarvis\actualizacion_fuente\empaquetar.py <clon> AAAA-MM-DD`. Copia lo que cambió, quita los datos personales de las habilidades, escribe el manifiesto y **falla si queda un dato personal, una clave o un binario**. Esa carpeta solo existe en el equipo donde se creó y no se sube, porque contiene la lista de datos a quitar. Actualiza antes en ella `ACTUALIZAR_JARVIS.md`: el nombre de la rama aparece en las instrucciones y en los enlaces.
4. Prueba la instalación en limpio: extrae `main` en una carpeta aparte, descarga la rama con `git clone` y aplica el instalador con `--destino` y `--skills`.
5. Haz un solo commit con el correo privado de GitHub (`-c user.email=<cuenta>@users.noreply.github.com`) y sube **solo la rama**. Pasarla a `main` es decisión del dueño.
6. Comprueba que los enlaces abren y que `main` no cambió.
