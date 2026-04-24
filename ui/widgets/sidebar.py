import flet as ft


class Sidebar(ft.Container):
    def __init__(self, on_navigate):
        super().__init__()
        self.on_navigate = on_navigate
        self.selected_index = 0
        self.width = 180
        self.bgcolor = ft.Colors.SURFACE_CONTAINER
        self.padding = 10

        self.nav_items = [
            ("概览", 'DASHBOARD'),
            ("配置", 'SETTINGS'),
            ("日志", 'ARTICLE'),
            ("工具", 'BUILD'),
        ]

        self.content = ft.Column(
            [
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon('ROCKET_LAUNCH', color=ft.Colors.PRIMARY, size=24),
                            ft.Text("Trae Proxy", size=16, weight=ft.FontWeight.BOLD),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    padding=ft.padding.symmetric(vertical=15),
                ),
                ft.Divider(height=1),
                *self._build_nav_buttons(),
            ],
            spacing=4,
            alignment=ft.MainAxisAlignment.START,
            expand=True,
        )

    def _build_nav_buttons(self):
        buttons = []
        for i, (label, icon) in enumerate(self.nav_items):
            btn = ft.Container(
                content=ft.Row(
                    [ft.Icon(icon, size=20), ft.Text(label, size=14)],
                    spacing=12,
                ),
                padding=ft.padding.symmetric(horizontal=12, vertical=10),
                border_radius=8,
                bgcolor=ft.Colors.PRIMARY if i == 0 else None,
                on_click=lambda e, idx=i: self._on_click(e, idx),
                animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            )
            buttons.append(btn)
        return buttons

    def _on_click(self, e, index):
        self.selected_index = index
        # 更新按钮样式
        col = self.content
        for i, child in enumerate(col.controls):
            if isinstance(child, ft.Container) and i >= 2:
                child.bgcolor = ft.Colors.PRIMARY if (i - 2) == index else None
        self.update()
        self.on_navigate(index)
