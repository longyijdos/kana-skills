#!/usr/bin/env node
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');

const PORT = parseInt(process.env.PORT, 10) || 3456;
const TOKEN_FILE = path.join(__dirname, '.agent-token');
const CURSOR_FILE = path.join(__dirname, '.agent-cursor');
const DICE_ICONS = ['', '⚀', '⚁', '⚂', '⚃', '⚄', '⚅'];

const args = process.argv.slice(2);
const command = args.shift() || 'status';
const options = {};
const words = [];
let agentToken;

function usage() {
  console.log('用法: node dice.js <命令> [选项]');
  console.log('  status / observe                       读取当前状态');
  console.log('  new [--starter player|agent]           开新局');
  console.log('  call <数量> <点数> [-m "台词"]          叫点');
  console.log('  open [-m "台词"]                       喊开');
  console.log('  talk <台词>                            说话');
  console.log('  wait                                   等待未读事件或下一局');
  console.log('选项: --no-wait、--json、--after <事件序号>');
  console.log('动作默认自动等待；仍有行动权或已经结算时立即返回。');
}

function readCursor() {
  if (options.after !== undefined) return Number(options.after);
  if (!fs.existsSync(CURSOR_FILE)) return 0;
  const cursor = JSON.parse(fs.readFileSync(CURSOR_FILE, 'utf8'));
  return cursor.token === agentToken && cursor.port === PORT ? cursor.seq : 0;
}

function renderResponse(response) {
  if (options.json) {
    console.log(JSON.stringify(response, null, 2));
    return;
  }
  const { state, events, seq, timedOut } = response;
  console.log(`====================================\n【事件序号】${seq}`);
  for (const event of events) console.log(`[${event.seq}] ${event.text}`);
  if (command === 'status' || command === 'observe') {
    for (const entry of state.history) console.log(entry.text);
  }
  if (timedOut) console.log('⏳ 等待超时，返回当前状态。');

  if (state.status === 'waiting') {
    console.log('【对局状态】等待开局：使用 new，或使用 wait 等待玩家开局。');
  } else {
    console.log(`你的骰子: ${state.myDice.map(d => DICE_ICONS[d] + ' (' + d + ')').join(' ')}`);
    if (state.status === 'ended') {
      console.log(`对手骰子: ${state.opponentDice.map(d => DICE_ICONS[d] + ' (' + d + ')').join(' ')}`);
      console.log(`【结算】${state.result.reason}`);
      console.log('使用 new 发起下一局，或使用 wait 等待玩家开局。');
    } else {
      console.log(state.isMyTurn ? '👉 轮到你行动。' : '⏳ 等待玩家行动。');
      console.log(`万能1点: ${state.onesAreWild ? '有效' : '已失效'}`);
      if (state.currentBid) {
        const { count, point, bidder } = state.currentBid;
        console.log(`当前最高叫点: ${count} 个 ${point}（${bidder === 'agent' ? '你' : '玩家'}叫出）`);
      } else {
        console.log('当前无人叫点。');
      }
      if (state.isMyTurn) console.log('可用命令: call、open（已有叫点时）、talk。');
    }
  }
  console.log('====================================');
}

function requestApi(method, endpoint, payload) {
  const body = payload === undefined ? null : JSON.stringify(payload);
  const req = http.request({
    hostname: '127.0.0.1',
    port: PORT,
    path: endpoint,
    method,
    headers: {
      Authorization: `Bearer ${agentToken}`,
      ...(body ? {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body)
      } : {})
    }
  }, res => {
    let responseBody = '';
    res.on('data', chunk => { responseBody += chunk; });
    res.on('end', () => {
      try {
        const response = JSON.parse(responseBody);
        if (response.state) {
          renderResponse(response);
          fs.writeFileSync(CURSOR_FILE, JSON.stringify({ token: agentToken, port: PORT, seq: response.seq }), {
            mode: 0o600
          });
        } else if (options.json) {
          console.log(JSON.stringify(response, null, 2));
        }
        if (res.statusCode >= 400 || !response.success) {
          console.error(`[API 错误 ${res.statusCode}] ${response.error}`);
          process.exitCode = 1;
        }
      } catch (err) {
        console.error(`[响应错误] ${err.message}`);
        process.exitCode = 1;
      }
    });
  });
  req.on('error', err => {
    console.error(`[连接错误] 127.0.0.1:${PORT}: ${err.message}`);
    process.exitCode = 1;
  });
  req.end(body);
}

try {
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === '--') {
      words.push(...args.slice(i + 1));
      break;
    }
    if (arg === '--json' || arg === '--no-wait') {
      options[arg.slice(2)] = true;
    } else if (['--message', '-m', '--starter', '--after'].includes(arg)) {
      if (args[i + 1] === undefined) throw new Error(`${arg} 缺少参数`);
      options[arg === '-m' ? 'message' : arg.slice(2)] = args[++i];
    } else if (arg.startsWith('--')) {
      throw new Error(`未知选项: ${arg}`);
    } else {
      words.push(arg);
    }
  }

  if (command === 'help' || command === '--help' || command === '-h') {
    usage();
  } else {
    agentToken = (process.env.AGENT_TOKEN ||
      (fs.existsSync(TOKEN_FILE) ? fs.readFileSync(TOKEN_FILE, 'utf8') : '')).trim();
    if (!agentToken) throw new Error('未找到 Agent Token，请先启动服务或设置 AGENT_TOKEN');

    if (command === 'status' || command === 'observe') {
      requestApi('GET', '/api/v1/state');
    } else {
      const after = readCursor();
      if (!Number.isInteger(after) || after < 0) throw new Error('after 必须是非负整数');
      if (command === 'wait') {
        requestApi('POST', '/api/v1/wait', { after });
      } else {
        const payload = { action: command, after, wait: options['no-wait'] ? 'none' : 'auto' };
        if (command === 'new') {
          payload.starter = options.starter || 'player';
        } else if (command === 'talk') {
          payload.message = words.join(' ');
          if (!payload.message.trim()) throw new Error('talk 需要台词内容');
        } else if (command === 'call') {
          payload.count = Number(words[0]);
          payload.point = Number(words[1]);
          if (!Number.isInteger(payload.count) || !Number.isInteger(payload.point)) {
            throw new Error('call 需要整数数量和点数');
          }
          payload.message = options.message || '';
        } else if (command === 'open') {
          payload.message = options.message || '';
        } else {
          throw new Error(`未知命令: ${command}`);
        }
        requestApi('POST', '/api/v1/action', payload);
      }
    }
  }
} catch (err) {
  console.error(`[错误] ${err.message}`);
  usage();
  process.exitCode = 1;
}
