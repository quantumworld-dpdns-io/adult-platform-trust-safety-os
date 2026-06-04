import multiprocessing
import os
import resource
import signal
import time
from typing import Any, Callable, Dict, Optional


class SandboxIsolator:
    def __init__(self):
        self._sandboxes: Dict[str, Dict] = {}
        self._default_limits = {
            "cpu_time": 10,
            "memory": 100 * 1024 * 1024,
            "processes": 10,
            "file_size": 10 * 1024 * 1024,
            "open_files": 64,
        }

    def create_sandbox(self, sandbox_id: Optional[str] = None) -> str:
        if sandbox_id is None:
            sandbox_id = f"sandbox_{int(time.time() * 1000)}"
        self._sandboxes[sandbox_id] = {
            "id": sandbox_id,
            "created_at": time.time(),
            "status": "created",
            "resource_usage": {},
            "limits": dict(self._default_limits),
        }
        return sandbox_id

    def execute_in_sandbox(self, sandbox_id: str, func: Callable,
                            args: tuple = (), kwargs: Optional[Dict] = None,
                            timeout: int = 10) -> Any:
        if sandbox_id not in self._sandboxes:
            raise ValueError(f"Sandbox '{sandbox_id}' not found")
        if kwargs is None:
            kwargs = {}
        result_queue = multiprocessing.Queue()
        def worker(q, f, a, kw):
            try:
                result = f(*a, **kw)
                q.put({"success": True, "result": result})
            except Exception as e:
                q.put({"success": False, "error": str(e)})
        process = multiprocessing.Process(target=worker, args=(result_queue, func, args, kwargs))
        process.start()
        process.join(timeout=timeout)
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)
            if process.is_alive():
                process.kill()
            self._sandboxes[sandbox_id]["status"] = "timeout"
            raise TimeoutError(f"Sandbox execution timed out after {timeout}s")
        if not result_queue.empty():
            result = result_queue.get()
            if result["success"]:
                self._sandboxes[sandbox_id]["status"] = "completed"
                return result["result"]
            else:
                self._sandboxes[sandbox_id]["status"] = "error"
                raise RuntimeError(result["error"])
        self._sandboxes[sandbox_id]["status"] = "completed"
        return None

    def set_resource_limits(self, sandbox_id: str, limits: Dict[str, Any]) -> None:
        if sandbox_id not in self._sandboxes:
            raise ValueError(f"Sandbox '{sandbox_id}' not found")
        self._sandboxes[sandbox_id]["limits"].update(limits)

    def _apply_limits(self, limits: Dict[str, Any]) -> None:
        try:
            if "cpu_time" in limits:
                resource.setrlimit(resource.RLIMIT_CPU, (limits["cpu_time"], limits["cpu_time"]))
            if "memory" in limits:
                resource.setrlimit(resource.RLIMIT_AS, (limits["memory"], limits["memory"]))
            if "file_size" in limits:
                resource.setrlimit(resource.RLIMIT_FSIZE, (limits["file_size"], limits["file_size"]))
            if "open_files" in limits:
                resource.setrlimit(resource.RLIMIT_NOFILE, (limits["open_files"], limits["open_files"]))
        except (ValueError, resource.error):
            pass

    def monitor_resource_usage(self, sandbox_id: str) -> Dict:
        if sandbox_id not in self._sandboxes:
            raise ValueError(f"Sandbox '{sandbox_id}' not found")
        usage = {
            "cpu_time": 0,
            "memory": 0,
            "status": self._sandboxes[sandbox_id]["status"],
            "uptime": time.time() - self._sandboxes[sandbox_id]["created_at"],
        }
        try:
            usage["cpu_time"] = resource.getrusage(resource.RUSAGE_SELF).ru_utime
            usage["memory"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        except Exception:
            pass
        self._sandboxes[sandbox_id]["resource_usage"] = usage
        return usage

    def terminate_sandbox(self, sandbox_id: str) -> bool:
        if sandbox_id not in self._sandboxes:
            return False
        self._sandboxes[sandbox_id]["status"] = "terminated"
        return True

    def list_sandboxes(self) -> list:
        return [
            {"id": sid, "status": info["status"]}
            for sid, info in self._sandboxes.items()
        ]

    def cleanup_sandbox(self, sandbox_id: str) -> bool:
        if sandbox_id in self._sandboxes:
            del self._sandboxes[sandbox_id]
            return True
        return False
