# Telegram to Zectrix

Fetch the latest message from multiple public Telegram channels and push them to your Zectrix e-ink device via GitHub Actions.

## Prerequisites

- A Zectrix Cloud account with an API key
- A Zectrix e-ink device (with its MAC address / device ID)
- Public Telegram channels to monitor
- Python 3.11+ and `uv` (for local testing)

## Quick Start

### 1. Add GitHub Secrets

Go to your repository: Settings → Secrets and variables → Actions

Add these secrets:

| Secret | Value |
|--------|-------|
| `ZECTRIX_API_KEY` | Your API key from https://cloud.zectrix.com (format: `zt_...`) |
| `ZECTRIX_DEVICE_ID` | Your device MAC address (format: `AA:BB:CC:DD:EE:FF`) |
| `TELEGRAM_CHANNELS` | JSON array of channel usernames: `["BBC_News", "CNN"]` |

### 2. Push to GitHub

The workflow will run automatically every 10 minutes.

## Configuration

### ZECTRIX_API_KEY
Your Zectrix Cloud API key.

**How to get it:**
1. Go to https://cloud.zectrix.com
2. Log in to your account
3. Navigate to API settings
4. Copy your API key

### ZECTRIX_DEVICE_ID
The MAC address of your Zectrix device.

**How to find it:**
1. Go to https://cloud.zectrix.com
2. Navigate to Devices
3. Copy the device ID (MAC address)

### TELEGRAM_CHANNELS
A JSON array of public Telegram channel usernames.

**Format:**
```json
["channel1", "channel2", "channel3"]
```

**Examples:**
- `["BBC_News", "CNN", "Reuters"]`
- `["TechCrunch", "Hacker_News"]`

**How to find channel usernames:**
- Open the channel in Telegram
- The username is in the channel link: `https://t.me/channel_username`

## Testing Locally

### Setup

```bash
# Install dependencies
uv sync

# Create .env file with your secrets
cat > .env << 'EOF'
ZECTRIX_API_KEY=zt_your_key_here
ZECTRIX_DEVICE_ID=AA:BB:CC:DD:EE:FF
TELEGRAM_CHANNELS=["BBC_News", "CNN"]
EOF
```

### Run the Script

```bash
# Load env vars and run
set -a
source .env
set +a
uv run fetch_and_push.py
```

Or pass env vars directly:

```bash
ZECTRIX_API_KEY=zt_your_key_here \
ZECTRIX_DEVICE_ID=AA:BB:CC:DD:EE:FF \
TELEGRAM_CHANNELS='["BBC_News"]' \
uv run fetch_and_push.py
```

### Expected Output

```
2026-05-25 10:30:45 - INFO - Starting fetch from 2 channels
2026-05-25 10:30:45 - INFO - Processing channel: BBC_News
2026-05-25 10:30:47 - INFO - Fetched message from BBC_News: 245 chars
2026-05-25 10:30:48 - INFO - Successfully pushed to device AA:BB:CC:DD:EE:FF
2026-05-25 10:30:48 - INFO - Processing channel: CNN
2026-05-25 10:30:50 - INFO - Fetched message from CNN: 312 chars
2026-05-25 10:30:51 - INFO - Successfully pushed to device AA:BB:CC:DD:EE:FF
2026-05-25 10:30:51 - INFO - Completed
```

## Workflow Schedule

The workflow runs automatically every 10 minutes.

To change the schedule, edit `.github/workflows/telegram-to-zectrix.yml` and modify the `cron` expression:
- `*/10 * * * *` — every 10 minutes (default)
- `0 * * * *` — every hour
- `0 0 * * *` — daily at midnight
- `*/30 * * * *` — every 30 minutes

## Manual Trigger

You can also manually trigger the workflow:
1. Go to Actions tab in your repository
2. Select "Telegram to Zectrix"
3. Click "Run workflow"

## Behavior

- Fetches the latest message from each channel
- Only pushes if the message contains text
- Skips channels with no text messages
- Truncates messages longer than 5000 characters (Zectrix limit)
- Logs all activity for debugging

## Troubleshooting

### Workflow fails with "TELEGRAM_CHANNELS not set"
- Verify the secret is added correctly in GitHub Settings
- Check the secret name is exactly `TELEGRAM_CHANNELS`

### "Cannot access channel" error
- Ensure the channel is public (not private)
- Verify the channel username is correct
- The channel must have at least one message

### Zectrix API error
- Verify `ZECTRIX_API_KEY` is correct
- Verify `ZECTRIX_DEVICE_ID` is in the correct format (MAC address)
- Check that your API key has permission to push to the device

### No message pushed
- Check the workflow logs in GitHub Actions
- Verify the Telegram channel has messages
- Ensure the message is text-only (images/media are skipped)

### Local testing hangs
- Press Ctrl+C to stop
- Check your internet connection
- Verify the channel username is correct

## Logs

### GitHub Actions
1. Go to Actions tab
2. Click the latest workflow run
3. Click "fetch-and-push" job
4. Scroll to see detailed logs

### Local Testing
Logs are printed to stdout with timestamps and log levels.
