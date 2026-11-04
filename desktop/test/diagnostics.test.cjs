'use strict';
const {test}=require('node:test');const assert=require('node:assert/strict');const {diagnosticSummary}=require('../diagnostics.cjs');
test('diagnostics exports only whitelisted versions, service flags and aggregate counts',()=>{
  const report=diagnosticSummary({version:'0.5.0-beta.18',versions:{electron:'44.9.1',node:'22.1',chrome:'130.1',secret:'PRIVATE'},platform:'darwin',arch:'arm64',osRelease:'24.6.0',backend:{token:'PRIVATE',workspace:'/private/USER',base:'https://PRIVATE',owned:true},reachable:true,sessions:[{title:'PRIVATE',messages:['PRIVATE']}],runs:[{status:'running',data:'PRIVATE'},{status:'PRIVATE'}]});
  assert.equal(report.counts.tasks,1);assert.equal(report.counts.run_status.running,1);assert.equal(report.service.desktop_owned,true);assert.ok(!JSON.stringify(report).includes('PRIVATE'));assert.ok(!JSON.stringify(report).includes('/private/USER'));
});
