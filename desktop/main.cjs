'use strict';
const {app, BrowserWindow, ipcMain, dialog, protocol, net, Menu, Tray, nativeImage, Notification, globalShortcut, shell, safeStorage, clipboard} = require('electron');
const fs = require('node:fs/promises');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {Backend} = require('./backend.cjs');
const {randomUUID} = require('node:crypto');
const {desktopRelease} = require('./releases.cjs');
if (process.env.PANTHEON_DESKTOP_USER_DATA) app.setPath('userData', path.resolve(process.env.PANTHEON_DESKTOP_USER_DATA));
protocol.registerSchemesAsPrivileged([{scheme:'pantheon', privileges:{standard:true,secure:true,supportFetchAPI:true}}]);
const windows = new Map(), backends = new Map();
let preferences = {theme:'light', layout:'professional', fontSize:14, panelWidth:300, notifications:false, background:false, globalShortcut:false}, recent = [], savedRemote = null, tray, quitting = false;
const uiRoot = app.isPackaged ? path.join(process.resourcesPath,'ui') : path.join(__dirname,'..','pantheon','desktop','static');
const preferenceFile = () => path.join(app.getPath('userData'),'desktop.json');
async function savePreferences() {
  await fs.mkdir(app.getPath('userData'),{recursive:true});
  const temp = preferenceFile()+'.'+randomUUID()+'.tmp';
  await fs.writeFile(temp,JSON.stringify({preferences,recent,savedRemote}),{mode:0o600}); await fs.rename(temp,preferenceFile());
}
function coreCommand() {
  if (app.isPackaged) return {executable:path.join(process.resourcesPath,'runtime','pantheon-runtime'+(process.platform==='win32'?'.exe':'')),args:[]};
  return {executable:process.env.PANTHEON_DESKTOP_PYTHON || 'python3', args:['-m','pantheon.desktop.runner']};
}
function senderContext(event, requireBackend = true) {
  const context = windows.get(event.sender.id);
  if (!context || event.senderFrame !== event.sender.mainFrame || !event.senderFrame.url.startsWith('pantheon://app/')) throw new Error('Untrusted desktop message');
  if (requireBackend && !context.backend) throw new Error('Choose a project folder or connect a remote server first.');
  return context;
}
function publicInfo(context) {
  return {version:app.getVersion(),platform:process.platform,workspace:context.backend?.info || null,
          remote:!!context.backend?.remote,remoteOrigin:context.backend?.remote?context.backend.base:'', owned:!!context.backend?.owned, preferences,recent,
          savedRemote: savedRemote ? {url:savedRemote.url,username:savedRemote.username} : null,
          initialSession:context.initialSession || '', startupError:context.startupError || '', packaged:app.isPackaged};
}
async function attachLocal(context, target) {
  if(!context.win.isDestroyed())context.win.webContents.send('desktop:workspace-status',{phase:'opening',path:target});
  try {
  const root = await fs.realpath(target);
  const key = 'local:'+root;
  if (!backends.has(key)) backends.set(key, new Backend({...coreCommand(),env:{...process.env,PYTHONPATH:app.isPackaged?'':path.join(__dirname,'..')}}).local(root));
  try { context.backend = await backends.get(key);context.lost=false;context.startupError=''; } catch(error) { backends.delete(key); throw error; }
  recent = [root,...recent.filter(item=>item!==root)].slice(0,12); await savePreferences();
  return publicInfo(context);
  } catch(error) {
    if(!context.win.isDestroyed())context.win.webContents.send('desktop:workspace-status',{phase:'error',path:target,message:error.message});
    throw error;
  }
}
function createWindow(backend = null, initialSession = '') {
  const win = new BrowserWindow({width:1440,height:1000,minWidth:820,minHeight:680,backgroundColor:'#ffffff',
    show:process.env.PANTHEON_DESKTOP_TEST!=='1',title:'Pantheon',icon:path.join(__dirname,'assets','icon.png'),
    ...(process.platform==='darwin'?{titleBarStyle:'hiddenInset',trafficLightPosition:{x:18,y:17}}:{}),
    webPreferences:{preload:path.join(__dirname,'preload.cjs'),contextIsolation:true,sandbox:true,nodeIntegration:false,webSecurity:true,spellcheck:true,backgroundThrottling:process.env.PANTHEON_DESKTOP_TEST!=='1'}});
  const context = {win,backend,initialSession,terminal:null},windowId=win.webContents.id; windows.set(windowId,context);
  win.webContents.setWindowOpenHandler(()=>({action:'deny'}));
  win.webContents.on('will-navigate',(event,url)=>{if(!url.startsWith('pantheon://app/'))event.preventDefault();});
  win.webContents.session.setPermissionRequestHandler((_contents,_permission,callback)=>callback(false));
  win.on('close',event=>{
    if (quitting || windows.size > 1) return;
    event.preventDefault();
    if(preferences.background && tray) win.hide(); else app.quit();
  });
  win.on('closed',()=>{context.terminal?.abort(); windows.delete(windowId);});
  win.loadURL('pantheon://app/index.html');
  return context;
}
function sendCommand(command) { BrowserWindow.getFocusedWindow()?.webContents.send('desktop:command',command); }
function configureNative() {
  if(process.env.PANTHEON_DESKTOP_TEST==='1')return;
  if (!tray) {
    const icon = nativeImage.createFromPath(path.join(__dirname,'assets','icon.png')).resize({width:18,height:18});
    tray = new Tray(icon); tray.setToolTip('Pantheon');
    tray.setContextMenu(Menu.buildFromTemplate([{label:'Open Pantheon',click:()=>{ const item=[...windows.values()][0]; item?item.win.show():createWindow(); }},{label:'New window',click:()=>createWindow([...windows.values()][0]?.backend || null)},{type:'separator'},{label:'Quit Pantheon',click:()=>app.quit()}]));
    tray.on('click',()=>[...windows.values()][0]?.win.show());
  }
  globalShortcut.unregisterAll();
  if(preferences.globalShortcut) globalShortcut.register('CommandOrControl+Shift+Space',()=>{ const context=[...windows.values()][0] || createWindow();context.win.show();context.win.focus();context.win.webContents.send('desktop:command','focus'); });
}
async function checkUpdates(){
  if(process.env.PANTHEON_DESKTOP_TEST==='1')return {version:app.getVersion(),available:false,reason:'Update checks are disabled in isolated tests.'};
  const response=await fetch('https://api.github.com/repos/RyosukeSAMA/github-ai/releases/latest',{signal:AbortSignal.timeout(12000),redirect:'error'});if(!response.ok)throw new Error('Release check is unavailable.');
  const result=desktopRelease(await response.json(),app.getVersion(),process.platform,process.arch);
  if(result.available)for(const context of windows.values())context.win.webContents.send('desktop:update',result);return result;
}
function notifyTask(backend,body){if(!preferences.notifications||!Notification.isSupported())return;const note=new Notification({title:'Pantheon',body});note.on('click',()=>{const context=[...windows.values()].find(item=>item.backend===backend)||createWindow(backend);context.win.show();context.win.focus();});note.show();}
let monitoring=false;const observed=new WeakMap();
async function monitorTasks(){
  if(monitoring||quitting||app.quitPending)return;monitoring=true;
  try{for(const result of await Promise.allSettled([...backends.values()])){if(result.status!=='fulfilled')continue;const backend=result.value;try{
    const value=await backend.request('/api/desktop/sessions');let seen=observed.get(backend);if(!seen){seen=new Map();observed.set(backend,seen);}
    for(const run of value.runs){const previous=seen.get(run.id);if(previous&&['queued','running','stopping'].includes(previous.status)&&!['queued','running','stopping'].includes(run.status))notifyTask(backend,run.status==='completed'?'A task has completed.':'A task needs your attention.');
      const record={status:run.status,cursor:previous?.cursor||0};
      if(['queued','running','stopping'].includes(run.status)){const events=await backend.request('/api/desktop/runs/'+run.id+'/events?after='+record.cursor);for(const event of events.events){record.cursor=event.id;if(event.event==='mcp_approval_required')notifyTask(backend,'A task needs tool approval. Open Pantheon to review it.');}}
      seen.set(run.id,record);
    }const ids=new Set(value.runs.map(run=>run.id));for(const id of seen.keys())if(!ids.has(id))seen.delete(id);
  }catch{for(const context of windows.values())if(context.backend===backend&&!context.lost){context.lost=true;context.win.webContents.send('desktop:command','connection-lost');}}}}finally{monitoring=false;}
}
function installIPC() {
  ipcMain.handle('desktop:info',event=>publicInfo(senderContext(event,false)));
  ipcMain.handle('desktop:workspace',async event=>{const context=senderContext(event,false);const result=await dialog.showOpenDialog(context.win,{title:'Choose a Pantheon project',properties:['openDirectory','createDirectory']});return result.canceled?{canceled:true,info:publicInfo(context)}:{canceled:false,info:await attachLocal(context,result.filePaths[0])};});
  ipcMain.handle('desktop:reconnect',async event=>{const context=senderContext(event),old=context.backend;if(old.remote)throw new Error('Sign in to the remote host again.');try{await old.identity();return publicInfo(context);}catch{}if(old.owned&&old.child?.exitCode===null)throw new Error('The core process is still running. Wait for it to recover before reconnecting.');backends.delete('local:'+old.workspace);return attachLocal(context,old.workspace);});
  ipcMain.handle('desktop:api',async(event,target,options)=>senderContext(event).backend.request(target,options));
  ipcMain.handle('desktop:remote',async(event,value)=>{
    const context=senderContext(event,false);
    if(value?.remember && (!safeStorage.isEncryptionAvailable() || (process.platform==='linux' && safeStorage.getSelectedStorageBackend()==='basic_text')))throw new Error('Secure storage is unavailable. Connect without remembering the password.');
    if(!value || typeof value.url!=='string' || typeof value.username!=='string' || typeof value.password!=='string')throw new Error('Server, username and password are required.');
    const backend=await new Backend(coreCommand()).connectRemote(value);backends.set('remote:'+backend.base+':'+value.username,Promise.resolve(backend));context.backend=backend;
    if(value.remember){
      if(!safeStorage.isEncryptionAvailable() || (process.platform==='linux' && safeStorage.getSelectedStorageBackend()==='basic_text'))throw new Error('Secure storage is unavailable. Connect without remembering the password.');
      savedRemote={url:backend.base,username:value.username,password:safeStorage.encryptString(value.password).toString('base64')};await savePreferences();
    }else if(savedRemote?.url===backend.base&&savedRemote.username===value.username){savedRemote=null;await savePreferences();}
    return publicInfo(context);
  });
  ipcMain.handle('desktop:remote-reconnect',async event=>{
    const context=senderContext(event,false);if(!savedRemote || !safeStorage.isEncryptionAvailable() || context.backend?.remote&&(context.backend.base!==savedRemote.url||context.backend.username!==savedRemote.username))throw new Error('Sign in to the current remote server again. Saved credentials belong to a different server or account.');
    context.backend=await new Backend(coreCommand()).connectRemote({...savedRemote,password:safeStorage.decryptString(Buffer.from(savedRemote.password,'base64'))});
    backends.set('remote:'+context.backend.base+':'+savedRemote.username,Promise.resolve(context.backend));return publicInfo(context);
  });
  ipcMain.handle('desktop:files',async(event,kind='vision')=>{if(!['vision','audio'].includes(kind))throw new Error('Choose images/PDF or audio.');
    const context=senderContext(event);
    const result=await dialog.showOpenDialog(context.win,{properties:['openFile','multiSelections'],filters:[{name:kind==='audio'?'Audio':'Images and PDF',extensions:kind==='audio'?['mp3','wav','m4a','ogg']:['png','jpg','jpeg','webp','pdf']} ]});
    const items=[];
    for(const file of result.filePaths.slice(0,5)){
      const stat=await fs.stat(file);if(stat.size>20*1024*1024)throw new Error('Attachments must be 20 MB or smaller.');
      items.push({name:path.basename(file),data:(await fs.readFile(file)).toString('base64')});
    }
    return items;
  });
  ipcMain.handle('desktop:drop',async(event,paths)=>{
    const context=senderContext(event,false);if(!Array.isArray(paths)||paths.length>5||paths.some(item=>typeof item!=='string'||!path.isAbsolute(item)))throw new Error('Drop up to five files or one folder.');
    const items=await Promise.all(paths.map(async file=>({file,stat:await fs.stat(file)})));const folder=items.find(item=>item.stat.isDirectory());
    if(folder){if(items.length!==1)throw new Error('Drop one project folder at a time.');const choice=await dialog.showMessageBox(context.win,{type:'question',message:'Open this folder as a Pantheon project?',detail:folder.file,buttons:['Cancel','Open project'],defaultId:0,cancelId:0});if(choice.response!==1)return {};await context.win.webContents.executeJavaScript('flushDrafts()');return {info:await attachLocal(context,folder.file)};}
    senderContext(event);const files=[];for(const {file,stat} of items){if(!stat.isFile()||stat.size>20*1024*1024||!/[.](png|jpe?g|webp|pdf|mp3|wav|m4a|ogg)$/i.test(file))throw new Error('Use images, PDFs or audio up to 20 MB.');files.push({name:path.basename(file),data:(await fs.readFile(file)).toString('base64')});}return {files};
  });
  ipcMain.handle('desktop:media-file',async(event,id,save)=>{
    const context=senderContext(event);if(typeof id!=='string'||! /^[a-f0-9]{32}$/.test(id)||typeof save!=='boolean')throw new Error('Invalid media selection');
    const response=await context.backend.response('/api/media/'+id+'/file');if(!response.ok)throw new Error('Media file is unavailable.');const type=response.headers.get('content-type')?.split(';')[0];if(!['image/png','image/jpeg','image/webp','audio/mpeg','audio/wav','audio/mp4','audio/ogg','application/pdf','text/plain'].includes(type))throw new Error('Unsupported media output');
    const chunks=[];let size=0;for await(const chunk of response.body){size+=chunk.length;if(size>30*1024*1024)throw new Error('Media output exceeds 30 MB');chunks.push(chunk);}const buffer=Buffer.concat(chunks);
    if(!save){if(!type.startsWith('image/'))throw new Error('Only images can be previewed inline.');return 'data:'+type+';base64,'+buffer.toString('base64');}
    const ext={'image/png':'png','image/jpeg':'jpg','image/webp':'webp','application/pdf':'pdf','text/plain':'txt'}[type]||'audio';const result=await dialog.showSaveDialog(context.win,{defaultPath:'pantheon-output.'+ext});if(result.canceled)return {saved:false};await fs.writeFile(result.filePath,buffer);return {saved:true};
  });
  ipcMain.handle('desktop:reveal',async(event,relative='')=>{
    const context=senderContext(event);if(context.backend.remote)throw new Error('Remote paths cannot be opened on this computer.');
    if(typeof relative!=='string'||path.isAbsolute(relative))throw new Error('Use a project-relative path.');
    const root=context.backend.workspace,target=await fs.realpath(path.join(root,relative));
    if(target!==root && !target.startsWith(root+path.sep))throw new Error('Path is outside the current project.');
    if(relative)shell.showItemInFolder(target);else {const error=await shell.openPath(root);if(error)throw new Error(error);}
    return {opened:true};
  });
  ipcMain.handle('desktop:window',(event,sessionId='')=>{const context=senderContext(event);if(typeof sessionId!=='string'||!/^[-a-zA-Z0-9_]{0,100}$/.test(sessionId))throw new Error('Invalid session');createWindow(context.backend,sessionId);return {opened:true};});
  ipcMain.handle('desktop:worktree',async(event,target)=>{
    const context=senderContext(event);if(context.backend.remote)throw new Error('Open this worktree on its remote host.');
    const status=await context.backend.request('/api/desktop/git');
    if(typeof target!=='string'||!status.worktrees?.split('\n').some(line=>line==='worktree '+target))throw new Error('Choose a registered worktree.');
    const result=await dialog.showMessageBox(context.win,{type:'question',message:'Open this isolated project?',detail:target,buttons:['Cancel','Open project'],defaultId:1,cancelId:0});
    if(result.response!==1)return {opened:false};
    await context.win.webContents.executeJavaScript('flushDrafts()');return attachLocal(context,target);
  });
  ipcMain.handle('desktop:preferences',async(event,value)=>{
    senderContext(event,false);if(value){
      const allowed=['layout','theme','fontSize','panelWidth','notifications','background','globalShortcut'];
      if(Object.keys(value).some(key=>!allowed.includes(key)))throw new Error('Unsupported preference');
      if(value.layout && !['professional','focus'].includes(value.layout))throw new Error('Invalid layout');
      if(value.theme && !['light','dark'].includes(value.theme))throw new Error('Invalid theme');
      if(value.fontSize!==undefined && (!Number.isInteger(value.fontSize)||value.fontSize<13||value.fontSize>20))throw new Error('Choose a font size from 13 to 20');
      if(value.panelWidth!==undefined && (!Number.isInteger(value.panelWidth)||value.panelWidth<260||value.panelWidth>460))throw new Error('Choose a context width from 260 to 460');
      for(const key of ['notifications','background','globalShortcut'])if(value[key]!==undefined && typeof value[key]!=='boolean')throw new Error('Invalid preference');
      preferences={...preferences,...value};await savePreferences();configureNative();
      for(const context of windows.values())context.win.webContents.send('desktop:command','preferences');
    }return preferences;
  });
  ipcMain.handle('desktop:notify',(event,value)=>{const context=senderContext(event);if(preferences.notifications && Notification.isSupported()){
    const notification=new Notification({title:'Pantheon',body:String(value?.body||'Task updated').slice(0,160)});notification.on('click',()=>{context.win.show();context.win.focus();});notification.show();
  }return {enabled:preferences.notifications};});
  ipcMain.handle('desktop:updates',async event=>{senderContext(event,false);return checkUpdates();});
  ipcMain.handle('desktop:open-link',async(event,value)=>{senderContext(event,false);if(typeof value!=='string'||value.length>3000)throw new Error('Invalid link');const url=new URL(value);if(url.protocol!=='https:'||url.username||url.password)throw new Error('Only HTTPS links without credentials can be opened.');return shell.openExternal(url.href);});
  ipcMain.handle('desktop:copy-text',(event,value)=>{senderContext(event,false);if(typeof value!=='string'||value.length>1000000)throw new Error('Copy up to one million characters of text.');clipboard.writeText(value);return {copied:true};});
  ipcMain.handle('desktop:archive',async(event,id)=>{const context=senderContext(event);if(typeof id!=='string'||!/^[-A-Za-z0-9_]{1,100}$/.test(id))throw new Error('Invalid task');const archive=await context.backend.request('/api/tasks/'+id+'/archive');const selected=await dialog.showSaveDialog(context.win,{defaultPath:'pantheon-task-'+id+'.json',filters:[{name:'Task archive',extensions:['json']}]});if(selected.canceled)return {saved:false};await fs.writeFile(selected.filePath,JSON.stringify(archive,null,2),{mode:0o600});return {saved:true};});
  ipcMain.handle('desktop:release',event=>{senderContext(event,false);return shell.openExternal('https://github.com/RyosukeSAMA/github-ai/releases');});
  ipcMain.handle('desktop:terminal-stop',event=>{senderContext(event).terminal?.abort();return {stopped:true};});
  ipcMain.handle('desktop:terminal',async(event,value)=>{
    const context=senderContext(event);if(context.terminal)throw new Error('Stop the current command first.');
    if(typeof value?.command!=='string'||value.command.length>4000)throw new Error('Enter a command up to 4000 characters.');
    const consent=await dialog.showMessageBox(context.win,{type:'question',message:context.backend.remote?'Run this command on the remote host?':'Run this command in your project?',detail:context.backend.workspace+'\n\n'+value.command,buttons:['Cancel','Run once'],cancelId:0,defaultId:0});if(consent.response!==1)return {started:false};
    const controller=new AbortController();context.terminal=controller;
    (async()=>{try{
      const response=await context.backend.response('/api/workspace/terminal/stream',{method:'POST',body:{command:value.command,cwd:value.cwd||'',timeout_seconds:120}},controller.signal,true);
      if(!response.ok)throw new Error('Terminal request failed ('+response.status+')');
      for await(const chunk of response.body){if(!context.win.isDestroyed())context.win.webContents.send('desktop:terminal-data',{text:Buffer.from(chunk).toString('utf8')});}
    }catch(error){if(!context.win.isDestroyed())context.win.webContents.send('desktop:terminal-data',{error:error.name==='AbortError'?'Command stopped.':error.message});}
    finally{context.terminal=null;if(!context.win.isDestroyed())context.win.webContents.send('desktop:terminal-data',{done:true});}})();
    return {started:true};
  });
}
app.on('before-quit',event=>{
  if(quitting)return;event.preventDefault();if(app.quitPending)return;app.quitPending=true;
  (async()=>{
    const drafts=await Promise.allSettled([...windows.values()].map(context=>context.win.webContents.executeJavaScript('typeof flushDrafts === \"function\" ? flushDrafts() : undefined')));
    if(drafts.some(item=>item.status==='rejected')){const choice=await dialog.showMessageBox({type:'warning',message:'Some drafts could not be saved.',detail:'Keep the app open to resolve the conflict, or quit while keeping the local recovery draft.',buttons:['Keep open','Quit'],cancelId:0,defaultId:0});if(choice.response!==1){app.quitPending=false;return;}}
    const values=await Promise.allSettled([...backends.values()]);const local=values.filter(item=>item.status==='fulfilled').map(item=>item.value).filter(item=>item.owned);
    let active=0;for(const backend of local){try{active+=(await backend.request('/api/desktop/sessions')).runs.filter(run=>['queued','running','stopping'].includes(run.status)).length;}catch{}}
    if(active){const answer=await dialog.showMessageBox({type:'question',message:'Quit with '+active+' active task(s)?',detail:'Owned local services will stop. Saved results remain, but unfinished work may need recovery. Reused and remote services will keep running.',buttons:['Keep running','Quit'],cancelId:0,defaultId:0});if(answer.response!==1){app.quitPending=false;return;}}
    quitting=true;globalShortcut.unregisterAll();for(const context of windows.values())context.terminal?.abort();await Promise.allSettled(local.map(backend=>backend.stop()));tray?.destroy();for(const context of windows.values())context.win.destroy();app.exit(0);
  })().catch(error=>{console.error('Desktop cleanup failed:',error.message);quitting=false;app.quitPending=false;});
});
app.whenReady().then(async()=>{
  if(!app.requestSingleInstanceLock()){app.exit();return;}
  app.on('second-instance',()=>{const context=[...windows.values()][0];context?.win.show();context?.win.focus();});
  try{const saved=JSON.parse(await fs.readFile(preferenceFile(),'utf8'));preferences={...preferences,...saved.preferences};recent=(saved.recent||[]).filter(item=>typeof item==='string');savedRemote=saved.savedRemote||null;}catch{}
  protocol.handle('pantheon',async request=>{
    const url=new URL(request.url);if(url.hostname!=='app')return new Response('Not found',{status:404});
    const relative=decodeURIComponent(url.pathname).replace(/^\//,'')||'index.html';
    if(!/^[a-zA-Z0-9_.-]+$/.test(relative))return new Response('Not found',{status:404});
    const response=await net.fetch(pathToFileURL(path.join(uiRoot,relative)).toString());
    const headers=new Headers(response.headers);headers.set('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'none'; frame-src blob:; object-src 'none'; base-uri 'none'; form-action 'none'");
    return new Response(response.body,{status:response.status,headers});
  });
  installIPC();configureNative();setInterval(monitorTasks,3000).unref();setTimeout(()=>checkUpdates().catch(()=>{}),6000).unref();setInterval(()=>checkUpdates().catch(()=>{}),6*60*60*1000).unref();
  Menu.setApplicationMenu(Menu.buildFromTemplate([
    ...(process.platform==='darwin'?[{role:'appMenu'}]:[]),
    {label:'File',submenu:[{label:'New task',accelerator:'CommandOrControl+N',click:()=>sendCommand('new')},{label:'Open project…',accelerator:'CommandOrControl+O',click:()=>sendCommand('workspace')},{label:'New window',accelerator:'CommandOrControl+Shift+N',click:()=>createWindow([...windows.values()][0]?.backend||null)}, {type:'separator'},{role:'quit'}]},
    {role:'editMenu'}, {label:'View',submenu:[{label:'Command palette',accelerator:'CommandOrControl+K',click:()=>sendCommand('palette')},{role:'reload'},{role:'togglefullscreen'},...(!app.isPackaged?[{role:'toggleDevTools'}]:[])]},
    {role:'windowMenu'}, {label:'Help',submenu:[{label:'Check for updates',click:()=>sendCommand('updates')}]}]));
  const context=createWindow();
  const initial=process.env.PANTHEON_DESKTOP_WORKSPACE || recent[0];
  if(initial){try{await attachLocal(context,initial);context.win.webContents.send('desktop:command','workspace-ready');}catch(error){context.startupError=error.message;}}
});
app.on('activate',()=>{if(!windows.size)createWindow();else [...windows.values()][0].win.show();});
