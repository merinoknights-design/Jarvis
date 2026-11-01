# Parches aplicados a Jarvis

Historial de cambios al código de `C:\Jarvis`, del más reciente al más antiguo. Cada parche lleva: fecha · ID del backlog · archivos · respaldo · prueba que lo demuestra. Si un parche se revierte, márcalo `REVERTIDO (fecha, motivo)`; no lo borres.

---

## 2026-11-01 · Portabilidad y primera actualización publicada

**Pedido por el usuario** (2026-11-01): subir los cambios al repositorio del autor original para que su Claude trabaje igual.
**Respaldo previo:** `C:\Jarvis_respaldos\2026-11-01_portable\`.
**Regresión:** 23/23 en `C:\Jarvis` y 23/23 en una copia aislada instalada desde cero con el instalador.

| ID | Qué | Archivos | Prueba |
|---|---|---|---|
| — | Solid Edge se detecta en el registro de Windows, sin rutas fijas | `rutas_se.py` (nuevo), `agente\plano.py`, `agente\receta_pieza.py`, `agente\tornilleria.py`, `firmas_api.py` | En este equipo da su carpeta real; con `JARVIS_SE_RAIZ` falsa, mensaje claro |
| — | Las ayudas en C# se compilan en cada equipo; no se suben binarios | `agente\csharp\compilar.py` (nuevo) | Compiladas desde cero en la copia aislada; los casos de interferencia pasan |
| — | La carpeta del Cardán sale de `JARVIS_CARDAN_RAIZ` en `.env`; recetas de prueba con `%ENSAYOS%`; `correr_todo.py` con rutas relativas; sin nombres propios en el código | `cardan\rutas_cardan.py`, `pruebas\*`, `.env.ejemplo` (nuevo), `.gitignore` | Regresión |
| — | Instalador para otro equipo: ensayo, respaldo, sin pisar cambios propios, repetible, conserva la memoria de las habilidades | `actualizacion_fuente\actualizar_jarvis.py`, `ACTUALIZAR_JARVIS.md`, `empaquetar.py` (privado) | Conflicto, `--resuelto`, repetición y memoria, probados |

**Sin probar:** un equipo con Solid Edge en otra carpeta real (la detección se probó aquí) y en otro idioma.

---

## 2026-11-01 · Barrido de choques durante el giro

**Pedido por el usuario:** "Sí, hazla" (2026-11-01), tras ver que el choque del Cardán dependía de la posición.
**Respaldo previo:** `C:\Jarvis_respaldos\2026-11-01_barrido\` (`correr_todo.py`). `barrido_choques.py` es nuevo. No se tocó el código del servidor, así que no hubo que reiniciarlo.
**Regresión:** `C:\Jarvis\pruebas\correr_todo.py --cardan` → **23/23 OK** (`%TEMP%\jarvis_ensayos\regresion_20261101_090605`).

| ID | Qué | Archivos | Prueba |
|---|---|---|---|
| JRV-32 | Gira la pieza motriz por pasos y corre la interferencia en cada posición, sobre la pose en memoria. Agrupa en tramos: pareja, desde, hasta, pico y máximo; separa choques (≥ umbral), roces (≥ aviso) y esperados; marca lo que no depende del giro (`constante`). Se detiene y lo dice si se rompe una relación, si la pieza deja de girar o si falla la interferencia. Se niega a tocar un ensamble ya abierto. Cierra sin guardar y comprueba la huella | `agente\barrido_choques.py` (nuevo) | Vuelta del Cardán en copia con `--cada 8`: 4 tramos, 33 posiciones, 247 s, tramo que cruza 0° bien unido, huella igual. Con el valor por defecto (5°), en 30°: 0°, 7°, 14°, 21°, 28,1° y 35,2°, igual que el barrido manual de 46 posiciones. Negativas probadas: ensamble abierto, archivo inexistente, pieza inexistente |
| — | Regresión: casos de barrido (constante, negativa y Cardán), `caso(espera_fallo=True)` para pruebas negativas, y copia del Cardán con otro nombre (`Cardan_regresion.asm`) para no abrir un segundo documento con el nombre del que el usuario pueda tener abierto | `pruebas\correr_todo.py` | 23/23 |

**Sin probar:** la vuelta completa con el valor por defecto en la herramienta final (sí en el script de ensayo, con la misma lógica) y su ejecución por la API con la acción `receta`, porque el servidor estaba apagado.

---

## 2026-10-31 · Choques, agujeros con rosca, patrones, tornillería, editar piezas, cotas de revolución

**Pedido por el usuario** (2026-10-31): revisar lo que Jarvis no hacía y ver si se podía implementar: detectar choques (primer filtro; la revisión final es suya), agujeros normalizados y roscados, editar una pieza existente sin rehacerla, cotas para los planos, y explicarle los patrones de operación.
**Respaldo previo:** `C:\Jarvis_respaldos\2026-10-31_choques\` (`acciones.py`, `api_agente.py`, `receta_pieza.py`, `correr_todo.py`). Los demás archivos son nuevos.
**Regresión:** `C:\Jarvis\pruebas\correr_todo.py` → **19/19 OK** (`%TEMP%\jarvis_ensayos\regresion_20261031_080233`).

| ID | Qué | Archivos | Prueba |
|---|---|---|---|
| JRV-24 | **Interferencia por fin funciona.** Interop tipado generado de las type libraries con `TypeLibConverter` de .NET (sin SDK ni tlbimp) y llamada tipada desde C#; Python interpreta el informe: choques reales (≥ umbral, 1 mm³ por defecto), contactos, choques esperados (`--esperado "A.par<>B.par"`), veredicto, y huella del ensamble sin cambios. Acción `interferencia` de la API | `agente\csharp\GenerarInterop.cs`, `agente\csharp\InterferenciaTipada.cs`, `agente\csharp\interop\*.dll` (nuevos), `agente\interferencia.py` (reescrito), `api_agente.py` | Ensamble con choque a propósito → 1 choque; Cardán → 1 choque real pequeño **Fork.par:4 ↔ tuercaM3.par:25 (2,103 mm³)** + 40 solapes perno-tuerca de 2,945 mm³ (rosca modelada, esperados); el ensamble de prueba de relaciones tiene un cruce real eje-brida de 4 542,7 mm³ |
| JRV-15 | Operación `agujero` en recetas: Ø simple o rosca métrica (`"rosca": "M6"`), pasante o ciego; el Ø de taladro sale del menor de `<SE>\Preferences\HOLES.TXT`; un agujero por centro; comprobación de volumen | `agente\receta_pieza.py` | Placa: Ø8, M6 pasante, M5 ciego 10 mm con la rosca guardada en el agujero |
| JRV-15 | Inventario de tornillería de un ensamble: cantidades por archivo, tipo por nombre, designación métrica DEDUCIDA de la geometría (sugerencia), largo, agujeros y roscas de cada pieza | `agente\tornilleria.py` (nuevo) | Cardán → perno M3 ×40, tuerca M3 ×40 |
| JRV-16 | Operación `patron` en recetas: circular (cantidad, centro, ángulo opcional) y rectangular (cantidades y pasos en x/y) sobre las operaciones creadas por otra operación con nombre | `agente\receta_pieza.py` (`op_patron`, `creadas` en `construir`) | Brida: 6×M8 en PCD 90 (−2 602,6 mm³ = 5 copias) y matriz 3×2 de Ø4 (−942,5 mm³ = 5 copias) |
| JRV-17 | Editar una pieza existente: `listar` (cotas de boceto, profundidades, agujeros) y `cambiar` (cotas y profundidades) → guarda como pieza NUEVA, original intacto (huella), no guarda si alguna operación falla | `agente\editar_pieza.py` (nuevo) | Brida: profundidad +2 mm → pieza nueva con más volumen, original sin cambios |
| JRV-54 | Las cotas que crea `receta_pieza` ahora **gobiernan** (`Constraint=True`), y los perfiles de revolución se acotan (Ø simétrico respecto del eje y largos) para que el plano de un eje salga con sus diámetros | `agente\receta_pieza.py` (`_acotar`, `acotar_revolucion`) | Eje escalonado acotado; cambiar una cota mueve la geometría |

**Sigue sin resolverse:** rosca cosmética exterior en pernos (`Threads.Add`/`AddEx` → 0x80020009); motor nativo (JRV-33); explosión oficial con líneas de flujo (espera a la clase); cotas de posición de agujeros/PCD en el plano; chapa (JRV-18, aplazada por el usuario).

---

## 2026-10-30 · Bloques 1–6: piezas, ensambles, movimiento, explosión, planos, calidad

**Aprobado por el usuario:** "continúa con todas las mejoras que están programadas" (2026-10-30).
**Respaldo previo:** `C:\Jarvis_respaldos\2026-10-30_bloque1\` (`server.py` y `cad_engine.py` **reconstruidos** al estado previo porque se editaron antes de respaldar —mismo error que el 28—; `task_manager.py`, `mcp_config.json`, `gemini_brain.py`, `ui_controller.py` respaldados antes de tocarlos). `.gitignore` solo recibió `.env` al final.
**Servidor reiniciado:** sí (PID final 15800). **Regresión:** `C:\Jarvis\pruebas\correr_todo.py --cardan` → **12/12 OK**.

| ID | Qué | Archivos | Prueba |
|---|---|---|---|
| JRV-10 | Ejecutor de recetas de pieza (JSON en mm): protrusión, corte (pasante o con profundidad, con retroceso de dirección), revolución, corte de revolución (Pappus), redondeo, chaflán; perfiles rect/círculo/polígono/contorno con arcos/círculos en círculo; estado real y volumen por operación; verificación de caja y volumen; acota los bocetos (Ø, ancho, alto) para que el plano las recupere | `agente\receta_pieza.py` (nuevo) | Brida: volúmenes exactos por operación; eje escalonado 46 784,6 mm³ exacto |
| JRV-14 | Material (`MatTable.ApplyMaterial`, aviso si no existe) y propiedades (`SummaryInfo`) | `agente\receta_pieza.py` | "Acero" aplicado; Title/Author/ProjectName puestos |
| JRV-12 | El parser ya no inventa medidas: `cotas_supuestas`; el chat pregunta en vez de modelar (rutas "sí", "modela el plano", modelado por frase y `/api/cad/model_pending`) | `cad_engine.py`, `server.py` (`_preguntar_cotas`) | "modela una brida en solid edge" → pregunta 5 medidas; placa con todas las medidas → sin supuestos |
| JRV-63 | Rutas CAD del chat en segundo plano; **"parcial" ya no lanza el motor de pistón** (exige verbo de crear + "motor de pistón") | `server.py` | "mañana tengo parcial de cálculo" → conversación |
| JRV-61 | Clave de Brave fuera del código: `C:\Jarvis\.env` + `entorno.py`; `.env` en `.gitignore` | `entorno.py` (nuevo), `server.py`, `gemini_brain.py`, `ui_controller.py`, `config\mcp_config.json`, `.gitignore` | Los 3 módulos cargan la clave; ningún archivo de código la contiene |
| JRV-20/21/25 | Ejecutor de recetas de ensamble: caras por reglas geométricas (`caras.py`), fijar, coincidir, alinear plano (+desfase), alinear eje, insertar, ángulo (con plano de medida), tangente, conjunto rígido; orden y nombres del PathFinder | `agente\caras.py`, `agente\receta_ensamble.py` (nuevos), acción `caras` | 6 relaciones resueltas; ángulo 30,000°, desfase 50 mm, coaxial 0,000 mm, tangente a 15,000 mm |
| JRV-30/31 | "Motor" por pasos (PutMatrix, técnica de `prueba_giro`) con pieza seguidora y video MP4 (ffmpeg) | `agente\motor.py` (nuevo) | Cardán: 362,9° → −362,7°, 45 pasos, 0 relaciones rotas, video de 91 KB |
| JRV-40 (alternativa B) | Pseudo-explosión en copia (relaciones suprimidas, piezas separadas del centro) | `agente\explosion.py` (nuevo) | 183 relaciones suprimidas, 89 piezas separadas; original intacto. Separación modesta |
| JRV-50/51/52/53 | Planos: pieza (frontal + 2 plegadas + iso, escala normalizada, cotas recuperadas y reacomodadas, líneas de centro) y ensamble (iso, lista "ISO" con globos número/cantidad, sobre el cuadro); propiedades del cuadro; PDF | `agente\plano.py` (nuevo) | Brida: Ø120/Ø60/Ø30/Ø10/15/40 legibles; Cardán: 8 filas, globos 6/40, 8/40… como el formato del curso |
| JRV-19 | Acción `exportar` (STEP/STL/IGES/Parasolid/PDF con SaveCopyAs) | `agente\acciones.py`, `api_agente.py` | STEP de la brida, original sin cambios |
| JRV-64 | Batería de regresión de un comando | `pruebas\correr_todo.py`, `pruebas\recetas\*.json` | 12/12 OK |
| JRV-24, JRV-32, AutoExplode | **Bloqueados** (ver lecciones): `CheckInterference`, `DragComponentRotation` y `AutoExplode` no se dejan llamar con éxito desde Python ni desde C# dinámico | `agente\interferencia.py`, `agente\csharp\Interferencia.cs` (experimentales, sin exponer en la API) | Documentado |

---

## 2026-10-28 · JRV-69: Cardán con vínculos redirigidos a su carpeta nueva

**Aprobado por el usuario:** "Redirige vínculos" (2026-10-28).
**Contexto:** el usuario movió `Downloads\CAD Cardan` y `Documents\Proyectos_SolidEdge\Cardan` a `<proyectos CAD>\`, y el `.asm` abría vacío.
**Respaldo:** `C:\Jarvis_respaldos\2026-10-28_JRV-69\` (`Cardan.asm` B8ACDDEC…, `Cardan.cfg` 0CAEF1CF… originales; `codigo\` con los 4 archivos de Jarvis antes de cambiar rutas).

| Paso | Resultado |
|---|---|
| Copia de trabajo en `%TEMP%\jarvis_ensayos\cardan_vinculos\` | Original intacto en todo momento |
| Revision Manager: 8 vínculos `Downloads\CAD Cardan\*.par` → `…\CAD\CAD Cardan\*.par` (`LinkedDocument.Replace` + `SaveAllLinks`) | Relectura en sesión nueva: 8/8 existen |
| Abrir la copia en Solid Edge y **guardarla una vez** (tras redirigir abría marcada "con cambios") | Reabierta limpia |
| Verificación de la copia por la API: `inspeccionar`, `capturar` y `receta prueba_giro.py` | 90 ocurrencias, 184 relaciones resueltas, 0 faltantes; imagen completa; giro 360,59° → 360,55°, 44 pasos, 0 fallos |
| Copia puesta en su lugar (`Cardan.asm` 0085504B…, `Cardan.cfg` 4C403F19…) y re-verificada allí | Igual de bien; imagen `Cardan_vista_iso_ok.png` junto al ensamble |
| Las 8 `.par` | Huellas idénticas a las originales antes y después |
| Rutas de Jarvis en un solo sitio: `cardan\rutas_cardan.py` (nuevo); lo leen `server.py`, `ensamblar_cardan.py`, `inspeccionar_piezas.py`, `agente\acciones.py` y el diagnóstico | "estado del cardán" → fases [1–5] en la ruta nueva; servidor reiniciado (PID 19796) |
| Herramienta nueva `agente\vinculos.py` (`listar` / `redirigir`) | Lista los 8 vínculos sanos del Cardán definitivo |
| Corrección en `agente\acciones.py`: `cerrar()` espera a que el documento desaparezca | Mejora defensiva; **no** era la causa del documento que quedó abierto (ver lecciones) |

---

## 2026-10-28 · Bloque 0: cimientos (JRV-01, 02, 03, 05, 06, 60, 62)

**Aprobado por el usuario:** "Sí, bloque 0" (2026-10-28).
**Respaldo previo:** `C:\Jarvis_respaldos\2026-10-28_bloque0\` (`server.py`, `se_com_seguro.py`, `git_sync.py` (copiado del respaldo de la mañana; no había cambiado), `ensamblar_cardan.py` (reconstruido quitando las 5 líneas añadidas; compila)). ⚠️ `git_sync.py` y `ensamblar_cardan.py` se editaron **antes** de respaldarlos; se corrigió enseguida. Lección: respaldar TODOS los archivos de la lista antes de la primera edición.
**Servidor reiniciado:** sí (PID final 32476).

| ID | Cambio | Archivos | Prueba |
|---|---|---|---|
| JRV-62 | `guardia_disco()` + `espacio_libre_gb()`; `guardar_nuevo` se niega con < 0,3 GB; cada fase del Cardán también; la API rechaza las acciones que escriben | `se_com_seguro.py`, `cardan\ensamblar_cardan.py`, `api_agente.py` | Compila; la API devuelve el aviso de disco |
| JRV-60 | "actualízate" ya **no** descomprime encima de `C:\Jarvis`: descarga a `C:\Jarvis_respaldos\<fecha>_github\`, compara y lista qué cambiaría | `git_sync.py` (`revisar_actualizacion_github`), `server.py` | Prueba sin red con un paquete simulado: habría revertido 7 archivos parchados y dejado huérfanos 15; `C:\Jarvis` quedó intacto |
| JRV-05 | Acción `inspeccionar`: operaciones, volumen, caja, propiedades / ocurrencias, relaciones, problemas, **vínculos rotos**, configuraciones / hojas y vistas | `agente\acciones.py` (nuevo) | Pieza de prueba (exacta); Cardán real: 90 ocurrencias, 184 relaciones, 0 problemas, huella intacta, 11 s |
| JRV-03 | Acción `capturar`: `SaveAsImage` y, si falla, `PrintWindow`; validación por contenido; muestra ocurrencias ocultas si abrió Jarvis; opción de ventana completa | `agente\acciones.py` | Pieza y ensamble de prueba capturados bien (vista iso); el Cardán sale vacío por vínculos rotos y la acción lo explica |
| JRV-01/02 | API de agentes: `/api/agente/acciones`, `/ejecutar`, `/tarea/{id}`, `/tareas`; procesos aparte, una tarea de Solid Edge a la vez, registro persistente | `api_agente.py` (nuevo), `server.py` | 8 pruebas contra el servidor real: estado, inspección, captura, receta permitida (regresión JRV-11: 9/9 en 15 s), receta fuera de carpeta y acción inexistente rechazadas, doble lectura de tarea |
| JRV-06 | "abre Solid Edge" / "abre <ruta>" abren sin crear; la ruta de modelado exige un verbo de crear (antes, cualquier frase con "solid edge" creaba una pieza) | `server.py` | "¿qué versión de Solid Edge tengo?" → conversación, sin pieza; "abre Solid Edge" y "abre <ruta>.par" → tarea `abrir` OK; ninguna pieza nueva creada |

---

## 2026-10-28 · JRV-11: la verificación de piezas ya no miente

**Aprobado por el usuario:** "Sí, aplica JRV-11" (2026-10-28).
**Respaldo previo:** `C:\Jarvis_respaldos\2026-10-28_JRV-11\` (`cad_atomic_lib.py`, `cad_validator.py` y los resultados de la regresión antes y después).
**Servidor reiniciado:** sí (PID 18516 → 13420); "estado del cardán" responde.
**Prueba:** `C:\Jarvis\pruebas\regresion_jrv11.py` (no guarda nada; crea piezas en memoria y las cierra).

| Cambio | Archivo | Antes → después (medido) |
|---|---|---|
| Estados sanos = `igFeatureOK` y `igFeatureWarned` (constantes con nombre); se quitó `1216476311 = igFeatureFailed` | `cad_atomic_lib.py` | Operación fallida: "sana" → **no sana** |
| `bounding_box_mm(body)` nuevo: `GetRange` leyendo el retorno (`Body.Range` no existe) | `cad_atomic_lib.py`, `cad_validator.py` | Caja 0 × 0 × 0 → **100 × 80 × 30** y **60 × 60 × 80** (correctas) |
| `get_model_physical_properties`: cada medida en su propio `try`; `Faces(1)` en vez de `Faces` | `cad_atomic_lib.py`, `cad_validator.py` | Caja 0 (la excepción de `Faces` lo saltaba todo) → correcta |
| `end_and_hide_profile` valida con `End(igProfileClosed)` (y eje de revolución en los vaciados por revolución) y lanza `ValueError` claro | `cad_atomic_lib.py` | Perfil abierto: seguía sin aviso → **se detiene** ("Profile.End devolvió -103") |
| `verify_removed_volume(model, antes, esperado)` nuevo | `cad_atomic_lib.py` | Distingue agujero bueno (14 726,2 mm³ quitados) de uno fuera de la pieza (0 mm³) |
| `validate_part_model_health` separa `warned_features` de `failed_features` | `cad_validator.py` | — |
| `verify_dimensions_against_plan`: tolerancia por defecto 5 → **0,5 mm** (nunca se había ejecutado de verdad porque la caja valía 0) | `cad_validator.py` | Hoy ningún flujo la llama |
| Comentario de aviso: `igRight`/`igLeft` están **invertidos** respecto a la type library; constantes reales `SE_LEFT`/`SE_RIGHT` añadidas. **No** se cambiaron los valores viejos | `cad_atomic_lib.py` | Sin cambio de comportamiento (ver JRV-67) |

Compilan e importan: `cad_atomic_lib`, `cad_validator`, `cad_engine`, `cad_pipeline`, `build_piston_engine_project`, `universal_cad_builder`, `server`.
**Riesgo residual:** los scripts viejos que llaman a `prof.End(0)` directamente (en `cad_engine.py`, `build_*.py`) siguen sin validar sus perfiles; solo los que pasan por `cad_atomic_lib` validan. Un flujo viejo con un perfil abierto que antes "terminaba" ahora se detiene con error: es el comportamiento buscado.

---

## 2026-10-28 · Blindaje inicial + receta del Cardán

**Respaldo previo:** `C:\Jarvis_respaldos\2026-10-28_pre_blindaje\` (todo el código, sin `venv`).
**Servidor reiniciado:** sí (PID nuevo tras el cambio).

| # | Cambio | Archivo(s) | Prueba |
|---|---|---|---|
| 1 | **Capa COM segura** nueva: conectar sin matar Edge.exe, reintentos ante "ocupado", `guardar_nuevo`/`ruta_libre`, `quitar_fijo`, `describir` caras, matrices, `estado_ensamble`, `Bitacora`, `huellas`. | `se_com_seguro.py` (nuevo) | Usada por todas las fases del Cardán. |
| 2 | **Receta del Cardán** por fases 1–5, con reglas geométricas, preposicionado, validación previa, verificación posterior, paradas y bitácora. | `cardan\ensamblar_cardan.py`, `cardan\inspeccionar_piezas.py`, `cardan\prueba_giro.py` (nuevos) | Ensayo + corrida oficial: 184/184 relaciones, verificación final sin fallos, giro de 360°. |
| 3 | `get_or_start_solidedge` y `connect_or_launch_solidedge` ya **no ejecutan `taskkill /f Edge.exe`**. | `cad_engine.py:36`, `cad_atomic_lib.py:29` | Compila e importa. |
| 4 | **Nunca borra ni sobrescribe** al guardar: se cambió `unlink()` + `SaveAs` por `ruta_libre`. | `cad_engine.py` (4 sitios) | Compila. |
| 5 | **Mensajes honestos**: el ensamble genérico devuelve `relations_created: 0` y lo dice; el motor de pistón ya no anuncia relaciones que no crea. | `cad_engine.py` (`assemble_any_parts_in_solidedge`), `build_piston_engine_project.py:400` | Revisión de código. |
| 6 | Los errores de tareas en segundo plano **se notifican** en vez de perderse. | `task_manager.py:42` | Compila. |
| 7 | **Órdenes del Cardán** en el chat; el ensamble genérico **pregunta** si no sabe qué piezas usar; reglas CAD de honestidad en el prompt. | `server.py` (`cardan_orden`, ruta "ensambla las piezas", `SYSTEM_PROMPT`) | Prueba de enrutado: "estado del cardán", "¿qué es un cardán?" (no actúa), "ensambla las piezas" (pregunta), "fase 9" (pide fase válida). Corrida oficial completa desde el chat. |

Descubrimientos durante la corrida → `memoria/lecciones.md` §1 (FixedRotate, NormalsAligned, normales exteriores, GetCylinderData, convención de matriz).
