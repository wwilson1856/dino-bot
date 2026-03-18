# Discord Bot Setup Instructions

## Step 1: Create Discord Bot

1. Go to https://discord.com/developers/applications
2. Click "New Application"
3. Name it "Moneymaker" (or whatever you want)
4. Go to "Bot" tab
5. Click "Add Bot"
6. Under "Privileged Gateway Intents", enable:
   - ✅ Message Content Intent
7. Click "Reset Token" and copy the token
8. Save it somewhere safe

## Step 2: Add Bot to Your Server

1. Go to "OAuth2" → "URL Generator"
2. Select scopes:
   - ✅ bot
3. Select bot permissions:
   - ✅ Send Messages
   - ✅ Embed Links
   - ✅ Read Message History
4. Copy the generated URL
5. Open it in browser and add bot to your server

## Step 3: Configure Environment

Add to your `.env` file:
```
DISCORD_BOT_TOKEN=your_bot_token_here
```

## Step 4: Run the Bot

```bash
cd /moneymaker/betting_model
source venv/bin/activate
python3 discord_bot.py
```

Keep it running in the background (use screen/tmux or systemd service).

## Available Commands

Once the bot is running, users can type in Discord:

- `!pick` — Get today's top pick
- `!record` — Show win/loss record and profit
- `!profit` — Show total units up/down
- `!stats <team>` — Get recent form (e.g., `!stats Buffalo Sabres`)
- `!help` — Show command list

## Running as a Service (Optional)

Create `/etc/systemd/system/moneymaker-bot.service`:

```ini
[Unit]
Description=Moneymaker Discord Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/moneymaker/betting_model
ExecStart=/moneymaker/betting_model/venv/bin/python3 /moneymaker/betting_model/discord_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable moneymaker-bot
sudo systemctl start moneymaker-bot
sudo systemctl status moneymaker-bot
```

## Notes

- Bot runs independently from the 4 PM job
- Both can run simultaneously
- Bot responds to commands in real-time
- 4 PM job still sends automated picks via webhook
