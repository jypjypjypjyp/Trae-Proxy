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

MULTI_BACKEND_CONFIG = None

# 初始化Flask应用
app = Flask(__name__)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('trae_proxy')


@app.route('/', methods=['GET'])
def root():
    """处理根路径请求"""
    return jsonify({
        "message": "Welcome to the OpenAI API! Documentation is available at https://platform.openai.com/docs/api-reference"
    })


@app.route('/v1', methods=['GET'])
def v1_root():
    """处理/v1路径请求"""
    return jsonify({
        "message": "OpenAI API v1 endpoint",
        "endpoints": {
            "chat/completions": "/v1/chat/completions"
        }
    })


@app.route('/v1/models', methods=['GET'])
def list_models():
    """列出可用模型"""
    try:
        # 从配置中获取模型列表
        models = []
        if MULTI_BACKEND_CONFIG:
            apis = MULTI_BACKEND_CONFIG.get('apis', [])
            for api in apis:
                if api.get('active', False):
                    models.append({
                        "id": api.get('custom_model_id', ''),
                        "object": "model",
                        "created": 1,
                        "owned_by": "trae-proxy",
                        "supports_image": api.get('supports_image', True)
                    })
        else:
            models.append({
                "id": CUSTOM_MODEL_ID,
                "object": "model", 
                "created": 1,
                "owned_by": "trae-proxy"
            })
        
        return jsonify({
            "object": "list",
            "data": models
        })
    except Exception as e:
        logger.error(f"列出模型时发生错误: {str(e)}")
        return jsonify({"error": f"内部服务器错误: {str(e)}"}), 500


def debug_log(message):
    """调试日志记录"""
    DEBUG_MODE = MULTI_BACKEND_CONFIG['server'].get('debug', False)
    if DEBUG_MODE:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        with open("debug_request.log", "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
        logger.debug(message)


def load_multi_backend_config():
    """加载多后端配置"""
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
                return True
        else:
            logger.warning("配置文件不存在，使用单后端模式")
            return False
    except Exception as e:
        logger.error(f"加载多后端配置失败: {str(e)}")
        return False


def select_backend_by_model(requested_model):
    """根据请求的模型选择后端API"""
    if not MULTI_BACKEND_CONFIG:
        return None
    
    apis = MULTI_BACKEND_CONFIG.get('apis', [])
    
    # 首先尝试根据模型ID精确匹配
    for api in apis:
        if api.get('active', False) and api.get('custom_model_id') == requested_model:
            logger.info(f"根据模型ID匹配到后端: {api['name']} -> {api['endpoint']}")
            return api
    
    # 如果没有精确匹配，使用第一个激活的API
    for api in apis:
        if api.get('active', False):
            logger.info(f"使用默认激活后端: {api['name']} -> {api['endpoint']}")
            return api
    
    # 如果都没有激活的，使用第一个
    if apis:
        logger.warning(f"没有激活的API配置，使用第一个: {apis[0]['name']}")
        return apis[0]
    
    return None


def generate_stream(response):
    """生成流式响应，按SSE事件边界拆分，保证顺序正确"""
    try:
        buffer = ""
        for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
            if chunk:
                buffer += chunk
                while "\n\n" in buffer:
                    event, buffer = buffer.split("\n\n", 1)
                    # 拦截 GLM 的非标准事件
                    if "event: progress_notice" in event or "event: context_usage" in event:
                        log_content = event.replace('\n', ' | ')
                        logger.debug(f"Discarded unsupported SSE event: {log_content}")
                        debug_log(f"Discarded unsupported SSE event: {log_content}")
                        continue # 继续等待后续的标准消息，不断开流
                    yield (event + "\n\n").encode("utf-8")
        if buffer.strip():
            yield (buffer + "\n\n").encode("utf-8")
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
            "choices": [
                {
                    "index": 0,
                    "delta": {"role": "assistant"},
                    "finish_reason": None
                }
            ]
        }
        yield f"data: {json.dumps(first_chunk, ensure_ascii=False)}\n\n".encode("utf-8")
        for i in range(0, len(content), 4):
            chunk = content[i:i+4]
            data = {
                "id": "chatcmpl-simulated",
                "object": "chat.completion.chunk",
                "created": 1,
                "model": model_id,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": chunk},
                        "finish_reason": None
                    }
                ]
            }
            yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8")
        end_chunk = {
            "id": "chatcmpl-simulated",
            "object": "chat.completion.chunk",
            "created": 1,
            "model": model_id,
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }
            ]
        }
        yield f"data: {json.dumps(end_chunk, ensure_ascii=False)}\n\n".encode("utf-8")
        yield b"data: [DONE]\n\n"
    except Exception as e:
        logger.error(f"模拟流式响应失败: {e}")
        err = {"error": f"模拟流式响应失败: {str(e)}"}
        yield f"data: {json.dumps(err, ensure_ascii=False)}\n\n".encode("utf-8")


