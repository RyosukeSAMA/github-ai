'use strict';
const $ = selector => document.querySelector(selector);
const app = $('.app');
const taskTabs = ['result', 'activity', 'review', 'files'];
const globalViews = ['tasks', 'library', 'capabilities', 'automation'];
const entries = [
  ['hermes', 'H', 'Hermes', '任务拆解与角色分工', '把目标、约束和交付要求整理成一个有序计划。'],
  ['athena', 'A', 'Athena', '研究与证据核对', '收集需要核对的项目，标记未验证的信息。'],
  ['forge', 'He', 'Hephaestus', '执行路径与恢复检查', '复核执行、失败状态和恢复边界，整理可操作清单。'],
  ['hermes', 'H', 'Hermes', '汇总成果', '把阶段输出整理成可交付的项目文档。'],
];
const sampleTasks = [
  {id: 'launch', title: '发布准备', heading: '把复杂任务，交给合适的神。', prompt: '审查项目，整理一份可以执行的上线前检查清单。', state: '已完成 · 示例', activities: entries.map(item => [...item])},
  {id: 'research', title: '比较数据存储方案', heading: '先把证据放到桌面上。', prompt: '比较两种数据存储方案，并记录适用条件与证据来源。', state: '待继续 · 示例'},
  {id: 'page', title: '制作产品介绍页', heading: '从目标，到可以预览的成果。', prompt: '为示例产品制作一个清晰、克制的介绍页面。', state: '草稿 · 示例'},
];
const artifacts = [
  {title: '上线前检查清单', type: 'document', label: '文档', mark: 'M↓', task: 'launch', filename: 'launch-checklist.md', description: '入口、恢复与交付的检查记录。'},
  {title: '数据存储比较框架', type: 'research', label: '研究', mark: 'A', task: 'research', filename: 'research-outline.md', description: '比较条件、证据来源与待核对项。'},
  {title: '产品介绍页草图', type: 'web', label: '网页', mark: '</>', task: 'page', filename: 'index.html', description: '页面结构与内容的静态示例。'},
];
const fileText = {
  checklist: '# 上线前检查清单（示例）\n\n- [ ] 确认安装与模型配置入口\n- [ ] 检查失败状态与任务恢复\n- [ ] 留存测试记录和验证边界\n\n此文件仅为原型展示，不代表真实验收。',
  notes: '任务：审查示例项目\n\n协作：Hermes → Athena → Hephaestus → Hermes\n\n边界：\n未读取本机工作区\n未调用供应商 API\n未执行工具或写入文件\n\n此记录仅保存在原型内存中。',
};
let selectedTask = 'launch', currentView = 'work', layout = 'professional', artifactFilter = 'all';
let modelsMode = 'single';
const runs = new Map();
const task = () => sampleTasks.find(item => item.id === selectedTask);
sampleTasks.forEach(item => { item.activities ||= []; item.draft = ''; item.mode = 'auto'; });
function toast(text) {
  $('#toast').textContent = text; $('#toast').hidden = false;
  clearTimeout(toast.timer); toast.timer = setTimeout(() => { $('#toast').hidden = true; }, 3300);
}
function openDialog(id) { const dialog = $(id); if (!dialog.open) dialog.showModal(); }
function info(title, text) { $('#info-title').textContent = title; $('#info-text').textContent = text; openDialog('#info-dialog'); }
function make(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}
function renderTasks() {
  $('#task-list').replaceChildren();
  sampleTasks.forEach(item => {
    const button = make('button', selectedTask === item.id ? 'selected' : '');
    button.setAttribute('aria-current', String(selectedTask === item.id));
    const mark = make('span', 'status-dot' + (item.state.startsWith('已完成') || runs.has(item.id) ? '' : ' neutral'));
    button.append(mark, make('span', '', item.title)); button.onclick = () => selectTask(item.id);
    $('#task-list').append(button);
  });
  $('.count').textContent = sampleTasks.length;
  $('#running-count').textContent = runs.size;
  renderMissions();
}
function paintTask() {
  const item = task();
  if (!globalViews.includes(currentView)) $('#breadcrumb-task').textContent = item.title;
  $('#task-title').textContent = item.heading;
  $('#task-subtitle').textContent = item.prompt; $('#task-state').textContent = item.state;
  $('#prompt').value = item.draft || '';
  $('#run-demo').textContent = runs.has(item.id) ? '停止示例 ■' : '发送示例任务 ↑';
  const stage = runs.get(item.id)?.stage || 0;
  document.querySelectorAll('.route-check').forEach((element, index) => {
    element.textContent = item.state.startsWith('已完成') || (runs.has(item.id) && index < stage) ? '✓' : '·';
  });
  document.querySelectorAll('[data-mode]').forEach(button => button.classList.toggle('selected', button.dataset.mode === item.mode));
  $('#review-state').textContent = item.reviewState || '等待审阅 · 尚未写入任何文件';
  renderActivity(); updateModelTags(); renderFiles();
}
function selectTask(id) {
  task().draft = $('#prompt').value;
  selectedTask = id; paintTask(); renderTasks(); setView('work');
  setTab(id === 'launch' ? 'result' : 'activity');
}
function renderActivity() {
  $('#activity-list').replaceChildren();
  $('#activity-tab span').textContent = task().activities.length;
  task().activities.forEach(([kind, mark, name, title, description], index) => {
    const li = make('li'); const content = make('div');
    content.append(make('strong', '', `${name} · ${title}`), make('p', '', description), make('small', '', `阶段 ${index + 1} · 示例记录`));
    li.append(make('span', `role-mark ${kind}`, mark), content); $('#activity-list').append(li);
  });
}
function addActivity(title, description, id = selectedTask) {
  sampleTasks.find(item => item.id === id).activities.push(['hermes', 'H', 'Pantheon', title, description]);
  if (id === selectedTask) renderActivity();
}
function setTab(name) {
  if (globalViews.includes(currentView)) setView('work');
  taskTabs.forEach(key => {
    $('#' + key + '-pane').hidden = key !== name;
    $('#' + key + '-tab').setAttribute('aria-selected', String(key === name));
    $('#' + key + '-tab').tabIndex = key === name ? 0 : -1;
  });
  globalViews.forEach(key => $('#' + key + '-pane').hidden = true);
}
function setView(name) {
  currentView = name; app.dataset.surface = name;
  document.querySelectorAll('[data-view]').forEach(button => button.classList.toggle('selected', button.dataset.view === name));
  const global = globalViews.includes(name);
  const viewLabels = {tasks: '任务中心', library: '成果库', capabilities: '能力中心', automation: '自动化'};
  $('#breadcrumb-task').textContent = global ? viewLabels[name] : task().title;
  $('#approval-open').hidden = global;
  document.querySelectorAll('.task-heading, .council-route, .content-tabs, .composer').forEach(element => { element.hidden = global; });
  taskTabs.forEach(key => { $('#' + key + '-pane').hidden = true; });
  globalViews.forEach(key => { $('#' + key + '-pane').hidden = key !== name; });
  $('.content-scroll').scrollTop = 0;
  if (!global) setTab(name === 'files' ? 'files' : 'result');
  if (name === 'tasks') renderMissions();
  if (name === 'library') renderArtifacts();
}
function showInspector(show) {
  app.classList.toggle('no-inspector', !show); app.classList.toggle('show-inspector', show);
  $('#inspector-toggle').setAttribute('aria-pressed', String(show));
}
function setLayout(value) {
  layout = value; app.dataset.layout = value;
  $('#layout-toggle').textContent = value === 'focus' ? '专注布局' : '专业工作台';
  $('#layout-toggle').setAttribute('aria-pressed', String(value === 'focus'));
  showInspector(value !== 'focus' && !compactLayout.matches);
  if (value === 'focus') { showTerminal(false); if (currentView === 'capabilities') setView('work'); }
}
function showTerminal(show) { $('#terminal-drawer').hidden = !show; $('#terminal-toggle').setAttribute('aria-expanded', String(show)); }
function updateModelTags() {
  document.querySelectorAll('.inspector-role .text-tag').forEach((tag, index) => { tag.textContent = task().modelProviders?.[index] || '默认模型'; });
}
function showModels() {
  modelsMode = task().modelsMode || 'single';
  document.querySelectorAll('[name="model-mode"]').forEach(input => { input.checked = input.value === modelsMode; });
  $('#model-strategy').value = task().strategy || 'balanced'; renderModels(task().modelProviders); openDialog('#models-dialog');
}
function renderModels(providers) {
  $('#model-rows').replaceChildren();
  ['Hermes', 'Athena', 'Hephaestus', 'Apollo'].forEach((name, index) => {
    const row = make('label', 'model-row'); const label = make('span', '', name);
    label.append(make('small', '', '示例 · 未连接'));
    const select = make('select'); select.setAttribute('aria-label', name + ' 示例供应商');
    ['DeepSeek', 'OpenAI', 'Anthropic'].forEach(provider => select.append(make('option', '', provider)));
    select.value = providers?.[index] || (modelsMode === 'single' ? 'DeepSeek' : ['DeepSeek', 'OpenAI', 'Anthropic'][index % 3]);
    select.onchange = () => { if (modelsMode === 'single') $('#model-rows').querySelectorAll('select').forEach(other => { other.value = select.value; }); };
    row.append(label, select); $('#model-rows').append(row);
  });
}
function renderMissions() {
  $('#metric-running').textContent = runs.size;
  $('#metric-waiting').textContent = sampleTasks.filter(item => !runs.has(item.id) && !item.state.startsWith('已完成')).length;
  $('#metric-completed').textContent = sampleTasks.filter(item => item.state.startsWith('已完成')).length;
  $('#mission-list').replaceChildren();
  sampleTasks.forEach(item => {
    const row = make('div', 'mission-row'); const content = make('div', 'mission-title');
    content.append(make('strong', '', item.title), make('small', '', item.prompt));
    const state = make('span', 'mission-state' + (runs.has(item.id) ? ' active' : ''), item.state);
    const open = make('button', '', '打开'); open.onclick = () => selectTask(item.id);
    const run = make('button', '', runs.has(item.id) ? '停止示例' : '运行示例');
    run.onclick = () => { if (runs.has(item.id)) endRun(item.id, true); else startRun(item.id, item.prompt); };
    row.append(make('span', 'role-mark hermes', 'H'), content, state, open, run); $('#mission-list').append(row);
  });
}
function endRun(id, stopped) {
  const run = runs.get(id); if (!run) return;
  clearInterval(run.timer); runs.delete(id);
  const item = sampleTasks.find(other => other.id === id);
  item.state = stopped ? '已停止 · 示例' : '已完成 · 示例';
  addActivity(stopped ? '停止示例运行' : '示例流程结束', '本地交互演示，没有发送真实请求或执行工具。', id);
  if (id === selectedTask) paintTask();
  renderTasks(); toast(stopped ? '已停止这个示例任务，其他任务不受影响。' : '示例流程完成，没有产生模型费用。');
}
function startRun(id, prompt) {
  if (runs.has(id)) return;
  if (runs.size >= 2) { toast('原型最多同时演示两个任务，请先停止一个。'); return; }
  const item = sampleTasks.find(other => other.id === id); item.prompt = prompt; item.state = '正在规划 · 示例';
  const run = {stage: 0, timer: null}; runs.set(id, run);
  addActivity('开始示例任务', '任务状态、停止操作和草稿独立保存在各自的示例任务中。', id);
  run.timer = setInterval(() => {
    run.stage++;
    if (run.stage === 3) { endRun(id, false); return; }
    item.state = run.stage === 1 ? '角色执行 · 示例' : '汇总成果 · 示例';
    if (id === selectedTask) paintTask(); renderTasks();
  }, 1800);
  if (id === selectedTask) paintTask(); renderTasks();
}
function runDemo() {
  if (runs.has(selectedTask)) { endRun(selectedTask, true); return; }
  const prompt = $('#prompt').value.trim();
  if (!prompt) { $('#prompt').focus(); toast('先写下一个示例任务。'); return; }
  task().draft = ''; $('#prompt').value = ''; startRun(selectedTask, prompt); setTab('activity');
}
function renderFiles() {
  const item = task(), artifact = artifacts.find(other => other.task === item.id);
  const key = item.activeFile || 'checklist';
  document.querySelectorAll('[data-file]').forEach(button => {
    const name = button.dataset.file === 'notes' ? 'task-notes.txt' : (artifact?.filename || 'task-brief.md');
    button.textContent = '▤ ' + name;
    button.classList.toggle('selected', button.dataset.file === key);
  });
  $('#file-content').textContent = item.id === 'launch' ? fileText[key] :
    (key === 'notes' ? `任务：${item.title}\n\n${item.prompt}\n\n仅保存在原型内存，未读取真实文件。` :
      `# ${artifact?.title || item.title}（静态示例）\n\n${artifact?.description || item.prompt}\n\n来源任务：${item.title}\n\n没有读取真实项目文件。`);
}
function renderArtifacts() {
  $('#artifact-grid').replaceChildren();
  artifacts.filter(item => artifactFilter === 'all' || item.type === artifactFilter).forEach(item => {
    const card = make('button', 'artifact-tile');
    card.append(make('span', 'artifact-cover ' + item.type, item.mark), make('small', '', item.label + ' · 示例'), make('strong', '', item.title), make('p', '', item.description), make('small', '', item.filename));
    card.onclick = () => { selectTask(item.task); task().activeFile = 'checklist'; renderFiles(); setTab('files'); };
    $('#artifact-grid').append(card);
  });
}
const commands = [
  ['新建示例任务', '⌘ N', () => openDialog('#new-dialog')],
  ['打开任务中心', '任务', () => setView('tasks')],
  ['浏览成果库', '成果', () => setView('library')],
  ['查看项目文件', '文件', () => setView('files')],
  ['查看协作记录', '任务', () => setTab('activity')],
  ['审阅示例变更', '审阅', () => setTab('review')],
  ['分配角色模型', '模型', showModels],
  ['打开能力中心', '工具', () => { setLayout('professional'); setView('capabilities'); }],
  ['展开终端抽屉', '终端', () => showTerminal(true)],
  ['切换专注布局', '布局', () => setLayout(layout === 'focus' ? 'professional' : 'focus')],
  ['切换外观', '主题', () => $('#theme-toggle').click()],
];
function renderCommands(query = '') {
  $('#command-list').replaceChildren();
  commands.filter(([name]) => name.includes(query.trim())).forEach(([name, shortcut, action]) => {
    const button = make('button'); button.append(make('span', '', name), make('kbd', '', shortcut));
    button.onclick = () => { $('#palette').close(); action(); }; $('#command-list').append(button);
  });
}
function openPalette() { renderCommands(); $('#command-search').value = ''; openDialog('#palette'); $('#command-search').focus(); }
const capabilityDetails = {
  skills: ['技能与工作流', '按项目启用技能，查看其说明、来源和所需工具。桌面会复用核心技能管理；安装或启用不代表获得额外目录权限。'],
  tools: ['工具与 MCP', '集中查看服务状态、工具描述和作用范围。实际执行仍经过共享核心的审批和工作区边界；扩展不可绕过权限。'],
  memory: ['项目记忆', '设计为可查看、编辑和停用，并说明来源和适用项目。切换项目不把私有上下文悄悄带到其他任务。'],
  channels: ['消息渠道', '桌面统一管理已有 Telegram、Slack、Discord 接入。真实账号仍需用户配置和验证，原型不会发送消息。'],
  desktop: ['桌面能力规划', '本地目录拖入、文件变化提示、多窗口、托盘常驻、系统通知、全局快捷键和安装更新均尚未实现，属于后续原生开发。电脑关机或休眠后，本地任务不能继续执行。'],
};
document.querySelectorAll('[data-close]').forEach(button => { button.onclick = () => button.closest('dialog').close(); });
document.querySelectorAll('[data-tab]').forEach(button => { button.onclick = () => setTab(button.dataset.tab); });
document.querySelectorAll('[data-view]').forEach(button => { button.onclick = () => setView(button.dataset.view); });
document.querySelectorAll('[data-mode]').forEach(button => { button.onclick = () => { task().mode = button.dataset.mode; paintTask(); toast(task().mode === 'auto' ? '示例：Hermes 自动选择角色。' : '示例：多角色协作，实际用量随任务而变。'); }; });
document.querySelectorAll('[data-file]').forEach(button => { button.onclick = () => { task().activeFile = button.dataset.file; renderFiles(); }; });
document.querySelectorAll('[name="model-mode"]').forEach(input => { input.onchange = () => { modelsMode = input.value; renderModels(); }; });
document.querySelectorAll('[data-kind]').forEach(button => { button.onclick = () => { artifactFilter = button.dataset.kind; document.querySelectorAll('[data-kind]').forEach(other => other.setAttribute('aria-pressed', String(other === button))); renderArtifacts(); }; });
document.querySelectorAll('[data-capability]').forEach(button => { button.onclick = () => { if (button.dataset.capability === 'roles') showModels(); else info(...capabilityDetails[button.dataset.capability]); }; });
$('#prompt').oninput = () => { task().draft = $('#prompt').value; };
$('#new-task').onclick = () => openDialog('#new-dialog');
$('#new-form').onsubmit = event => {
  event.preventDefault(); const prompt = $('#new-prompt').value.trim(); if (!prompt) return;
  const item = {id: 'task-' + Date.now(), title: prompt.slice(0, 16), heading: '准备开始一项新工作。', prompt, state: '草稿 · 示例', activities: [], mode: 'auto', draft: prompt};
  task().draft = $('#prompt').value; sampleTasks.unshift(item); $('#new-dialog').close(); $('#new-prompt').value = '';
  selectedTask = item.id; paintTask(); renderTasks(); setView('work'); setTab('activity'); $('#prompt').focus();
};
$('#theme-toggle').onclick = () => { app.dataset.theme = app.dataset.theme === 'dark' ? 'light' : 'dark'; $('#theme-toggle').setAttribute('aria-pressed', String(app.dataset.theme === 'dark')); };
$('#layout-toggle').onclick = $('#focus-preview').onclick = () => setLayout(layout === 'focus' ? 'professional' : 'focus');
$('#inspector-toggle').onclick = () => showInspector($('#inspector-toggle').getAttribute('aria-pressed') !== 'true');
$('#inspector-close').onclick = () => showInspector(false);
$('#terminal-toggle').onclick = () => showTerminal($('#terminal-drawer').hidden);
$('#terminal-close').onclick = () => showTerminal(false);
$('#terminal-simulate').onclick = () => { $('#terminal-output').textContent += '\n[示例] 检查记录已显示。没有运行 shell 命令。'; };
$('#model-open').onclick = $('#inspector-model').onclick = $('#connection-open').onclick = showModels;
$('#save-models').onclick = () => {
  task().modelProviders = [...$('#model-rows').querySelectorAll('select')].map(select => select.value);
  task().modelsMode = modelsMode; task().strategy = $('#model-strategy').value;
  updateModelTags(); $('#models-dialog').close(); toast('分配已保存到当前示例任务，未更换真实模型或凭据。');
};
$('#mock-connections').onclick = () => { $('#models-dialog').close(); info('连接管理与角色模型分开', '桌面端将共用连接保存、启停、引用检查和删除能力。这个原型不收集 API Key。'); };
$('#approval-open').onclick = () => openDialog('#approval-dialog');
$('#allow-approval').onclick = $('#deny-approval').onclick = event => {
  const allowed = event.currentTarget.id === 'allow-approval'; $('#approval-dialog').close();
  addActivity(allowed ? '示例审批：允许一次' : '示例审批：已拒绝', '没有执行任何命令；真实应用会在工具边界完成审批。'); setTab('activity');
  toast(allowed ? '已记录示例授权，不会执行命令。' : '已记录示例拒绝。');
};
$('#review-accept').onclick = $('#review-reject').onclick = event => {
  const accepted = event.currentTarget.id === 'review-accept';
  task().reviewState = accepted ? '示例已接受 · 未写入项目文件' : '示例已退回 · 等待修订';
  $('#review-state').textContent = task().reviewState;
  addActivity(accepted ? '接受示例变更' : '退回示例变更', '仅记录原型中的审阅选择，没有修改真实文件。');
};
$('#run-demo').onclick = runDemo;
$('#palette-open').onclick = $('#search-tasks').onclick = openPalette;
$('#command-search').oninput = event => renderCommands(event.target.value);
$('#command-search').onkeydown = event => { if (event.key === 'Enter') { event.preventDefault(); $('#command-list button')?.click(); } if (event.key === 'ArrowDown') { event.preventDefault(); $('#command-list button')?.focus(); } };
$('#workspace-demo').onclick = $('#project-switch').onclick = () => info('工作区始终明确', '实际桌面端需要用户选择项目目录。会话、工具权限和文件操作绑定当前工作区；切换工作区不会复用其他目录的任务。');
$('#lifecycle-open').onclick = () => info('桌面应用的运行边界', '核对后台归属、避免重复服务，区分关闭窗口与退出服务。选择常驻后可隐藏窗口；电脑需保持唤醒。原型没有启动后台任务。');
$('#usage-preview').onclick = () => info('每一笔用量，都能追溯到工作', '读取共享核心的任务、角色、阶段和供应商用量。单家与混用都应支持额度控制；未知 token 或单价继续显示未知，不把估算当账单。');
$('#automation-preview').onclick = () => info('自动化需要明确启用', '显示本地时区、下一次运行和交付位置。后台服务未运行或电脑休眠时，本地任务不会按时执行；唤醒后先核对状态，不自动补跑外部操作。');
$('#native-preview').onclick = () => info(...capabilityDetails.desktop);
$('#attach-demo').onclick = () => info('附件进入明确的上下文', '将共用图片/PDF/音频上传能力，支持桌面拖入与目录选择，并在发送前明确文件和供应商边界。原型不打开文件选择器或读取文件。');
$('#copy-result').onclick = async () => { try { await navigator.clipboard.writeText(fileText.checklist); toast('已复制示例清单。'); } catch (_) { toast('当前预览未获得剪贴板权限，可在文件页查看原文。'); } };
document.addEventListener('keydown', event => {
  const mod = event.metaKey || event.ctrlKey;
  if (mod && event.key.toLowerCase() === 'k') { event.preventDefault(); openPalette(); }
  if (mod && event.key.toLowerCase() === 'n') { event.preventDefault(); openDialog('#new-dialog'); }
});
$('.content-tabs').addEventListener('keydown', event => {
  const tabs = [...document.querySelectorAll('[role="tab"]')]; if (!tabs.includes(event.target)) return;
  const direction = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0; if (!direction) return;
  event.preventDefault(); const target = tabs[(tabs.indexOf(event.target) + direction + tabs.length) % tabs.length]; setTab(target.dataset.tab); target.focus();
});
const compactLayout = window.matchMedia('(max-width:1150px)');
compactLayout.addEventListener('change', event => showInspector(layout !== 'focus' && !event.matches));
renderTasks(); paintTask();
if (compactLayout.matches) showInspector(false);
