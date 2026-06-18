/* ==========================================================================
   Pantheon Web UI — Frontend logic (v2: 2-pane layout, god rows w/ model)
   ========================================================================== */

(function () {
  'use strict';

  // ---------- God metadata ----------
  const GOD_META = {
    hermes:     { icon: '📨', label: 'Hermes',     color: 'var(--god-hermes)' },
    hephaestus: { icon: '🔨', label: 'Hephaestus', color: 'var(--god-hephaestus)' },
    athena:     { icon: '🦉', label: 'Athena',     color: 'var(--god-athena)' },
    apollo:     { icon: '🎵', label: 'Apollo',     color: 'var(--god-apollo)' },
    chronos:    { icon: '⏰', label: 'Chronos',    color: 'var(--god-chronos)' },
  };
  const FALLBACK_GOD = { icon: '✨', label: '?', color: 'var(--accent)' };

  function metaFor(name) {
    return GOD_META[name] || { ...FALLBACK_GOD, label: name };
  }

  // ---------- Element refs ----------
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => Array.from(document.querySelectorAll(s));

  const chatEl       = $('#chat');
  const inputEl      = $('#input');
  const sendBtn      = $('#send-btn');
  const composerForm = $('#composer');
  const modeChips    = $$('.mode-chip');
  const modeDisplay  = $('#mode-display b');
  const topbarIcon   = $('#topbar-mode-icon');
  const topbarName   = $('#topbar-mode-name');
  const providerPill = $('#provider-name');
  const providerDot  = providerPill.previousElementSibling;
  const godsList     = $('#gods-list');
  const aboutBtn     = $('#about-btn');
  const aboutModal   = $('#about-modal');
  const aboutClose   = $('#about-close');
  const aboutProvider = $('#about-provider');
  const aboutRoles   = $('#about-roles');
  const aboutStatus  = $('#about-status');
  const aboutRolesList = $('#about-roles-list');
  const newChatBtn   = $('#new-chat-btn');
  const toggleWsBtn  = $('#toggle-workspace');
  const workspaceEl  = $('#workspace');
  const workspaceClose = $('#workspace-close');
  const wsPlanEl     = $('#ws-plan');
  const wsStepsEl    = $('#ws-steps');
  const wsOutputEl   = $('#ws-output');
  const toggleSetBtn = $('#toggle-settings');
  const settingsPanel = $('#settings-panel');
  const settingsClose = $('#settings-close');
  const settingsTabs = $$('.settings-tab');
  const settingsPanes = $$('.settings-pane');
  const settingsRoles = $('#settings-roles');
  const settingsRolesCount = $('#settings-roles-count');
  const settingsPy = $('#settings-py');
  const settingsStatus = $('#settings-status');

  // ---------- State ----------
  let currentMode = 'auto';
  let roles = [];
  let isStreaming = false;
  let abortCtrl = null;
  let turns = [];   // conversation history (in-memory only)

  // ---------- Helpers ----------
  function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[c]);
  }

  function renderMarkdown(text) {
    if (window.marked) {
      try {
        return window.marked.parse(text, { breaks: true, gfm: true });
      } catch (_) { /* fall through */ }
    }
    return escapeHtml(text);
  }

  function highlightCode(root) {
    if (window.hljs) {
      root.querySelectorAll('pre code').forEach((el) => {
        // Detect language from class first (set by marked)
        const cls = el.className || '';
        if (!cls.match(/language-\w+/)) {
          el.classList.add('language-plaintext');
        }
        try { window.hljs.highlightElement(el); } catch (_) {}
      });
      // Add data-lang attribute on <pre> for the corner badge
      root.querySelectorAll('pre').forEach((pre) => {
        const code = pre.querySelector('code');
        if (code) {
          const lang = (code.className.match(/language-(\w+)/) || [])[1];
          if (lang && lang !== 'plaintext') {
            pre.setAttribute('data-lang', lang);
          }
        }
      });
    }
  }

  function highlightGod(roleName) {
    $$('.god-row').forEach((row) => {
      row.classList.toggle('active', row.dataset.role === roleName);
    });
  }
  function clearGodHighlight() {
    $$('.god-row').forEach((row) => row.classList.remove('active'));
  }

  function setProvider(name, status = 'online') {
    providerPill.textContent = name || 'disconnected';
    providerDot.classList.remove('offline', 'connecting');
    if (status === 'offline')    providerDot.classList.add('offline');
    if (status === 'connecting') providerDot.classList.add('connecting');
  }

  function setMode(mode) {
    currentMode = mode;
    modeChips.forEach((chip) => {
      chip.classList.toggle('active', chip.dataset.mode === mode);
    });

    // Update topbar pill
    let label, icon;
    if (mode === 'auto') {
      label = 'Auto'; icon = '🪄';
    } else if (mode === 'multi') {
      label = 'Multi-role'; icon = '🧩';
    } else if (mode.startsWith('role:')) {
      const name = mode.slice(5);
      label = metaFor(name).label; icon = metaFor(name).icon;
    } else {
      label = mode; icon = '✨';
    }
    topbarName.textContent = label;
    topbarIcon.textContent = icon;

    // Update composer meta
    modeDisplay.textContent = label;
  }

  // ---------- Render god list (sidebar) ----------
  function renderGods() {
    if (!roles.length) {
      godsList.innerHTML = '<div class="god-row loading"><span class="god-avatar">⏳</span><div class="god-info"><div class="god-name">No roles</div></div></div>';
      return;
    }
    godsList.innerHTML = '';
    for (const r of roles) {
      const meta = metaFor(r.name);
      const row = document.createElement('div');
      row.className = 'god-row';
      row.dataset.role = r.name;
      row.style.setProperty('--god-color', meta.color);
      const modelShort = (r.model || '').replace(/^deepseek-/, '').replace(/^claude-/, '').replace(/^gpt-/, '');
      const isChronosRow = (r.name === 'chronos');
      const badge = isChronosRow ? '<span class="god-badge" title="Scheduling role — no LLM">⏰</span>' : '';
      row.innerHTML = `
        <span class="god-avatar">${meta.icon}</span>
        <div class="god-info">
          <div class="god-name">${escapeHtml(meta.label)}${badge}</div>
          <div class="god-model" title="${escapeHtml(r.model || 'no model')}">${isChronosRow ? '(scheduling)' : escapeHtml(modelShort || r.model || '—')}</div>
        </div>
      `;
      if (isChronosRow) row.classList.add('scheduling');
      row.addEventListener('click', () => {
        if (isChronosRow) {
          // Chronos is a scheduling role — clicking shows a friendly hint instead of switching mode
          inputEl.value = '';
          inputEl.placeholder = '⏰ Chronos is a scheduling role — it cannot answer questions directly.';
          inputEl.focus();
          return;
        }
        setMode(`role:${r.name}`);
        inputEl.focus();
      });
      godsList.appendChild(row);
    }
  }

  // ---------- About modal ----------
  function openAbout() {
    aboutProvider.textContent = providerPill.textContent;
    aboutRoles.textContent = String(roles.length);
    aboutStatus.textContent = providerDot.classList.contains('offline') ? 'disconnected' : 'connected';

    aboutRolesList.innerHTML = '';
    for (const r of roles) {
      const meta = metaFor(r.name);
      const li = document.createElement('li');
      li.innerHTML = `
        <span class="ar-icon" style="color: ${meta.color}">${meta.icon}</span>
        <span class="ar-name" style="color: ${meta.color}">${escapeHtml(meta.label)}</span>
        <span class="ar-model">${escapeHtml(r.model || 'no LLM')}</span>
      `;
      aboutRolesList.appendChild(li);
    }
    aboutModal.hidden = false;
  }
  function closeAbout() {
    aboutModal.hidden = true;
  }
  aboutBtn.addEventListener('click', openAbout);
  aboutClose.addEventListener('click', closeAbout);
  aboutModal.addEventListener('click', (e) => {
    if (e.target === aboutModal) closeAbout();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !aboutModal.hidden) closeAbout();
  });

  // ---------- Mode chip events ----------
  modeChips.forEach((chip) => {
    chip.addEventListener('click', () => setMode(chip.dataset.mode));
  });

  // ---------- Workspace toggle ----------
  function openWorkspace() {
    workspaceEl.hidden = false;
    document.body.classList.add('workspace-open');
    toggleWsBtn.classList.add('active');
  }
  function closeWorkspace() {
    workspaceEl.hidden = true;
    document.body.classList.remove('workspace-open');
    toggleWsBtn.classList.remove('active');
  }
  function toggleWorkspace() {
    if (workspaceEl.hidden) openWorkspace();
    else closeWorkspace();
  }
  toggleWsBtn.addEventListener('click', toggleWorkspace);
  workspaceClose.addEventListener('click', closeWorkspace);

  // ---------- Settings toggle ----------
  function openSettings() {
    // Mutex: close workspace if open
    if (!workspaceEl.hidden) closeWorkspace();
    settingsPanel.hidden = false;
    document.body.classList.add('settings-open');
    toggleSetBtn.classList.add('active');
  }
  function closeSettings() {
    settingsPanel.hidden = true;
    document.body.classList.remove('settings-open');
    toggleSetBtn.classList.remove('active');
  }
  function toggleSettings() {
    if (settingsPanel.hidden) openSettings();
    else closeSettings();
  }
  toggleSetBtn.addEventListener('click', toggleSettings);
  settingsClose.addEventListener('click', closeSettings);

  // ---------- Settings tab switching ----------
  settingsTabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      const target = tab.dataset.tab;
      settingsTabs.forEach((t) => t.classList.toggle('active', t === tab));
      settingsPanes.forEach((p) => p.classList.toggle('active', p.dataset.pane === target));
    });
  });

  // ---------- Render settings → Models tab ----------
  // Model catalog: each provider lists models in the order shown.
  // Long technical names are paired with a friendly alias so the UI stays compact.
  const MODEL_CATALOG = {
    openai: [
      { id: 'gpt-4o',                  label: 'GPT-4o' },
      { id: 'gpt-4o-mini',             label: 'GPT-4o mini' },
      { id: 'gpt-4-turbo',             label: 'GPT-4 Turbo' },
      { id: 'o1',                      label: 'o1' },
      { id: 'o1-mini',                 label: 'o1 mini' },
      { id: 'gpt-image-1',             label: 'GPT Image 1' },
    ],
    anthropic: [
      { id: 'claude-opus-4-20250514',        label: 'Claude Opus 4' },
      { id: 'claude-sonnet-4-20250514',      label: 'Claude Sonnet 4' },
      { id: 'claude-3-5-sonnet-20241022',    label: 'Claude 3.5 Sonnet' },
      { id: 'claude-3-haiku-20240307',       label: 'Claude 3 Haiku' },
    ],
    deepseek: [
      { id: 'deepseek-chat',       label: 'DeepSeek Chat' },
      { id: 'deepseek-coder',      label: 'DeepSeek Coder' },
      { id: 'deepseek-reasoner',   label: 'DeepSeek Reasoner' },
    ],
    ollama: [
      { id: 'llama3.1:70b',   label: 'Llama 3.1 70B' },
      { id: 'llama3.1:8b',    label: 'Llama 3.1 8B' },
      { id: 'qwen2.5:72b',    label: 'Qwen 2.5 72B' },
      { id: 'mistral-large',  label: 'Mistral Large' },
    ],
    none: [
      { id: 'none', label: '(no model)' },
    ],
  };
  // Persisted in-memory overrides from the settings UI.
  const roleOverrides = {}; // { roleName: { provider, model } }

  function providerModels(provider) {
    return MODEL_CATALOG[provider] || [];
  }
  function providerModelIds(provider) {
    return providerModels(provider).map((m) => m.id);
  }
  function modelLabel(provider, id) {
    const entry = providerModels(provider).find((m) => m.id === id);
    return entry ? entry.label : id;
  }

  function renderSettingsModels() {
    settingsRoles.innerHTML = '';
    for (const r of roles) {
      const meta = metaFor(r.name);
      const provider = r.provider || 'none';
      const override = roleOverrides[r.name] || {};
      const currentProvider = override.provider || provider;
      const currentModel = override.model || r.model || '';
      const knownProviders = Object.keys(MODEL_CATALOG);
      const knownModelIds = providerModelIds(currentProvider);

      const card = document.createElement('div');
      card.className = 'settings-role';
      card.dataset.role = r.name;
      const isChronos = (r.name === 'chronos');
      if (isChronos) card.classList.add('scheduling-role');
      const lockAttrs = isChronos ? 'disabled title="This role has no LLM by design (scheduling only)"' : '';
      card.innerHTML = `
        <div class="settings-role-head">
          <span class="sr-icon" style="color: ${meta.color}">${meta.icon}</span>
          <span class="sr-name">${escapeHtml(meta.label)}</span>
          ${isChronos ? '<span class="sr-badge">⏰ scheduling</span>' : ''}
        </div>
        ${r.note ? `<div class="settings-role-note">${escapeHtml(r.note)}</div>` : ''}
        <div class="settings-role-row">
          <span class="sr-key">Provider</span>
          <select class="sr-provider" data-role="${escapeHtml(r.name)}" title="Provider" ${lockAttrs}>
            ${knownProviders.map((p) => `<option value="${escapeHtml(p)}" ${p === currentProvider ? 'selected' : ''}>${escapeHtml(p)}</option>`).join('')}
          </select>
        </div>
        <div class="settings-role-row">
          <span class="sr-key">Model</span>
          <select class="sr-model" data-role="${escapeHtml(r.name)}" title="Model" ${lockAttrs}>
            ${knownModelIds.map((id) => {
              const lbl = modelLabel(currentProvider, id);
              return `<option value="${escapeHtml(id)}" ${id === currentModel ? 'selected' : ''}>${escapeHtml(lbl)}</option>`;
            }).join('')}
          </select>
        </div>
      `;
      settingsRoles.appendChild(card);

      const provSel = card.querySelector('.sr-provider');
      const modSel = card.querySelector('.sr-model');
      // If currentModel isn't in the catalog for this provider, add a synthetic
      // option so the user can still see what was set (e.g. deepseek-chat from yaml).
      if (currentModel && !knownModelIds.includes(currentModel)) {
        const opt = document.createElement('option');
        opt.value = currentModel;
        opt.textContent = currentModel + ' (custom)';
        modSel.appendChild(opt);
        modSel.value = currentModel;
      }
      // Scheduling role: don't bind change handlers (selects are disabled)
      if (isChronos) return;
      provSel.addEventListener('change', () => {
        const newProv = provSel.value;
        const ids = providerModelIds(newProv);
        modSel.innerHTML = ids.map((id) => {
          const lbl = modelLabel(newProv, id);
          return `<option value="${escapeHtml(id)}">${escapeHtml(lbl)}</option>`;
        }).join('');
        // Pick first option of new provider as default
        const defaultModel = ids[0] || '';
        if (defaultModel) modSel.value = defaultModel;
        roleOverrides[r.name] = { provider: newProv, model: modSel.value };
        modSel.classList.add('changed');
        provSel.classList.add('changed');
      });
      modSel.addEventListener('change', () => {
        roleOverrides[r.name] = { provider: provSel.value, model: modSel.value };
        modSel.classList.add('changed');
        provSel.classList.add('changed');
      });
    }
  }

  // Get current effective provider/model for a role (with override)
  function effectiveModel(roleName) {
    return roleOverrides[roleName] || null;
  }

  function renderSettingsInfo() {
    settingsRolesCount.textContent = String(roles.length);
    settingsStatus.textContent = providerDot.classList.contains('offline') ? 'disconnected' : 'connected';
    settingsPy.textContent = 'Python (detected server-side)';
  }

  // ---------- Display preferences (saved in localStorage) ----------
  const PREF_KEY = 'pantheon:display-prefs';
  const DEFAULT_PREFS = {
    theme: 'dark',       // 'dark' | 'light'
    fontSize: 'md',      // 'sm' | 'md' | 'lg'
    animatedBg: 'on',    // 'on' | 'off'
    density: 'comfortable', // 'comfortable' | 'compact'
  };

  function loadPrefs() {
    try {
      const stored = JSON.parse(localStorage.getItem(PREF_KEY) || '{}');
      return { ...DEFAULT_PREFS, ...stored };
    } catch (_) {
      return { ...DEFAULT_PREFS };
    }
  }
  function savePrefs(p) {
    try { localStorage.setItem(PREF_KEY, JSON.stringify(p)); } catch (_) {}
  }

  function applyPrefs(prefs) {
    // Theme
    document.body.classList.toggle('light', prefs.theme === 'light');
    // Font size
    document.body.classList.remove('font-sm', 'font-md', 'font-lg');
    document.body.classList.add(`font-${prefs.fontSize}`);
    const baseSize = prefs.fontSize === 'sm' ? '13px' : prefs.fontSize === 'lg' ? '15px' : '14px';
    document.documentElement.style.fontSize = baseSize;
    // Animated bg
    document.body.classList.toggle('no-bg-anim', prefs.animatedBg === 'off');
    // Density
    document.body.classList.toggle('density-compact', prefs.density === 'compact');
  }

  function syncOptBtnActive(prefs) {
    $$('.opt-btn').forEach((btn) => {
      const action = btn.dataset.action;
      const value = btn.dataset.value;
      if (!action) return;
      let isActive = false;
      if (action === 'theme')      isActive = (value === prefs.theme);
      else if (action === 'fontSize')   isActive = (value === prefs.fontSize);
      else if (action === 'animatedBg') isActive = (value === prefs.animatedBg);
      else if (action === 'density')    isActive = (value === prefs.density);
      btn.classList.toggle('active', isActive);
    });
  }

  function wireOptBtns() {
    $$('.opt-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const action = btn.dataset.action;
        const value = btn.dataset.value;
        if (!action || !value) return;
        const prefs = loadPrefs();
        // Validate value
        const validMap = {
          theme:      ['dark', 'light'],
          fontSize:   ['sm', 'md', 'lg'],
          animatedBg: ['on', 'off'],
          density:    ['comfortable', 'compact'],
        };
        if (!validMap[action] || !validMap[action].includes(value)) return;
        prefs[action] = value;
        savePrefs(prefs);
        applyPrefs(prefs);
        syncOptBtnActive(prefs);
      });
    });
    applyPrefs(loadPrefs());
    syncOptBtnActive(loadPrefs());
  }

  function resetWorkspace() {
    wsPlanEl.innerHTML = '<span class="ws-empty">Waiting for Hermes to plan…</span>';
    wsPlanEl.classList.remove('active');
    wsStepsEl.innerHTML = '<li class="ws-step-empty">No steps yet</li>';
    wsOutputEl.textContent = '// output will appear here';
  }
  resetWorkspace();

  function addWorkspaceStep(role, task) {
    // Remove "empty" placeholder
    const empty = wsStepsEl.querySelector('.ws-step-empty');
    if (empty) empty.remove();

    const meta = metaFor(role);
    const li = document.createElement('li');
    li.className = 'ws-step running';
    li.dataset.role = role;
    const start = Date.now();
    li.innerHTML = `
      <span class="ws-step-dot"></span>
      <div class="ws-step-text">
        <div class="ws-step-role" style="color: ${meta.color}">${meta.icon} ${escapeHtml(meta.label)}</div>
        <div class="ws-step-task">${escapeHtml(task || 'thinking…')}</div>
      </div>
      <span class="ws-step-time" data-time>…</span>
    `;
    wsStepsEl.appendChild(li);
    // tick the timer every 100ms
    const tick = setInterval(() => {
      const elapsed = ((Date.now() - start) / 1000).toFixed(1);
      const t = li.querySelector('[data-time]');
      if (t) t.textContent = `${elapsed}s`;
    }, 100);
    li._tickInterval = tick;
    wsStepsEl.scrollTop = wsStepsEl.scrollHeight;
    return li;
  }

  function updateWorkspaceStep(role, status, durationMs) {
    const li = wsStepsEl.querySelector(`.ws-step[data-role="${role}"]:last-of-type`) ||
               wsStepsEl.querySelector(`.ws-step[data-role="${role}"]`);
    if (!li) return;
    li.classList.remove('running');
    li.classList.add(status);
    if (li._tickInterval) clearInterval(li._tickInterval);
    const t = li.querySelector('[data-time]');
    if (t && durationMs) t.textContent = `${(durationMs / 1000).toFixed(1)}s`;
  }

  // ---------- New chat (clear conversation) ----------
  newChatBtn.addEventListener('click', () => {
    if (isStreaming) return;
    turns = [];
    chatEl.innerHTML = '';
    recreateWelcome();
  });

  function recreateWelcome() {
    const w = document.createElement('div');
    w.className = 'welcome';
    w.id = 'welcome';
    w.innerHTML = `
      <div class="welcome-icon">🏛️</div>
      <h2>Welcome to the Pantheon</h2>
      <p>Each god uses a model best suited to its specialty.<br>
         Hermes will route your task to the right one.</p>
      <div class="welcome-examples">
        <button class="example-chip" data-prompt="Write a Python function to check if a string is a palindrome">💡 Write a palindrome checker</button>
        <button class="example-chip" data-prompt="Compare PostgreSQL and MongoDB for a new project">💡 Compare Postgres vs MongoDB</button>
        <button class="example-chip" data-prompt="Write a Midjourney prompt for a cyberpunk shrine at night">💡 Cyberpunk shrine prompt</button>
        <button class="example-chip" data-prompt="调研 Python Web 框架趋势并写一个 FastAPI demo">💡 调研并写 FastAPI demo</button>
      </div>
    `;
    chatEl.appendChild(w);
    // Re-bind example chips
    w.querySelectorAll('.example-chip').forEach((chip) => {
      chip.addEventListener('click', () => {
        inputEl.value = chip.dataset.prompt || '';
        autoResize();
        inputEl.focus();
      });
    });
  }

  // ---------- Welcome removal ----------
  function clearWelcome() {
    const w = chatEl.querySelector('.welcome');
    if (w) w.remove();
  }

  // ---------- Chat messages ----------
  function addMessage(role, contentHTML, opts = {}) {
    clearWelcome();
    const meta = metaFor(role);
    const msg = document.createElement('div');
    msg.className = `msg ${role}`;
    msg.innerHTML = `
      <div class="msg-avatar">${opts.icon || meta.icon}</div>
      <div class="msg-body">
        <div class="msg-meta">
          <span class="msg-role" style="color: ${opts.roleColor || meta.color}">${escapeHtml(opts.label || meta.label)}</span>
          <span class="msg-time">${new Date().toLocaleTimeString()}</span>
        </div>
        <div class="msg-content">${contentHTML}</div>
      </div>
    `;
    chatEl.appendChild(msg);
    chatEl.scrollTop = chatEl.scrollHeight;
    highlightCode(msg);
    return msg;
  }

  function addUserMessage(text) {
    return addMessage('user', `<div>${escapeHtml(text)}</div>`, {
      icon: '👤', label: 'You', roleColor: 'var(--accent)'
    });
  }

  function addErrorMessage(text) {
    return addMessage('error', `<div>⚠️ ${escapeHtml(text)}</div>`, {
      icon: '⚠️', label: 'Error', roleColor: 'var(--accent-err)'
    });
  }

  function createStepBlock(roleName) {
    const meta = metaFor(roleName);
    return addMessage('assistant', `
      <div class="step-block" data-step-block>
        <div class="step-block-header">
          <span class="step-role" style="color: ${meta.color}">${meta.icon} ${escapeHtml(meta.label)}</span>
          <span class="step-status streaming">streaming…</span>
        </div>
        <div class="step-block-body" data-step-body>
          <span class="streaming-cursor"></span>
        </div>
      </div>
    `, { icon: meta.icon, label: meta.label, roleColor: meta.color });
  }

  function appendToStep(msgEl, text) {
    const body = msgEl.querySelector('[data-step-body]');
    if (!body) return;
    const cursor = body.querySelector('.streaming-cursor');
    if (cursor) cursor.remove();
    if (!body.dataset.markdown) body.dataset.markdown = '';
    body.dataset.markdown += text;
    body.innerHTML = renderMarkdown(body.dataset.markdown) + '<span class="streaming-cursor"></span>';
    highlightCode(body);
    chatEl.scrollTop = chatEl.scrollHeight;
  }

  function finalizeStep(msgEl, finalContent) {
    const body = msgEl.querySelector('[data-step-body]');
    const status = msgEl.querySelector('.step-status');
    if (body) {
      const cursor = body.querySelector('.streaming-cursor');
      if (cursor) cursor.remove();
      if (finalContent != null) {
        body.innerHTML = renderMarkdown(finalContent);
        highlightCode(body);
      }
    }
    if (status) {
      status.classList.remove('streaming');
      status.textContent = 'done';
      status.style.color = 'var(--accent-3)';
    }
  }

  // ---------- SSE send ----------
  async function sendAsk(task) {
    if (isStreaming) return;
    isStreaming = true;
    abortCtrl = new AbortController();
    sendBtn.disabled = true;
    sendBtn.querySelector('.send-text').textContent = 'Stop';
    providerDot.classList.add('connecting');
    clearGodHighlight();

    addUserMessage(task);
    resetWorkspace();
    const startTime = Date.now();

    // Determine initial highlight
    if (currentMode === 'auto')        highlightGod('hermes');
    else if (currentMode === 'multi')  highlightGod('hermes');
    else if (currentMode.startsWith('role:')) highlightGod(currentMode.slice(5));

    let currentMsg = null;

    try {
      const resp = await fetch('/api/ask/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task,
          mode: currentMode,
          overrides: Object.keys(roleOverrides).length ? roleOverrides : undefined,
        }),
        signal: abortCtrl.signal,
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: resp.statusText }));
        throw new Error(err.detail || `HTTP ${resp.status}`);
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let sep;
        while ((sep = buffer.indexOf('\n\n')) !== -1) {
          const frame = buffer.slice(0, sep);
          buffer = buffer.slice(sep + 2);
          handleFrame(frame);
        }
      }

      function handleFrame(frame) {
        if (!frame.trim()) return;
        const lines = frame.split('\n');
        let event = 'message';
        let dataLines = [];
        for (const line of lines) {
          if (line.startsWith('event:')) event = line.slice(6).trim();
          else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
        }
        let data;
        try { data = JSON.parse(dataLines.join('\n')); }
        catch (_) { return; }
        handleEvent(event, data);
      }

      function handleEvent(event, data) {
        switch (event) {
          case 'start':
            // No-op; we already started
            break;
          case 'plan':
            // Display Hermes's plan in workspace
            if (data.plan) {
              wsPlanEl.textContent = data.plan;
              wsPlanEl.classList.add('active');
            }
            break;
          case 'step_start': {
            const r = data.role;
            highlightGod(r);
            if (currentMsg) finalizeStep(currentMsg, null);  // close previous
            currentMsg = createStepBlock(r);
            // Add to workspace steps
            addWorkspaceStep(r, '');
            break;
          }
          case 'step_chunk': {
            if (currentMsg) appendToStep(currentMsg, data.text || '');
            // Also append raw to workspace output (last step)
            if (data.text) {
              wsOutputEl.textContent += data.text;
              wsOutputEl.scrollTop = wsOutputEl.scrollHeight;
            }
            break;
          }
          case 'step_done': {
            if (currentMsg) finalizeStep(currentMsg, data.content);
            updateWorkspaceStep(data.role, 'done', data.duration_ms || 0);
            break;
          }
          case 'step_error': {
            if (currentMsg) {
              finalizeStep(currentMsg, '❌ ' + (data.error || 'unknown'));
              const s = currentMsg.querySelector('.step-status');
              if (s) { s.style.color = 'var(--accent-err)'; s.textContent = 'error'; }
            }
            updateWorkspaceStep(data.role, 'error', 0);
            break;
          }
          case 'done':
            providerDot.classList.remove('connecting');
            providerDot.classList.add('online');
            break;
          case 'error':
            addErrorMessage(data.message || 'Unknown error');
            break;
        }
      }
    } catch (e) {
      if (e.name === 'AbortError') {
        // user stopped
      } else {
        console.error(e);
        addErrorMessage(String(e.message || e));
      }
    } finally {
      clearGodHighlight();
      isStreaming = false;
      abortCtrl = null;
      sendBtn.disabled = false;
      sendBtn.querySelector('.send-text').textContent = 'Send';
      providerDot.classList.remove('connecting');
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
      console.log(`[pantheon] request completed in ${elapsed}s`);
    }
  }

  // ---------- Bootstrap ----------
  async function loadRoles() {
    setProvider('connecting…', 'connecting');
    try {
      const r = await fetch('/api/roles');
      if (!r.ok) throw new Error('failed to fetch roles');
      const data = await r.json();
      roles = data.roles || [];
      renderGods();
      renderSettingsModels();
      renderSettingsInfo();
      if (roles.length) {
        // Show provider as a comma-separated list of unique providers
        const providers = [...new Set(roles.map(r => r.model || '').filter(Boolean))];
        setProvider(providers.join(' · ') || 'connected', 'online');
      } else {
        setProvider('no roles', 'offline');
      }
    } catch (e) {
      console.error(e);
      setProvider('disconnected', 'offline');
    }
  }

  // ---------- Wire up events ----------
  composerForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const text = inputEl.value.trim();
    if (!text || isStreaming) return;
    inputEl.value = '';
    autoResize();
    sendAsk(text);
  });

  inputEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      composerForm.dispatchEvent(new Event('submit'));
    }
  });

  inputEl.addEventListener('input', autoResize);
  function autoResize() {
    inputEl.style.height = 'auto';
    inputEl.style.height = Math.min(inputEl.scrollHeight, 200) + 'px';
  }

  $$('.example-chip').forEach((chip) => {
    chip.addEventListener('click', () => {
      inputEl.value = chip.dataset.prompt || '';
      autoResize();
      inputEl.focus();
    });
  });

  // Init
  loadRoles();
  setMode('auto');
  setProvider('connecting…', 'connecting');
  wireOptBtns();
})();