def _has_image_content(messages):
    """检查消息中是否包含图片（image_url 类型的内容）"""
    for msg in messages:
        content = msg.get('content', '')
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get('type') == 'image_url':
                    return True
    return False


def _get_vision_fallback_backend():
    """获取用于图片描述的 fallback 后端"""
    if not MULTI_BACKEND_CONFIG:
        return None

    vision_fallback = MULTI_BACKEND_CONFIG.get('vision_fallback', '')
    if vision_fallback:
        for api in MULTI_BACKEND_CONFIG.get('apis', []):
            if api.get('active', False) and api.get('custom_model_id') == vision_fallback:
                return api

    for api in MULTI_BACKEND_CONFIG.get('apis', []):
        if api.get('active', False) and api.get('supports_image', False):
            return api

    return None


def _describe_and_replace_images(messages, fallback_backend, auth_headers):
    """使用 vision 模型描述图片，将 image_url 替换为文本描述"""
    vision_url = f"{fallback_backend['endpoint']}/v1/chat/completions"
    fallback_verify = fallback_backend.get('verify_ssl', True)
    
    new_messages = []
    for msg in messages:
        content = msg.get('content', '')
        if not isinstance(content, list):
            new_messages.append(msg)
            continue
        text_parts = [item.get('text', '') for item in content if isinstance(item, dict) and item.get('type') == 'text']
        image_items = [item for item in content if isinstance(item, dict) and item.get('type') == 'image_url']
        if not image_items:
            new_messages.append(msg)
            continue
        
        user_context = ' '.join(text_parts).strip()
        prompt_text = f"用户在问：「{user_context}」请结合用户的问题，详细描述图片中的相关内容" if user_context else "请详细描述以下图片的内容"
        if len(image_items) > 1:
            prompt_text += "。请按顺序用「图1:」「图2:」的格式描述每张图片，不要遗漏"
        vision_content = [{"type": "text", "text": prompt_text}]
        vision_content.extend({"type": "image_url", "image_url": {"url": item['image_url']['url']}} for item in image_items)
        vision_payload = {"model": fallback_backend.get('target_model_id'), "messages": [{"role": "user", "content": vision_content}], "stream": False, "max_tokens": 4096}
        description_texts = []
        try:
            resp = requests.post(vision_url, json=vision_payload, headers=auth_headers, timeout=120, verify=fallback_verify)
            resp.raise_for_status()
            full_text = resp.json()['choices'][0]['message']['content']
            if len(image_items) > 1:
                import re
                matches = re.findall(r'图\d+:\s*(.*?)(?=\n图\d+:|\Z)', full_text, re.DOTALL)
                description_texts = [m.strip() for m in matches] if matches and len(matches) == len(image_items) else [full_text] * len(image_items)
            else:
                description_texts = [full_text]
        except Exception as e:
            logger.error(f"图片描述请求失败: {e}")
            description_texts = ["[图片描述失败]"] * len(image_items)

        desc_iter = iter(description_texts)
        new_content = [
            {"type": "text", "text": f"[Image Description: {next(desc_iter)}]"}
            if isinstance(item, dict) and item.get('type') == 'image_url'
            else item
            for item in content
        ]
        new_messages.append({**msg, 'content': new_content})

    return new_messages


