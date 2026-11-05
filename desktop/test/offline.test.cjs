'use strict';
const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs/promises');const os=require('node:os');const path=require('node:path');
const {OfflineWorkspace,identityKey,offlineList}=require('../offline.cjs');
async function fixture(t){
  const root=await fs.mkdtemp(path.join(os.tmpdir(),'pantheon-offline-'));t.after(()=>fs.rm(root,{recursive:true,force:true}));
  const identity={origin:'https://fixture.invalid',username:'user',workspace:'/srv/project'},events=[],session={id:'a'.repeat(32),title:'Remote task',draft:'Original draft',mode:'auto',messages:[],desktop_version:0};let broken=false,lost=false,requests=0,applied=0;const done=new Map();
  const backend={info:{workspace:identity.workspace,workspace_name:'Project'},remote:true,identity:async()=>{if(broken)throw new Error('Offline');return backend.info;},request:async(target,options={})=>{
    requests++;if(broken)throw new Error('Offline');if(target==='/api/desktop/sync'){
      if(!options.method)return {version:1,execution:false,revision:'draft-hash-v1'};const body=options.body;if(done.has(body.operation_id))return structuredClone(session);
      if(body.expected_version!==session.desktop_version&&!body.create){const error=new Error('Conflict');error.status=409;error.detail={current:structuredClone(session)};throw error;}
      Object.assign(session,body.changes,{desktop_version:session.desktop_version+1,id:body.session_id});done.set(body.operation_id,true);applied++;if(lost){lost=false;throw new Error('Response lost after application');}return structuredClone(session);
    }
    if(target==='/api/setup/status')return {providers:[],role_statuses:[]};if(target==='/api/desktop/sessions')return {sessions:[structuredClone(session)],runs:[]};if(target.startsWith('/api/desktop/sessions/'))return structuredClone(session);if(target.startsWith('/api/usage/details'))return {task:target};throw new Error('Unexpected request '+target);
  }};
  const store=await new OfflineWorkspace({directory:path.join(root,identityKey(identity)),identity,onChange:value=>events.push(value)}).load();await store.enable(backend);await store.request(backend,'/api/desktop/sessions');await store.request(backend,'/api/desktop/sessions/'+session.id);
  return {root,identity,store,backend,session,events,break:()=>{broken=true;},recover:()=>{broken=false;},lose:()=>{lost=true;},stats:()=>({requests,applied})};
}
test('opted-in private cache reopens only for its bound server/account/project',async t=>{
  const f=await fixture(t);f.break();assert.equal((await f.store.request(f.backend,'/api/desktop/sessions')).sessions.length,1);assert.equal(f.store.status().offline,true);
  const reopened=await new OfflineWorkspace({directory:f.store.directory,identity:f.identity}).load();reopened.offline=true;assert.equal((await reopened.request(f.backend,'/api/desktop/sessions/'+f.session.id)).draft,'Original draft');
  assert.equal((await offlineList(f.root)).length,1);if(process.platform!=='win32')assert.equal((await fs.stat(path.join(f.store.directory,'workspace.json'))).mode&0o077,0);
  await assert.rejects(new OfflineWorkspace({directory:f.store.directory,identity:{...f.identity,username:'another user'}}).load(),/identity/);
});
test('offline edits coalesce, stay local after reconnection and sync only explicitly',async t=>{
  const f=await fixture(t);f.break();await f.store.request(f.backend,'/api/desktop/sessions');const first=await f.store.request(f.backend,'/api/desktop/sessions/'+f.session.id,{method:'PATCH',body:{expected_version:0,draft:'First local'}});
  await f.store.request(f.backend,'/api/desktop/sessions/'+f.session.id,{method:'PATCH',body:{expected_version:first.desktop_version,draft:'Final local'}});assert.equal(f.store.status().pending,1);assert.equal(f.session.draft,'Original draft');f.recover();await f.store.request(f.backend,'/api/desktop/sessions');assert.equal(f.session.draft,'Original draft');
  const result=await f.store.sync(f.backend);assert.equal(result.applied,1);assert.equal(f.session.draft,'Final local');assert.equal(f.store.status().pending,0);assert.equal(f.stats().applied,1);
});
test('a lost response retries the identical operation without duplicated mutation',async t=>{
  const f=await fixture(t);f.lose();await f.store.request(f.backend,'/api/desktop/sessions/'+f.session.id,{method:'PATCH',body:{expected_version:0,draft:'Already applied'}});assert.equal(f.store.status().pending,1);assert.equal(f.stats().applied,1);await f.store.sync(f.backend);assert.equal(f.stats().applied,1);assert.equal(f.store.status().pending,0);
});
test('other-device conflicts remain for review and require another explicit sync',async t=>{
  const f=await fixture(t);f.break();await f.store.request(f.backend,'/api/desktop/sessions');await f.store.request(f.backend,'/api/desktop/sessions/'+f.session.id,{method:'PATCH',body:{expected_version:0,draft:'Local choice'}});f.session.draft='Other device';f.session.desktop_version++;f.recover();await f.store.sync(f.backend);assert.equal(f.store.status().conflicts.length,1);assert.equal(f.session.draft,'Other device');await f.store.resolve(f.session.id,'local');assert.equal(f.session.draft,'Other device');await f.store.sync(f.backend);assert.equal(f.session.draft,'Local choice');
});
test('discarding a local conflict retains a recoverable copy and never executes',async t=>{
  const f=await fixture(t);f.break();await f.store.request(f.backend,'/api/desktop/sessions');await f.store.request(f.backend,'/api/desktop/sessions/'+f.session.id,{method:'PATCH',body:{expected_version:0,draft:'Keep recovery copy'}});f.session.desktop_version++;f.recover();await f.store.sync(f.backend);await f.store.resolve(f.session.id,'remote');assert.equal(f.store.status().pending,0);assert.equal(f.store.data.recovered[0].draft,'Keep recovery copy');assert.equal(f.stats().applied,0);
});
test('offline actions cannot replay execution, messages, files or model configuration',async t=>{
  const f=await fixture(t);f.break();await f.store.request(f.backend,'/api/desktop/sessions');const before=f.stats().requests;
  for(const target of ['/api/desktop/sessions/'+f.session.id+'/runs','/api/connections/deepseek','/api/desktop/reviews'])await assert.rejects(f.store.request(f.backend,target,{method:'POST',body:{}}),/requires/);
  await assert.rejects(f.store.request(f.backend,'/api/desktop/sessions/'+f.session.id,{method:'PATCH',body:{expected_version:0,overrides:{}}}),/requires/);assert.equal(f.stats().requests,before);
});
test('per-task usage caches cannot be mistaken for another task and pending edits cannot be disabled',async t=>{
  const f=await fixture(t);await f.store.request(f.backend,'/api/usage/details?task_id=one');await f.store.request(f.backend,'/api/usage/details?task_id=two');f.break();await f.store.request(f.backend,'/api/desktop/sessions');assert.equal((await f.store.request(f.backend,'/api/usage/details?task_id=one')).task,'/api/usage/details?task_id=one');await f.store.request(f.backend,'/api/desktop/sessions/'+f.session.id,{method:'PATCH',body:{expected_version:0,draft:'Pending'}});await assert.rejects(f.store.disable(),/pending/);
});

