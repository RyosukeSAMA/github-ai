'use strict';
const desktopSystem={update:null,ticket:null,maintenanceControls:new Map()};
function systemTab(name){for(const key of ['updates','backups','sync']){$('#system-tab-'+key).setAttribute('aria-selected',String(key===name));$('#system-'+key).hidden=key!==name;}}
function formatSize(size){return size>=1024*1024?(size/1024/1024).toFixed(1)+' MB':Math.ceil(size/1024)+' KB';}
async function openSystemDialog(tab='updates'){
  await renderSyncPanel();
  systemTab(tab);$('#system-version').textContent=state.info.version;$('#update-channel').value=state.info.preferences.updateChannel||'stable';
  $('#system-project').textContent=state.info.workspace?.workspace_name||'No project selected';
  $('#system-project-status').textContent=state.info.workspace?(state.info.remote?'Remote project':state.info.owned?'Local project':'Connected local service'):'Choose a project to create a workspace backup.';
  $('#system-reconnect').hidden=!state.info.workspace;showDialog('#system-dialog');
  renderUpdateStatus(await native.updateStatus());await loadWorkspaceBackups();
}
function renderUpdateStatus(value){
  desktopSystem.update=value;
  const phase=value.phase||'idle',busy=['checking','downloading'].includes(phase),card=$('#update-title').parentElement;
  card.dataset.state=phase;$('#update-channel').value=value.channel||state.info.preferences.updateChannel||'stable';$('#update-channel').disabled=busy;
  const titles={idle:'Check for updates',checking:'Checking official releases…',available:'A new version is available',current:'You’re up to date',downloading:'Downloading verified installer…',downloaded:'Installer verified and ready',cancelled:'Download cancelled',failed:'Update needs attention'};
  $('#update-title').textContent=titles[phase]||'Updates';
  $('#update-message').textContent=phase==='available'?'Pantheon '+value.latest+' is available for this computer.':phase==='downloading'?value.asset_name:phase==='downloaded'?value.record.name:phase==='failed'?value.error:phase==='cancelled'?'You can restart the download when you are ready.':value.reason||'Choose a channel, then check the official releases.';
  $('#update-progress').hidden=phase!=='downloading';$('#update-progress').value=value.total?Math.min(100,100*value.downloaded/value.total):0;
  $('#update-bytes').textContent=phase==='downloading'?formatSize(value.downloaded||0)+' / '+formatSize(value.total||0):'';
  $('#update-check').disabled=busy;$('#update-download').hidden=!value.available||phase==='downloaded';$('#update-download').disabled=busy;$('#update-cancel').hidden=phase!=='downloading';$('#update-open').hidden=phase!=='downloaded';
  const assets=value.assets||[],signature=JSON.stringify(assets.map(item=>[item.id,item.name]));
  if($('#update-assets').dataset.signature!==signature){$('#update-assets').replaceChildren();for(const asset of assets){const option=element('option','',asset.name);option.value=asset.id;$('#update-assets').append(option);}$('#update-assets').dataset.signature=signature;}
  $('#update-assets-label').hidden=!value.available||!assets.length||phase==='downloaded';$('#update-assets').disabled=busy;
  const notesSignature=value.latest+'\n'+value.notes;if($('#update-notes').dataset.signature!==notesSignature){$('#update-notes').replaceChildren(markdown(value.notes||''));$('#update-notes').dataset.signature=notesSignature;}$('#update-notes-section').hidden=!value.notes;
  if(value.history)renderDownloadedInstallers(value.history);
  if(value.recovery)renderRecoveryVersions(value.recovery);
}
async function refreshUpdateHistory(){const value=await native.updateStatus();if($('#system-dialog').open)renderUpdateStatus(value);}
function renderDownloadedInstallers(items){
  const target=$('#update-history');target.replaceChildren();if(!items.length){target.append(element('p','','No verified installers downloaded yet.'));return;}
  for(const item of items){const row=element('div','system-recovery-row'),copy=element('div');copy.append(element('strong','',item.name),element('small','',formatSize(item.size)+' · '+new Date(item.downloaded_at).toLocaleString()));
    const open=element('button','','Prepare installer'),reveal=element('button','','Show file');action(open,()=>prepareInstaller(item.id));action(reveal,()=>native.revealUpdateInstaller(item.id));row.append(copy,open,reveal);target.append(row);}
}
function renderRecoveryVersions(items){
  const target=$('#update-recovery');target.replaceChildren();
  for(const release of items){const row=element('div','system-recovery-row'),copy=element('div');copy.append(element('strong','',release.latest),element('small','','Earlier compatible app version'));const download=element('button','','Download earlier version');download.disabled=desktopSystem.update?.phase==='downloading';
    action(download,async()=>{const asset=release.assets[0];await native.downloadUpdate({id:asset.id,rollback:true});await refreshUpdateHistory();});row.append(copy,download);target.append(row);}
}
async function prepareInstaller(id){
  $('#update-title').textContent='Preparing your recovery copy…';$('#update-message').textContent='Review the confirmation. Idle local workspaces will be backed up before opening the installer.';$('#update-open').disabled=true;
  try{const result=await native.openUpdateInstaller(id);if(!result.opened){await refreshUpdateHistory();return;}
    $('#update-title').textContent='Verified installer opened';$('#update-message').textContent=(result.backups?result.backups+' workspace backup(s) created. ':'No local workspace needed a backup. ')+result.manual_steps;
    await loadWorkspaceBackups();toast('Verified installer opened. Your recovery backups are ready.');
  }catch(error){$('#update-title').textContent='Installer preparation needs attention';$('#update-message').textContent=errorText(error);throw error;}finally{$('#update-open').disabled=false;}
}
async function backupOperation(label,request){$('#backup-message').textContent=label;$('#backup-message').dataset.state='pending';try{const result=await request();$('#backup-message').dataset.state='complete';return result;}catch(error){$('#backup-message').dataset.state='failed';$('#backup-message').textContent=errorText(error);throw error;}}
async function loadWorkspaceBackups(){
  const target=$('#backup-list');target.replaceChildren();
  if(!state.info.workspace){$('#backup-create').disabled=true;$('#backup-inspect').disabled=true;$('#backup-help').textContent='Choose a project before backing up its data.';return;}
  const value=await native.backups();$('#backup-create').disabled=!value.owned||!!state.maintenance;$('#backup-inspect').disabled=!value.owned||!!state.maintenance;
  $('#backup-help').textContent=value.owned?'Backup and restore briefly pause this idle workspace. Active tasks must finish first.':'Manage backup and restore on the remote or reused service’s host. Desktop will not stop a service it does not own.';
  for(const item of value.items){const row=element('div','system-backup-row'),copy=element('div');copy.append(element('strong','',item.name),element('small','',new Date(item.created_at).toLocaleString()+' · '+formatSize(item.size)+' · '+(item.includes_secrets?'Includes credentials':'Data only')));const reveal=element('button','','Show file');action(reveal,()=>native.revealBackup(item.id));row.append(copy,reveal);target.append(row);}
  if(!value.items.length)target.append(element('p','','No workspace backups created in Desktop yet.'));
}
async function discardRestore(){if(desktopSystem.ticket)await native.discardRestore(desktopSystem.ticket.ticket);desktopSystem.ticket=null;$('#backup-review').hidden=true;}
function maintenanceStatus(value){
  if(value.workspace!==state.info?.workspace?.workspace)return;
  const busy=['preparing','working'].includes(value.phase);state.maintenance=busy;
  const controls=['#prompt','#run','#attach','#new-task','#new-window','#project-open','#mode-trigger'];
  if(busy){for(const key of controls){const control=$(key);if(control&&!desktopSystem.maintenanceControls.has(control)){desktopSystem.maintenanceControls.set(control,control.disabled);control.disabled=true;}}notice(value.phase==='preparing'?'Preparing the workspace and saving drafts…':value.operation==='restore'?'Restoring workspace data…':'Creating a workspace recovery copy…');}
  else{for(const [control,disabled] of desktopSystem.maintenanceControls)control.disabled=disabled;desktopSystem.maintenanceControls.clear();updateComposerState();notice(value.phase==='failed'?value.error:'');if($('#system-dialog').open)loadWorkspaceBackups().catch(error=>toast(errorText(error)));}
}
function bindSystem(){
  $('.system-tabs').addEventListener('keydown',event=>{if(!['ArrowLeft','ArrowRight'].includes(event.key))return;event.preventDefault();const names=['updates','backups','sync'],current=names.indexOf(event.target.id.replace('system-tab-','')),name=names[(current+(event.key==='ArrowRight'?1:2))%3];systemTab(name);$('#system-tab-'+name).focus();});
  action($('#system-tab-updates'),()=>systemTab('updates'));action($('#system-tab-backups'),()=>systemTab('backups'));
  action($('#system-reconnect'),async()=>{await reconnectService();await openSystemDialog();});
  action($('#system-remote'),()=>{closeDialog('#system-dialog');showDialog('#remote-dialog');});action($('#system-quit'),()=>native.quit());
  action($('#update-check'),async()=>{renderUpdateStatus(await native.updates());await refreshUpdateHistory();});
  $('#update-channel').onchange=()=>{native.setUpdateChannel($('#update-channel').value).then(async value=>{state.info=await native.info();renderUpdateStatus(value);await refreshUpdateHistory();}).catch(error=>toast(errorText(error)));};
  action($('#update-download'),async()=>{await native.downloadUpdate({id:Number($('#update-assets').value),rollback:false});await refreshUpdateHistory();});action($('#update-cancel'),()=>native.cancelUpdate());
  action($('#update-open'),()=>prepareInstaller(desktopSystem.update.record.id));action($('#update-releases'),()=>native.openRelease());
  action($('#backup-create'),async()=>{const result=await backupOperation('Creating a workspace backup…',()=>native.backupWorkspace({includeSecrets:$('#backup-secrets').checked}));if(result.cancelled){$('#backup-message').textContent='Backup cancelled. Existing backups are kept.';return;}await loadWorkspaceBackups();$('#backup-message').textContent='Backup created. '+(result.path||'');});
  action($('#backup-inspect'),async()=>{await discardRestore();const result=await backupOperation('Reading the selected backup…',()=>native.inspectBackup());if(result.cancelled){$('#backup-message').textContent='No backup selected.';return;}desktopSystem.ticket=result;$('#backup-review-description').textContent=result.name+' · '+result.files+' files · '+formatSize(result.uncompressed_bytes)+(result.includes_secrets?' · Contains API credentials and configuration.':' · Workspace data only.');$('#backup-review').hidden=false;$('#backup-message').textContent='Review the archive before restoring.';});
  action($('#backup-discard'),discardRestore);action($('#backup-restore'),async()=>{const result=await backupOperation('Restoring workspace data…',()=>native.restoreWorkspace(desktopSystem.ticket.ticket));if(result.cancelled){$('#backup-message').textContent='Restore cancelled. Current workspace data is kept.';return;}desktopSystem.ticket=null;$('#backup-review').hidden=true;await loadWorkspaceBackups();$('#backup-message').textContent='Workspace restored. Automations, pending tasks, messages and approvals remain stopped. A recovery copy is kept locally.';});
  $('#system-dialog').addEventListener('close',()=>discardRestore().catch(()=>{}));
  native.onMaintenance?.(maintenanceStatus);
  native.onUpdate?.(value=>{if($('#system-dialog').open)renderUpdateStatus(value);if(value.phase==='downloaded')refreshUpdateHistory().catch(error=>toast(errorText(error)));});
}
