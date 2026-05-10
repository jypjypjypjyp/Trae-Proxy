#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import tempfile
import atexit
import shutil
import logging

logger = logging.getLogger(__name__)

# 临时文件列表，用于退出时清理
temp_files = []


def error(message):
    """记录错误日志并退出"""
    logger.error(message)
    sys.exit(1)


def run_command(command, check=True):
    """运行命令并检查返回码"""
    logger.info(f"执行命令: {command}")
    result = subprocess.run(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    if check and result.returncode != 0:
        error(f"命令执行失败: {command}\n{result.stderr}")
    return result


def create_temp_file(content):
    """创建临时文件并返回其路径"""
    fd, path = tempfile.mkstemp(suffix=".cnf")
    os.write(fd, content.encode("utf-8"))
    os.close(fd)
    temp_files.append(path)
    return path


def cleanup_temp_files():
    """清理所有临时文件"""
    for path in temp_files:
        try:
            if os.path.exists(path):
                os.unlink(path)
        except:
            pass


# 注册退出时的清理函数
atexit.register(cleanup_temp_files)


def check_openssl():
    """检查 OpenSSL 是否已安装"""
    try:
        run_command("openssl version")
    except:
        logger.error("未找到 OpenSSL，无法生成证书。")
        logger.error("请从 https://slproweb.com/products/Win32OpenSSL.html 下载安装 OpenSSL for Windows")
        logger.error("建议安装选项: Win64 OpenSSL v3.x.x (Light 版即可，约 5MB)")
        logger.error("安装后请确保将 OpenSSL 的 bin 目录添加到系统 PATH 环境变量中。")
        logger.error("（默认安装路径: C:\\Program Files\\OpenSSL-Win64\\bin）")
        sys.exit(1)


def create_default_config_files(domain="api.openai.com"):
    """创建默认的 OpenSSL 配置文件"""
    os.makedirs("ca", exist_ok=True)

    # 基础 req 配置，不要把 v3_req / v3_ca 混进来，避免重复 section 干扰
    openssl_cnf = """
[ req ]
default_bits        = 2048
default_md          = sha256
default_keyfile     = privkey.pem
distinguished_name  = req_distinguished_name
prompt              = no

[ req_distinguished_name ]
C                   = CN
ST                  = State
L                   = City
O                   = Organization
OU                  = Unit
CN                  = localhost
emailAddress        = admin@example.com
""".strip() + "\n"

    # CSR 请求扩展：这里只放请求阶段可用的扩展
    v3_req_cnf = """
[ v3_req ]
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names
""".strip() + "\n"

    # 最终服务器证书扩展：签发时使用，这里可以放 authorityKeyIdentifier
    v3_cert_cnf = """
[ v3_cert ]
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names
authorityKeyIdentifier = keyid,issuer
subjectKeyIdentifier = hash
""".strip() + "\n"

    # CA 证书扩展
    v3_ca_cnf = """
[ v3_ca ]
basicConstraints = critical, CA:true
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer:always
keyUsage = critical, cRLSign, keyCertSign
""".strip() + "\n"

    # 域名 SAN 配置
    domain_cnf = f"""
[ alt_names ]
DNS.1 = {domain}
""".strip() + "\n"

    # 证书主题
    domain_subj = f"/C=CN/ST=State/L=City/O=Organization/OU=Unit/CN={domain}"

    # 统一覆盖写入，避免历史错误配置残留
    with open("ca/openssl.cnf", "w", encoding="utf-8") as f:
        f.write(openssl_cnf)

    with open("ca/v3_req.cnf", "w", encoding="utf-8") as f:
        f.write(v3_req_cnf)

    with open("ca/v3_cert.cnf", "w", encoding="utf-8") as f:
        f.write(v3_cert_cnf)

    with open("ca/v3_ca.cnf", "w", encoding="utf-8") as f:
        f.write(v3_ca_cnf)

    with open(f"ca/{domain}.cnf", "w", encoding="utf-8") as f:
        f.write(domain_cnf)

    with open(f"ca/{domain}.subj", "w", encoding="utf-8") as f:
        f.write(domain_subj)


def generate_ca_cert():
    """生成 CA 证书和私钥"""
    logger.info("生成 CA 证书...")

    # 生成 CA 私钥
    run_command("openssl genrsa -out ca/ca.key 2048")

    # 生成自签名 CA 证书
    run_command(
        'openssl req -new -x509 -days 36500 '
        '-key ca/ca.key '
        '-out ca/ca.crt '
        '-subj "/C=CN/ST=State/L=City/O=TraeProxy CA/OU=TraeProxy/CN=TraeProxy Root CA"'
    )

    logger.info("CA 证书生成完成")


def generate_server_cert(domain="api.openai.com"):
    """为指定域名生成服务器证书"""
    logger.info(f"为域名 {domain} 生成服务器证书...")

    required_files = [
        "ca/openssl.cnf",
        "ca/v3_req.cnf",
        "ca/v3_cert.cnf",
        f"ca/{domain}.cnf",
        f"ca/{domain}.subj",
        "ca/ca.key",
        "ca/ca.crt"
    ]

    for file in required_files:
        if not os.path.exists(file):
            error(f"缺少必要文件: {file}")

    with open("ca/openssl.cnf", "r", encoding="utf-8") as f:
        openssl_cnf = f.read()

    with open("ca/v3_req.cnf", "r", encoding="utf-8") as f:
        v3_req_cnf = f.read()

    with open("ca/v3_cert.cnf", "r", encoding="utf-8") as f:
        v3_cert_cnf = f.read()

    with open(f"ca/{domain}.cnf", "r", encoding="utf-8") as f:
        domain_cnf = f.read()

    with open(f"ca/{domain}.subj", "r", encoding="utf-8") as f:
        domain_subj = f.read().strip()

    # CSR 用配置：不能包含 authorityKeyIdentifier
    csr_cnf = openssl_cnf + "\n" + v3_req_cnf + "\n" + domain_cnf
    csr_temp_cnf = create_temp_file(csr_cnf)

    # 最终证书签发扩展
    cert_cnf = v3_cert_cnf + "\n" + domain_cnf
    cert_temp_cnf = create_temp_file(cert_cnf)

    # 生成服务器私钥
    run_command(f'openssl genrsa -out "ca/{domain}.key" 2048')

    # 转换为 PKCS#8 格式
    run_command(
        f'openssl pkcs8 -topk8 -nocrypt '
        f'-in "ca/{domain}.key" '
        f'-out "ca/{domain}.key.pkcs8"'
    )
    shutil.move(f"ca/{domain}.key.pkcs8", f"ca/{domain}.key")

    # 生成 CSR
    run_command(
        f'openssl req -sha256 -new '
        f'-key "ca/{domain}.key" '
        f'-out "ca/{domain}.csr" '
        f'-config "{csr_temp_cnf}" '
        f'-reqexts v3_req '
        f'-subj "{domain_subj}"'
    )

    # 使用 CA 签发服务器证书
    run_command(
        f'openssl x509 -req -days 365 '
        f'-in "ca/{domain}.csr" '
        f'-CA "ca/ca.crt" '
        f'-CAkey "ca/ca.key" '
        f'-CAcreateserial '
        f'-out "ca/{domain}.crt" '
        f'-extfile "{cert_temp_cnf}" '
        f'-extensions v3_cert'
    )

    # 删除 CSR 文件
    if os.path.exists(f"ca/{domain}.csr"):
        os.remove(f"ca/{domain}.csr")

    print(f"服务器证书生成完成: ca/{domain}.crt")


def main():
    """主函数"""
    domain = "api.openai.com"

    if len(sys.argv) > 1 and sys.argv[1] == "--domain" and len(sys.argv) > 2:
        domain = sys.argv[2]

    # 检查 OpenSSL
    check_openssl()

    # 创建默认配置文件
    create_default_config_files(domain)

    # 生成 CA 证书
    generate_ca_cert()

    # 生成服务器证书
    generate_server_cert(domain)

    logger.info("所有证书生成完成")
    logger.info("CA 证书: ca/ca.crt")
    logger.info("CA 私钥: ca/ca.key")
    logger.info(f"服务器证书: ca/{domain}.crt")
    logger.info(f"服务器私钥: ca/{domain}.key")


if __name__ == "__main__":
    main()