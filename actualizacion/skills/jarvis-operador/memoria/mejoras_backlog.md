# Backlog de mejoras de Jarvis

El mapa de crecimiento de Jarvis: lo que le falta para hacer en Solid Edge **todo lo que haría un humano**, paso a paso y con calidad verificable. Lo mantiene Claude: cuando algo falla o falta, se registra aquí; cuando se implementa, se pasa a `parches_aplicados.md` y aquí se marca ✅ con la fecha.

**Prioridad**: **P1** = necesario para la entrega final (piezas del proyecto → ensamble general → explosionado → planos) · **P2** = calidad y comodidad · **P3** = después.
**Estado**: ⬜ pendiente · 🟨 en curso · ✅ hecho (fecha) · ⛔ descartado (motivo).
**Vía**: API = COM documentado · CMD = `StartCommand` con ID de comando · UI = automatizar la interfaz (pywinauto) · C# = ayudante en .NET · — = sin Solid Edge.

## Contenido
1. Comunicación Claude ↔ Jarvis
2. Piezas (.par)
3. Ensambles (.asm)
4. Movimiento y animación
5. Explosionado
6. Planos (.dft)
7. Robustez e infraestructura
8. Orden sugerido de implementación

---

## 1. Comunicación Claude ↔ Jarvis

| ID | Función | Problema hoy | Enfoque | Vía | P | Estado |
|---|---|---|---|---|---|---|
| JRV-01 | **API para agentes**: `POST /api/agente/ejecutar {accion, parametros}` síncrona o con id de tarea, que devuelva JSON estructurado (resultado, archivos, métricas, errores), y `GET /api/agente/tarea/{id}`. | Claude habla con Jarvis por el chat pensado para humanos (frases, palabras clave, respuestas en prosa). Las trampas de palabras clave pueden disparar acciones no deseadas. | Endpoints nuevos que llaman a funciones registradas (catálogo de acciones), sin pasar por el enrutado de frases. | — | P1 | ✅ 2026-10-28 (ver parches_aplicados.md) |
| JRV-02 | **Notificaciones con historial por cliente** (o un id de tarea consultable). | El buzón de un solo lector deja a Claude o al usuario sin el aviso. | Guardar resultados por id y que cada cliente lea desde su último id. | — | P1 | ✅ 2026-10-28 (ver parches_aplicados.md) |
| JRV-03 | **Captura visual fiable** del documento activo (PNG por vista: iso, frontal, superior; y de la ventana completa). | `View.SaveAsImage` dio imágenes en blanco con el Cardán. Claude no puede "ver" el resultado y el usuario no puede revisar a distancia. | Probar en orden: traer la ventana al frente + `View.Update` + `SaveAsImage`; captura de la ventana con `PIL.ImageGrab`/Win32 `PrintWindow`; exportar a JPG/PNG por `SaveCopyAs`. Validar que la imagen no esté vacía (varianza de píxeles). | API / Win32 | P1 | ✅ 2026-10-28 (ver parches_aplicados.md) |
| JRV-04 | **Bitácora unificada** (JSON Lines) para toda acción CAD, no solo el Cardán. | Solo el Cardán deja rastro auditable. | `se_com_seguro.Bitacora` en todas las rutas CAD + id de tarea. | — | P2 | ✅ 2026-10-30 (registro de tareas de la API + bitácoras CSV de cada receta) |
| JRV-05 | **Inspector de documento**: volcado del PathFinder (operaciones y su estado; ocurrencias, relaciones y estados; variables; propiedades). | Para revisar lo que hay hay que escribir un script cada vez. | Acción de solo lectura `inspeccionar(documento)` → JSON. Base: `inspeccionar_piezas.py` y `estado_ensamble`. | API | P1 | ✅ 2026-10-28 (ver parches_aplicados.md) |
| JRV-06 | **Orden "abre/activa documento" segura** (sin crear piezas). | "Abre Solid Edge" en el chat crea una pieza genérica (trampa de la palabra clave). | Ruta explícita antes del disparador "solid edge"; abrir solo lectura si se pide. | API | P2 | ✅ 2026-10-28 (ver parches_aplicados.md) |
## 2. Piezas (.par)

