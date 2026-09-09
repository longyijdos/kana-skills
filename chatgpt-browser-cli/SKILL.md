---
name: chatgpt-browser-cli
description: |
  Use this when complex reasoning, difficult analysis, or public-web research would
  benefit from a second independent answer from ChatGPT. Uses a local browser CLI
  with an imported Edge login and may take several minutes to return.
---

# ChatGPT Browser CLI

Use the CLI in this skill directory to obtain a supplementary answer from ChatGPT.
Keep doing any independent work that does not depend on the answer while the command
runs. Treat the result as a second opinion rather than as authoritative evidence.

## Operating rules

1. Run the preflight check before the first query in each task.
2. Never print, inspect, summarize, or transmit values from `.auth/chatgpt.json`.
3. Send only the context needed for the question. Remove credentials, private data,
   and unrelated repository contents.
4. Run one query at a time. Do not start duplicate queries because an answer is slow.
5. Prefer the execution environment's background process or yielded-session support.
   If none is available, run the command in the foreground.

## Preflight and Cookie refresh

From this skill directory, run:

```bash
uv run chatgpt-cli check
```

Read the specific `Cookie 本地有效期` result rather than relying only on the process
exit code, because other fingerprint checks also affect that code.

- `PASS`: continue to the query.
- `WARN`: one or more Cookies have expired. Run `import-edge` once, then check again.
- `FAIL`, or a missing state-file error: run `import-edge` once, then check again.

Refresh from the currently logged-in macOS Edge profile with:

```bash
uv run chatgpt-cli import-edge
```

Importing may require macOS Keychain access. If interaction is required and the agent
cannot provide it, stop and tell the user what action is needed. Never repeat imports
in a loop. After one refresh:

- If all Cookies are still expired or no Cookies were imported, stop and report the
  problem.
- If only a partial-expiry warning remains while unexpired or session Cookies exist,
  continue; the local expiry data cannot identify which Cookie controls the server
  session.
- If a non-Cookie check is `FAIL`, report it instead of starting a query.

The preflight compares only the saved `expires` timestamps. It does not prove that
ChatGPT still accepts the login session.

## Run a query

Use a focused prompt that contains the question, essential context, desired output,
and relevant constraints:

```bash
uv run chatgpt-cli ask --timeout 300 "your question"
```

For long inputs (such as rich context, extensive code snippets, or lengthy prompts over 150-200 characters), add `--fast` to use direct DOM input rather than simulated keystrokes:

```bash
uv run chatgpt-cli ask --fast --timeout 300 "your long question..."
```

> **Risk note**: `--fast` bypasses human-like typing delays and mouse trajectories, filling the input box instantly. While safe for occasional use, using `--fast` excessively or on very frequent queries may increase detection risk by Cloudflare or ChatGPT anti-bot systems.

For complex reasoning, ask for an independent analysis and make important assumptions
explicit. For web research, ask for source URLs and relevant publication dates, then
verify material claims against the original sources before using them.

## Background execution

ChatGPT may take several minutes to answer. When the agent environment supports a
background process, asynchronous command, or yielded execution session:

1. Start the `ask` command with a short initial yield and retain its process or session
   identifier.
2. Continue independent local analysis while it runs.
3. Wait for or poll the existing process at reasonable intervals.
4. Read stdout only after the process finishes; use stderr to diagnose a failure.

Do not launch another query while the first is still running. If the command reaches
its timeout, confirm that the original process has exited before retrying once with a
larger `--timeout` value.

## Handling results

- Use stdout as ChatGPT's answer and integrate only the parts supported by your own
  reasoning or verification.
- Treat cited links as discovery leads. Fetch the original pages before quoting them
  or relying on precise factual claims.
- Clearly distinguish the CLI's conclusions from independently verified facts when
  they disagree.
- If the command exits unsuccessfully or returns an empty answer, report the concrete
  error; do not invent or reconstruct a missing response.

## Dependencies

- `uv`
- Microsoft Edge on macOS
- An Edge profile currently logged in to ChatGPT
- Network access to `chatgpt.com`
