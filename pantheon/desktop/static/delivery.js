'use strict';
let desktopDelivery=null;
function bindDeliveryChecks(){
  desktopDelivery=PantheonDelivery.mount({
    request:async(path,body,method)=>{try{return await api(path,body,method);}catch(error){if(/changed|already applied/i.test(error.message))error.status=409;throw error;}},
    scope:()=>String(state.info?.remoteOrigin||'')+':'+String(state.info?.workspace?.workspace||''),context:()=>state.selected,
    unavailable:()=>!state.info?.workspace||state.offline||state.serviceLost||state.maintenance||state.projectOpening,
    busy:()=>!!activeRun()||state.sending||state.creatingTask,
    repairOverrides:()=>state.detail?.overrides?.hephaestus?{hephaestus:state.detail.overrides.hephaestus}:{},
    confirm:confirmChoice,projectChanged:()=>{refreshProjectOverview();renderDelivery();}
  });
  action($('#delivery-open'),async()=>{if(!state.info?.workspace&&!await connectWorkspace())return;if(!state.selected)await newTask();await desktopDelivery.open();});
}
