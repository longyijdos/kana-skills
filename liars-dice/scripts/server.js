#!/usr/bin/env node
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const DEFAULT_TIMEOUT_MS = 10 * 60 * 1000;
const roleName = role => role === 'player' ? '玩家' : 'Agent';

class GameEngine {
  constructor() {
    this.status = 'waiting';
    this.playerDice = [];
    this.agentDice = [];
    this.history = [];
    this.currentTurn = null;
    this.currentBid = null;
    this.onesAreWild = true;
    this.result = null;
  }

  rollDice() {
    return Array.from({ length: 5 }, () => Math.floor(Math.random() * 6) + 1)
      .sort((a, b) => a - b);
  }

  isMyTurn(role) {
    return this.status === 'playing' && this.currentTurn === role;
  }

  isValidBid(count, point) {
    if (!Number.isInteger(count) || !Number.isInteger(point)) return false;
    if (count < 2 || count > 10 || point < 1 || point > 6) return false;
    return !this.currentBid || count > this.currentBid.count ||
      (count === this.currentBid.count && point > this.currentBid.point);
  }

  executeAction(role, payload) {
    const { action } = payload;

    if (action === 'new') {
      if (this.status === 'playing') throw new Error('对局进行中，不能重新开局');
      const starter = payload.starter === undefined ? 'player' : payload.starter;
      if (starter !== 'player' && starter !== 'agent') {
        throw new Error('starter 必须是 player 或 agent');
      }
      this.status = 'playing';
      this.playerDice = this.rollDice();
      this.agentDice = this.rollDice();
      this.currentTurn = starter;
      this.currentBid = null;
      this.onesAreWild = true;
      this.result = null;
      const text = `对局开启！先手方: ${roleName(starter)}`;
      this.history = [{ sender: 'system', type: 'system', text }];
      return { type: 'game_start', sender: role, message: text, text, data: { starter } };
    }

    if (!['talk', 'call', 'open'].includes(action)) {
      throw new Error(`未知动作类型: ${action}`);
    }
    if (payload.message !== undefined && typeof payload.message !== 'string') {
      throw new Error('message 必须是字符串');
    }
    const message = (payload.message || '').trim();

    if (action === 'talk') {
      if (!message) throw new Error('台词内容不能为空');
      const text = `${roleName(role)}说: ${message}`;
      this.history.push({ sender: role, type: 'talk', message, text });
      return { type: 'chat_talk', sender: role, message, text, data: {} };
    }

    if (this.status !== 'playing') throw new Error('当前对局未开始或已结束');
    if (!this.isMyTurn(role)) throw new Error(`当前不是 ${role} 的行动回合`);

    if (action === 'call') {
      const { count, point } = payload;
      if (!this.isValidBid(count, point)) {
        throw new Error('叫点不合法：2 至 10 个、点数 1 至 6；数量需更多，或数量相同点数更大');
      }
      if (point === 1) this.onesAreWild = false;
      this.currentBid = { count, point, bidder: role };
      this.currentTurn = role === 'player' ? 'agent' : 'player';
      const text = `${roleName(role)} 叫了 ${count} 个 ${point}` +
        (point === 1 ? '（1点失去通配）' : '') + (message ? `「${message}」` : '');
      this.history.push({ sender: role, type: 'call', count, point, message, text });
      return { type: 'action_call', sender: role, message, text, data: { count, point } };
    }

    if (!this.currentBid) throw new Error('尚未有人叫点，无法喊开');
    const { count: bidCount, point: targetPoint, bidder } = this.currentBid;
    const wild = this.onesAreWild && targetPoint !== 1;
    const actualCount = [...this.playerDice, ...this.agentDice]
      .filter(d => d === targetPoint || (wild && d === 1)).length;
    const winner = actualCount >= bidCount ? bidder : role;
    const reason = `场上实际有 ${actualCount} 个 ${targetPoint}（叫了 ${bidCount} 个），` +
      `${roleName(role)} ${actualCount >= bidCount ? '开错' : '抓虚成功'}，${roleName(winner)} 获胜！`;
    this.result = {
      opener: role, bidder, targetPoint, bidCount, actualCount,
      allDice: { player: this.playerDice, agent: this.agentDice },
      onesAreWild: wild, winner, reason
    };
    this.status = 'ended';
    this.currentTurn = null;
    const text = `${roleName(role)} 喊了开！【${roleName(winner)}获胜】` +
      (message ? `「${message}」` : '');
    this.history.push({ sender: role, type: 'open', message, text });
    return { type: 'action_open', sender: role, message, text, data: { result: this.result } };
  }