| ID | Función | Problema hoy | Enfoque | Vía | P | Estado |
|---|---|---|---|---|---|---|
| JRV-10 | **Ejecutor de recetas de pieza** (JSON): planos de referencia, bocetos con geometría + relaciones + cotas, y operaciones (protrusión, vaciado, revolución, barrido, desvanecido, agujero, rosca, patrón, simetría, redondeo, chaflán, vaciado de pared, nervio), con verificación por operación. | Solo hay 5 plantillas rígidas (pistón, revolución, brida, prismática, en L). Cualquier pieza distinta sale mal o no sale. | Claude lee el plano y escribe la receta; Jarvis la ejecuta paso a paso, comprueba `Feature.Status` tras cada operación y se detiene en el primer fallo. Base: `cad_atomic_lib.py`. | API | P1 | ✅ 2026-10-30 (`agente\receta_pieza.py`) |
| JRV-11 | 🔴 **Arreglar la verificación de piezas** en `cad_atomic_lib` y `cad_validator`: (a) `HEALTHY_STATUS_CODES` incluye `1216476311 = igFeatureFailed` → **las operaciones fallidas pasan por sanas**; (b) `body.Range` **no existe** → la caja siempre vale 0; (c) `Profile.End(0)` no valida el perfil; (d) añadir verificación contra la hoja de cotas y del volumen quitado por cada corte. | Hoy Jarvis puede decir "pieza correcta" sobre una pieza rota. | Sano = solo `1216476310`; `GetRange` leyendo el retorno; `End(1)`; reutilizar `comprobar`/`comprobar_quitado`/`verificar` de `scripts/plantilla_pieza.py` (probados en vivo). Cambio pequeño pero toca módulos existentes → **OK del usuario**. | API | P1 | ✅ 2026-10-28 (ver `parches_aplicados.md`; la verificación contra la hoja de cotas completa queda en JRV-10) |
| JRV-12 | **Quitar las medidas inventadas** del parser regex: si falta una cota, preguntar. | Rellena con 140×90×45, Ø100, etc. sin avisar. | Devolver la lista de cotas faltantes en vez de valores por defecto. | — | P1 | ✅ 2026-10-30 |
| JRV-13 | **Revisar o retirar el análisis de planos con Gemini**. | Prompt con JSON mal formado, modelos sin verificar, 8 s de espera y 1200 tokens de salida. | Que Claude haga la lectura del plano (multimodal) y produzca la hoja de cotas; dejar Gemini como opción secundaria y corregida. | — | P2 | ⛔ 2026-10-30: reemplazado (Claude lee el plano y escribe la receta) |
| JRV-14 | **Material y propiedades de archivo** (Autor, Título, Número de documento, Proyecto) al crear o guardar. | La lista de piezas del plano necesita "Autor" y nombre; hoy no se rellenan. | `doc.Properties` / SummaryInfo + tabla de materiales. | API | P1 | ✅ 2026-10-30 |
| JRV-15 | **Agujeros normalizados y roscas** (M3…: pasante, roscado, avellanado, refrentado) y rosca cosmética. | Los agujeros se hacen como cortes circulares. | `Holes` + `HoleData`; `Threads`. | API | P2 | ✅ 2026-10-31 agujeros simples y roscados (M…, pasantes o ciegos) en `receta_pieza` (op `agujero`) + inventario `agente\tornilleria.py`. Falta: avellanado/refrentado sin probar y **rosca cosmética exterior** en pernos (`Threads.Add`/`AddEx` dan 0x80020009) |
| JRV-16 | **Patrones de operación** (rectangular, circular) y **simetría**. | Las plantillas dibujan cada agujero a mano; sin patrón real, el ensamble no puede usar Patrón de ensamble. | `Patterns`/`MirrorCopies`. | API | P2 | ✅ 2026-10-31 patrón circular y rectangular de operación (op `patron` de `receta_pieza`); falta la simetría (`MirrorCopies`) |
| JRV-17 | **Editar una pieza existente** (cambiar una cota o variable y regenerar) sin rehacerla. | No existe; toda corrección es rehacer. | Tabla de variables / `Dimensions` + recompute. Siempre sobre copia nueva. | API | P2 | ✅ 2026-10-31 `agente\editar_pieza.py` (listar cotas y profundidades; cambiar → pieza nueva, original intacto, no guarda si una operación falla). Sirve para piezas con historial; las `CopiedPart` (como las del Cardán) no tienen cotas que cambiar |
| JRV-18 | **Chapa** (.psm): pestaña, brida, pliegue, desarrollo. | No existe. | API de SheetMetal. | API | P3 | ⬜ |
| JRV-19 | **Exportar STEP/STL/PDF 3D** de una pieza. | Existe a medias en el código del pistón. | `SaveCopyAs` con extensión, a ruta nueva. | API | P3 | ✅ 2026-10-30 (acción `exportar`) |

