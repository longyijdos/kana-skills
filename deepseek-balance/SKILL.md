---
name: deepseek-balance
description: |
  Use this only when you need to query the DeepSeek API account balance.
  Returns available balance, granted balance, and topped-up balance
  in both CNY and USD.
---

# DeepSeek Balance

Use the bundled script to query DeepSeek API account balance via the `/user/balance` endpoint.

## Parameters

None. This skill takes no arguments.

## Dependencies

- `DEEPSEEK_API_KEY` environment variable
- Python 3 standard library only (no external packages)

## Run

```bash
python scripts/check_balance.py
```

Returns JSON with `is_available`, `balance_infos` (currency, total_balance,
granted_balance, topped_up_balance).

## Handling Results

- Report whether the account is available before listing balances.
- Preserve currency labels from `balance_infos`.
- If multiple currencies are returned, summarize each currency separately.
- If the script returns an `error`, report the missing `DEEPSEEK_API_KEY`, HTTP status, or connection failure directly.
