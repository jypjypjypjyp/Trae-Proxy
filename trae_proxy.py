#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, request, Response, jsonify, stream_with_context
import requests
import json
import ssl
import logging
import os
import sys
import yaml
from datetime import datetime

from core.state import AppState
from core.stats import RequestTracker

MULTI_BACKEND_CONFIG = None
APP_STATE = None

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('trae_proxy')


def create_app(app_state: AppState = None):
    global APP_STATE
    APP_STATE = app_state

    app = Flask(__name__)

    @app.route('/', methods=['GET'])
    def root():
        return jsonify({
            "message": "Welcome to the OpenAI API! Documentation is available at https://platform.openai.com/docs/api-reference"
        })

    @app.route('/v1', methods=['GET'])
    def v1_root():
        return jsonify({
            "message": "OpenAI API v1 endpoint",
            "endpoints": {
                "chat/completions": "/v1/chat/completions"
            }
        })

    @app.route('/v1/models', methods=['GET'])
    def list_models():
        try:
            models = []
            if MULTI_BACKEND_CONFIG:
                apis = MULTI_BACKEND_CONFIG.get('apis', [])
                for api in apis:
                    if api.get('active', False):
                        models.append({
                            "id": api.get('custom_model_id', ''),
                            "object": "model",
                            "created": 1,
                            "owned_by": "trae-proxy"
                        })
            return jsonify({"object": "list", "data": models})
        except Exception as e:
            logger.error(f"列出模型时发生错误: {str(e)}")
            return jsonify({"error": f"内部服务器错误: {str(e)}"}), 500

    @app.route('/v1/chat/completions', methods=['POST'])
    def chat_completions():
        selected_backend = None
        custom_model_id = ""
        target_model_id = ""
        target_api_url = ""
        stream_mode = None

        try:
            DEBUG_MODE = MULTI_BACKEND_CONFIG['server'].get('debug', False)
            content_type = request.headers.get('Content-Type', '')
            if 'application/json' not in content_type:
                return jsonify({"error": "Content-Type必须为application/json"}), 400

            try:
                req_json = request.json
                if req_json is None:
                    return jsonify({"error": "无效的JSON请求体"}), 400
            except Exception as e:
                return jsonify({"error": f"JSON解析失败: {str(e)}"}), 400

            if DEBUG_MODE:
                debug_log(f"请求头: {dict(request.headers)}")
                debug_log(f"请求体: {json.dumps(req_json, ensure_ascii=False)}")

            requested_model = req_json.get('model', '')
            selected_backend = select_backend_by_model(requested_model)

            if selected_backend:
                target_api_url = selected_backend.get('endpoint', '').strip()
                target_model_id = selected_backend.get('target_model_id', '').strip()
                custom_model_id = selected_backend.get('custom_model_id', '').strip()
                stream_mode = selected_backend.get('stream_mode')
                logger.info(f"选择后端: {selected_backend['name']} -> {target_api_url}")

                if 'model' in req_json:
                    original_model = req_json['model']
                    req_json['model'] = target_model_id
                    debug_log(f"模型ID从 {original_model} 修改为 {target_model_id}")
                else:
                    req_json['model'] = target_model_id
                    debug_log(f"添加模型ID: {target_model_id}")

                if stream_mode is not None:
                    original_stream = req_json.get('stream', False)
                    req_json['stream'] = stream_mode == 'true'
                    debug_log(f"流模式从 {original_stream} 修改为 {req_json['stream']}")

            backend_name = selected_backend['name'] if selected_backend else 'default'
            with RequestTracker(APP_STATE, backend_name) as tracker:
                tracker.set_input(req_json.get('messages', []))

                headers = {'Content-Type': 'application/json'}
                auth_token = os.environ.get('ANTHROPIC_AUTH_TOKEN', '')
                if auth_token:
                    headers['Authorization'] = f'Bearer {auth_token}'
                else:
                    auth_header = request.headers.get('Authorization')
                    if auth_header:
                        headers['Authorization'] = auth_header

                target_url = f"{target_api_url}/v1/chat/completions"
                debug_log(f"转发请求到: {target_url}")

                verify_ssl = selected_backend.get('verify_ssl', True) if selected_backend else True

                try:
                    response = requests.post(
                        target_url,
                        json=req_json,
                        headers=headers,
                        stream=req_json.get('stream', False),
                        timeout=600,
                        verify=verify_ssl
                    )
                except requests.exceptions.Timeout as e:
                    logger.error(f"请求超时：{target_url}, 超时：{str(e)}")
                    return jsonify({"error": "请求超时，请稍后重试"}), 504
                except requests.exceptions.SSLError as e:
                    logger.error(f"SSL 错误：{str(e)}")
                    return jsonify({"error": f"SSL 错误：{str(e)}"}), 503
                except requests.exceptions.ConnectionError as e:
                    logger.error(f"连接错误：{str(e)}")
                    return jsonify({"error": f"连接错误：{str(e)}"}), 503
                except requests.exceptions.RequestException as e:
                    logger.error(f"请求异常：{str(e)}")
                    return jsonify({"error": f"请求异常：{str(e)}"}), 503

                try:
                    response.raise_for_status()
                except requests.exceptions.HTTPError as e:
                    status_code = e.response.status_code
                    logger.error(f"HTTP 错误 {status_code}: {target_url}")
                    try:
                        error_json = e.response.json()
                        return jsonify(error_json), status_code
                    except:
                        return jsonify({"error": f"HTTP 错误：{status_code}"}), status_code

                if req_json.get('stream', False):
                    debug_log("返回流式响应")
                    try:
                        return Response(
                            stream_with_context(generate_stream(response, tracker, APP_STATE)),
                            content_type=response.headers.get('Content-Type', 'text/event-stream')
                        )
                    except Exception as e:
                        logger.error(f"流式响应处理失败：{str(e)}")
                        raise
                else:
                    response_json = response.json()
                    if DEBUG_MODE:
                        debug_log(f"响应体: {json.dumps(response_json, ensure_ascii=False)}")

                    # 统计输出token
                    content = ""
                    try:
                        content = response_json["choices"][0]["message"]["content"]
                    except:
                        pass
                    tracker.set_output(content)

                    if stream_mode == 'false':
                        debug_log("模拟流式响应")
                        return Response(
                            stream_with_context(simulate_stream(response_json, custom_model_id)),
                            content_type='text/event-stream'
                        )

                    if 'model' in response_json:
                        response_json['model'] = custom_model_id
                    return jsonify(response_json)

        except Exception as e:
            logger.error(f"处理请求时发生错误：{str(e)}")
            return jsonify({"error": f"内部服务器错误：{str(e)}"}), 500

    return app


