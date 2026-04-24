import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BackendStat:
    name: str = ""
    request_count: int = 0
    success_count: int = 0
    error_count: int = 0
    total_latency_ms: int = 0
    last_latency_ms: int = 0
    avg_latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    last_request_time: str = ""
    tokens_per_second: float = 0.0


class AppState:
    def __init__(self):
        self._lock = threading.Lock()
        self.service_running = False
        self.service_port = 443
        self.active_backend = ""
        self.request_count = 0
        self.last_error: Optional[str] = None
        self.logs: deque[str] = deque(maxlen=500)
        self.config_modified = False
        self.backend_stats: dict[str, BackendStat] = {}
        self.config: dict = {}
        self.exiting = False

    def update_stat(self, name: str, stat: BackendStat):
        with self._lock:
            self.backend_stats[name] = stat

    def get_stats(self) -> dict[str, BackendStat]:
        with self._lock:
            return dict(self.backend_stats)

    def add_log(self, message: str):
        with self._lock:
            self.logs.append(message)

    def get_logs(self) -> list[str]:
        with self._lock:
            return list(self.logs)

    def set_service_running(self, running: bool):
        with self._lock:
            self.service_running = running

    def is_service_running(self) -> bool:
        with self._lock:
            return self.service_running

    def set_config(self, config: dict):
        with self._lock:
            self.config = config
            self.service_port = config.get("server", {}).get("port", 443)

    def get_config(self) -> dict:
        with self._lock:
            return dict(self.config)
