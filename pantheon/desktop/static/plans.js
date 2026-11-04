'use strict';
async function openModelPlans(){
  await refreshSetup();const epoch=state.epoch,saved=await api('/api/desktop/model-plans'),content=element('div','model-plans');
  content.append(element('p','','Compare explicit preferences, then review the assignment before applying. One connection is enough. Quality scores and extra capabilities come from you; no model-name guessing or paid test is performed here.'));
  const form=element('form'),rows=element('div'),keys=new Set(Object.keys(saved.ratings));rows.id='model-rating-rows';
  for(const row of $('#model-rows').children)keys.add(row.querySelector('select').value+'/'+row.querySelector('input').value.trim());
  for(const provider of state.setup.providers.filter(item=>item.connection_saved&&item.enabled))keys.add(provider.id+'/'+provider.test_model);
  for(const key of [...keys].filter(key=>!key.endsWith('/')).slice(0,200)){
    const value=saved.ratings[key]||{},row=element('section','data-card');row.dataset.key=key;row.append(element('strong','',key));
    const label=element('label','','Your quality rating (1–5, optional)'),quality=element('input');quality.type='number';quality.min='1';quality.max='5';quality.step='any';quality.value=value.quality||'';quality.dataset.field='quality';label.append(quality);row.append(label);
    row.append(element('small','','Text comes from the text-model catalog. Declare any additional capability only after checking it yourself.'));
    for(const capability of ['tools','vision']){const label=element('label','check-label',capability==='tools'?'I confirmed tool calling':'I confirmed image understanding'),input=element('input');input.type='checkbox';input.dataset.capability=capability;input.checked=value.capabilities?.includes(capability)||false;label.prepend(input);row.append(label);}rows.append(row);
  }
  const details=element('details');details.append(element('summary','','Your ratings and capability declarations'),rows);const save=element('button','','Save my ratings');save.type='submit';details.append(save);form.append(details);content.append(form);
  const verifiedLabel=element('label','check-label'),verified=element('input');verified.id='plan-verified-only';verified.type='checkbox';verified.checked=true;verifiedLabel.append(verified,document.createTextNode('Only models with a current successful saved API test'));
  const required=element('select');required.id='plan-capability';for(const [value,label] of [['text','Text tasks'],['tools','Require tool calling (your declaration)'],['vision','Require image understanding (your declaration)']]){const option=element('option','',label);option.value=value;required.append(option);}
  const result=element('div');result.id='model-plan-results';const feedback=element('p');feedback.id='model-plan-feedback';feedback.setAttribute('role','status');
  const generate=element('button','primary','Compare plans');
  action(generate,async()=>{if(epoch!==state.epoch)throw new Error('Project changed. Reopen model plans.');feedback.textContent='Comparing saved data…';result.replaceChildren();const value=await api('/api/desktop/model-plans/suggest',{verified_only:verified.checked,required:required.value==='text'?['text']:['text',required.value]});if(epoch!==state.epoch)return;feedback.textContent=value.note;
    for(const plan of value.plans){
      const card=element('section','data-card');card.dataset.plan=plan.kind;card.append(element('h3','',({cost:'Cost conscious',balanced:'Balanced',quality:'Quality preference'})[plan.kind]),element('p','',plan.reason));
      if(plan.choice){const choice=plan.choice;card.append(element('strong','',choice.provider+' / '+choice.model),element('p','',choice.verified?'This model has saved API verification.':'This model is not currently API-verified.'),element('p','',choice.price?'Your entered rates · $'+choice.price.input+' input / $'+choice.price.output+' output per 1M tokens.':'Cost unknown; no entered price.'),element('p','',choice.quality?'Your quality rating · '+choice.quality+'/5':'No quality rating entered.'));
        const review=element('button','','Review assignment');action(review,()=>{closeDialog('#info-dialog');$('[name="model-mode"][value="single"]').checked=true;renderModels();for(const row of $('#model-rows').children){row.querySelector('select').value=choice.provider;row.querySelector('input').value=choice.model;refreshModelPicker(row.querySelector('input'));}$('#model-plan-note').textContent=card.querySelector('h3').textContent+' loaded for review. No assignments saved. Apply to this task when ready.';$('#model-plan-note').hidden=false;});card.append(review);
      }result.append(card);
    }
  });
  form.onsubmit=event=>{event.preventDefault();if(!form.reportValidity())return;(async()=>{if(epoch!==state.epoch)throw new Error('Project changed. Reopen model plans.');const ratings={};for(const row of rows.children){const quality=row.querySelector('[data-field=quality]').value;if(quality!=='')ratings[row.dataset.key]={quality:Number(quality),capabilities:['text',...[...row.querySelectorAll('[data-capability]:checked')].map(input=>input.dataset.capability)]};}await api('/api/desktop/model-plans/ratings',ratings);feedback.textContent='Your ratings saved. Assignments are unchanged. Compare plans to review suggestions.';})().catch(error=>{feedback.textContent=errorText(error);});};
  content.append(verifiedLabel,required,generate,feedback,result);info('Model plans',content);
}
