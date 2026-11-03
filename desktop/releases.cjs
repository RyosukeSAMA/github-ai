'use strict';
function compareVersions(left,right){
  const parse=value=>{const match=/^v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$/.exec(value||'');return match?{core:match.slice(1,4).map(Number),pre:match[4]?.split('.')||[]}:null;};
  const a=parse(left),b=parse(right);if(!a||!b)return null;
  for(let i=0;i<3;i++)if(a.core[i]!==b.core[i])return Math.sign(a.core[i]-b.core[i]);
  if(!a.pre.length||!b.pre.length)return a.pre.length===b.pre.length?0:a.pre.length?-1:1;
  for(let i=0;i<Math.max(a.pre.length,b.pre.length);i++){if(a.pre[i]===undefined)return -1;if(b.pre[i]===undefined)return 1;if(a.pre[i]===b.pre[i])continue;const an=/^\d+$/.test(a.pre[i]),bn=/^\d+$/.test(b.pre[i]);return an&&bn?Math.sign(Number(a.pre[i])-Number(b.pre[i])):an!==bn?an?-1:1:a.pre[i]<b.pre[i]?-1:1;}return 0;
}
function desktopRelease(release,current,platform,arch,channel='stable'){
  if(!['stable','beta'].includes(channel))throw new Error('Choose the Stable or Beta update channel.');
  const newer=compareVersions(release.tag_name,current)===1;
  const extension=platform==='darwin'?/\.dmg$/:platform==='win32'?/\.exe$/:/\.(AppImage|deb)$/;
  const matching=(release.assets||[]).filter(item=>/^Pantheon[-_]/i.test(item.name)&&extension.test(item.name)&&new RegExp('(?:^|[-_])'+(arch==='x64'?'(?:x64|amd64)':arch)+'(?:[-_.]|$)','i').test(item.name));
  const allowed=!release.draft&&(!release.prerelease||channel==='beta');
  return {version:current,latest:release.tag_name,channel,available:!!newer&&matching.length>0&&allowed,assets:allowed?matching:[],notes:String(release.body||'').slice(0,20000),published_at:release.published_at||null,url:'https://github.com/RyosukeSAMA/github-ai/releases',reason:!allowed?'This release is outside your update channel.':!newer?'This app is up to date.':matching.length?'':'A newer core release exists, but no desktop installer for this platform is published yet.'};
}
function selectRelease(releases,current,platform,arch,channel='stable'){
  if(!['stable','beta'].includes(channel))throw new Error('Choose the Stable or Beta update channel.');
  const eligible=releases.filter(item=>!item.draft&&compareVersions(item.tag_name,'0.0.0')!==null&&(!item.prerelease||channel==='beta'));
  eligible.sort((a,b)=>compareVersions(b.tag_name,a.tag_name));
  const choices=eligible.map(item=>desktopRelease(item,current,platform,arch,channel));
  return choices.find(item=>item.available)||choices[0]||{version:current,channel,available:false,assets:[],reason:'No desktop releases are published for this channel.',url:'https://github.com/RyosukeSAMA/github-ai/releases'};
}
module.exports={compareVersions,desktopRelease,selectRelease};
