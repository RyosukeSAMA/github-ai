'use strict';
const desktopOperations={status:null,applications:[],steps:[]};
function operationFields(){
  const action=$('#operation-action').value;$('#operation-arg-label').hidden=!['navigate','click','fill','button'].includes(action);$('#operation-value-label').hidden=!['fill','type'].includes(action);$('#operation-ms-label').hidden=action!=='wait';$('#operation-key-label').hidden=action!=='key';
  $('#operation-arg-label').firstChild.textContent=action==='navigate'?'URL in approved origin':action==='button'?'Exact button title':'CSS selector';
}
function operationActions(){
  const kind=desktopOperations.status?.scope?.kind||$('#operation-kind').value;if($('#operation-action').dataset.kind===kind)return;$('#operation-action').dataset.kind=kind;$('#operation-action').replaceChildren();
  for(const [value,label] of (kind==='browser'?[['navigate','Navigate'],['click','Click element'],['fill','Fill field'],['wait','Wait'],['screenshot','Capture browser']]:[['activate','Bring app forward'],['type','Type text'],['button','Click named button'],['key','Press key'],['wait','Wait']])){const option=element('option','',label);option.value=value;$('#operation-action').append(option);}operationFields();
}
function renderOperationSteps(){
  $('#operation-steps').replaceChildren();for(const [index,step] of desktopOperations.steps.entries()){
    const row=element('li'),label=step.action==='navigate'?'Navigate within approved origin':step.action==='fill'?'Fill '+step.selector+' · '+step.value.length+' characters':step.action==='type'?'Type '+step.value.length+' characters':step.action==='click'?'Click '+step.selector:step.action==='button'?'Click button '+step.name:step.action==='key'?'Press '+step.key:step.action==='wait'?'Wait '+step.ms+' ms':step.action==='activate'?'Bring selected app forward':'Capture browser';row.append(element('span','',label));
    const remove=element('button','','Remove');remove.type='button';action(remove,()=>{desktopOperations.steps.splice(index,1);renderOperationSteps();});row.append(remove);$('#operation-steps').append(row);
  }$('#operation-run').disabled=!desktopOperations.status?.active||desktopOperations.status?.busy||!desktopOperations.steps.length;
}
function renderOperationStatus(value){
  desktopOperations.status=value;if(value.applications)desktopOperations.applications=value.applications;
  const active=!!value.active,busy=!!value.busy;$('#operation-notice').hidden=!active&&!busy;$('#operation-notice-text').textContent=(busy?'Operation running':'Operation session')+' · '+(value.scope?.origin||value.scope?.name||'Stopping');
  $('#operation-scope-label').textContent=active?'Approved scope · '+(value.scope.origin||value.scope.name):'No active session';
  for(const key of ['kind','url','app'])$('#operation-'+key).disabled=active||busy;
  $('#operation-start').disabled=active||busy||!state.info?.workspace;$('#operation-stop').disabled=!active&&!busy;$('#operation-stop-global').disabled=!active&&!busy;$('#operation-add').disabled=!active||busy;$('#operation-clear').disabled=busy;
  $('#operation-preview').disabled=!value.has_capture;$('#operation-save').disabled=!value.has_capture;
  $('#operation-app-label').hidden=$('#operation-kind').value!=='application';$('#operation-url-label').hidden=$('#operation-kind').value!=='browser';
  const application=(value.scope?.kind||$('#operation-kind').value)==='application';
  $('#operation-permissions').textContent=!application?'The approved browser is separate from your app session. Its navigation stays within the displayed origin.':value.application_supported?'macOS app control · Accessibility '+(value.accessibility?'granted':'not granted')+'. Automation permission is checked by the OS when you run an app step.':'Native application control is currently available on macOS; this platform has no app adapter.';
  $('#operation-accessibility').hidden=!application||!value.application_supported||!!value.accessibility;
  if(value.applications){const selected=$('#operation-app').value;$('#operation-app').replaceChildren();for(const app of value.applications){const option=element('option','',app.name);option.value=app.id;$('#operation-app').append(option);}if(value.applications.some(app=>app.id===selected))$('#operation-app').value=selected;}
  $('#operation-kind option[value=application]').disabled=!value.application_supported||!desktopOperations.applications.length;
  $('#operation-audit').replaceChildren();for(const item of value.audit||[]){const row=element('div','operation-event');row.append(element('time','',new Date(item.time).toLocaleTimeString()),element('span','',(item.step?item.step+'. ':'')+item.action),element('strong','',item.status));row.dataset.status=item.status;$('#operation-audit').append(row);}
  operationActions();renderOperationSteps();
}
async function openOperations(){renderOperationStatus(await native.operationStatus());showDialog('#operations-dialog');}
function bindOperations(){
  for(const key of ['operations-open','operation-notice-open'])action($('#'+key),openOperations);
  $('#operation-kind').onchange=()=>{renderOperationStatus(desktopOperations.status);};$('#operation-action').onchange=operationFields;
  for(const key of ['Enter','Tab','Escape','Left','Right','Up','Down','Command+A','Command+S']){const option=element('option','',key);option.value=key;$('#operation-key').append(option);}
  action($('#operation-start'),async()=>{const result=await native.startOperations({kind:$('#operation-kind').value,url:$('#operation-url').value,bundle:$('#operation-app').value});if(!result.cancelled){desktopOperations.steps=[];renderOperationStatus(result);$('#operation-feedback').textContent='Session ready. Add steps, then review before running.';}});
  const stop=async()=>{renderOperationStatus(await native.stopOperations());$('#operation-feedback').textContent='Session stopped. Remaining steps were cancelled; actions already sent may finish.';};action($('#operation-stop'),stop);action($('#operation-stop-global'),stop);
  action($('#operation-accessibility'),async()=>{const result=await native.requestAccessibility();$('#operation-feedback').textContent=result.trusted?'Accessibility is granted. Review your app plan before running.':'Enable Pantheon in system Accessibility settings, then reopen this panel to refresh. No app step was sent.';renderOperationStatus(await native.operationStatus());});
  $('#operation-step-form').onsubmit=event=>{event.preventDefault();if(!desktopOperations.status?.active||desktopOperations.status.busy)return;const action=$('#operation-action').value,step={action},argument=$('#operation-arg').value;
    if(action==='navigate')step.url=argument;if(['click','fill'].includes(action))step.selector=argument;if(['fill','type'].includes(action))step.value=$('#operation-value').value;if(action==='button')step.name=argument;if(action==='key')step.key=$('#operation-key').value;if(action==='wait')step.ms=Number($('#operation-ms').value);desktopOperations.steps.push(step);$('#operation-value').value='';renderOperationSteps();};
  action($('#operation-run'),async()=>{const feedback=$('#operation-feedback');feedback.textContent='Review the native plan confirmation. No step runs before approval.';try{const result=await native.runOperations(desktopOperations.steps);feedback.textContent=result.cancelled?'Plan cancelled. No new step was sent.':'Reviewed steps completed. Inspect the browser or selected app.';}catch(error){feedback.textContent=errorText(error);}renderOperationStatus(await native.operationStatus());});
  action($('#operation-clear'),()=>{desktopOperations.steps=[];renderOperationSteps();});
  action($('#operation-preview'),async()=>{const value=await native.operationCapture(false),image=element('img','operation-capture');image.alt='User-requested capture of the approved browser';image.src=value.data;info('Browser capture',image);});
  action($('#operation-save'),async()=>{const result=await native.operationCapture(true);$('#operation-feedback').textContent=result.saved?'Capture saved locally. Nothing was uploaded.':'Capture export cancelled.';});
  native.onOperation?.(renderOperationStatus);
}
