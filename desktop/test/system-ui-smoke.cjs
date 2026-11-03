'use strict';
const {_electron:electron}=require('playwright');
const {expect}=require('playwright/test');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const path=require('node:path');
const os=require('node:os');
const http=require('node:http');
const {createHash}=require('node:crypto');
const {smokeProgress,smokeTimeout}=require('./smoke-support.cjs');
const repo=path.resolve(__dirname,'../..');
async function main(){
  const timeoutMs=smokeTimeout(240000),root=await fs.mkdtemp(path.join(os.tmpdir(),'pantheon-system-ui-'));
  const project=path.join(root,'Garden studio');await fs.mkdir(project);const archive=path.join(root,'workspace-backup.zip');
  const evidence=path.join(repo,'dist','system-ui-evidence');await fs.mkdir(evidence,{recursive:true});await fs.rm(path.join(evidence,'result.json'),{force:true});
  const bytes=Buffer.from('An inert, checksum-verified installer fixture.');let corrupt=true;
  const name='Pantheon-0.6.0-beta.1-'+process.platform+'-'+process.arch+'.'+(process.platform==='darwin'?'dmg':process.platform==='win32'?'exe':'AppImage');
  const release={tag_name:'v0.6.0-beta.1',prerelease:true,draft:false,body:'# Update preview\n\nVerified download and recovery.',assets:[{id:17,name,size:bytes.length,digest:'sha256:'+createHash('sha256').update(bytes).digest('hex'),browser_download_url:'https://github.com/RyosukeSAMA/github-ai/releases/download/v0.6.0-beta.1/'+name}]};
  const fixture=http.createServer((req,res)=>{if(req.url==='/releases'){res.setHeader('content-type','application/json');res.end(JSON.stringify([release]));}else res.end(corrupt?Buffer.alloc(bytes.length):bytes);});
  await new Promise(resolve=>fixture.listen(0,'127.0.0.1',resolve));const origin='http://127.0.0.1:'+fixture.address().port;
  const env={...process.env,PANTHEON_DESKTOP_TEST:'1',PANTHEON_DESKTOP_WORKSPACE:project,PANTHEON_DESKTOP_USER_DATA:path.join(root,'profile'),PANTHEON_DATA_DIR:path.join(root,'data'),PANTHEON_STATE_MODE:'workspace',PANTHEON_MODEL_DOCS_SYNC:'0',PANTHEON_DESKTOP_PYTHON:process.env.PANTHEON_DESKTOP_PYTHON||path.join(repo,'.venv','bin','python')};
  for(const key of ['OPENAI_API_KEY','ANTHROPIC_API_KEY','DEEPSEEK_API_KEY','PANTHEON_CONFIG','PANTHEON_DESKTOP_TOKEN'])delete env[key];
  const loader=path.join(path.dirname(require.resolve('playwright-core/package.json')),'lib','server','electron','loader.js');
  const app=await electron.launch({executablePath:process.env.PANTHEON_TEST_EXECUTABLE||require('electron'),args:process.env.PANTHEON_TEST_EXECUTABLE?['-r',loader]:[path.join(repo,'desktop')],env});
  const child=app.process(),progress=smokeProgress('system-ui',evidence,timeoutMs,()=>{child.kill('SIGKILL');fixture.closeAllConnections();});
  const page=await app.firstWindow(),errors=[];page.setDefaultTimeout(20000);page.on('pageerror',error=>errors.push(String(error)));
  const shot=async file=>{await page.mouse.move(5,70);await page.screenshot({path:path.join(evidence,file+'.png'),animations:'disabled',scale:'css'});};
  try{
    await expect(page.locator('#connection-state')).toHaveText('Local connected',{timeout:30000});
    if(process.env.PANTHEON_TEST_EXECUTABLE)assert.equal((await page.evaluate(()=>window.pantheonDesktop.info())).packaged,true);
    // External transport/dialog substitutions stay in this driver, never in the shipped app.
    await app.evaluate(async({app,dialog,shell},{origin,archive})=>{
      const {createRequire}=process.getBuiltinModule('module');const require=createRequire(app.getAppPath()+'/package.json');
      const {UpdateManager}=require(app.getAppPath()+'/updates.cjs');const original=UpdateManager.prototype.check;
      UpdateManager.prototype.check=function(...args){this.fetchImpl=(url,options)=>fetch(origin+(url.startsWith('https://api.github.com/')?'/releases':'/installer'),{...options,redirect:'manual'});return original.apply(this,args);};
      delete process.env.PANTHEON_DESKTOP_TEST;
      dialog.showSaveDialog=async()=>({canceled:false,filePath:archive});dialog.showOpenDialog=async()=>({canceled:false,filePaths:[archive]});dialog.showMessageBox=async()=>({response:1});
      globalThis.pantheonOpenedInstaller='';shell.openPath=async file=>{globalThis.pantheonOpenedInstaller=file;return '';};
    },{origin,archive});
    await page.locator('#new-task').click();await page.locator('#prompt').fill('A draft kept in the backup');await expect(page.locator('#draft-state')).toHaveText('Saved');
    await page.locator('#service-open').click();await expect(page.locator('#system-dialog')).toBeVisible();await page.locator('#update-check').click();
    await expect(page.locator('#update-title')).toHaveText('A new version is available');await expect(page.locator('#update-channel')).toHaveValue('beta');
    progress.stage('channel selection and verified download');
    await page.locator('#update-channel').selectOption('stable');await expect(page.locator('#update-download')).not.toBeVisible();
    await page.locator('#update-channel').selectOption('beta');await expect(page.locator('#update-download')).toBeVisible();
    await page.locator('#update-download').click();await expect(page.locator('#update-title')).toHaveText('Update needs attention');await expect(page.locator('#update-message')).toContainText('verification failed');
    corrupt=false;await page.locator('#update-download').click();await expect(page.locator('#update-title')).toHaveText('Installer verified and ready');await app.evaluate(()=>{process.env.PANTHEON_DESKTOP_TEST='1';});await shot('updates-light');
    await page.locator('#system-tab-backups').click();await page.locator('#backup-create').click();await expect(page.locator('#backup-message')).toContainText('Backup created');
    assert.ok((await fs.stat(archive)).size>0);await expect(page.locator('#connection-state')).toHaveText('Local connected');
    await page.locator('#system-dialog [data-close]').first().click();await expect(page.locator('#prompt')).toHaveValue('A draft kept in the backup');
    await page.locator('#prompt').fill('A newer saved draft');await expect(page.locator('#draft-state')).toHaveText('Saved');
    await page.locator('#service-open').click();await page.locator('#system-tab-backups').click();await page.locator('#backup-inspect').click();
    await expect(page.locator('#backup-review')).toBeVisible();await expect(page.locator('#backup-review-description')).toContainText('Workspace data only');await shot('backup-review');
    progress.stage('offline backup and restore');
    await page.locator('#backup-restore').click();await expect(page.locator('#backup-message')).toContainText('Workspace restored');
    await page.locator('#system-dialog [data-close]').first().click();await expect(page.locator('#prompt')).toHaveValue('A draft kept in the backup');
    await page.locator('#service-open').click();await page.locator('#system-tab-updates').click();await page.locator('#update-open').click();await expect(page.locator('#update-message')).toContainText('Quit Pantheon');
    assert.ok((await app.evaluate(()=>globalThis.pantheonOpenedInstaller)).endsWith(name));
    await page.locator('#system-dialog [data-close]').first().click();await page.locator('#theme-toggle').click();await page.locator('#service-open').click();await shot('updates-dark');
    await app.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows()[0].setSize(820,720));
    await expect(page.locator('#system-dialog footer')).toBeInViewport();assert.ok(await page.locator('#system-dialog').evaluate(node=>node.scrollWidth<=node.clientWidth));await shot('system-narrow');
    await page.locator('#system-dialog [data-close]').first().click();assert.deepEqual(errors,[]);
    await app.close();assert.equal(child.exitCode,0);progress.finish(true);
    await fs.writeFile(path.join(evidence,'result.json'),JSON.stringify({passed:true,packaged:!!process.env.PANTHEON_TEST_EXECUTABLE,page_errors:errors,paid_api_calls:0,checks:['Stable/Beta channels','failed checksum and retry','verified cache and installer preparation','real offline backup/restore','draft retention','dark/light/narrow']},null,2));
    console.log('SYSTEM_UI_PASS: verified update and real offline recovery; inert installer and no paid APIs');
  }catch(error){if(child.exitCode===null)await shot('failure').catch(()=>{});throw error;}
  finally{if(child.exitCode===null)await app.close().catch(()=>child.kill('SIGKILL'));fixture.closeAllConnections();await new Promise(resolve=>fixture.close(resolve));progress.finish(false);}
}
main().catch(error=>{console.error(error);process.exitCode=1;});
