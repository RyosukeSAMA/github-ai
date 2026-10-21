'use strict';
const $ = selector => document.querySelector(selector);
const native = window.pantheonDesktop;
const state = {info:null, sessions:[], runs:[], artifacts:[], coreTasks:[], setup:null, selected:'', detail:null,
  view:'work', tab:'conversation', eventCache:new Map(), cursors:new Map(), output:new Map(), attachments:new Map(),
  activeReview:null, file:null, fileDirectory:'', patchQueue:Promise.resolve(), draftTimer:null, editorTimer:null,
  epoch:0, selectionGeneration:0, edits:new Map(), dirty:new Set(), mutation:0, polling:false, cap:'skills', approvals:new Map(), seenFinal:new Set(), messageLimit:80, saving:false};
const activeStatuses = new Set(['queued','running','stopping']);
const roleNames = ['hermes','hephaestus','athena','apollo'];
const currentSession = () => state.sessions.find(item => item.id === state.selected);
const latestRun = id => state.runs.filter(run => run.session_id === (id || state.selected)).sort((a,b)=>b.created-a.created)[0];
const activeRun = id => state.runs.find(run => run.session_id === (id || state.selected) && activeStatuses.has(run.status));
function element(tag, className, text) {const value=document.createElement(tag);if(className)value.className=className;if(text!==undefined)value.textContent=text;return value;}
function empty(target, text) {target.replaceChildren(element('p','empty-state',text));}
function toast(text) {$('#toast').textContent=text;$('#toast').hidden=false;clearTimeout(toast.timer);toast.timer=setTimeout(()=>{$('#toast').hidden=true;},4200);}
function notice(text='') {$('#global-notice').textContent=text;$('#global-notice').hidden=!text;}
function errorText(error) {return String(error?.message || error || 'Operation failed');}
function showDialog(id) {const dialog=$(id);if(!dialog.open)dialog.showModal();}
function closeDialog(id) {$(id).close();}
function info(title, content) {$('#info-title').textContent=title;$('#info-content').replaceChildren(typeof content==='string'?element('p','',content):content);showDialog('#info-dialog');}
async function api(path, body, method) {if(!native)throw new Error('Open this interface in the Pantheon desktop app.');return native.api(path,{method:method || (body===undefined?'GET':'POST'),...(body===undefined?{}:{body})});}
function action(button, callback) {button.onclick=async event=>{try{await callback(event);}catch(error){toast(errorText(error));}};}
function showInspector(show) {$('.app').classList.toggle('no-inspector',!show);$('.app').classList.toggle('show-inspector',show);$('#inspector-toggle').setAttribute('aria-pressed',String(show));setIconButton($('#inspector-toggle'),'context',show?'Hide context':'Show context');}
function showTerminal(show) {$('#terminal-drawer').hidden=!show;$('#terminal-toggle').setAttribute('aria-expanded',String(show));setIconButton($('#terminal-toggle'),'terminal',show?'Close terminal':'Open terminal');}
function applyPreferences(preferences) {
  $('.app').dataset.theme=preferences.theme;$('.app').dataset.layout=preferences.layout || 'professional';
  $('.app').style.setProperty('--reader-size',preferences.fontSize+'px');$('.app').style.setProperty('--context-width',preferences.panelWidth+'px');
  setIconButton($('#theme-toggle'),preferences.theme==='dark'?'sun':'moon',preferences.theme==='dark'?'Switch to light theme':'Switch to dark theme');
  setIconButton($('#layout-toggle'),preferences.layout==='focus'?'focus':'layout',preferences.layout==='focus'?'Switch to Pro workspace':'Switch to Focus layout');
  showInspector(innerWidth>1150 && preferences.layout!=='focus');
}
function inlineMarkdown(text){
  const fragment=document.createDocumentFragment(),pattern=/(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\(https:\/\/[^\s)]+\))/g;let last=0;
  for(const match of String(text).matchAll(pattern)){fragment.append(document.createTextNode(text.slice(last,match.index)));const token=match[0];if(token.startsWith('**'))fragment.append(element('strong','',token.slice(2,-2)));else if(token.startsWith('`'))fragment.append(element('code','',token.slice(1,-1)));else{const link=/^\[([^\]]+)\]\((.+)\)$/.exec(token),button=element('button','source-link',link[1]);button.title=link[2];action(button,()=>native.openLink(link[2]));fragment.append(button);}last=match.index+token.length;}fragment.append(document.createTextNode(text.slice(last)));return fragment;
}
function markdown(text){
  const container=element('div','markdown'),lines=String(text||'').split('\n');let code=null,paragraph=[];
  const appendText=(tag,text)=>{const node=element(tag);node.append(inlineMarkdown(text));container.append(node);};
  const flush=()=>{if(paragraph.length){appendText('p',paragraph.join('\n'));paragraph=[];}};
  for(let i=0;i<lines.length;i++){const line=lines[i];
    if(line.startsWith('```')){flush();if(code){container.append(element('pre','',code.join('\n')));code=null;}else code=[];continue;}if(code){code.push(line);continue;}
    if(line.includes('|')&&/^\s*\|?\s*:?-{3,}:?\s*\|/.test(lines[i+1]||'')){flush();const table=element('table'),head=element('thead'),row=element('tr'),cells=value=>value.trim().replace(/^\||\|$/g,'').split('|').map(x=>x.trim());for(const cell of cells(line)){const value=element('th');value.append(inlineMarkdown(cell));row.append(value);}head.append(row);table.append(head);i++;const body=element('tbody');while(i+1<lines.length&&lines[i+1].includes('|')&&lines[i+1].trim()){const row=element('tr');for(const cell of cells(lines[++i])){const value=element('td');value.append(inlineMarkdown(cell));row.append(value);}body.append(row);}table.append(body);const wrapper=element('div','table-scroll');wrapper.append(table);container.append(wrapper);continue;}
    const heading=/^(#{1,3})\s+(.+)$/.exec(line);if(heading){flush();appendText('h'+heading[1].length,heading[2]);}else if(/^\s*[-*]\s+/.test(line)){flush();appendText('p','• '+line.replace(/^\s*[-*]\s+/,''));}else if(!line.trim())flush();else paragraph.push(line);
  }flush();if(code)container.append(element('pre','',code.join('\n')));return container;
}
async function askText(title,label,value='') {
  $('#text-title').textContent=title;$('#text-label').textContent=label;$('#text-input').value=value;showDialog('#text-dialog');$('#text-input').focus();
  return new Promise(resolve=>{const dialog=$('#text-dialog');let result=null;$('#text-form').onsubmit=event=>{event.preventDefault();result=$('#text-input').value;dialog.close();};dialog.addEventListener('close',()=>resolve(result),{once:true});});
}
async function confirmChoice(title,text,button='Continue') {
  const content=element('div');content.append(element('p','',text));const controls=element('div','form-actions');
  const accept=element('button','primary',button),cancel=element('button','','Cancel');controls.append(cancel,accept);content.append(controls);info(title,content);
  return new Promise(resolve=>{let accepted=false;accept.onclick=()=>{accepted=true;closeDialog('#info-dialog');};cancel.onclick=()=>closeDialog('#info-dialog');$('#info-dialog').addEventListener('close',()=>resolve(accepted),{once:true});});
}
async function refreshSetup(){state.setup=await api('/api/setup/status');renderRoles();}
function workspaceUI() {
  const connected=!!state.info?.workspace;document.body.dataset.platform=state.info?.platform||'';
  $('#host-label').textContent=connected?(state.info.remote?'Remote · ':'Local · ')+state.info.workspace.workspace_name:'Choose a workspace';
  $('#project-name').textContent=connected?state.info.workspace.workspace_name:'Choose project…';
  $('#context-project').textContent=connected?state.info.workspace.workspace_name:'No project selected';
  $('#context-host').textContent=connected?(state.info.remote?'Remote host · ':'Local project · ')+state.info.workspace.workspace:'Choose a project to begin.';
  $('#connection-state').textContent=connected?(state.info.remote?'Remote connected':'Local connected'):'Not connected';
  $('#service-status').textContent=connected?(state.info.owned?'Desktop-owned local service':state.info.remote?'Remote service':'Reused local service'):'Choose a workspace';
  $('#terminal-host').textContent=state.info?.remote?'Remote project terminal':'Local project terminal';
  $('#startup-error').textContent=state.info?.startupError||'';
  if(!connected){showWelcome();}else $('.app').classList.remove('welcome-state');
}
function showWelcome() {
  $('.app').classList.add('welcome-state');$('#welcome').hidden=false;
  ['#task-heading','#council-route','#content-tabs','#composer'].forEach(key=>{$(key).hidden=true;});
  document.querySelectorAll('.pane,.global-pane').forEach(pane=>{pane.hidden=true;});
  $('#breadcrumb').textContent='Get started';
}
async function connectWorkspace() {
  await flushDrafts();const value=await native.chooseWorkspace();if(!value.workspace)return;
  state.info=value;resetWorkspace();workspaceUI();await refresh();
}
function resetWorkspace() {
  state.epoch++;state.selectionGeneration++;state.dirty.clear();
  state.selected='';state.detail=null;state.sessions=[];state.runs=[];state.artifacts=[];state.file=null;
  state.eventCache.clear();state.cursors.clear();state.output.clear();state.attachments.clear();state.approvals.clear();
  $('#file-editor').value='';$('#file-editor').disabled=true;notice('');
}
async function selectSession(id, initial=false) {
  if(!initial)await flushDrafts();
  const generation=++state.selectionGeneration,epoch=state.epoch;
  const detail=await api('/api/desktop/sessions/'+id);if(generation!==state.selectionGeneration||epoch!==state.epoch)return;state.selected=id;state.detail=detail;state.messageLimit=80;try{localStorage.setItem('pantheon-selected:'+state.info.workspace.workspace,id);}catch{}
  const localKey='pantheon-draft:'+state.info.workspace.workspace+':'+id;
  try{const saved=JSON.parse(localStorage.getItem(localKey)||'null');if(saved && saved.updated>detail.updatedAt && saved.value!==detail.draft){detail.draft=saved.value;notice('A local draft was recovered. It has not been sent.');}}catch{}
  $('#prompt').value=detail.draft||'';$('#mode').value=detail.mode||'auto';
  if(detail.editor_draft?.path){state.file={path:detail.editor_draft.path,hash:detail.editor_draft.hash};$('#file-editor').value=detail.editor_draft.content;$('#file-editor').disabled=false;$('#editor-label').textContent=state.file.path;}
  else{state.file=null;$('#file-editor').value='';$('#file-editor').disabled=true;$('#editor-label').textContent='Select a UTF-8 text file';}
  state.attachments.set(id,detail.attachments||[]);renderAttachments();renderSidebar();setView('work');renderTask();await pollEvents();await refreshUsage();
}
async function refresh() {
  if(!state.info?.workspace)return;
  const epoch=state.epoch,mutation=state.mutation;
  const data=await api('/api/desktop/sessions');if(epoch!==state.epoch||mutation!==state.mutation||state.saving)return;
  const old=new Map(state.sessions.map(item=>[item.id,item]));state.sessions=data.sessions.map(item=>state.dirty.has(item.id)&&old.has(item.id)?{...item,desktop_version:old.get(item.id).desktop_version}:item);state.runs=data.runs;
  if(!state.setup)await refreshSetup();
  if(!state.selected && state.sessions.length){let last=state.info.initialSession;try{last=last||localStorage.getItem('pantheon-selected:'+state.info.workspace.workspace);}catch{}if(!state.sessions.some(item=>item.id===last))last=state.sessions.filter(item=>!item.archived).sort((a,b)=>b.updatedAt-a.updatedAt)[0]?.id||state.sessions[0].id;await selectSession(last,true);}
  else if(state.selected){
    const item=currentSession();if(item && !state.saving && !state.dirty.has(state.selected)){
      const detail=await api('/api/desktop/sessions/'+state.selected);
      if(state.detail?.desktop_version!==detail.desktop_version){const localDraft=$('#prompt').value;state.detail=detail;if(document.activeElement!==$('#prompt'))$('#prompt').value=detail.draft||'';else state.detail.draft=localDraft;}
    }
    renderTask();
  }
  renderSidebar();if(state.view==='tasks')renderMissions().catch(error=>toast(errorText(error)));
  if(!state.selected)showWelcome();
}
async function newTask() {
  if(!state.info?.workspace){await connectWorkspace();if(!state.info?.workspace)return;}
  await flushDrafts();const item=await api('/api/desktop/sessions',{title:'New task'});state.sessions.unshift(item);await selectSession(item.id,true);$('#prompt').focus();
}
async function patchSession(changes,id=state.selected) {
  if(!id)return;
  const generation=state.edits.get(id)||0;
  const pending=async()=>{
    state.mutation++;state.saving=true;$('#draft-state').textContent='Saving…';
    const item=state.sessions.find(item=>item.id===id);
    try{
      let saved;const base=state.selected===id?state.detail:item;
      try{saved=await api('/api/desktop/sessions/'+id,{expected_version:item?.desktop_version||0,...changes},'PATCH');}
      catch(error){if(!/another window|changed/i.test(errorText(error)))throw error;const latest=await api('/api/desktop/sessions/'+id);if(!Object.keys(changes).every(key=>JSON.stringify(latest[key])===JSON.stringify(base?.[key])))throw error;saved=await api('/api/desktop/sessions/'+id,{expected_version:latest.desktop_version||0,...changes},'PATCH');if(state.selected===id)state.detail=latest;}
      const index=state.sessions.findIndex(item=>item.id===id);if(index>=0)state.sessions[index]=saved;
      if(state.selected===id)state.detail={...state.detail,...saved,...changes};
      state.mutation++;const settled=(state.edits.get(id)||0)===generation;if(settled)state.dirty.delete(id);$('#draft-state').textContent=settled?'Saved':'Unsaved';
      if(settled && 'draft' in changes)try{localStorage.removeItem('pantheon-draft:'+state.info.workspace.workspace+':'+id);}catch{}
      renderSidebar();return saved;
    }catch(error){$('#draft-state').textContent='Not saved';notice(errorText(error)+' Your current local draft is still visible.');if(/another window|changed/i.test(errorText(error))){const reload=element('button','','Resolve draft conflict');action(reload,()=>resolveDraftConflict(id));$('#global-notice').append(document.createTextNode(' '),reload);}throw error;}
    finally{state.saving=false;}
  };
  const result=state.patchQueue.then(pending);state.patchQueue=result.catch(()=>{});return result;
}
async function flushDrafts(){clearTimeout(state.draftTimer);clearTimeout(state.editorTimer);if(state.selected && state.detail){const changes={};if($('#prompt').value!==(state.detail.draft||''))changes.draft=$('#prompt').value;if(state.file && $('#file-editor').value!==(state.detail.editor_draft?.content||''))changes.editor_draft={...state.file,content:$('#file-editor').value};if(Object.keys(changes).length)await patchSession(changes);}await state.patchQueue;}
function renderSidebar() {
  const visible=state.sessions.filter(item=>!item.archived).sort((a,b)=>Number(!!b.pinned)-Number(!!a.pinned)||b.updatedAt-a.updatedAt).slice(0,80),target=$('#task-list');
  $('#running-count').textContent=state.runs.filter(run=>activeStatuses.has(run.status)).length;
  const signature=JSON.stringify([state.selected,visible.map(item=>[item.id,item.title,!!item.pinned,!!activeRun(item.id)])]);if(target.dataset.signature===signature)return;target.dataset.signature=signature;target.replaceChildren();
  visible.forEach(item=>{
    const row=element('div','task-row'),button=element('button',item.id===state.selected?'selected':'');button.append(element('span','status-dot'+(activeRun(item.id)?'':' neutral')),element('span','',(item.pinned?'★ ':'')+item.title));button.setAttribute('aria-current',String(item.id===state.selected));action(button,()=>selectSession(item.id));
    const menu=setIconButton(element('button'),'edit','Actions for '+item.title);action(menu,()=>taskActions(item.id));row.append(button,menu);$('#task-list').append(row);
  });
}
function setView(view) {
  if(!state.info?.workspace){showWelcome();return;}
  state.view=view;$('.app').dataset.surface=view;
  document.querySelectorAll('[data-view]').forEach(button=>{button.classList.toggle('selected',button.dataset.view===view);button.setAttribute('aria-current',button.dataset.view===view?'page':'false');});
  const global=view!=='work';$('#welcome').hidden=true;['#task-heading','#content-tabs','#composer'].forEach(key=>{$(key).hidden=global||!state.selected;});$('#council-route').hidden=global||!state.selected;
  document.querySelectorAll('.pane,.global-pane').forEach(pane=>{pane.hidden=true;});
  $('#breadcrumb').textContent=global?({tasks:'Task center',library:'Artifact library',files:'Project files',automation:'Automations',capabilities:'Capabilities'})[view]:currentSession()?.title||'Workbench';
  if(!global){if(state.selected)setTab(state.tab);else showWelcome();}
  else{$('#'+view+'-pane').hidden=false;if(view==='tasks')renderMissions().catch(error=>toast(errorText(error)));if(view==='library')loadArtifacts().catch(error=>toast(errorText(error)));if(view==='files')loadDirectory(state.fileDirectory).catch(error=>toast(errorText(error)));if(view==='automation')loadSchedules().catch(error=>toast(errorText(error)));if(view==='capabilities')loadCapability(state.cap).catch(error=>toast(errorText(error)));}
}
function setTab(tab) {state.tab=tab;if(tab==='result')loadResultArtifacts().catch(error=>toast(errorText(error)));if(state.view!=='work')setView('work');['conversation','result','activity','review'].forEach(name=>{$('#'+name+'-pane').hidden=name!==tab;const button=$('#'+name+'-tab');button.setAttribute('aria-selected',String(name===tab));button.tabIndex=name===tab?0:-1;});}
function renderTask() {
  const session=currentSession();if(!session)return;
  if(state.view==='work'){$('#task-heading').hidden=false;$('#content-tabs').hidden=false;$('#composer').hidden=false;$('#welcome').hidden=true;$('.app').classList.remove('welcome-state');}
  const run=latestRun();$('#task-title').textContent=session.title;$('#task-state').textContent=run?.status||'Ready';
  $('#task-subtitle').textContent=activeRun()?'Working in '+(state.info.remote?'your remote project':'your local project'):run?.status==='completed'?'Ready to review, save, or continue.':'Describe the goal and expected outcome.';
  setIconButton($('#run'),activeRun()?'stop':'send',activeRun()?'Stop task':'Run task');
  renderMessages();renderActivity();renderRoles();
  const result=(state.detail?.messages||[]).filter(item=>item.role==='assistant').at(-1);
  $('#result-content').replaceChildren(markdown(result?.text || 'Your completed result will appear here.'));
  $('#export-archive').disabled=!run?.task_id;$('#resume-open').hidden=!run?.task_id || !['failed','partial_failure','stopped','interrupted'].includes(run.status);
}
function renderMessages() {
  const target=$('#messages'),detail=state.detail;if(!detail)return;const outputKey=activeRun()?state.output.get(activeRun().id):null;const signature=JSON.stringify([state.selected,detail.messages,activeRun()?.status,outputKey]);if(target.dataset.signature===signature)return;target.dataset.signature=signature;const scroll=$('.content-scroll'),nearEnd=scroll.scrollHeight-scroll.scrollTop-scroll.clientHeight<80,position=scroll.scrollTop;target.replaceChildren();
  $('#older-messages').hidden=!detail.message_start;
  for(const message of detail.messages){const block=element('article','message '+message.role);block.append(element('div','message-meta',message.role==='user'?'You':message.status && message.status!=='completed'?'Pantheon · '+message.status:'Pantheon'),markdown(message.text));target.append(block);}
  const run=activeRun(),output=run?state.output.get(run.id):null;
  if(run){const live=element('div','live-output');live.append(element('div','message-meta',run.status==='stopping'?'Stop requested. Waiting for the core to finish safely.':'Working…'),markdown(output?.summary || output?.step || 'Connecting to your council…'));target.append(live);}
  if(!detail.messages.length&&!run)empty(target,'What would you like your council to get done?');requestAnimationFrame(()=>{scroll.scrollTop=nearEnd?scroll.scrollHeight:position;});
}
function renderActivity() {
  const run=latestRun(),events=run?state.eventCache.get(run.id)||[]:[];$('#activity-list').replaceChildren();
  const visible=events.filter(item=>!['step_chunk','summary_chunk','progress'].includes(item.event)).slice(-100);
  for(const item of visible){const row=element('li'),data=item.data||{};row.append(element('span','role-mark hermes',(data.role||'H').slice(0,2).toUpperCase()));const body=element('div');body.append(element('strong','',(data.role?data.role+' · ':'')+item.event.replaceAll('_',' ')),element('p','',data.description||data.detail||data.summary||data.message||data.error||data.plan||''));row.append(body);$('#activity-list').append(row);}
  if(!visible.length)empty($('#activity-list'),'Execution and tool activity will appear here.');
  const roles=new Set();for(const item of events)if(item.data?.role)roles.add(item.data.role);$('#council-route').replaceChildren();
  for(const role of roles){const block=element('div');block.append(element('span','role-mark '+(role==='athena'?'athena':role==='hephaestus'?'forge':'hermes'),role.slice(0,2).toUpperCase()),element('strong','',role));$('#council-route').append(block);}
  $('#council-route').hidden=state.view!=='work'||!roles.size;
}
function renderRoles() {
  $('#role-list').replaceChildren();const statuses=state.setup?.role_statuses||[];
  for(const role of roleNames){const saved=statuses.find(item=>item.role===role),choice=currentSession()?.overrides?.[role] || saved;const row=element('div','inspector-role');row.append(element('span','role-mark mini hermes',role.slice(0,2).toUpperCase()));const body=element('div');body.append(element('strong','',role[0].toUpperCase()+role.slice(1)),element('span','model-label',choice?.model?(choice.provider||'')+' · '+choice.model:'No model assigned'));row.append(body);$('#role-list').append(row);}
}
async function runTask(resume) {
  const running=activeRun();if(running){await api('/api/desktop/runs/'+running.id+'/stop',{});toast('Stop requested. Completed work is retained.');await refresh();return;}
  if(!state.selected)await newTask();await flushDrafts();const prompt=resume?.prompt || $('#prompt').value.trim();if(!prompt){$('#prompt').focus();return;}
  const session=currentSession();
  if(session.title==='New task')await patchSession({title:prompt.slice(0,80)});
  const request={prompt,request_id:crypto.randomUUID(),expected_version:currentSession().desktop_version||0,attachments:(state.attachments.get(state.selected)||[]).map(item=>item.id),...(resume?{resume_task_id:resume.id,acknowledge_effects:resume.ack}: {})};
  $('#run').disabled=true;
  try{const run=await api('/api/desktop/sessions/'+state.selected+'/runs',request);state.runs.unshift(run);$('#prompt').value='';state.detail.draft='';state.attachments.set(state.selected,[]);renderAttachments();setTab('conversation');await refresh();}
  catch(error){if(/timeout|fetch|network/i.test(errorText(error)))notice('The send status is uncertain. Refresh task history before trying again; do not resend automatically.');throw error;}
  finally{$('#run').disabled=false;}
}
async function pollEvents() {
  const candidates=state.runs.filter(run=>activeStatuses.has(run.status)||run.session_id===state.selected).slice(0,15);
  for(const run of candidates){const response=await api('/api/desktop/runs/'+run.id+'/events?after='+(state.cursors.get(run.id)||0));if(!response.events.length)continue;
    const cache=state.eventCache.get(run.id)||[],output=state.output.get(run.id)||{summary:'',step:''};
    for(const event of response.events){cache.push(event);state.cursors.set(run.id,event.id);
      if(event.event==='step_start')output.step='';
      if(event.event==='step_chunk')output.step+=event.data.text||'';
      if(event.event==='summary_chunk')output.summary+=event.data.text||'';
      if(event.event==='mcp_approval_required'){state.approvals.set(event.data.approval_id,event.data);}
      if(event.event==='mcp_approval_resolved')state.approvals.delete(event.data.approval_id);
      if(event.event==='desktop_final'&&!state.seenFinal.has(run.id)){state.seenFinal.add(run.id);refreshUsage().catch(()=>{});loadResultArtifacts().catch(()=>{});}
    }
    state.eventCache.set(run.id,cache.slice(-6000));state.output.set(run.id,output);
    const index=state.runs.findIndex(item=>item.id===run.id);state.runs[index]={...run,...response.run};
  }
  if(state.selected){renderMessages();renderActivity();}
  if(state.approvals.size&&!$('#approval-dialog').open){const pending=[...state.approvals.values()][0];$('#approval-dialog').dataset.approvalId=pending.approval_id;$('#approval-details').textContent=JSON.stringify(pending,null,2);showDialog('#approval-dialog');}
}
async function tick(){if(state.polling||!state.info?.workspace)return;state.polling=true;try{await pollEvents();await refresh();if(state.file && !$('#files-pane').hidden){const disk=await api('/api/desktop/file?path='+encodeURIComponent(state.file.path));if(disk.hash!==state.file.hash){$('#file-change-notice').textContent='This file changed outside the editor. Reload it or review against the new version before saving.';$('#file-change-notice').hidden=false;}}}catch(error){notice(errorText(error));}finally{state.polling=false;}}
async function taskActions(id=state.selected) {
  const session=state.sessions.find(item=>item.id===id);if(!session)return;const content=element('div');content.append(element('p','',session.title));
  for(const [label,callback] of [
    ['Rename',async()=>{const title=await askText('Rename task','Task name',session.title);if(title)await patchSession({title},id);}],
    [session.pinned?'Unpin':'Pin',()=>patchSession({pinned:!session.pinned},id)],
    [session.archived?'Restore task':'Archive task',()=>patchSession({archived:!session.archived},id)],
    ['Open in a new window',()=>native.newWindow(id)]]){const button=element('button','wide-button',label);action(button,async()=>{closeDialog('#info-dialog');await callback();if(state.view==='tasks')renderMissions().catch(error=>toast(errorText(error)));});content.append(button);}
  info('Task actions',content);
}
async function renderMissions() {
  const query=$('#task-filter').value.trim(),filter=$('#task-status').value,epoch=state.epoch;
  const found=query?new Set((await api('/api/desktop/search?query='+encodeURIComponent(query))).sessions.map(item=>item.id)):null;
  const tasks=await api('/api/tasks');if(epoch!==state.epoch||query!==$('#task-filter').value.trim()||filter!==$('#task-status').value)return;state.coreTasks=tasks.tasks||[];
  const signature=JSON.stringify([query,filter,state.sessions.map(item=>[item.id,item.title,item.pinned,item.archived,item.updatedAt,latestRun(item.id)?.status]),state.coreTasks.map(item=>[item.id,item.status,item.updated])]);const target=$('#mission-list');if(target.dataset.signature===signature)return;target.dataset.signature=signature;target.replaceChildren();
  for(const session of state.sessions.filter(item=>filter==='archived'?item.archived:!item.archived)){
    const run=latestRun(session.id);if(found&&!found.has(session.id))continue;
    if(filter==='running'&&!activeRun(session.id))continue;if(filter==='attention'&&run?.status==='completed')continue;
    const row=element('div','mission-row'),title=element('div','mission-title');title.append(element('strong','',(session.pinned?'★ ':'')+session.title),element('small','',new Date(session.updatedAt).toLocaleString()));row.append(title,element('span','mission-state',run?.status||'Ready'));
    const open=setIconButton(element('button'),'open','Open task');action(open,()=>selectSession(session.id));row.append(open);
    if(activeRun(session.id)){const stop=setIconButton(element('button'),'stop','Stop task');action(stop,async()=>{await api('/api/desktop/runs/'+activeRun(session.id).id+'/stop',{});await refresh();});row.append(stop);}
    const menu=setIconButton(element('button'),'edit','Task actions');action(menu,()=>taskActions(session.id));row.append(menu);$('#mission-list').append(row);
  }
  if(!$('#mission-list').children.length)empty($('#mission-list'),'No tasks match this view.');
  const known=new Set(state.runs.map(run=>run.task_id));
  for(const task of state.coreTasks.filter(item=>!known.has(item.id))){const row=element('div','data-card');row.append(element('strong','',task.data?.task||task.id),element('p','',task.status+' · CLI / Web task'));const view=element('button','','View saved result');action(view,async()=>{const data=await api('/api/tasks/'+encodeURIComponent(task.id));info('Saved task',markdown(data.data?.result||JSON.stringify(data,null,2)));});row.append(view);$('#mission-list').append(row);}
}
async function loadArtifacts() {const query=$('#artifact-query').value;state.artifacts=(await api('/api/desktop/artifacts?query='+encodeURIComponent(query))).artifacts;$('#artifact-grid').replaceChildren();for(const item of state.artifacts.filter(value=>$('#artifact-kind').value==='all'||value.kind===$('#artifact-kind').value))$('#artifact-grid').append(artifactCard(item));if(!$('#artifact-grid').children.length)empty($('#artifact-grid'),'Completed tasks will add their outputs here.');}
function artifactCard(item) {const card=element('div','artifact-card');card.append(element('strong','',item.title),element('small','',item.filename+' · v'+item.version+(item.saved_path?' · Saved: '+item.saved_path:' · Not saved to project')),element('p','',new Date(item.created*1000).toLocaleString()));const actions=element('div','artifact-actions');for(const [label,callback] of [['Preview',()=>previewArtifact(item.id)],['Source task',()=>selectSession(item.session_id)],['Review and save',()=>saveArtifact(item.id)]]){const button=element('button','',label);action(button,callback);actions.append(button);}card.append(actions);return card;}
async function previewArtifact(id) {const item=await api('/api/desktop/artifacts/'+id);const content=element('div');if(item.filename.endsWith('.html')){const frame=element('iframe','artifact-preview');frame.setAttribute('sandbox','');frame.title=item.title;const html='<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; style-src &#39;unsafe-inline&#39;; img-src data:; script-src &#39;none&#39;; form-action &#39;none&#39;; base-uri &#39;none&#39;">'+item.content;const url=URL.createObjectURL(new Blob([html],{type:'text/html'}));frame.src=url;content.append(frame);$('#info-dialog').addEventListener('close',()=>URL.revokeObjectURL(url),{once:true});}else content.append(markdown(item.content));info(item.title,content);}
async function saveArtifact(id) {const item=await api('/api/desktop/artifacts/'+id);const path=await askText('Save artifact','Project-relative file path',item.filename);if(path)await prepareReview({path,content:item.content,artifact_id:id});}
async function loadDirectory(path='') {const value=await api('/api/workspace/files?path='+encodeURIComponent(path));state.fileDirectory=value.cwd;$('#file-directory').textContent=value.cwd||'Project root';$('#file-tree').replaceChildren();if(value.parent!==null){const parent=element('button','','← Parent folder');action(parent,()=>loadDirectory(value.parent));$('#file-tree').append(parent);}for(const item of value.items.filter(item=>!item.name.startsWith('.')&&!/\.(pem|key)$/.test(item.name))){const button=element('button','',(item.kind==='directory'?'▸ ':'')+item.name);action(button,()=>item.kind==='directory'?loadDirectory(item.path):openFile(item.path));$('#file-tree').append(button);}}
async function openFile(path) {if(!state.selected)await newTask();await flushDrafts();const value=await api('/api/desktop/file?path='+encodeURIComponent(path));state.file={path:value.path,hash:value.hash};$('#editor-label').textContent=value.path;$('#file-editor').disabled=false;$('#file-editor').value=value.content;$('#file-change-notice').hidden=true;await patchSession({editor_draft:{...state.file,content:value.content}});}
async function prepareReview(value) {state.activeReview=await api('/api/desktop/reviews',value);$('#review-path').textContent=state.activeReview.path;$('#review-diff').textContent=state.activeReview.diff||'No text changes.';$('#review-state').textContent=state.activeReview.truncated?'Diff truncated. Inspect the full file before accepting.':'Pending review · No files written';$('#review-accept').disabled=state.activeReview.truncated;setView('work');setTab('review');}
async function loadSchedules() {const value=await api('/api/chronos/jobs');$('#schedule-list').replaceChildren();for(const item of value.jobs){const card=element('div','data-card');card.append(element('strong','',item.task||item.name||item.id),element('p','',(item.enabled===false?'Paused':'Enabled')+' · '+(item.cron||item.schedule||JSON.stringify(item.schedule_spec||{}))));for(const operation of [item.enabled===false?'resume':'pause','run']){const button=element('button','',operation==='run'?'Run once':operation==='pause'?'Pause':'Enable');action(button,async()=>{if(operation==='run'&&!await confirmChoice('Run scheduled task now?','This can call your configured providers and execute approved tools.','Run once'))return;await api('/api/chronos/jobs/'+item.id+'/'+operation,{});await loadSchedules();});card.append(button);}$('#schedule-list').append(card);}if(!value.jobs.length)empty($('#schedule-list'),'No schedules configured.');}
async function loadCapability(name) {
  state.cap=name;const target=$('#capability-content');target.replaceChildren();
  if(name==='git'){const value=await api('/api/desktop/git');if(!value.available){empty(target,value.message);return;}const card=element('div','data-card');card.append(element('strong','',value.branch||'Detached HEAD'),element('pre','',value.status||'Working tree is clean'),element('pre','',value.diff||'No unstaged diff'));const create=element('button','','Create isolated worktree');action(create,async()=>{const base=await askText('Create isolated worktree','Starting branch or commit','HEAD');if(!base)return;const tree=await api('/api/desktop/git/worktrees',{base});const panel=element('div');panel.append(element('p','',tree.note),element('pre','',tree.path+'\n'+tree.branch));const open=element('button','primary','Open isolated project');action(open,async()=>{state.info=await native.openWorktree(tree.path);if(state.info.workspace){closeDialog('#info-dialog');resetWorkspace();workspaceUI();await refresh();}});panel.append(open);info('Worktree created',panel);});card.append(create);target.append(card,element('pre','',value.worktrees));return;}
  if(name==='media'){await loadMedia(target);return;}const value=await api('/api/'+name);const items=value.items||value.servers||value.channels||[];
  if(name==='memory'){const add=element('button','primary','Add memory');action(add,async()=>{const text=await askText('Project memory','Content');if(text){await api('/api/memory',{content:text});await loadCapability(name);}});target.append(add);}
  const list=Array.isArray(items)?items:Object.entries(items).map(([id,data])=>({id,...data}));
  for(const item of list){const card=element('div','data-card');card.append(element('strong','',item.name||item.title||item.platform||item.id),element('p','',item.description||item.content||item.summary||''),element('small','',item.enabled===false?'Disabled':item.status||'Configured'));
    if(['skills','plugins'].includes(name)){const toggle=element('button','',item.enabled===false?'Enable':'Disable');action(toggle,async()=>{await api('/api/'+name+'/'+item.id+'/toggle',{enabled:item.enabled===false});await loadCapability(name);});card.append(toggle);}
    if(['skills','plugins','mcp/servers'].includes(name)&&item.source!=='builtin'){const edit=element('button','','Edit');action(edit,()=>editCapability(name,item));card.append(edit);}if(name==='mcp/servers'){const inspect=element('button','','Inspect tools');action(inspect,async()=>{if(!await confirmChoice('Connect to this MCP server?',item.transport==='stdio'?'This starts the configured program on the connected host.':'This connects to the configured MCP endpoint.','Connect and inspect'))return;await api('/api/mcp/servers/'+item.id+'/test',{});await loadCapability(name);});const policies=element('button','','Tool policies');action(policies,()=>editToolPolicies(item));card.append(inspect,policies);}const details=element('button','','View details');action(details,()=>info('Capability details',element('pre','',JSON.stringify(item,null,2))));card.append(details);target.append(card);
  }
  if(!list.length)empty(target,'No '+name+' configured.');
  if(name==='channels'){for(const item of list){const button=element('button','','Configure '+item.name);action(button,()=>editChannel(item));target.append(button);}}
  else if(['skills','plugins','mcp/servers'].includes(name)){const button=element('button','','Add '+(name==='mcp/servers'?'MCP server':name.slice(0,-1)));action(button,()=>editCapability(name));target.append(button);}
}
async function openConnections() {await refreshSetup();const selected=$('#provider').value;$('#provider').replaceChildren();for(const provider of state.setup.providers){const option=element('option','',provider.label||provider.id);option.value=provider.id;$('#provider').append(option);}if(selected&&state.setup.providers.some(item=>item.id===selected))$('#provider').value=selected;fillProvider();renderConnectionSummary();showDialog('#connections-dialog');}
function providerChoice(){return state.setup?.providers.find(item=>item.id===$('#provider').value);}
function fillProvider(){const provider=providerChoice();if(!provider)return;$('#base-url').value=provider.base_url||'';$('#test-model').value=provider.test_model||provider.default_model||provider.models?.[0]?.id||'';$('#api-key').value='';$('#credential-storage').value=provider.credential_storage||'env';$('#streaming').checked=provider.streaming!==false;$('#model-options').replaceChildren();for(const model of provider.models||[]){const option=element('option');option.value=model.id;option.label=model.label||model.id;$('#model-options').append(option);}$('#connection-message').textContent=provider.key_configured?'Saved key available. Leave the key field blank to keep it.':'Add a key to use this provider.';}
function renderConnectionSummary() {$('#connection-summary').replaceChildren();for(const provider of state.setup.providers.filter(item=>item.connection_saved)){const row=element('div','data-card');row.append(element('strong','',provider.label||provider.id),element('p','',(provider.enabled?'Enabled':'Disabled')+' · '+(provider.api_health?.state||'Untested')));$('#connection-summary').append(row);}}
function connectionBody(){return {provider:$('#provider').value,model:$('#test-model').value.trim(),base_url:$('#base-url').value.trim(),api_key:$('#api-key').value.trim()||undefined,credential_storage:$('#credential-storage').value,streaming:$('#streaming').checked};}
async function openModels(){if(!state.selected)await newTask();await refreshSetup();const choices=roleNames.map(role=>currentSession()?.overrides?.[role]||state.setup.role_statuses.find(item=>item.role===role)||{});const mixed=new Set(choices.map(item=>item.provider+'/'+item.model)).size>1;$('[name="model-mode"][value="'+(mixed?'mixed':'single')+'"]').checked=true;renderModels();showDialog('#models-dialog');}
function renderModels(){const mixed=$('[name="model-mode"]:checked')?.value==='mixed';$('#model-rows').replaceChildren();for(const [index,role] of roleNames.entries()){const row=element('div','model-row'),label=element('strong','',role);const provider=element('select'),model=element('input');model.setAttribute('aria-label',role+' model');provider.setAttribute('aria-label',role+' provider');for(const choice of state.setup.providers.filter(item=>item.enabled)){const option=element('option','',choice.label||choice.id);option.value=choice.id;provider.append(option);}const saved=currentSession()?.overrides?.[role]||state.setup.role_statuses.find(item=>item.role===role)||{};provider.value=saved.provider||state.setup.provider;model.value=saved.model||providerChoice()?.test_model||'';const changed=()=>{const choice=state.setup.providers.find(item=>item.id===provider.value);model.value=choice?.test_model||choice?.models?.[0]?.id||'';if(!mixed)$('#model-rows').querySelectorAll('.model-row').forEach(other=>{other.querySelector('select').value=provider.value;other.querySelector('input').value=model.value;});};provider.onchange=changed;model.oninput=()=>{if(!mixed)$('#model-rows').querySelectorAll('input').forEach(other=>{other.value=model.value;});};row.dataset.role=role;row.append(label,provider,model);$('#model-rows').append(row);if(!mixed&&index>0){provider.value=$('#model-rows select').value;model.value=$('#model-rows input').value;}}}
async function openUsage() {const run=latestRun();const [usage,budget]=await Promise.all([api('/api/usage/details'+(run?.task_id?'?task_id='+encodeURIComponent(run.task_id):'')),api('/api/budgets')]);const content=element('div');content.append(element('p','',usage.note));for(const group of usage.groups){const card=element('div','data-card');card.append(element('strong','',(group.role||'Other')+' · '+group.phase),element('p','',group.provider+' / '+group.model+' · '+group.calls+' call(s)'),element('p','',(group.input_tokens===null?'Unknown':group.input_tokens)+' input tokens · '+(group.output_tokens===null?'Unknown':group.output_tokens)+' output tokens'),element('p','',group.unpriced?'Cost unknown':('$'+Number(group.estimated_usd||0).toFixed(4)+' estimated')));content.append(card);}if(!usage.groups.length)content.append(element('p','','No calls recorded for this task.'));const input=element('textarea');input.rows=12;input.style.width='100%';input.value=JSON.stringify(budget.policy||budget,null,2);const save=element('button','primary','Save workspace budget');action(save,async()=>{await api('/api/budgets',JSON.parse(input.value));toast('Budget saved.');});const details=element('details');details.append(element('summary','','Workspace budget policy'),element('p','','Prices must be entered explicitly. Unknown prices remain unknown.'),input,save);content.append(details);info('Usage and budgets',content);}
async function recoverTask(){const run=latestRun();if(!run?.task_id)return;const core=await api('/api/tasks/'+encodeURIComponent(run.task_id));const accepted=await confirmChoice('Review before resuming','Completed steps are retained. Inspect any external actions before retrying. Resume uses the current saved configuration.','I checked the effects — resume');if(accepted)await runTask({id:run.task_id,prompt:core.data?.task||run.data.prompt,ack:true});}
async function addAttachments(items){if(!state.selected)await newTask();const list=state.attachments.get(state.selected)||[];for(const item of items){if(list.length>=5)throw new Error('Use up to five attachments per message.');const uploaded=await api('/api/desktop/attachments',item);if(uploaded.type.startsWith('audio/')){toast('Transcribe audio in Capabilities → Media, then use the text in your task.');continue;}list.push(uploaded);}state.attachments.set(state.selected,list);await patchSession({attachment_draft:list.map(item=>item.id)});renderAttachments();}
function renderAttachments(){$('#attachment-list').replaceChildren();for(const item of state.attachments.get(state.selected)||[]){const chip=element('span','attachment-chip',item.name),remove=element('button','','×');remove.setAttribute('aria-label','Remove '+item.name);action(remove,async()=>{const list=state.attachments.get(state.selected).filter(value=>value.id!==item.id);state.attachments.set(state.selected,list);await patchSession({attachment_draft:list.map(value=>value.id)});renderAttachments();});chip.append(remove);$('#attachment-list').append(chip);}}
const commands=[['New task',newTask],['Choose project',connectWorkspace],['Task center',()=>setView('tasks')],['Artifact library',()=>setView('library')],['Project files',()=>setView('files')],['Models and connections',openConnections],['Capabilities',()=>setView('capabilities')],['Open terminal',()=>showTerminal(true)],['Toggle Focus layout',async()=>{const layout=$('.app').dataset.layout==='focus'?'professional':'focus';state.info.preferences=await native.preferences({layout});applyPreferences(state.info.preferences);}],['Connect remote server',()=>showDialog('#remote-dialog')]];
async function searchCommands(query='') {const target=$('#command-list');target.replaceChildren();for(const [name,callback] of commands.filter(([name])=>name.toLowerCase().includes(query.toLowerCase()))){const button=element('button','',name);action(button,async()=>{closeDialog('#palette');await callback();});target.append(button);}if(query.trim()&&state.info?.workspace){const found=await api('/api/desktop/search?query='+encodeURIComponent(query));if($('#command-search').value!==query)return;for(const session of found.sessions){const button=element('button','',session.title);button.append(element('small','','Task'+(session.archived?' · Archived':'')));action(button,async()=>{closeDialog('#palette');await selectSession(session.id);});target.append(button);}for(const item of found.artifacts.slice(0,20)){const button=element('button','',item.title);button.append(element('small','','Artifact'));action(button,async()=>{closeDialog('#palette');await previewArtifact(item.id);});target.append(button);}}}
function openPalette(){showDialog('#palette');$('#command-search').value='';searchCommands().catch(error=>toast(errorText(error)));$('#command-search').focus();}
function bind() {
  document.querySelectorAll('[data-close]').forEach(button=>{button.onclick=()=>button.closest('dialog').close();});
  document.querySelectorAll('[data-view]').forEach(button=>{const mark=button.querySelector('[data-nav-icon]');if(mark)mark.replaceChildren(desktopIcon(mark.dataset.navIcon));button.dataset.tooltip=button.textContent.trim();action(button,()=>setView(button.dataset.view));});
  document.querySelectorAll('[data-tab]').forEach(button=>{button.onclick=()=>setTab(button.dataset.tab);});
  action($('#new-task'),newTask);action($('#project-open'),connectWorkspace);action($('#project-name'),connectWorkspace);action($('#welcome-workspace'),connectWorkspace);
  action($('#welcome-connections'),openConnections);action($('#connections-open'),openConnections);action($('#welcome-remote'),()=>showDialog('#remote-dialog'));
  action($('#run'),()=>runTask());action($('#mode'),()=>{});$('#mode').onchange=()=>patchSession({mode:$('#mode').value}).catch(error=>toast(errorText(error)));
  $('#prompt').oninput=()=>{const id=state.selected;state.edits.set(id,(state.edits.get(id)||0)+1);state.dirty.add(id);try{localStorage.setItem('pantheon-draft:'+state.info.workspace.workspace+':'+id,JSON.stringify({value:$('#prompt').value,updated:Date.now()}));}catch{}$('#draft-state').textContent='Unsaved';clearTimeout(state.draftTimer);const draft=$('#prompt').value;state.draftTimer=setTimeout(()=>patchSession({draft},id).catch(error=>toast(errorText(error))),450);};
  $('#file-editor').oninput=()=>{state.edits.set(state.selected,(state.edits.get(state.selected)||0)+1);state.dirty.add(state.selected);clearTimeout(state.editorTimer);const id=state.selected,draft={...state.file,content:$('#file-editor').value};state.editorTimer=setTimeout(()=>patchSession({editor_draft:draft},id).catch(error=>toast(errorText(error))),600);};
  action($('#older-messages'),async()=>{const older=await api('/api/desktop/sessions/'+state.selected+'?before='+state.detail.message_start);state.detail.messages=[...older.messages,...state.detail.messages];state.detail.message_start=older.message_start;renderMessages();});
  action($('#models-open'),openModels);action($('#models-edit'),openModels);action($('#assign-open'),async()=>{closeDialog('#connections-dialog');await openModels();});
  document.querySelectorAll('[name="model-mode"]').forEach(input=>{input.onchange=renderModels;});
  action($('#save-models'),async()=>{const overrides={};$('#model-rows').querySelectorAll('.model-row').forEach(row=>{overrides[row.dataset.role]={provider:row.querySelector('select').value,model:row.querySelector('input').value.trim()};});await patchSession({overrides});closeDialog('#models-dialog');renderRoles();});
  $('#provider').onchange=fillProvider;
  $('#connection-form').onsubmit=event=>{event.preventDefault();(async()=>{state.setup=await api('/api/connections/save',connectionBody());$('#api-key').value='';renderConnectionSummary();$('#connection-message').textContent='Connection saved. Existing role assignments are unchanged.';})().catch(error=>{$('#connection-message').textContent=errorText(error);});};
  action($('#test-api'),async()=>{if(!await confirmChoice('Test provider access?','This sends a small request to the selected provider and can incur usage.','Test API'))return;const value=await api('/api/setup/test',connectionBody());state.setup=value;$('#connection-message').textContent=value.ok?'API verified.':value.problem||'API test failed.';renderConnectionSummary();});
  action($('#refresh-models'),async()=>{const value=await api('/api/setup/models',{...connectionBody(),current_model:$('#test-model').value});await refreshSetup();fillProvider();$('#connection-message').textContent=value.message;});
  action($('#use-provider'),async()=>{if(!await confirmChoice('Update defaults for new tasks?','Existing conversations keep their saved model choices.','Update defaults'))return;const models=Object.fromEntries(roleNames.map(role=>[role,{provider:$('#provider').value,model:$('#test-model').value.trim()}]));state.setup=await api('/api/models/defaults',{models});toast('New-task defaults saved.');});
  action($('#manage-connection'),manageConnection);
  action($('#task-menu'),()=>taskActions());action($('#new-window'),()=>native.newWindow(state.selected));
  action($('#inspector-toggle'),()=>showInspector($('#inspector-toggle').getAttribute('aria-pressed')!=='true'));action($('#inspector-close'),()=>showInspector(false));
  action($('#theme-toggle'),async()=>{state.info.preferences=await native.preferences({theme:$('.app').dataset.theme==='light'?'dark':'light'});applyPreferences(state.info.preferences);});
  action($('#layout-toggle'),commands.find(([name])=>name==='Toggle Focus layout')[1]);
  action($('#terminal-toggle'),()=>showTerminal($('#terminal-drawer').hidden));action($('#terminal-close'),()=>showTerminal(false));action($('#terminal-stop'),()=>native.stopTerminal());
  let terminalBuffer='';native.onTerminal(value=>{if(value.text){terminalBuffer+=value.text;while(terminalBuffer.includes('\n\n')){const i=terminalBuffer.indexOf('\n\n'),block=terminalBuffer.slice(0,i);terminalBuffer=terminalBuffer.slice(i+2);const line=block.split('\n').find(line=>line.startsWith('data: '));if(line){try{const data=JSON.parse(line.slice(6));$('#terminal-output').textContent+=(data.text||data.output||data.message||data.error||JSON.stringify(data))+'\n';}catch{}}}}if(value.error)$('#terminal-output').textContent+=value.error+'\n';if($('#terminal-output').textContent.length>200000)$('#terminal-output').textContent=$('#terminal-output').textContent.slice(-200000);$('#terminal-output').scrollTop=$('#terminal-output').scrollHeight;});
  $('#terminal-form').onsubmit=event=>{event.preventDefault();native.terminal({command:$('#terminal-command').value}).catch(error=>toast(errorText(error)));};
  action($('#attach'),async()=>addAttachments(await native.pickFiles()));
  action($('#reveal-project'),()=>native.reveal(''));action($('#reload-file'),()=>state.file?openFile(state.file.path):Promise.resolve());
  action($('#prepare-file'),async()=>{if(state.file)await prepareReview({path:state.file.path,content:$('#file-editor').value,expected_hash:state.file.hash});});
  action($('#review-accept'),async()=>{if(!state.activeReview)return;const value=await api('/api/desktop/reviews/'+state.activeReview.id+'/accept',{});$('#review-state').textContent='Saved to '+value.path;state.activeReview=null;$('#review-accept').disabled=true;if(state.file?.path===value.path){state.file.hash=value.hash;await patchSession({editor_draft:{...state.file,content:$('#file-editor').value}});}toast('Reviewed changes saved.');});
  action($('#review-reject'),async()=>{if(state.activeReview)await api('/api/desktop/reviews/'+state.activeReview.id+'/reject',{});state.activeReview=null;$('#review-state').textContent='Changes not applied.';$('#review-accept').disabled=true;});
  action($('#export-archive'),async()=>{if(latestRun()?.task_id)await native.exportArchive(latestRun().task_id);});action($('#usage-open'),openUsage);action($('#resume-open'),recoverTask);
  for(const [id,approved] of [['allow-approval',true],['deny-approval',false]])action($('#'+id),async()=>{const id=$('#approval-dialog').dataset.approvalId;try{await api('/api/mcp/approvals/'+id,{approved});}finally{state.approvals.delete(id);closeDialog('#approval-dialog');}});
  $('#schedule-form').onsubmit=event=>{event.preventDefault();(async()=>{await api('/api/chronos/jobs',{text:$('#schedule-text').value});$('#schedule-text').value='';await loadSchedules();})().catch(error=>toast(errorText(error)));};
  document.querySelectorAll('[data-cap]').forEach(button=>action(button,()=>loadCapability(button.dataset.cap)));
  $('#task-filter').oninput=()=>renderMissions().catch(error=>toast(errorText(error)));$('#task-status').onchange=()=>renderMissions().catch(error=>toast(errorText(error)));
  $('#artifact-query').oninput=()=>loadArtifacts().catch(error=>toast(errorText(error)));$('#artifact-kind').onchange=()=>loadArtifacts().catch(error=>toast(errorText(error)));
  action($('#palette-open'),openPalette);action($('#search-tasks'),openPalette);let searchTimer;$('#command-search').oninput=()=>{clearTimeout(searchTimer);searchTimer=setTimeout(()=>searchCommands($('#command-search').value).catch(error=>toast(errorText(error))),180);};
  $('#command-search').onkeydown=event=>{if(event.key==='ArrowDown'){$('#command-list button')?.focus();event.preventDefault();}if(event.key==='Enter'){$('#command-list button')?.click();event.preventDefault();}};
  action($('#settings-open'),async()=>{const preferences=await native.preferences();$('#font-size').value=preferences.fontSize;$('#panel-width').value=preferences.panelWidth;for(const id of ['notifications','background','global-shortcut'])$('#'+id).checked=preferences[id==='global-shortcut'?'globalShortcut':id];showDialog('#settings-dialog');});
  $('#preferences-form').onsubmit=event=>{event.preventDefault();native.preferences({fontSize:Number($('#font-size').value),panelWidth:Number($('#panel-width').value),notifications:$('#notifications').checked,background:$('#background').checked,globalShortcut:$('#global-shortcut').checked}).then(value=>{state.info.preferences=value;applyPreferences(value);closeDialog('#settings-dialog');}).catch(error=>toast(errorText(error)));};
  action($('#service-open'),showService);
  $('#remote-form').onsubmit=event=>{event.preventDefault();(async()=>{await flushDrafts();const value=await native.connectRemote({url:$('#remote-url').value,username:$('#remote-user').value,password:$('#remote-password').value,remember:$('#remote-remember').checked});$('#remote-password').value='';state.info=value;resetWorkspace();closeDialog('#remote-dialog');workspaceUI();await refresh();})().catch(error=>{$('#remote-error').textContent=errorText(error);$('#remote-password').value='';});};
  native.onCommand(command=>{(async()=>{if(command==='connection-lost'){$('#connection-state').textContent='Disconnected';notice('The core is unavailable. Saved tasks will not be resent. Open Service and updates to reconnect.');}if(command==='new')await newTask();if(command==='workspace')await connectWorkspace();if(command==='palette')openPalette();if(command==='focus')$('#prompt').focus();if(command==='workspace-ready'){state.info=await native.info();workspaceUI();await refresh();}if(command==='preferences'){state.info.preferences=await native.preferences();applyPreferences(state.info.preferences);}if(command==='updates')await showService();})().catch(error=>toast(errorText(error)));});
  document.addEventListener('keydown',event=>{const mod=event.metaKey||event.ctrlKey;if(mod&&event.key.toLowerCase()==='k'){event.preventDefault();openPalette();}if(mod&&event.key.toLowerCase()==='n'){event.preventDefault();newTask().catch(error=>toast(errorText(error)));}if(mod&&event.key==='Enter'&&event.target===$('#prompt')){event.preventDefault();runTask().catch(error=>toast(errorText(error)));}});
  $('#content-tabs').addEventListener('keydown',event=>{const tabs=[...document.querySelectorAll('[role=tab]')],index=tabs.indexOf(event.target);if(index<0||!['ArrowLeft','ArrowRight'].includes(event.key))return;event.preventDefault();const button=tabs[(index+(event.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length];setTab(button.dataset.tab);button.focus();});
  document.addEventListener('dragover',event=>{if(event.dataTransfer.types.includes('Files')){event.preventDefault();$('.app').classList.add('drag-target');}});document.addEventListener('dragleave',event=>{if(!event.relatedTarget)$('.app').classList.remove('drag-target');});
  document.addEventListener('drop',async event=>{if(native.onDrop)return;event.preventDefault();$('.app').classList.remove('drag-target');try{const items=[];for(const file of [...event.dataTransfer.files].slice(0,5)){if(!file.size)continue;if(file.size>20*1024*1024)throw new Error('File exceeds 20 MB');const bytes=new Uint8Array(await file.arrayBuffer());let binary='';for(let i=0;i<bytes.length;i+=32768)binary+=String.fromCharCode(...bytes.subarray(i,i+32768));items.push({name:file.name,data:btoa(binary)});}if(items.length)await addAttachments(items);}catch(error){toast(errorText(error));}});
}
async function showService(){const panel=element('div');panel.append(element('p','',state.info?.workspace?(state.info.remote?'Connected to a remote server. Its lifecycle is managed on that host.':state.info.owned?'Desktop owns this core. Closing the window can keep it in the tray; quitting stops this owned service.':'This is an existing service. Quitting Desktop will not stop it.'):'No core connected.'));const reconnect=element('button','','Reconnect current host');action(reconnect,async()=>{await flushDrafts().catch(()=>{});state.info=state.info.remote?await native.reconnectRemote():await native.reconnect();state.setup=null;notice('');workspaceUI();await refresh();closeDialog('#info-dialog');});if(state.info?.workspace)panel.append(reconnect);const check=element('button','','Check for updates');action(check,async()=>{const result=await native.updates();panel.append(element('p','',result.available?'Update available: '+result.latest+'. Current app: '+result.version:result.reason||('You are up to date. Current app: '+result.version)));});const releases=element('button','','Open official releases');action(releases,()=>native.openRelease());const remote=element('button','','Connect remote server');action(remote,()=>{closeDialog('#info-dialog');showDialog('#remote-dialog');});panel.append(check,releases,remote);info('Service and updates',panel);}
async function boot(){if(!native){showWelcome();$('#startup-error').textContent='This interface needs the native Pantheon app. The browser prototype remains in docs/desktop.';return;}state.info=await native.info();applyPreferences(state.info.preferences);workspaceUI();bind();native.onDrop?.(value=>{(async()=>{if(value.error)throw new Error(value.error);if(value.info){state.info=value.info;resetWorkspace();workspaceUI();await refresh();}if(value.files?.length)await addAttachments(value.files);})().catch(error=>toast(errorText(error)));});native.onUpdate?.(value=>{if(value.available){notice('Pantheon '+value.latest+' is available. Open Service and updates to download it.');$('#service-open').dataset.tooltip='Update available: '+value.latest;}});if(state.info.workspace)await refresh();setInterval(tick,1800);setInterval(async()=>{if(!state.info?.workspace){state.info=await native.info();workspaceUI();if(state.info.workspace)await refresh();}},1500);}
boot().catch(error=>{$('#startup-error').textContent=errorText(error);showWelcome();});
