---
name: edge-tts
description: |
  Use this when the user wants to hear something spoken aloud as TTS audio,
  or asks to speak/say a message out loud. Converts Chinese or English text
  to speech with Microsoft Edge voices and plays it through `kana-say`.
---

# Edge TTS

Use `kana-say` (a wrapper around `edge-tts`'s `edge-playback`) to speak text
out loud. It outputs nothing; the audio is the only result.

## Run

All paths relative to this skill directory:

```bash
bash scripts/kana-say "Text to read aloud"
echo "Text" | bash scripts/kana-say
bash scripts/kana-say -v zh-CN-YunxiNeural -r +20% "Text"
bash scripts/kana-say -f /path/to/file.txt
```

The wrapper is self-contained at `scripts/kana-say`; no global install is
needed for the wrapper itself.

## Parameters

| Flag | Meaning | Default |
|---|---|---|
| `-v` | Voice name | `zh-CN-XiaoxiaoNeural` |
| `-r` | Rate like `+20%`, `-10%` | `+0%` |
| `-f` | Read text from file instead of args/stdin | — |
| `-h` | Show usage | — |

Environment variables `KANA_SAY_VOICE` and `KANA_SAY_RATE` override the
corresponding defaults.

Common Chinese voices: `zh-CN-XiaoxiaoNeural` (Xiaoxiao, default),
`zh-CN-YunxiNeural` (Yunxi), `zh-CN-YunyangNeural` (Yunyang),
`zh-CN-XiaoyiNeural` (Xiaoyi), `zh-CN-YunjianNeural` (Yunjian).

## Dependencies

- `edge-tts` installed via `uv tool install edge-tts` (provides `edge-playback`
  on PATH; required, the wrapper calls it)

## Operating rules

1. Speak only when the user asks to hear something said out loud. Do not
   proactively speak at the start of a turn.
2. `kana-say` is silent on success: a clean exit (no output, exit 0) is the
   success signal. Exit 1 after retries means the TTS call failed.
3. The wrapper retries the TTS call a few times internally before giving up.
   Do not retry the command repeatedly on failure; report the failure instead.
4. Use the default voice unless the user expresses a preference; the default
   is `zh-CN-XiaoxiaoNeural` (Xiaoxiao).
5. Keep text natural and short (a sentence or two). Read the user's intent,
   not verbatim long code or dumps.
