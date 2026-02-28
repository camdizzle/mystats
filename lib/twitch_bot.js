const fs = require('fs');
const path = require('path');
const tls = require('tls');

class TwitchIrcBot {
  constructor({ settingsPath, log }) {
    this.settingsPath = settingsPath;
    this.log = log || console.log;
    this.socket = null;
    this.connected = false;
  }

  _readSettings() {
    const raw = fs.existsSync(this.settingsPath) ? fs.readFileSync(this.settingsPath, 'utf8') : '';
    const out = {};
    for (const line of raw.split(/\r?\n/)) {
      const i = line.indexOf('=');
      if (i < 1) continue;
      out[line.slice(0, i).trim()] = line.slice(i + 1).trim();
    }
    return out;
  }

  _readToken() {
    const tokenPath = path.join(path.dirname(this.settingsPath), 'token.json');
    if (!fs.existsSync(tokenPath)) return null;
    try {
      const parsed = JSON.parse(fs.readFileSync(tokenPath, 'utf8'));
      if (parsed?.access_token) return `oauth:${parsed.access_token}`;
    } catch {
      return null;
    }
    return null;
  }

  start() {
    if (this.socket) return;

    const settings = this._readSettings();
    const nick = (settings.TWITCH_USERNAME || settings.CHANNEL || '').replace(/^[@#]/, '').trim();
    const channel = (settings.CHANNEL || settings.TWITCH_USERNAME || '').replace(/^[@#]/, '').trim();
    const pass = this._readToken() || settings.TWITCH_OAUTH || '';

    if (!nick || !channel || !pass) {
      this.log('[bot] Missing TWITCH_USERNAME/CHANNEL/token. Bot not started.');
      return;
    }

    this.socket = tls.connect(6697, 'irc.chat.twitch.tv', () => {
      this.socket.write(`PASS ${pass}\r\n`);
      this.socket.write(`NICK ${nick}\r\n`);
      this.socket.write(`JOIN #${channel}\r\n`);
      this.connected = true;
      this.log(`[bot] Connected to #${channel} as ${nick}`);
    });

    this.socket.on('data', (buf) => {
      const lines = buf.toString('utf8').split(/\r?\n/).filter(Boolean);
      for (const line of lines) {
        if (line.startsWith('PING ')) {
          this.socket.write(line.replace('PING', 'PONG') + '\r\n');
          continue;
        }
        this.log(`[twitch] ${line}`);
      }
    });

    this.socket.on('error', (err) => {
      this.log(`[bot] Error: ${err.message}`);
    });

    this.socket.on('close', () => {
      this.connected = false;
      this.socket = null;
      this.log('[bot] Disconnected');
    });
  }

  stop() {
    if (!this.socket) return;
    try {
      this.socket.end();
    } catch {}
    this.socket = null;
    this.connected = false;
  }

  say(message) {
    if (!this.socket || !this.connected) return false;
    const settings = this._readSettings();
    const channel = (settings.CHANNEL || settings.TWITCH_USERNAME || '').replace(/^[@#]/, '').trim();
    if (!channel) return false;
    this.socket.write(`PRIVMSG #${channel} :${message}\r\n`);
    return true;
  }
}

module.exports = { TwitchIrcBot };
