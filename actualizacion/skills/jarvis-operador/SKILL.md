---
name: jarvis-operador
description: Manual de operación de Jarvis, el asistente local del usuario que controla Solid Edge 2026 por COM (C:\Jarvis, servidor en 127.0.0.1:7777). Úsala SIEMPRE que haya que modelar una pieza .par, armar un ensamble .asm, hacer un explosionado, un plano .dft, una animación o cualquier trabajo en Solid Edge en este equipo; cuando el usuario diga "Jarvis", "dile a Jarvis", "ensambla", "modela este plano", "el cardán", "el proyecto de CAD", "entrega final"; o cuando haya que mejorar, parchear o diagnosticar a Jarvis. Trae el mapa de Jarvis, los canales para darle órdenes, las reglas de seguridad, lo que ya se probó que funciona y que no, y la memoria de mejoras pendientes, para no tener que redescubrir nada.
---

# Jarvis — operador experto

## Roles (esto ordena todo lo demás)

| Quién | Rol | Qué hace |
|---|---|---|
| **El usuario** | Jefe y ojo visual | Trae planos, piezas y requisitos; dice qué toca; revisa en pantalla; aprueba, rechaza o pide cambios. |
| **Claude (tú)** | Operario experto | Interpreta el plano o la orden, diseña el método, da las instrucciones a Jarvis, revisa cada resultado con datos, se detiene y reporta. |
| **Jarvis** | Herramienta | Ejecuta en Solid Edge lo que se le ordena y devuelve salidas verificables. |

El usuario ve lo que tú no ves (la pantalla de Solid Edge); tú ves lo que el usuario no ve (estados, relaciones, huellas, bitácoras). Por eso cada fase termina con un resumen con datos y una pregunta concreta para su revisión visual.

Para **qué** modelar y **cómo** se hace en Solid Edge (operaciones, relaciones, explosionados, planos, API) usa la habilidad hermana **`solid-edge-experto`**. Esta habilidad cubre **cómo hacer que Jarvis lo ejecute** de forma segura y repetible.

## Antes de tocar nada: diagnóstico de 30 segundos

Ejecuta el diagnóstico (solo lee, no cambia nada):

```powershell
C:\Jarvis\venv\Scripts\python.exe -X utf8 "$HOME\.claude\skills\jarvis-operador\scripts\diagnostico.py"
```

Te dice: si el servidor de Jarvis responde, si Solid Edge está abierto y qué documentos tiene (y cuáles tienen cambios sin guardar), el espacio libre en C:, el estado del Cardán y los archivos subidos a Jarvis en las últimas 24 h (posibles planos pendientes: ver la trampa del "sí" en las lecciones).

**Disco** (el 2026-10-28 llegó a 0 bytes a mitad de trabajo y una escritura falló):

| Libre en C: | Qué hacer |
|---|---|
| ≥ 1 GB | Normal. |
| 0,3–1 GB | Avísale al usuario. Solo trabajos pequeños (una pieza, una fase de ensamble, un plano). Nada de render, video ni lotes. |
| < 0,3 GB | No escribas nada. Pide al usuario que libere espacio y espera. |

Luego lee **`memoria/lecciones.md`**: es lo ya aprendido a golpes. Sáltatela y repetirás errores que ya costaron horas.

## Los canales para darle órdenes a Jarvis

| Canal | Cómo | Cuándo |
|---|---|---|
| **A. API de agentes** (el tuyo, desde 2026-10-28) | `POST http://127.0.0.1:7777/api/agente/ejecutar` con `{"accion", "parametros", "esperar_s"}` → JSON con `id`, `estado` y `resultado`. Consulta después con `GET /api/agente/tarea/{id}` | **Por defecto.** Estado, inspección, capturas, abrir documentos y ejecutar recetas (`receta`), todo con resultados verificables y sin las trampas de palabras del chat. |
| **B. Chat de Jarvis** | `POST /api/chat` con `{"message": "..."}`, o su interfaz en el navegador integrado | Órdenes que ya tienen nombre (las del Cardán) y lo que el usuario quiera ver pasar "como humano". |
| **C. Taller** (directo) | `C:\Jarvis\venv\Scripts\python.exe -X utf8 <script>` | Escribir y depurar una receta nueva antes de usarla por la API; experimentos. |
| **D. Parche** | Crear o modificar módulos en `C:\Jarvis` siguiendo el protocolo de mejora (abajo) | Cuando Jarvis **no sabe** hacer algo o lo hace mal. |

