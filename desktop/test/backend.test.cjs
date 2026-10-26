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
