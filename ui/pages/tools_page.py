import flet as ft
import os
import subprocess
from core.state import AppState


class ToolsPage(ft.Column):
    def __init__(self, app_state: AppState):
        super().__init__()
        self.app_state = app_state
        self.expand = True
        self.spacing = 16
        self.padding = 20

        self.cert_result = ft.Text("证书状态: 未检查", size=14)
        self.test_result = ft.Text("测试结果将显示在这里", size=14)

        self.controls = [
            ft.Text("工具", size=24, weight=ft.FontWeight.BOLD),
            # 证书管理
            ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("证书管理", size=16, weight=ft.FontWeight.BOLD),
                            self.cert_result,
                            ft.ElevatedButton("生成/重新生成证书", icon='SECURITY', on_click=self._generate_certs),
                        ],
                        spacing=12,
                    ),
                    padding=16,
                ),
                elevation=2,
            ),
            # 模型测试
            ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("模型连通性测试", size=16, weight=ft.FontWeight.BOLD),
                            ft.Text("选择一个已配置的后端发送测试请求", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Row(
                                [
                                    ft.Dropdown(
                                        label="选择后端",
                                        options=[],
                                        width=200,
                                    ),
                                    ft.ElevatedButton("发送测试", icon='SEND', on_click=self._test_model),
                                ],
                                spacing=12,
                            ),
                            ft.Container(
                                content=self.test_result,
                                bgcolor=ft.Colors.SURFACE_CONTAINER,
                                border_radius=6,
                                padding=12,
                            ),
                        ],
                        spacing=12,
                    ),
                    padding=16,
                ),
                elevation=2,
            ),
            # Hosts 配置
            ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Hosts 配置指引", size=16, weight=ft.FontWeight.BOLD),
                            ft.Text("在 hosts 文件中添加以下行（需要管理员权限）:", size=12),
                            ft.Container(
                                content=ft.Text("127.0.0.1 api.openai.com", selectable=True, font_family="Consolas"),
                                bgcolor=ft.Colors.SURFACE_CONTAINER,
                                border_radius=6,
                                padding=12,
                            ),
                            ft.ElevatedButton("复制到剪贴板", icon='CONTENT_COPY', on_click=self._copy_hosts),
                        ],
                        spacing=12,
                    ),
                    padding=16,
                ),
                elevation=2,
            ),
        ]

    def _generate_certs(self, e):
        try:
            result = subprocess.run(["python", "generate_certs.py"], capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                self.cert_result.value = "证书状态: 生成成功"
                self.cert_result.color = ft.Colors.GREEN
                self.page.show_snack_bar(ft.SnackBar(content=ft.Text("证书生成成功")))
            else:
                self.cert_result.value = f"证书状态: 生成失败 - {result.stderr}"
                self.cert_result.color = ft.Colors.RED
        except Exception as ex:
            self.cert_result.value = f"证书状态: 异常 - {ex}"
            self.cert_result.color = ft.Colors.RED
        self.update()

    def _test_model(self, e):
        self.test_result.value = "测试中..."
        self.update()
        # 这里可以接入实际的测试逻辑
        self.test_result.value = "测试功能需要配置有效 API 密钥和端点后方可使用"
        self.update()

    def _copy_hosts(self, e):
        hosts_line = "127.0.0.1 api.openai.com"
        # 使用 flet 的 clipboard 或系统命令
        try:
            subprocess.run(["powershell", "-command", f"Set-Clipboard -Value '{hosts_line}'"], check=True)
            self.page.show_snack_bar(ft.SnackBar(content=ft.Text("已复制到剪贴板")))
        except Exception:
            self.page.show_snack_bar(ft.SnackBar(content=ft.Text("复制失败")))
