---
name: tldraw-offline
description: |
  Use this when the user wants to read, create, tidy, restyle, relabel, or
  screenshot a canvas in the tldraw Desktop app (tldraw offline), or mentions
  a .tldraw / .tldr file or "my canvas / 画布 / 白板". Drives the open app
  through its local HTTP API; edits stay editable and undoable in the GUI.
---

# tldraw Desktop canvas

tldraw Desktop runs a local agent API (default `http://localhost:7236`) while
the app is open. It can list open documents, read shapes and arrow bindings,
take screenshots, and run JavaScript against the live tldraw `Editor`.

## Dependencies

- tldraw Desktop running (`brew install --cask tldraw` on macOS)
- `bash`, `curl`, `python3`

## Run

All paths relative to this skill directory. `scripts/tq` re-reads the port and
per-launch token from the app's `server.json` on every call and bypasses HTTP
proxies for localhost.

1. Read the official API docs first, once per session. They cover endpoints,
   shape format, saving, lints, and recipes; follow them.

   ```bash
   bash scripts/tq readme
   ```

2. Find the document, read its shapes, then edit with one `exec` per logical
   change. Pass JavaScript on stdin through a quoted heredoc, so no JSON
   escaping is needed:

   ```bash
   bash scripts/tq search <<'EOF'
   return await api.getDocs()
   EOF

   bash scripts/tq exec "$DOC_ID" <<'EOF'
   editor.alignShapes(editor.getSelectedShapeIds(), 'top')
   await helpers.saveDoc()
   return 'ok'
   EOF
   ```

   Other endpoints: `bash scripts/tq GET|POST|DELETE <path>` (POST reads a
   JSON body from stdin).

If `server.json` is missing or the port does not answer, the app is not
running. Ask the user to open it rather than retrying.

## Undo behavior

- One `exec` call is one undo step. The user's Cmd+Z reverts exactly that call
  and nothing they drew themselves. Put one logical change (tidy layout,
  rename labels, restyle) in a single `exec` so it can be undone as a unit.
- An `exec` that throws is rolled back automatically.
- `helpers.saveDoc()` keeps the undo history.
- `helpers.translateShapes` and `helpers.renderEphemeral` write with
  `history: 'ignore'`, so their edits cannot be undone. For user-visible edits,
  use `editor.updateShapes`, `alignShapes`, `stackShapes`, or
  `distributeShapes` instead.

## Handling Results

- Keep arrow bindings intact (`api.getBindings`). An arrow near a shape is not
  the same as an arrow bound to it.
- Only change canvas content. Do not write board scripts (`script-workspace`)
  unless the user asks for durable behavior.
- Before reporting done, run `helpers.getLints()` and fix new lints. Then take
  one `api.getScreenshot` and inspect it. It returns a temp file path, not
  image data.
