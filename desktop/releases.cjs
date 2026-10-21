'use strict';
function compareVersions(left,right){
  const parse=value=>{const match=/^v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$/.exec(value||'');return match?{core:match.slice(1,4).map(Number),pre:match[4]?.split('.')||[]}:null;};
  const a=parse(left),b=parse(right);if(!a||!b)return null;
  for(let i=0;i<3;i++)if(a.core[i]!==b.core[i])return Math.sign(a.core[i]-b.core[i]);
  if(!a.pre.length||!b.pre.length)return a.pre.length===b.pre.length?0:a.pre.length?-1:1;
  for(let i=0;i<Math.max(a.pre.length,b.pre.length);i++){if(a.pre[i]===undefined)return -1;if(b.pre[i]===undefined)return 1;if(a.pre[i]===b.pre[i])continue;const an=/^\d+$/.test(a.pre[i]),bn=/^\d+$/.test(b.pre[i]);return an&&bn?Math.sign(Number(a.pre[i])-Number(b.pre[i])):an!==bn?an?-1:1:a.pre[i]<b.pre[i]?-1:1;}return 0;
}
function desktopRelease(release,current,platform,arch){
  const newer=compareVersions(release.tag_name,current)===1;
  const extension=platform==='darwin'?/\.dmg$/:platform==='win32'?/\.exe$/:/\.(AppImage|deb)$/;
  const matching=(release.assets||[]).filter(item=>/^Pantheon[-_]/i.test(item.name)&&extension.test(item.name)&&new RegExp('(?:^|[-_])'+(arch==='x64'?'(?:x64|amd64)':arch)+'(?:[-_.]|$)','i').test(item.name));
  return {version:current,latest:release.tag_name,available:!!newer&&matching.length>0&&!release.draft&&!release.prerelease,url:'https://github.com/RyosukeSAMA/github-ai/releases',reason:!newer?'This app is up to date.':matching.length?'':'A newer core release exists, but no desktop installer for this platform is published yet.'};
}
module.exports={compareVersions,desktopRelease};
