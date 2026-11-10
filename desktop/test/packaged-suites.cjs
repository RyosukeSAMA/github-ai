'use strict';
// Each suite owns a different temporary profile/project and runs against the same built app.
const {spawnSync}=require('node:child_process');
const fs=require('node:fs');
const path=require('node:path');
const {smokeTimeout}=require('./smoke-support.cjs');
if(!process.env.PANTHEON_TEST_EXECUTABLE)throw new Error('Set PANTHEON_TEST_EXECUTABLE to the packaged application.');
const repo=path.resolve(__dirname,'../..'),results=[];
const output=path.join(repo,'dist','desktop-evidence');fs.mkdirSync(output,{recursive:true});
fs.rmSync(path.join(output,'packaged-suites.json'),{force:true});
for(const [suite,fallback] of [['native-smoke',600000],['provider-ui-smoke',300000],['toolbar-ui-smoke',300000],['system-ui-smoke',300000],['productivity-ui-smoke',300000],['sync-ui-smoke',300000],['operations-ui-smoke',300000],['journey-ui-smoke',300000],['project-ui-smoke',300000],['delivery-ui-smoke',300000]]){
  const timeout=smokeTimeout(fallback),start=Date.now();
  console.log('PACKAGED_SUITE_START: '+suite+' (budget '+timeout+' ms)');
  const child=spawnSync(process.execPath,[path.join(__dirname,suite+'.cjs')],{env:{...process.env,PANTHEON_DESKTOP_TEST_TIMEOUT_MS:String(timeout)},stdio:'inherit',timeout:timeout+30000});
  results.push({suite,passed:child.status===0&&!child.error,exit_code:child.status,signal:child.signal,elapsed_ms:Date.now()-start,error:child.error?.message||null});
  console.log('PACKAGED_SUITE_END: '+JSON.stringify(results.at(-1)));
}
fs.writeFileSync(path.join(output,'packaged-suites.json'),JSON.stringify({platform:process.platform,passed:results.every(item=>item.passed),results},null,2));
if(results.some(item=>!item.passed))process.exitCode=1;
