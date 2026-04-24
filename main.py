#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import logging
from core.state import AppState
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

    # 启动服务线程
    service = ServiceThread(app_state)
    service.start()
    time.sleep(0.5)  # 给服务一点时间初始化

    # 使用可变对象包装，以便在闭包中修改
    service_holder = [service]

    # 托盘回调
    def on_show():
        pass  # UI 启动后会设置实际回调

    def on_toggle_service(restart=False):
        current = service_holder[0]
        if current.is_running() or restart:
            logger.info("停止服务...")
            current.stop()
            current.join(timeout=3)
        if not current.is_running() or restart:
            logger.info("启动服务...")
            new_service = ServiceThread(app_state)
            service_holder[0] = new_service
            new_service.start()

    def on_exit():
        logger.info("正在退出...")
        app_state.exiting = True
        service_holder[0].stop()
        tray.stop()
        os._exit(0)

    # 启动托盘线程
    tray = TrayThread(app_state, on_show, on_toggle_service, on_exit)
    tray.start()

    # 启动 UI（阻塞主线程）
    try:
        run_ui(app_state, tray)
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("清理资源...")
        service_holder[0].stop()
        tray.stop()
        sys.exit(0)


if __name__ == "__main__":
    main()
