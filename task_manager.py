import threading
import time
import uuid
from typing import Callable, Dict, Any, List

# Cola de notificaciones pendientes para que Jarvis avise por voz y chat apenas termine una tarea en 2do plano
COMPLETED_NOTIFICATIONS: List[Dict[str, Any]] = []
ACTIVE_TASKS: Dict[str, Dict[str, Any]] = {}
_lock = threading.Lock()


def run_background_task(title: str, worker_fn: Callable[[], str], tool_name: str = "filesystem") -> str:
    """
    Lanza cualquier proceso pesado (CAD Solid Edge, Spotify UI Automation, Descargas, Análisis)
    en un hilo independiente en segundo plano y encola un aviso automático cuando termina.
    """
    task_id = str(uuid.uuid4())[:8]
    with _lock:
        ACTIVE_TASKS[task_id] = {
            "id": task_id,
            "title": title,
            "status": "running",
            "started_at": time.time(),
            "tool": tool_name,
        }

    def _runner():
        try:
            result_message = worker_fn()
            with _lock:
                if task_id in ACTIVE_TASKS:
                    del ACTIVE_TASKS[task_id]
                COMPLETED_NOTIFICATIONS.append({
                    "id": task_id,
                    "title": title,
                    "message": f"🔔 Tarea finalizada ({title}):\n{result_message}",
                    "voice_summary": f"Señor, le informo que ya terminé la tarea: {title}.",
                    "tool_used": tool_name,
                    "status": "done"
                })
        except Exception as e:
            with _lock:
                if task_id in ACTIVE_TASKS:
                    del ACTIVE_TASKS[task_id]
                COMPLETED_NOTIFICATIONS.append({
                    "id": task_id,
                    "title": title,
                    "message": f"⚠️ Aviso en tarea ({title}): {e}",
                    "voice_summary": f"Señor, hubo un detalle al completar la tarea {title}.",
                    "tool_used": tool_name,
                    "status": "error"
                })

    t = threading.Thread(target=_runner, daemon=True)
    t.start()
    return task_id


def pop_completed_notifications() -> Dict[str, Any]:
    """Devuelve todas las tareas recién terminadas para que el frontend las anuncie en voz alta."""
    with _lock:
        done = list(COMPLETED_NOTIFICATIONS)
        COMPLETED_NOTIFICATIONS.clear()
        running = list(ACTIVE_TASKS.values())
    return {
        "completed": done,
        "active_tasks": running
    }