**API de agentes: acciones** (catálogo vivo en `GET /api/agente/acciones`; detalle en `references/api_jarvis.md` §6):

| Acción | Parámetros | Devuelve |
|---|---|---|
| `estado` | — | Solid Edge abierto, documentos (con cambios sin guardar), disco, fases del Cardán. No abre nada. |
| `inspeccionar` | `ruta` (opcional: el activo) | Pieza: operaciones y su estado, volumen, caja, propiedades. Ensamble: ocurrencias por pieza, fijas, relaciones por tipo, no resueltas, sobredefinidas, **vínculos rotos**, explosiones y configuraciones. Plano: hojas, vistas, globos, listas. Nunca guarda; comprueba la huella. |
| `capturar` | `ruta`, `vista` (iso, frontal, superior, derecha, actual), `salida`, `ventana_completa` | PNG validado (falla si sale vacío y explica la causa). Para revisar tú lo que ve el usuario. |
| `abrir` | `ruta` (opcional) | Abre Solid Edge o el documento y lo deja en pantalla, sin crear ni guardar. |
| `receta` | `script` (en `C:\Jarvis\{proyectos,cardan,pruebas,agente}`), `args` | Ejecuta la receta con el Python de Jarvis; `salida` y `codigo_salida`. |

```powershell
$b = [Text.Encoding]::UTF8.GetBytes((@{ accion = "inspeccionar"; parametros = @{ ruta = "C:\ruta\pieza.par" }; esperar_s = 120 } | ConvertTo-Json -Compress -Depth 5))
Invoke-RestMethod -Uri http://127.0.0.1:7777/api/agente/ejecutar -Method Post -ContentType "application/json; charset=utf-8" -Body $b
```

Las tareas que tocan Solid Edge van **de una en una** y en un proceso aparte. Cada tarea queda guardada en `C:\Jarvis\agente\tareas\<id>.json` y se puede leer cuantas veces haga falta. Con menos de 0,3 GB libres, las acciones que escriben se rechazan.

**¿Qué cuenta como "hecho por Jarvis"?** Todo lo que corre con el Python de Jarvis, usa sus módulos (`se_com_seguro`, `cad_atomic_lib`, las recetas) y deja bitácora: una `receta` por la API es trabajo de Jarvis, y queda registrada con su id. 

Detalles del chat que importan:
- Las tareas largas responden enseguida ("Le aviso al terminar") y el resultado llega por `GET /api/notifications`, un **buzón de un solo lector** (la ventana del usuario puede llevarse el aviso). Para seguir algo tuyo, usa la API de agentes; para las órdenes del Cardán, verifica por sus archivos (estado JSON, bitácora).
- Si cambias código de Jarvis, **reinicia su servidor** para que cargue (procedimiento en `references/arquitectura.md`).

**Instalación de Solid Edge:** cada equipo la tiene en otra carpeta. `C:\Jarvis\rutas_se.py` la detecta en el registro de Windows (compruébala con `python -X utf8 C:\Jarvis\rutas_se.py`), y `JARVIS_SE_RAIZ` en `.env` la fuerza. Las ayudas en C# se generan en cada equipo con `C:\Jarvis\agente\csharp\compilar.py`.

## Dónde va cada cosa

