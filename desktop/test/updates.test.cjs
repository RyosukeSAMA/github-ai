'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const path=require('node:path');
const os=require('node:os');
const {createHash}=require('node:crypto');
const {UpdateManager,assetURL}=require('../updates.cjs');
const {selectRelease}=require('../releases.cjs');
const data=Buffer.from('A verified installer fixture.');
const digest=createHash('sha256').update(data).digest('hex');
const url='https://github.com/RyosukeSAMA/github-ai/releases/download/v0.6.0/Pantheon-0.6.0-mac-arm64.dmg';
const release=()=>({tag_name:'v0.6.0',draft:false,prerelease:false,assets:[{id:17,name:'Pantheon-0.6.0-mac-arm64.dmg',size:data.length,browser_download_url:url,digest:'sha256:'+digest}]});
async function fixture(t,custom){
  const directory=await fs.mkdtemp(path.join(os.tmpdir(),'pantheon-updates-'));t.after(()=>fs.rm(directory,{recursive:true,force:true}));
  const releases=[release()],events=[],requests=[];
  const manager=new UpdateManager({directory,version:'0.5.0-beta.16',platform:'darwin',arch:'arm64',onChange:value=>events.push(value),fetchImpl:async(value,options)=>{requests.push(value);if(value.startsWith('https://api.github.com/'))return new Response(JSON.stringify(releases));return custom?custom(value,options):new Response(data);}});
  await manager.check('beta');return {manager,releases,events,requests,directory};
}
test('channels select the newest compatible release, skip drafts and preserve stable defaults',()=>{
  const stable=release(),beta={...release(),tag_name:'v0.7.0-beta.1',prerelease:true};
  assert.equal(selectRelease([beta,stable],'0.5.0','darwin','arm64').latest,'v0.6.0');
  assert.equal(selectRelease([stable,beta],'0.5.0','darwin','arm64','beta').latest,'v0.7.0-beta.1');
  assert.equal(selectRelease([{...beta,draft:true},stable],'0.5.0','darwin','arm64','beta').latest,'v0.6.0');
  assert.equal(selectRelease([stable],'0.5.0','win32','arm64').available,false);
  assert.throws(()=>selectRelease([stable],'0.5.0','darwin','arm64','untrusted'));
});
test('verified download emits progress, retains a private record and detects later tampering',async t=>{
  const {manager,events}=await fixture(t);await manager.download(17);
  assert.equal(manager.snapshot().phase,'downloaded');assert.ok(events.some(item=>item.phase==='downloading'&&item.downloaded>0));
  const id=manager.snapshot().record.id,file=await manager.verifiedFile(id);assert.deepEqual(await fs.readFile(file),data);
  if(process.platform!=='win32')assert.equal((await fs.stat(file)).mode&0o077,0);
  await fs.writeFile(file,'changed');await assert.rejects(manager.verifiedFile(id),/changed/);
});
test('checksum mismatch removes incomplete data and permits a real retry',async t=>{
  const {manager,releases,directory}=await fixture(t);releases[0].assets[0].digest='sha256:'+'0'.repeat(64);
  // Refresh the manager-owned metadata, rather than relying on shared fixture references.
  await manager.check('beta');await assert.rejects(manager.download(17),/verification failed/);
  assert.equal(manager.snapshot().phase,'failed');assert.deepEqual(await fs.readdir(directory),[]);
  releases[0].assets[0].digest='sha256:'+digest;await manager.check('beta');await manager.download(17);assert.equal(manager.snapshot().phase,'downloaded');
});
test('download fallback reads the exact installer checksum from the release manifest',async t=>{
  const {manager,releases}=await fixture(t,(value)=>new Response(value.endsWith('SHA256SUMS.txt')?digest+'  '+release().assets[0].name+'\n':data));
  delete releases[0].assets[0].digest;releases[0].assets.push({id:18,name:'SHA256SUMS.txt',browser_download_url:'https://github.com/RyosukeSAMA/github-ai/releases/download/v0.6.0/SHA256SUMS.txt'});
  await manager.check('beta');await manager.download(17);assert.equal(manager.snapshot().phase,'downloaded');
});
test('unpublished checksums, foreign repositories and unsafe redirect hosts cannot produce an installer',async t=>{
  const {manager,releases}=await fixture(t);delete releases[0].assets[0].digest;await manager.check('beta');await assert.rejects(manager.download(17),/No verified checksum/);
  assert.throws(()=>assetURL('https://github.com/elsewhere/project/releases/download/v1/installer.exe'),/official/);
  const bad=await fixture(t,()=>new Response(null,{status:302,headers:{location:'https://unexpected.example/installer'}}));
  await assert.rejects(bad.manager.download(17),/Unsafe/);assert.equal(bad.requests.some(value=>value.includes('unexpected.example')),false);
});
test('cancelling a streaming download removes partial files and releases the operation lock',async t=>{
  const payload=Buffer.alloc(1024*10,7),hash=createHash('sha256').update(payload).digest('hex');
  const {manager,releases,directory}=await fixture(t,()=>new Response(new ReadableStream({async pull(controller){await new Promise(resolve=>setTimeout(resolve,5));controller.enqueue(payload.subarray(0,1024));}})));
  releases[0].assets[0].size=payload.length;releases[0].assets[0].digest='sha256:'+hash;await manager.check('beta');
  manager.onChange=value=>{if(value.phase==='downloading'&&value.downloaded>0)manager.cancel();};
  await assert.rejects(manager.download(17));assert.equal(manager.snapshot().phase,'cancelled');assert.equal(manager.controller,null);assert.deepEqual(await fs.readdir(directory),[]);
});
test('older installers require an explicit recovery operation and cached paths cannot escape the cache',async t=>{
  const {manager,releases,directory}=await fixture(t);manager.version='0.7.0';await manager.check('beta');
  assert.equal(manager.recoveryVersions().length,1);await assert.rejects(manager.download(17),/newer/);await manager.download(17,{rollback:true});
  const records=await manager.history();records[0].path=path.join(directory,'..','unexpected.dmg');await fs.writeFile(path.join(directory,'downloads.json'),JSON.stringify(records));
  await assert.rejects(manager.verifiedFile(records[0].id),/not in the update cache/);
});

test('Linux update selection matches actual electron-builder AppImage and Debian architecture names',()=>{
  const {desktopRelease}=require('../releases.cjs');
  const release={tag_name:'v0.6.0',assets:[{id:1,name:'Pantheon-0.6.0-linux-x86_64.AppImage'},{id:2,name:'Pantheon-0.6.0-linux-amd64.deb'}]};
  assert.equal(desktopRelease(release,'0.5.0','linux','x64').assets.length,2);
});

test('a new client rejects an older core revision with upgrade guidance instead of reusing missing routes',async()=>{
  const {Backend}=require('../backend.cjs');const backend=new Backend({executable:'unused'});let revision;backend.request=async target=>({api_version:1,api_revision:revision,challenge:new URL(target,'http://localhost').searchParams.get('challenge')});await assert.rejects(backend.identity(),/Update this Pantheon host/);revision=3;assert.equal((await backend.identity()).api_revision,3);
});
