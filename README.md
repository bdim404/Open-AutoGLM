# PhoneGenie - 手机精灵

基于 [Open-AutoGLM](https://github.com/zai-org/Open-AutoGLM)，支持 Telegram Bot 和飞书 Bot，通过聊天机器人操作 Android 手机。

## 快速开始

1. 安装依赖
```bash
pip install -r requirements.txt
```

2. 配置 Bot
复制示例配置：
```bash
cp config/bot_config.example.yaml config/bot_config.yaml
```

编辑 `config/bot_config.yaml`，参考以下配置：

**Telegram Bot 配置：**
```yaml
telegram:
  token: "YOUR_BOT_TOKEN"
  allowed_user_id: YOUR_USER_ID
```

**飞书 Bot 配置：**
```yaml
lark:
  app_id: "cli_xxx"
  app_secret: "xxx"
  verification_token: "xxx"
  allowed_users:
    - "ou_xxx"
  webhook_host: "0.0.0.0"
  webhook_port: 8080
```

**模型配置：**
```yaml
model:
  base_url: "http://localhost:8000/v1"
  model_name: "autoglm-phone-9b"

agent:
  max_steps: 100
  device_id: null
  lang: "cn"
```

3. 连接手机并启动

**Telegram Bot：**
```bash
python bot_main.py
```

**飞书 Bot：**
```bash
uvicorn lark_main:app --host 0.0.0.0 --port 8080
```

> 两个 Bot 可以同时运行，互不影响

## 使用

### Telegram Bot
在 Telegram 中向你的 Bot 发送任务：
- `/start` - 查看帮助
- `/status` - 查看设备状态
- `/cancel` - 取消当前任务
- 直接发送任务（如"打开微信"）

### 飞书 Bot
在飞书中直接向机器人发送任务：
- 发送任务描述即可执行（如"打开微信"）
- 支持交互式确认（通过消息卡片按钮）
- 支持进度实时显示

## 特性

- 💬 **多平台支持**：Telegram 和飞书双平台
- 📊 **实时进度**：显示执行步骤和思考过程
- 📸 **截图反馈**：每步自动发送手机截图
- ✋ **人工接管**：支持任务取消和手动操作
- 🎯 **交互确认**：关键操作前请求用户确认
- 🖥️ **CLI 模式**：保留命令行模式（`python main.py`）

## 飞书应用创建

1. 访问 [飞书开放平台](https://open.feishu.cn/app)
2. 创建企业自建应用
3. 获取 App ID 和 App Secret
4. 开启机器人能力
5. 添加权限：
   - `im:message` - 接收消息
   - `im:message:send_as_bot` - 发送消息
   - `im:resource` - 上传图片
6. 配置事件订阅：
   - 请求地址：`https://your-domain/webhook/event`
   - 订阅事件：`im.message.receive_v1`
7. 发布应用并添加测试用户
8. 获取用户 Open ID 并添加到 `allowed_users` 列表

### 本地测试（使用 ngrok）
```bash
# 安装 ngrok
brew install ngrok

# 启动服务
uvicorn lark_main:app --host 0.0.0.0 --port 8080

# 在另一个终端启动 ngrok
ngrok http 8080

# 将 ngrok 提供的 HTTPS 地址配置到飞书事件订阅
# 例如：https://xxxx.ngrok.io/webhook/event
```
