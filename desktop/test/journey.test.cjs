'use strict';
const {test}=require('node:test');const assert=require('node:assert/strict');
const {briefText,readiness,progress,delivery}=require('../../pantheon/desktop/static/journey-data.js');
test('task briefs retain user scope, omit blank sections and require a goal',()=>{
  assert.throws(()=>briefText({goal:'  '}),/goal/);
  assert.equal(briefText({goal:'  Fix the export  ',deliverables:'CSV',acceptance:'Keep unicode',constraints:''}),'Fix the export\n\nDeliverables:\nCSV\n\nAcceptance criteria:\nKeep unicode');
});
test('readiness evaluates current task overrides and local scheduling without asserting API verification',()=>{
  const setup={providers:[{id:'deepseek',label:'DeepSeek',key_configured:true},{id:'anthropic',key_configured:false}],role_statuses:['hermes','hephaestus','athena','apollo'].map(role=>({role,provider:'deepseek',model:'chat'}))};
  assert.equal(readiness(setup,{},'multi').ready,true);
  const session={overrides:{athena:{provider:'anthropic',model:'custom'}}};assert.deepEqual(readiness(setup,session,'multi').missing.map(x=>x.role),['athena']);
  assert.equal(readiness(setup,session,'role:hephaestus').ready,true);assert.equal(readiness(setup,session,'role:chronos').scheduled,true);assert.equal(readiness(setup,session,'role:chronos',true).ready,false);
  setup.providers[0].enabled=false;assert.equal(readiness(setup,{},'role:hephaestus').ready,false);
});
test('progress represents actual steps, parallel active roles, errors and synthesis',()=>{
  const events=[{event:'plan',data:{plan:'Research then build',steps:[{index:0,role:'athena',task:'Research'},{index:1,role:'hephaestus',task:'Build'}]}},{event:'step_start',data:{index:0,role:'athena'}},{event:'step_start',data:{index:1,role:'hephaestus'}}];
  let value=progress({status:'running'},events);assert.equal(value.active.length,2);assert.equal(value.completed,0);assert.equal(value.total,2);
  events.push({event:'step_done',data:{index:0,success:true}},{event:'step_error',data:{index:1,error:'File changed'}});value=progress({status:'partial_failure'},events);assert.equal(value.completed,1);assert.equal(value.issue,'File changed');assert.equal(value.title,'Some work needs attention');
  events.push({event:'summary_start',data:{description:'Preparing the final answer'}});assert.equal(progress({status:'running'},events).phase,'delivery');assert.equal(progress({status:'completed'},events).phase,'complete');
});
test('approval waiting is resolved by its event or terminal status and unknown plans stay unknown',()=>{
  const approvals=new Map([['a',{}]]),events=[{event:'mcp_approval_required',data:{approval_id:'a'}}];assert.equal(progress({status:'running'},events,approvals).waiting,true);assert.equal(progress({status:'failed'},events,approvals).waiting,false);
  events.push({event:'mcp_approval_resolved',data:{approval_id:'a'}});const value=progress({status:'running'},events,approvals);assert.equal(value.waiting,false);assert.equal(value.total,0);assert.equal(value.completed,0);
});
test('delivery scopes artifacts and saves to the selected run and never promotes response claims to verified checks',()=>{
  const run={id:'new',status:'completed'},artifacts=[{id:'one',session_id:'s',run_id:'old',saved_path:'old.txt'},{id:'two',session_id:'s',run_id:'new'},{id:'three',session_id:'other',run_id:'new',saved_path:'private.txt'}];
  let value=delivery(run,[{event:'summary_done',data:{content:'All tests passed'}}],artifacts,'s');assert.deepEqual(value.outputs.map(x=>x.id),['two']);assert.equal(value.saves.length,0);assert.match(value.verification,/No independent test results/);
  artifacts[1].saved_path='reviewed.txt';value=delivery(run,[],artifacts,'s');assert.equal(value.saves[0].path,'reviewed.txt');
});