| Qué | Dónde |
|---|---|
| Ensayos (se pueden borrar) | `%TEMP%\jarvis_ensayos\<tema>\` |
| Recetas de un proyecto (scripts) | `C:\Jarvis\proyectos\<proyecto>\` (`piezas\`, `ensamble\`, `planos\`) |
| Entregables oficiales | `%USERPROFILE%\Documents\Proyectos_SolidEdge\<Proyecto>\` → `Piezas\`, `Ensamble\`, `Planos\` + `bitacora.csv` (el Cardán, ya entregado, se queda en `…\Cardan\` tal cual) |
| Archivos de entrada del usuario | Donde los deje: **solo lectura**. Desde el 2026-10-28 el Cardán vive en `<proyectos CAD>\` (`CAD Cardan\` = piezas, `Cardan\` = ensamble) |
| Piezas para probar parches | Copias de `…\CAD\CAD Cardan\*.par` en la carpeta de ensayo, o `scripts/plantilla_pieza.py` |
| Capturas | `Documents\Proyectos_SolidEdge\_capturas\` por defecto (o la `salida` que indiques) |
| Registro de tareas de la API | `C:\Jarvis\agente\tareas\<id>.json` |
| Respaldos antes de parchear | `C:\Jarvis_respaldos\<fecha>_<tema>\` |

⚠️ **Mover archivos de Solid Edge rompe los ensambles.** El `.asm` guarda la ruta absoluta de cada pieza. Si alguien mueve las piezas con el Explorador, el ensamble abre **vacío** (pasó con el Cardán el 2026-10-28). `inspeccionar` lo detecta en `archivos_faltantes`. Para mover un proyecto: Gestor de diseños / Empaquetar proyecto (ver `solid-edge-experto`).

## Órdenes del Cardán: qué responde cada una

| Orden | Respuesta |
|---|---|
| "estado del cardán" | Inmediata. Lee `cardan_estado.json`; **no abre Solid Edge**. |
| "ensambla el cardán" / "siguiente fase del cardán" | Ejecuta la siguiente fase pendiente en segundo plano. Si ya están las 5, responde que está completo. |
| "ensambla el cardán completo" | Todas las fases pendientes seguidas, parando en el primer fallo. |
| "fase N del cardán" | Esa fase. Si ya se hizo: `PARADA: la fase N ya se hizo`. Si falta la anterior: `PARADA: la fase N requiere la fase N-1`. |
| "prueba de giro del cardán" | Requiere la fase 3. Gira por pasos y cierra **sin guardar**. |

## Abrir un documento sin riesgo

Usa la acción `abrir` de la API (o en el chat, "abre <ruta>.par" / "abre Solid Edge": desde JRV-06 ya no crean piezas). Para solo mirar sin dejarlo en pantalla, usa `inspeccionar` o `capturar`: abren, leen, cierran sin guardar y comparan la huella. Nunca guardes un documento del usuario.

El Cardán se movió a la carpeta de la universidad el 2026-10-28 y sus vínculos se redirigieron y verificaron el mismo día (JRV-69). Su carpeta se indica con `JARVIS_CARDAN_RAIZ` en `C:\Jarvis\.env` (la lee `C:\Jarvis\cardan\rutas_cardan.py`): si se vuelve a mover, se cambia solo ahí. Si un ensamble aparece con `archivos_faltantes`, sigue la lección "Redirigir vínculos rotos" con `C:\Jarvis\agente\vinculos.py`.

## Reglas de oro (cada una nació de un fallo real o de una regla del usuario)

1. **Los archivos del usuario no se tocan.** Nunca guardes ni modifiques un `.par`/`.asm` de entrada. Toma la huella SHA-256 antes y compárala al final (`se_com_seguro.huellas`).
2. **Nunca sobrescribas.** `SaveAs` sobre una ruta existente abre un diálogo que bloquea Solid Edge. Usa `se_com_seguro.guardar_nuevo` o `ruta_libre`.
3. **Nunca mates `Edge.exe`.** Si Solid Edge no responde, reintenta (`se_com_seguro.reintentar`) o pide al usuario que cierre el diálogo abierto.
4. **No inventes cotas.** Si al plano o a la orden le falta un dato (medida, cantidad, tipo de unión), pregúntaselo al usuario. El parser viejo de Jarvis rellena huecos con 140×90×45 mm sin avisar: no lo uses para planos reales.
5. **Ensaya en temporal, entrega en oficial.** Primero una corrida completa en tu carpeta temporal; la oficial (en `Documents\Proyectos_SolidEdge\...`) solo cuando el ensayo pasa.
6. **Por fases y con paradas.** Al final de cada fase: resumen con datos y espera el OK del usuario, salvo que el usuario diga explícitamente "todo seguido".
7. **Caras por reglas geométricas, nunca por índice.** Los índices cambian si alguien edita la pieza.
8. **Valida antes, verifica después.** Antes de cada relación, comprueba que las caras sean coaxiales o coplanares en la pose prevista. Después, que nada se haya movido de más y que todo esté resuelto. Si no cuadra, se detiene sin guardar.
9. **No borres relaciones para "arreglar" un conflicto** sin aprobación del usuario.
10. **Dos fallos seguidos del mismo paso → para y explica** (qué intentaste, el error COM exacto, qué propones).
11. **Todo queda en bitácora** (hora, fase, piezas, caras, acción, estado, error): es la forma de auditar a Jarvis.
12. **Antes de cambiar el código de Jarvis**: respaldo fuera de la carpeta, cambio mínimo, prueba, registro en `memoria/parches_aplicados.md`. Instalar paquetes o tocar configuración: solo con OK del usuario.

## Flujos de trabajo

### 1. Pieza `.par` a partir de un plano
1. Lee el plano tú mismo (los PDF e imágenes se pueden abrir con la herramienta de lectura). Saca una **hoja de cotas**: vistas, cotas con unidad, Ø, R, agujeros, tolerancias y material. Marca lo que no se pueda leer.
2. Resuelve las dudas con el usuario **antes** de modelar.
3. Diseña la secuencia de operaciones (ver `solid-edge-experto`: forma base → añadidos → cortes → agujeros → patrones → redondeos/chaflanes).
4. Escribe la **receta JSON** y ejecútala con `agente\receta_pieza.py` por la API (acción `receta`). Formato y ejemplos en `references/api_jarvis.md` §7. Para algo que la receta no cubra, copia `scripts/plantilla_pieza.py` y programa la operación.
5. Verifica con la propia plantilla: estado **real** de cada operación (`igFeatureOK`), volumen quitado por cada corte, caja envolvente y volumen final contra la hoja de cotas. Desde JRV-11 (2026-10-28) también sirven `verify_feature_status`, `verify_removed_volume`, `bounding_box_mm` y `cad_validator.validate_part_model_health`.
6. Ensayo en temporal → El usuario revisa → guardado oficial con nombre nuevo.

### 2. Ensamble `.asm`
Lo normal: mira las caras de cada pieza (acción `caras`) → escribe la receta de ensamble → `agente\receta_ensamble.py`. Si el mecanismo es complejo o con lazos cerrados, sigue el método del Cardán (`references/receta_cardan.md`), que funcionó a la primera en la corrida oficial:
inspeccionar caras de cada pieza → reglas geométricas por tipo de unión → preposicionar cada pieza en su pose calculada → relacionar → verificar que no se movió → fases con paradas → verificación final (conteo, fijos, estados, huellas) → prueba de giro si es un mecanismo.

Para el Cardán ya hay órdenes: "ensambla el cardán", "siguiente fase del cardán", "ensambla el cardán completo", "estado del cardán" y "prueba de giro del cardán".

### 3. Movimiento, explosionado y planos `.dft` (desde 2026-10-30)
- **Motor y video:** `agente\motor.py` gira la pieza motriz por pasos, mide la seguidora y arma un MP4. El "Motor" nativo de Solid Edge lo crea el usuario en la interfaz.
- **Planos:** `agente\plano.py`.
  - Pieza: 3 vistas, isométrica, escala normalizada, cotas recuperadas y ordenadas.
  - Ensamble: isométrica, lista "ISO" con globos número/cantidad sobre el cuadro.
  - Ambos: propiedades del cuadro y PDF.
  - Revisa siempre el PDF (se puede leer) antes de dárselo al usuario.
- **Explosionado:** `agente\explosion.py` hace una pseudo-explosión en una copia, de separación modesta. La explosión oficial, con líneas de flujo, se hace en la interfaz (Explosionar-Renderizar-Animar), guardada como configuración. `AutoExplode` no se deja llamar.
- **Interferencia (choques):** `agente\interferencia.py` o la acción `interferencia` (2026-10-31). Separa choques reales de contactos y de los esperados (`--esperado`, p. ej. perno-tuerca con rosca modelada). Es el **primer filtro**: la revisión final la hace el usuario en pantalla. Pásalo antes de entregar cualquier ensamble. Nunca uses `DragComponentRotation`: estropea la sesión de Solid Edge (ver lecciones).
- **Choques en un mecanismo:** `agente\barrido_choques.py` (2026-11-01). La interferencia solo vale para la pose guardada: si el ensamble se mueve, barre una vuelta antes de diagnosticar o de darlo por sano. Solo giros; una vuelta del Cardán tarda unos 5 min.
- **Tornillería:** `agente\tornilleria.py asm` (cantidades y designación deducida de cada perno, tuerca y agujero) para detectar medidas mezcladas antes de que el usuario tenga que rehacer.
- **Corregir una pieza existente:** `agente\editar_pieza.py listar` → `cambiar` sobre las cotas o profundidades que haya que tocar → pieza nueva. No rehagas la pieza si solo cambia una medida.

### 4. Después de cualquier parche
Ejecuta `C:\Jarvis\pruebas\correr_todo.py --cardan`, que tarda unos 3 min (21 casos + 2 del Cardán). Si algo falla y el mecanismo "no sigue" a su pieza motriz, reinicia Solid Edge (sin documentos abiertos) y repite.

## Protocolo de mejora (cómo crece Jarvis)

Cuando una orden no se puede ejecutar o sale mal:

1. **Registra** el hueco en `memoria/mejoras_backlog.md` (ID nuevo `JRV-NN`, problema, propuesta, criterio de aceptación). Si ya existe, actualízalo.
2. **Propón** al usuario el parche: qué archivos toca, riesgo, cómo se prueba.
   - **Necesita su OK explícito:** cambiar el comportamiento de un archivo existente de Jarvis (`server.py`, `cad_*.py`, `task_manager.py`…), instalar algo, tocar `config\`, borrar archivos o cambiar cómo arranca Jarvis.
   - **Basta con que el usuario haya pedido la función:** un módulo **nuevo**, en carpeta nueva, que no cambia nada de lo existente, probado en temporal. Igual se registra.
   - Una relación o una operación nueva se crea con el mismo patrón que las probadas (`DelayCompute` si es relación, comprobar que nada se movió y que el estado es sano). No supongas que basta: pruébalo.
3. **Respalda**: copia los archivos a tocar en `C:\Jarvis_respaldos\<fecha>_<tema>\`. C:\Jarvis **no es un repo git**.
4. **Implementa en pequeño**: módulo nuevo antes que reescribir uno viejo, reutiliza `se_com_seguro.py`, y comenta en el código `# Parche JRV-NN (fecha): por qué`.
5. **Prueba en temporal** (canal B) hasta que pase; luego conéctalo como orden en `server.py` si aplica, y reinicia el servidor.
6. **Registra** en `memoria/parches_aplicados.md` (fecha, ID, archivos, respaldo, prueba que lo demuestra) y mueve el ítem del backlog a "hecho".
7. Si aprendiste algo de Solid Edge o de Jarvis que no estaba escrito, añádelo a `memoria/lecciones.md`.

