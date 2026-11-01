# Actualización de Jarvis (2026-11-01)

**Si eres una persona:** no tienes que hacer estos pasos. Abre Claude Code en tu PC y pégale esto:

> Actualiza mi Jarvis con la versión nueva. Sigue de principio a fin las instrucciones de este archivo: https://raw.githubusercontent.com/merinoknights-design/Jarvis/actualizacion-2026-11-01/ACTUALIZAR_JARVIS.md. Lo autorizo en C:\Jarvis. Hazlo todo tú y pregúntame solo si un archivo choca con cambios míos o si algo falla. Al final dime qué quedó y qué debo revisar.

Claude te irá pidiendo permiso para ejecutar comandos: acéptalos. Con Solid Edge abierto o cerrado funciona igual, pero guarda antes lo que tengas sin guardar.

**Si eres Claude:** tu usuario te pidió aplicar esta actualización. Lo que sigue son tus instrucciones.

## Qué trae

Jarvis pasa de construir con plantillas y dar por buenas operaciones fallidas a trabajar con resultados que se pueden comprobar. Claude lo opera por una API propia, y la forma de trabajar queda en dos habilidades:

| Área | Qué se añade |
|---|---|
| **Seguridad** | Nunca sobrescribe, no mata `Edge.exe`, respalda, compara huellas de archivos y deja bitácora (`se_com_seguro.py`). Clave de Brave fuera del código (`.env`). «actualízate» ya no pisa los cambios locales. «parcial» ya no lanza el motor de pistón |
| **Verificación honesta** | Las operaciones fallidas ya no pasan por sanas. La caja envolvente ya no da 0. Comprueba perfiles cerrados y volumen por operación. El chat pregunta las medidas que faltan en vez de inventarlas |
| **API para agentes** | `POST /api/agente/ejecutar`: estado, inspeccionar, capturar, abrir, caras, exportar, interferencia y recetas, con respuestas JSON verificables |
| **Piezas** | `agente\receta_pieza.py`: recetas JSON en mm con protrusión, corte, revolución, redondeo, chaflán, agujeros normalizados y roscados, patrones circulares y rectangulares, material, propiedades y cotas que gobiernan |
| **Corregir piezas** | `agente\editar_pieza.py`: cambia una cota o una profundidad sin rehacer la pieza; guarda una pieza nueva |
| **Ensambles** | `agente\receta_ensamble.py`: caras elegidas por geometría; coincidir, alinear, insertar, ángulo, tangente y conjunto rígido |
| **Choques** | `agente\interferencia.py` (posición actual) y `agente\barrido_choques.py` (toda la vuelta de un mecanismo). `agente\tornilleria.py` hace el inventario de pernos y tuercas |
| **Movimiento y planos** | `agente\motor.py` (giro por pasos y video), `agente\explosion.py` (vista separada en una copia), `agente\plano.py` (planos con cotas, lista de piezas, globos y PDF), `agente\vinculos.py` (redirigir vínculos rotos) |
| **Pruebas** | `pruebas\correr_todo.py`: batería de regresión de un comando |
| **Forma de trabajar** | Habilidades de Claude `jarvis-operador` y `solid-edge-experto`, con lecciones, backlog y referencia de la API |

La forma de trabajar: **el usuario dice qué toca y revisa en pantalla; Claude interpreta, ordena y comprueba cada resultado con datos; Jarvis ejecuta en Solid Edge.**

## Reglas mientras actualizas

- No borres nada. El instalador no borra; tú tampoco.
- Nunca muestres ni pases por la línea de comandos el valor de una clave.
- No toques `venv`, `uploads`, `memory`, `logs` ni un `.env` que ya exista.
- Lee `actualizacion\actualizar_jarvis.py` antes de ejecutarlo.
- No ejecutes la orden «actualízate» de Jarvis: su versión vieja descomprime sobre `C:\Jarvis` sin comprobar nada.
- Si un paso falla dos veces, detente y explica al usuario qué intentaste y el error exacto.

## Pasos

Usa el Python de Jarvis (`C:\Jarvis\venv\Scripts\python.exe`) y deja el código descargado en una carpeta temporal, fuera de `C:\Jarvis`. Cada comando define `$t` porque el estado de la consola puede no conservarse entre llamadas.

**1. Descarga la rama.** Si la carpeta ya existe de un intento anterior, actualízala con `git -C "$t\Jarvis" pull` en vez de clonar.

```powershell
$t = Join-Path $env:TEMP "jarvis_actualizacion"; New-Item -ItemType Directory -Force $t | Out-Null
git clone --depth 1 --branch actualizacion-2026-11-01 https://github.com/merinoknights-design/Jarvis.git "$t\Jarvis"
```

Si `git` no está: descarga y descomprime `https://github.com/merinoknights-design/Jarvis/archive/refs/heads/actualizacion-2026-11-01.zip` en `$t\Jarvis`.

