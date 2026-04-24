import flet as ft
from core.state import AppState


class StatusBar(ft.Container):
    def __init__(self, app_state: AppState):
        super().__init__()
        self.app_state = app_state
        self.height = 32
        self.bgcolor = ft.Colors.SURFACE
        self.border = ft.border.only(top=ft.border.BorderSide(1, ft.Colors.OUTLINE))
        self.padding = ft.padding.symmetric(horizontal=16)

        self.status_text = ft.Text("服务: 未启动", size=12)
        self.port_text = ft.Text("端口: -", size=12)
        self.backend_text = ft.Text("后端: -", size=12)
        self.req_text = ft.Text("请求: 0", size=12)

        self.content = ft.Row(
            [
                self.status_text,
                ft.VerticalDivider(width=1, color=ft.Colors.OUTLINE),
                self.port_text,
                ft.VerticalDivider(width=1, color=ft.Colors.OUTLINE),
                self.backend_text,
                ft.VerticalDivider(width=1, color=ft.Colors.OUTLINE),
                self.req_text,
            ],
            alignment=ft.MainAxisAlignment.START,
            spacing=12,
        )

    def refresh(self):
        running = self.app_state.is_service_running()
        self.status_text.value = f"服务: {'运行中' if running else '已停止'}"
        self.status_text.color = ft.Colors.GREEN if running else ft.Colors.RED
        self.port_text.value = f"端口: {self.app_state.service_port}"
        self.backend_text.value = f"后端: {self.app_state.active_backend or '-'}"
        self.req_text.value = f"请求: {self.app_state.request_count}"
