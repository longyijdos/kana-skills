---
name: liars-dice
description: Play Liar's Dice (大话骰) with the user via a local web UI and companion CLI. Use when the user wants to play dice, play a bluffing bar game, or test interactive CLI/Web game capabilities.
---

# Liar's Dice (大话骰)

A fast, interactive 2-player Liar's Dice game played between an AI Agent and a human user. The user interacts through a retro pixel-art browser interface, while the Agent controls its actions via a companion CLI tool (`dice.js`).

## Rules Overview
- Each player has 5 dice hidden under their cup (total 10 dice in play).
- A bid consists of quantity and pip value (e.g. "3 个 4").
- Subsequent bids must increase the quantity, or call a higher pip with the same quantity.
- **1s are wild (万能 1 点)** by default (counting as any called pip), until a player bids on 1s directly, which permanently revokes the wild status for the rest of that round.
- Either player can challenge the previous bid by calling **Open (开盅)**.

## Project Structure
All files reside in this skill directory:
- `server.js`: HTTP + SSE game server. Serves the web UI and REST/SSE endpoints. Generates `.agent-token` for CLI authentication.
- `index.html`: Retro pixel-art web client with realtime SSE event sync.
- `dice.js`: Agent CLI client with state inspection, auto-wait semantics, and action commands.
- `.agent-cursor`: Local state tracking file for incremental event polling.

---

## Game Workflow

### 1. Launch Server
Check if the server is already running, or start it as a background job:
```bash
node server.js
```
- Default port is `3456`. To use a custom port: `PORT=3457 node server.js`.
- Direct the user to open `http://localhost:3456` in their browser.

### 2. Status & Observation
Inspect the current game state, your dice, whose turn it is, and event history:
```bash
node dice.js status
# or
node dice.js observe
```
Add `--json` if structured JSON output is preferred.

### 3. Understanding the Wait Mechanism (`wait: auto` vs `--no-wait`)
By default, `dice.js` commands (`call`, `open`, `new`, `talk`) use **auto-wait**:
- If the action results in the turn passing to the human player, the command will **block** (HTTP long-polling for up to 30s) until the player responds or an unread event arrives.
- If it is already/still the Agent's turn, or if the game has ended (settled), the command **returns immediately**.
- Passing **`--no-wait`** forces immediate return without blocking.

**Agent Execution Strategy**:
- When using tools with strict command execution timeouts (e.g. 30s), blocking foreground commands can risk timeouts if the human takes time to think.
- **Recommended Agent Pattern**:
  1. Execute actions with `--no-wait` for instantaneous feedback and state synchronization.
  2. If the turn shifts to the user, launch a background job to wait for the user's move:
     ```bash
     node dice.js wait
     ```
  3. When the background job completes, read its output to see the player's move, then make your next turn.

### 4. Game Actions & Table Banter

- **Start a New Game**:
  ```bash
  node dice.js new [player|agent] [-m "Table message"] [--no-wait]
  ```
  `starter` defaults to `player`.

- **Make a Bid (Call)**:
  ```bash
  node dice.js call <count> <point> [-m "Table message"] [--no-wait]
  ```
  *Example*: `node dice.js call 3 5 -m "起步先来 3 个 5，你跟不跟？" --no-wait`

- **Challenge / Open Cup**:
  ```bash
  node dice.js open [-m "Table message"] [--no-wait]
  ```
  *Example*: `node dice.js open -m "我手里一颗都没有，开盅抓你！" --no-wait`

- **Standalone Table Talk (Chat / Trash Talk)**:
  Send a message directly to the table talk history without making a move:
  ```bash
  node dice.js talk "怎么想了这么久，不敢叫了吗？" [--no-wait]
  ```
  This displays as an in-game speech bubble and chat entry on the human player's web screen.

- **Wait for Events / Human Action**:
  ```bash
  node dice.js wait
  ```
  Blocks until a new event occurs (e.g., human makes a move or speaks) and outputs the updated game state.

### 5. Game End & Cleanup
- When a game ends, the winner and full cup reveal are output by `dice.js`.
- Either side can initiate a new round with `node dice.js new`.
- When the user is done playing, terminate the background `node server.js` process.
