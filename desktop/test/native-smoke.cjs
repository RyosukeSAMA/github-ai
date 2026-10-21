'use strict';
const {_electron:electron}=require('playwright');
const {expect} = require('playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const http = require('node:http');
const os = require('node:os');
const repo = path.resolve(__dirname,'../..');
async function main(){
  await fs.mkdir(path.join(repo,'dist','desktop-evidence'),{recursive:true});await fs.rm(path.join(repo,'dist','desktop-evidence','native-smoke.json'),{force:true});
  const root = await fs.mkdtemp(path.join(os.tmpdir(),'pantheon-native-'));
  const project=path.join(root,'Research & product ideas - Pantheon');await fs.mkdir(project);const workspace=await fs.realpath(project);await fs.writeFile(path.join(workspace,'notes.txt'),'Original project note.\n');
  let calls=0;
  const provider=http.createServer((req,res)=>{
    let body='';req.on('data',data=>body+=data);req.on('end',()=>{
      if(req.method==='GET'){res.setHeader('content-type','application/json');res.end(JSON.stringify({data:[{id:'test-chat',object:'model'}]}));return;}
      calls++;const input=JSON.parse(body||'{}');const content=input.messages?.some(item=>item.content?.includes('Reply with exactly'))?'ok':'# Native task complete\n\nThe shared core produced this result.\n\n```html\n<h1>Pantheon native output</h1>\n```';
      if(input.stream){res.writeHead(200,{'content-type':'text/event-stream'});res.write('data: '+JSON.stringify({id:'local',object:'chat.completion.chunk',model:'test-chat',choices:[{index:0,delta:{content},finish_reason:null}]})+'\n\n');res.write('data: '+JSON.stringify({id:'local',choices:[{index:0,delta:{},finish_reason:'stop'}],usage:{prompt_tokens:15,completion_tokens:25,total_tokens:40}})+'\n\n');res.end('data: [DONE]\n\n');}
      else {res.setHeader('content-type','application/json');res.end(JSON.stringify({id:'local',object:'chat.completion',model:'test-chat',choices:[{index:0,message:{role:'assistant',content},finish_reason:'stop'}],usage:{prompt_tokens:15,completion_tokens:25,total_tokens:40}}));}
    });
  });await new Promise(resolve=>provider.listen(0,'127.0.0.1',resolve));
  const url='http://127.0.0.1:'+provider.address().port+'/v1';
  const executable=process.env.PANTHEON_TEST_EXECUTABLE || require('electron');
  const loader=path.join(path.dirname(require.resolve('playwright-core/package.json')),'lib','server','electron','loader.js');
  const args=process.env.PANTHEON_TEST_EXECUTABLE?['-r',loader]:[path.join(repo,'desktop')];
  const env={...process.env,PANTHEON_DESKTOP_TEST:'1',PANTHEON_DESKTOP_WORKSPACE:'',PANTHEON_DESKTOP_USER_DATA:path.join(root,'user-data'),PANTHEON_DATA_DIR:path.join(root,'data'),PANTHEON_STATE_MODE:'workspace',PANTHEON_MODEL_DOCS_SYNC:'0',PANTHEON_DESKTOP_PYTHON:process.env.PANTHEON_DESKTOP_PYTHON || path.join(repo,'.venv','bin','python')};
  for(const name of ['OPENAI_API_KEY','ANTHROPIC_API_KEY','DEEPSEEK_API_KEY','PANTHEON_CONFIG','PANTHEON_DESKTOP_TOKEN'])delete env[name];
  let application;
  const deadline=setTimeout(()=>{application?.process().kill('SIGKILL');provider.closeAllConnections();console.error('Native test exceeded its 240-second deadline.');process.exit(1);},240000);deadline.unref();
  const failures=[];
  const launch=async(onboarding=false)=>{
    const handle=await electron.launch({executablePath:executable,args,env,timeout:30000});const child=handle.process();
    await handle.evaluate(({dialog},{workspace,onboarding})=>{
      dialog.showMessageBox=async()=>({response:1});
      const choices=onboarding?[{canceled:true,filePaths:[]},{canceled:false,filePaths:[workspace+'-missing']},{canceled:false,filePaths:[workspace]}]:[];
      dialog.showOpenDialog=async()=>{await new Promise(resolve=>setTimeout(resolve,350));return choices.shift()||{canceled:true,filePaths:[]};};
    },{workspace,onboarding});
    application={process:()=>child,windows:()=>handle.windows(),resize:(width,height)=>handle.evaluate(({BrowserWindow},{width,height})=>BrowserWindow.getAllWindows()[0].setSize(width,height),{width,height}),close:async()=>{let timer;try{await Promise.race([handle.close(),new Promise((_,reject)=>{timer=setTimeout(()=>{child.kill('SIGKILL');reject(new Error('Native quit exceeded 20 seconds.'));},20000);})]);assert.equal(child.exitCode,0,'Native application must exit normally');}finally{clearTimeout(timer);}}};
    const page=await handle.firstWindow();page.setDefaultTimeout(20000);page.on('pageerror',error=>failures.push(String(error)));
    if(!onboarding)await page.waitForFunction(()=>document.querySelector('#connection-state').textContent==='Local connected');if(process.env.PANTHEON_TEST_EXECUTABLE)assert.equal((await page.evaluate(()=>window.pantheonDesktop.info())).packaged,true,'Must exercise the packaged application');
    return page;
  };
  try {
    let page=await launch(true);
    await expect(page.locator('#welcome-workspace')).toHaveText('Choose project');await expect(page.locator('#welcome-connections')).toBeDisabled();
    await page.waitForFunction(()=>[...document.querySelectorAll('#welcome img')].every(image=>image.complete&&image.naturalWidth>0));await page.screenshot({path:path.join(repo,'dist','desktop-evidence','welcome-art.png')});
    await page.locator('#welcome-workspace').click();await expect(page.locator('#welcome-workspace')).toBeDisabled();await expect(page.locator('#toast')).toContainText('Project selection canceled');await expect(page.locator('#connection-state')).toHaveText('Not connected');
    await page.locator('#welcome-workspace').click();await expect(page.locator('#project-feedback-title')).toHaveText('Could not open project');await expect(page.locator('#project-feedback-detail')).toContainText('folder is no longer available');await expect(page.locator('#connection-state')).toHaveText('Not connected');
    await page.waitForTimeout(4500);await expect(page.locator('#project-feedback')).toBeVisible();await page.screenshot({path:path.join(repo,'dist','desktop-evidence','project-error.png')});
    await page.evaluate(()=>{window.workspaceProgress=[];window.pantheonDesktop.onWorkspaceStatus(value=>window.workspaceProgress.push(value.phase));});
    await page.locator('#project-retry').click();await expect(page.locator('#connection-state')).toHaveText('Local connected',{timeout:30000});await expect(page.locator('#project-feedback-title')).toHaveText('Project connected');await expect(page.locator('#project-feedback-path')).toHaveText(workspace);await expect(page.locator('#project-path')).toHaveText(workspace);await expect(page.locator('#onboarding-project')).toHaveAttribute('data-state','complete');await expect(page.locator('#welcome-connections')).toHaveClass(/primary/);assert.ok((await page.evaluate(()=>window.workspaceProgress)).includes('opening'));
    await expect(page.locator('#workspace-folder-name')).toHaveText(path.basename(workspace));await expect(page.locator('#workspace-card-path')).toHaveText(workspace);await expect(page.locator('#workspace-card-path')).toBeVisible();await expect(page.locator('#workspace-card-badge')).toContainText('connected');await expect(page.locator('#project-glyph svg')).toBeVisible();
    await page.screenshot({path:path.join(repo,'dist','desktop-evidence','project-connected.png')});
    await page.locator('#theme-toggle').click();await page.screenshot({path:path.join(repo,'dist','desktop-evidence','welcome-dark.png')});await page.locator('#theme-toggle').click();
    for(const [width,height] of [[1024,800],[820,720]]){await application.resize(width,height);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Welcome must fit the native window');await expect(page.locator('#workspace-folder-name')).toBeVisible();await expect(page.locator('#inspector')).not.toBeVisible();}
    await page.screenshot({path:path.join(repo,'dist','desktop-evidence','welcome-narrow.png')});await application.resize(1440,1000);
    await page.locator('#workspace-folder').click();await expect(page.locator('#file-tree')).toContainText('notes.txt');await page.waitForTimeout(2200);await expect(page.locator('#files-pane')).toBeVisible();await page.locator('[data-view=work]').click();await page.locator('#welcome-connections').click();
    await page.locator('#provider').selectOption('deepseek');await page.locator('#base-url').fill(url);await page.locator('#test-model').fill('test-chat');await page.locator('#api-key').fill('local-test-only');
    await page.getByRole('button',{name:'Save connection',exact:true}).click();
    await expect(page.locator('#connection-message')).toContainText('Connection saved');
    await page.locator('#use-provider').click();await page.getByRole('button',{name:'Update defaults',exact:true}).click();
    await expect(page.locator('#toast')).toContainText('defaults saved');await page.locator('#connections-dialog [data-close]').click();
    await expect(page.locator('#welcome-task')).toBeVisible();await page.locator('#welcome-task').click();await page.locator('#mode').selectOption('role:hephaestus');await page.locator('#prompt').fill('Build native sample');await page.locator('#run').click();
    await expect(page.locator('#task-state')).toHaveText('completed',{timeout:30000});await expect(page.locator('#messages')).toContainText('Native task complete');
    assert.equal(calls,1,'No unexpected provider calls');
    const taskLink=page.locator('#task-list').getByRole('button',{name:'Build native sample',exact:true});await taskLink.focus();await page.waitForTimeout(2200);await expect(taskLink).toBeFocused();
    await page.reload();await expect(page.locator('#messages')).toContainText('Native task complete');
    await page.locator('[data-view=library]').click();await expect(page.locator('#artifact-grid')).toContainText('Generated HTML');
    const artifact=page.locator('.artifact-card').filter({hasText:'Generated HTML'});await artifact.getByRole('button',{name:'Preview',exact:true}).click();
    await expect(page.locator('iframe.artifact-preview')).toBeVisible();await page.locator('#info-dialog [data-close]').first().click();
    await artifact.getByRole('button',{name:'Review and save',exact:true}).click();await page.locator('#text-input').fill('created.html');await page.getByRole('button',{name:'Continue',exact:true}).click();
    await expect(page.locator('#review-diff')).toContainText('Pantheon native output');await page.locator('#review-accept').click();await expect(page.locator('#review-state')).toContainText('Saved to created.html');
    assert.match(await fs.readFile(path.join(workspace,'created.html'),'utf8'),/Pantheon native output/);
    await page.locator('[data-view=files]').click();await page.getByRole('button',{name:'notes.txt',exact:true}).click();await page.locator('#file-editor').fill('Edited in native app.\n');
    await fs.writeFile(path.join(workspace,'notes.txt'),'Changed outside.\n');await page.locator('#prepare-file').click();await expect(page.locator('#toast')).toContainText('changed outside');
    assert.equal(await fs.readFile(path.join(workspace,'notes.txt'),'utf8'),'Changed outside.\n');
    await page.locator('#reload-file').click();await expect(page.locator('#file-editor')).toHaveValue('Changed outside.\n');await page.locator('#file-editor').fill('Reviewed native edit.\n');await page.locator('#prepare-file').click();await expect(page.locator('#review-diff')).toContainText('+Reviewed native edit.');await page.locator('#review-accept').click();await expect(page.locator('#review-state')).toContainText('Saved to notes.txt');assert.equal(await fs.readFile(path.join(workspace,'notes.txt'),'utf8'),'Reviewed native edit.\n');
    await page.locator('[data-view=tasks]').click();await page.locator('#task-filter').fill('shared core');await expect(page.locator('#mission-list')).toContainText('Build native sample');
    await page.locator('#task-filter').fill('');await page.locator('#new-window').click();await expect.poll(()=>application.windows().length).toBe(2);
    const second=application.windows()[1];await expect(second.locator('#task-title')).toHaveText('Build native sample');
    await page.locator('[data-view=capabilities]').click();
    for(const capability of ['skills','plugins','mcp/servers','memory','channels','media','git']){await page.locator('[data-cap=\"'+capability+'\"]').click();await expect(page.locator('#capability-content')).not.toHaveText('');}
    await page.locator('[data-cap=channels]').click();await page.getByRole('button',{name:'Configure Telegram',exact:true}).click();await expect(page.locator('#info-dialog')).toContainText('Allowed user IDs');await page.locator('#info-dialog [data-close]').first().click();
    await page.locator('[data-view=work]').click();await page.locator('#prompt').fill('Window one draft');await expect(page.locator('#draft-state')).toHaveText('Saved');
    await second.locator('#prompt').fill('A conflicting second draft');await expect(second.locator('#global-notice')).toContainText('Resolve draft conflict');await second.getByRole('button',{name:'Resolve draft conflict',exact:true}).click();await expect(second.locator('#info-dialog')).toContainText('Window one draft');await second.getByRole('button',{name:'Load saved draft',exact:true}).click();await expect(second.locator('#prompt')).toHaveValue('Window one draft');
    await page.locator('#connections-open').click();
    for(const providerName of ['openai','anthropic']){await page.locator('#provider').selectOption(providerName);await page.locator('#base-url').fill(url);await page.locator('#test-model').fill('test-chat');await page.locator('#api-key').fill('local-test-only');await page.getByRole('button',{name:'Save connection',exact:true}).click();await expect(page.locator('#connection-message')).toContainText('Connection saved');}
    await page.locator('#connections-dialog [data-close]').click();await page.locator('#models-open').click();await page.locator('[name=model-mode][value=mixed]').check();await page.locator('[data-role=hephaestus] select').selectOption('anthropic');await page.locator('[data-role=athena] select').selectOption('openai');await page.locator('#save-models').click();
    await page.locator('#new-task').click();await page.locator('#models-open').click();await expect(page.locator('[data-role=hephaestus] select')).toHaveValue('deepseek');await page.locator('#models-dialog [data-close]').first().click();await page.locator('#task-list').getByRole('button',{name:'Build native sample',exact:true}).click();await page.locator('#models-open').click();await expect(page.locator('[data-role=hephaestus] select')).toHaveValue('anthropic');await expect(page.locator('[data-role=athena] select')).toHaveValue('openai');await page.locator('#models-dialog [data-close]').first().click();
    await page.locator('[data-view=tasks]').click();await page.locator('#task-status').selectOption('attention');await expect(page.locator('#mission-list')).toContainText('No tasks match this view.');await page.locator('#task-status').selectOption('all');await page.locator('[data-view=work]').click();
    await page.locator('#project-open').click();await expect(page.locator('#toast')).toContainText('current project is unchanged');await expect(page.locator('#task-title')).toHaveText('Build native sample');await expect(page.locator('#prompt')).toHaveValue('Window one draft');
    const bypass=await page.evaluate(async()=>{try{await window.pantheonDesktop.api('/api/workspace/terminal/stream',{method:'POST',body:{command:'echo must-not-run'}});return '';}catch(error){return String(error);}});assert.match(bypass,/native confirmation/);
    await page.locator('#terminal-toggle').click();await page.locator('#terminal-command').fill('echo desktop-terminal-ok');await page.locator('#terminal-form').getByRole('button',{name:'Run once',exact:true}).click();await expect(page.locator('#terminal-output')).toContainText('desktop-terminal-ok');await page.locator('#terminal-close').click();
    await page.locator('#prompt').fill('Durable unsent prompt');await expect(page.locator('#draft-state')).toHaveText('Saved');await page.locator('#theme-toggle').click();
    await fs.mkdir(path.join(repo,'dist','desktop-evidence'),{recursive:true});await page.screenshot({path:path.join(repo,'dist','desktop-evidence','native-dark.png')});await page.locator('#theme-toggle').click();await page.screenshot({path:path.join(repo,'dist','desktop-evidence','native-light.png')});
    await application.close();application=null;page=await launch();await expect(page.locator('#messages')).toContainText('Native task complete');await expect(page.locator('#prompt')).toHaveValue('Durable unsent prompt');assert.equal(calls,1);
    assert.deepEqual(failures,[]);await application.close();application=null;console.log('NATIVE_SMOKE_PASS: shared-core request, durable restart, artifacts, sandbox preview, conflict-aware save, search and multiple windows, conflict resolution, model isolation, capabilities and confirmed terminal; no paid APIs');
    await fs.writeFile(path.join(repo,'dist','desktop-evidence','native-smoke.json'),JSON.stringify({passed:true,packaged:!!process.env.PANTHEON_TEST_EXECUTABLE,platform:process.platform,architecture:process.arch,provider_calls:calls,paid_api_calls:0,page_errors:failures,workspace:'isolated temporary test project'},null,2));
  }catch(error){if(application){const pages=application.windows();if(pages[0]){await fs.mkdir(path.join(repo,'dist','desktop-evidence'),{recursive:true});await pages[0].screenshot({path:path.join(repo,'dist','desktop-evidence','failure.png')}).catch(()=>{});console.error((await pages[0].locator('body').innerText()).slice(0,8000));}}throw error;}
  finally {if(application)await application.close().catch(()=>{});await new Promise(resolve=>provider.close(resolve));clearTimeout(deadline);}
}
main().catch(error=>{console.error(error);process.exitCode=1;});
