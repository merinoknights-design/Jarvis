# Lecciones aprendidas (léelas antes de operar)

Cada entrada: qué pasó → por qué → qué hacer. Añade las nuevas arriba de su sección, con fecha. Si una lección deja de ser cierta (por un parche), táchala con `~~…~~` y di qué la derogó; no la borres.

## Contenido
1. API COM de Solid Edge (verificado en este equipo)
2. Trampas de Jarvis
3. Entorno y equipo
4. Lo que funcionó y conviene repetir

---

## 1. API COM de Solid Edge (verificado en SE 2026 de este equipo, 2026-10-28)

- **Antes de suponer que un método no existe, mira la type library.** La documentación pública de la API llega a ST7–ST8; SE 2026 tiene bastante más (`AssemblyDocument` pasó de ~178 a 223 miembros). Con `solid-edge-experto/scripts/firmas_api.py` se lee la firma exacta en segundos y sin abrir Solid Edge. Así aparecieron `AutoExplode`, `DragComponentRotation`/`Translation` (con detección de colisiones), `CheckInterference2/3/4` y `DrawingView.RetrieveDimensions`, que la investigación web había dado por inexistentes.
- **Estado OK no es geometría correcta.** Un corte con un círculo y `ProfileSide = igRight` quitó todo lo de **fuera** del círculo (dejó un cilindro Ø10) y la operación salió `igFeatureOK`. `igLeft` quita el interior. → Mide el volumen antes y después de cada corte (`plantilla_pieza.comprobar_quitado`). (2026-10-28)
- ~~El código viejo de Jarvis da por buena una operación fallida~~ → **corregido por JRV-11 (2026-10-28)**: en `cad_atomic_lib` sano es `igFeatureOK` (1216476310) o `igFeatureWarned` (…312); `1216476311` es `igFeatureFailed`.
- **`Body.Range` no existe** (solo `GetRange` y `GetExactRange`), y `Body.Faces` exige el argumento `1` (igQueryAll). El código viejo fallaba en las dos y la caja envolvente salía 0. Corregido en `cad_atomic_lib.bounding_box_mm` y `get_model_physical_properties` (JRV-11).
- **`Profile.End(1)`** (igProfileClosed) valida que el perfil esté cerrado y devuelve 0 si está bien; un perfil abierto devuelve −103. Para revolución, `End(1 | 16)` (exige eje). `end_and_hide_profile` ya valida así; los scripts viejos que llaman a `End(0)` directamente, no (JRV-68).
- **`igRight`/`igLeft` están invertidos en `cad_atomic_lib.py` y `cad_engine.py`** (1/2 en vez de 2/1). El código viejo funciona *porque* está invertido. En código nuevo usa `SE_LEFT = 1` / `SE_RIGHT = 2`, o mejor, comprueba el volumen quitado (JRV-67).
- **Las pruebas viejas de Jarvis también se equivocaban de geometría sin saberlo**: en `test_atomic_lib.py`, el "taladro pasante" solo atravesaba 20 de 30 mm y la ranura anular quedaba fuera del cilindro y no quitaba nada, y ambas "pasaban". Una prueba que no mide volumen no prueba nada. Regresión buena: `C:\Jarvis\pruebas\regresion_jrv11.py`. (2026-10-28)
- Tras `doc.Close(False)`, cualquier acceso a ese `doc` da "El objeto invocado ha desconectado de sus clientes": lee lo que necesites antes de cerrar.
- **No hay "Motor" en la API** (ni objeto ni ID de comando en `MotionCommandConstants`). Para mover un mecanismo: relación Angular motriz por pasos, o `DragComponentRotation`.
- Que la firma exista **no garantiza** que funcione desde pywin32 dinámico: los `[out]` (Status, ErrorCode, CollisionFound) pueden necesitar makepy (`win32com.client.gencache.EnsureDispatch`) o `VARIANT` byref. Pruébalo en temporal antes de construir encima.