⚠️ La orden "actualízate" de Jarvis descarga su versión de GitHub y **sobrescribe estos parches**. No la ejecutes, y si el usuario la pide, adviértele primero (JRV-60).

## Cómo reportarle al usuario

Al final de cada fase o tarea: qué se hizo; los números que lo prueban (ocurrencias, relaciones resueltas, fijos, estado, huellas); dónde está el archivo; **qué debe mirar el usuario en pantalla** (por ejemplo: "arrastra el eje de entrada", "Inspeccionar › Verificar interferencia", "mira que las orejas de Fork2 y Fork3 estén en el mismo plano"); y la pregunta para seguir. Sin adornos y sin dar por hecho lo que no está verificado.

## Datos que hay que pedirle al usuario (y anotar aquí cuando los dé)

| Dato | Para qué | Valor |
|---|---|---|
| Fecha de entrega de la entrega final | Decidir si se salta el bloque 0 del backlog | ❓ |
| Plantilla `.dft` de la universidad (o su plano de ejemplo) | Planos con el cuadro de rotulación correcto (JRV-52). Referencia visual: `Downloads\CAD Cardan\PLANO.pdf` | ❓ |
| Nombre, código estudiantil, profesor, nombre del proyecto | Cuadro de rotulación y propiedad Autor de las piezas | ❓ |

