'use strict';
async function refreshUsage(){
  const run=latestRun();if(!run?.task_id){$('#usage-summary').textContent='No calls recorded for this task.';return;}
  const selected=state.selected;const value=await api('/api/usage/details?task_id='+encodeURIComponent(run.task_id));if(selected!==state.selected)return;
  const calls=value.groups.reduce((n,item)=>n+item.calls,0),unknown=value.groups.some(item=>item.input_tokens===null||item.output_tokens===null),unpriced=value.groups.some(item=>item.unpriced);
  const tokens=value.groups.reduce((n,item)=>n+(item.input_tokens||0)+(item.output_tokens||0),0),cost=value.groups.reduce((n,item)=>n+(item.estimated_usd||0),0);
  $('#usage-summary').textContent=calls+' call(s) · '+tokens.toLocaleString()+(unknown?' reported tokens (incomplete)':' tokens')+' · '+(unpriced?'Cost unknown':'$'+cost.toFixed(4)+' estimated');
}
async function loadResultArtifacts(){if(!state.selected||state.tab!=='result')return;const selected=state.selected;const value=await api('/api/desktop/artifacts');if(state.selected!==selected)return;$('#result-artifacts').replaceChildren();for(const item of value.artifacts.filter(item=>item.session_id===selected))$('#result-artifacts').append(artifactCard(item));}
function formField(form,label,value='',type='text'){
  const wrapper=element('label','field',label),input=element(type==='textarea'?'textarea':'input');if(type!=='textarea')input.type=type;else input.rows=6;input.value=value;wrapper.append(input);form.append(wrapper);return input;
}
function formSelect(form,label,options,value){const wrapper=element('label','field',label),input=element('select');for(const [id,name] of options){const option=element('option','',name);option.value=id;input.append(option);}input.value=value;wrapper.append(input);form.append(wrapper);return input;}
function formCheck(form,label,value=false){const wrapper=element('label','check-label'),input=element('input');input.type='checkbox';input.checked=value;wrapper.append(input,document.createTextNode(label));form.append(wrapper);return input;}
async function editCapability(name,item={}){
  const form=element('form','feature-form');const title=formField(form,'Name',item.name||'');title.required=true;
  const description=name==='mcp/servers'?null:formField(form,'Description',item.description||'');
  const instructions=name==='mcp/servers'?null:formField(form,'Instructions',item.instructions||'','textarea');if(instructions)instructions.required=true;
  const roles=formField(form,'Roles (comma separated; leave blank for all)',(item.roles||[]).join(', '));
  const enabled=formCheck(form,'Enabled',item.enabled!==false);let transport,command,args,url,credentialName,credentialValue,allowAgent;
  if(name==='mcp/servers'){
    form.append(element('p','','A stdio server executes a local program on the connected host. Only add a server you trust. Agent tool calls retain the shared approval policies.'));
    allowAgent=formCheck(form,'Allow agents to request this server’s tools',item.allow_agent_calls);transport=formSelect(form,'Transport',[['stdio','Local program (stdio)'],['streamable_http','Remote HTTP'] ],item.transport||'stdio');
    command=formField(form,'Program',item.command||'');args=formField(form,'Arguments (JSON array)',JSON.stringify(item.args||[]));url=formField(form,'Server URL',item.url||'');
    credentialName=formField(form,'Credential environment name (optional)',item.credential_env_var||'');credentialValue=formField(form,'Credential value (leave blank to keep saved value)','','password');
  }
  const status=element('p','',''),save=element('button','primary','Save '+(name==='mcp/servers'?'server':name.slice(0,-1)));form.append(status,save);
  form.onsubmit=event=>{event.preventDefault();(async()=>{const body={name:title.value,roles:roles.value.split(',').map(x=>x.trim()).filter(Boolean),enabled:enabled.checked};if(instructions)Object.assign(body,{description:description.value,instructions:instructions.value});else Object.assign(body,{transport:transport.value,command:command.value,args:JSON.parse(args.value||'[]'),url:url.value,credential_env_var:credentialName.value,credential_value:credentialValue.value,allow_agent_calls:allowAgent.checked,cwd:item.cwd||'',env:item.env||{},headers_env:item.headers_env||{},bearer_token_env_var:item.bearer_token_env_var||'',tool_policies:item.tool_policies||{},startup_timeout_seconds:item.startup_timeout_seconds||15,tool_timeout_seconds:item.tool_timeout_seconds||60});await api('/api/'+name+(item.id?'/'+item.id:''),body,item.id?'PUT':'POST');closeDialog('#info-dialog');await loadCapability(name);})().catch(error=>{status.textContent=errorText(error);});};
  info((item.id?'Edit ':'Add ')+(name==='mcp/servers'?'MCP server':name.slice(0,-1)),form);
}
async function editChannel(item){
  const form=element('form','feature-form');form.append(element('p','','Incoming messages need a reachable HTTPS callback on your server. Saving is local; no test message is sent.'));
  const enabled=formCheck(form,'Enable incoming requests',item.enabled),reply=formCheck(form,'Allow replies to approved users and channels',item.auto_reply);
  const users=formField(form,'Allowed user IDs (comma separated)',(item.users||[]).join(',')),channels=formField(form,'Allowed channel IDs (comma separated)',(item.channels||[]).join(','));
  const account=formField(form,'Team / application ID',item.account_id||''),publicKey=item.id==='discord'?formField(form,'Application Ed25519 public key',item.public_key||''):null;
  const secrets={};for(const key of item.id==='telegram'?['bot_token','secret_token']:item.id==='slack'?['bot_token','signing_secret']:[]){secrets[key]=formField(form,key.replaceAll('_',' ')+' (leave blank to keep saved value)','','password');}
  if(item.id==='webhook'){form.replaceChildren(element('p','','Webhooks receive authenticated requests. Enabling generates a token; keep it private.'));const enable=formCheck(form,'Enable webhook',item.enabled),save=element('button','primary','Save webhook');form.append(save);form.onsubmit=event=>{event.preventDefault();api('/api/channels/webhook/config',{enabled:enable.checked}).then(value=>{const panel=element('div');panel.append(element('p','','Endpoint: '+value.endpoint),element('p','','Token is shown only here. Store it privately.'),element('pre','',value.token||'(unchanged)'));info('Webhook saved',panel);}).catch(error=>toast(errorText(error)));};info('Configure webhook',form);return;}
  const status=element('p'),save=element('button','primary','Save connection');form.append(element('small','','Callback: '+item.endpoint),status,save);
  form.onsubmit=event=>{event.preventDefault();const secretValues=Object.fromEntries(Object.entries(secrets).filter(([,input])=>input.value).map(([key,input])=>[key,input.value]));const ids=input=>input.value.split(',').map(x=>x.trim()).filter(Boolean);api('/api/channels/'+item.id+'/config',{config:{enabled:enabled.checked,auto_reply:reply.checked,users:ids(users),channels:ids(channels),account_id:account.value,public_key:publicKey?.value||'',mode:item.mode||'auto'},secrets:secretValues}).then(async()=>{closeDialog('#info-dialog');await loadCapability('channels');}).catch(error=>{status.textContent=errorText(error);});};info('Configure '+item.name,form);
}
async function loadMedia(target){
  const value=await api('/api/media');target.append(element('p','',value.note));
  const form=element('form','feature-form'),settings=value.settings;
  const provider=formSelect(form,'Images / PDF understanding provider',[['openai','OpenAI'],['anthropic','Anthropic']],settings.vision_provider),vision=formField(form,'Understanding model',settings.vision_model),image=formField(form,'Image generation model (OpenAI)',settings.image_model),audio=formField(form,'Transcription model (OpenAI)',settings.audio_model);
  const save=element('button','primary','Save media models');form.append(save);form.onsubmit=event=>{event.preventDefault();api('/api/media/settings',{vision_provider:provider.value,vision_model:vision.value,image_model:image.value,audio_model:audio.value}).then(()=>toast('Media models saved.')).catch(error=>toast(errorText(error)));};target.append(form);
  const prompt=element('textarea');prompt.rows=3;prompt.placeholder='Describe the image you want to create…';prompt.setAttribute('aria-label','Image prompt');const generate=element('button','','Generate image');action(generate,async()=>{if(!prompt.value.trim())throw new Error('Describe an image first.');if(!await confirmChoice('Generate an image?','This sends your prompt to OpenAI and uses your shared budget.','Generate image'))return;generate.disabled=true;try{const item=await api('/api/media/generate',{prompt:prompt.value});await showMediaOutput(item);}finally{generate.disabled=false;}});target.append(element('h3','','Create an image'),prompt,generate);
  const upload=element('button','','Choose audio to transcribe');action(upload,async()=>{const files=await native.pickFiles('audio');for(const file of files){const item=await api('/api/desktop/attachments',file);if(!item.type.startsWith('audio/'))throw new Error('Choose an audio file for transcription.');if(!await confirmChoice('Transcribe audio?','This sends the selected audio to OpenAI and uses your shared budget.','Transcribe'))return;const result=await api('/api/media/transcribe',{id:item.id});const panel=element('div');panel.append(markdown(result.text));const insert=element('button','primary','Use in task draft');action(insert,async()=>{if(!state.selected)await newTask();$('#prompt').value=result.text;await patchSession({draft:result.text});closeDialog('#info-dialog');setView('work');});panel.append(insert);info('Transcription',panel);}});target.append(element('h3','','Audio transcription'),upload);
}
async function showMediaOutput(item){const panel=element('div');if(item.type.startsWith('image/')){const image=element('img','generated-media');image.alt='Generated image';image.src=await native.mediaFile(item.id,false);panel.append(image);}const save=element('button','primary','Save output…');action(save,()=>native.mediaFile(item.id,true));panel.append(save);info('Generated output',panel);}

