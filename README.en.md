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
  webhook_host: "0.0.0.0"
  webhook_port: 8080
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
uvicorn lark_main:app --host 0.0.0.0 --port 8080
```

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

1. Visit [Lark Open Platform](https://open.larksuite.com/app)
2. Create a custom app
3. Get App ID and App Secret
4. Enable bot capabilities
5. Add permissions:
   - `im:message` - Receive messages
   - `im:message:send_as_bot` - Send messages
   - `im:resource` - Upload images
6. Configure event subscription:
   - Request URL: `https://your-domain/webhook/event`
   - Subscribe to event: `im.message.receive_v1`
7. Publish the app and add test users
8. Get user Open ID and add to `allowed_users` list

### Local Testing (with ngrok)
```bash
# Install ngrok
brew install ngrok

# Start the service
uvicorn lark_main:app --host 0.0.0.0 --port 8080

# In another terminal, start ngrok
ngrok http 8080

# Configure the HTTPS URL provided by ngrok to Lark event subscription
# Example: https://xxxx.ngrok.io/webhook/event
```