## 3. Ensambles (.asm)

| ID | Función | Problema hoy | Enfoque | Vía | P | Estado |
|---|---|---|---|---|---|---|
| JRV-20 | **Receta de ensamble genérica** (JSON: piezas y cantidades, uniones tipo A/B/C/D…, cierre de lazo, fases). | El método del Cardán está codificado para el Cardán. | Extraer `Geo`/`Pose`/`Ensamble` de `ensamblar_cardan.py` a un módulo `ensamble_lib.py` y leer la receta de un JSON. | API | P1 | ✅ 2026-10-30 (`agente\receta_ensamble.py`) |
| JRV-21 | **Más relaciones** con la misma validación: Ángulo, Tangente, Plano medio, Engranaje, Trayectoria, Conjunto rígido, Insertar (= coincidir + axial), desfases. | Solo Fijar, Alinear eje y Coincidir/Alinear plano. | `AddAngular`, `AddTangent`, `AddCenterPlane`, `AddGear`, `AddPath`, `AddRigidSet`, `AddPoint` (firmas verificadas en `solid-edge-experto/references/05_api_automatizacion.md` §11). | API | P1 | ✅ 2026-10-30 (ángulo, tangente, conjunto rígido, desfases; engranaje y plano medio sin probar) |
| JRV-22 | **Subensambles** (crear, insertar un .asm dentro de otro). | No existe. | `Occurrences.AddByFilename` con .asm + relaciones. | API | P2 | 🟨 (se puede insertar un .asm como pieza; relaciones a caras de un subensamble sin soporte) |
| JRV-23 | **Patrón de ensamble real** cuando la pieza tiene un patrón de operación; si no, plan B por script (como el Cardán). | Las piezas del Cardán no tienen historial. | `AssemblyPatterns.Create` (a probar con una pieza que sí tenga patrón). | API | P2 | ⬜ |
| JRV-24 | **Verificación de interferencia automática**. | `CheckInterference` no funciona desde pywin32 dinámico (parámetro `[out]` Status). | Hay 4 variantes (`CheckInterference`…`4`, firmas verificadas). Probar en orden: makepy (`gencache.EnsureDispatch`, devuelve los `[out]` como tupla) → `VARIANT` byref → ayudante en C# (muestra oficial `ReportInterference`) → interfaz. | API / C# | P1 | ✅ 2026-10-31 con interop TIPADO generado de las type libraries (`agente\csharp\GenerarInterop.cs` + `InterferenciaTipada.cs`) y `agente\interferencia.py` (choques reales vs contactos, choques esperados, archivo sin cambios). Acción `interferencia` de la API |
| JRV-25 | **Orden y nombres en el PathFinder** (`ReorderOccurrence`, renombrar ocurrencias, agrupar tornillería). | Solo el orden de inserción. | API de Occurrences. | API | P2 | ✅ 2026-10-30 |
| JRV-26 | **Insertar piezas estándar** (tornillos, tuercas, arandelas ISO) desde la biblioteca. | Solo piezas que trae el usuario. | Standard Parts (a investigar). | ? | P3 | ⬜ |
| JRV-69 | 🔴 **El Cardán quedó con vínculos rotos** y Jarvis apunta a la ruta vieja. El 2026-10-28 se movieron `Downloads\CAD Cardan` → `<proyectos CAD>\CAD Cardan` y `Documents\Proyectos_SolidEdge\Cardan` → `…\CAD\Cardan`. El `.asm` sigue apuntando a `Downloads\CAD Cardan\*.par` y abre **vacío**. `server.py` (`CARDAN_ASM`) y `ensamblar_cardan.py` (carpeta de piezas) usan las rutas viejas. | El entregable no se ve, y "ensambla el cardán" empezaría uno nuevo. | **Decide el usuario:** (a) volver a dejar las carpetas donde estaban; o (b) redirigir los vínculos con el Gestor de diseños de Solid Edge o por API sobre una **copia** (`Occurrence.Replace`, a investigar) y actualizar las rutas de Jarvis. Las 8 piezas movidas son idénticas a las originales (huellas verificadas). | UI / API | P1 | ✅ 2026-10-28 (vínculos redirigidos con Revision Manager; rutas en `cardan\rutas_cardan.py`) |
| JRV-70 | **Avisar al mover proyectos**: orden "mueve/empaqueta el proyecto X" que use Empaquetar proyecto o reescriba los vínculos, y que `inspeccionar` se ejecute tras cualquier movimiento. | Mover con el Explorador rompe ensambles en silencio. | Investigar la API de Design Manager / Pack and Go; mientras tanto, avisar. | API | P2 | 🟨 (existe `agente\vinculos.py` para listar/redirigir; falta la orden "mueve el proyecto") |
## 4. Movimiento y animación

