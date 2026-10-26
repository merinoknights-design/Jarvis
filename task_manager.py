import threading
import time
import uuid
from typing import Callable, Dict, Any, List

COMPLETED_NOTIFICATIONS: List[Dict[str, Any]] = []
ACTIVE_TASKS: Dict[str, Dict[str, Any]] = {}
_lock = threading.Lock()


def has_active_tasks() -> bool:
    with _lock:
        return len(ACTIVE_TASKS) > 0


def execute_smart_task(
    title: str,
    worker_fn: Callable[[], str],
    tool_name: str = "filesystem",
    force_background: bool = False,
    notify_on_complete: bool = False,
) -> Dict[str, Any]:
    """
    Si NO hay otra tarea corriendo y es 1 sola orden:
      - La lanza directamente sin decir 'en segundo plano'.
      - Si notify_on_complete=True (flujos multi-paso como redactar borrador, comentar en YouTube, mandar WhatsApp),
        avisa al usuario apenas termina todos los pasos ("Ya terminé la acción, Señor").
    Si YA hay una tarea corriendo (2 o más tareas simultáneas) o force_background=True:
      - La corre en cola en segundo plano y avisa al terminar.
    """
    already_busy = has_active_tasks() or force_background
    task_id = str(uuid.uuid4())[:8]

    if not already_busy and not notify_on_complete:
        with _lock:
            ACTIVE_TASKS[task_id] = {"id": task_id, "title": title, "status": "running", "tool": tool_name}

        def _silent_worker():
            try:
                worker_fn()
            finally:
                with _lock:
                    ACTIVE_TASKS.pop(task_id, None)

        threading.Thread(target=_silent_worker, daemon=True).start()
        return {
            "queued_in_background": False,
            "task_id": task_id
        }

    with _lock:
        ACTIVE_TASKS[task_id] = {"id": task_id, "title": title, "status": "running", "tool": tool_name}

    def _notifying_worker():
        try:
            result_message = worker_fn()
            with _lock:
                ACTIVE_TASKS.pop(task_id, None)
                COMPLETED_NOTIFICATIONS.append({
                    "id": task_id,
                    "title": title,
                    "message": f"✅ {result_message}",
                    "voice_summary": result_message if len(str(result_message)) < 140 else f"Ya terminé la acción de {title}, Señor.",
                    "tool_used": tool_name,
                    "status": "done"
                })
        except Exception as e:
            with _lock:
                ACTIVE_TASKS.pop(task_id, None)
                COMPLETED_NOTIFICATIONS.append({
                    "id": task_id,
                    "title": title,
                    "message": f"⚠️ Detalle en {title}: {e}",
                    "voice_summary": f"Hubo un detalle en {title}, Señor.",
                    "tool_used": tool_name,
                    "status": "error"
                })

    threading.Thread(target=_notifying_worker, daemon=True).start()
    return {
        "queued_in_background": already_busy,
        "task_id": task_id
    }


def pop_completed_notifications() -> Dict[str, Any]:
    with _lock:
        done = list(COMPLETED_NOTIFICATIONS)
        COMPLETED_NOTIFICATIONS.clear()
        running = list(ACTIVE_TASKS.values())
    return {
        "completed": done,
        "active_tasks": running
    }