  getStateForRole(role) {
    const isPlayer = role === 'player';
    return {
      role,
      status: this.status,
      currentTurn: this.currentTurn,
      isMyTurn: this.isMyTurn(role),
      currentBid: this.currentBid,
      onesAreWild: this.onesAreWild,
      myDice: isPlayer ? this.playerDice : this.agentDice,
      opponentDiceCount: (isPlayer ? this.agentDice : this.playerDice).length,
      opponentDice: this.status === 'ended' ?
        (isPlayer ? this.agentDice : this.playerDice) : undefined,
      history: this.history,
      result: this.result
    };
  }
}

// 事件记录公共动作；私有骰子只通过角色状态提供，结算时才公开。
class EventLog {
  constructor() {
    this.events = [];
  }

  get seq() {
    return this.events.length;
  }

  append(event) {
    const entry = { ...event, seq: this.seq + 1 };
    this.events.push(entry);
    return entry;
  }

  since(after) {
    return this.events.slice(after);
  }

  hasUnreadOpponentEvents(role, after) {
    return this.since(after).some(event => event.sender !== role);
  }
}

class WaitManager {
  constructor() {
    this.waiters = new Set();
  }

  wait(role, timeoutMs, respond, eventsOnly = false) {
    const waiter = { role, eventsOnly, finish: timedOut => {
      cancel();
      respond(timedOut);
    } };
    const cancel = () => {
      clearTimeout(timer);
      this.waiters.delete(waiter);
    };
    const timer = setTimeout(() => waiter.finish(true), timeoutMs);
    this.waiters.add(waiter);
    return cancel;
  }

  publish(event) {
    for (const waiter of this.waiters) {
      if (waiter.eventsOnly || event.sender !== waiter.role) waiter.finish(false);
    }
  }
}

async function readJson(req) {
  let body = '';
  for await (const chunk of req) body += chunk;
  const payload = body ? JSON.parse(body) : {};
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    throw new Error('请求体必须是 JSON 对象');
  }
  return payload;
}

function sendJson(res, status, data) {
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization'
  });
  res.end(JSON.stringify(data));
}

