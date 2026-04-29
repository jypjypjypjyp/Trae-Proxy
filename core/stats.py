import time
import logging
from datetime import datetime
from core.state import AppState, BackendStat

logger = logging.getLogger('trae_proxy')


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 3)


class RequestTracker:
    def __init__(self, app_state: AppState, backend_name: str):
        self.app_state = app_state
        self.backend_name = backend_name
        self.start_time = 0.0
        self.input_tokens = 0
        self.output_tokens = 0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def set_input(self, messages: list):
        text = ""
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                text += content
        self.input_tokens = estimate_tokens(text)

    def set_output(self, content: str):
        self.output_tokens = estimate_tokens(content)

    def finalize_output_stats(self):
        """流式响应专用：__exit__ 执行时 stream 还没消费完，
        output_tokens 为 0，tokens_per_second 也为 0。
        在 generate_stream 消费完流后手动修正这两个值。"""
        if self.output_tokens <= 0:
            return
        total_ms = int((time.time() - self.start_time) * 1000)
        stats = self.app_state.get_stats()
        stat = stats.get(self.backend_name)
        if stat is None:
            return
        stat.output_tokens += self.output_tokens
        if total_ms > 0:
            stat.tokens_per_second = round(self.output_tokens / (total_ms / 1000), 1)
        self.app_state.update_stat(self.backend_name, stat)
        logger.info(f"[stats] finalize_output_stats: backend={self.backend_name}, "
                     f"output_tokens={stat.output_tokens}, tokens_per_second={stat.tokens_per_second}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        latency_ms = int((time.time() - self.start_time) * 1000)
        success = exc_type is None

        stats = self.app_state.get_stats()
        stat = stats.get(self.backend_name, BackendStat(name=self.backend_name))

        stat.request_count += 1
        stat.last_latency_ms = latency_ms
        stat.total_latency_ms += latency_ms
        if stat.request_count > 0:
            stat.avg_latency_ms = stat.total_latency_ms / stat.request_count
        stat.input_tokens += self.input_tokens
        stat.output_tokens += self.output_tokens
        stat.last_request_time = datetime.now().strftime("%H:%M:%S")

        if self.output_tokens > 0 and latency_ms > 0:
            stat.tokens_per_second = round(self.output_tokens / (latency_ms / 1000), 1)

        if success:
            stat.success_count += 1
        else:
            stat.error_count += 1

        self.app_state.update_stat(self.backend_name, stat)
        self.app_state.request_count += 1
        logger.info(f"[stats] RequestTracker 记录: backend={self.backend_name}, "
                     f"request_count={stat.request_count}, success={success}, "
                     f"latency={latency_ms}ms")
