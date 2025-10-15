# main.py - 主逻辑文件
# 功能：实现微信读书自动阅读功能，包括请求构建、加密签名生成、自动刷新cookie等核心功能
# 作者：findmover
# 版本：5.0

import re
import json
import time
import random
import logging
import hashlib
import requests
import urllib.parse
from push import push  # 导入推送模块，用于发送通知
from config import data, headers, cookies, READ_NUM, PUSH_METHOD, book, chapter  # 导入配置信息

# 配置日志格式，便于调试和查看运行状态
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)-8s - %(message)s')

# 关键常量定义
KEY = "3c5c8717f3daf09iop3423zafeqoi"  # 用于生成安全签名的密钥，通过逆向JS获得
COOKIE_DATA = {"rq": "%2Fweb%2Fbook%2Fread"}  # 刷新cookie时的请求数据
# COOKIE_DATA = {"rq": "%2Fweb%2Fbook%2Fread","ql": True}
READ_URL = "https://weread.qq.com/web/book/read"  # 微信读书阅读接口URL
RENEW_URL = "https://weread.qq.com/web/login/renewal"  # 刷新token的URL
FIX_SYNCKEY_URL = "https://weread.qq.com/web/book/chapterInfos"  # 修复synckey的URL


def encode_data(data):
    """
    数据编码函数：将字典转换为URL编码的字符串，并按键名排序
    参数:
        data: 包含请求参数的字典
    返回:
        按键名排序并URL编码后的字符串
    """
    return '&'.join(f"{k}={urllib.parse.quote(str(data[k]), safe='')}" for k in sorted(data.keys()))


def cal_hash(input_string):
    """
    计算哈希值：使用特定算法计算字符串的哈希值，用于请求校验
    这是从微信读书前端JS逆向得到的算法
    参数:
        input_string: 需要计算哈希的字符串
    返回:
        计算后的哈希值（十六进制字符串）
    """
    _7032f5 = 0x15051505  # 初始化第一个哈希值
    _cc1055 = _7032f5     # 初始化第二个哈希值
    length = len(input_string)  # 获取输入字符串长度
    _19094e = length - 1  # 从字符串末尾开始

    # 循环处理字符串中的每对字符
    while _19094e > 0:
        # 对第一个哈希值进行位运算
        _7032f5 = 0x7fffffff & (_7032f5 ^ ord(input_string[_19094e]) << (length - _19094e) % 30)
        # 对第二个哈希值进行位运算
        _cc1055 = 0x7fffffff & (_cc1055 ^ ord(input_string[_19094e - 1]) << _19094e % 30)
        _19094e -= 2  # 每次处理两个字符

    # 返回两个哈希值相加后的十六进制表示（去掉0x前缀）
    return hex(_7032f5 + _cc1055)[2:].lower()

def get_wr_skey():
    """
    刷新cookie密钥：获取新的wr_skey值
    微信读书的cookie需要定期刷新，此函数负责获取新的密钥
    返回:
        成功返回新的wr_skey值，失败返回None
    """
    # 发送请求获取新的cookie
    response = requests.post(RENEW_URL, headers=headers, cookies=cookies,
                             data=json.dumps(COOKIE_DATA, separators=(',', ':')))
    # 从响应头中提取wr_skey
    for cookie in response.headers.get('Set-Cookie', '').split(';'):
        if "wr_skey" in cookie:
            return cookie.split('=')[-1][:8]  # 返回前8位
    return None  # 如果没找到则返回None

def fix_no_synckey():
    """
    修复synckey缺失问题：通过请求章节信息接口
    有时阅读请求会返回没有synckey的情况，需要通过此函数修复
    """
    # 发送请求获取章节信息，间接修复synckey
    requests.post(FIX_SYNCKEY_URL, headers=headers, cookies=cookies,
                             data=json.dumps({"bookIds":["3300060341"]}, separators=(',', ':')))

def refresh_cookie():
    """
    刷新cookie：获取并更新wr_skey
    这是保持会话有效的关键函数
    """
    logging.info(f"🍪 刷新cookie")
    new_skey = get_wr_skey()  # 获取新的skey
    if new_skey:
        # 更新cookies中的wr_skey
        cookies['wr_skey'] = new_skey
        logging.info(f"✅ 密钥刷新成功，新密钥：{new_skey}")
        logging.info(f"🔄 重新本次阅读。")
    else:
        # 获取失败，记录错误并推送通知
        ERROR_CODE = "❌ 无法获取新密钥或者WXREAD_CURL_BASH配置有误，终止运行。"
        logging.error(ERROR_CODE)
        push(ERROR_CODE, PUSH_METHOD)  # 推送错误信息
        raise Exception(ERROR_CODE)  # 抛出异常终止程序

# 主程序开始执行

# 首先刷新cookie确保有效
refresh_cookie()

# 初始化计数器和时间
index = 1  # 阅读次数计数器
lastTime = int(time.time()) - 30  # 上次阅读时间（初始为当前时间减30秒）

# 循环执行阅读操作，直到达到设定的次数
while index <= READ_NUM:
    # 移除旧的校验和
    data.pop('s')
    
    # 随机选择书籍和章节，增加真实性
    data['b'] = random.choice(book)  # 随机选择一本书
    data['c'] = random.choice(chapter)  # 随机选择一个章节
    
    # 更新时间相关字段
    thisTime = int(time.time())  # 当前时间戳（秒）
    data['ct'] = thisTime  # 当前时间
    data['rt'] = thisTime - lastTime  # 阅读时长
    data['ts'] = int(thisTime * 1000) + random.randint(0, 1000)  # 毫秒级时间戳加随机数
    data['rn'] = random.randint(0, 1000)  # 随机数
    
    # 生成安全签名
    data['sg'] = hashlib.sha256(f"{data['ts']}{data['rn']}{KEY}".encode()).hexdigest()
    
    # 计算校验和
    data['s'] = cal_hash(encode_data(data))

    # 记录日志
    logging.info(f"⏱️ 尝试第 {index} 次阅读...")
    logging.info(f"📕 data: {data}")
    
    # 发送阅读请求
    response = requests.post(READ_URL, headers=headers, cookies=cookies, data=json.dumps(data, separators=(',', ':')))
    resData = response.json()  # 解析响应JSON
    logging.info(f"📕 response: {resData}")

    # 处理响应结果
    if 'succ' in resData:  # 请求成功
        if 'synckey' in resData:  # 有同步键，表示阅读成功
            lastTime = thisTime  # 更新上次阅读时间
            index += 1  # 计数器加1
            time.sleep(30)  # 等待30秒，模拟真实阅读间隔
            logging.info(f"✅ 阅读成功，阅读进度：{(index - 1) * 0.5} 分钟")
        else:
            # 没有synckey，尝试修复
            logging.warning("❌ 无synckey, 尝试修复...")
            fix_no_synckey()
    else:
        # 请求失败，可能是cookie过期
        logging.warning("❌ cookie 已过期，尝试刷新...")
        refresh_cookie()  # 刷新cookie

# 所有阅读完成
logging.info("🎉 阅读脚本已完成！")

# 如果配置了推送方法，则发送完成通知
if PUSH_METHOD not in (None, ''):
    logging.info("⏱️ 开始推送...")
    push(f"🎉 微信读书自动阅读完成！\n⏱️ 阅读时长：{(index - 1) * 0.5}分钟。", PUSH_METHOD)