- **`AddAxial` hace saltar la pieza.** Nace con `FixedRotate=True`; si el solver resuelve en ese instante, gira la pieza a una orientación "canónica" (Fork2 giró 73° alrededor de su pasador). → Crea las relaciones axiales dentro de `app.DelayCompute = True`, pon `rel.FixedRotate = False` y luego `DelayCompute = False`. Resultado: 0,0000 mm de movimiento.
- **`AddPlanar(ref1, ref2, True, p1, p2)` = Coincidir** respecto de las **normales exteriores** de las caras (se probó con normales geométricas opuestas, y la pieza no se volteó). `False` = Alinear plano. Los puntos van en coordenadas de pieza y funcionan aunque la pieza esté desplazada.
- **`GetPlaneData` no da la normal exterior.** → Usa `Face.GetParamRange([0]*2, [0]*2)` y `Face.GetNormal(1, [u, v])`.
- **`GetCylinderData` necesita 3 argumentos** en Python: `([0.0]*3, [0.0]*3, 0.0)`. El contexto original decía 2. Los resultados se leen **del valor de retorno**, nunca de la lista que pasas.
- **El mismo error de parámetros de salida está en el código viejo de Jarvis**: `body.Range(min, max)` en `cad_validator.py` y `cad_atomic_lib.py` lee las listas que pasó → la caja envolvente siempre da 0 y la "verificación contra el plano" no verifica nada. → Lee el retorno: `r = body.GetRange([0]*3, [0]*3)` (o `Range`) y usa `r`.
- **Matriz de ocurrencia**: `occ.GetMatrix([0.0]*16)` devuelve 16 valores; `p_asm = R·p + t` con `R[i][j] = M[4j+i]` y `t = M[12:15]`. Verificado girando el Fork 90° y comparando `GetRangeBox`. `occ.PutMatrix(M, True)` mueve la ocurrencia.
- **`AddByFilename` deja la ocurrencia Fijada** (una relación Ground). Quítala con `se_com_seguro.quitar_fijo` antes de relacionar, salvo la base.
- **Las piezas abiertas dentro de un ensamble son de solo lectura** (`ReadOnly=True`, `Dirty=False`): Solid Edge no puede guardarlas desde ahí. Aun así, compara huellas al final.
- ~~`CheckInterference` no funciona desde pywin32~~ → **resuelto el 2026-10-31 con interop tipado + C#** (ver la lección del interop tipado más abajo; herramienta `agente\interferencia.py`).
- **`SaveAs` a una ruta existente** abre un diálogo que `DisplayAlerts=False` no suprime y bloquea Solid Edge. → `guardar_nuevo` / `ruta_libre`.
- **`View.SaveAsImage` dio imagen en blanco dos veces** con el Cardán (90 ocurrencias), incluso tras esperar 6+3 s y `View.Fit()`. Causa no aclarada (¿ventana sin foco o minimizada?). → Hoy no hay forma fiable de "ver" el ensamble por script (JRV-03).
- **`PutMatrix` sobre una pieza ya relacionada es una petición**: el solver la cumple solo en parte (~3° por cada 10° pedidos al girar el Cardán). Sirve para simular un arrastre, no para fijar un ángulo exacto.
- **Velocidad**: crear una relación tarda entre 0,01 y 0,06 s; las 80 piezas de tornillería con 160 relaciones tardaron 45 s. No hace falta optimizar.
- **Estados**: relación resuelta = `Status 1`. Ocurrencia: 2 = fija, 4 = subdefinida (normal en un mecanismo), 32776 = sobredefinida, 32784 = inconsistente.
- **Las piezas del Cardán son `CopiedPart`** (sin historial de operaciones) → `AssemblyPatterns.Create` (Patrón de ensamble) no tiene un patrón de operación en el que apoyarse. Revisa `Model.Features` antes de prometer patrones.

