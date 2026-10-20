'use strict';
const $ = selector => document.querySelector(selector);
const app = $('.app');
const taskTabs = ['result', 'activity', 'review', 'files'];
const globalViews = ['tasks', 'library', 'capabilities', 'automation'];
const entries = [
  ['hermes', 'H', 'Hermes', 'Plan & delegate', 'Turn the goal, constraints, and expected output into a clear plan.'],
  ['athena', 'A', 'Athena', 'Research & verify', 'Gather evidence and flag information that still needs verification.'],
  ['forge', 'He', 'Hephaestus', 'Execution & recovery review', 'Review execution, failure handling, and recovery in an actionable checklist.'],
  ['hermes', 'H', 'Hermes', 'Synthesize results', 'Bring stage outputs together in a project-ready document.'],
];
const sampleTasks = [
  {id: 'launch', title: 'Launch preparation', heading: 'A council for every task.', prompt: 'Review the project and prepare an actionable launch checklist.', state: 'Completed · Demo', activities: entries.map(item => [...item])},
  {id: 'research', title: 'Compare data stores', heading: 'Start with the evidence.', prompt: 'Compare two data stores, including trade-offs and evidence sources.', state: 'Needs attention · Demo'},
  {id: 'page', title: 'Build a product page', heading: 'From a goal to something tangible.', prompt: 'Create a clear, focused introduction page for a sample product.', state: 'Draft · Demo'},
];
const artifacts = [
  {title: 'Launch checklist', type: 'document', label: 'Documents', mark: 'M↓', task: 'launch', filename: 'launch-checklist.md', description: 'A checklist for setup, recovery, and delivery.'},
  {title: 'Data store comparison', type: 'research', label: 'Research', mark: 'A', task: 'research', filename: 'research-outline.md', description: 'Comparison criteria, evidence sources, and open questions.'},
  {title: 'Product page draft', type: 'web', label: 'Web pages', mark: '</>', task: 'page', filename: 'index.html', description: 'A static example of page structure and content.'},
];
const fileText = {
  checklist: '# Launch checklist (Demo)\n\n- [ ] Check onboarding and model setup\n- [ ] Check failure handling and task recovery\n- [ ] Keep test evidence and note unverified checks\n\nPrototype example only. This is not a real validation report.',
  notes: 'Task: Review a sample project\n\nCouncil: Hermes → Athena → Hephaestus → Hermes\n\nScope:\nNo local workspace read\nNo provider API calls\nNo tools executed or files written\n\nThis record is held in prototype memory only.',
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
    const mark = make('span', 'status-dot' + (item.state.startsWith('Completed') || runs.has(item.id) ? '' : ' neutral'));
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
  setIconButton($('#run-demo'), runs.has(item.id) ? 'stop' : 'send', runs.has(item.id) ? 'Stop demo' : 'Run demo');
  const stage = runs.get(item.id)?.stage || 0;
  document.querySelectorAll('.route-check').forEach((element, index) => {
    element.textContent = item.state.startsWith('Completed') || (runs.has(item.id) && index < stage) ? '✓' : '·';
  });
  document.querySelectorAll('[data-mode]').forEach(button => button.classList.toggle('selected', button.dataset.mode === item.mode));
  $('#review-state').textContent = item.reviewState || 'Awaiting review · No files written';
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
    content.append(make('strong', '', `${name} · ${title}`), make('p', '', description), make('small', '', `Stage ${index + 1} · Sample activity`));
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
  const viewLabels = {tasks: 'Task center', library: 'Artifact library', capabilities: 'Capabilities', automation: 'Automations'};
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
  setIconButton($('#inspector-toggle'), 'context', show ? 'Hide context' : 'Show context');
}
function setLayout(value) {
  layout = value; app.dataset.layout = value;
  setIconButton($('#layout-toggle'), value === 'focus' ? 'focus' : 'layout', value === 'focus' ? 'Switch to Pro workspace' : 'Switch to Focus layout');
  $('#layout-toggle').setAttribute('aria-pressed', String(value === 'focus'));
  showInspector(value !== 'focus' && !compactLayout.matches);
  if (value === 'focus') { showTerminal(false); if (currentView === 'capabilities') setView('work'); }
}
function showTerminal(show) { $('#terminal-drawer').hidden = !show; $('#terminal-toggle').setAttribute('aria-expanded', String(show)); setIconButton($('#terminal-toggle'), 'terminal', show ? 'Close terminal' : 'Open terminal'); }
function updateModelTags() {
  document.querySelectorAll('.inspector-role .text-tag').forEach((tag, index) => { tag.textContent = task().modelProviders?.[index] || 'Default model'; });
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
    label.append(make('small', '', 'Demo · Not connected'));
    const select = make('select'); select.setAttribute('aria-label', name + ' demo provider');
    ['DeepSeek', 'OpenAI', 'Anthropic'].forEach(provider => select.append(make('option', '', provider)));
    select.value = providers?.[index] || (modelsMode === 'single' ? 'DeepSeek' : ['DeepSeek', 'OpenAI', 'Anthropic'][index % 3]);
    select.onchange = () => { if (modelsMode === 'single') $('#model-rows').querySelectorAll('select').forEach(other => { other.value = select.value; }); };
    row.append(label, select); $('#model-rows').append(row);
  });
}
function renderMissions() {
  $('#metric-running').textContent = runs.size;
  $('#metric-waiting').textContent = sampleTasks.filter(item => !runs.has(item.id) && !item.state.startsWith('Completed')).length;
  $('#metric-completed').textContent = sampleTasks.filter(item => item.state.startsWith('Completed')).length;
  if (activeTooltipButton && $('#mission-list').contains(activeTooltipButton)) hideButtonTooltip();
  $('#mission-list').replaceChildren();
  sampleTasks.forEach(item => {
    const row = make('div', 'mission-row'); const content = make('div', 'mission-title');
    content.append(make('strong', '', item.title), make('small', '', item.prompt));
    const state = make('span', 'mission-state' + (runs.has(item.id) ? ' active' : ''), item.state);
    const open = setIconButton(make('button'), 'open', 'Open task'); open.onclick = () => selectTask(item.id);
    const run = setIconButton(make('button'), runs.has(item.id) ? 'stop' : 'play', runs.has(item.id) ? 'Stop demo' : 'Run demo');
    run.onclick = () => { if (runs.has(item.id)) endRun(item.id, true); else startRun(item.id, item.prompt); };
    row.append(make('span', 'role-mark hermes', 'H'), content, state, open, run); $('#mission-list').append(row);
  });
}
function endRun(id, stopped) {
  const run = runs.get(id); if (!run) return;
  clearInterval(run.timer); runs.delete(id);
  const item = sampleTasks.find(other => other.id === id);
  item.state = stopped ? 'Stopped · Demo' : 'Completed · Demo';
  addActivity(stopped ? 'Demo stopped' : 'Demo completed', 'Local interaction demo. No requests sent or tools executed.', id);
  if (id === selectedTask) paintTask();
  renderTasks(); toast(stopped ? 'Demo stopped. Other tasks are unaffected.' : 'Demo completed. No model costs incurred.');
}
function startRun(id, prompt) {
  if (runs.has(id)) return;
  if (runs.size >= 2) { toast('This prototype supports two demo runs at a time. Stop one to continue.'); return; }
  const item = sampleTasks.find(other => other.id === id); item.prompt = prompt; item.state = 'Planning · Demo';
  const run = {stage: 0, timer: null}; runs.set(id, run);
  addActivity('Demo started', 'Status, stop controls, and drafts stay separate for each demo task.', id);
  run.timer = setInterval(() => {
    run.stage++;
    if (run.stage === 3) { endRun(id, false); return; }
    item.state = run.stage === 1 ? 'Executing · Demo' : 'Synthesizing · Demo';
    if (id === selectedTask) paintTask(); renderTasks();
  }, 1800);
  if (id === selectedTask) paintTask(); renderTasks();
}
function runDemo() {
  if (runs.has(selectedTask)) { endRun(selectedTask, true); return; }
  const prompt = $('#prompt').value.trim();
  if (!prompt) { $('#prompt').focus(); toast('Describe a demo task first.'); return; }
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
    (key === 'notes' ? `Task: ${item.title}\n\n${item.prompt}\n\nHeld in prototype memory. No real files read.` :
      `# ${artifact?.title || item.title} (Static example)\n\n${artifact?.description || item.prompt}\n\nSource task: ${item.title}\n\nNo real project files were read.`);
}
function renderArtifacts() {
  $('#artifact-grid').replaceChildren();
  artifacts.filter(item => artifactFilter === 'all' || item.type === artifactFilter).forEach(item => {
    const card = make('button', 'artifact-tile');
    card.append(make('span', 'artifact-cover ' + item.type, item.mark), make('small', '', item.label + ' · Demo'), make('strong', '', item.title), make('p', '', item.description), make('small', '', item.filename));
    card.onclick = () => { selectTask(item.task); task().activeFile = 'checklist'; renderFiles(); setTab('files'); };
    $('#artifact-grid').append(card);
  });
}
const commands = [
  ['New demo task', '⌘ N', () => openDialog('#new-dialog')],
  ['Open task center', 'Task', () => setView('tasks')],
  ['Browse artifacts', 'Result', () => setView('library')],
  ['View project files', 'Files', () => setView('files')],
  ['View activity', 'Task', () => setTab('activity')],
  ['Review demo changes', 'Review', () => setTab('review')],
  ['Assign role models', 'Models', showModels],
  ['Open capabilities', 'Tools', () => { setLayout('professional'); setView('capabilities'); }],
  ['Open terminal drawer', 'Terminal', () => showTerminal(true)],
  ['Toggle Focus layout', 'Layout', () => setLayout(layout === 'focus' ? 'professional' : 'focus')],
  ['Toggle theme', 'Theme', () => $('#theme-toggle').click()],
];
function renderCommands(query = '') {
  $('#command-list').replaceChildren();
  commands.filter(([name]) => name.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase())).forEach(([name, shortcut, action]) => {
    const button = make('button'); button.append(make('span', '', name), make('kbd', '', shortcut));
    button.onclick = () => { $('#palette').close(); action(); }; $('#command-list').append(button);
  });
}
function openPalette() { renderCommands(); $('#command-search').value = ''; openDialog('#palette'); $('#command-search').focus(); }
const capabilityDetails = {
  skills: ['Skills & workflows', 'Enable skills by project and inspect their sources and tools. Desktop will share core skill management. Enabling a skill does not grant folder access.'],
  tools: ['Tools & MCP', 'See service status, tool descriptions, and scope. Execution stays within core approvals and workspace boundaries.'],
  memory: ['Project memory', 'Review, edit, or disable saved memory with its source and project scope. Private context stays with its project.'],
  channels: ['Messaging', 'Manage Telegram, Slack, and Discord connections. Real accounts require setup and verification. This prototype sends no messages.'],
  desktop: ['Desktop roadmap', 'Folder drop, file watching, multiple windows, tray mode, notifications, global shortcuts, and packaged updates are not implemented yet. Local tasks cannot run while the computer is asleep or shut down.'],
};
document.querySelectorAll('[data-close]').forEach(button => { button.onclick = () => button.closest('dialog').close(); });
document.querySelectorAll('[data-tab]').forEach(button => { button.onclick = () => setTab(button.dataset.tab); });
document.querySelectorAll('[data-view]').forEach(button => { button.onclick = () => setView(button.dataset.view); });
document.querySelectorAll('[data-mode]').forEach(button => { button.onclick = () => { task().mode = button.dataset.mode; paintTask(); toast(task().mode === 'auto' ? 'Demo: Hermes selects the roles for the task.' : 'Demo: multiple roles work together. Actual usage depends on the task.'); }; });
document.querySelectorAll('[data-file]').forEach(button => { button.onclick = () => { task().activeFile = button.dataset.file; renderFiles(); }; });
document.querySelectorAll('[name="model-mode"]').forEach(input => { input.onchange = () => { modelsMode = input.value; renderModels(); }; });
document.querySelectorAll('[data-kind]').forEach(button => { button.onclick = () => { artifactFilter = button.dataset.kind; document.querySelectorAll('[data-kind]').forEach(other => other.setAttribute('aria-pressed', String(other === button))); renderArtifacts(); }; });
document.querySelectorAll('[data-capability]').forEach(button => { button.onclick = () => { if (button.dataset.capability === 'roles') showModels(); else info(...capabilityDetails[button.dataset.capability]); }; });
$('#prompt').oninput = () => { task().draft = $('#prompt').value; };
$('#new-task').onclick = () => openDialog('#new-dialog');
$('#new-form').onsubmit = event => {
  event.preventDefault(); const prompt = $('#new-prompt').value.trim(); if (!prompt) return;
  const item = {id: 'task-' + Date.now(), title: prompt.slice(0, 48), heading: 'A fresh start for your next task.', prompt, state: 'Draft · Demo', activities: [], mode: 'auto', draft: prompt};
  task().draft = $('#prompt').value; sampleTasks.unshift(item); $('#new-dialog').close(); $('#new-prompt').value = '';
  selectedTask = item.id; paintTask(); renderTasks(); setView('work'); setTab('activity'); $('#prompt').focus();
};
$('#theme-toggle').onclick = () => { app.dataset.theme = app.dataset.theme === 'dark' ? 'light' : 'dark'; $('#theme-toggle').setAttribute('aria-pressed', String(app.dataset.theme === 'dark')); setIconButton($('#theme-toggle'), app.dataset.theme === 'dark' ? 'sun' : 'moon', app.dataset.theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'); };
$('#layout-toggle').onclick = $('#focus-preview').onclick = () => setLayout(layout === 'focus' ? 'professional' : 'focus');
$('#inspector-toggle').onclick = () => showInspector($('#inspector-toggle').getAttribute('aria-pressed') !== 'true');
$('#inspector-close').onclick = () => showInspector(false);
$('#terminal-toggle').onclick = () => showTerminal($('#terminal-drawer').hidden);
$('#terminal-close').onclick = () => showTerminal(false);
$('#terminal-simulate').onclick = () => { $('#terminal-output').textContent += '\n[Demo] Sample output displayed. No shell command was run.'; };
$('#model-open').onclick = $('#inspector-model').onclick = $('#connection-open').onclick = showModels;
$('#save-models').onclick = () => {
  task().modelProviders = [...$('#model-rows').querySelectorAll('select')].map(select => select.value);
  task().modelsMode = modelsMode; task().strategy = $('#model-strategy').value;
  updateModelTags(); $('#models-dialog').close(); toast('Assignment saved to this demo task. Real models and credentials are unchanged.');
};
$('#mock-connections').onclick = () => { $('#models-dialog').close(); info('Connections and role assignments are separate', 'Desktop will share connection storage, enable/disable controls, reference checks, and removal. This prototype does not collect API keys.'); };
$('#approval-open').onclick = () => openDialog('#approval-dialog');
$('#allow-approval').onclick = $('#deny-approval').onclick = event => {
  const allowed = event.currentTarget.id === 'allow-approval'; $('#approval-dialog').close();
  addActivity(allowed ? 'Demo approval: allowed once' : 'Demo approval: denied', 'No commands were run. The desktop app will enforce approvals at the tool boundary.'); setTab('activity');
  toast(allowed ? 'Demo permission recorded. No command will run.' : 'Demo denial recorded.');
};
$('#review-accept').onclick = $('#review-reject').onclick = event => {
  const accepted = event.currentTarget.id === 'review-accept';
  task().reviewState = accepted ? 'Accepted in demo · No files written' : 'Changes requested · Awaiting revision';
  $('#review-state').textContent = task().reviewState;
  addActivity(accepted ? 'Accept demo changes' : 'Demo changes requested', 'Recorded the demo review choice. No real files changed.');
};
$('#run-demo').onclick = runDemo;
$('#palette-open').onclick = $('#search-tasks').onclick = openPalette;
$('#command-search').oninput = event => renderCommands(event.target.value);
$('#command-search').onkeydown = event => { if (event.key === 'Enter') { event.preventDefault(); $('#command-list button')?.click(); } if (event.key === 'ArrowDown') { event.preventDefault(); $('#command-list button')?.focus(); } };
$('#workspace-demo').onclick = $('#project-switch').onclick = () => info('A clear workspace boundary', 'Choose a project folder in the desktop app. Sessions, tools, and file operations stay within that workspace; switching projects does not reuse another folder’s tasks.');
$('#lifecycle-open').onclick = () => info('Local service lifecycle', 'Desktop will identify its backend and avoid duplicate services. Closing a window is separate from quitting. Background work needs an awake computer. This prototype starts no backend tasks.');
$('#usage-preview').onclick = () => info('Usage you can trace', 'Usage will show task, role, stage, and provider details from the core. Budgets apply to single and mixed setups. Missing tokens or prices stay unknown; estimates are not bills.');
$('#automation-preview').onclick = () => info('Schedules need an active service', 'Show the local timezone, next run, and delivery location. Local schedules require an active service and an awake computer. Missed external actions are not automatically replayed.');
$('#native-preview').onclick = () => info(...capabilityDetails.desktop);
$('#attach-demo').onclick = () => info('Attachments with a clear scope', 'Desktop will share image, PDF, and audio support, with drag-and-drop and folder selection. File scope and provider destinations stay explicit. This prototype reads no files.');
$('#copy-result').onclick = async () => { try { await navigator.clipboard.writeText(fileText.checklist); toast('Sample checklist copied.'); } catch (_) { toast('Clipboard access is unavailable. Open Files to view the text.'); } };
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

document.querySelectorAll('[data-nav-icon]').forEach(mark => {
  mark.replaceChildren(desktopIcon(mark.dataset.navIcon));
  const button = mark.closest('button');
  const labels = {work: 'Workbench', tasks: 'Task center', library: 'Artifact library', files: 'Project files', automation: 'Automations', capabilities: 'Capabilities'};
  button.dataset.tooltip = labels[button.dataset.view]; button.setAttribute('aria-label', labels[button.dataset.view]);
});
