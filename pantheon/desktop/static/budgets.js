'use strict';
async function openUsage(){
  const run=latestRun(),epoch=state.epoch;
  const [usage,budget]=await Promise.all([api('/api/usage/details'+(run?.task_id?'?task_id='+encodeURIComponent(run.task_id):'')),api('/api/budgets')]);if(epoch!==state.epoch)return;
  const content=element('div','budget-content');content.append(element('p','',usage.note));
  for(const group of usage.groups){const card=element('div','data-card');card.append(element('strong','',(group.role||'Other')+' · '+group.phase),element('p','',group.provider+' / '+group.model+' · '+group.calls+' call(s)'),element('p','',(group.input_tokens===null?'Unknown':group.input_tokens)+' input tokens · '+(group.output_tokens===null?'Unknown':group.output_tokens)+' output tokens'),element('p','',group.unpriced?'Cost unknown':('$'+Number(group.estimated_usd||0).toFixed(4)+' estimated')));content.append(card);}
  if(!usage.groups.length)content.append(element('p','','No calls recorded for this task.'));
  const form=element('form','budget-form'),fields=new Map(),policy=structuredClone(budget.policy);
  form.id='budget-form';form.append(element('h3','','Workspace limits'),element('p','','Limits apply to this project across Desktop, Web and CLI. Leave a limit empty for no limit. Requests include attempts and failures. Daily means a rolling 24 hours.'));
  const grid=element('div','budget-grid');
  for(const [key,label,integer,hint] of [['task_requests','Requests per task',true,'All roles and stages share this limit.'],['daily_requests','Requests in 24 hours',true,'Includes failed attempts.'],['output_tokens','Output tokens per request',true,'Caps output for each request; it is not a total-token budget.'],['task_usd','Estimated USD per task',false,'Requires an explicit price for every model used.'],['daily_usd','Estimated USD in 24 hours',false,'Uses your rates, not a provider invoice.']]){
    const wrapper=element('label','',label),input=element('input');input.id='budget-'+key;input.type='number';input.min='0';input.step=integer?'1':'any';if(integer)input.max='1000000';input.placeholder='No limit';input.value=policy[key]||'';fields.set(key,input);wrapper.append(input,element('small','',hint));grid.append(wrapper);
  }form.append(grid);
  const prices=element('div','budget-prices');prices.id='budget-prices';
  function priceRow(key='',rates={}){
    const row=element('div','budget-price-row');
    for(const [name,label,value] of [['model','Provider/model ID',key],['input','Input USD / 1M tokens',rates.input],['output','Output USD / 1M tokens',rates.output]]){const field=element('label','',label),input=element('input');input.dataset.field=name;input.required=true;input.value=value??'';if(name!=='model'){input.type='number';input.min='0';input.step='any';}else input.placeholder='deepseek/deepseek-flash';field.append(input);row.append(field);}
    const remove=element('button','','Remove price');remove.type='button';action(remove,()=>row.remove());row.append(remove);prices.append(row);
  }
  form.append(element('h3','','Your model prices'),element('p','','Enter USD rates per million tokens from your provider/account. Pantheon does not infer a current price or promise model quality. A USD limit blocks a request without a configured price; use request limits if prices are unknown. Zero is an explicit zero rate.'));
  for(const [key,rates] of Object.entries(policy.prices))priceRow(key,rates);
  const add=element('button','','Add model price');add.type='button';action(add,()=>{priceRow();prices.lastChild.querySelector('input').focus();});form.append(prices,add);
  const media=element('div','budget-media-prices');media.id='budget-media-prices';
  function mediaRow(key='',rate=''){
    const row=element('div','budget-price-row');for(const [name,label,value] of [['model','Provider/model ID',key],['rate','Estimated USD per media request',rate]]){const field=element('label','',label),input=element('input');input.dataset.field=name;input.required=true;input.value=value;if(name==='rate'){input.type='number';input.min='0';input.step='any';}field.append(input);row.append(field);}
    const remove=element('button','','Remove estimate');remove.type='button';action(remove,()=>row.remove());row.append(remove);media.append(row);
  }
  const advanced=element('details');advanced.append(element('summary','','Media request estimates'),element('p','','Image and audio requests can use a flat per-request estimate. Enter your own conservative estimate; actual provider charges can vary.'));
  for(const [key,rate] of Object.entries(policy.operation_prices))mediaRow(key,rate);
  const addMedia=element('button','','Add media estimate');addMedia.type='button';action(addMedia,()=>mediaRow());advanced.append(media,addMedia);form.append(advanced);
  const feedback=element('p','budget-feedback');feedback.id='budget-feedback';feedback.setAttribute('role','status');
  const save=element('button','primary','Save workspace budget');save.type='submit';form.append(feedback,save);
  const summary=element('div','data-card'),recent=budget.last_24_hours||{};
  summary.append(element('strong','','Last 24 hours'),element('p','',(recent.requests||0)+' requests · '+(recent.unpriced||0)+' without a price · '+(recent.uncertain||0)+' awaiting final usage'),element('p','','Known estimates: $'+Number(recent.estimated_usd||0).toFixed(4)+(recent.unpriced?' + unknown cost':'')));
  for(const warning of budget.warnings||[])summary.append(element('p','',warning));content.append(summary,form);
  form.onsubmit=event=>{event.preventDefault();if(!form.reportValidity()||save.disabled)return;save.disabled=true;feedback.textContent='Saving…';(async()=>{
    try{
      const next={...policy,prices:{},operation_prices:{}};
      for(const [key,input] of fields){const value=input.value===''?0:Number(input.value);if(!Number.isFinite(value)||value<0||input.step==='1'&&(!Number.isSafeInteger(value)||value>1000000))throw new Error('Enter valid non-negative limits.');next[key]=value;}
      function modelKey(row,map){const key=row.querySelector('[data-field=model]').value.trim();if(!/^[a-z0-9_-]+\/[^\s/][^\s]*$/i.test(key))throw new Error('Use provider/model for each price.');if(Object.hasOwn(map,key))throw new Error('Each provider/model needs one price row.');return key;}
      for(const row of prices.children){const key=modelKey(row,next.prices);next.prices[key]={input:Number(row.querySelector('[data-field=input]').value),output:Number(row.querySelector('[data-field=output]').value)};}
      for(const row of media.children){const key=modelKey(row,next.operation_prices);next.operation_prices[key]=Number(row.querySelector('[data-field=rate]').value);}
      if(epoch!==state.epoch)throw new Error('The project changed. Reopen budgets for the current project.');
      await api('/api/budgets',next);Object.assign(policy,next);feedback.textContent='Workspace budget saved. Other projects are unchanged.';
    }catch(error){feedback.textContent=errorText(error);}finally{save.disabled=false;}
  })();};info('Usage and budgets',content);
}