@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    """处理聊天完成请求"""
    try:
        DEBUG_MODE = MULTI_BACKEND_CONFIG['server'].get('debug', False)
        # 检查Content-Type
        content_type = request.headers.get('Content-Type', '')
        if 'application/json' not in content_type:
            return jsonify({"error": "Content-Type必须为application/json"}), 400
        
        # 解析请求JSON
        try:
            req_json = request.json
            if req_json is None:
                return jsonify({"error": "无效的JSON请求体"}), 400
        except Exception as e:
            return jsonify({"error": f"JSON解析失败: {str(e)}"}), 400
        
        # 调试日志
        if DEBUG_MODE:
            debug_log(f"请求头: {dict(request.headers)}")
            debug_log(f"请求体: {json.dumps(req_json, ensure_ascii=False)}")
        
        # 获取请求的模型ID
        requested_model = req_json.get('model', '')
        
        # 多后端模式：根据模型选择后端
        selected_backend = select_backend_by_model(requested_model)
        if selected_backend:
            target_api_url = selected_backend.get('endpoint', '').strip()
            target_model_id = selected_backend.get('target_model_id', '').strip()
            custom_model_id = selected_backend.get('custom_model_id', '').strip()
            stream_mode = selected_backend.get('stream_mode')
            logger.info(f"选择后端: {selected_backend['name']} -> {target_api_url}")
            
            # 修改模型ID
            if 'model' in req_json:
                original_model = req_json['model']
                req_json['model'] = target_model_id
                debug_log(f"模型ID从 {original_model} 修改为 {target_model_id}")
            else:
                req_json['model'] = target_model_id
                debug_log(f"添加模型ID: {target_model_id}")
            
            # 处理流模式
            if stream_mode is not None:
                original_stream = req_json.get('stream', False)
                req_json['stream'] = stream_mode == 'true'
                debug_log(f"流模式从 {original_stream} 修改为 {req_json['stream']}")
            
            # 图片 fallback：当模型不支持图片且消息中包含图片时
            if not selected_backend.get('supports_image', True):
                messages = req_json.get('messages', [])
                if _has_image_content(messages):
                    logger.info(f"模型 {selected_backend['name']} 不支持图片，使用 vision fallback 模型描述图片")
                    fallback_backend = _get_vision_fallback_backend()
                    if fallback_backend:
                        logger.info(f"vision fallback 模型: {fallback_backend['name']}")
                        fb_headers = {'Content-Type': 'application/json'}
                        fb_token = os.environ.get('ANTHROPIC_AUTH_TOKEN', '')
                        if fb_token:
                            fb_headers['Authorization'] = f'Bearer {fb_token}'
                        else:
                            fb_auth = request.headers.get('Authorization')
                            if fb_auth:
                                fb_headers['Authorization'] = fb_auth
                        modified_messages = _describe_and_replace_images(messages, fallback_backend, fb_headers)
                        req_json['messages'] = modified_messages
                    else:
                        logger.warning("未找到可用的 vision fallback 模型，图片将保持原样发送")
            
        # 准备转发请求
        headers = {
            'Content-Type': 'application/json'
        }
        
        # 复制Authorization头，优先使用环境变量
        auth_token = os.environ.get('ANTHROPIC_AUTH_TOKEN', '')
        if auth_token:
            headers['Authorization'] = f'Bearer {auth_token}'
        else:
            auth_header = request.headers.get('Authorization')
            if auth_header:
                headers['Authorization'] = auth_header
        
        # 构建目标URL
        target_url = f"{target_api_url}/v1/chat/completions"
        debug_log(f"转发请求到: {target_url}")
        
        # 获取 SSL 验证配置
        verify_ssl = selected_backend.get('verify_ssl', True) if selected_backend else True
        
        # 发送请求到目标 API
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
        
        # 检查响应状态
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
        
        # 处理响应
        if req_json.get('stream', False):
            # 流式响应
            debug_log("返回流式响应")
            try:
                return Response(
                    stream_with_context(generate_stream(response)),
                    content_type=response.headers.get('Content-Type', 'text/event-stream')
                )
            except Exception as e:
                logger.error(f"流式响应处理失败：{str(e)}")
                raise
        else:
            # 非流式响应
            response_json = response.json()
            
            if DEBUG_MODE:
                debug_log(f"响应体: {json.dumps(response_json, ensure_ascii=False)}")
            
            # 如果客户端请求流式但目标API返回非流式，且stream_mode为False
            if stream_mode == 'false':
                debug_log("模拟流式响应")
                return Response(
                    stream_with_context(simulate_stream(response_json)),
                    content_type='text/event-stream'
                )
            
            # 修改响应中的模型ID
            if 'model' in response_json:
                response_json['model'] = custom_model_id
            
            return jsonify(response_json)
    
    except Exception as e:
        # 其他异常
        logger.error(f"处理请求时发生错误：{str(e)}")
        return jsonify({"error": f"内部服务器错误：{str(e)}"}), 500


def main():
    """主函数"""
    
    # 加载多后端配置
    load_multi_backend_config()

    # 检查证书文件
    CERT_FILE = f"ca/{MULTI_BACKEND_CONFIG['domain']}.crt"
    KEY_FILE = f"ca/{MULTI_BACKEND_CONFIG['domain']}.key"
    if not os.path.exists(CERT_FILE) or not os.path.exists(KEY_FILE):
        logger.error(f"证书文件不存在: {CERT_FILE} 或 {KEY_FILE}")
        logger.info("请先运行 generate_certs.py 生成证书")
        sys.exit(1)
    
    # 创建SSL上下文
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(CERT_FILE, KEY_FILE)
    
    # 打印配置信息
    assert MULTI_BACKEND_CONFIG
    logger.info("多后端模式已启用")
    apis = MULTI_BACKEND_CONFIG.get('apis', [])
    for api in apis:
        status = "激活" if api.get('active', False) else "未激活"
        logger.info(f"  - {api['name']} [{status}]: {api.get('endpoint', '')} -> {api.get('custom_model_id', '')}; 流模式: {api.get('stream_mode', None)}")
    logger.info(f"调试模式: {MULTI_BACKEND_CONFIG['server'].get('debug', False)}")
    logger.info(f"{MULTI_BACKEND_CONFIG['domain']}证书文件: {CERT_FILE}")
    logger.info(f"{MULTI_BACKEND_CONFIG['domain']}私钥文件: {KEY_FILE}")
    
    # 启动服务器
    logger.info("启动代理服务器...")
    app.run(host='0.0.0.0', port=MULTI_BACKEND_CONFIG['server'].get('port', 443), ssl_context=context, threaded=True)


if __name__ == "__main__":
    main()