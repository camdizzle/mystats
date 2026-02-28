const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('mystatsDesktop', {
  getBootstrap: () => ipcRenderer.invoke('get-bootstrap'),
  saveSettings: (payload) => ipcRenderer.invoke('save-settings', payload),
  botStart: () => ipcRenderer.invoke('bot-start'),
  botStop: () => ipcRenderer.invoke('bot-stop'),
  botSay: (message) => ipcRenderer.invoke('bot-say', message),
  openUrl: (url) => ipcRenderer.invoke('open-url', url),
  onLog: (cb) => ipcRenderer.on('app-log', (_e, line) => cb(line)),
});
