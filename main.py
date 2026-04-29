#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import threading
import logging
from core.state import AppState, install_log_handler
from core.service import ServiceThread
from core.tray import TrayThread
from ui.app import run_ui

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('trae_proxy')


def main():
    app_state = AppState()
    install_log_handler(app_state)

    service = ServiceThread(app_state)
    service.start()
    time.sleep(0.5)

    service_holder = [service]
    _need_show = threading.Event()

    def on_toggle_service(restart=False):
        current = service_holder[0]
        if current.is_running():
            logger.info("停止服务...")
            current.stop()
            current.join(timeout=3)
        if restart:
            logger.info("启动服务...")
            new_service = ServiceThread(app_state)
            service_holder[0] = new_service
            new_service.start()

    def on_exit():
        logger.info("正在退出...")
        app_state.exiting = True
        service_holder[0].stop()
        _need_show.set()

    def on_show_ui():
        _need_show.set()

    tray = TrayThread(app_state, on_toggle_service, on_exit, on_show_ui)
    threading.Thread(target=tray.run, daemon=True).start()

    run_ui(app_state)

    while not app_state.exiting:
        _need_show.clear()
        _need_show.wait()
        if not app_state.exiting:
            run_ui(app_state)


if __name__ == "__main__":
    main()