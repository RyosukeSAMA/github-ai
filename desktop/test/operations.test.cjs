'use strict';
const {test}=require('node:test');const assert=require('node:assert/strict');const {browserURL,operationPlan,planSummary}=require('../operations-policy.cjs');const {applicationCommand}=require('../operations-mac.cjs');
test('browser scope accepts HTTPS and local previews but no credential, file or script URLs',()=>{
  for(const value of ['https://example.com/path','http://127.0.0.1:8000','http://localhost:9000'])assert.ok(browserURL(value));
  for(const value of ['file:///private/data','javascript:alert(1)','https://user:secret@example.com','http://example.com','data:text/html,hello'])assert.throws(()=>browserURL(value));
  assert.throws(()=>operationPlan([{action:'navigate',url:'https://foreign.invalid'}],{kind:'browser',origin:'https://example.com'}),/approved origin/);
});
test('plans reject unbounded waits, unsupported actions and extra payload fields before execution',()=>{
  const scope={kind:'browser',origin:'https://example.com'};
  for(const plan of [[{action:'eval',code:'secret'}],[{action:'wait',ms:5000}],[{action:'click',selector:'#send',code:'dangerous'}],Array.from({length:31},()=>({action:'screenshot'}))])assert.throws(()=>operationPlan(plan,scope));
  assert.equal(operationPlan([{action:'fill',selector:'input[name=email]',value:'private text'}],scope).length,1);
});
test('redacted step outcomes and plan summaries never contain typed values or URL query tokens',()=>{
  const steps=operationPlan([{action:'navigate',url:'https://example.com/private?token=SECRET'},{action:'fill',selector:'#name',value:'SECRET'}],{kind:'browser',origin:'https://example.com'});
  assert.ok(!planSummary(steps).includes('SECRET'));
});
test('native applications are allowlisted and text is passed as argv instead of script source',()=>{
  const text='say "hello" & do shell script "UNTRUSTED"';const command=applicationCommand('com.apple.TextEdit',{action:'type',value:text});assert.equal(command.executable,'/usr/bin/osascript');assert.ok(!command.args[1].includes('UNTRUSTED'));assert.equal(command.args.at(-1),text);
  assert.throws(()=>applicationCommand('arbitrary.bundle',{action:'activate'}));
  assert.throws(()=>operationPlan([{action:'type',value:'hello\nexecute'}],{kind:'application',bundle:'com.apple.TextEdit'}),/Enter\/Tab/);
  assert.throws(()=>operationPlan([{action:'key',key:'Command+Q'}],{kind:'application',bundle:'com.apple.TextEdit'}));
});
