import os
import threading
import pystray
from PIL import Image, ImageDraw
from pystray import MenuItem, Menu
from core.state import AppState


class TrayThread:
    def __init__(self, app_state: AppState, on_toggle_service, on_exit, on_show_ui):
        self.app_state = app_state
        self.on_toggle_service = on_toggle_service
        self.on_exit = on_exit
        self.on_show_ui = on_show_ui
        self.icon = None

    def _create_image(self):
        path = os.path.join(os.path.dirname(__file__), "..", "asset", "logo.png")
        if os.path.exists(path):
            return Image.open(path).convert("RGBA")
        img = Image.new('RGBA', (64, 64), color=(59, 130, 246, 255))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([12, 12, 52, 52], radius=8, fill=(255, 255, 255, 255))
        return img

    def _get_menu(self):
        running = self.app_state.is_service_running()
        toggle_text = "停止服务" if running else "启动服务"
        return Menu(
            MenuItem("显示窗口", lambda icon, item: self.on_show_ui()),
            MenuItem(toggle_text, lambda icon, item: self.on_toggle_service()),
            MenuItem("重启服务", lambda icon, item: self.on_toggle_service(restart=True)),
            Menu.SEPARATOR,
            MenuItem(f"服务: {'运行中' if running else '已停止'}", lambda i, m: None, enabled=False),
            MenuItem(f"请求: {self.app_state.request_count}", lambda i, m: None, enabled=False),
            Menu.SEPARATOR,
            MenuItem("退出", lambda icon, item: self.on_exit()),
        )

    def run(self):
        self.icon = pystray.Icon(
            "trae_proxy", self._create_image(), "Trae Proxy", self._get_menu()
        )

        def _poll():
            while self.icon is not None:
                self.update_menu()
                threading.Event().wait(3)

        threading.Thread(target=_poll, daemon=True).start()
        self.icon.run()

    def stop(self):
        if self.icon:
            self.icon.stop()
            self.icon = None

    def update_menu(self):
        if self.icon:
            self.icon.menu = self._get_menu()
            self.icon.update_menu()
