'use strict';
// Native visual/interaction checks. Dummy keys are saved in an isolated project;
// no API test, model refresh or task run is requested.
const {_electron: electron} = require('playwright');
const {expect} = require('playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const {smokeTimeout,smokeProgress}=require('./smoke-support.cjs');
const repo = path.resolve(__dirname, '../..');

async function main() {
  const timeoutMs=smokeTimeout(180000);
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'pantheon-provider-ui-'));
  const project = path.join(root, 'Garden workspace'); await fs.mkdir(project);
  const evidence = path.join(repo, 'dist', 'provider-ui-evidence'); await fs.mkdir(evidence, {recursive: true});
  await fs.rm(path.join(evidence,'verification.json'),{force:true});
  const env = {...process.env, PANTHEON_DESKTOP_TEST: '1', PANTHEON_DESKTOP_WORKSPACE: project,
    PANTHEON_DESKTOP_USER_DATA: path.join(root, 'profile'), PANTHEON_DATA_DIR: path.join(root, 'data'),
    PANTHEON_STATE_MODE: 'workspace', PANTHEON_MODEL_DOCS_SYNC: '0',
    PANTHEON_DESKTOP_PYTHON: process.env.PANTHEON_DESKTOP_PYTHON || path.join(repo, '.venv', 'bin', 'python')};
  for (const key of ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'DEEPSEEK_API_KEY', 'PANTHEON_CONFIG', 'PANTHEON_DESKTOP_TOKEN']) delete env[key];
  const executablePath = process.env.PANTHEON_TEST_EXECUTABLE || require('electron');
  const loader = path.join(path.dirname(require.resolve('playwright-core/package.json')), 'lib', 'server', 'electron', 'loader.js');
  const application = await electron.launch({executablePath, args: process.env.PANTHEON_TEST_EXECUTABLE ? ['-r', loader] : [path.join(repo, 'desktop')], env});
  const child=application.process(),progress=smokeProgress('provider-ui',evidence,timeoutMs,()=>child.kill('SIGKILL'));
  const errors = [], page = await application.firstWindow(); page.setDefaultTimeout(15000);
  page.on('pageerror', error => errors.push(String(error)));
  const screenshot = async name => {await page.mouse.move(10, 60); await page.screenshot({path: path.join(evidence, name + '.png'), animations: 'disabled', scale: 'css'});};
  const resize = (width, height) => application.evaluate(({BrowserWindow}, size) => BrowserWindow.getAllWindows()[0].setSize(size.width, size.height), {width, height});
  const mark = (target, id) => expect(target.locator('.model-picker-mark .provider-mark')).toHaveAttribute('data-provider', id);
  try {
    await expect(page.locator('#connection-state')).toHaveText('Local connected', {timeout: 30000});
    if (process.env.PANTHEON_TEST_EXECUTABLE) assert.equal((await page.evaluate(() => window.pantheonDesktop.info())).packaged, true);
    await resize(1440, 1000); await page.locator('#connections-open').click();
    for (const provider of ['deepseek', 'openai', 'anthropic', 'ollama']) {
      await page.locator('#provider').selectOption(provider);
      await mark(page.locator('#connection-form'), provider);
      if (provider !== 'ollama') await page.locator('#api-key').fill('local-preview-only-never-send');
      await page.getByRole('button', {name: 'Save connection', exact: true}).click();
      await expect(page.locator('#connection-message')).toContainText('Connection saved');
    }
    progress.stage('saved provider connections');
    await expect(page.locator('#connection-summary .connection-pill')).toHaveCount(4);
    await page.locator('#provider').selectOption('deepseek');
    await page.locator('#connection-form').scrollIntoViewIfNeeded();
    await page.waitForFunction(() => [...document.querySelectorAll('.provider-mark img')].every(image => image.complete && image.naturalWidth > 0));
    await screenshot('connections-light');
    progress.stage('provider and searchable model menus');
    await page.locator('#provider').click();
    await expect.poll(() => page.locator('#provider').evaluate(select => select.matches(':open'))).toBe(true);
    await screenshot('providers-light'); await page.keyboard.press('Escape');
    await page.locator('#test-model').focus(); await page.keyboard.press('ArrowDown');
    await expect(page.locator('#test-model')).toHaveAttribute('aria-expanded', 'true');
    await expect(page.locator('.model-menu:popover-open .model-menu-option').first()).toBeVisible();
    await screenshot('model-menu-light'); await page.keyboard.press('Escape');
    await expect(page.locator('#connections-dialog')).toBeVisible();
    await page.locator('#use-provider').click(); await page.getByRole('button', {name: 'Update defaults', exact: true}).click();
    await page.locator('#new-task').click(); await page.locator('#models-open').click(); await expect(page.locator('#models-dialog')).toBeVisible();
    await page.locator('[name=model-mode][value=mixed]').check();
    for (const [role, provider] of [['hephaestus', 'anthropic'], ['athena', 'openai'], ['apollo', 'ollama']]) {
      await page.locator('[data-role=' + role + '] select').selectOption(provider);
      await mark(page.locator('[data-role=' + role + ']'), provider);
    }
    const field = page.locator('[data-role=athena] input');
    await field.fill('a-unique-preview-custom-model'); await page.keyboard.press('ArrowDown');
    const custom = page.locator('.model-menu:popover-open [data-model=a-unique-preview-custom-model]');
    await expect(custom).toContainText('Custom model ID'); await custom.click();
    await expect(field).toHaveValue('a-unique-preview-custom-model');
    await expect(field).toHaveAttribute('aria-expanded', 'false');
    await page.locator('[data-role=athena] select').selectOption('deepseek');
    await page.locator('[data-role=athena] select').selectOption('openai');
    await field.focus(); await page.keyboard.press('ArrowDown'); await page.keyboard.press('Enter');
    await expect(field).toHaveAttribute('aria-expanded', 'false');
    assert.ok(await field.inputValue());
    await screenshot('assignments-light');
    await page.locator('[data-role=athena] .model-picker-toggle').click(); await screenshot('role-model-menu-light');
    await page.keyboard.press('Escape');
    await page.locator('#models-dialog [data-close]').first().click(); await page.locator('#theme-toggle').click();
    progress.stage('single and mixed assignments');
    await page.locator('#models-open').click(); await expect(page.locator('#models-dialog')).toBeVisible(); await page.locator('[name=model-mode][value=mixed]').check();
    for (const [role, provider] of [['hephaestus', 'anthropic'], ['athena', 'openai'], ['apollo', 'ollama']]) await page.locator('[data-role=' + role + '] select').selectOption(provider);
    await screenshot('assignments-dark');
    progress.stage('narrow window');
    await resize(820, 720);
    assert.ok(await page.locator('#models-dialog').evaluate(dialog => dialog.scrollWidth <= dialog.clientWidth));
    await expect(page.locator('#save-models')).toBeInViewport();
    await page.locator('[data-role=apollo] .model-picker-toggle').click();
    assert.ok(await page.locator('.model-menu:popover-open').evaluate(menu => {const rect = menu.getBoundingClientRect(); return rect.left >= 0 && rect.right <= innerWidth && rect.top >= 0 && rect.bottom <= innerHeight;}));
    await screenshot('assignments-narrow'); await page.keyboard.press('Escape');
    await resize(1440, 1000); await page.locator('#save-models').click();
    await expect(page.locator('#models-dialog')).not.toBeVisible(); await page.locator('#inspector-toggle').click();
    await expect(page.locator('#role-list .provider-mark[data-provider=anthropic]')).toBeVisible();
    await expect(page.locator('#role-list .provider-mark[data-provider=openai]')).toBeVisible();
    await expect(page.locator('#role-list .provider-mark[data-provider=ollama]')).toBeVisible();
    await page.locator('#setup-complete-dismiss').click(); await screenshot('council-dark');
    await page.locator('#theme-toggle').click(); await screenshot('council-light');
    await page.locator('#models-open').click(); await expect(page.locator('#models-dialog')).toBeVisible(); await page.locator('[name=model-mode][value=single]').check();
    await page.locator('[data-role=hermes] select').selectOption('deepseek');
    for (const role of ['hermes', 'hephaestus', 'athena', 'apollo']) await mark(page.locator('[data-role=' + role + ']'), 'deepseek');
    await page.locator('#models-dialog [data-close]').first().click();
    const saved = await page.evaluate(async () => (await window.pantheonDesktop.api('/api/desktop/sessions')).sessions);
    const choices = saved.find(item => item.overrides?.athena?.provider === 'openai');
    assert.equal(choices.overrides.hephaestus.provider, 'anthropic'); assert.equal(choices.overrides.apollo.provider, 'ollama');
    const unknown = await page.evaluate(() => providerMark('unknown-gateway').outerHTML); assert.ok(unknown.includes('<svg')); assert.ok(!unknown.includes('<img'));
    const usage = await page.evaluate(async () => window.pantheonDesktop.api('/api/usage/details')); assert.equal(usage.groups.length, 0);
    assert.deepEqual(errors, []);
    await application.close();assert.equal(child.exitCode,0,'Provider preview app must exit normally');progress.finish(true);
    await fs.writeFile(path.join(evidence, 'verification.json'), JSON.stringify({passed: true, packaged: !!process.env.PANTHEON_TEST_EXECUTABLE, platform: process.platform, paid_api_calls: 0, task_runs: 0, page_errors: errors, providers: ['deepseek', 'openai', 'anthropic', 'ollama'], workspace: 'isolated temporary project'}, null, 2));
    console.log('PROVIDER_UI_PASS: four local logos, searchable keyboard menus, custom IDs, single/mixed assignments, cancel retention, context, themes and narrow window; no provider calls');
  } catch (error) {if(child.exitCode===null)await screenshot('failure').catch(() => {}); throw error;}
  finally {try{if(child.exitCode===null)await application.close();}finally{progress.finish(false);}}
}
main().catch(error => {console.error(error); process.exitCode = 1;});
