# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## 项目概述

这是一个微信读书自动阅读脚本，通过逆向分析微信读书Web接口实现自动刷阅读时长和签到功能。支持GitHub Actions定时运行和Docker部署，具备自动Cookie刷新和多种推送通知方式。

## 核心架构

### 三个主要模块
1. **main.py** - 核心逻辑
   - 负责构建阅读请求、生成加密签名(SHA256)和校验和(cal_hash)
   - 实现自动Cookie刷新机制(`refresh_cookie`、`get_wr_skey`)
   - 处理synckey缺失的修复逻辑(`fix_no_synckey`)
   - 循环执行阅读任务，每次间隔30秒

2. **config.py** - 配置管理
   - 统一管理环境变量和本地配置(优先使用环境变量)
   - `convert()函数`：从curl bash命令提取headers和cookies(支持`-H 'Cookie:'`和`-b`两种格式)
   - 预定义书籍和章节ID列表，运行时随机选择增加真实性

3. **push.py** - 消息推送
   - 封装三种推送方式：PushPlus、WxPusher、Telegram
   - 内置重试机制(最多5次，间隔3-6分钟)
   - Telegram支持代理和直连两种方式

### 关键算法

**加密签名生成**：
```python
sg = hashlib.sha256(f"{ts}{rn}{KEY}".encode()).hexdigest()
KEY = "3c5c5c8717f3daf09iop3423zafeqoi"  # 通过JS逆向获得
```

**校验和计算**：`cal_hash()`函数实现特殊的哈希算法，对URL编码后的请求参数进行校验。

**Cookie自动更新**：定期请求`/web/login/renewal`接口获取新的`wr_skey`(8位)。

## 常用命令

### 本地开发/测试
```bash
# 直接运行脚本(需先配置config.py)
python main.py

# 测试推送功能
python -c "from push import push; push('测试消息', 'pushplus')"
```

### Docker部署
```bash
# 构建并运行容器
docker rm -f wxread && docker build -t wxread . && docker run -d --name wxread -v $(pwd)/logs:/app/logs --restart always wxread

# 测试运行
docker exec -it wxread python /app/main.py

# 查看日志
docker logs -f wxread
```

### GitHub Actions
- 手动触发：仓库页面 Actions → wxread → Run workflow
- 定时任务：默认每天北京时间01:00(UTC 17:00)运行
- 配置位置：`.github/workflows/deploy.yml`

## 配置说明

### 环境变量(Secrets)
- `WXREAD_CURL_BASH`：抓包获取的read接口curl bash命令(**必填**)
- `PUSH_METHOD`：推送方式，可选`pushplus`/`wxpusher`/`telegram`
- 对应推送token：`PUSHPLUS_TOKEN`、`WXPUSHER_SPT`或`TELEGRAM_BOT_TOKEN`+`TELEGRAM_CHAT_ID`

### 环境变量(Variables)
- `READ_NUM`：阅读次数，每次30秒，默认40次(20分钟)

### 抓包方法
1. 访问[微信读书](https://weread.qq.com/)搜索【三体】点击阅读
2. 抓取`https://weread.qq.com/web/book/read`接口
3. 右键复制为Bash格式(curl命令)
4. 验证返回格式：`{"succ": 1, "synckey": 数字}`

## 重要接口

- **阅读接口**：`POST https://weread.qq.com/web/book/read`
- **刷新Cookie**：`POST https://weread.qq.com/web/login/renewal`
- **修复Synckey**：`POST https://weread.qq.com/web/book/chapterInfos`

## 数据字段说明

`data`字典中的关键字段：
- `b`：书籍ID(运行时随机选择)
- `c`：章节ID(运行时随机选择)
- `ct`：当前时间戳(秒)
- `rt`：阅读时长(与上次间隔)
- `ts`：毫秒级时间戳+随机数
- `rn`：0-1000的随机数
- `sg`：安全签名(SHA256)
- `s`：校验和(cal_hash算法)

## 依赖项

```
requests>=2.32.3
urllib3>=2.2.3
certifi==2024.8.30
charset-normalizer==3.4.0
idna==3.10
```

## 故障排查

1. **阅读时间未增加**：保留`config.py`中的`data`字段默认值，默认阅读三体
2. **Cookie过期**：脚本会自动刷新，如持续失败检查`WXREAD_CURL_BASH`配置
3. **无synckey**：脚本会自动调用`fix_no_synckey()`修复
4. **推送失败**：PushPlus和WxPusher有5次重试机制，Telegram会尝试代理和直连

## 注意事项

- 不要频繁修改`READ_NUM`，避免被检测异常行为
- GitHub Actions需要定期(60天内)有活动，否则workflow会被停用
- Docker容器默认每天凌晨1点(Asia/Shanghai)执行
- 日志文件按日期存储在`logs/`目录(Docker挂载卷)
