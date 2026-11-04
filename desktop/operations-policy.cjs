'use strict';
const APPLICATIONS={
  'com.apple.TextEdit':{name:'TextEdit',paths:['/System/Applications/TextEdit.app','/Applications/TextEdit.app']},
  'com.apple.Notes':{name:'Notes',paths:['/System/Applications/Notes.app']},
  'com.apple.Safari':{name:'Safari',paths:['/Applications/Safari.app']},
  'com.google.Chrome':{name:'Google Chrome',paths:['/Applications/Google Chrome.app']},
  'com.microsoft.VSCode':{name:'Visual Studio Code',paths:['/Applications/Visual Studio Code.app']}
};
const KEYS=['Enter','Tab','Escape','Left','Right','Up','Down','Command+A','Command+S'];
function browserURL(value){if(typeof value!=='string'||value.length>2000)throw new Error('Enter a browser URL up to 2,000 characters.');const url=new URL(value);if(url.username||url.password||!(url.protocol==='https:'||url.protocol==='http:'&&['localhost','127.0.0.1','[::1]'].includes(url.hostname)))throw new Error('Use HTTPS or a local preview URL without embedded credentials.');return url;}
function operationPlan(value,scope){
  if(!Array.isArray(value)||!value.length||value.length>30)throw new Error('Review between 1 and 30 steps.');let wait=0;
  return value.map(step=>{
    if(!step||typeof step!=='object'||Array.isArray(step)||typeof step.action!=='string')throw new Error('Each step needs an action.');
    const allowed=scope.kind==='browser'?['navigate','click','fill','wait','screenshot']:['activate','type','button','key','wait'];if(!allowed.includes(step.action))throw new Error('This action is not available for the selected scope.');
    const keys={navigate:['action','url'],click:['action','selector'],fill:['action','selector','value'],wait:['action','ms'],screenshot:['action'],activate:['action'],type:['action','value'],button:['action','name'],key:['action','key']}[step.action];if(Object.keys(step).some(key=>!keys.includes(key)))throw new Error('A step contains unsupported fields.');
    const result={action:step.action};
    if(step.action==='navigate'){const url=browserURL(step.url);if(url.origin!==scope.origin)throw new Error('Navigation must stay inside the approved origin.');result.url=url.href;}
    if(['click','fill'].includes(step.action)){if(typeof step.selector!=='string'||!step.selector.trim()||step.selector.length>400)throw new Error('Use a CSS selector up to 400 characters.');result.selector=step.selector;}
    if(['fill','type'].includes(step.action)){if(typeof step.value!=='string'||step.value.length>4000||scope.kind==='application'&&/[\x00-\x1f\x7f]/.test(step.value))throw new Error('Use up to 4,000 characters; application Enter/Tab must be separate key steps.');result.value=step.value;}
    if(step.action==='wait'){if(!Number.isInteger(step.ms)||step.ms<0||step.ms>3000||(wait+=step.ms)>10000)throw new Error('Wait up to 3 seconds per step and 10 seconds per plan.');result.ms=step.ms;}
    if(step.action==='button'){if(typeof step.name!=='string'||!step.name.trim()||step.name.length>120)throw new Error('Enter the exact button title.');result.name=step.name;}
    if(step.action==='key'){if(!KEYS.includes(step.key))throw new Error('Choose a listed key.');result.key=step.key;}
    if(scope.kind==='application'&&!APPLICATIONS[scope.bundle])throw new Error('Choose a listed application.');return result;
  });
}
function planSummary(steps){return steps.map((step,index)=>(index+1)+'. '+({navigate:'Navigate within approved origin',click:'Click selected element',fill:'Fill selected field ('+String(step.value||'').length+' characters)',wait:'Wait '+step.ms+' ms',screenshot:'Capture this browser window',activate:'Bring selected app forward',type:'Type '+String(step.value||'').length+' characters into selected app',button:'Click button: '+(step.name||''),key:'Press '+(step.key||'')})[step.action]).join('\n');}
module.exports={APPLICATIONS,KEYS,browserURL,operationPlan,planSummary};
