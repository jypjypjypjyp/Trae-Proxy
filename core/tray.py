import threading
import pystray
from PIL import Image, ImageDraw
import os
from pystray import MenuItem, Menu
from core.state import AppState


class TrayThread(threading.Thread):
    def __init__(self, app_state: AppState, on_show, on_toggle_service, on_exit):
        super().__init__(daemon=True)
        self.app_state = app_state
        self.on_show = on_show
        self.on_toggle_service = on_toggle_service
        self.on_exit = on_exit
        self.icon = None
        self._stop_event = threading.Event()

    def _create_image(self):
        path = os.path.join(os.path.dirname(__file__), "..", "asset", "logo.png")
        if os.path.exists(path):
            return Image.open(path).convert("RGBA")
        # fallback: 生成简单图标
        img = Image.new('RGBA', (64, 64), color=(59, 130, 246, 255))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([12, 12, 52, 52], radius=8, fill=(255, 255, 255, 255))
        return img

    def _get_menu(self):
        running = self.app_state.is_service_running()
        status_text = f"状态: {'运行中' if running else '已停止'}"
        toggle_text = "停止服务" if running else "启动服务"

        return Menu(
            MenuItem("显示主窗口", lambda icon, item: self.on_show()),
            MenuItem(toggle_text, lambda icon, item: self.on_toggle_service()),
            MenuItem("重启服务", lambda icon, item: self.on_toggle_service(restart=True)),
            Menu.SEPARATOR,
            MenuItem(status_text, lambda icon, item: None, enabled=False),
            MenuItem(f"端口: {self.app_state.service_port}", lambda icon, item: None, enabled=False),
            MenuItem(f"请求: {self.app_state.request_count}", lambda icon, item: None, enabled=False),
            Menu.SEPARATOR,
            MenuItem("退出", lambda icon, item: self.on_exit()),
        )

    def run(self):
        self.icon = pystray.Icon(
            "trae_proxy",
            self._create_image(),
            "Trae Proxy",
            self._get_menu()
        )
        self.icon.run()

    def stop(self):
        if self.icon:
            self.icon.stop()
        self._stop_event.set()

    def update_menu(self):
        if self.icon:
            self.icon.menu = self._get_menu()
            self.icon.update_menu()
