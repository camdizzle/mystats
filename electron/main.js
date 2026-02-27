const path = require('path');
const { app, BrowserWindow, ipcMain, shell } = require('electron');
const { startServer } = require('../server');
const { parseSettings, updateSetting, ensureDefaults } = require('../lib/settings');
const { TwitchIrcBot } = require('../lib/twitch_bot');

const ROOT = path.resolve(__dirname, '..');
// Harden Electron startup for headless/root/dev environments.
// This avoids Chromium sandbox/zygote startup crashes that can surface as ICU fd errors.
if (process.platform === 'linux') {
  app.commandLine.appendSwitch('no-sandbox');
  app.commandLine.appendSwitch('disable-setuid-sandbox');
  app.commandLine.appendSwitch('disable-gpu');
  app.disableHardwareAcceleration();
}

const settingsPath = process.env.MYSTATS_SETTINGS || path.join(ROOT, 'settings.txt');
const defaults = {
  overlay_server_port: '5000',
  app_language: 'en',
  overlay_theme: 'midnight',
  directory: ROOT,
};

let mainWindow = null;
const logBuffer = [];

function emitLog(message) {
  const line = `[${new Date().toLocaleTimeString()}] ${message}`;
  logBuffer.push(line);
  if (logBuffer.length > 600) logBuffer.shift();
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('app-log', line);
  }
}

ensureDefaults(settingsPath, defaults);
const { port } = startServer();
emitLog(`Node server started on port ${port}`);

const bot = new TwitchIrcBot({ settingsPath, log: (m) => emitLog(m) });

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1360,
    height: 860,
    minWidth: 1180,
    minHeight: 760,
    title: 'MyStats',
    backgroundColor: '#0b1120',
    webPreferences: {
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  mainWindow.loadFile(path.join(ROOT, 'desktop_app', 'index.html'));
}

ipcMain.handle('get-bootstrap', async () => {
  const settings = parseSettings(settingsPath);
  return {
    settings,
    port,
    logs: [...logBuffer],
  };
});

ipcMain.handle('save-settings', async (_e, payload) => {
  const current = parseSettings(settingsPath);
  const merged = { ...current };
  for (const [k, v] of Object.entries(payload || {})) merged[k] = String(v ?? '');
  for (const [k, v] of Object.entries(merged)) updateSetting(settingsPath, k, v);
  emitLog('Settings saved from desktop window.');
  return parseSettings(settingsPath);
});

ipcMain.handle('bot-start', async () => {
  bot.start();
  return true;
});

ipcMain.handle('bot-stop', async () => {
  bot.stop();
  emitLog('Bot stopped.');
  return true;
});

ipcMain.handle('bot-say', async (_e, message) => {
  const ok = bot.say(String(message || ''));
  emitLog(ok ? `Sent chat: ${message}` : 'Bot not connected; message not sent.');
  return ok;
});

ipcMain.handle('open-url', async (_e, url) => {
  await shell.openExternal(url);
  return true;
});

app.whenReady().then(createWindow);
app.on('window-all-closed', () => {
  bot.stop();
  if (process.platform !== 'darwin') app.quit();
});

process.on('uncaughtException', (err) => {
  emitLog(`Fatal error: ${err?.stack || err}`);
});

process.on('unhandledRejection', (reason) => {
  emitLog(`Unhandled rejection: ${reason}`);
});
