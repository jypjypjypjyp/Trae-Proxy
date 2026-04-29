import threading
import ssl
import logging
from werkzeug.serving import make_server
from trae_proxy import create_app
import trae_proxy
from core.state import AppState

logger = logging.getLogger('trae_proxy')


class ServiceThread(threading.Thread):
    def __init__(self, app_state: AppState):
        super().__init__(daemon=True)
        self.app_state = app_state
        self.server = None
        self._running = False

    def run(self):
        try:
            trae_proxy.load_multi_backend_config()
            if trae_proxy.MULTI_BACKEND_CONFIG:
                self.app_state.set_config(trae_proxy.MULTI_BACKEND_CONFIG)
            config = self.app_state.get_config()
            if not config:
                logger.error("配置加载失败")
                return

            app = create_app(self.app_state)
            port = config.get("server", {}).get("port", 443)
            domain = config.get("domain", "api.openai.com")

            cert_file = f"ca/{domain}.crt"
            key_file = f"ca/{domain}.key"

            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(cert_file, key_file)

            self.server = make_server('0.0.0.0', port, app, ssl_context=context, threaded=True)
            self._running = True
            self.app_state.set_service_running(True)
            logger.info(f"服务启动于 0.0.0.0:{port}")
            self.server.serve_forever()
        except Exception as e:
            logger.error(f"服务线程异常: {e}")
        finally:
            self._running = False
            self.app_state.set_service_running(False)

    def stop(self):
        self._running = False
        self.app_state.set_service_running(False)
        if self.server:
            self.server.shutdown()
            logger.info("服务已停止")

    def is_running(self) -> bool:
        return self._running
