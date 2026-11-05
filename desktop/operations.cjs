'use strict';
const {BrowserWindow,dialog,session,systemPreferences}=require('electron');const {randomUUID}=require('node:crypto');const {setTimeout:delay}=require('node:timers/promises');
const {APPLICATIONS,browserURL,operationPlan,planSummary}=require('./operations-policy.cjs');const {applicationStep,installedApplications}=require('./operations-mac.cjs');
let applicationBusy=false;
class Operations{
  constructor({parent,workspace,onChange=()=>{}}){Object.assign(this,{parent,workspace,onChange});this.scope=null;this.browser=null;this.controller=null;this.audit=[];this.capture=null;this.sequence=0;}
  status(){return {active:!!this.scope,busy:!!this.controller||!!this.opening,scope:this.scope?{...this.scope}:null,audit:[...this.audit],has_capture:!!this.capture,platform:process.platform,application_supported:process.platform==='darwin',accessibility:process.platform==='darwin'?systemPreferences.isTrustedAccessibilityClient(false):null};}
  changed(){this.onChange(this.status());}
  record(action,status,index=null){this.audit.push({time:Date.now(),action,status,step:index});this.audit=this.audit.slice(-100);this.changed();}
  async available(){return {...this.status(),applications:process.platform==='darwin'?await installedApplications():[]};}
  async start(value){
    if(this.controller)throw new Error('Stop the running plan first.');let scope,url;
    if(value?.kind==='browser'){url=browserURL(value.url);scope={kind:'browser',origin:url.origin};}
    else if(value?.kind==='application'&&process.platform==='darwin'&&(await installedApplications()).some(item=>item.id===value.bundle))scope={kind:'application',bundle:value.bundle,name:APPLICATIONS[value.bundle].name};
    else throw new Error('Choose an available browser or installed application adapter.');
    const choice=await dialog.showMessageBox(this.parent,{type:'question',message:'Start a scoped operation session?',detail:scope.kind==='browser'?scope.origin+'\n\nA separate visible browser uses its own temporary session. Navigation stays in this origin; the page may load normal external assets. Downloads, pop-ups, camera and microphone are blocked. Steps require separate plan confirmation.':scope.name+'\n\nOnly the selected application receives approved steps. Typing, button clicks and keys require OS Accessibility/Automation permission. No action runs until a plan is reviewed.',buttons:['Cancel','Start session'],defaultId:0,cancelId:0});
    if(choice.response!==1)return {cancelled:true};await this.stop();this.scope=scope;this.audit=[];this.capture=null;this.opening=true;this.record('session','opening');
    if(scope.kind==='browser'){
      const partition='pantheon-operation-'+randomUUID(),isolated=session.fromPartition(partition);isolated.setPermissionRequestHandler((_web,_permission,callback)=>callback(false));isolated.setPermissionCheckHandler(()=>false);isolated.on('will-download',(event,item)=>{event.preventDefault();item.cancel();this.record('download','blocked');});
      const browser=new BrowserWindow({parent:this.parent,width:1180,height:820,show:process.env.PANTHEON_DESKTOP_TEST!=='1',title:'Pantheon · Approved browser',webPreferences:{partition,contextIsolation:true,sandbox:true,nodeIntegration:false,webSecurity:true}});this.browser=browser;
      browser.webContents.setWindowOpenHandler(()=>({action:'deny'}));const guard=(event,target)=>{try{if(browserURL(target).origin!==scope.origin){event.preventDefault();browser.webContents.stop();this.record('navigation','blocked outside scope');}}catch{event.preventDefault();}};browser.webContents.on('will-navigate',guard);browser.webContents.on('will-redirect',guard);browser.on('closed',()=>{if(this.browser===browser){this.browser=null;this.scope=null;this.controller?.abort();this.record('session','closed');}isolated.clearStorageData().catch(()=>{});});
      try{await this.navigate(browser,url.href);}catch{if(this.browser!==browser)return {cancelled:true};await this.stop();throw new Error('The approved page could not be opened. Check its address and connection.');}
    }
    if(!this.scope)return {cancelled:true};this.opening=false;this.record('session','ready');return this.status();
  }
  async run(value){
    if(!this.scope||this.scope.kind==='browser'&&!this.browser)throw new Error('Start a scoped session first.');if(this.controller||this.opening)throw new Error('Wait for the approved session or running plan to finish.');
    const steps=operationPlan(value,this.scope),scope={...this.scope};
    if(scope.kind==='application'&&steps.some(step=>step.action!=='activate'&&step.action!=='wait')&&!systemPreferences.isTrustedAccessibilityClient(false))throw new Error('Accessibility access is required. Use Request Accessibility, then review the plan again.');
    const choice=await dialog.showMessageBox(this.parent,{type:'warning',message:'Run this reviewed operation plan?',detail:(scope.origin||scope.name)+'\n\n'+planSummary(steps)+'\n\nSite/app actions can save or send information. Stop cancels remaining steps; actions already sent may finish.',buttons:['Cancel','Run reviewed steps'],defaultId:0,cancelId:0});if(choice.response!==1)return {cancelled:true};
    if(scope.kind==='application'&&applicationBusy)throw new Error('Another application plan is running. Stop or finish it first.');if(scope.kind==='application')applicationBusy=true;
    const controller=new AbortController();this.controller=controller;const sequence=++this.sequence;this.changed();
    try{for(const [index,step] of steps.entries()){
      controller.signal.throwIfAborted();if(sequence!==this.sequence)throw new Error('Session changed.');this.record(step.action,'running',index+1);
      if(step.action==='wait')await delay(step.ms,null,{signal:controller.signal});
      else if(scope.kind==='application')await applicationStep(scope.bundle,step,controller.signal);
      else await this.browserStep(step,controller.signal);
      controller.signal.throwIfAborted();this.record(step.action,'completed',index+1);
    }return {completed:true};}
    catch(error){this.record('plan',controller.signal.aborted?'stopped':'failed');if(!controller.signal.aborted)await this.stop();throw new Error(controller.signal.aborted?'Operation stopped. Already sent site/app actions may finish.':error.message);}
    finally{if(scope.kind==='application')applicationBusy=false;if(this.controller===controller)this.controller=null;this.changed();}
  }
  async navigate(browser,url){let timer;try{await Promise.race([browser.loadURL(url),new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error('Navigation timed out.')),15000);})]);}finally{clearTimeout(timer);}}
  async browserStep(step,signal){
    const browser=this.browser;if(!browser||browser.isDestroyed())throw new Error('Approved browser was closed.');if(browserURL(browser.webContents.getURL()).origin!==this.scope.origin)throw new Error('Browser moved outside its approved scope.');
    if(step.action==='navigate'){await this.navigate(browser,step.url);return;}
    if(step.action==='screenshot'){const image=await browser.webContents.capturePage();const buffer=image.resize({width:1180}).toPNG();if(buffer.length>4*1024*1024)throw new Error('Preview is too large. Use a smaller window.');signal.throwIfAborted();if(this.browser!==browser)throw new Error('Operation stopped.');this.capture=buffer;this.changed();return;}
    const code=`(()=>{const input=${JSON.stringify(step)};let target;try{target=document.querySelector(input.selector);}catch{return {ok:false};}if(!target||target.disabled||!target.getClientRects().length)return {ok:false};target.scrollIntoView({block:'center'});if(input.action==='click'){target.click();return {ok:true};}if(!(target instanceof HTMLInputElement||target instanceof HTMLTextAreaElement)||!['text','textarea','password','email','search','number','url','tel'].includes(target.type)||target.readOnly)return {ok:false};const prototype=target instanceof HTMLTextAreaElement?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(prototype,'value').set.call(target,input.value);target.dispatchEvent(new Event('input',{bubbles:true}));target.dispatchEvent(new Event('change',{bubbles:true}));return {ok:true};})()`;
    let timer;const timeout=new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error('The page action timed out.')),10000);});try{const result=await Promise.race([browser.webContents.executeJavaScript(code,true),timeout]);signal.throwIfAborted();if(!result?.ok)throw new Error('The selected element is unavailable, disabled or unsupported.');}finally{clearTimeout(timer);}
  }
  async stop(){this.opening=false;this.sequence++;this.controller?.abort();if(this.browser&&!this.browser.isDestroyed())this.browser.destroy();this.browser=null;this.scope=null;this.capture=null;this.record('session','stopped');return this.status();}
  requestAccess(){if(process.platform!=='darwin')throw new Error('Native application control is currently available on macOS.');return {trusted:systemPreferences.isTrustedAccessibilityClient(true)};}
}
module.exports={Operations};
