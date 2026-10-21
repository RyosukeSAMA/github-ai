'use strict';
const {contextBridge, ipcRenderer, webUtils} = require('electron');
const dropCallbacks=new Set();
contextBridge.exposeInMainWorld('pantheonDesktop', Object.freeze({
  info: () => ipcRenderer.invoke('desktop:info'),
  chooseWorkspace: () => ipcRenderer.invoke('desktop:workspace'),
  onWorkspaceStatus: callback => {const listener=(_event,value)=>callback(value);ipcRenderer.on('desktop:workspace-status',listener);return ()=>ipcRenderer.removeListener('desktop:workspace-status',listener);},
  reconnect: () => ipcRenderer.invoke('desktop:reconnect'),
  connectRemote: value => ipcRenderer.invoke('desktop:remote', value),
  reconnectRemote: () => ipcRenderer.invoke('desktop:remote-reconnect'),
  api: (target, options) => ipcRenderer.invoke('desktop:api', target, options),
  pickFiles: kind => ipcRenderer.invoke('desktop:files',kind),
  reveal: relative => ipcRenderer.invoke('desktop:reveal', relative),
  newWindow: sessionId => ipcRenderer.invoke('desktop:window', sessionId),
  openWorktree: target => ipcRenderer.invoke('desktop:worktree', target),
  preferences: value => ipcRenderer.invoke('desktop:preferences', value),
  notify: value => ipcRenderer.invoke('desktop:notify', value),
  updates: () => ipcRenderer.invoke('desktop:updates'),
  openLink: value => ipcRenderer.invoke('desktop:open-link',value),
  exportArchive: id => ipcRenderer.invoke('desktop:archive',id),
  mediaFile: (id,save) => ipcRenderer.invoke('desktop:media-file',id,save),
  onDrop: callback => {dropCallbacks.add(callback);return ()=>dropCallbacks.delete(callback);},
  onUpdate: callback => {const listener=(_event,value)=>callback(value);ipcRenderer.on('desktop:update',listener);return ()=>ipcRenderer.removeListener('desktop:update',listener);},
  openRelease: () => ipcRenderer.invoke('desktop:release'),
  terminal: value => ipcRenderer.invoke('desktop:terminal', value),
  stopTerminal: () => ipcRenderer.invoke('desktop:terminal-stop'),
  onTerminal: callback => { const listener = (_event, value) => callback(value); ipcRenderer.on('desktop:terminal-data',listener); return () => ipcRenderer.removeListener('desktop:terminal-data',listener); },
  onCommand: callback => { const listener = (_event, value) => callback(value); ipcRenderer.on('desktop:command',listener); return () => ipcRenderer.removeListener('desktop:command',listener); },
}));

window.addEventListener('drop',event=>{if(!event.isTrusted||!event.dataTransfer?.files.length)return;const paths=[...event.dataTransfer.files].map(file=>webUtils.getPathForFile(file));if(paths.some(path=>!path))return;event.preventDefault();event.stopImmediatePropagation();ipcRenderer.invoke('desktop:drop',paths).then(value=>dropCallbacks.forEach(callback=>callback(value))).catch(error=>dropCallbacks.forEach(callback=>callback({error:error.message})));},true);
