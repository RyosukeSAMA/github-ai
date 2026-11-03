'use strict';
const fs=require('node:fs');
const path=require('node:path');
const {performance}=require('node:perf_hooks');

function smokeTimeout(fallback){
  const value=process.env.PANTHEON_DESKTOP_TEST_TIMEOUT_MS;
  if(value===undefined)return fallback;
  if(!/^\d+$/.test(value)||Number(value)<1000||Number(value)>900000)throw new Error('PANTHEON_DESKTOP_TEST_TIMEOUT_MS must be 1000–900000.');
  return Number(value);
}
function smokeProgress(suite,evidence,timeoutMs,onTimeout){
  fs.mkdirSync(evidence,{recursive:true});
  const start=performance.now(),stages=[];let finished=false;
  const save=status=>fs.writeFileSync(path.join(evidence,'timings.json'),JSON.stringify({suite,status,timeout_ms:timeoutMs,elapsed_ms:Math.round(performance.now()-start),last_stage:stages.at(-1)?.name||'starting',stages},null,2));
  const stage=name=>{
    const elapsed_ms=Math.round(performance.now()-start),previous=stages.at(-1)?.elapsed_ms||0;
    stages.push({name,elapsed_ms,duration_ms:elapsed_ms-previous});save('running');
    console.log('NATIVE_STAGE: '+suite+' / '+name+' ('+elapsed_ms+' ms)');
  };
  const timer=setTimeout(()=>{
    save('timed_out');console.error(suite+' exceeded '+timeoutMs+' ms; last stage: '+(stages.at(-1)?.name||'starting')+'. See timings.json.');
    try{onTimeout();}finally{process.exit(1);}
  },timeoutMs);timer.unref();
  stage('starting');
  return {stage,finish(passed){if(finished)return;finished=true;clearTimeout(timer);save(passed?'passed':'failed');}};
}
module.exports={smokeTimeout,smokeProgress};
