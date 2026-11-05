'use strict';
function syncControls(){
  const offline=!!state.offline,busy=!!state.syncBusy||!!state.creatingTask;
  for(const key of ['#attach','#models-open','#connections-open','#file-history','#prepare-file','#terminal-toggle'])if($(key))$(key).disabled=offline||busy;
  $('#file-editor').disabled=offline||busy||!state.file;$('#prompt').disabled=busy||state.maintenance||state.projectOpening;
  $('#new-task').disabled=busy||state.maintenance||state.projectOpening;updateComposerState();
}
function applySyncStatus(value){
  state.sync=value||null;state.offline=!!value?.enabled&&!!value.offline;state.syncBusy=!!value?.busy;
  const pending=value?.pending||0,conflicts=value?.conflicts?.length||0;$('#sync-notice').hidden=!state.offline&&!pending&&!state.syncBusy;
  $('#sync-notice-text').textContent=state.syncBusy?'Syncing reviewed drafts…':state.offline?'Offline · draft edits stay on this computer. Reconnect and review sync before running.':conflicts?conflicts+' draft conflict(s) need review.':pending+' draft(s) saved locally, waiting for explicit sync.';
  if(pending&&$('#draft-state').textContent==='Saved')$('#draft-state').textContent='Saved locally';syncControls();syncToolbar();
}
async function renderSyncPanel(){
  const value=await native.syncStatus();applySyncStatus(value);
  $('#sync-summary').textContent=value.cache_error|| (value.enabled?(value.offline?'Offline cache':'Remote workspace')+' · '+value.pending+' pending draft(s) · '+value.conflicts.length+' conflict(s)'+(value.last_saved?' · Cached '+new Date(value.last_saved).toLocaleString():''):(value.remote?'Offline storage is off for this remote workspace.':'Local projects already save on this computer. Connect a remote host for device sync.'));
  $('#sync-export').hidden=!value.enabled;$('#sync-export').disabled=!value.pending&&!value.recovered?.length;
  $('#sync-enable').hidden=!value.remote||value.enabled;$('#sync-disable').hidden=!value.enabled;$('#sync-run').hidden=!value.enabled;$('#sync-run').disabled=value.busy;
  $('#sync-signin').textContent=value.remote?'Sign in to remote host':'Connect remote host';
  const conflicts=$('#sync-conflicts');conflicts.replaceChildren();for(const conflict of value.conflicts){
    const card=element('section','data-card sync-conflict');card.dataset.session=conflict.id;card.append(element('h3','',conflict.title||'Draft conflict'),element('p','','Compare both drafts. Choosing your draft queues a reviewed update; Sync drafts applies it separately. Choosing the remote draft keeps a recovered copy of your local text.'));
    for(const [label,text] of [['This computer',conflict.local_draft],['Remote host',conflict.remote_missing?'Task is missing on the host.':conflict.remote_draft]]){const copy=element('label','',label),area=element('textarea');area.readOnly=true;area.value=text;area.rows=4;copy.append(area);card.append(copy);}
    for(const [choice,label] of [['local','Keep my draft for reviewed sync'],['remote','Use remote draft']]){const button=element('button','',label);action(button,async()=>{await native.resolveSync({id:conflict.id,choice});$('#sync-feedback').textContent=choice==='local'?'Your draft is queued. Choose Sync drafts to apply it.':'Remote draft selected. Your previous local text is in Recovered draft copies.';await renderSyncPanel();});card.append(button);}conflicts.append(card);
  }
  $('#sync-recovered').replaceChildren();for(const item of value.recovered||[]){const card=element('div','data-card');card.append(element('strong','',item.title),element('p','',new Date(item.created).toLocaleString()));const copy=element('button','','Copy recovered draft');action(copy,()=>native.copyText(item.draft));card.append(copy);$('#sync-recovered').append(card);}
  $('#sync-workspaces').replaceChildren();for(const workspace of value.workspaces||[]){const card=element('div','data-card');card.append(element('strong','',workspace.workspace_name),element('p','',workspace.origin+' · '+workspace.pending+' pending'));const open=element('button','','Open cached workspace');action(open,async()=>{const info=await native.openOffline(workspace.id);closeDialog('#system-dialog');await adoptWorkspace(info);});card.append(open);$('#sync-workspaces').append(card);}if(!value.workspaces?.length)$('#sync-workspaces').append(element('p','','No opted-in remote workspaces cached on this computer.'));
}
function bindSync(){
  action($('#system-tab-sync'),async()=>{systemTab('sync');await renderSyncPanel();});
  action($('#sync-notice-open'),()=>openSystemDialog('sync'));
  action($('#sync-enable'),async()=>{await flushDrafts();const value=await native.enableOffline();if(!value.cancelled){applySyncStatus(value);await refresh();}await renderSyncPanel();});
  action($('#sync-disable'),async()=>{const value=await native.disableOffline();if(!value.cancelled)applySyncStatus(value);await renderSyncPanel();});
  action($('#sync-run'),async()=>{const feedback=$('#sync-feedback');feedback.textContent='Checking the host and syncing reviewed drafts…';try{const value=await native.syncDrafts();feedback.textContent=value.conflicts.length?'Other-device changes need review below.':value.applied+' draft(s) synced. No tasks or messages were sent.';await renderSyncPanel();}catch(error){feedback.textContent=errorText(error);await renderSyncPanel();}});
  action($('#sync-export'),async()=>{const result=await native.exportOfflineDrafts();$('#sync-feedback').textContent=result.saved?'Private draft text exported locally. Inspect it before sharing.':'Draft export cancelled.';});
  action($('#sync-signin'),()=>{closeDialog('#system-dialog');$('#remote-url').value=state.sync?.origin||'';$('#remote-user').value=state.sync?.username||'';showDialog('#remote-dialog');});
  native.onSync?.(value=>{applySyncStatus(value);if($('#system-dialog').open&&!$('#system-sync').hidden)renderSyncPanel().catch(error=>{$('#sync-feedback').textContent=errorText(error);});});
}