**2. Haz el ensayo, que no cambia nada.**

```powershell
$t = Join-Path $env:TEMP "jarvis_actualizacion"
& "C:\Jarvis\venv\Scripts\python.exe" -I -X utf8 "$t\Jarvis\actualizacion\actualizar_jarvis.py"
```

Lee el JSON de la última línea. Detente y pregúntale al usuario si:

- `entorno.es_c_jarvis` es falso o `entorno.destino_existe` es falso. Todo el código de Jarvis asume `C:\Jarvis`.
- `entorno.solid_edge_registrado` es nulo. Solid Edge no está instalado o registrado; si está en otra carpeta, se indica con `JARVIS_SE_RAIZ` en `.env`.
- `entorno.python_de_jarvis` es falso. Jarvis no tiene su entorno creado.

**3. Si hay `conflictos`, fusiónalos.** Son archivos que el usuario cambió por su cuenta. No se pisan. Para cada uno, compara su versión con la nueva (`$t\Jarvis\<archivo>`) y con la base (el commit indicado en `manifiesto.json`, campo `base`), conserva lo suyo y añade lo nuevo, y muéstrale el resultado. Repite el paso 4 con `--resuelto <archivo>` por cada uno.

**4. Aplica.**

```powershell
$t = Join-Path $env:TEMP "jarvis_actualizacion"
& "C:\Jarvis\venv\Scripts\python.exe" -I -X utf8 "$t\Jarvis\actualizacion\actualizar_jarvis.py" --aplicar
```

Comprueba que `ok` sea verdadero y anota `respaldo`. Si `compilacion.ok` es falso, lee `compilacion.error`: suele ser Solid Edge en otra carpeta.

**5. Si `reiniciar_servidor` es verdadero, reinicia Jarvis** para que cargue el código nuevo. El procedimiento está en la habilidad `jarvis-operador`, `references\arquitectura.md`, sección «Reiniciar el servidor». Si no estaba corriendo, no lo arranques por tu cuenta salvo para probar la API.

**6. Verifica con hechos, no por suposición.**

```powershell
& "C:\Jarvis\venv\Scripts\python.exe" -X utf8 "$HOME\.claude\skills\jarvis-operador\scripts\diagnostico.py"
& "C:\Jarvis\venv\Scripts\python.exe" -X utf8 C:\Jarvis\pruebas\correr_todo.py
```

La batería abre Solid Edge, crea documentos de prueba en `%TEMP%\jarvis_ensayos` y los cierra sin tocar los del usuario. Tarda unos 2 minutos. Deben salir **todos los casos OK**. No uses `--cardan` salvo que el usuario tenga ese ensamble. Si un caso falla en este PC, no lo des por bueno: investígalo y dile al usuario exactamente cuál falló. Esta versión se probó solo con **Solid Edge 2026 en español**: en otra versión o idioma pueden fallar los nombres de materiales («Acero»), de hojas («Hoja A3») y de vistas. Esos fallos se corrigen en el código de Jarvis siguiendo el protocolo de mejora de la habilidad.

**7. Clave de Brave.** La clave que estaba escrita en el código de este repositorio es pública desde hace tiempo y sigue en el historial de git. Dile al usuario que debe crear una nueva en https://brave.com/search/api/ y ponerla en `C:\Jarvis\.env` (`BRAVE_API_KEY=...`). Que no te la pegue en el chat: que edite el archivo él mismo.

**8. Carga las habilidades.** Lee `jarvis-operador` (`SKILL.md` y `memoria\lecciones.md`). Desde ahora, todo trabajo con Solid Edge se hace siguiéndolas. Si la sesión no las ve, pídele al usuario que abra una sesión nueva de Claude Code.

**9. Informa al usuario.** Dile:

- qué versión quedó y dónde está el respaldo;
- el resultado de la batería, caso por caso si algo falló;
- qué debe revisar él en pantalla;
- cómo pedirte trabajo a partir de ahora, por ejemplo: «modela esta pieza con este plano», «ensambla estas piezas», «revisa los choques en una vuelta», «hazme el plano».

**10. GitHub.** Esta actualización está en la rama `actualizacion-2026-11-01`; `main` no cambió. Pasarla a `main` es decisión del dueño del repositorio: cuando funcione, pregúntale si quiere fusionarla. Se hace en https://github.com/merinoknights-design/Jarvis/pull/new/actualizacion-2026-11-01 o con git. No la fusiones sin su OK.

## Si algo sale mal

Todo lo reemplazado está en la carpeta `respaldo` del informe (`C:\Jarvis_respaldos\<fecha>_pre_actualizacion\jarvis\`), con las mismas rutas relativas: basta con copiarlo de vuelta a `C:\Jarvis`. Las habilidades anteriores, si las había, están en `skills\` dentro de esa misma carpeta. Los archivos nuevos no estorban a la versión anterior.
