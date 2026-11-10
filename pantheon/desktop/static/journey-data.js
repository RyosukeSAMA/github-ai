'use strict';
const JourneyData = (() => {
  const templates = {
    explore: {name:'Explore this project',goal:'Explain how this project is organized and how to run it.',deliverables:'A project map, key entry points, and a short getting-started guide.',acceptance:'Reference the files you inspected. Distinguish confirmed facts from assumptions.',constraints:'Start with a read-only overview. Ask before changing project files.'},
    build: {name:'Build something',goal:'',deliverables:'An implementation, a summary of changed files, and relevant verification.',acceptance:'Describe how to check the result. Report checks actually run and any remaining gaps.',constraints:'Follow the project conventions. Review changes before saving.'},
    fix: {name:'Fix an issue',goal:'',deliverables:'A diagnosis, a focused correction, and a regression check where appropriate.',acceptance:'Explain the cause with evidence. State which checks passed, failed, or were not run.',constraints:'Preserve unrelated work. Describe any unresolved symptoms.'},
    research: {name:'Research a topic',goal:'',deliverables:'A sourced comparison, a recommendation, and remaining uncertainties.',acceptance:'Link the sources used. Separate evidence from inference.',constraints:'State the scope and the date when time-sensitive information matters.'}
  };
  function briefText(value) {
    const goal=String(value.goal||'').trim();if(!goal)throw new Error('Describe the goal first.');
    return goal+'\n\n'+[['Deliverables',value.deliverables],['Acceptance criteria',value.acceptance],['Constraints',value.constraints]].filter(([,v])=>String(v||'').trim()).map(([label,v])=>label+':\n'+String(v).trim()).join('\n\n');
  }
  function readiness(setup,session,mode,offline=false) {
    const required=mode==='role:chronos'?[]:mode?.startsWith('role:')?[mode.slice(5)]:['hermes','hephaestus','athena','apollo'];
    const choices=required.map(role=>{
      const choice=session?.overrides?.[role]||setup?.role_statuses?.find(x=>x.role===role)||{};
      const provider=setup?.providers?.find(x=>x.id===choice.provider);
      return {role,...choice,label:provider?.label||choice.provider||'Not assigned',configured:!!choice.model&&choice.model!=='none'&&!!provider&&provider.enabled!==false&&(provider.key_configured===true||provider.requires_key===false)};
    });
    const missing=choices.filter(x=>!x.configured);
    return {choices,missing,ready:!offline&&!missing.length,offline,scheduled:!required.length};
  }
  function stepLabel(step) {const description=String(step.description||'');return String(/^User specified role:/i.test(description)?step.task||'Working on your request':description||step.task||'Recorded execution step').split(/\r?\n/)[0].slice(0,320);}
  function progress(run,events=[],approvals=new Map()) {
    const steps=new Map();let plan='',phase='queued',current='',pending=new Set(),lastIssue='';
    const key=d=>String(Number.isInteger(d.index)?d.index:d.role||'step');
    for(const event of events){
      const d=event.data||{},type=event.event;
      if(type==='plan_start'||type==='phase'&&d.stage==='planning'){phase='planning';current=d.detail||d.description||'Hermes is choosing a route.';}
      if(type==='plan'||type==='plan_ready'){
        plan=typeof d.plan==='string'?d.plan:'';phase='working';
        for(const [index,step] of (Array.isArray(d.steps)?d.steps:[]).entries())steps.set(key({...step,index:step.index??index}),{...step,index:step.index??index,status:'planned'});
      }
      if(type==='phase'&&d.detail)current=d.detail;
      if(['step_start','step_done','step_error'].includes(type)){
        const id=key(d),previous=steps.get(id)||{};steps.set(id,{...previous,...d,status:type==='step_start'?'running':type==='step_error'||d.success===false?'failed':'completed'});phase='working';current=stepLabel({...previous,...d});
        if(type==='step_error'||d.error)lastIssue=String(d.error||d.message||'A step needs review.');
      }
      if(type==='summary_start'||type==='phase'&&d.stage==='synthesizing'){phase='delivery';current=d.description||d.detail||'Hermes is preparing the result.';}
      if(type==='mcp_approval_required')pending.add(d.approval_id);
      if(type==='mcp_approval_resolved')pending.delete(d.approval_id);
      if(type==='error'||type==='persistence_warning')lastIssue=String(d.message||d.error||'Review the recorded activity.');
    }
    const statuses={queued:'Waiting to start',running:phase==='planning'?'Planning the approach':phase==='delivery'?'Preparing your delivery':'Working on your task',completed:'Ready for your review',partial_failure:'Some work needs attention',failed:'Task needs attention',stopped:'Task stopped',interrupted:'Task interrupted',stopping:'Stopping safely'};
    const waiting=['queued','running','stopping'].includes(run?.status)&&Array.from(pending).some(id=>approvals.has(id));
    const list=Array.from(steps.values()),completed=list.filter(x=>x.status==='completed'),active=list.filter(x=>x.status==='running');
    return {phase:run?.status==='completed'?'complete':phase,title:waiting?'Your approval is needed':statuses[run?.status]||'No run recorded',current,plan,steps:list,completed:completed.length,total:list.length,active,waiting,issue:lastIssue};
  }
  function delivery(run,events,artifacts,sessionId) {
    const snapshot=progress(run,events),outputs=artifacts.filter(x=>x.session_id===sessionId&&x.run_id===run?.id);
    const saves=outputs.filter(x=>x.saved_path).map(x=>({id:x.id,path:x.saved_path}));
    return {...snapshot,outputs,saves,successful:run?.status==='completed',verification:'No independent test results recorded. Review any reported checks in the council response.'};
  }
  return {templates,briefText,readiness,progress,delivery,stepLabel};
})();
if(typeof module!=='undefined')module.exports=JourneyData;