def generate_stream(response, tracker=None, app_state=None):
    try:
        buffer = ""
        output_content = ""
        for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
            if chunk:
                buffer += chunk
                while "\n\n" in buffer:
                    event, buffer = buffer.split("\n\n", 1)
                    if "event: progress_notice" in event or "event: context_usage" in event:
                        log_content = event.replace('\n', ' | ')
                        logger.debug(f"Discarded unsupported SSE event: {log_content}")
                        debug_log(f"Discarded unsupported SSE event: {log_content}")
                        continue
                    # 累加输出内容用于统计
                    if tracker and "data:" in event:
                        try:
                            data_str = event.split("data:", 1)[1].strip()
                            data_json = json.loads(data_str)
                            delta = data_json.get("choices", [{}])[0].get("delta", {})
                            output_content += delta.get("content", "")
                        except:
                            pass
                    yield (event + "\n\n").encode("utf-8")
        if buffer.strip():
            yield (buffer + "\n\n").encode("utf-8")
        if tracker:
            tracker.set_output(output_content)
    except requests.exceptions.ConnectionError as e:
        logger.error(f"流式响应连接中断：{str(e)}")
        raise
    except Exception as e:
        logger.error(f"流式响应异常：{str(e)}")
        raise


def simulate_stream(response_json, model_id):
    try:
        content = response_json["choices"][0]["message"]["content"]
        first_chunk = {
            "id": "chatcmpl-simulated",
            "object": "chat.completion.chunk",
            "created": 1,
            "model": model_id,
            "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]
        }
        yield f"data: {json.dumps(first_chunk, ensure_ascii=False)}\n\n".encode("utf-8")
        for i in range(0, len(content), 4):
            chunk = content[i:i+4]
            data = {
                "id": "chatcmpl-simulated",
                "object": "chat.completion.chunk",
                "created": 1,
                "model": model_id,
                "choices": [{"index": 0, "delta": {"content": chunk}, "finish_reason": None}]
            }
            yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8")
        end_chunk = {
            "id": "chatcmpl-simulated",
            "object": "chat.completion.chunk",
            "created": 1,
            "model": model_id,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
        }
        yield f"data: {json.dumps(end_chunk, ensure_ascii=False)}\n\n".encode("utf-8")
        yield b"data: [DONE]\n\n"
    except Exception as e:
        logger.error(f"模拟流式响应失败: {e}")
        err = {"error": f"模拟流式响应失败: {str(e)}"}
        yield f"data: {json.dumps(err, ensure_ascii=False)}\n\n".encode("utf-8")


