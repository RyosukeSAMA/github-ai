'use strict';
async function openFileHistory(path){
  const epoch=state.epoch,value=await api('/api/desktop/versions?path='+encodeURIComponent(path));if(epoch!==state.epoch)return;
  const content=element('div','version-history');content.append(element('p','',value.path),element('p','',value.retention));
  if(!value.versions.length)content.append(element('p','','No reviewed saves recorded yet. Saving through Review and save starts this file’s history. Files edited externally are captured when you next review and save.'));
  for(const version of value.versions){
    const row=element('section','data-card'),compare=element('button','','Compare snapshot');row.dataset.version=version.id;
    row.append(element('strong','',new Date(version.created*1000).toLocaleString()),element('p','',version.source+' · '+version.hash.slice(0,12)));
    action(compare,async()=>{
      const comparison=await api('/api/desktop/versions/'+version.id+'/compare');if(epoch!==state.epoch)return;
      const panel=element('div','version-comparison');panel.append(element('p','',comparison.path),element('p','','Current file → selected snapshot. Comparing has not changed any file.'));
      const diff=element('pre','version-diff',comparison.diff||'The current file matches this snapshot.');panel.append(diff);
      if(comparison.truncated)panel.append(element('p','','Diff is truncated. Inspect the full file before restoring.'));
      const restore=element('button','primary','Review restoration');restore.disabled=comparison.truncated||!comparison.diff;
      action(restore,async()=>{if(epoch!==state.epoch)throw new Error('Project changed. Reopen file history.');const review=await api('/api/desktop/versions/'+version.id+'/review',{expected_hash:comparison.expected_hash});closeDialog('#info-dialog');showPreparedReview(review);});
      const back=element('button','','Back to history');action(back,()=>openFileHistory(path));panel.append(restore,back);info('Compare file version',panel);
    });row.append(compare);content.append(row);
  }info('File version history',content);
}
function showPreparedReview(review){
  review.editor_content_before=state.file?.path===review.path?$('#file-editor').value:null;state.activeReview=review;$('#review-path').textContent=review.path;renderDiff(review.diff||'No text changes.');$('#review-state').dataset.state=review.truncated?'attention':'pending';$('#review-state').textContent=review.truncated?'Diff truncated. Inspect the full file before accepting.':'Pending review · No files written';$('#review-accept').disabled=review.truncated;setView('work');setTab('review');
}
