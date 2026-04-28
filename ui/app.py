import flet as ft
import threading
import logging
from core.state import AppState

logger = logging.getLogger('trae_proxy')


def run_ui(app_state: AppState):
    def main(page: ft.Page):
        page.title = "Trae Proxy"
        page.theme_mode = ft.ThemeMode.SYSTEM
        page.window.width = 800
        page.window.height = 500
        page.padding = 0

        status_dot = ft.Text("●", size=16)
        status_label = ft.Text("服务: 已停止", size=14)
        req_label = ft.Text("请求: 0", size=14)
        auto_scroll = ft.Switch(label="自动滚动", value=True)
        log_text = ft.TextField(
            multiline=True, read_only=True, min_lines=10, max_lines=30,
            expand=True, border=ft.InputBorder.NONE, text_size=12,
        )

        _closing = False

        def refresh():
            nonlocal _closing
            try:
                if app_state.exiting:
                    if not _closing:
                        _closing = True
                        page.run_task(page.window.close)
                    return
                running = app_state.is_service_running()
                status_dot.color = ft.Colors.GREEN if running else ft.Colors.RED
                status_label.value = f"服务: {'运行中' if running else '已停止'}"
                status_label.color = ft.Colors.GREEN if running else ft.Colors.RED
                req_label.value = f"请求: {app_state.request_count}"
                logs = app_state.get_logs()
                log_text.value = "\n".join(logs[-200:])
                if auto_scroll.value:
                    log_text.scroll_offset = float('inf')
                page.update()
            except Exception:
                pass

        def schedule():
            refresh()
            if not app_state.exiting:
                threading.Timer(2.0, schedule).start()

        threading.Timer(2.0, schedule).start()

        def clear_logs(e):
            app_state.logs.clear()
            log_text.value = ""
            page.update()

        page.add(
            ft.Column(
                [
                    ft.Container(
                        content=ft.Row(
                            [
                                status_dot,
                                status_label,
                                ft.VerticalDivider(width=1),
                                req_label,
                                ft.Container(expand=True),
                                auto_scroll,
                                ft.TextButton("清空日志", on_click=clear_logs, style=ft.ButtonStyle(padding=5)),
                            ],
                            spacing=8,
                        ),
                        padding=ft.padding.symmetric(horizontal=16, vertical=8),
                        border=ft.border.only(bottom=ft.border.BorderSide(1, ft.Colors.OUTLINE)),
                    ),
                    ft.Container(content=log_text, expand=True, padding=16),
                ],
                expand=True,
                spacing=0,
            )
        )

    ft.app(target=main)