| ID | Función | Problema hoy | Enfoque | Vía | P | Estado |
|---|---|---|---|---|---|---|
| JRV-30 | **"Motor" por API**: girar el eje de entrada un ángulo exacto y que la cadena lo siga. | No existe. **SE 2026 no tiene objeto ni comando "Motor" en su API** (verificado en la type library). | Relación **Angular** motriz en el eje de entrada (`Relations3d.AddAngular`, firma verificada) cuyo `Angle` se cambia por pasos; verificar relaciones tras cada paso. El motor "de verdad" (Motor + Simular motor) lo crea el usuario en la interfaz. | API | P1 | ✅ 2026-10-30 (`agente\motor.py`, giro por pasos) |
| JRV-31 | **Video del mecanismo** (giro completo). | No existe. | JRV-30 por pasos + captura por paso (JRV-03) + `ffmpeg` (habilidad `ffmpeg`). | API + — | P2 | ✅ 2026-10-30 (video MP4 con ffmpeg) |
| JRV-32 | **Arrastre con detección de colisiones** (prueba de giro que además detecte choques). | La prueba de giro no detecta choques. | `asm.DragComponentRotation(occ, 1 detectar, 1 todas, ángulo, …, eje)` → devuelve `CollisionFound` y las piezas que chocan (firma verificada; falta probar los `[out]` desde pywin32). | API | P1 | ✅ 2026-11-01 por barrido: `agente\barrido_choques.py` detecta los choques en toda la vuelta. El arrastre en sí sigue ⛔ desde 2026-10-30: DragComponentRotation se puede llamar (makepy + EdgeOrAxis=None) pero no mueve nada y DEJÓ EL SOLVER SIN PROPAGAR hasta reiniciar Solid Edge. No usar. 🟨 2026-10-31: el objetivo (avisar de choques) se cubre con JRV-24 sobre la posición actual; 2026-11-01: **probado el barrido durante el giro** en una copia del Cardán: `PutMatrix` por pasos + `InterferenciaTipada.exe` en cada posición (si el documento ya está abierto usa la pose en memoria, unos 6 s por verificación), 46 posiciones en una vuelta, 0 relaciones rotas; el usuario pidió convertirlo en herramienta y ya lo es. Solo cubre giros: un movimiento lineal no está soportado. Con el interop tipado se podría reintentar `DragComponentRotation` en temporal, nunca en la sesión de trabajo |

| JRV-33 | **Motor nativo** de Solid Edge (Motor + Simular motor del entorno Conjunto), para que el mecanismo quede con su motor como lo haría el usuario. | La API no expone el motor (ni objeto ni ID de comando en `MotionCommandConstants`, verificado 2026-10-28). Hoy el motor lo crea el usuario en la interfaz; Jarvis solo simula con `motor.py`. | Investigar sin prisa (el usuario, 2026-10-31: "no por ahora, pero ir viendo cómo"): (1) buscar en TODAS las type libraries de `<SE>\Program` con el interop tipado (miembros ocultos, `Motors`, `MotionSimulation`); (2) IDs de comando de la cinta "Motores" con `StartCommand` + que el usuario complete el diálogo; (3) automatizar la interfaz (pywinauto) como último recurso. | API / CMD / UI | P3 | ⬜ |

## 5. Explosionado