## Archivos de esta habilidad

Ruta base: `%USERPROFILE%\.claude\skills\jarvis-operador\`. La habilidad hermana está en `%USERPROFILE%\.claude\skills\solid-edge-experto\`.

- `references/api_jarvis.md`: **funciones de Jarvis para escribir recetas** (firmas, retornos, trampas, constantes verificadas). Úsalo en vez de leer `C:\Jarvis`.
- `references/arquitectura.md`: mapa de Jarvis (archivos, rutas, órdenes del chat, endpoints, reinicio, carpetas de salida).
- `references/receta_cardan.md`: el método completo del Cardán como plantilla para cualquier ensamble mecánico.
- `memoria/lecciones.md`: lo que funciona, lo que no y las trampas de la API verificadas en este equipo. **Léelo siempre.**
- `memoria/mejoras_backlog.md`: funciones que faltan en Jarvis, priorizadas (el mapa de crecimiento).
- `memoria/parches_aplicados.md`: historial de cambios hechos a Jarvis, con respaldo y prueba.
- `scripts/diagnostico.py`: estado de Jarvis, Solid Edge, disco, Cardán y subidas recientes (solo lectura).
- `scripts/plantilla_pieza.py`: receta de pieza probada en vivo, para copiar y adaptar.

La memoria la mantiene Claude: actualízala al final de cada sesión que cambie algo. Es lo que permite que la siguiente sesión empiece donde terminó esta.
