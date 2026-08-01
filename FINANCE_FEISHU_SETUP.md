# Finance Feishu Push Setup

This fork adds a finance-focused Horizon run for Feishu/Lark push delivery.

## What It Does

- Runs four times daily at 08:00, 12:00, 20:00, and 00:00 Asia/Shanghai.
- Fetches finance news from TianAPI, Google News RSS, GDELT, CNBC Finance, and BBC Business.
- Uses Aliyun Bailian/DashScope compatible mode with `qwen-plus`.
- Sends a Chinese Feishu interactive card to your custom bot webhook.
- Uses a zero score threshold so every successfully analyzed finance item can be considered; `digest.max_items` controls message length.

## Required GitHub Secrets

Add these under GitHub repository `Settings` -> `Secrets and variables` -> `Actions`:

```text
DASHSCOPE_API_KEY
TIANAPI_KEY
FEISHU_WEBHOOK
FEISHU_SECRET
```

`FEISHU_SECRET` can be empty only if your Feishu custom bot does not use signature verification.

## Files

- `data/config.finance.json`: Finance-only Horizon configuration.
- `.github/workflows/finance-feishu.yml`: Scheduled GitHub Actions workflow.
- `src/scrapers/tianapi.py`: TianAPI source adapter.

## Manual Test In GitHub

1. Open the repository on GitHub.
2. Go to `Actions`.
3. Choose `Finance Feishu Digest`.
4. Click `Run workflow`.

If it succeeds, your Feishu group should receive one card message.

## Local Test

Create a local `.env` file:

```text
DASHSCOPE_API_KEY=your_dashscope_key
TIANAPI_KEY=your_tianapi_key
HORIZON_WEBHOOK_URL=your_feishu_webhook
FEISHU_SECRET=your_feishu_secret
```

Then run:

```bash
uv sync
cp data/config.finance.json data/config.json
uv run horizon --hours 14
```

## Schedule

GitHub Actions cron uses UTC:

```text
0 0,4,12,16 * * *
```

That maps to:

```text
08:00 Asia/Shanghai
12:00 Asia/Shanghai
20:00 Asia/Shanghai
00:00 Asia/Shanghai
```