async function resolveDraftConflict(id){
  clearTimeout(state.draftTimer);clearTimeout(state.editorTimer);await state.patchQueue;
  const latest=await api('/api/desktop/sessions/'+id);const local=id===state.selected?{draft:$('#prompt').value,editor_draft:state.file?{...state.file,content:$('#file-editor').value}:latest.editor_draft}:{draft:currentSession()?.draft||''};
  const panel=element('div');panel.append(element('p','','Another window changed this task. Review both drafts before choosing.'),element('h3','','Saved draft'),element('pre','',latest.draft||'(empty)'),element('h3','','Your local draft'),element('pre','',local.draft||'(empty)'));
  if(local.editor_draft?.content!==latest.editor_draft?.content)panel.append(element('p','','The editor draft also differs. Keeping your draft will replace the saved editor draft; project files remain unchanged.'));
  const keep=element('button','primary','Keep my draft'),reload=element('button','','Load saved draft');
  action(keep,async()=>{const index=state.sessions.findIndex(item=>item.id===id);if(index>=0)state.sessions[index]=latest;if(id===state.selected)state.detail=latest;await patchSession(local,id);notice('');closeDialog('#info-dialog');});
  action(reload,async()=>{state.dirty.delete(id);if(id===state.selected){state.detail=latest;$('#prompt').value=latest.draft||'';if(latest.editor_draft?.path){state.file={path:latest.editor_draft.path,hash:latest.editor_draft.hash};$('#file-editor').value=latest.editor_draft.content;}}try{localStorage.removeItem('pantheon-draft:'+state.info.workspace.workspace+':'+id);}catch{}notice('');closeDialog('#info-dialog');await refresh();});
  panel.append(keep,reload);info('Resolve draft conflict',panel);
}

