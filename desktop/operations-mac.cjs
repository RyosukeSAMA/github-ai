'use strict';
const fs=require('node:fs/promises');const {execFile}=require('node:child_process');const {promisify}=require('node:util');const {APPLICATIONS}=require('./operations-policy.cjs');const exec=promisify(execFile);
// Text is passed only as argv. Nothing from a page, task or input becomes script source.
const SCRIPT=`on run argv
  set bundleID to item 1 of argv
  set operationName to item 2 of argv
  set operationValue to item 3 of argv
  tell application "System Events"
    set targetProcess to first application process whose bundle identifier is bundleID
    set frontmost of targetProcess to true
    tell targetProcess
      if operationName is "type" then
        keystroke operationValue
      else if operationName is "button" then
        click button operationValue of front window
      else if operationValue is "Enter" then
        key code 36
      else if operationValue is "Tab" then
        key code 48
      else if operationValue is "Escape" then
        key code 53
      else if operationValue is "Left" then
        key code 123
      else if operationValue is "Right" then
        key code 124
      else if operationValue is "Up" then
        key code 126
      else if operationValue is "Down" then
        key code 125
      else if operationValue is "Command+A" then
        keystroke "a" using command down
      else if operationValue is "Command+S" then
        keystroke "s" using command down
      end if
    end tell
  end tell
end run`;
function applicationCommand(bundle,step){if(!APPLICATIONS[bundle])throw new Error('Choose a listed application.');if(step.action==='activate')return {executable:'/usr/bin/open',args:['-b',bundle]};return {executable:'/usr/bin/osascript',args:['-e',SCRIPT,'--',bundle,step.action,step.value||step.name||step.key||'']};}
async function installedApplications(){const items=[];for(const [id,value] of Object.entries(APPLICATIONS)){for(const file of value.paths)try{await fs.access(file);items.push({id,name:value.name});break;}catch{}}return items;}
async function applicationStep(bundle,step,signal){const command=applicationCommand(bundle,step);try{await exec(command.executable,command.args,{signal,timeout:10000,maxBuffer:10000});}catch(error){if(signal.aborted)throw new Error('Operation stopped.');throw new Error('The selected app did not accept the action. Check Accessibility and Automation permissions, its front window and the exact button title.');}}
module.exports={applicationCommand,installedApplications,applicationStep};
