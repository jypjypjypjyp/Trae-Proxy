import flet as ft
from core.state import AppState


class LogsPage(ft.Column):
    def __init__(self, app_state: AppState):
        super().__init__()
        self.app_state = app_state
        self.expand = True
        self.spacing = 12
        self.padding = 20

        self.log_text = ft.TextField(
            multiline=True,
            read_only=True,
            min_lines=20,
            expand=True,
            border_color=ft.Colors.OUTLINE,
        )

        self.filter_info = ft.Checkbox(label="INFO", value=True)
        self.filter_error = ft.Checkbox(label="ERROR", value=True)
        self.filter_debug = ft.Checkbox(label="DEBUG", value=False)
        self.auto_scroll = ft.Switch(label="自动滚动", value=True)

        self.controls = [
            ft.Text("日志", size=24, weight=ft.FontWeight.BOLD),
            ft.Row(
                [
                    ft.Text("筛选:", size=14),
                    self.filter_info,
                    self.filter_error,
                    self.filter_debug,
                    ft.Container(expand=True),
                    self.auto_scroll,
                    ft.IconButton(icon='CLEAR_ALL', tooltip="清空", on_click=self._clear_logs),
                ],
                spacing=8,
            ),
            ft.Container(
                content=self.log_text,
                border=ft.border.all(1, ft.Colors.OUTLINE),
                border_radius=8,
                expand=True,
            ),
        ]

    def refresh(self):
        logs = self.app_state.get_logs()
        filtered = []
        for log in logs:
            if "ERROR" in log and self.filter_error.value:
                filtered.append(log)
            elif "DEBUG" in log and self.filter_debug.value:
                filtered.append(log)
            elif "INFO" in log and self.filter_info.value:
                filtered.append(log)
            elif not any(t in log for t in ["INFO", "ERROR", "DEBUG"]):
                if self.filter_info.value:
                    filtered.append(log)

        text = "\n".join(filtered)
        self.log_text.value = text
        if self.auto_scroll.value:
            self.log_text.scroll_offset = float('inf')

    def _clear_logs(self, e):
        self.app_state.logs.clear()
        self.log_text.value = ""
        self.update()
