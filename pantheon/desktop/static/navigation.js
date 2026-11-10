'use strict';
let paletteRequest=0;
function paletteCommands(){
  const project=!!state.info?.workspace&&!state.maintenance,live=project&&!state.offline&&!state.syncBusy&&!state.creatingTask;
  return [
    ['New task',newTask,project],['Choose project',connectWorkspace,!state.maintenance],
    ['Task center',()=>setView('tasks'),project],['Artifact library',()=>setView('library'),project],
    ['Delivery checks',()=>desktopDelivery.open(),live],['Project overview',()=>nativeProject.open(),live],['Project files',()=>setView('files'),live],['Models and connections',openConnections,live],
    ['Capabilities',()=>setView('capabilities'),live],['Open terminal',()=>showTerminal(true),live],
    ['Usage and budgets',openUsage,live],['Toggle Focus layout',toggleLayout,true],
    ['Connect remote server',()=>showDialog('#remote-dialog'),!state.maintenance],
    ['Service and updates',showService,true],['What’s new',openWhatsNew,true],['Explore features',openFeatureGuide,true],['Task brief',()=>openTaskBrief('build'),live],['Help and diagnostics',openHelp,true]
  ];
}
function commandResult(name,detail,callback,enabled=true){
  const button=element('button','command-result',name);button.setAttribute('aria-label',name);button.disabled=!enabled;
  if(detail)button.append(element('small','',detail));
  action(button,async()=>{closeDialog('#palette');await callback();});return button;
}
async function searchCommands(query=''){
  const request=++paletteRequest,epoch=state.epoch,target=$('#command-list'),status=$('#command-status');
  target.dataset.query=query;target.replaceChildren();status.replaceChildren();target.setAttribute('aria-busy','false');
  const normalized=query.trim().toLowerCase();let count=0;
  const group=(label)=>{target.append(element('h3','command-group',label));};
  const commands=paletteCommands().filter(([name])=>name.toLowerCase().includes(normalized));
  if(commands.length){group('Commands');for(const [name,callback,enabled] of commands){target.append(commandResult(name,enabled?'':'Choose a project first',callback,enabled));count++;}}
  if(!normalized){status.textContent=state.info?.workspace?'Search this project’s task messages and artifacts, or choose a command.':'Choose a project to search its tasks and artifacts.';return;}
  if(!state.info?.workspace){status.textContent=count?'Project search is available after choosing a project.':'No matching commands. Choose a project to search its tasks.';return;}
  target.setAttribute('aria-busy','true');status.textContent='Searching this project…';
  try{
    const found=await api('/api/desktop/search?query='+encodeURIComponent(query));
    if(request!==paletteRequest||epoch!==state.epoch||!$('#palette').open)return;
    if(found.sessions.length){group('Tasks');for(const session of found.sessions.slice(0,50)){target.append(commandResult(session.title,'Task'+(session.archived?' · Archived':''),()=>selectSession(session.id)));count++;}}
    if(found.artifacts.length){group('Artifacts');for(const item of found.artifacts.slice(0,30)){target.append(commandResult(item.title,'Artifact',()=>previewArtifact(item.id)));count++;}}
    status.textContent=count?count+' results in '+state.info.workspace.workspace_name+'.':'No matching tasks, artifacts or commands. Try a different word.';
  }catch(error){
    if(request!==paletteRequest||epoch!==state.epoch||!$('#palette').open)return;
    status.append(element('span','','Project search is unavailable. '+errorText(error)+' '));
    const retry=element('button','','Retry search');action(retry,()=>searchCommands($('#command-search').value));status.append(retry);
  }finally{if(request===paletteRequest)target.setAttribute('aria-busy','false');}
}
function openPalette(){showDialog('#palette');$('#command-search').value='';searchCommands();$('#command-search').focus();}
function bindNavigation(){
  let timer;$('#command-search').oninput=()=>{++paletteRequest;clearTimeout(timer);$('#command-list').replaceChildren();$('#command-list').dataset.query='';$('#command-status').textContent='Searching…';timer=setTimeout(()=>searchCommands($('#command-search').value),180);};
  $('#palette').addEventListener('close',()=>{++paletteRequest;clearTimeout(timer);});
  $('#palette').addEventListener('keydown',event=>{
    if(!['ArrowDown','ArrowUp','Home','End','Enter'].includes(event.key)||event.altKey||event.metaKey||event.ctrlKey)return;
    const input=$('#command-search'),buttons=[...$('#command-list').querySelectorAll('button:not(:disabled)')],index=buttons.indexOf(document.activeElement);
    if(event.key==='Enter'&&document.activeElement===input){event.preventDefault();if($('#command-list').dataset.query!==input.value){clearTimeout(timer);searchCommands(input.value).then(()=>$('#command-list button:not(:disabled)')?.click());}else buttons[0]?.click();return;}
    if(event.key==='Home'||event.key==='End'){if(document.activeElement===input)return;event.preventDefault();(event.key==='Home'?buttons[0]:buttons.at(-1))?.focus();return;}
    if(event.key==='ArrowDown'||event.key==='ArrowUp'){
      event.preventDefault();const next=index+(event.key==='ArrowDown'?1:-1);
      if(index===-1)(event.key==='ArrowDown'?buttons[0]:buttons.at(-1))?.focus();
      else if(next<0||next>=buttons.length)input.focus();else buttons[next].focus();
    }
  });
  action($('#help-open'),openHelp);
}
async function openHelp(){
  const content=element('div','help-content');
  content.append(element('p','','Pantheon Desktop '+state.info.version+' · '+state.info.platform+(state.info.packaged?' · Bundled runtime':' · Development runtime')));
  const steps=element('ol');for(const text of ['Choose a project folder and wait for Project connected.','Connect one provider, optionally Test API, then Save connection. Tests may incur usage.','Choose future-task defaults or assign models only to this task. Additional providers are optional.','Describe your goal. Review file changes before saving; inspect interrupted tasks before resuming.'])steps.append(element('li','',text));content.append(element('h3','','Your first task'),steps);
  const list=element('dl','shortcut-list');for(const [key,description] of [['⌘ / Ctrl K','Search tasks, artifacts and commands'],['⌘ / Ctrl N','Create a new task'],['⌘ / Ctrl O','Choose a project'],['⌘ / Ctrl Shift N','Open this task in another window'],['⌘ / Ctrl Enter','Send the current prompt'],['Escape','Close the active menu or dialog']])list.append(element('dt','',key),element('dd','',description));content.append(element('h3','','Keyboard shortcuts'),list);
  content.append(element('h3','','What the controls do'),element('p','','The connection badge separates service access from saved API test evidence. Focus hides navigation without changing your task. Theme changes artwork and controls; select System in Desktop preferences to follow your OS. Service & updates manages verified downloads and offline backups.'));
  const whatsNew=journeyButton('What’s new',()=>{closeDialog('#info-dialog');openWhatsNew();}),features=journeyButton('Explore features',()=>{closeDialog('#info-dialog');openFeatureGuide();});content.append(whatsNew,features);
  const updates=element('button','','Updates and recovery');action(updates,()=>{closeDialog('#info-dialog');return showService();});content.append(updates);
  content.append(element('h3','','Diagnostic export'),element('p','','Export a local JSON file containing app/runtime versions, OS/CPU, service reachability and counts. No API keys, credentials, prompts, messages, files, project names, paths, server URLs or raw logs are included. Nothing is uploaded. Inspect the file before sharing it.'));
  const feedback=element('p','help-feedback');feedback.setAttribute('role','status');const save=element('button','primary','Export private diagnostic summary');
  action(save,async()=>{try{const result=await native.exportDiagnostics();feedback.textContent=result.saved?'Diagnostic summary saved locally. Nothing was uploaded.':'Export cancelled.';}catch(error){feedback.textContent=errorText(error);}});content.append(save,feedback);info('Help and diagnostics',content);
}
