'use strict';
const $ = selector => document.querySelector(selector);
const app = $('.app');
const sampleTasks = [
  {id:'launch', title:'发布准备', heading:'把复杂任务，交给合适的神。', prompt:'审查项目，整理一份可以执行的上线前检查清单。', state:'已完成 · 示例'},
  {id:'research', title:'比较数据存储方案', heading:'先把证据放到桌面上。', prompt:'比较两种数据存储方案，并记录适用条件与证据来源。', state:'待继续 · 示例'},
  {id:'page', title:'制作产品介绍页', heading:'从目标，到可以预览的成果。', prompt:'为示例产品制作一个清晰、克制的介绍页面。', state:'草稿 · 示例'},
];
let selectedTask = 'launch', mode = 'auto', running = false, timer = null, modelsMode = 'single';
const entries = [
  ['hermes','H','Hermes','任务拆解与角色分工','把目标、约束和交付要求整理成一个有序计划。'],
  ['athena','A','Athena','研究与证据核对','收集需要核对的项目，标记未验证的信息。'],
  ['forge','He','Hephaestus','执行路径与恢复检查','复核执行、失败状态和恢复边界，整理可操作清单。'],
  ['hermes','H','Hermes','汇总成果','把阶段输出整理成可交付的项目文档。'],
];
sampleTasks.forEach(task => { task.activities = task.id === 'launch' ? entries.map(item => [...item]) : []; });
const fileText = {
  checklist:'# 上线前检查清单（示例）\n\n- [ ] 确认安装与模型配置入口\n- [ ] 检查失败状态与任务恢复\n- [ ] 留存测试记录和验证边界\n\n此文件仅为原型展示，不代表真实验收。',
  notes:'任务：审查示例项目\n\n协作：Hermes → Athena → Hephaestus → Hermes\n\n边界：\n未读取本机工作区\n未调用供应商 API\n未执行工具或写入文件\n\n此记录仅保存在原型内存中。',
};
function toast(text) { $('#toast').textContent = text; $('#toast').hidden = false; clearTimeout(toast.timer); toast.timer = setTimeout(() => $('#toast').hidden = true, 3300); }
function openDialog(id) { const dialog = $(id); if (!dialog.open) dialog.showModal(); }
function info(title, text) { $('#info-title').textContent = title; $('#info-text').textContent = text; openDialog('#info-dialog'); }
function renderTasks() {
  $('#task-list').replaceChildren();
  sampleTasks.forEach(task => {
    const button = document.createElement('button');
    button.classList.toggle('selected', selectedTask === task.id);
    button.setAttribute('aria-current', selectedTask === task.id ? 'true' : 'false');
    const mark = document.createElement('span'); mark.className = 'status-dot' + (task.id === 'launch' ? '' : ' neutral');
    const title = document.createElement('span'); title.textContent = task.title;
    button.append(mark, title); button.onclick = () => selectTask(task.id); $('#task-list').appendChild(button);
  });
  $('.count').textContent = sampleTasks.length;
}
function selectTask(id) {
  if (running) { toast('请先停止当前示例任务。'); return; }
  selectedTask = id;
  const task = sampleTasks.find(item => item.id === id);
  $('#breadcrumb-task').textContent = task.title; $('#task-title').textContent = task.heading;
  $('#task-subtitle').textContent = task.prompt; $('#task-state').textContent = task.state;
  document.querySelectorAll('.route-check').forEach(item => item.textContent = task.state.startsWith('已完成') ? '✓' : '·');
  renderTasks(); renderActivity(); updateModelTags(); setView('work'); setTab(id === 'launch' ? 'result' : 'activity');
}
function renderActivity() {
  $('#activity-list').replaceChildren();
  const activity = sampleTasks.find(task => task.id === selectedTask).activities || [];
  $('#activity-tab span').textContent = activity.length;
  activity.forEach(([kind, mark, name, title, description], index) => {
    const li = document.createElement('li');
    const avatar = document.createElement('span'); avatar.className = `role-mark ${kind}`; avatar.textContent = mark;
    const content = document.createElement('div');
    const strong = document.createElement('strong'); strong.textContent = `${name} · ${title}`;
    const p = document.createElement('p'); p.textContent = description;
    const small = document.createElement('small'); small.textContent = `阶段 ${index + 1} · 示例记录`;
    content.append(strong, p, small); li.append(avatar, content); $('#activity-list').appendChild(li);
  });
}
function addActivity(title, description) { const task = sampleTasks.find(item => item.id === selectedTask); (task.activities ||= []).push(['hermes','H','Pantheon',title,description]); renderActivity(); }
function setTab(name) {
  $('#automation-pane').hidden = true;
  ['result','activity','files'].forEach(key => {
    $('#' + key + '-pane').hidden = key !== name;
    $('#' + key + '-tab').setAttribute('aria-selected', String(key === name));
    $('#' + key + '-tab').tabIndex = key === name ? 0 : -1;
  });
}
function setView(name) {
  document.querySelectorAll('[data-view]').forEach(button => button.classList.toggle('selected', button.dataset.view === name));
  if (name === 'files') setTab('files');
  else if (name === 'automation') { ['result','activity','files'].forEach(key => $('#' + key + '-pane').hidden = true); $('#automation-pane').hidden = false; }
  else setTab('result');
}
function showInspector(show) { app.classList.toggle('no-inspector', !show); app.classList.toggle('show-inspector', show); $('#inspector-toggle').setAttribute('aria-pressed', String(show)); }
function showTerminal(show) { $('#terminal-drawer').hidden = !show; $('#terminal-toggle').setAttribute('aria-expanded', String(show)); }
function updateModelTags() { const providers = sampleTasks.find(task => task.id === selectedTask).modelProviders || []; document.querySelectorAll('.inspector-role .text-tag').forEach((tag,index) => tag.textContent = providers[index] ? providers[index] + ' · 默认' : '默认模型'); }
function showModels() { renderModels(); openDialog('#models-dialog'); }
function renderModels() {
  $('#model-rows').replaceChildren();
  ['Hermes','Athena','Hephaestus','Apollo'].forEach((name, index) => {
    const row = document.createElement('label'); row.className = 'model-row';
    const label = document.createElement('span'); label.textContent = name;
    const small = document.createElement('small'); small.textContent = '示例 · 未连接'; label.appendChild(small);
    const select = document.createElement('select'); select.setAttribute('aria-label', name + ' 示例供应商');
    ['DeepSeek','OpenAI','Anthropic'].forEach(provider => { const option = document.createElement('option'); option.textContent = provider; select.appendChild(option); });
    select.selectedIndex = modelsMode === 'single' ? 0 : index % 3;
    select.onchange = () => { if (modelsMode === 'single') $('#model-rows').querySelectorAll('select').forEach(item => item.value = select.value); };
    row.append(label, select); $('#model-rows').appendChild(row);
  });
}
function endRun(stopped) {
  clearInterval(timer); timer = null; running = false;
  const task = sampleTasks.find(item => item.id === selectedTask);
  task.state = stopped ? '已停止 · 示例' : '已完成 · 示例'; $('#task-state').textContent = task.state;
  $('#run-demo').textContent = '发送示例任务 ↑'; $('#run-demo').classList.remove('stopping');
  document.querySelectorAll('.route-check').forEach(item => item.textContent = stopped ? '·' : '✓');
  addActivity(stopped ? '停止示例运行' : '示例流程结束', '这是本地交互演示，没有发送真实请求或执行工具。');
  if (!stopped) setTab('result');
  toast(stopped ? '示例已停止；没有任何真实任务被取消。' : '示例流程完成；没有产生模型费用。');
}
function runDemo() {
  if (running) { endRun(true); return; }
  const prompt = $('#prompt').value.trim();
  if (!prompt) { $('#prompt').focus(); toast('先写下一个示例任务。'); return; }
  const task = sampleTasks.find(item => item.id === selectedTask); task.prompt = prompt;
  $('#task-subtitle').textContent = prompt; $('#prompt').value = ''; running = true; setTab('activity');
  $('#run-demo').textContent = '停止示例 ■'; $('#task-state').textContent = '正在规划 · 示例';
  const stages = ['正在规划 · 示例','角色执行 · 示例','汇总成果 · 示例']; let index = 0;
  document.querySelectorAll('.route-check').forEach(item => item.textContent = '·');
  timer = setInterval(() => {
    document.querySelectorAll('.route-check')[index].textContent = '✓'; index++;
    if (index === stages.length) endRun(false); else $('#task-state').textContent = stages[index];
  }, 850);
}
const commands = [
  ['新建示例任务','⌘ N',() => openDialog('#new-dialog')],
  ['查看项目文件','文件',() => setView('files')],
  ['查看协作记录','任务',() => setTab('activity')],
  ['分配角色模型','模型',showModels],
  ['展开终端抽屉','终端',() => showTerminal(true)],
  ['切换外观','主题',() => $('#theme-toggle').click()],
];
function renderCommands(query = '') {
  $('#command-list').replaceChildren();
  commands.filter(([name]) => name.includes(query.trim())).forEach(([name, shortcut, action]) => {
    const button = document.createElement('button'); const text = document.createElement('span'); text.textContent = name;
    const key = document.createElement('kbd'); key.textContent = shortcut; button.append(text, key);
    button.onclick = () => { $('#palette').close(); action(); }; $('#command-list').appendChild(button);
  });
}
function openPalette() { renderCommands(); $('#command-search').value = ''; openDialog('#palette'); $('#command-search').focus(); }
document.querySelectorAll('[data-close]').forEach(button => button.onclick = () => button.closest('dialog').close());
document.querySelectorAll('[data-tab]').forEach(button => button.onclick = () => setTab(button.dataset.tab));
document.querySelectorAll('[data-view]').forEach(button => button.onclick = () => setView(button.dataset.view));
document.querySelectorAll('[data-mode]').forEach(button => button.onclick = () => { mode = button.dataset.mode; document.querySelectorAll('[data-mode]').forEach(item => item.classList.toggle('selected', item === button)); toast(mode === 'auto' ? '示例：Hermes 自动选择角色。' : '示例：多角色协作；实际使用量随任务而变。'); });
document.querySelectorAll('[data-file]').forEach(button => button.onclick = () => { document.querySelectorAll('[data-file]').forEach(item => item.classList.toggle('selected', item === button)); $('#file-content').textContent = fileText[button.dataset.file]; });
document.querySelectorAll('[name="model-mode"]').forEach(input => input.onchange = () => { modelsMode = input.value; renderModels(); });
$('#new-task').onclick = () => openDialog('#new-dialog');
$('#new-form').onsubmit = event => {
  event.preventDefault(); if (running) { toast('请先停止当前示例任务。'); return; }
  const prompt = $('#new-prompt').value.trim(); if (!prompt) return;
  const task = {id:'task-'+Date.now(),title:prompt.slice(0,16),heading:'准备开始一项新工作。',prompt,state:'草稿 · 示例'};
  sampleTasks.unshift(task); $('#new-dialog').close(); $('#new-prompt').value = ''; selectTask(task.id); $('#prompt').value = prompt; $('#prompt').focus();
};
$('#theme-toggle').onclick = () => { app.dataset.theme = app.dataset.theme === 'dark' ? 'light' : 'dark'; $('#theme-toggle').setAttribute('aria-pressed', String(app.dataset.theme === 'dark')); };
$('#inspector-toggle').onclick = () => showInspector($('#inspector-toggle').getAttribute('aria-pressed') !== 'true');
$('#inspector-close').onclick = () => showInspector(false);
$('#terminal-toggle').onclick = () => showTerminal($('#terminal-drawer').hidden);
$('#terminal-close').onclick = () => showTerminal(false);
$('#terminal-simulate').onclick = () => $('#terminal-output').textContent += '\n[示例] 检查记录已显示。没有运行 shell 命令。';
$('#model-open').onclick = $('#inspector-model').onclick = $('#connection-open').onclick = showModels;
$('#save-models').onclick = () => { sampleTasks.find(task => task.id === selectedTask).modelProviders = [...$('#model-rows').querySelectorAll('select')].map(select => select.value); updateModelTags(); $('#models-dialog').close(); toast('模型分配已应用到原型；没有保存真实连接。'); };
$('#mock-connections').onclick = () => { $('#models-dialog').close(); info('连接管理与角色模型分开','桌面端将共用已实现的连接保存、启停、引用检查和删除能力。这个原型不收集 API Key。'); };
$('#approval-open').onclick = () => openDialog('#approval-dialog');
$('#allow-approval').onclick = $('#deny-approval').onclick = event => { const allowed = event.target.id === 'allow-approval'; $('#approval-dialog').close(); addActivity(allowed ? '示例审批：允许一次' : '示例审批：已拒绝','没有执行任何命令；真实应用会在工具边界完成审批。'); setTab('activity'); toast(allowed ? '已记录示例授权；不会执行命令。' : '已记录示例拒绝。'); };
$('#run-demo').onclick = runDemo;
$('#palette-open').onclick = $('#search-tasks').onclick = openPalette;
$('#command-search').oninput = event => renderCommands(event.target.value);
$('#command-search').onkeydown = event => { if (event.key === 'Enter') { event.preventDefault(); $('#command-list button')?.click(); } if (event.key === 'ArrowDown') { event.preventDefault(); $('#command-list button')?.focus(); } };
$('#workspace-demo').onclick = $('#project-switch').onclick = () => info('工作区始终明确','实际桌面端需要用户选择项目目录。会话、工具权限和文件操作都绑定当前工作区；切换工作区不会偷偷复用其他目录的任务。');
$('#lifecycle-open').onclick = () => info('桌面应用的运行边界','后续实现将核对后台归属、避免重复服务、区分关闭窗口与退出服务，并在退出前处理进行中的任务。原型没有启动任何后台进程。');
$('#usage-preview').onclick = () => info('每一笔用量，都能追溯到工作','桌面端会读取共享核心已有的任务、角色、阶段和供应商用量。未返回 token 或未配置单价时继续显示未知，不把估算当成账单。');
$('#automation-preview').onclick = () => info('自动化需要明确启用','设计为显示本地时区、下一次运行和交付位置。未配置的规则不启动，不在关闭窗口后静默增加新任务。');
$('#attach-demo').onclick = () => info('附件进入明确的上下文','实际应用将共用图片/PDF/音频上传能力，并在发送前说明供应商与文件边界。原型不会打开文件选择器或读取本机文件。');
$('#copy-result').onclick = async () => { try { await navigator.clipboard.writeText(fileText.checklist); toast('已复制示例清单。'); } catch (_) { toast('当前预览未获得剪贴板权限，可在文件页查看原文。'); } };
document.addEventListener('keydown', event => { const mod = event.metaKey || event.ctrlKey; if (mod && event.key.toLowerCase() === 'k') { event.preventDefault(); openPalette(); } if (mod && event.key.toLowerCase() === 'n') { event.preventDefault(); openDialog('#new-dialog'); } });
$('.content-tabs').addEventListener('keydown', event => { const tabs = [...document.querySelectorAll('[role="tab"]')]; if (!tabs.includes(event.target)) return; const direction = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0; if (!direction) return; event.preventDefault(); const target = tabs[(tabs.indexOf(event.target)+direction+tabs.length)%tabs.length]; setTab(target.dataset.tab); target.focus(); });
renderTasks(); renderActivity(); $('#file-content').textContent = fileText.checklist;
const compactLayout = window.matchMedia('(max-width:1150px)');
compactLayout.addEventListener('change', event => showInspector(!event.matches));
if (compactLayout.matches) showInspector(false);
