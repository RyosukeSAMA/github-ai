'use strict';
const fs=require('node:fs/promises');const path=require('node:path');const {createHash,randomUUID}=require('node:crypto');
const {remoteURL,apiPath}=require('./backend.cjs');
const id=()=>randomUUID().replaceAll('-','');
const editable=new Set(['draft','title','mode','pinned','archived']);
function identityKey(value){return createHash('sha256').update(JSON.stringify([remoteURL(value.origin),value.username,value.workspace])).digest('hex');}
function cacheKey(target){const url=new URL(target,'https://offline.invalid');return url.pathname;}
function storageKey(target){const url=new URL(target,'https://offline.invalid');url.searchParams.sort();return url.pathname+url.search;}
function cacheable(target){return /^\/api\/desktop\/(sessions|artifacts)(\/[a-f0-9]{32})?$/.test(cacheKey(target))||/^\/api\/(setup\/status|roles|tasks|usage\/details|budgets)$/.test(cacheKey(target));}
function cacheValue(target,value){
  const copy=structuredClone(value);
  if(cacheKey(target)==='/api/setup/status'){
    const scrub=object=>{for(const key of ['api_key','masked_key','base_url','config_path','env_path','password','token'])delete object[key];};
    scrub(copy);for(const item of copy.providers||[])scrub(item);for(const item of copy.role_statuses||[])scrub(item);
  }return copy;
}
class OfflineWorkspace{
  constructor({directory,identity,onChange=()=>{}}){this.directory=directory;this.identity=identity;this.onChange=onChange;this.chain=Promise.resolve();this.offline=false;this.busy=false;this.data={format:1,identity,enabled:false,cache:{},queue:{},recovered:[]};}
  serial(callback){const pending=this.chain.then(callback);this.chain=pending.catch(()=>{});return pending;}
  async load(){try{const file=path.join(this.directory,'workspace.json');if((await fs.stat(file)).size>32*1024*1024)throw new Error('Offline cache is too large.');const data=JSON.parse(await fs.readFile(file,'utf8'));if(data.format!==1||identityKey(data.identity)!==identityKey(this.identity)||!data.cache||!data.queue)throw new Error('Offline workspace identity does not match.');this.data=data;}catch(error){if(error.code!=='ENOENT')throw error;}return this;}
  status(){const queue=Object.values(this.data.queue);return {enabled:this.data.enabled,offline:this.offline,busy:this.busy,pending:queue.length,conflicts:queue.filter(item=>item.conflict).map(item=>({id:item.session_id,title:item.local.title,local_draft:item.local.draft||'',remote_draft:item.conflict.current?.draft||'',remote_missing:!item.conflict.current})),cache_error:this.cacheError||null,last_saved:this.data.updated_at||null,origin:this.identity.origin,username:this.identity.username,recovered:structuredClone(this.data.recovered||[])};}
  changed(){this.onChange(this.status());}
  async save(){
    let raw=JSON.stringify(this.data);const candidates=Object.entries(this.data.cache).filter(([key])=>!['/api/desktop/sessions','/api/setup/status'].includes(key)).sort((a,b)=>a[1].at-b[1].at);
    while((raw.length>20*1024*1024||Object.keys(this.data.cache).length>200)&&candidates.length){delete this.data.cache[candidates.shift()[0]];raw=JSON.stringify(this.data);}
    if(raw.length>30*1024*1024)throw new Error('Offline cache reached its size limit. Sync drafts before adding more.');
    await fs.mkdir(this.directory,{recursive:true,mode:0o700});if((await fs.lstat(this.directory)).isSymbolicLink())throw new Error('Offline cache cannot be a symbolic link.');
    const temporary=path.join(this.directory,id()+'.tmp');await fs.writeFile(temporary,raw,{mode:0o600});await fs.rename(temporary,path.join(this.directory,'workspace.json'));
  }
  async enable(backend){return this.serial(async()=>{let capability;try{capability=await backend.request('/api/desktop/sync');}catch(error){if(error.status===404||error instanceof SyntaxError)throw new Error('Update the remote host to the current Desktop source before enabling offline drafts.');throw error;}if(capability.version!==1||capability.execution!==false||capability.revision!=='draft-hash-v1')throw new Error('Update the remote host before enabling offline drafts.');this.data.info={...backend.info};await this.cache('/api/desktop/sessions',await backend.request('/api/desktop/sessions'));await this.cache('/api/setup/status',await backend.request('/api/setup/status'));this.data.enabled=true;this.offline=false;try{await this.save();}catch{this.data.enabled=false;throw new Error('Could not save the private offline cache.');}this.changed();});}
  async disable(){return this.serial(async()=>{if(Object.keys(this.data.queue).length)throw new Error('Sync or resolve pending drafts before disabling offline storage.');await fs.rm(this.directory,{recursive:true,force:true});this.data.enabled=false;this.data.cache={};this.changed();});}
  session(sessionId){const pending=this.data.queue[sessionId];if(pending)return structuredClone(pending.local);const detail=this.data.cache['/api/desktop/sessions/'+sessionId]?.value;return structuredClone(detail||this.data.cache['/api/desktop/sessions']?.value.sessions.find(item=>item.id===sessionId)||null);}
  overlay(target,value){
    const key=cacheKey(target),copy=structuredClone(value);
    if(key==='/api/desktop/sessions'){
      const sessions=new Map(copy.sessions.map(item=>[item.id,item]));for(const item of Object.values(this.data.queue))sessions.set(item.session_id,item.local);
      copy.sessions=[...sessions.values()].map(({messages,editor_draft,...item})=>({...item,message_count:messages?.length||item.message_count||0,offline_cached:this.offline}));copy.runs=copy.runs.map(item=>({...item,offline_cached:this.offline}));
    }else if(/^\/api\/desktop\/sessions\/[a-f0-9]{32}$/.test(key)){const pending=this.data.queue[key.split('/').at(-1)];if(pending)return {...structuredClone(pending.local),messages:copy.messages||pending.local.messages};}
    return copy;
  }
  async cache(target,value){const key=storageKey(target);if(!cacheable(target))return;value=cacheValue(target,value);const old=this.data.cache[key]?.value;if(JSON.stringify(old)===JSON.stringify(value))return;this.data.cache[key]={at:Date.now(),value:structuredClone(value)};this.data.updated_at=Date.now();await this.save();}
  async accepted(operation,value){delete this.data.queue[operation.session_id];await this.cache('/api/desktop/sessions/'+operation.session_id,value);const list=this.data.cache['/api/desktop/sessions']?.value;if(list){list.sessions=[value,...list.sessions.filter(item=>item.id!==value.id)];}await this.save();}
  wire(operation){return {operation_id:operation.operation_id,session_id:operation.session_id,expected_version:operation.expected_version,expected_revision:operation.expected_revision??null,create:operation.create,changes:operation.changes};}
  async send(backend,operation){
    try{const value=await backend.request('/api/desktop/sync',{method:'POST',body:this.wire(operation)},AbortSignal.timeout(10000));await this.accepted(operation,value);return value;}
    catch(error){if(error.status===409||error.status===404){operation.conflict={current:error.detail?.current||null};await this.save();this.changed();return operation.local;}throw error;}
  }
  validate(changes){if(!changes||Object.keys(changes).some(key=>!editable.has(key)))throw new Error('Offline mode saves text drafts and task metadata only. Files, attachments, model changes and execution require a connection.');for(const key of ['draft','title','mode'])if(changes[key]!==undefined&&(typeof changes[key]!=='string'||changes[key].length>(key==='draft'?24000:200)))throw new Error('Draft metadata is invalid.');if(changes.mode!==undefined&&!['auto','multi','role:hermes','role:hephaestus','role:athena','role:apollo','role:chronos'].includes(changes.mode))throw new Error('Unsupported task mode.');for(const key of ['pinned','archived'])if(changes[key]!==undefined&&typeof changes[key]!=='boolean')throw new Error('Task flags must be true or false.');}
  async edit(backend,sessionId,body,create=false){
    const {expected_version,...changes}=body;this.validate(changes);const previous=this.data.queue[sessionId],original=create?{id:sessionId,title:'New task',draft:'',mode:'auto',overrides:{},messages:[],pinned:false,archived:false,createdAt:Date.now(),updatedAt:Date.now(),desktop_version:0}:this.session(sessionId);
    if(!original)throw new Error('This task is not cached. Reconnect before editing it.');if(!create&&expected_version!==original.desktop_version)throw new Error('This offline draft changed in another window. Reload before editing.');
    if(!previous&&Object.keys(this.data.queue).length>=100)throw new Error('Sync pending drafts before creating more.');
    const operation={operation_id:id(),session_id:sessionId,expected_version:previous?.expected_version??original.desktop_version,expected_revision:previous?.expected_revision??original.sync_revision??null,create:previous?.create??create,changes:{...previous?.changes,...changes},local:{...original,...changes,desktop_version:original.desktop_version+1,updatedAt:Date.now(),offline_pending:true}};
    this.data.queue[sessionId]=operation;try{await this.save();}catch{if(previous)this.data.queue[sessionId]=previous;else delete this.data.queue[sessionId];throw new Error('The local draft could not be saved. Keep this window open and copy your text before retrying.');}let value=operation.local;
    if(!this.offline&&!backend.offlineOnly){try{value=await this.send(backend,operation);}catch(error){if(error.status&&![401,403,502,503,504].includes(error.status)){if(previous)this.data.queue[sessionId]=previous;else delete this.data.queue[sessionId];await this.save();throw error;}this.offline=true;}}
    this.changed();return value;
  }
  request(backend,target,options={}){return this.serial(async()=>{
    target=apiPath(target);const method=options.method||'GET',key=cacheKey(target);
    if(method==='POST'&&key==='/api/desktop/sessions')return this.edit(backend,id(),options.body||{},true);
    if(method==='PATCH'&&/^\/api\/desktop\/sessions\/[a-f0-9]{32}$/.test(key)&&Object.keys(options.body||{}).every(key=>key==='expected_version'||editable.has(key)))return this.edit(backend,key.split('/').at(-1),options.body||{});
    if(this.offline||backend.offlineOnly){
      if(method!=='GET')throw new Error('Offline: this action requires the remote host. No task or message was sent.');
      if(key==='/api/desktop/search'){
        const query=(new URL(target,'https://offline.invalid').searchParams.get('query')||'').slice(0,200).toLowerCase();
        const sessions=this.overlay('/api/desktop/sessions',this.data.cache['/api/desktop/sessions']?.value||{sessions:[],runs:[]}).sessions.filter(item=>{const detail=this.session(item.id)||item;return [item.title,item.draft,...(detail.messages||[]).map(message=>message.text)].join('\n').toLowerCase().includes(query);});
        const artifacts=(this.data.cache['/api/desktop/artifacts']?.value.artifacts||[]).filter(item=>[item.title,item.filename,this.data.cache['/api/desktop/artifacts/'+item.id]?.value.content].join('\n').toLowerCase().includes(query));return {sessions,artifacts};
      }
      if(/^\/api\/desktop\/sessions\/[a-f0-9]{32}$/.test(key)){
        const sessionId=key.split('/').at(-1),local=this.session(sessionId);if(local)return {...local,messages:local.messages||[],offline_history_unavailable:!local.messages&&!!local.message_count};
      }
      const cached=this.data.cache[storageKey(target)];if(!cacheable(target)||!cached)throw new Error('This data is not cached. Sign in and reconnect to its remote host.');return this.overlay(target,cached.value);
    }
    let value;try{value=await backend.request(target,options,AbortSignal.timeout(method==='GET'?5000:30000));}
    catch(error){if(method!=='GET'||error.status&&![401,502,503,504].includes(error.status))throw error;this.offline=true;this.changed();const cached=this.data.cache[storageKey(target)];if(!cached||!cacheable(target))throw error;return this.overlay(target,cached.value);}
    if(method==='GET')try{await this.cache(target,value);this.cacheError=null;}catch{this.cacheError='Could not save the private offline cache. Check free disk space before relying on offline edits.';this.changed();}
    return this.overlay(target,value);
  });}
  sync(backend){return this.serial(async()=>{
    if(backend.offlineOnly)throw new Error('Sign in to the original remote server before syncing.');this.busy=true;this.changed();let applied=0;
    try{const identity=await backend.identity();if(identity.workspace!==this.identity.workspace)throw new Error('Remote project changed. Reconnect to the original project.');this.offline=false;
      for(const operation of Object.values(this.data.queue)){if(operation.conflict)continue;try{await this.send(backend,operation);if(!this.data.queue[operation.session_id])applied++;}catch(error){if(!error.status||[401,502,503,504].includes(error.status))this.offline=true;throw error;}}
      await this.save();return {applied};
    }finally{this.busy=false;this.changed();}
  });}
  resolve(sessionId,choice){return this.serial(async()=>{const operation=this.data.queue[sessionId];if(!operation?.conflict||!['local','remote'].includes(choice))throw new Error('Choose a pending conflict and a draft to retain.');const remote=operation.conflict.current;
    if(choice==='remote'){this.data.recovered=[{title:operation.local.title,draft:operation.local.draft||'',created:Date.now()},...this.data.recovered].slice(0,20);delete this.data.queue[sessionId];if(remote)await this.accepted({session_id:sessionId},{...remote,messages:this.data.cache['/api/desktop/sessions/'+sessionId]?.value.messages||[]});else{delete this.data.cache['/api/desktop/sessions/'+sessionId];const list=this.data.cache['/api/desktop/sessions']?.value;if(list)list.sessions=list.sessions.filter(item=>item.id!==sessionId);}}
    else{operation.operation_id=id();operation.expected_version=remote?.desktop_version||0;operation.expected_revision=remote?.sync_revision??null;operation.create=!remote;delete operation.conflict;}
    await this.save();this.changed();return this.status();
  });}
}
async function offlineList(root){const result=[];await fs.mkdir(root,{recursive:true,mode:0o700});for(const name of await fs.readdir(root)){if(!/^[a-f0-9]{64}$/.test(name))continue;try{const file=path.join(root,name,'workspace.json');if((await fs.stat(file)).size>32*1024*1024)continue;const value=JSON.parse(await fs.readFile(file,'utf8'));if(value.enabled&&identityKey(value.identity)===name)result.push({id:name,origin:value.identity.origin,username:value.identity.username,workspace_name:value.info.workspace_name,pending:Object.keys(value.queue||{}).length});}catch{}}
  return result;
}
module.exports={OfflineWorkspace,identityKey,offlineList,cacheable};
