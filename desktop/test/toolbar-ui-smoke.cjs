'use strict';
// Real native windows and shared-core persistence in a disposable project.
// Only explicit fixture probes contact localhost; opening the toolbar never probes a model.
const {_electron:electron}=require('playwright');
const {expect}=require('playwright/test');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const path=require('node:path');
const os=require('node:os');
const http=require('node:http');
const {smokeTimeout,smokeProgress}=require('./smoke-support.cjs');
const repo=path.resolve(__dirname,'../..');

async function main(){
  const timeoutMs=smokeTimeout(180000);
  const root=await fs.mkdtemp(path.join(os.tmpdir(),'pantheon-toolbar-'));
  const project=path.join(root,'Garden studio');await fs.mkdir(project);
  const evidence=path.join(repo,'dist','toolbar-ui-evidence');await fs.mkdir(evidence,{recursive:true});
  await fs.rm(path.join(evidence,'result.json'),{force:true});
  let providerCalls=0;
  const fixture=http.createServer((req,res)=>{
    let body='';req.on('data',chunk=>body+=chunk);req.on('end',()=>{
      res.setHeader('content-type','application/json');
      if(req.method==='GET'){res.end(JSON.stringify({data:[{id:'garden-chat'}]}));return;}
      providerCalls++;const input=JSON.parse(body);
      if(input.model==='unavailable-model'){res.writeHead(404);res.end(JSON.stringify({error:{message:'Fixture model unavailable',code:'model_not_found'}}));return;}
      res.end(JSON.stringify({id:'fixture',model:input.model,choices:[{message:{role:'assistant',content:'ok'},finish_reason:'stop'}],usage:{prompt_tokens:2,completion_tokens:1}}));
    });
  });await new Promise(resolve=>fixture.listen(0,'127.0.0.1',resolve));
  const base='http://127.0.0.1:'+fixture.address().port+'/v1';
  const env={...process.env,PANTHEON_DESKTOP_TEST:'1',PANTHEON_DESKTOP_WORKSPACE:'',PANTHEON_DESKTOP_USER_DATA:path.join(root,'profile'),PANTHEON_DATA_DIR:path.join(root,'data'),PANTHEON_STATE_MODE:'workspace',PANTHEON_MODEL_DOCS_SYNC:'0',PANTHEON_DESKTOP_PYTHON:process.env.PANTHEON_DESKTOP_PYTHON||path.join(repo,'.venv','bin','python')};
  for(const key of ['OPENAI_API_KEY','ANTHROPIC_API_KEY','DEEPSEEK_API_KEY','PANTHEON_CONFIG','PANTHEON_DESKTOP_TOKEN'])delete env[key];
  const loader=path.join(path.dirname(require.resolve('playwright-core/package.json')),'lib','server','electron','loader.js');
  const app=await electron.launch({executablePath:process.env.PANTHEON_TEST_EXECUTABLE||require('electron'),args:process.env.PANTHEON_TEST_EXECUTABLE?['-r',loader]:[path.join(repo,'desktop')],env});
  const child=app.process();
  const progress=smokeProgress('toolbar-ui',evidence,timeoutMs,()=>{child.kill('SIGKILL');fixture.closeAllConnections();});
  const errors=[];app.on('window',page=>page.on('pageerror',error=>errors.push(String(error))));
  const page=await app.firstWindow();page.setDefaultTimeout(20000);
  const shot=async name=>{await page.mouse.move(5,70);await page.screenshot({path:path.join(evidence,name+'.png'),animations:'disabled',scale:'css'});};
  const panel=page.locator('#connection-panel');
  try{
    if(process.env.PANTHEON_TEST_EXECUTABLE)assert.equal((await page.evaluate(()=>window.pantheonDesktop.info())).packaged,true);
    await expect(page.locator('#new-window')).toHaveAttribute('aria-label','New window');
    await page.locator('#connection-state').focus();await page.keyboard.press('Enter');await expect(panel).toBeVisible();
    await expect(panel).toContainText('No project');await expect(page.locator('#connection-choose')).toBeVisible();await expect(page.locator('#connection-configure')).not.toBeVisible();
    await page.keyboard.press('Escape');await expect(panel).not.toBeVisible();await expect(page.locator('#connection-state')).toHaveAttribute('aria-expanded','false');
    await page.locator('#new-window').click();await expect.poll(()=>app.windows().length).toBe(2);
    let second=app.windows().find(other=>other!==page);await expect(second.locator('#connection-state')).toHaveText('Not connected');
    await second.close();await expect.poll(()=>app.windows().length).toBe(1);
    assert.ok(app.windows().includes(page),'The originating window must stay open');
    await app.evaluate(({dialog},project)=>{dialog.showOpenDialog=async()=>({canceled:false,filePaths:[project]});},project);
    await page.locator('#connection-state').click();await page.locator('#connection-choose').click();
    await expect(page.locator('#connection-state')).toHaveText('Local connected',{timeout:30000});
    await expect(page.locator('#new-window')).toHaveAttribute('aria-label','Open in new window');
    progress.stage('project connected');
    await page.locator('#connection-state').click();await expect(panel).toContainText('No API connections saved yet');await expect(panel.locator('.service-health')).toContainText('Connected');
    await page.locator('#connection-panel-close').click();assert.equal(providerCalls,0);
    await page.evaluate(async base=>{
      for(const [provider,model] of [['deepseek','garden-chat'],['openai','unavailable-model'],['anthropic','claude-preview']])await window.pantheonDesktop.api('/api/connections/save',{method:'POST',body:{provider,model,base_url:base,api_key:'local-fixture-only',credential_storage:'env',streaming:false}});
      for(const [provider,model] of [['deepseek','garden-chat'],['openai','unavailable-model']])await window.pantheonDesktop.api('/api/setup/test',{method:'POST',body:{provider,model,base_url:base}});
      await window.pantheonDesktop.api('/api/models/defaults',{method:'POST',body:{models:Object.fromEntries(['hermes','hephaestus','athena','apollo'].map(role=>[role,{provider:'deepseek',model:'garden-chat'}]))}});
      await refreshSetup();
    },base);
    progress.stage('saved API evidence');
    const explicitCalls=providerCalls;assert.ok(explicitCalls>=2);
    await page.locator('#new-task').click();await expect(page.locator('#prompt')).toBeVisible();
    await page.locator('#connection-state').click();
    await expect(panel.locator('[data-provider=deepseek] .health-badge')).toHaveText('API verified');
    await expect(panel.locator('[data-provider=openai] .health-badge')).toHaveText('Test failed');
    await expect(panel.locator('[data-provider=anthropic] .health-badge')).toHaveText('Not tested');
    await expect(panel.locator('.connection-health-row[data-provider=deepseek]')).toContainText('Last tested');
    assert.ok(!(await panel.innerText()).includes('local-fixture-only'));
    await shot('connection-status-light');await page.keyboard.press('Escape');
    await page.locator('#theme-toggle').click();await page.locator('#connection-state').click();await shot('connection-status-dark');
    await page.locator('#connection-configure').click();await expect(page.locator('#connections-dialog')).toBeVisible();await expect(panel).not.toBeVisible();await page.locator('#connections-dialog [data-close]').click();
    await app.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows()[0].setSize(820,720));
    await page.locator('#connection-state').click();await expect(panel).toBeVisible();
    assert.ok(await panel.evaluate(node=>{const r=node.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&r.top>=0&&r.bottom<=innerHeight;}));
    await shot('connection-status-narrow');await page.keyboard.press('Escape');
    await app.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows()[0].setSize(1440,1000));await page.locator('#theme-toggle').click();
    // Click immediately after typing, before the autosave debounce; the other window must load the saved draft.
    progress.stage('drafts and independent windows');
    const draft='Draft saved before opening another window';await page.locator('#prompt').fill(draft);await page.locator('#new-window').click();
    await expect.poll(()=>app.windows().length).toBe(2);second=app.windows().find(other=>other!==page);
    await expect(second.locator('#prompt')).toHaveValue(draft);await expect(second.locator('.app')).toHaveAttribute('data-layout','professional');
    await page.locator('#inspector-toggle').click();await expect(page.locator('#inspector')).toBeVisible();
    await page.locator('#layout-toggle').click();await expect(page.locator('.sidebar')).not.toBeVisible();
    await expect(second.locator('.sidebar')).toBeVisible();await expect(second.locator('.app')).toHaveAttribute('data-layout','professional');
    await second.locator('#layout-toggle').click();await expect(second.locator('.app')).toHaveAttribute('data-layout','focus');
    await page.locator('#layout-toggle').click();await expect(page.locator('#inspector')).toBeVisible();await expect(second.locator('.app')).toHaveAttribute('data-layout','focus');
    await page.locator('#theme-toggle').click();await expect(second.locator('.app')).toHaveAttribute('data-theme','dark');await expect(second.locator('.app')).toHaveAttribute('data-layout','focus');
    await second.reload();await expect(second.locator('.app')).toHaveAttribute('data-layout','focus');await expect(page.locator('.app')).toHaveAttribute('data-layout','professional');
    await page.locator('#theme-toggle').click();await expect(second.locator('.app')).toHaveAttribute('data-layout','focus');
    await second.screenshot({path:path.join(evidence,'independent-focus-window.png'),animations:'disabled',scale:'css'});
    await page.locator('#connection-state').click();await shot('standard-window-status');await page.keyboard.press('Escape');
    progress.stage('draft conflict guard');
    // Hold this renderer's polling while the other window saves a real conflicting edit.
    await page.evaluate(()=>{state.polling=true;});
    await second.locator('#prompt').fill('Saved from the other window');await expect(second.locator('#draft-state')).toHaveText('Saved');
    await page.locator('#prompt').fill('Keep my conflicting local draft');await page.locator('#new-window').click();
    await expect(page.locator('#toast')).toContainText(/another window|changed/i);assert.equal(app.windows().length,2);
    await expect(page.locator('#prompt')).toHaveValue('Keep my conflicting local draft');
    await page.getByRole('button',{name:'Resolve draft conflict',exact:true}).click();
    await page.getByRole('button',{name:'Load saved draft',exact:true}).click();await page.evaluate(()=>{state.polling=false;});
    progress.stage('real service restart');
    // Stop only this test's owned core, then exercise the real failed-read and reconnect path.
    const descriptor=JSON.parse(await fs.readFile(path.join(project,'.pantheon','desktop-runtime.json'),'utf8'));
    assert.equal(descriptor.workspace,await fs.realpath(project));assert.ok(Number.isInteger(descriptor.pid));
    process.kill(descriptor.pid,'SIGTERM');
    await page.waitForFunction(()=>document.querySelector('#connection-state').textContent==='Disconnected');
    await page.locator('#connection-state').click();await expect(panel.locator('.service-health')).toContainText('Unavailable');
    await expect(panel).toContainText('Could not refresh saved results');await shot('service-unavailable');
    await page.locator('#connection-reconnect').click();await expect(panel).not.toBeVisible();await expect(page.locator('#toast')).toContainText('Service reconnected');
    await expect(second.locator('#connection-state')).toHaveText('Local connected');
    await expect(second.locator('.app')).toHaveAttribute('data-layout','focus');
    assert.equal(providerCalls,explicitCalls,'Toolbar and window actions must not probe any provider');
    assert.deepEqual(errors,[]);
    await app.close();assert.equal(child.exitCode,0);progress.finish(true);
    await fs.writeFile(path.join(evidence,'result.json'),JSON.stringify({passed:true,packaged:!!process.env.PANTHEON_TEST_EXECUTABLE,provider_fixture_calls:providerCalls,paid_api_calls:0,page_errors:errors,checks:['empty workspace','same-task draft saved before opening','failed draft save blocks new window and retains local text','saved verification and failure evidence','light dark and 820px layout','independent layouts and restoration','shared theme retains per-window layouts','reload retains per-window layout','status reconnect']},null,2));
    console.log('TOOLBAR_UI_PASS: status, saved API evidence, independent native windows, draft flush, empty workspace, themes and reconnect; zero paid APIs');
  }catch(error){await shot('failure').catch(()=>{});throw error;}
  finally{if(child.exitCode===null)await app.close().catch(()=>child.kill('SIGKILL'));fixture.closeAllConnections();await new Promise(resolve=>fixture.close(resolve));progress.finish(false);}
}
main().catch(error=>{console.error(error);process.exitCode=1;});
