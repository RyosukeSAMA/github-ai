const test = require('node:test');
const assert = require('node:assert/strict');
const {apiPath,remoteURL}=require('../backend.cjs');
test('API proxy does not accept arbitrary origins or unreviewed file writes',()=>{
  assert.equal(apiPath('/api/desktop/sessions'),'/api/desktop/sessions');
  for(const path of ['https://evil.invalid/api/tasks','//evil.invalid/api/tasks','/api/../private','/api/security/save','/api/workspace/file','/api/workspace/preview','/api/tasks\\evil'])assert.throws(()=>apiPath(path));
});
test('remote connections require a clean HTTPS origin',()=>{
  assert.equal(remoteURL('https://example.com'),'https://example.com');
  for(const url of ['http://example.com','https://name:secret@example.com','https://example.com/private','https://example.com/?token=secret','file:///etc/passwd'])assert.throws(()=>remoteURL(url));
});

require('node:test').test('renderer proxy cannot bypass native terminal confirmation using encoded paths',()=>{
  for(const route of ['/api/workspace/terminal','/api/workspace/terminal/stream','/api/workspace/%74erminal/stream','/api/workspace%2fterminal'])assert.throws(()=>apiPath(route),/native confirmation/);
  assert.equal(apiPath('/api/workspace/terminal/stream',true),'/api/workspace/terminal/stream');
});

require('node:test').test('long media requests keep a bounded provider-appropriate timeout',()=>{const {requestTimeout}=require('../backend.cjs');assert.equal(requestTimeout('/api/media/generate'),300000);assert.equal(requestTimeout('/api/media/transcribe'),300000);assert.equal(requestTimeout('/api/desktop/sessions'),30000);});

test('a read-locked runtime is reused only after authenticated identity and PID verification',async t=>{
  const fs=require('node:fs/promises'),path=require('node:path'),os=require('node:os'),http=require('node:http');
  const {Backend}=require('../backend.cjs'),root=await fs.mkdtemp(path.join(os.tmpdir(),'pantheon-locked-runtime-'));
  t.after(()=>fs.rm(root,{recursive:true,force:true}));
  const workspace=await fs.realpath(root),descriptor=path.join(root,'desktop-runtime.json'),runtimeLock=path.join(root,'runtime.lock'),token='fixture-private-token-'.repeat(3);let wrongPID=false;
  const server=http.createServer((req,res)=>{res.setHeader('content-type','application/json');if(req.headers['x-pantheon-desktop-token']!==token){res.writeHead(403);res.end('{}');return;}res.end(JSON.stringify({api_version:1,api_revision:2,challenge:new URL(req.url,'http://localhost').searchParams.get('challenge'),pid:wrongPID?process.pid+1:process.pid,instance_id:'locked-fixture',workspace}));});
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));t.after(()=>new Promise(resolve=>server.close(resolve)));
  await fs.writeFile(descriptor,JSON.stringify({pid:process.pid,port:server.address().port,instance_id:'locked-fixture',workspace,token}),{mode:0o600});
  const locator=path.join(root,'locate.cjs');await fs.writeFile(locator,'process.stdout.write('+JSON.stringify(JSON.stringify({descriptor,runtime_lock:runtimeLock}))+')');
  const readFile=fs.readFile;fs.readFile=async function(file,...args){if(file===runtimeLock){const error=new Error('Fixture Windows byte-range read lock');error.code='EACCES';throw error;}return readFile.call(this,file,...args);};t.after(()=>{fs.readFile=readFile;});
  const backend=new Backend({executable:process.execPath,args:[locator]});await backend.local(workspace);assert.equal(backend.owned,false);assert.equal(backend.child,null);assert.equal(backend.info.pid,process.pid);
  wrongPID=true;const rejected=new Backend({executable:process.execPath,args:[locator]});await assert.rejects(rejected.local(workspace),/could not be verified/);assert.equal(rejected.child,null,'An unverified locked runtime must never trigger a replacement process');
});
