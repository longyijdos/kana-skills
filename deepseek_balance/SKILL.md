---
name: deepseek-balance
description: |
  Use this when you need to query the DeepSeek API account balance.
  Returns available balance, granted balance, and topped-up balance
  in both CNY and USD.
---

# DeepSeek Balance

Query DeepSeek API account balance via the `/user/balance` endpoint.

## When to Use

- User wants to check their DeepSeek API balance
- User asks "how much credit do I have", "check my DeepSeek balance", etc.
- Monitoring API usage / remaining quota

## Parameters

None — this skill takes no arguments.

## Dependencies

- `DEEPSEEK_API_KEY` environment variable
- Python 3 standard library only (no external packages)

## Usage

```bash
python scripts/check_balance.py
```

Returns JSON with `is_available`, `balance_infos` (currency, total_balance,
granted_balance, topped_up_balance).