| ID | Función | Problema hoy | Enfoque | Vía | P | Estado |
|---|---|---|---|---|---|---|
| JRV-40 | **Vista explosionada** del ensamble general **guardada como configuración** para usarla en el plano. | No existe. | **`asm.AutoExplode(0, False, 1, out ErrorCode, distancia)` existe** (firma verificada). Ensayo en copia temporal: `AutoExplode` → `Configurations.Add("Explosion_1")` → comprobar `ConfigurationType == 1` y `ExplosionsCount`. Si no se puede guardar por API: `StartCommand(33079)` → `StartCommand(65062)` y el usuario ajusta y guarda; el script verifica. | API + CMD | P1 | 🟨 2026-10-30: AutoExplode no se deja llamar; alternativa B `agente\explosion.py` (pseudo-explosión en copia). La explosión oficial la hace el usuario en ERA. 2026-10-31: en espera hasta que el usuario vea el tema en clase y confirme cómo lo piden; el interop tipado que destrabó `CheckInterference` es la idea nueva para reintentar `AutoExplode` |
| JRV-41 | **Ajustes manuales y líneas de flujo** (Explosionar 65064, Reposicionar 65066, Líneas de flujo 33095). | No existe. | Sin método: `StartCommand` + el usuario completa en pantalla (modo asistido). | CMD/UI | P2 | ⬜ |
| JRV-42 | **Animación de la explosión** (video). | No existe. | Entorno Estudio (línea de tiempo 33097) en la interfaz; o fotogramas a distintas `SpreadDistance` + ffmpeg. | CMD/UI | P3 | ⬜ |

## 6. Planos (.dft)

| ID | Función | Problema hoy | Enfoque | Vía | P | Estado |
|---|---|---|---|---|---|---|
| JRV-50 | **Plano de pieza**: A3/A4 ISO con la plantilla de la universidad, vistas principales + isométrica, escala, recuperar cotas del modelo, líneas de centro. | No existe. | `ModelLinks.Add` + `DrawingViews.AddPartView` + `AddByFold` + `DrawingView.RetrieveDimensions(...)` + `RetrieveCenterLinesCenterMarks(...)` (las cuatro firmas verificadas). Revisión visual del usuario: el acomodo de cotas recuperadas casi siempre pide retoque. | API | P1 | ✅ 2026-10-30 (`agente\plano.py`) |
| JRV-51 | **Plano de ensamble explosionado** con **globos** (número/cantidad) y **lista de piezas** (Número de elemento · Nombre de archivo · Autor · Cantidad), como el plano del Cardán. | No existe. | `DrawingViews.AddAssemblyView(ml, orient, escala, x, y, tipo, ConfigurationName="Explosion_1")` + `PartsLists.Add(vista, ajustes, AutoBalloon=1, CreatePartsList=1)` (firmas verificadas). Depende de JRV-40 y JRV-14 (Autor). | API | P1 | ✅ 2026-10-30 |
| JRV-52 | **Cuadro de rotulación** con propiedades (proyecto, pieza, profesor, fecha, nombre, código estudiantil, plano número). | No existe. | Plantilla `.dft` del usuario + texto de propiedades. | API | P1 | 🟨 (propiedades en el cuadro ISO de la instalación; falta la plantilla propia de la universidad) |
| JRV-53 | **Exportar PDF** del plano. | No existe. | `SaveAs` / `SaveCopyAs` .pdf a ruta nueva. | API | P1 | ✅ 2026-10-30 |
| JRV-54 | **Cotas, tolerancias y anotaciones** manuales sobre vistas (cuando "recuperar cotas" no basta). | No existe. | `Dimensions` del Draft. | API | P2 | 🟨 (cotas del boceto + reacomodo automático; 2026-10-31: cotas que GOBIERNAN (`Constraint=True`) y diámetros/largos de los perfiles de revolución, así que un eje sale acotado en el plano. Faltan: posición de agujeros/PCD, tolerancias y cotas manuales en vistas) |

## 7. Robustez e infraestructura

