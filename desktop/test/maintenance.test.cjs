'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const path=require('node:path');
const os=require('node:os');
const {MaintenanceManager}=require('../maintenance.cjs');
async function fixture(t,runs=[]){
  const root=await fs.mkdtemp(path.join(os.tmpdir(),'pantheon-maintenance-'));t.after(()=>fs.rm(root,{recursive:true,force:true}));
  const events=[],backend={owned:true,remote:false,workspace:root,env:{},request:async()=>({runs}),stop:async()=>events.push('stop')};
  const manager=new MaintenanceManager({directory:path.join(root,'backups'),command:{executable:'unused',args:[]},flush:async()=>events.push('flush'),reconnect:async()=>events.push('reconnect'),onChange:(_backend,value)=>events.push(value.phase)});
  return {root,backend,manager,events};
}
test('maintenance does not stop remote/reused services or active tasks',async t=>{
  const {manager,backend,events}=await fixture(t,[{status:'running'}]);
  await assert.rejects(manager.perform({...backend,owned:false},'backup','unused'),/owned by Desktop/);
  await assert.rejects(manager.perform({...backend,remote:true},'backup','unused'),/owned by Desktop/);
  await assert.rejects(manager.perform(backend,'backup','unused'),/active tasks/);assert.equal(events.includes('stop'),false);assert.equal(backend.maintenance,false);assert.equal(manager.busy.size,0);
});
test('a failed offline operation always reconnects the workspace and clears its busy state',async t=>{
  const {manager,backend,events}=await fixture(t);manager.offline=async()=>{throw new Error('Fixture archive rejected');};
  await assert.rejects(manager.perform(backend,'restore','unused'),/archive rejected/);
  assert.ok(events.indexOf('flush')<events.indexOf('stop'));assert.ok(events.indexOf('stop')<events.indexOf('reconnect'));assert.equal(events.at(-1),'failed');assert.equal(backend.maintenance,false);assert.equal(manager.busy.size,0);
});
test('backup history is scoped to the owning project and exposes no arbitrary reveal paths',async t=>{
  const {manager,backend,root}=await fixture(t),file=path.join(root,'private-backup.zip');
  manager.offline=async()=>{await fs.writeFile(file,'fixture archive');return {saved:true};};
  const saved=await manager.perform(backend,'backup',file);const items=await manager.list(root);
  assert.equal(items.length,1);assert.equal(items[0].includes_secrets,false);assert.equal(items[0].path,undefined);
  assert.equal(await manager.revealFile(saved.backup_id,root),file);await assert.rejects(manager.revealFile(saved.backup_id,root+'-other'),/belonging/);
});