function createGameServer({
  agentToken = crypto.randomBytes(24).toString('hex'),
  playerToken = crypto.randomBytes(24).toString('hex')
} = {}) {
  const game = new GameEngine();
  const log = new EventLog();
  const waits = new WaitManager();
  const snapshot = (role, after, timedOut = false) => ({
    success: true,
    state: game.getStateForRole(role),
    events: log.since(after),
    seq: log.seq,
    timedOut
  });

  const park = (role, after, timeoutMs, res, eventsOnly = false) => {
    const cancel = waits.wait(role, timeoutMs, timedOut => {
      res.off('close', cancel);
      sendJson(res, 200, snapshot(role, after, timedOut));
    }, eventsOnly);
    res.once('close', cancel);
  };

  return http.createServer(async (req, res) => {
    const pathname = new URL(req.url, 'http://localhost').pathname;
    if (req.method === 'OPTIONS') return sendJson(res, 204, {});

    if ((pathname === '/' || pathname === '/index.html') && req.method === 'GET') {
      fs.readFile(path.join(__dirname, 'index.html'), (err, html) => {
        res.writeHead(err ? 500 : 200, { 'Content-Type': 'text/html; charset=utf-8' });
        res.end(err ? 'Error loading index.html' : html);
      });
      return;
    }
    if (pathname === '/api/v1/player/auth' && req.method === 'POST') {
      return sendJson(res, 200, { success: true, playerToken });
    }
    if (!['/api/v1/state', '/api/v1/action', '/api/v1/wait'].includes(pathname)) {
      return sendJson(res, 404, { success: false, error: '接口不存在' });
    }
    const authHeader = req.headers.authorization || '';
    const token = authHeader.startsWith('Bearer ') ? authHeader.slice(7).trim() : '';
    const role = token === agentToken ? 'agent' : token === playerToken ? 'player' : null;
    if (!role) return sendJson(res, 403, { success: false, error: 'Token 无效或缺失' });
    if (pathname === '/api/v1/state' && req.method === 'GET') {
      return sendJson(res, 200, snapshot(role, log.seq));
    }
    if (pathname === '/api/v1/state' || req.method !== 'POST') {
      return sendJson(res, 405, { success: false, error: '请求方法不支持' });
    }

    let after = log.seq;
    try {
      const payload = await readJson(req);
      after = payload.after === undefined && pathname === '/api/v1/action' ? log.seq : payload.after;
      if (!Number.isInteger(after) || after < 0 || after > log.seq) {
        throw new Error('after 必须是 0 至当前 seq 之间的整数');
      }
      const timeoutMs = payload.timeoutMs === undefined ? DEFAULT_TIMEOUT_MS : payload.timeoutMs;
      if (!Number.isInteger(timeoutMs) || timeoutMs < 1 || timeoutMs > 2147483647) {
        throw new Error('timeoutMs 必须是 1 至 2147483647 之间的整数');
      }
      if (pathname === '/api/v1/wait') {
        const waitFor = payload.waitFor === undefined ? 'event-or-turn' : payload.waitFor;
        if (waitFor !== 'event' && waitFor !== 'event-or-turn') {
          throw new Error('waitFor 必须是 event 或 event-or-turn');
        }
        const eventsOnly = waitFor === 'event';
        if (log.seq > after || (!eventsOnly && game.isMyTurn(role))) {
          return sendJson(res, 200, snapshot(role, after));
        }
        park(role, after, timeoutMs, res, eventsOnly);
        return;
      }

      const wait = payload.wait === undefined ? 'none' : payload.wait;
      if (wait !== 'none' && wait !== 'auto') throw new Error('wait 必须是 none 或 auto');
      // 从检查未读事件到登记等待没有 await，其他动作无法插入。
      const hadUnreadEvents = log.hasUnreadOpponentEvents(role, after);
      const event = log.append(game.executeAction(role, payload));
      waits.publish(event);
      if (wait === 'none' || hadUnreadEvents || game.isMyTurn(role) || game.status === 'ended') {
        return sendJson(res, 200, snapshot(role, after));
      }
      // 自身动作先发布，再登记等待；响应仍包含自身动作和后续事件。
      park(role, after, timeoutMs, res);
    } catch (err) {
      const errorAfter = Number.isInteger(after) && after >= 0 && after <= log.seq ? after : log.seq;
      sendJson(res, 400, { ...snapshot(role, errorAfter), success: false, error: err.message });
    }
  });
}

if (require.main === module) {
  const port = parseInt(process.env.PORT, 10) || 3456;
  const agentToken = crypto.randomBytes(24).toString('hex');
  const tokenFile = path.join(__dirname, '.agent-token');
  const server = createGameServer({ agentToken });
  server.listen(port, '127.0.0.1', () => {
    fs.writeFileSync(tokenFile, agentToken, { mode: 0o600 });
    console.log(`[Liar's Dice Arena] Server running at http://127.0.0.1:${port}/`);
    console.log(`Agent Token: ${tokenFile}`);
  });
}

module.exports = { GameEngine, EventLog, WaitManager, createGameServer };