test('offline setup cache excludes connection keys and credential-bearing endpoint URLs',async t=>{
  const f=await fixture(t);await f.store.cache('/api/setup/status',{api_key:'SENTINEL-KEY',base_url:'https://example.com/token-SENTINEL',providers:[{id:'fixture',masked_key:'SENTINEL-MASK',api_key:'SENTINEL-RAW',base_url:'https://secret.invalid',key_configured:true}],role_statuses:[]});const raw=await fs.readFile(path.join(f.store.directory,'workspace.json'),'utf8');assert.ok(!raw.includes('SENTINEL'));assert.equal(f.store.data.cache['/api/setup/status'].value.providers[0].key_configured,true);
});

test('cache disk errors do not pretend a live service went offline and unsaved edits are rejected',async t=>{
  const f=await fixture(t);f.session.title='Fresh live title';f.store.save=async()=>{throw new Error('Disk full');};const result=await f.store.request(f.backend,'/api/desktop/sessions');assert.equal(result.sessions[0].title,'Fresh live title');assert.equal(f.store.status().offline,false);assert.match(f.store.status().cache_error,/free disk/);f.store.offline=true;await assert.rejects(f.store.request(f.backend,'/api/desktop/sessions/'+f.session.id,{method:'PATCH',body:{expected_version:0,draft:'Not persisted'}}),/could not be saved/);assert.equal(f.store.status().pending,0);
});

test('new offline tasks reopen and cached search finds their unsent drafts',async t=>{
 const f=await fixture(t);f.break();await f.store.request(f.backend,'/api/desktop/sessions');const created=await f.store.request(f.backend,'/api/desktop/sessions',{method:'POST',body:{title:'Offline-only task'}});const changed=await f.store.request(f.backend,'/api/desktop/sessions/'+created.id,{method:'PATCH',body:{expected_version:created.desktop_version,draft:'Unique offline note'}});assert.equal((await f.store.request(f.backend,'/api/desktop/sessions/'+created.id)).draft,changed.draft);const reopened=await new OfflineWorkspace({directory:f.store.directory,identity:f.identity}).load();reopened.offline=true;assert.equal((await reopened.request(f.backend,'/api/desktop/search?query=Unique')).sessions[0].id,created.id);assert.equal(f.stats().applied,0);
});
test('offline wrapper retains the native API proxy boundary',async t=>{
 const f=await fixture(t);await assert.rejects(f.store.request(f.backend,'https://foreign.invalid/api/desktop/sessions'),/Invalid API path/);assert.equal(f.store.status().offline,false);
});

test('older remote hosts give a source-upgrade instruction before enabling the cache',async t=>{
 const f=await fixture(t);await f.store.disable();f.backend.request=async()=>{const error=new Error('Not found');error.status=404;throw error;};await assert.rejects(f.store.enable(f.backend),/Update the remote host/);assert.equal(f.store.status().enabled,false);
});
