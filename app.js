const path = require('path');
const readline = require('readline');
const { startServer } = require('./server');
const { parseSettings, updateSetting, ensureDefaults } = require('./lib/settings');
const { TwitchIrcBot } = require('./lib/twitch_bot');

const ROOT = __dirname;
const settingsPath = process.env.MYSTATS_SETTINGS || path.join(ROOT, 'settings.txt');

const DEFAULTS = {
  overlay_server_port: '5000',
  app_language: 'en',
  overlay_theme: 'midnight',
  directory: ROOT,
};

ensureDefaults(settingsPath, DEFAULTS);

function log(msg) {
  process.stdout.write(`${msg}\n`);
}

const { port } = startServer();
log(`[app] Web runtime started on port ${port}`);

const bot = new TwitchIrcBot({ settingsPath, log });

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  prompt: 'mystats> ',
});

function printHelp() {
  log('Commands:');
  log('  help                          Show this help');
  log('  settings list                 List all settings');
  log('  settings set <k> <v>          Update a setting in settings.txt');
  log('  settings get <k>              Get one setting');
  log('  bot start                     Start Twitch IRC bot');
  log('  bot stop                      Stop Twitch IRC bot');
  log('  bot say <message>             Send a chat message');
  log('  urls                          Print dashboard/overlay URLs');
  log('  exit                          Stop app');
}

function printUrls() {
  log(`Dashboard: http://127.0.0.1:${port}/dashboard`);
  log(`Overlay:   http://127.0.0.1:${port}/overlay`);
  log(`Tilt:      http://127.0.0.1:${port}/overlay/tilt`);
}

printHelp();
printUrls();
rl.prompt();

rl.on('line', (line) => {
  const raw = line.trim();
  if (!raw) return rl.prompt();

  const [cmd, sub, ...rest] = raw.split(' ');

  if (cmd === 'help') {
    printHelp();
  } else if (cmd === 'urls') {
    printUrls();
  } else if (cmd === 'settings') {
    if (sub === 'list') {
      const settings = parseSettings(settingsPath);
      Object.keys(settings).sort().forEach((k) => log(`${k}=${settings[k]}`));
    } else if (sub === 'set') {
      const key = rest[0];
      const value = rest.slice(1).join(' ');
      if (!key) {
        log('Usage: settings set <key> <value>');
      } else {
        updateSetting(settingsPath, key, value);
        log(`Updated ${key}`);
      }
    } else if (sub === 'get') {
      const key = rest[0];
      if (!key) {
        log('Usage: settings get <key>');
      } else {
        const settings = parseSettings(settingsPath);
        log(`${key}=${settings[key] ?? ''}`);
      }
    } else {
      log('Usage: settings [list|get|set] ...');
    }
  } else if (cmd === 'bot') {
    if (sub === 'start') bot.start();
    else if (sub === 'stop') bot.stop();
    else if (sub === 'say') {
      const msg = rest.join(' ');
      if (!msg) log('Usage: bot say <message>');
      else if (!bot.say(msg)) log('Bot not connected. Run: bot start');
    } else {
      log('Usage: bot [start|stop|say] ...');
    }
  } else if (cmd === 'exit' || cmd === 'quit') {
    bot.stop();
    rl.close();
    process.exit(0);
  } else {
    log(`Unknown command: ${cmd}`);
  }

  rl.prompt();
});

rl.on('SIGINT', () => {
  bot.stop();
  rl.close();
  process.exit(0);
});
