'use strict';
const journey={artifacts:[],artifactSession:'',artifactRun:'',request:0,brief:null};
const journeyNotes=[
  ['From completed to checked','Set website criteria, inspect actual browser evidence and review bounded repair candidates.','Open delivery checks','delivery-checks'],
  ['Pick up where your project left off','Review confirmed decisions, outputs and next steps across Desktop and Web.','Open project overview','project'],
  ['Your next step, within reach','What’s new and quick links make capabilities easier to find.','Explore features','features'],
  ['Start with a clearer brief','Turn a starting point into an editable goal, deliverables and acceptance criteria.','Try a task template','template'],
  ['Follow the actual work','See recorded steps, active roles and requests for approval as they happen.','Open task activity','activity'],
  ['A delivery you can use','Review the outcome, outputs, saved artifacts and follow-up actions together.','Open task delivery','delivery']
];
function journeyButton(label,callback,className=''){const button=element('button',className,label);button.type='button';action(button,callback);return button;}
function featureAction(id){
  closeDialog('#whats-new-dialog');closeDialog('#feature-guide');
  if(id==='template')return (async()=>{if(!state.info?.workspace&&!await connectWorkspace())return;if(!state.selected)await newTask();return openTaskBrief('build');})();
  if(id==='activity'||id==='delivery'){if(!state.selected){toast('Choose or create a task first.');return setView('tasks');}return setTab(id==='delivery'?'result':'activity');}
  if(id==='delivery-checks')return desktopDelivery.open();if(id==='project')return nativeProject.open();if(id==='models')return openModels();if(id==='budgets')return openUsage();if(id==='operations')return openOperations();
  if(id==='files')return setView('files');if(id==='features')return openFeatureGuide();
  return openSystemDialog(id==='sync'?'sync':id==='backups'?'backups':'updates');
}
function openWhatsNew(){
  $('#whats-new-version').textContent='New in '+state.info.version;
  $('#whats-new-cards').replaceChildren();for(const [title,text,label,id] of journeyNotes){const card=element('article','journey-feature-card');card.append(element('h3','',title),element('p','',text),journeyButton(label,()=>featureAction(id)));$('#whats-new-cards').append(card);}showDialog('#whats-new-dialog');
}
function markJourneyRead(){try{localStorage.setItem('pantheon-whats-new-read',state.info.version);}catch{}$('#whats-new-notice').hidden=true;closeDialog('#whats-new-dialog');}
function syncJourneyNotice(){let seen=false;try{seen=localStorage.getItem('pantheon-whats-new-read')===state.info?.version;}catch{}$('#whats-new-notice').hidden=seen||!!activeRun()||!!state.sending;$('#whats-new-notice-version').textContent='New in '+(state.info?.version||'this version');}
function openFeatureGuide(){
  const content=$('#feature-guide-list');content.replaceChildren();
  for(const [title,text,id,needsProject] of [
    ['Website delivery checks','Define success, inspect real evidence and review bounded repairs.','delivery-checks',true],
    ['Project continuity','Review shared state, tracked file changes and prepare a continuation.','project',true],
    ['Task templates','Shape a goal and decide what a useful delivery looks like.','template',true],
    ['Role models','Use one provider or mix saved connections for this conversation.','models',true],
    ['Usage and budgets','Review recorded usage and set workspace limits.','budgets',true],
    ['Project files & history','Inspect files and compare reviewed text snapshots.','files',true],
    ['Offline drafts','Opt in on a remote workspace. Sync unsent text deliberately.','sync',false],
    ['Backups & recovery','Inspect, back up or restore an idle owned local workspace.','backups',false],
    ['Operation sessions','Review bounded browser or macOS application steps before running.','operations',true],
    ['Updates','Choose a release channel and verify an installer before opening it.','updates',false]
  ]){const button=journeyButton('',()=>featureAction(id),'journey-feature-link');button.append(element('strong','',title),element('span','',text));button.disabled=!!needsProject&&(!state.info?.workspace||state.offline||state.maintenance);content.append(button);}showDialog('#feature-guide');
}
async function openTaskBrief(id){
  const template=JourneyData.templates[id];if(!template||activeRun()||state.sending||state.creatingTask)return;
  journey.brief={id,epoch:state.epoch,session:state.selected,draft:$('#prompt').value};
  $('#brief-title').textContent=template.name;for(const field of ['goal','deliverables','acceptance','constraints'])$('#brief-'+field).value=template[field];
  $('#brief-feedback').textContent='This prepares a draft. It does not send a task or change your model assignment.';showDialog('#brief-dialog');$('#brief-goal').focus();
}
async function applyTaskBrief(){
  const target=journey.brief;if(!target)return;
  const valid=()=>target.epoch===state.epoch&&target.session===state.selected&&target.draft===$('#prompt').value&&!activeRun()&&!state.sending;
  if(!valid()){$('#brief-feedback').textContent='The project, task or draft changed. Close this brief and reopen a template.';return;}
  const text=JourneyData.briefText(Object.fromEntries(['goal','deliverables','acceptance','constraints'].map(key=>[key,$('#brief-'+key).value])));
  if(target.draft.trim()&&!await confirmChoice('Replace this draft?','Your current prompt has not been sent. Replace it with this task brief?','Replace draft'))return;
  if(!valid()){$('#brief-feedback').textContent='The task changed while this brief was open. Your draft was kept.';return;}
  $('#prompt').value=text;$('#prompt').dispatchEvent(new Event('input',{bubbles:true}));closeDialog('#brief-dialog');$('#prompt').focus();toast('Task brief added. Review it, then send when you are ready.');
}
function renderJourneyReadiness(){
  const container=$('#task-readiness');container.hidden=!state.selected||state.view!=='work'||!!activeRun();if(container.hidden)return;
  const value=JourneyData.readiness(state.setup,currentSession(),$('#mode').value,state.offline),signature=JSON.stringify([state.selected,state.info?.workspace?.workspace_name,$('#mode').value,value,state.serviceLost,state.projectOpening,state.maintenance]);if(container.dataset.signature===signature)return;container.dataset.signature=signature;container.replaceChildren();
  const project=journeyButton('',()=>showInspector(true),'readiness-project');project.append(desktopIcon('folder'),element('span','',state.info?.workspace?.workspace_name||'Choose project'));project.title=state.info?.workspace?.workspace||'';
  const models=journeyButton(value.scheduled?'Local scheduling':new Set(value.choices.map(x=>x.label)).size===1?value.choices[0]?.label||'Choose models':'Mixed providers',value.scheduled?()=>setView('automation'):openModels);models.prepend(desktopIcon('models'));models.title=value.choices.map(x=>councilRoles[x.role].name+': '+(x.model||'Not assigned')).join('\n');models.disabled=!!state.offline||state.serviceLost||state.projectOpening||state.maintenance;
  const status=element('span','readiness-state',state.offline?'Offline · draft only':state.projectOpening?'Opening project…':state.serviceLost?'Reconnect service':state.maintenance?'Workspace maintenance':!state.setup?'Reading setup…':value.ready?'Ready to start':value.missing.length+' roles need setup');status.dataset.ready=String(value.ready&&!!state.setup&&!state.serviceLost&&!state.projectOpening&&!state.maintenance);
  container.append(project,models,status);if(!value.ready&&!state.offline&&!state.serviceLost&&!state.projectOpening&&!state.maintenance&&state.setup){const fix=journeyButton('Review setup',openConnections);container.append(fix);}container.append(element('small','',state.serviceLost?'Saved configuration · reconnect the service before sending.':value.ready?'Saved configuration · API testing is optional.':state.offline?'Text stays on this computer until reviewed sync.':'Check connections and task assignments before sending.'));
}
function durationText(run){if(!run?.created)return '';const end=activeStatuses.has(run.status)?Date.now()/1000:run.updated||run.created,seconds=Math.max(0,Math.floor(end-run.created));return seconds<60?seconds+'s elapsed':Math.floor(seconds/60)+'m '+seconds%60+'s elapsed';}
function renderJourneyProgress(){
  const run=latestRun(),panel=$('#task-progress'),shortcut=$('#journey-open-run');shortcut.hidden=!run||state.view!=='work';panel.hidden=!run||state.view!=='work';if(panel.hidden)return;shortcut.textContent=activeStatuses.has(run.status)?'View progress':'Review delivery';
  const events=state.eventCache.get(run.id)||[],value=JourneyData.progress(run,events,state.approvals),signature=JSON.stringify([state.selected,run.id,run.status,value,state.offline]);
  if(panel.dataset.signature!==signature){panel.dataset.signature=signature;panel.replaceChildren();panel.dataset.state=run.status;
    const heading=element('div','journey-section-heading'),copy=element('div');copy.append(element('span','document-kicker','YOUR TASK, IN MOTION'),element('h2','',value.title));heading.append(copy,element('span','progress-elapsed',durationText(run)));panel.append(heading);
    const phases=element('ol','journey-phases'),index={queued:0,planning:1,working:2,delivery:3,complete:4}[value.phase]??0;
    for(const [i,label] of ['Queued','Plan','Work','Deliver'].entries()){const item=element('li','',label);item.dataset.state=i<index?'complete':i===index?'current':'pending';phases.append(item);}panel.append(phases);
    panel.append(element('p','progress-current',state.offline?'Cached activity. Reconnect to refresh this run.':value.waiting?'A tool is paused until you review its approval request.':activeStatuses.has(run.status)?(value.phase==='working'&&value.active.length?value.active.map(step=>(councilRoles[step.role]?.name||step.role||'Specialist')+' · '+JourneyData.stepLabel(step)).join('\n'):value.current||'Waiting for the first recorded execution event.'):value.issue||'Recorded work is retained. Review the delivery and full activity.'));
    const line=element('div','progress-actions');line.append(element('span','',value.total?value.completed+' of '+value.total+' recorded steps complete':'No execution steps recorded yet'),journeyButton('Full activity',()=>setTab('activity')));
    if(!activeStatuses.has(run.status))line.append(journeyButton('Review delivery',()=>setTab('result'),'primary'));if(value.waiting)line.append(journeyButton('Review approval',reviewJourneyApproval,'primary'));panel.append(line);
    if(value.steps.length){const details=element('details','progress-step-details');details.append(element('summary','','Recorded plan'));if(value.plan)details.append(element('p','',value.plan));const list=element('ol');for(const step of value.steps){const row=element('li');row.dataset.state=step.status;row.append(element('strong','',councilRoles[step.role]?.name||step.role||'Step'),element('span','',JourneyData.stepLabel(step)),element('small','',step.status));list.append(row);}details.append(list);panel.append(details);}
  }else panel.querySelector('.progress-elapsed').textContent=durationText(run);
}
function reviewJourneyApproval(){const pending=[...state.approvals.values()][0];if(!pending)return toast('No pending approval is recorded.');$('#approval-dialog').dataset.approvalId=pending.approval_id;$('#approval-details').textContent=JSON.stringify(pending,null,2);showDialog('#approval-dialog');}
async function journeyFollowup(text){
  const epoch=state.epoch,id=state.selected,draft=$('#prompt').value;
  if(draft.trim()&&!await confirmChoice('Replace the current draft?','The current draft has not been sent. Replace it with this follow-up?','Replace draft'))return;
  if(epoch!==state.epoch||id!==state.selected||draft!==$('#prompt').value||activeRun())return toast('The task changed. Your current draft was kept.');
  $('#prompt').value=text;$('#prompt').dispatchEvent(new Event('input',{bubbles:true}));setTab('conversation');$('#prompt').focus();toast('Follow-up prepared. Review before sending.');
}
function renderDelivery(){
  const panel=$('#delivery-summary'),run=latestRun();panel.hidden=!run;if(panel.hidden)return;
  const artifacts=journey.artifactSession===state.selected&&journey.artifactRun===run.id&&journey.artifactEpoch===state.epoch?journey.artifacts:[],value=JourneyData.delivery(run,state.eventCache.get(run.id)||[],artifacts,state.selected);
  const errorContext=journey.artifactErrorContext,outputError=errorContext?.session===state.selected&&errorContext?.run===run.id&&errorContext?.epoch===state.epoch?journey.artifactError:'';
  const checked=typeof desktopDelivery!=='undefined'?desktopDelivery?.summary():null;
  const signature=JSON.stringify([state.selected,run.id,run.status,value,outputError,checked]);if(panel.dataset.signature===signature)return;panel.dataset.signature=signature;panel.replaceChildren();
  const header=element('div','journey-section-heading'),copy=element('div');copy.append(element('span','document-kicker','YOUR DELIVERY'),element('h2','',value.title),element('p','',value.successful?'Review the outcome, keep the useful work, and choose what comes next.':'Review retained work and recorded issues before continuing.'));header.append(copy);panel.append(header);
  const metrics=element('div','delivery-metrics');for(const [number,label] of [[value.completed,'Completed steps'],[value.outputs.length,'Outputs this run'],[value.saves.length,'Reviewed artifact saves']]){const item=label==='Outputs this run'?journeyButton('',()=>$('#result-artifacts').scrollIntoView({block:'start'})):element('div');if(item.tagName==='BUTTON'){item.disabled=!value.outputs.length;item.title='View this run’s outputs';}item.append(element('strong','',String(number)),element('small','',label));metrics.append(item);}panel.append(metrics);
  if(activeStatuses.has(run.status))panel.append(element('p','delivery-note','This run is still in progress. Outputs and saved state may change.'));
  if(value.steps.some(x=>x.status==='completed')){const work=element('section','delivery-completed');work.append(element('h3','','Completed work'));const list=element('ul');for(const step of value.steps.filter(x=>x.status==='completed'))list.append(element('li','',(councilRoles[step.role]?.name||step.role||'Step')+' · '+JourneyData.stepLabel(step)));work.append(list);panel.append(work);}
  const checks=element('section','delivery-evidence');checks.append(element('h3','','Checks & open items'),element('p','',checked?'Recorded website checks: '+checked.verification+(checked.accepted?' · accepted by user':' · user acceptance pending'):value.verification),journeyButton('Open delivery checks',()=>desktopDelivery.open()));if(value.issue)checks.append(element('p','delivery-issue',value.issue));else checks.append(element('p','',value.successful?'No execution errors are present in the loaded activity. Check the response for limitations.':'Review Full activity for the latest recorded status.'));panel.append(checks);
  if(value.saves.length){const saves=element('section','delivery-saves');saves.append(element('h3','','Reviewed artifact saves'));for(const save of value.saves){const button=journeyButton(save.path,()=>openFileHistory(save.path));saves.append(button);}saves.append(element('small','','These are recorded artifact saves, not a complete project diff.'));panel.append(saves);}
  const actions=element('div','delivery-actions');actions.append(journeyButton('Continue conversation',()=>{setTab('conversation');$('#prompt').focus();},'primary'),journeyButton('Review for gaps',()=>journeyFollowup('Review the last result for gaps against the original goal and acceptance criteria. Explain unresolved points and propose the next step.')),journeyButton('Refine this result',()=>journeyFollowup('Refine the last result. The changes I want are: ')),journeyButton('Full activity',()=>setTab('activity')));for(const b of actions.querySelectorAll('button'))b.disabled=!!activeRun();panel.append(actions);
  if(outputError){const error=element('p','delivery-issue','Outputs could not be refreshed. '+outputError+' ');error.append(journeyButton('Retry outputs',loadResultArtifacts));panel.append(error);}
}
function renderJourney(){if(typeof desktopDelivery!=='undefined')desktopDelivery?.contextChanged();syncJourneyNotice();renderJourneyReadiness();renderJourneyProgress();renderDelivery();}
function bindJourney(){
  action($('#journey-open-run'),()=>{const run=latestRun();setTab(activeStatuses.has(run?.status)?'conversation':'result');if(activeStatuses.has(run?.status))$('.content-scroll').scrollTop=0;});action($('#whats-new-open'),openWhatsNew);action($('#whats-new-dismiss'),markJourneyRead);action($('#whats-new-done'),markJourneyRead);action($('#feature-guide-open'),openFeatureGuide);action($('#task-template-open'),()=>openTaskBrief('build'));
  $('#brief-form').onsubmit=event=>{event.preventDefault();applyTaskBrief().catch(error=>{$('#brief-feedback').textContent=errorText(error);});};
  $('#whats-new-dialog').addEventListener('close',()=>{$('#whats-new-open').focus({preventScroll:true});});
}