async function manageConnection(){
  const provider=providerChoice(),refs=await api('/api/connections/'+provider.id+'/references'),panel=element('div');
  panel.append(element('p','','Saved roles: '+(refs.saved_roles.join(', ')||'none')),element('p','','Conversations using this provider: '+refs.chats.length),element('p','','Media references: '+(refs.media.join(', ')||'none')),element('p','','Assignments are kept. Disabled or removed connections cannot run until configured again.'));
  const erase=formCheck(panel,'Also delete the saved API key when removing',false),toggle=element('button','',provider.enabled?'Disable connection':'Enable connection'),remove=element('button','','Remove saved connection');
  const change=async actionName=>{state.setup=await api('/api/connections/'+provider.id+'/manage',{action:actionName,acknowledge_references:true,delete_saved_key:actionName==='remove'&&erase.checked});closeDialog('#info-dialog');renderConnectionSummary();fillProvider();};
  action(toggle,()=>change(provider.enabled?'disable':'enable'));action(remove,()=>change('remove'));panel.append(toggle,remove);info('Manage '+provider.label,panel);
}
async function editToolPolicies(item){
  const panel=element('div');panel.append(element('p','','Choose which tools agents may request. Ask requires a separate approval during execution.'));
  for(const tool of item.tools||[]){const policy=item.tool_policies?.[tool.name]||{},form=element('form','feature-form');form.append(element('strong','',tool.name));const enabled=formCheck(form,'Enabled',policy.enabled!==false),roles=formField(form,'Roles (comma separated)',(policy.roles||item.roles||[]).join(', ')),approval=formSelect(form,'Approval',[['ask','Ask every time'],['auto','Allow automatically']],policy.approval||'ask'),save=element('button','','Save tool policy'),status=element('p');form.append(save,status);form.onsubmit=event=>{event.preventDefault();api('/api/mcp/servers/'+item.id+'/tools/'+encodeURIComponent(tool.name)+'/policy',{enabled:enabled.checked,roles:roles.value.split(',').map(x=>x.trim()).filter(Boolean),approval:approval.value},'PUT').then(()=>{status.textContent='Policy saved.';}).catch(error=>{status.textContent=errorText(error);});};panel.append(form);}
  if(!item.tools?.length)panel.append(element('p','','Inspect the server first to discover tools.'));info('Tool policies',panel);
}
