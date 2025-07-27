# push.py - 消息推送模块
# 功能：支持多种推送方式（PushPlus、wxpusher、Telegram）发送通知消息
# 作者：findmover
# 版本：5.0

import os
import random
import time
import json
import requests
import logging
from config import PUSHPLUS_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_BOT_TOKEN, WXPUSHER_SPT

# 获取logger实例
logger = logging.getLogger(__name__)


class PushNotification:
    """
    推送通知类：封装了多种推送方式的实现
    支持PushPlus、Telegram和WxPusher三种推送渠道
    """
    
    def __init__(self):
        """初始化推送通知类，设置各推送渠道的URL和请求头"""
        self.pushplus_url = "https://www.pushplus.plus/send"  # PushPlus推送API
        self.telegram_url = "https://api.telegram.org/bot{}/sendMessage"  # Telegram API
        self.headers = {'Content-Type': 'application/json'}  # 通用请求头
        
        # 从环境变量获取代理设置，用于Telegram推送
        self.proxies = {
            'http': os.getenv('http_proxy'),
            'https': os.getenv('https_proxy')
        }
        
        # WxPusher简易推送URL
        self.wxpusher_simple_url = "https://wxpusher.zjiecode.com/api/send/message/{}/{}"

    def push_pushplus(self, content, token):
        """
        PushPlus消息推送
        
        参数:
            content: 推送内容
            token: PushPlus的token
        """
        attempts = 5  # 最大尝试次数
        for attempt in range(attempts):
            try:
                # 发送POST请求到PushPlus
                response = requests.post(
                    self.pushplus_url,
                    data=json.dumps({
                        "token": token,
                        "title": "微信阅读推送...",
                        "content": content
                    }).encode('utf-8'),
                    headers=self.headers,
                    timeout=10
                )
                response.raise_for_status()  # 检查响应状态
                logger.info("✅ PushPlus响应: %s", response.text)
                break  # 成功推送，跳出循环
            except requests.exceptions.RequestException as e:
                logger.error("❌ PushPlus推送失败: %s", e)
                if attempt < attempts - 1:  # 如果不是最后一次尝试
                    sleep_time = random.randint(180, 360)  # 随机3到6分钟
                    logger.info("将在 %d 秒后重试...", sleep_time)
                    time.sleep(sleep_time)  # 等待一段时间后重试

    def push_telegram(self, content, bot_token, chat_id):
        """
        Telegram消息推送，失败时自动尝试直连
        
        参数:
            content: 推送内容
            bot_token: Telegram机器人token
            chat_id: 聊天ID
            
        返回:
            bool: 推送成功返回True，否则返回False
        """
        url = self.telegram_url.format(bot_token)  # 格式化URL
        payload = {"chat_id": chat_id, "text": content}  # 请求数据

        try:
            # 先尝试使用代理
            response = requests.post(url, json=payload, proxies=self.proxies, timeout=30)
            logger.info("✅ Telegram响应: %s", response.text)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error("❌ Telegram代理发送失败: %s", e)
            try:
                # 代理失败后直连
                response = requests.post(url, json=payload, timeout=30)
                response.raise_for_status()
                return True
            except Exception as e:
                logger.error("❌ Telegram发送失败: %s", e)
                return False
    
    def push_wxpusher(self, content, spt):
        """
        WxPusher消息推送（极简方式）
        
        参数:
            content: 推送内容
            spt: WxPusher的SPT参数
        """
        attempts = 5  # 最大尝试次数
        url = self.wxpusher_simple_url.format(spt, content)  # 格式化URL
        
        for attempt in range(attempts):
            try:
                # 发送GET请求到WxPusher
                response = requests.get(url, timeout=10)
                response.raise_for_status()  # 检查响应状态
                logger.info("✅ WxPusher响应: %s", response.text)
                break  # 成功推送，跳出循环
            except requests.exceptions.RequestException as e:
                logger.error("❌ WxPusher推送失败: %s", e)
                if attempt < attempts - 1:  # 如果不是最后一次尝试
                    sleep_time = random.randint(180, 360)  # 随机3到6分钟
                    logger.info("将在 %d 秒后重试...", sleep_time)
                    time.sleep(sleep_time)  # 等待一段时间后重试


"""外部调用接口"""


def push(content, method):
    """
    统一推送接口，支持多种推送方式
    
    参数:
        content: 推送内容
        method: 推送方式，支持'pushplus'、'telegram'和'wxpusher'
        
    返回:
        根据不同推送方式返回相应结果
        
    异常:
        ValueError: 当提供的推送方式无效时抛出
    """
    notifier = PushNotification()  # 创建推送通知实例

    if method == "pushplus":
        token = PUSHPLUS_TOKEN
        return notifier.push_pushplus(content, token)
    elif method == "telegram":
        bot_token = TELEGRAM_BOT_TOKEN
        chat_id = TELEGRAM_CHAT_ID
        return notifier.push_telegram(content, bot_token, chat_id)
    elif method == "wxpusher":
        return notifier.push_wxpusher(content, WXPUSHER_SPT)
    else:
        raise ValueError("❌ 无效的通知渠道，请选择 'pushplus'、'telegram' 或 'wxpusher'")