def debug_log(message):
    if MULTI_BACKEND_CONFIG and MULTI_BACKEND_CONFIG.get('server', {}).get('debug', False):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        with open("debug_request.log", "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
        logger.debug(message)


def load_multi_backend_config():
    global MULTI_BACKEND_CONFIG
    try:
        config_file = "config.yaml"
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                MULTI_BACKEND_CONFIG = config
                base_url = os.environ.get('ANTHROPIC_BASE_URL', '')
                for api in config.get('apis', []):
                    if not api.get('endpoint') and base_url:
                        api['endpoint'] = base_url
                if base_url:
                    logger.info(f"已从环境变量 ANTHROPIC_BASE_URL 加载 endpoint: {base_url}")
                logger.info(f"已加载多后端配置，共 {len(config.get('apis', []))} 个API配置")
                if APP_STATE:
                    APP_STATE.set_config(config)
                return True
        else:
            logger.warning("配置文件不存在，使用单后端模式")
            return False
    except Exception as e:
        logger.error(f"加载多后端配置失败: {str(e)}")
        return False


def select_backend_by_model(requested_model):
    if not MULTI_BACKEND_CONFIG:
        return None
    apis = MULTI_BACKEND_CONFIG.get('apis', [])
    for api in apis:
        if api.get('active', False) and api.get('custom_model_id') == requested_model:
            logger.info(f"根据模型ID匹配到后端: {api['name']} -> {api['endpoint']}")
            return api
    for api in apis:
        if api.get('active', False):
            logger.info(f"使用默认激活后端: {api['name']} -> {api['endpoint']}")
            return api
    if apis:
        logger.warning(f"没有激活的API配置，使用第一个: {apis[0]['name']}")
        return apis[0]
    return None


def run_server(port=443, app_state=None):
    load_multi_backend_config()
    app = create_app(app_state)

    domain = MULTI_BACKEND_CONFIG.get('domain', 'api.openai.com') if MULTI_BACKEND_CONFIG else 'api.openai.com'
    CERT_FILE = f"ca/{domain}.crt"
    KEY_FILE = f"ca/{domain}.key"

    if not os.path.exists(CERT_FILE) or not os.path.exists(KEY_FILE):
        logger.error(f"证书文件不存在: {CERT_FILE} 或 {KEY_FILE}")
        logger.info("请先运行 generate_certs.py 生成证书")
        sys.exit(1)

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(CERT_FILE, KEY_FILE)

    assert MULTI_BACKEND_CONFIG
    logger.info("多后端模式已启用")
    apis = MULTI_BACKEND_CONFIG.get('apis', [])
    for api in apis:
        status = "激活" if api.get('active', False) else "未激活"
        logger.info(f"  - {api['name']} [{status}]: {api.get('endpoint', '')} -> {api.get('custom_model_id', '')}; 流模式: {api.get('stream_mode', None)}")
    logger.info(f"调试模式: {MULTI_BACKEND_CONFIG['server'].get('debug', False)}")
    logger.info(f"{domain}证书文件: {CERT_FILE}")
    logger.info(f"{domain}私钥文件: {KEY_FILE}")
    logger.info("启动代理服务器...")

    if app_state:
        app_state.set_service_running(True)

    app.run(host='0.0.0.0', port=port, ssl_context=context, threaded=True)


def main():
    load_multi_backend_config()
    port = MULTI_BACKEND_CONFIG['server'].get('port', 443) if MULTI_BACKEND_CONFIG else 443
    run_server(port=port)


if __name__ == "__main__":
    main()
