'use strict';
const {test}=require('node:test');const assert=require('node:assert/strict');const {compareVersions,desktopRelease}=require('../releases.cjs');
test('release ordering handles prereleases and does not offer an older installer',()=>{
  assert.equal(compareVersions('v0.5.0','0.5.0-beta.1'),1);assert.equal(compareVersions('v0.4.0','0.5.0-beta.1'),-1);assert.equal(compareVersions('0.5.0-beta.10','0.5.0-beta.2'),1);
  const release={tag_name:'v0.4.0',assets:[{name:'Pantheon-0.4.0-arm64.dmg'}]};assert.equal(desktopRelease(release,'0.5.0-beta.1','darwin','arm64').available,false);
});
test('release check requires a matching installer, platform, architecture and stable version',()=>{
 const release={tag_name:'v0.6.0',assets:[{name:'Pantheon-0.6.0-arm64.dmg'}]};assert.equal(desktopRelease(release,'0.5.0-beta.1','darwin','arm64').available,true);assert.equal(desktopRelease(release,'0.5.0-beta.1','darwin','x64').available,false);assert.equal(desktopRelease({...release,prerelease:true},'0.5.0-beta.1','darwin','arm64').available,false);assert.equal(desktopRelease(release,'0.5.0-beta.1','win32','arm64').available,false);
});
