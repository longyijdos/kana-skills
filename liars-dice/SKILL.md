---
name: liars-dice
description: Play Liar's Dice (大话骰) with the user via a local web UI and companion CLI. Use when the user wants to play dice, play a bluffing bar game, or test interactive CLI/Web game capabilities.
---

# Liar's Dice (大话骰)

A fast, interactive 2-player Liar's Dice game played between an AI Agent and a human user. The user interacts through a retro pixel-art browser interface, while the Agent controls its actions via a companion CLI tool (`scripts/dice.js`).

## Rules Overview
- Each player has 5 dice hidden under their cup (total 10 dice in play).
- A bid consists of quantity and pip value (e.g. "3 个 4").
- Subsequent bids must increase the quantity, or call a higher pip with the same quantity.
- **1s are wild (万能 1 点)** by default (counting as any called pip), until a player bids on 1s directly, which permanently revokes the wild status for the rest of that round.
- Either player can challenge the previous bid by calling **Open (开盅)**.

## Project Structure
All implementation files reside in `scripts/`:
- `scripts/server.js`: HTTP + SSE game server. Serves the web UI and REST/SSE endpoints. Generates `.agent-token` for CLI authentication.
- `scripts/index.html`: Retro pixel-art web client with realtime SSE event sync.
- `scripts/dice.js`: Agent CLI client with state inspection, auto-wait semantics, and action commands.
- `scripts/.agent-cursor`: Local state tracking file for incremental event polling.

---

## Game Workflow & Agent Interaction Guidelines

All commands below should be executed relative to this skill directory (or with `scripts/` prefix).

### 1. Launch Server
Check if the server is already running, or start it as a background job:
```bash
node scripts/server.js
```
- Default port is `3456`. To use a custom port: `PORT=3457 node scripts/server.js`.
- Direct the user to open `http://localhost:3456` in their browser.

### 2. Communicating via CLI (Crucial)
Once the game starts, the human player is actively interacting in their web browser and **may not return to the Agent chat terminal** until the game finishes.
- **Always communicate in-game via CLI**: Deliver all turn commentary, trash talk, thoughts, and guidance using the action message flag (`-m "..."`) or the dedicated command `node scripts/dice.js talk "..."`.
- Messages sent through the CLI display immediately as live speech bubbles and activity logs on the user's web dashboard. Do not rely solely on the agent's LLM response text in the terminal.

### 3. Asynchronous Wait & Wakeup Rule (Mandatory)
When the Agent finishes its turn (or after starting a game where the player acts first), **the turn passes to the human player**:
- **Always launch a background job to wait**: You **MUST** launch a background job running `node scripts/dice.js wait` (e.g. via `job_start`) before completing your turn.
- **Why this is mandatory**: The user will perform their move (call, open, chat) inside the browser. If the Agent finishes its response without leaving an active background `wait` process, the Agent session will enter an idle state and **will NOT be woken up** when the user makes their move in the browser.
- **When the background job completes**: You will automatically be notified. Inspect the job output to see the player's action and continue the match.

### 4. Command Execution Pattern (`--no-wait` + Background `wait`)
By default, `dice.js` actions (`call`, `open`, `new`, `talk`) use auto-wait (HTTP long-polling up to 30s when turn transfers). Because users often take longer than 30s to think in the browser, foreground commands risk hitting tool execution timeouts.

**Standard Agent Turn Pattern**:
1. Inspect state if needed:
   ```bash
   node scripts/dice.js status
   ```
2. Execute the move with `--no-wait` and include an in-game message:
   ```bash
   node scripts/dice.js call <count> <point> -m "Taunt message" --no-wait
   # or
   node scripts/dice.js open -m "Taunt message" --no-wait
   ```
3. If the game continues and it is the user's turn, **immediately start a background job**:
   ```bash
   # Launch as background job
   node scripts/dice.js wait
   ```
4. Wait for the background job completion notification, consume output via job tools, and repeat.

---

## Command Reference

- **Inspect Status**:
  ```bash
  node scripts/dice.js status
  # or
  node scripts/dice.js observe [--json]
  ```

- **Start New Game**:
  ```bash
  node scripts/dice.js new [player|agent] [-m "Welcome/Taunt message"] [--no-wait]
  ```

- **Make a Bid (Call)**:
  ```bash
  node scripts/dice.js call <count> <point> [-m "Message"] [--no-wait]
  ```

- **Challenge / Open Cup**:
  ```bash
  node scripts/dice.js open [-m "Message"] [--no-wait]
  ```

- **Standalone Table Talk**:
  Send a message directly to the web dashboard without taking a game turn:
  ```bash
  node scripts/dice.js talk "怎么想了这么久，不敢叫了吗？" [--no-wait]
  ```

- **Wait for Events / User Action**:
  ```bash
  node scripts/dice.js wait
  ```
  Blocks until the user makes a move, sends a message, or starts a new round.

### 5. Cleanup
When the user indicates they are finished playing, terminate the background `node scripts/server.js` process.