| ID | Función | Problema hoy | Enfoque | Vía | P | Estado |
|---|---|---|---|---|---|---|
| JRV-60 | **Proteger los parches** de la auto-actualización desde GitHub (y versionar C:\Jarvis). | "actualízate" sobrescribe C:\Jarvis. | `git init` local en C:\Jarvis (con OK del usuario: cambia el comportamiento de `git_sync.py`) o respaldo automático + aviso antes de actualizar. | — | P1 | ✅ 2026-10-28 (ver parches_aplicados.md) |
| JRV-61 | **Sacar la clave de Brave del código** a variable de entorno o `.env`. | Clave escrita en claro en `server.py` y `config\mcp_config.json`. | `.env` + rotar la clave si se ha compartido. | — | P2 | ✅ 2026-10-30 (falta que el usuario ROTE la clave: estuvo en claro) |
| JRV-62 | **Guardia de disco**: no empezar una tarea CAD con < 1 GB libre. | El disco llegó a 0 bytes. | Comprobación en `se_com_seguro.conectar` o al inicio de cada receta. | — | P1 | ✅ 2026-10-28 (ver parches_aplicados.md) |
| JRV-63 | **No bloquear el servidor**: toda ruta CAD en segundo plano. | Las rutas síncronas congelan la interfaz mientras trabaja Solid Edge. | `execute_smart_task` / `asyncio.to_thread`. | — | P2 | ✅ 2026-10-30 |
| JRV-64 | **Pruebas de regresión** de recetas (Cardán y futuras) en carpeta temporal, con un solo comando. | Hoy se prueba a mano. | `pruebas/correr_todo.py` → informe. | API | P2 | ✅ 2026-10-30 (`pruebas\correr_todo.py`, 12/12) |
| JRV-65 | **Paradas con botones en la interfaz** (OK / siguiente fase / detener) y resumen visible por fase. | La parada depende de escribir la frase justa. | Botones en `ui/index.html` que llamen a la API de agentes. | — | P3 | ⬜ |
| JRV-67 | **Constantes de lado invertidas**: en `cad_atomic_lib.py` y `cad_engine.py`, `igRight = 1` e `igLeft = 2`, al revés de la type library (`igLeft = 1`, `igRight = 2`). Todo el código viejo depende de esos valores. | Confunde a quien escriba código nuevo: un `igRight` "real" quita el exterior de un agujero. | No cambiar los valores; migrar el código nuevo a `SE_LEFT`/`SE_RIGHT` (ya existen) y, cuando las plantillas viejas se retiren (JRV-10), borrar los nombres viejos. | — | P2 | ⬜ |
| JRV-68 | **`prof.End(0)` directo en los scripts viejos** (`cad_engine.py`, `build_*.py`, `universal_cad_builder.py`): no validan el perfil. | JRV-11 solo arregló las funciones de `cad_atomic_lib`. | Sustituir por `end_and_hide_profile` cuando se toque cada script, o retirar las plantillas al llegar JRV-10. | API | P3 | ⬜ |
| JRV-66 | **Retirar `try/except: pass` silenciosos** en las rutas CAD (empezando por las que usa el chat). | Errores tragados → "terminado" sin resultado real. | Registrar y propagar; verificar el objeto producido. | — | P2 | ⬜ |

## 8. Orden sugerido de implementación

Ordenado por lo que pide la entrega final (piezas → ensamble general → explosionado → planos) y por dependencias. Cada bloque termina con una prueba en carpeta temporal y la revisión del usuario.

| Bloque | Qué | IDs | Por qué en este orden |
|---|---|---|---|
| 0 · Cimientos | Guardia de disco, proteger los parches, API para agentes, captura visual, inspector de documento | JRV-62, 60, 01, 02, 03, 05 | Todo lo demás se apoya en hablar con Jarvis sin trampas y en poder ver y auditar el resultado. |
| 1 · Piezas | Ejecutor de recetas de pieza, verificación que sí mide, sin medidas inventadas, propiedades del archivo | JRV-10, 11, 12, 14 | Las piezas del proyecto son la materia prima; la lista de piezas del plano necesita Autor y Título. |
| 2 · Ensamble general | Receta de ensamble genérica, más relaciones, interferencia, orden del PathFinder | JRV-20, 21, 24, 25 | Generaliza el método del Cardán al ensamble del proyecto. |
| 3 · Movimiento | Motor angular por pasos, arrastre con colisiones, video | JRV-30, 32, 31 | El mecanismo debe demostrarse en movimiento; también sirve de prueba de calidad del ensamble. |
| 4 · Explosionado | Explosión automática guardada como configuración; modo asistido para ajustes y líneas de flujo | JRV-40, 41 | El plano de ensamble depende de esta configuración. |
| 5 · Planos | Plano de pieza, plano de ensamble explosionado con globos y lista, rotulación, PDF | JRV-50, 51, 52, 53 | Entregable final. |
| 6 · Calidad | Regresión, errores no silenciosos, servidor sin bloqueos, agujeros/patrones/edición | JRV-64, 66, 63, 15, 16, 17 | Endurecer lo que ya funciona. |
| Después | Chapa, piezas estándar, exportes, botones de parada, animación de explosión | JRV-18, 26, 19, 65, 42, 22, 23 | No los pide la entrega final. |

**Siguiente paso concreto propuesto:** el bloque 0 completo, luego un ensayo de `AutoExplode` + `Configurations.Add` + `AddAssemblyView` + `PartsLists.Add` sobre una **copia** del Cardán. Ese ensayo resuelve de una vez los tres puntos inciertos del bloque 4–5.
