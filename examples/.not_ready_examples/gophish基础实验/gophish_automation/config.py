# Gophish 自动化配置
import os

# Gophish配置
GOPHISH_API_KEY = "a78b08ef30d9dc06074a49d155ff14f7d586d65007702a9c4170384d9c00d588"
GOPHISH_HOST = "https://localhost:3333"

# OpenAI配置
OPENAI_API_KEY = "sk-Q3EsPIoMUzEnhZapg1NYhgF2FvR9YVvuZTSPynitaujg2a6B"
OPENAI_BASE_URL = "https://www.dmxapi.cn/v1"

# QQ邮箱配置
SMTP_CONFIG = {
    "name": "QQ邮箱服务器",
    "host": "smtp.qq.com:465",
    "from_address": "809050685@qq.com",
    "username": "809050685@qq.com",
    "password": "xutqpejdkpfcbbhi",
    "ignore_cert_errors": True
}

# 默认配置
DEFAULT_PHISHING_URL = "http://localhost:8080"
MAIL_TEMPLATE_DIR = "/Users/zzw4257/Documents/ZJU_archieve/25-seed/gophish基础实验/mail_template"
