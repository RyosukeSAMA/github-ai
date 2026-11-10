'use strict';
let nativeProject=null;
function refreshProjectOverview(){if(nativeProject&&state.info?.workspace&&!state.offline&&!state.serviceLost&&!state.projectOpening)nativeProject.refresh(true);else if(nativeProject)$('#project-context-strip').hidden=true;}
function bindProjectOverview(){
  nativeProject=PantheonProject.mount({
    request:async(path,body,method)=>{try{return await api(path,body,method);}catch(error){if(/Project state changed|file changed again|Project state or tracked files changed/.test(error.message))error.status=409;throw error;}},
    scope:()=>String(state.info?.remoteOrigin||state.info?.workspace?.workspace||'')+':'+String(state.info?.workspace?.workspace||''),
    session:()=>state.selected,
    unavailable:()=>!state.info?.workspace||state.offline||state.serviceLost||state.maintenance||state.projectOpening,
    busy:()=>!!activeRun()||state.sending||state.creatingTask,
    confirm:confirmChoice,
    currentDraft:()=>$('#prompt').value,
    prepare:async(prompt)=>{const epoch=state.epoch,old=state.selected;await newTask();if(epoch!==state.epoch||!state.selected||state.selected===old)throw Error('A new task could not be prepared. Your original draft is retained.');$('#prompt').value=prompt;$('#prompt').dispatchEvent(new Event('input',{bubbles:true}));await flushDrafts();$('#prompt').focus();},
    notify:toast,strip:$('#project-context-strip')
  });
  action($('#project-overview-open'),async()=>{if(!state.info?.workspace&&!await connectWorkspace())return;await nativeProject.open();});
  refreshProjectOverview();
}
