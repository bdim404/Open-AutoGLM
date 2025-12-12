# PhoneGenie

Based on [Open-AutoGLM](https://github.com/zai-org/Open-AutoGLM), supporting both Telegram Bot and Lark Bot for controlling Android phones through chat.

## Quick Start

1. Install dependencies
```bash
pip install -r requirements.txt
```

2. Configure Bot
Copy the example configuration:
```bash
cp config/bot_config.example.yaml config/bot_config.yaml
```

Edit `config/bot_config.yaml` with the following settings:

**Telegram Bot Configuration:**
```yaml
telegram:
  token: "YOUR_BOT_TOKEN"
  allowed_user_id: YOUR_USER_ID
```

**Lark Bot Configuration:**
```yaml
lark:
  app_id: "cli_xxx"
  app_secret: "xxx"
  verification_token: "xxx"
  allowed_users:
    - "ou_xxx"
```

**Model Configuration:**
```yaml
model:
  base_url: "http://localhost:8000/v1"
  model_name: "autoglm-phone-9b"

agent:
  max_steps: 100
  device_id: null
  lang: "cn"
```

3. Connect your phone and start

**Telegram Bot:**
```bash
python bot_main.py
```

**Lark Bot:**
```bash
python lark_main.py
```

> Lark uses long connection mode, no need for public IP or ngrok, automatically connects to Lark servers after startup
> Both bots can run simultaneously without conflicts

## Usage

### Telegram Bot
Send tasks to your Bot in Telegram:
- `/start` - Show help
- `/status` - Check device status
- `/cancel` - Cancel current task
- Send task directly (e.g., "Open WeChat")

### Lark Bot
Send tasks directly to the bot in Lark:
- Send task description to execute (e.g., "Open WeChat")
- Interactive confirmation through message card buttons
- Real-time progress display

## Features

- 💬 **Multi-platform Support**: Both Telegram and Lark
- 📊 **Real-time Progress**: Display execution steps and reasoning
- 📸 **Screenshot Feedback**: Automatic screenshot for each step
- ✋ **Manual Takeover**: Task cancellation and manual operation support
- 🎯 **Interactive Confirmation**: User confirmation before critical operations
- 🖥️ **CLI Mode**: Preserved command-line mode (`python main.py`)

## Lark App Setup

### 1. Create App
1. Visit [Lark Open Platform](https://open.larksuite.com/app)
2. Create a custom app
3. Get App ID and App Secret
4. Get Verification Token (in Event Subscription page)

### 2. Configure Permissions
Add the following permissions:
- `im:message` - Receive messages
- `im:message:send_as_bot` - Send messages
- `im:resource` - Upload images

### 3. Subscribe Events
In "Event Subscription" page, subscribe to:
- `im.message.receive_v1` - Receive messages
- `card.action.trigger` - Message card interactions

> ⚠️ Using long connection mode, **no need to configure request URL**, just subscribe to events

### 4. Publish App
1. Click "Create Version" and publish
2. Add test users or make it available to all
3. Search and add your bot in Lark

### 5. Get User Open ID
Two ways to get it:
1. Send a message to the bot and check logs
2. View in "Event Subscription > Event Logs" on Lark Open Platform

Add the obtained Open ID to `allowed_users` list in `config/bot_config.yaml`