- **Un ensamble con las piezas movidas abre vacío.** El `.asm` guarda rutas absolutas (`c:\users\<usuario>\downloads\cad cardan\fork.par`). Si las piezas se mueven con el Explorador, al abrirlo por automatización **todas las ocurrencias quedan `Visible = False`, ponerlas en `True` no hace nada** y la vista solo muestra los ejes. Las relaciones siguen apareciendo "resueltas" (datos guardados): el inspector no basta, hay que mirar `archivos_faltantes`. (2026-10-28, Cardán)
- 🔴 **`DragComponentRotation` estropea la sesión de Solid Edge** (2026-10-30). Con makepy y `EdgeOrAxis=None` la llamada no da error pero no mueve nada, y después **el solver deja de propagar movimientos**: `prueba_giro` y el motor movían solo la pieza motriz y el resto se quedaba quieto. Se arregló cerrando Solid Edge sin documentos (`app.Quit()`) y volviéndolo a abrir. No la uses. Si un mecanismo deja de seguir a su pieza motriz, sospecha del estado de la sesión antes que del código: reinicia Solid Edge y repite.
- **Métodos con parámetros de salida que NO se pudieron usar desde Python** (2026-10-30): `CheckInterference`/`2` (DISP_E_TYPEMISMATCH con pywin32 dinámico, makepy y C# dinámico, se pasara lo que se pasara), `AutoExplode` (lo mismo; además `StartCommand(33079)` no cambia al entorno ERA por automatización) y `DragComponentRotation` (ver arriba). Necesitarían el interop tipado del SDK de Siemens. Unos diez intentos documentados en `parches_aplicados.md`: no los repitas sin una idea nueva. **La idea nueva llegó el 2026-10-31 y funcionó para `CheckInterference`** (siguiente lección); `AutoExplode` queda por reintentar así.
- 🔑 **Interop tipado sin el SDK** (2026-10-31): `System.Runtime.InteropServices.TypeLibConverter` (viene con .NET Framework, sin instalar nada) convierte las `.tlb` de `<SE>\Program` en `Interop.*.dll` (`agente\csharp\GenerarInterop.exe <carpeta_salida> <SE>\Program\assembly.tlb <SE>\Program\constant.tlb`, bandera `SafeArrayAsSystemArray`). Con esas DLL, C# llama a los métodos con `out` de verdad (`csc` de `C:\Windows\Microsoft.NET\Framework64\v4.0.30319`). Es la herramienta para cualquier método que pywin32 rechace por parámetros de salida.
- **`CheckInterference` tipado**: `doc.CheckInterference(n, ref set1, out status, seInterferenceComparisonSet1vsItself, Missing, Missing, false, informe, opciones, out num, ref partes1, ref partes2, ref confirmadas, out ocurrencia, roscas)`. Con `Set2` = `Missing` y los arrays de salida `null` funciona; con valores puestos da E_INVALIDARG. El resultado útil está en el **archivo de informe** (bloques "Interferencias", "n de m", dos nombres "Archivo.par:k", "Volumen de Interferencias X mm^3"). Un perno en una tuerca con rosca modelada da un solape fijo (2,945 mm³ en M3): por eso existe `--esperado`.
- **Agujeros (`Holes`/`HoleData`)** (2026-10-31): `HoleDataCollection.Add(33, Ø, …, IgnoreSavedDefaultValues=True)`; el tipo 37 se convierte en 36 y hereda los valores guardados del usuario (salió un refrentado de Ø12,7). La rosca se pone con `ThreadSetting = 164` + `ThreadNominalDiameter`, `ThreadMinorDiameter` y `ThreadDescription`, y el Ø del agujero = diámetro menor de `HOLES.TXT`. `ThreadDataByDescription` no llena el diámetro (sale 0). **Un `Holes2d` con dos centros solo hace el primero** → una operación por centro.
- **Rosca exterior (cosmética) en un perno: `Threads.Add`/`AddEx` dan 0x80020009** con todo lo probado. Sin resolver.
- **Cotas que gobiernan**: una cota creada por API nace como cota de referencia (`Constraint=False`): cambiar su `Value` no mueve la geometría. Hay que poner `Constraint = True`. `AddSymmetricalDiameter(eje, x, y, z, True, línea, x, y, z, True)` exige `keyPoint=True` en los dos (con `False` dio Ø200 o 0); compara el valor con 2×distancia al eje y borra la cota si no cuadra.
- **Leer las cotas de una pieza**: `Variables.Query` con filtros de tipo devolvió 0; recorrer `ProfileSets → Profiles → Dimensions` sí las da (`DisplayName` tipo `V340`).
- **Patrones de operación**: `Patterns.AddByCircular(n, [operaciones], plano, cantidad, ángulo, [cx, cy, 0], 0, 1, ajuste)` y `AddByRectangular(n, [operaciones], plano, nx, ny, px, py, 0, 2, 0)`. Comprobado por volumen (5 copias nuevas exactas). Para patronar hay que saber qué operaciones de SE creó cada paso de la receta: `construir` compara `Features.Count` antes y después.
- **La regresión encontró un choque real en el ensamble de prueba** (un eje atraviesa el disco de la brida, 4 542,7 mm³) que nadie había visto en 3 días. Una verificación nueva sirve también para auditar las pruebas viejas.
- 🔑 **En un mecanismo, una interferencia vale solo para esa pose** (2026-11-01, Cardán). `Fork.par:4 ↔ tuercaM3.par:25` parecía una tuerca mal puesta y resultó ser la punta de la oreja de una horquilla rozando las tuercas de la brida vecina, en 4 tramos de la vuelta (centrados en 0°, 92°, 179° y 272°). Antes de diagnosticar un choque en algo que se mueve, mira con qué está relacionada cada pieza (`Relations3d`) y barre una vuelta con `agente\barrido_choques.py`. Medir en todas las posiciones importa: con pasos de 36° el máximo salió 0,96 mm³ en un tramo donde hay 2,15, y cada 8° salió 1,97 donde hay 2,10.
- **`InterferenciaTipada.exe` analiza la pose en memoria** si el documento ya está abierto (busca por `FullName`): así se puede verificar entre pasos de `PutMatrix` sin guardar.
- **Señalar algo en pantalla sin ensuciar el documento** (2026-11-01): `View.SetCamera(eye, target, up, False, 0.1)` + `View.RangeZoomCamera(lo, hi)` + `doc.SelectSet.Add(occ)` (las pinta de verde en la interfaz, pero `SaveAsImage` no pinta la selección). `Dirty` sigue en `False`. `SetCamera` y `RangeZoomCamera` no centran exacto en el objetivo: ajusta el margen y mira la imagen. Para imágenes con colores: `occ.Style = "Rojo"` y `occ.Visible = False`, **solo en una copia**. `FaceStyles.Item(i).StyleName`: hay nombres en español y en inglés.
- **Vértices de un cuerpo:** `Body.Vertices` → `Item(i).GetPointData([0.0]*3)` devuelve los 3 valores directos (no un par). Para medir cuánto entra una pieza en otra, pasa los vértices de una a coordenadas axial/radial de la otra: los vértices de la tuerca dentro de la horquilla dieron 0,03 mm y los de la horquilla dentro de la tuerca, 0,79 mm (el real). Prueba las dos direcciones.
- 🔴 **Publicar Jarvis** (2026-11-01). El repositorio es **público**. Nunca uses `push_update_to_github` de `git_sync.py`: hace `git add .` y sube a `main`. El procedimiento correcto está en `references/arquitectura.md`, «Publicar una actualización». La clave de Brave escrita en el código sigue en el historial público de git: quitarla de los archivos no la protege, solo cambiarla.
- **Leer un PDF de plano ampliado sin instalar nada:** `Windows.Data.Pdf` desde PowerShell 5.1 renderiza a PNG de cualquier ancho y se recorta con PIL. Sirvió para comprobar la orientación de los pernos en `PLANO.pdf`. El visor de archivos locales del navegador integrado no deja tomar capturas.
- **Opcionales en makepy/dinámico**: un `double` opcional omitido llega como `None` y falla (pásalo explícito); un objeto opcional omitido da "tipos no coinciden" (pásalo como `None`). Los argumentos de salida van POR NOMBRE: en la firma ocupan su posición y un valor puesto ahí descoloca todo. Para usar makepy sin afectar al resto de Jarvis, caché PRIVADA: ver `agente\interferencia.py`.
- **`AddAngular` necesita los elementos de medida** (`MeasureElement1/2`): con `None` da E_INVALIDARG. Sirven las dos caras que ya están en contacto (`plano_medida` en la receta).
- **`ReorderOccurrence(occ, destino, AfterTarget)`**: con `True` el orden salió exactamente invertido; el efectivo es `False`.
- **`Occurrence.Name` se puede cambiar** (nombre visible en el PathFinder).
- **Recuperar cotas solo trae las cotas del boceto del modelo**: una pieza dibujada sin cotas da un plano sin diámetros. `receta_pieza` acota círculos (Ø) y rectángulos (ancho y alto); las cotas recuperadas salen amontonadas, y `Sheet.ArrangeDimensionsInSelectSet(1.0, True)` las ordena.
- **La lista de piezas sin posición queda fuera de la hoja**: `PartsList.AnchorPoint = 3` (inferior derecha) + `SetOrigin(ancho - 0.010, 0.062)` la pone sobre el cuadro de rotulación ISO.
- **La plantilla `<SE>\Template\ISO Metric\iso metric draft.dft`** trae por defecto un A3 apaisado con fondo "Hoja A3" (hay también A4, A4V, A2, A1 y A0), y la configuración de lista "ISO" tiene las columnas del curso (número, archivo, autor, cantidad).
- `MatTable.GetMaterialList` da E_NOTIMPL; `ApplyMaterial(doc, "Acero")` sí funciona.
- **El clasificador de seguridad de Claude Code bloquea** cerrar todos los documentos sin guardar y borrar archivos con `Remove-Item`. Cierra solo lo tuyo (`cerrar_copia.py` limita a la carpeta de ensayos) y guarda con otro nombre en vez de borrar.
- **Respalda ANTES de la primera edición**: el 28 y el 30 se editaron archivos antes de respaldarlos y hubo que reconstruir el estado previo. Primer paso de cada bloque: copiar a `C:\Jarvis_respaldos\<fecha>_<tema>\` todos los archivos de la lista.
- **Redirigir vínculos rotos** (verificado 2026-10-28, Cardán). Herramienta: `C:\Jarvis\agente\vinculos.py`. Pasos:
  1. Usa una **copia**.
  2. Redirige con Revision Manager (`RevisionManager.Application` → `Open` → por cada `LinkedDocuments`: `Replace(ruta_nueva)` → `SaveAllLinks`).
  3. **Abre la copia en Solid Edge y guárdala una vez**: tras redirigir, abre con `Dirty = True` y `prueba_giro` y las fases se detienen ("abierto con cambios sin guardar"). Solid Edge cambia también el `.cfg`.
  4. Verifica con `inspeccionar`, `capturar` y la prueba de giro.
  5. Reemplaza el original, después de respaldarlo.
- **pywin32 dinámico ejecuta los métodos sin argumentos al leer el atributo** (`doc.SaveAllLinks` ya guarda y devuelve un entero; `doc.SaveAllLinks()` falla con "'int' object is not callable", pero ya se guardó). Y `LinkedDocuments.Item(i)` falla: recorre con `for d in coleccion`.
- **No adivines la causa de un fallo: aíslalo.** El documento que quedaba abierto parecía culpa de la captura (se supuso un cierre asíncrono y se "corrigió"), pero ejecutando paso a paso resultó que lo abría `prueba_giro` y se detenía por el `Dirty` de los vínculos redirigidos. Un paso de verificación con `estado` entre acciones lo habría mostrado a la primera.
- `prueba_giro.py` necesita `cardan_estado.json` junto al `.asm` (lee los roles de las piezas). Al probar sobre una copia, cópialo también.
- **Captura de pantalla:** `View.SaveAsImage` funciona bien con pieza y ensamble si los vínculos están sanos. Para saber si una imagen está vacía, la desviación típica **no sirve** (una vista con solo los ejes daba 3,04). Usa la fracción de píxeles distintos del fondo: vacía ≈ 0,0004; pieza ≈ 0,15. `PrintWindow(app.hWnd)` captura la ventana completa de Solid Edge, con la cinta y todo: útil para ver diálogos y errores.
- **Interfaz en español vista en la captura:** la cinta del entorno Conjunto tiene los grupos "Ensamblar", "Ajuste magnético", **"Motores"**, "Relación de…", "Patrón" y "Configuraciones", y las pestañas Inicio, Operaciones, PMI, Simulación, Verificar, Herramientas, Ver y Gestión de datos. El cubo de vistas dice Planta, Alzado y Derecha.
- **PowerShell 5.1 se come las comillas dobles** del JSON pasado como argumento a un programa externo. Pasa los parámetros con `@archivo.json` (lo admite `acciones.py`) o por la API HTTP.

## 2. Trampas de Jarvis

- ~~"solid edge" en cualquier orden de chat crea una pieza~~ → **corregido por JRV-06 (2026-10-28)**: hace falta un verbo de crear; "abre Solid Edge" / "abre <ruta>" abren sin crear.
- ~~"actualízate" sobrescribe C:\Jarvis~~ → **corregido por JRV-60 (2026-10-28)**: ahora descarga aparte y compara. "sube actualización" sigue haciendo `git init` + commit local si no hay repo (sin remoto no publica nada).

- **"sí", "dale", "sigue", "hazlo"… con planos pendientes** los manda a modelar con las plantillas. Si subiste un plano solo para mirarlo, no respondas con un afirmativo suelto.
- **El parser de planos inventa medidas**: toma los primeros números del texto y rellena lo que falta con 140×90×45 mm, Ø100, espesor 15, redondeo 2,5. Para planos reales, lee tú el plano y construye con receta explícita.
- **El análisis de planos con Gemini** (`file_analyzer.analyze_blueprint_with_gemini`) usa un ejemplo JSON mal formado en el prompt, nombres de modelo sin verificar y 8 s de espera con 1200 tokens de salida. No es fiable hasta revisarlo (JRV-13).
- **Notificaciones de un solo lector** (chat): si el usuario tiene abierta la ventana de Jarvis, se lleva los avisos. Para lo tuyo usa la API de agentes (`/api/agente/tarea/{id}`, JRV-02); para el Cardán, sus archivos.
- **El servidor no recarga solo**: tras tocar el código, reinícialo (procedimiento en `references/arquitectura.md`).
- **Las rutas CAD del chat corren en el hilo del servidor** si no usan `execute_smart_task`. Una tarea larga ahí congela la interfaz (JRV-63). Las órdenes nuevas deben ir en segundo plano, como `cardan_orden`.
- **Errores tragados**: el código viejo está lleno de `try/except: pass`. Una función que "termina bien" no prueba que Solid Edge haya hecho lo pedido: verifica el objeto producido.

## 3. Entorno y equipo

- **Disco C: casi lleno.** Llegó a 0 bytes libres el 2026-10-28 (se recuperó a ~0,5–1,1 GB sin intervención). Lo más grande: `AppData\Local\Claude-Data` 11,4 GB, `hiberfil.sys` 6,4 GB, `AppData\Local\Packages` 6,3 GB, Docker 3,3 GB, uv 2,9 GB. Revísalo antes de corridas grandes; no borres nada sin permiso del usuario.
- Solid Edge tarda unos 20 s en arrancar por COM (`Dispatch` lo lanza con `/automation`, invisible: hay que poner `Visible = True`).
- La interfaz de Solid Edge está en **español**: Coincidir, Alinear plano, Alinear eje, Insertar, Fijar, Patrón.
- El Python de Windows de Jarvis es el único con pywin32 que funciona con Solid Edge. Usa siempre `C:\Jarvis\venv\Scripts\python.exe -X utf8`.

## 4. Lo que funcionó y conviene repetir

- **Preposicionar y luego relacionar**, comprobando que la pieza no se movió: convierte cualquier cara mal elegida en una parada inmediata y explicable.
- **Ensayo completo en temporal** antes de la corrida oficial: el fallo de `FixedRotate` apareció en el ensayo, no en el entregable.
- **Resolver el cierre de un lazo analíticamente** y cerrarlo solo con Alinear eje.
- **Estado por fases en JSON** (fases hechas + nombre de la ocurrencia de cada rol): permite reanudar y detectar trabajo a medias.
- **Huellas SHA-256** de los archivos de entrada, antes y después.
- **Prueba de giro por pasos** para validar un mecanismo sin la interfaz.
