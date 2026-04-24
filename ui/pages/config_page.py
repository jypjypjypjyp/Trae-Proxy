import flet as ft
import yaml
import os
from core.state import AppState


class ConfigPage(ft.Column):
    def __init__(self, app_state: AppState):
        super().__init__()
        self.app_state = app_state
        self.expand = True
        self.spacing = 16
        self.padding = 20

        # 代理设置
        self.domain_field = ft.TextField(label="代理域名", value="api.openai.com", width=300)
        self.port_field = ft.TextField(label="端口", value="443", width=120, keyboard_type=ft.KeyboardType.NUMBER)
        self.debug_switch = ft.Switch(label="调试模式", value=False)

        # 后端列表
        self.backend_list = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
        self.backends = []

        self.controls = [
            ft.Text("配置", size=24, weight=ft.FontWeight.BOLD),
            ft.Text("代理设置", size=16, weight=ft.FontWeight.BOLD),
            ft.Row([self.domain_field, self.port_field, self.debug_switch], spacing=16),
            ft.Divider(),
            ft.Row(
                [
                    ft.Text("后端列表", size=16, weight=ft.FontWeight.BOLD),
                    ft.ElevatedButton("+ 添加后端", icon='ADD', on_click=self._add_backend),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Container(
                content=self.backend_list,
                border=ft.border.all(1, ft.Colors.OUTLINE),
                border_radius=8,
                padding=12,
                expand=True,
            ),
            ft.Row(
                [
                    ft.ElevatedButton("保存配置", icon='SAVE', on_click=self._save_config, bgcolor=ft.Colors.PRIMARY, color=ft.Colors.ON_PRIMARY),
                    ft.Text("保存后需重启服务生效", size=12, color=ft.Colors.ON_SURFACE_VARIANT, italic=True),
                ],
                spacing=12,
            ),
        ]

        self._load_config()

    def _load_config(self):
        config = self.app_state.get_config()
        if not config:
            # 尝试从文件读取
            if os.path.exists("config.yaml"):
                with open("config.yaml", "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)

        if config:
            self.domain_field.value = config.get("domain", "api.openai.com")
            server = config.get("server", {})
            self.port_field.value = str(server.get("port", 443))
            self.debug_switch.value = server.get("debug", False)
            self.backends = config.get("apis", [])
            self._refresh_backend_list()

    def _refresh_backend_list(self):
        self.backend_list.controls.clear()
        for i, api in enumerate(self.backends):
            row = ft.Container(
                content=ft.Row(
                    [
                        ft.TextField(value=api.get("name", ""), label="名称", width=120, dense=True),
                        ft.TextField(value=api.get("endpoint", ""), label="Endpoint", width=200, dense=True),
                        ft.TextField(value=api.get("custom_model_id", ""), label="Custom Model", width=140, dense=True),
                        ft.TextField(value=api.get("target_model_id", ""), label="Target Model", width=140, dense=True),
                        ft.Dropdown(
                            label="Stream",
                            value=str(api.get("stream_mode", "null")),
                            options=[
                                ft.dropdown.Option("null", "默认"),
                                ft.dropdown.Option("true", "启用"),
                                ft.dropdown.Option("false", "禁用"),
                            ],
                            width=100,
                        ),
                        ft.Switch(label="启用", value=api.get("active", True)),
                        ft.IconButton(icon='DELETE', icon_color=ft.Colors.RED, tooltip="删除", data=i, on_click=self._remove_backend),
                    ],
                    spacing=8,
                ),
                padding=8,
                border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
                border_radius=6,
            )
            self.backend_list.controls.append(row)
        try:
            if self.page:
                self.update()
        except RuntimeError:
            pass

    def _add_backend(self, e):
        self.backends.append({
            "name": f"backend-{len(self.backends) + 1}",
            "endpoint": "",
            "custom_model_id": "",
            "target_model_id": "",
            "stream_mode": None,
            "active": True,
        })
        self._refresh_backend_list()

    def _remove_backend(self, e):
        idx = e.control.data
        if 0 <= idx < len(self.backends):
            self.backends.pop(idx)
            self._refresh_backend_list()

    def _save_config(self, e):
        # 从 UI 收集数据
        new_backends = []
        for row in self.backend_list.controls:
            controls = row.content.controls
            new_backends.append({
                "name": controls[0].value,
                "endpoint": controls[1].value,
                "custom_model_id": controls[2].value,
                "target_model_id": controls[3].value,
                "stream_mode": None if controls[4].value == "null" else controls[4].value,
                "active": controls[5].value,
            })

        config = {
            "domain": self.domain_field.value,
            "apis": new_backends,
            "server": {
                "port": int(self.port_field.value or 443),
                "debug": self.debug_switch.value,
            }
        }

        with open("config.yaml", "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, sort_keys=False)

        self.app_state.set_config(config)
        self.page.show_snack_bar(ft.SnackBar(content=ft.Text("配置已保存，重启服务生效")))
