/* ==========================================================================
   Pantheon Web UI — Frontend logic (v2: 2-pane layout, god rows w/ model)
   ========================================================================== */

(function () {
  'use strict';

  // ---------- God metadata ----------
  const GOD_META = {
    hermes:     { icon: 'H',  label: 'Hermes',     color: 'var(--god-hermes)',     avatar: '/static/avatars/hermes.png' },
    hephaestus: { icon: 'He', label: 'Hephaestus', color: 'var(--god-hephaestus)', avatar: '/static/avatars/hephaestus.png' },
    athena:     { icon: 'A',  label: 'Athena',     color: 'var(--god-athena)',     avatar: '/static/avatars/athena.png' },
    apollo:     { icon: 'Ap', label: 'Apollo',     color: 'var(--god-apollo)',     avatar: '/static/avatars/apollo.png' },
    chronos:    { icon: 'C',  label: 'Chronos',    color: 'var(--god-chronos)',    avatar: '/static/avatars/chronos.png' },
    local:      { icon: 'L',  label: 'Local preview', color: 'var(--accent-3)', avatar: '' },
  };
  const FALLBACK_GOD = { icon: '?', label: '?', color: 'var(--accent)', avatar: '' };

  function metaFor(name) {
    return GOD_META[name] || { ...FALLBACK_GOD, label: name };
  }

  // ---------- Element refs ----------
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => Array.from(document.querySelectorAll(s));

  const chatEl       = $('#chat');
  const inputEl      = $('#input');
  const sendBtn      = $('#send-btn');
  const enhancePromptBtn = $('#enhance-prompt-btn');
  const composerForm = $('#composer');
  const attachBtn    = $('#attach-btn');
  const attachmentInput = $('#attachment-input');
  const attachmentListEl = $('#composer-attachments');
  const voiceBtn     = $('#voice-btn');
  const composerStatus = $('#composer-status');
  const composerStatusDot = $('.composer-status-dot');
  const slashCommandMenu = $('#slash-command-menu');
  const loginScreen  = $('#login-screen');
  const loginForm    = $('#login-form');
  const loginUsername = $('#login-username');
  const loginPassword = $('#login-password');
  const loginStatus  = $('#login-status');
  const loginSubmit  = $('#login-submit');
  const modeChips    = $$('.mode-chip');
  const modeDisplay  = $('#mode-display b');
  const currentModePill = $('#current-mode-pill');
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
  const mcpApprovalModal = $('#mcp-approval-modal');
  const mcpApprovalClose = $('#mcp-approval-close');
  const mcpApprovalAllow = $('#mcp-approval-allow');
  const mcpApprovalDeny = $('#mcp-approval-deny');
  const mcpApprovalRisk = $('#mcp-approval-risk');
  const mcpApprovalTool = $('#mcp-approval-tool');
  const mcpApprovalRole = $('#mcp-approval-role');
  const mcpApprovalServer = $('#mcp-approval-server');
  const mcpApprovalToolId = $('#mcp-approval-tool-id');
  const mcpApprovalArgs = $('#mcp-approval-args');
  const newChatBtn   = $('#new-chat-btn');
  const chatListEl   = $('#chat-list');
  const modeBriefEl  = $('#mode-brief');
  const toggleWsBtn  = $('#toggle-workspace');
  const workspaceEl  = $('#workspace');
  const workspaceClose = $('#workspace-close');
  const workspaceState = $('#workspace-state');
  const workspaceTabs = $$('#workspace .workspace-tab');
  const workspacePanes = $$('#workspace .ws-pane');
  const wsCopyBtn = $('#ws-copy-output');
  const wsTaskTitleEl = $('#ws-task-title');
  const wsTaskModeEl = $('#ws-task-mode');
  const wsTaskElapsedEl = $('#ws-task-elapsed');
  const wsPlanEl     = $('#ws-plan');
  const wsStepsEl    = $('#ws-steps');
  const wsOutputEl   = $('#ws-output');
  const wsClearOutputBtn = $('#ws-clear-output');
  const chronosJobsEl = $('#chronos-jobs');
  const chronosRefreshBtn = $('#chronos-refresh');
  const wsTerminalHints = $('#ws-terminal-hints');
  const wsPreviewStatus = $('#ws-preview-status');
  const wsPreviewHint = $('#ws-preview-hint');
  const wsPreviewViewport = $('#ws-preview-viewport');
  const wsPreviewShell = $('#ws-preview-shell');
  const wsPreviewFrame = $('#ws-preview-frame');
  const wsPreviewEmpty = $('#ws-preview-empty');
  const wsOpenPreviewBtn = $('#ws-open-preview');
  const wsReloadPreviewBtn = $('#ws-reload-preview');
  const wsDownloadPreviewBtn = $('#ws-download-preview');
  const wsPreviewZoom = $('#ws-preview-zoom');
  const wsPreviewDeviceBtns = $$('[data-preview-device]');
  const wsFilesEl = $('#ws-files');
  const wsFilesPathEl = $('#ws-files-path');
  const wsFilesUpBtn = $('#ws-files-up');
  const wsRefreshFilesBtn = $('#ws-refresh-files');
  const wsFileViewEl = $('#ws-file-view');
  const wsFileSelectedKind = $('#ws-file-selected-kind');
  const wsFileSelectedName = $('#ws-file-selected-name');
  const wsFileSelectedMeta = $('#ws-file-selected-meta');
  const wsCopyFilePathBtn = $('#ws-copy-file-path');
  const wsCopyFileContentBtn = $('#ws-copy-file-content');
  const wsPreviewFileBtn = $('#ws-preview-file');
  const wsTerminalCwdEl = $('#ws-terminal-cwd');
  const wsCommandForm = $('#ws-command-form');
  const wsCommandInput = $('#ws-command-input');
  const wsRunCommandBtn = $('#ws-run-command');
  const toggleSetBtn = $('#toggle-settings');
  const exportChatBtn = $('#export-chat');
  const settingsPanel = $('#settings-panel');
  const settingsClose = $('#settings-close');
  const settingsTabs = $$('.settings-tab');
  const settingsPanes = $$('.settings-pane');
  const settingsRoles = $('#settings-roles');
  const settingsRolesCount = $('#settings-roles-count');
  const settingsPy = $('#settings-py');
  const settingsStatus = $('#settings-status');
  const infoVersionPill = $('#info-version-pill');
  const infoUiVersion = $('#info-ui-version');
  const infoBackendVersion = $('#info-backend-version');
  const infoPythonVersion = $('#info-python-version');
  const infoConfigPath = $('#info-config-path');
  const infoEnvPath = $('#info-env-path');
  const infoWorkspacePath = $('#info-workspace-path');
  const infoSetupTitle = $('#info-setup-title');
  const infoSetupPill = $('#info-setup-pill');
  const infoProvider = $('#info-provider');
  const infoModel = $('#info-model');
  const infoAgents = $('#info-agents');
  const infoCopyDiagnosticsBtn = $('#info-copy-diagnostics');
  const sidebarVersion = $('#sidebar-version');
  const updateBanner = $('#update-banner');
  const updateBannerText = $('#update-banner-text');
  const updateBannerLink = $('#update-banner-link');
  const updateBannerDismiss = $('#update-banner-dismiss');
  const infoUpdatePill = $('#info-update-pill');
  const infoUpdateStatus = $('#info-update-status');
  const infoUpdateCheck = $('#info-update-check');
  const infoUpdateLink = $('#info-update-link');
  const infoConversationPill = $('#info-conversation-pill');
  const infoConversationStatus = $('#info-conversation-status');
  const infoBackupExport = $('#info-backup-export');
  const infoBackupImport = $('#info-backup-import');
  const infoBackupFile = $('#info-backup-file');
  const infoConversationRetry = $('#info-conversation-retry');
  const infoUsageRefresh = $('#info-usage-refresh');
  const infoUsageTotal = $('#info-usage-total');
  const infoUsageModels = $('#info-usage-models');
  const voiceLanguageSelect = $('#voice-language');
  const setupForm = $('#setup-form');
  const setupProviderSelect = $('#setup-provider');
  const setupModelInput = $('#setup-model');
  const setupUseCustomModel = $('#setup-use-custom-model');
  const setupCustomModelInput = $('#setup-custom-model');
  const setupBaseUrlInput = $('#setup-base-url');
  const setupApiKeyInput = $('#setup-api-key');
  const setupApplyRoles = $('#setup-apply-roles');
  const setupSaveBtn = $('#setup-save');
  const setupCheckBtn = $('#setup-check');
  const setupTestBtn = $('#setup-test');
  const setupRefreshModelsBtn = $('#setup-refresh-models');
  const setupModelStatus = $('#setup-model-status');
  const setupToggleKeyBtn = $('#setup-toggle-key');
  const setupStatusEl = $('#setup-status');
  const setupStatusTitle = $('#setup-status-title');
  const setupStatusPill = $('#setup-status-pill');
  const setupRoleList = $('#setup-role-list');
  const setupProviderNote = $('#setup-provider-note');
  const setupKeyStatus = $('#setup-key-status');
  const setupCheckResult = $('#setup-check-result');
  const setupConfigPath = $('#setup-config-path');
  const setupEnvPath = $('#setup-env-path');
  const securityForm = $('#security-form');
  const securityEnabled = $('#security-enabled');
  const securityUsername = $('#security-username');
  const securityPassword = $('#security-password');
  const securitySaveBtn = $('#security-save');
  const securityLogoutBtn = $('#security-logout');
  const securityStatusTitle = $('#security-status-title');
  const securityStatusPill = $('#security-status-pill');
  const securityResult = $('#security-result');
  const securityEnvPath = $('#security-env-path');
  const securitySession = $('#security-session');
  const memoryForm = $('#memory-form');
  const memoryEnabled = $('#memory-enabled');
  const memoryAutoCapture = $('#memory-auto-capture');
  const memoryContent = $('#memory-content');
  const memoryKind = $('#memory-kind');
  const memoryRole = $('#memory-role');
  const memorySaveBtn = $('#memory-save');
  const memoryRefreshBtn = $('#memory-refresh');
  const memoryClearBtn = $('#memory-clear');
  const memorySearch = $('#memory-search');
  const memorySuggestionList = $('#memory-suggestion-list');
  const memorySuggestionCount = $('#memory-suggestion-count');
  const memoryList = $('#memory-list');
  const memoryStatus = $('#memory-status');
  const memoryStatusTitle = $('#memory-status-title');
  const memoryStatusPill = $('#memory-status-pill');
  const memoryPath = $('#memory-path');
  const memoryCount = $('#memory-count');
  const integrationsStatusTitle = $('#integrations-status-title');
  const integrationsStatusPill = $('#integrations-status-pill');
  const integrationNav = $('#integration-nav');
  const integrationList = $('#integration-list');
  const integrationsConfigPath = $('#integrations-config-path');
  const integrationsEnvPath = $('#integrations-env-path');
  const integrationsPluginsPath = $('#integrations-plugins-path');
  const integrationsSkillsPath = $('#integrations-skills-path');

  // ---------- State ----------
  let currentMode = 'auto';
  let roles = [];
  let isStreaming = false;
  let promptEnhancing = false;
  let promptBeforeEnhance = '';
  let enhancedPromptValue = '';
  let abortCtrl = null;
  let turns = [];   // conversation history (in-memory only)
  let sessions = [];
  let activeSessionId = null;
  let isRestoringSession = false;
  let workspaceStreamText = '';
  let workspaceConsoleText = '';
  let workspacePreviewHtml = '';
  let workspacePreviewKind = 'empty';
  let workspacePreviewOpenUrl = '';
  let workspacePreviewLabel = 'preview.html';
  let workspacePreviewHint = '';
  let workspacePreviewDevice = 'desktop';
  let workspacePreviewScale = 1;
  let workspaceRootName = '';
  let workspaceCwd = '';
  let workspaceParent = null;
  let workspaceTerminalCwd = '';
  let workspaceCommandHistory = [];
  let workspaceCommandHistoryIndex = 0;
  let workspaceFiles = [];
  let workspaceSelectedFile = '';
  let workspaceSelectedFileData = null;
  let workspaceArtifacts = [];
  let workspaceAutoPreview = false;
  let workspacePreviewActivated = false;
  let workspaceTerminalRunning = false;
  let workspaceTaskStartedAt = 0;
  let workspaceTaskTimer = null;
  let chronosJobs = [];
  let chronosRuns = [];
  let pendingAttachments = [];
  let attachmentSeq = 0;
  let voiceRecognition = null;
  let voiceListening = false;
  let voiceBaseText = '';
  let voiceFinalText = '';
  let voiceLastError = false;
  let composerStatusTimer = null;
  let lastComposerToolPointerAt = 0;
  let slashCommandOpen = false;
  let slashCommandQuery = '';
  let slashCommandIndex = -1;
  let slashCommandMatches = [];
  let authState = { enabled: false, authenticated: true, username: 'admin' };
  let latestMemoryStats = null;
  let memoryItems = [];
  let memorySuggestions = [];
  let memorySearchTimer = null;
  let latestIntegrations = null;
  let integrationData = { skills: null, plugins: null, mcp: null, channels: null };
  let activeIntegrationSection = 'mcp';
  let pendingMcpApproval = null;
  let mcpApprovalResolving = false;
  const mcpWorkspaceCalls = new Map();
  let protectedDataLoaded = false;

  const MAX_ATTACHMENTS = 8;
  const MAX_ATTACHMENT_TEXT_CHARS = 12000;
  const TEXT_ATTACHMENT_EXTENSIONS = new Set([
    'css', 'csv', 'html', 'htm', 'ini', 'js', 'json', 'jsx', 'md', 'mjs',
    'py', 'sh', 'sql', 'toml', 'ts', 'tsx', 'txt', 'xml', 'yaml', 'yml',
  ]);

  // ---------- Helpers ----------
  function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[c]);
  }

  function cleanDisplayText(s) {
    return String(s == null ? '' : s).trim().replace(/^\p{Extended_Pictographic}\s*/u, '');
  }

  function avatarHtml(meta, className = 'god-avatar') {
    if (meta.avatar) {
      return `<span class="${className}"><img src="${escapeHtml(meta.avatar)}" alt="${escapeHtml(meta.label)}" loading="lazy"></span>`;
    }
    return `<span class="${className}">${escapeHtml(meta.icon)}</span>`;
  }

  function messageAvatarHtml(meta, fallbackIcon) {
    const icon = fallbackIcon || meta.icon || '?';
    if (meta.avatar) {
      return `
        <div class="msg-avatar has-image" style="--avatar-fallback-color: ${meta.color}" data-fallback="${escapeHtml(icon)}">
          <img src="${escapeHtml(meta.avatar)}" alt="${escapeHtml(meta.label)}" loading="lazy" onerror="this.remove(); this.parentElement.classList.remove('has-image');">
        </div>
      `;
    }
    return `<div class="msg-avatar">${escapeHtml(icon)}</div>`;
  }

  function roleKind(roleName) {
    if (roleName === 'hermes') return 'Router';
    if (roleName === 'hephaestus') return 'Build';
    if (roleName === 'athena') return 'Research';
    if (roleName === 'apollo') return 'Creative';
    if (roleName === 'chronos') return 'Schedule';
    return 'Agent';
  }

  function safeMarkdownHref(href) {
    const raw = String(href || '').trim();
    if (!raw) return '';
    const lower = raw.toLowerCase();
    if (
      lower.startsWith('http://') ||
      lower.startsWith('https://') ||
      lower.startsWith('mailto:') ||
      lower.startsWith('tel:') ||
      raw.startsWith('#') ||
      raw.startsWith('/')
    ) {
      return raw;
    }
    return '';
  }

  function renderInlineMarkdown(text) {
    const codeTokens = [];
    let s = String(text == null ? '' : text).replace(/`([^`]+)`/g, (_, code) => {
      const token = `@@PANTHEON_INLINE_CODE_${codeTokens.length}@@`;
      codeTokens.push(`<code>${escapeHtml(code)}</code>`);
      return token;
    });
    s = escapeHtml(s);
    s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, label, href) => {
      const safeHref = safeMarkdownHref(href.replace(/&amp;/g, '&'));
      if (!safeHref) return match;
      return `<a href="${escapeHtml(safeHref)}" target="_blank" rel="noopener noreferrer">${label}</a>`;
    });
    s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    s = s.replace(/__([^_]+)__/g, '<strong>$1</strong>');
    s = s.replace(/(^|[\s(])\*([^*\n]+)\*(?=[\s).,!?:;]|$)/g, '$1<em>$2</em>');
    s = s.replace(/(^|[\s(])_([^_\n]+)_(?=[\s).,!?:;]|$)/g, '$1<em>$2</em>');
    codeTokens.forEach((html, index) => {
      s = s.replaceAll(`@@PANTHEON_INLINE_CODE_${index}@@`, html);
    });
    return s;
  }

  function isMarkdownTableDivider(line) {
    return /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line);
  }

  function isMarkdownBlockStart(line, nextLine = '') {
    return /^#{1,6}\s+/.test(line) ||
      /^>\s?/.test(line) ||
      /^[-*+]\s+/.test(line) ||
      /^\d+\.\s+/.test(line) ||
      /^-{3,}\s*$/.test(line) ||
      (line.includes('|') && isMarkdownTableDivider(nextLine || ''));
  }

  function tableCells(line) {
    return line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((cell) => cell.trim());
  }

  function renderMarkdownBlocks(src) {
    const lines = String(src || '').replace(/\r\n/g, '\n').split('\n');
    const html = [];
    let i = 0;

    while (i < lines.length) {
      const line = lines[i];
      const trimmed = line.trim();
      if (!trimmed) {
        i += 1;
        continue;
      }

      const heading = trimmed.match(/^(#{1,6})\s+(.+)$/);
      if (heading) {
        const level = Math.min(6, heading[1].length);
        html.push(`<h${level}>${renderInlineMarkdown(heading[2])}</h${level}>`);
        i += 1;
        continue;
      }

      if (/^-{3,}\s*$/.test(trimmed)) {
        html.push('<hr>');
        i += 1;
        continue;
      }

      if (/^>\s?/.test(trimmed)) {
        const quoted = [];
        while (i < lines.length && /^>\s?/.test(lines[i].trim())) {
          quoted.push(lines[i].trim().replace(/^>\s?/, ''));
          i += 1;
        }
        html.push(`<blockquote>${renderMarkdownBlocks(quoted.join('\n'))}</blockquote>`);
        continue;
      }

      if (line.includes('|') && isMarkdownTableDivider(lines[i + 1] || '')) {
        const headers = tableCells(line);
        i += 2;
        const rows = [];
        while (i < lines.length && lines[i].includes('|') && lines[i].trim()) {
          rows.push(tableCells(lines[i]));
          i += 1;
        }
        html.push(`
          <table>
            <thead><tr>${headers.map((cell) => `<th>${renderInlineMarkdown(cell)}</th>`).join('')}</tr></thead>
            <tbody>${rows.map((row) => `<tr>${row.map((cell) => `<td>${renderInlineMarkdown(cell)}</td>`).join('')}</tr>`).join('')}</tbody>
          </table>
        `);
        continue;
      }

      if (/^[-*+]\s+/.test(trimmed)) {
        const items = [];
        while (i < lines.length && /^[-*+]\s+/.test(lines[i].trim())) {
          items.push(lines[i].trim().replace(/^[-*+]\s+/, ''));
          i += 1;
        }
        html.push(`<ul>${items.map((item) => `<li>${renderInlineMarkdown(item)}</li>`).join('')}</ul>`);
        continue;
      }

      if (/^\d+\.\s+/.test(trimmed)) {
        const items = [];
        while (i < lines.length && /^\d+\.\s+/.test(lines[i].trim())) {
          items.push(lines[i].trim().replace(/^\d+\.\s+/, ''));
          i += 1;
        }
        html.push(`<ol>${items.map((item) => `<li>${renderInlineMarkdown(item)}</li>`).join('')}</ol>`);
        continue;
      }

      const paragraph = [trimmed];
      i += 1;
      while (
        i < lines.length &&
        lines[i].trim() &&
        !isMarkdownBlockStart(lines[i].trim(), lines[i + 1] || '')
      ) {
        paragraph.push(lines[i].trim());
        i += 1;
      }
      html.push(`<p>${renderInlineMarkdown(paragraph.join(' '))}</p>`);
    }

    return html.join('');
  }

  function renderMarkdownFallback(text) {
    const raw = String(text == null ? '' : text);
    const html = [];
    const fenceRe = /```([^\n`]*)\n([\s\S]*?)```/g;
    let last = 0;
    let match;
    while ((match = fenceRe.exec(raw)) !== null) {
      html.push(renderMarkdownBlocks(raw.slice(last, match.index)));
      const lang = cleanDisplayText(match[1] || 'text').toLowerCase() || 'text';
      html.push(`<pre data-lang="${escapeHtml(lang)}"><code class="language-${escapeHtml(lang)}">${escapeHtml(match[2] || '')}</code></pre>`);
      last = match.index + match[0].length;
    }
    html.push(renderMarkdownBlocks(raw.slice(last)));
    return html.join('');
  }

  function renderMarkdown(text) {
    if (window.marked) {
      try {
        return window.marked.parse(text, { breaks: true, gfm: true });
      } catch (_) { /* fall through */ }
    }
    return renderMarkdownFallback(text);
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
    decorateHtmlPreviewBtns(root);
    decorateArtifactBtns(root);
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

  function renderModeBrief() {
    if (!modeBriefEl) return;
    if (currentMode === 'multi') {
      const chain = roles.filter((r) => r.name !== 'chronos').map((r) => {
        const meta = metaFor(r.name);
        return `<span class="mode-brief-chip" style="--god-color: ${meta.color}">${escapeHtml(meta.icon)} ${escapeHtml(meta.label)}</span>`;
      }).join('');
      modeBriefEl.innerHTML = `
        <div class="mode-brief-title">Forced collaboration</div>
        <p>Hermes must create a multi-step plan, then coordinate the gods instead of answering with one role.</p>
        ${chain ? `<div class="mode-brief-chain">${chain}</div>` : ''}
        <button class="mode-config-btn" type="button" data-open-models>Models for this chat</button>
      `;
      return;
    }
    if (currentMode.startsWith('role:')) {
      const roleName = currentMode.slice(5);
      const meta = metaFor(roleName);
      if (roleName === 'chronos') {
        modeBriefEl.innerHTML = `
          <div class="mode-brief-title">Chronos scheduling</div>
          <p>Create a local scheduled task with phrases like “every 10 minutes…” or “10分钟后提醒我…”.</p>
          <button class="mode-config-btn" type="button" data-open-models>Models for this chat</button>
        `;
        return;
      }
      modeBriefEl.innerHTML = `
        <div class="mode-brief-title">${escapeHtml(meta.label)} direct mode</div>
        <p>This chat will bypass routing and send the next task directly to ${escapeHtml(meta.label)}.</p>
        <button class="mode-config-btn" type="button" data-open-models>Models for this chat</button>
      `;
      return;
    }
    modeBriefEl.innerHTML = `
      <div class="mode-brief-title">Auto routing</div>
      <p>Hermes decides whether one god is enough or a full collaboration is needed for the task.</p>
      <button class="mode-config-btn" type="button" data-open-models>Models for this chat</button>
    `;
  }

  function setMode(mode) {
    currentMode = mode;
    modeChips.forEach((chip) => {
      chip.classList.toggle('active', chip.dataset.mode === mode);
      chip.setAttribute('aria-pressed', chip.dataset.mode === mode ? 'true' : 'false');
    });

    // Update topbar pill
    let label, icon;
    if (mode === 'auto') {
      label = 'Auto'; icon = 'A';
    } else if (mode === 'multi') {
      label = 'Multi-role'; icon = 'M';
    } else if (mode.startsWith('role:')) {
      const name = mode.slice(5);
      label = metaFor(name).label; icon = metaFor(name).icon;
    } else {
      label = mode; icon = '?';
    }
    topbarName.textContent = label;
    topbarIcon.textContent = icon;
    if (mode.startsWith('role:')) highlightGod(mode.slice(5));
    else clearGodHighlight();
    if (currentModePill) {
      currentModePill.dataset.mode = mode;
      currentModePill.setAttribute('aria-label', `Current mode: ${label}. Click to toggle Auto and Multi-role.`);
      currentModePill.title = mode === 'auto' ? 'Switch to Multi-role' : 'Switch to Auto';
    }

    // Update composer meta
    modeDisplay.textContent = label;
    if (inputEl) {
      inputEl.placeholder = mode === 'role:chronos'
        ? 'Ask Chronos to schedule a task…'
        : 'Ask the Pantheon…';
    }
    renderModeBrief();
    saveActiveSession();
    renderSessions();
  }

  // ---------- Render god list (sidebar) ----------
  function renderGods() {
    if (!roles.length) {
      godsList.innerHTML = '<div class="god-row loading"><span class="god-avatar">?</span><div class="god-info"><div class="god-name">No roles</div></div></div>';
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
      const badge = isChronosRow ? '<span class="god-badge" title="Scheduling role - no LLM">schedule</span>' : '';
      row.innerHTML = `
        ${avatarHtml(meta)}
        <div class="god-info">
          <div class="god-name">${escapeHtml(meta.label)}${badge}</div>
          <div class="god-model" title="${escapeHtml(r.model || 'no model')}">${isChronosRow ? 'scheduling' : escapeHtml(modelShort || r.model || '—')}</div>
        </div>
      `;
      if (isChronosRow) row.classList.add('scheduling');
      row.addEventListener('click', () => {
        setMode(`role:${r.name}`);
        inputEl.focus();
      });
      godsList.appendChild(row);
    }
    if (currentMode.startsWith('role:')) highlightGod(currentMode.slice(5));
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
        ${avatarHtml(meta, 'ar-icon')}
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

  function openMcpApproval(data = {}) {
    if (!mcpApprovalModal) return;
    pendingMcpApproval = data;
    const risk = ['read', 'write', 'destructive'].includes(data.risk) ? data.risk : 'unknown';
    mcpApprovalRisk.className = `mcp-risk ${risk}`;
    mcpApprovalRisk.textContent = mcpRiskLabel({ risk });
    mcpApprovalTool.textContent = data.tool_title || data.tool || 'MCP tool';
    mcpApprovalRole.textContent = metaFor(data.role || '').label;
    mcpApprovalServer.textContent = data.server_name || data.server_id || '—';
    mcpApprovalToolId.textContent = data.tool || '—';
    mcpApprovalArgs.textContent = JSON.stringify(data.arguments || {}, null, 2);
    mcpApprovalModal.hidden = false;
    mcpApprovalAllow?.focus();
  }

  function closeMcpApproval() {
    if (!mcpApprovalModal) return;
    mcpApprovalModal.hidden = true;
    mcpApprovalAllow.disabled = false;
    mcpApprovalDeny.disabled = false;
  }

  async function decideMcpApproval(approved) {
    if (!pendingMcpApproval || mcpApprovalResolving) return;
    const approval = pendingMcpApproval;
    mcpApprovalResolving = true;
    mcpApprovalAllow.disabled = true;
    mcpApprovalDeny.disabled = true;
    try {
      await integrationFetch(`/api/mcp/approvals/${encodeURIComponent(approval.approval_id)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approved }),
      });
      pendingMcpApproval = null;
      closeMcpApproval();
      setComposerStatus(approved ? 'MCP action allowed once' : 'MCP action denied', approved ? 'ok' : 'warn');
    } catch (error) {
      if (Number(error?.status || 0) === 404 || /expired|resolved/i.test(setupErrorMessage(error))) {
        pendingMcpApproval = null;
        closeMcpApproval();
      }
      setComposerStatus(setupErrorMessage(error), 'error');
    } finally {
      mcpApprovalResolving = false;
      if (pendingMcpApproval) {
        mcpApprovalAllow.disabled = false;
        mcpApprovalDeny.disabled = false;
      }
    }
  }

  mcpApprovalAllow?.addEventListener('click', () => decideMcpApproval(true));
  mcpApprovalDeny?.addEventListener('click', () => decideMcpApproval(false));
  mcpApprovalClose?.addEventListener('click', () => decideMcpApproval(false));
  mcpApprovalModal?.addEventListener('click', (event) => {
    if (event.target === mcpApprovalModal) decideMcpApproval(false);
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && mcpApprovalModal && !mcpApprovalModal.hidden) {
      event.preventDefault();
      decideMcpApproval(false);
    }
  });

  // ---------- Mode chip events ----------
  modeChips.forEach((chip) => {
    chip.addEventListener('click', () => setMode(chip.dataset.mode));
  });
  function toggleRoutingMode() {
    if (currentMode === 'auto') setMode('multi');
    else setMode('auto');
  }
  if (currentModePill) {
    currentModePill.addEventListener('click', toggleRoutingMode);
  }
  if (modeBriefEl) {
    modeBriefEl.addEventListener('click', (e) => {
      if (!e.target.closest('[data-open-models]')) return;
      openSettings();
      activateSettingsTab('models');
    });
  }

  // ---------- Workspace toggle ----------
  function openWorkspace() {
    if (!settingsPanel.hidden) closeSettings();
    workspaceEl.hidden = false;
    document.body.classList.add('workspace-open');
    toggleWsBtn.classList.add('active');
    loadWorkspaceFiles(workspaceCwd || '');
    loadChronosJobs({ silent: true });
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

  function activateWorkspaceTab(target) {
    workspaceTabs.forEach((tab) => {
      tab.classList.toggle('active', tab.dataset.wsTab === target);
    });
    workspacePanes.forEach((pane) => {
      pane.classList.toggle('active', pane.dataset.wsPane === target);
    });
  }

  workspaceTabs.forEach((tab) => {
    tab.addEventListener('click', () => activateWorkspaceTab(tab.dataset.wsTab));
  });

  // ---------- Settings toggle ----------
  function openSettings() {
    if (!workspaceEl.hidden) closeWorkspace();
    settingsPanel.hidden = false;
    document.body.classList.add('settings-open');
    toggleSetBtn.classList.add('active');
    if (settingsTabs.some((tab) => tab.dataset.tab === 'setup' && tab.classList.contains('active'))) {
      void loadSetupStatus({ quiet: true, preserveForm: true });
    }
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
  function activateSettingsTab(target) {
    settingsTabs.forEach((t) => t.classList.toggle('active', t.dataset.tab === target));
    settingsPanes.forEach((p) => p.classList.toggle('active', p.dataset.pane === target));
    if (target === 'setup') {
      void loadSetupStatus({ quiet: true, preserveForm: true });
    }
  }

  settingsTabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      activateSettingsTab(tab.dataset.tab);
      if (tab.dataset.tab === 'security') loadAuthStatus();
      if (tab.dataset.tab === 'memory') loadMemory();
      if (tab.dataset.tab === 'integrations') loadIntegrations();
    });
  });

  // ---------- Render settings → Models tab ----------
  // Provider metadata is a startup fallback only. Model IDs come from the backend
  // so Setup and per-role selectors share one runtime catalog.
  const SETUP_PROVIDER_FALLBACKS = [
    {
      id: 'deepseek',
      label: 'DeepSeek',
      model: '',
      models: [],
      base_url: 'https://api.deepseek.com',
      env_var: 'DEEPSEEK_API_KEY',
      requires_key: true,
      note: 'OpenAI-compatible provider.',
    },
    {
      id: 'openai',
      label: 'OpenAI',
      model: '',
      models: [],
      base_url: 'https://api.openai.com/v1',
      env_var: 'OPENAI_API_KEY',
      requires_key: true,
      note: 'Use this when you have an OpenAI API key.',
    },
    {
      id: 'anthropic',
      label: 'Anthropic',
      model: '',
      models: [],
      base_url: 'https://api.anthropic.com',
      env_var: 'ANTHROPIC_API_KEY',
      requires_key: true,
      note: 'Official Anthropic and compatible Claude Messages gateways. Change the Base URL only when your provider supplies one.',
    },
    {
      id: 'ollama',
      label: 'Ollama',
      model: '',
      models: [],
      base_url: 'http://localhost:11434',
      env_var: '',
      requires_key: false,
      note: 'Local model server. Start Ollama locally before sending requests.',
    },
  ];
  let setupProviders = new Map(SETUP_PROVIDER_FALLBACKS.map((p) => [p.id, p]));
  let latestSetupStatus = null;
  let latestAppInfo = null;

  // Persisted in-memory overrides from the settings UI.
  let roleOverrides = {}; // { roleName: { provider, model } }

  function providerModels(provider) {
    if (provider === 'none') return [{ id: 'none', label: '(no model)' }];
    return setupProviders.get(provider)?.models || [];
  }
  function providerModelIds(provider) {
    return providerModels(provider).map((m) => m.id);
  }
  function modelLabel(provider, id) {
    const entry = providerModels(provider).find((m) => m.id === id);
    return entry ? entry.label : id;
  }

  function roleModelInfo(roleName) {
    if (!roleName || roleName === 'user' || roleName === 'error') return null;
    const override = roleOverrides[roleName];
    if (override?.model) {
      return {
        provider: override.provider || '',
        model: override.model,
        label: modelLabel(override.provider || '', override.model),
        overridden: true,
      };
    }
    const role = roles.find((item) => item.name === roleName);
    if (!role?.model) return null;
    return {
      provider: role.provider || '',
      model: role.model,
      label: modelLabel(role.provider || '', role.model),
      overridden: false,
    };
  }

  function messageKindLabel(roleName) {
    if (roleName === 'user') return 'Task';
    if (roleName === 'error') return 'Error';
    return roleKind(roleName);
  }

  function messageModelHtml(roleName) {
    const modelInfo = roleModelInfo(roleName);
    if (!modelInfo) return '';
    const label = `${modelInfo.label}${modelInfo.overridden ? ' · override' : ''}`;
    return `<span class="msg-model" title="${escapeHtml(modelInfo.model)}">${escapeHtml(label)}</span>`;
  }

  function formatDuration(ms) {
    const value = Number(ms || 0);
    if (!value) return '';
    if (value < 1000) return `${Math.round(value)}ms`;
    return `${(value / 1000).toFixed(1)}s`;
  }

  function renderSettingsModels() {
    settingsRoles.innerHTML = '';
    for (const r of roles) {
      const meta = metaFor(r.name);
      const provider = r.provider || 'none';
      const override = roleOverrides[r.name] || {};
      const currentProvider = override.provider || provider;
      const currentModel = override.model || r.model || '';
      const knownProviders = [...setupProviders.keys(), 'none'];
      const knownModelIds = providerModelIds(currentProvider);

      const card = document.createElement('div');
      card.className = 'settings-role';
      card.dataset.role = r.name;
      const isChronos = (r.name === 'chronos');
      if (isChronos) card.classList.add('scheduling-role');
      const lockAttrs = isChronos ? 'disabled title="This role has no LLM by design (scheduling only)"' : '';
      card.innerHTML = `
        <div class="settings-role-head">
          ${avatarHtml(meta, 'sr-avatar')}
          <span class="sr-name">${escapeHtml(meta.label)}</span>
          ${isChronos ? '<span class="sr-badge">scheduling</span>' : ''}
        </div>
        ${r.note ? `<div class="settings-role-note">${escapeHtml(cleanDisplayText(r.note))}</div>` : ''}
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
      // option so the user can still see what was set (for example a custom yaml model).
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
        saveActiveSession();
        renderSessions();
      });
      modSel.addEventListener('change', () => {
        roleOverrides[r.name] = { provider: provSel.value, model: modSel.value };
        modSel.classList.add('changed');
        provSel.classList.add('changed');
        saveActiveSession();
        renderSessions();
      });
    }
  }

  // Get current effective provider/model for a role (with override)
  function effectiveModel(roleName) {
    return roleOverrides[roleName] || null;
  }

  function renderSettingsInfo() {
    if (settingsRolesCount) settingsRolesCount.textContent = String(roles.length);
    if (settingsStatus) settingsStatus.textContent = providerDot.classList.contains('offline') ? 'disconnected' : 'connected';
    if (settingsPy) settingsPy.textContent = latestAppInfo?.python_version || '—';

    const version = latestAppInfo?.ui_version || '0.2.2';
    const renderedVersion = String(version).startsWith('v') ? version : `v${version}`;
    if (infoVersionPill) infoVersionPill.textContent = renderedVersion;
    if (infoUiVersion) infoUiVersion.textContent = renderedVersion;
    if (sidebarVersion) sidebarVersion.textContent = `UI ${renderedVersion}`;
    if (infoBackendVersion) {
      const backendVersion = latestAppInfo?.backend_version || version;
      infoBackendVersion.textContent = String(backendVersion).startsWith('v') ? backendVersion : `v${backendVersion}`;
    }
    if (infoPythonVersion) infoPythonVersion.textContent = latestAppInfo?.python_version || '—';

    const setup = latestSetupStatus || {};
    if (infoConfigPath) {
      infoConfigPath.textContent = latestAppInfo?.config_path || setup.config_path || '—';
      infoConfigPath.title = latestAppInfo?.config_path || setup.config_path || '';
    }
    if (infoEnvPath) {
      infoEnvPath.textContent = latestAppInfo?.env_path || setup.env_path || '—';
      infoEnvPath.title = latestAppInfo?.env_path || setup.env_path || '';
    }
    if (infoWorkspacePath) {
      infoWorkspacePath.textContent = latestAppInfo?.workspace_path || '—';
      infoWorkspacePath.title = latestAppInfo?.workspace_path || '';
    }

    const readyCount = setup.ready_count ?? 0;
    const roleCount = setup.role_count ?? 0;
    if (infoSetupTitle) infoSetupTitle.textContent = setup.summary_title || providerPill.textContent || 'Loading...';
    if (infoSetupPill) {
      infoSetupPill.textContent = setup.setup_ready ? 'ready' : roleCount ? `${readyCount}/${roleCount} ready` : 'checking';
      infoSetupPill.classList.remove('ok', 'warn', 'error');
      if (setup.setup_ready) infoSetupPill.classList.add('ok');
      else if (roleCount) infoSetupPill.classList.add('warn');
    }
    if (infoProvider) infoProvider.textContent = setup.provider_label || '—';
    if (infoModel) {
      infoModel.textContent = setup.model || '—';
      infoModel.title = setup.model || '';
    }
    if (infoAgents) infoAgents.textContent = roleCount ? `${readyCount}/${roleCount} ready` : `${roles.length} loaded`;
  }

  function diagnosticsText() {
    const setup = latestSetupStatus || {};
    const info = latestAppInfo || {};
    const readyCount = setup.ready_count ?? 0;
    const roleCount = setup.role_count ?? 0;
    const version = info.ui_version || '0.2.2';
    const renderedVersion = String(version).startsWith('v') ? version : `v${version}`;
    const lines = [
      'Pantheon diagnostics',
      `Generated: ${new Date().toLocaleString()}`,
      '',
      `UI: ${renderedVersion}`,
      `Backend: ${info.backend_version ? (String(info.backend_version).startsWith('v') ? info.backend_version : `v${info.backend_version}`) : '—'}`,
      `Python: ${info.python_version || '—'}`,
      '',
      `Workspace: ${info.workspace_path || '—'}`,
      `Config: ${info.config_path || setup.config_path || '—'}`,
      `Secrets: ${info.env_path || setup.env_path || '—'}`,
      '',
      `Setup: ${setup.summary_title || '—'}`,
      `Provider: ${setup.provider_label || '—'}`,
      `Model: ${setup.model || '—'}`,
      `Agents: ${roleCount ? `${readyCount}/${roleCount} ready` : `${roles.length} loaded`}`,
      `Login lock: ${authState.enabled ? `enabled (${authState.username || 'user'})` : 'disabled'}`,
    ];
    if (Array.isArray(setup.role_statuses) && setup.role_statuses.length) {
      lines.push('', 'Agent status:');
      setup.role_statuses.forEach((item) => {
        lines.push(`- ${item.label || item.role}: ${item.provider_label || item.provider || '—'} / ${item.model || '—'} / ${item.status || '—'}`);
      });
    }
    return lines.join('\n');
  }

  async function copyDiagnostics() {
    if (!infoCopyDiagnosticsBtn) return;
    const ok = await copyToClipboard(diagnosticsText());
    flashCopied(infoCopyDiagnosticsBtn, ok ? 'Copied' : 'Failed');
    setComposerStatus(ok ? 'Diagnostics copied' : 'Could not copy diagnostics', ok ? 'ok' : 'error');
  }

  if (infoCopyDiagnosticsBtn) {
    infoCopyDiagnosticsBtn.addEventListener('click', copyDiagnostics);
  }

  function providerLabelFromSetup(id) {
    return setupProviders.get(id)?.label || id || 'Provider';
  }

  function setupModelOptions(provider) {
    return Array.isArray(provider?.models) && provider.models.length
      ? provider.models
      : [{ id: provider?.model || '', label: provider?.model || 'Default model' }].filter((item) => item.id);
  }

  function setupModelOptionLabel(model) {
    const label = model.label || model.id;
    if (model.source === 'current' && model.available === false) return `${label} · current, not returned by model list`;
    if (model.source === 'current' && model.available === true) return `${label} · current · listed`;
    if (model.source === 'available') return `${label} · listed`;
    return label;
  }

  function setupModelStatusText(provider) {
    if (!provider) return '';
    const options = setupModelOptions(provider);
    const count = options.length;
    const available = options.filter((model) => model.available === true).length;
    if (provider.catalog_source === 'live') return `${available} listed by provider · ${count} choices · Test API confirms access`;
    if (provider.catalog_source === 'cache') {
      const suffix = provider.catalog_stale ? ' · refresh recommended' : '';
      return `${available} listed · ${count} choices · cached${suffix}`;
    }
    if (provider.catalog_source === 'documented') {
      return `${count} documented models · use Test API to verify access`;
    }
    if (provider.requires_key && !provider.key_configured) {
      return 'Official recommendations · add an API key to refresh models and verify access';
    }
    return 'Official recommendations · configured official providers are checked every 24 hours';
  }

  function setSetupCustomModel(enabled, value = '') {
    if (setupUseCustomModel) setupUseCustomModel.checked = Boolean(enabled);
    if (setupModelInput) setupModelInput.disabled = Boolean(enabled);
    if (setupCustomModelInput) {
      setupCustomModelInput.hidden = !enabled;
      if (value) setupCustomModelInput.value = value;
    }
  }

  function renderSetupModelOptions(provider, selectedModel = '') {
    if (!setupModelInput) return;
    const options = setupModelOptions(provider);
    setupModelInput.innerHTML = options.map((model) => (
      `<option value="${escapeHtml(model.id)}">${escapeHtml(setupModelOptionLabel(model))}</option>`
    )).join('');
    const knownIds = options.map((item) => item.id);
    const fallback = knownIds.includes(provider?.model) ? provider.model : knownIds[0] || '';
    if (selectedModel && knownIds.includes(selectedModel)) {
      setupModelInput.value = selectedModel;
      setSetupCustomModel(false);
    } else if (selectedModel && !knownIds.includes(selectedModel)) {
      setupModelInput.value = fallback;
      setSetupCustomModel(true, selectedModel);
    } else {
      setupModelInput.value = fallback;
      setSetupCustomModel(false);
      if (setupCustomModelInput) setupCustomModelInput.value = '';
    }
  }

  function populateSetupProviders(providers) {
    const list = Array.isArray(providers) && providers.length ? providers : SETUP_PROVIDER_FALLBACKS;
    setupProviders = new Map(list.map((p) => [p.id, p]));
    if (!setupProviderSelect) return;
    const current = setupProviderSelect.value;
    setupProviderSelect.innerHTML = list.map((p) => (
      `<option value="${escapeHtml(p.id)}">${escapeHtml(p.label)}</option>`
    )).join('');
    if (current && setupProviders.has(current)) setupProviderSelect.value = current;
  }

  function setSetupBusy(isBusy) {
    if (setupSaveBtn) setupSaveBtn.disabled = isBusy;
    if (setupCheckBtn) setupCheckBtn.disabled = isBusy;
    if (setupTestBtn) setupTestBtn.disabled = isBusy;
    if (setupRefreshModelsBtn) setupRefreshModelsBtn.disabled = isBusy;
  }

  function setSetupPill(text, tone = '') {
    if (!setupStatusPill) return;
    setupStatusPill.textContent = text;
    setupStatusPill.classList.remove('ok', 'warn', 'error');
    if (tone) setupStatusPill.classList.add(tone);
  }

  function renderSetupCheckResult(title, lines = [], tone = '') {
    if (!setupCheckResult) return;
    const items = Array.isArray(lines) ? lines.filter(Boolean) : [];
    setupCheckResult.hidden = false;
    setupCheckResult.classList.remove('ok', 'warn', 'error');
    if (tone) setupCheckResult.classList.add(tone);
    setupCheckResult.innerHTML = `
      <span class="setup-check-kicker">Status</span>
      <span class="setup-check-head">
        <span class="setup-check-light" aria-hidden="true"></span>
        <strong>${escapeHtml(title)}</strong>
      </span>
      ${items.length ? `<ul>${items.map((line) => `<li>${escapeHtml(line)}</li>`).join('')}</ul>` : ''}
    `;
  }

  function clearSetupCheckResult() {
    if (!setupCheckResult) return;
    setupCheckResult.hidden = true;
    setupCheckResult.innerHTML = '';
    setupCheckResult.classList.remove('ok', 'warn', 'error');
  }

  function syncSetupProviderFields({ useDefaults = true } = {}) {
    if (!setupProviderSelect) return;
    const provider = setupProviders.get(setupProviderSelect.value) || SETUP_PROVIDER_FALLBACKS[0];
    if (useDefaults) {
      clearSetupCheckResult();
      renderSetupModelOptions(provider);
      if (setupBaseUrlInput) setupBaseUrlInput.value = provider.base_url || '';
      if (setupApiKeyInput) setupApiKeyInput.value = '';
    }
    if (setupProviderNote) {
      setupProviderNote.textContent = provider.note || '';
      setupProviderNote.hidden = !provider.note;
    }
    if (setupModelStatus) setupModelStatus.textContent = setupModelStatusText(provider);
    if (setupApiKeyInput) {
      setupApiKeyInput.placeholder = provider.requires_key
        ? `Paste ${provider.env_var || 'API key'} once, then save`
        : 'No API key required';
    }
    if (setupKeyStatus) {
      setupKeyStatus.textContent = provider.requires_key
        ? `${provider.env_var || 'API key'} will be saved to .env`
        : 'No API key required for this provider';
    }
  }

  function renderSetupRoleStatuses(statuses = []) {
    if (!setupRoleList) return;
    if (!Array.isArray(statuses) || !statuses.length) {
      setupRoleList.innerHTML = '<div class="settings-hint">No saved role config found yet.</div>';
      return;
    }
    setupRoleList.innerHTML = statuses.map((item) => {
      const label = item.label || item.role || 'Role';
      const purpose = item.purpose || '';
      const provider = item.provider_label || item.provider || 'Provider';
      const model = item.model || 'not set';
      const env = item.env_var ? ` · ${item.env_var}` : '';
      const status = item.status || 'not_configured';
      const statusLabel = item.status_label || status;
      return `
        <div class="setup-role-row" data-role="${escapeHtml(item.role || '')}">
          <div class="setup-role-main">
            <span class="setup-role-name">${escapeHtml(label)}</span>
            <span class="setup-role-purpose">${escapeHtml(purpose)}</span>
          </div>
          <div class="setup-role-model">
            <strong title="${escapeHtml(model)}">${escapeHtml(model)}</strong>
            <span>${escapeHtml(provider)}${escapeHtml(env)}</span>
          </div>
          <span class="setup-role-status ${escapeHtml(status)}">${escapeHtml(statusLabel)}</span>
        </div>
      `;
    }).join('');
  }

  function applySetupStatus(status, options = {}) {
    if (!setupForm || !status) return;
    latestSetupStatus = status;
    const preserveForm = Boolean(options.preserveForm);
    const announce = options.announce !== false;
    const formProvider = preserveForm ? setupProviderSelect?.value || '' : '';
    const formModel = preserveForm
      ? (
        setupUseCustomModel?.checked
          ? setupCustomModelInput?.value || ''
          : setupModelInput?.value || ''
      ).trim()
      : '';
    const formBaseUrl = preserveForm ? setupBaseUrlInput?.value || '' : '';

    populateSetupProviders(status.providers);
    renderSettingsModels();
    if (preserveForm) {
      if (setupProviderSelect && formProvider && setupProviders.has(formProvider)) {
        setupProviderSelect.value = formProvider;
      }
      const provider = setupProviders.get(setupProviderSelect?.value || status.provider);
      renderSetupModelOptions(provider, formModel);
      if (setupBaseUrlInput) setupBaseUrlInput.value = formBaseUrl || provider?.base_url || '';
      syncSetupProviderFields({ useDefaults: false });
    } else {
      if (setupProviderSelect && status.provider && setupProviders.has(status.provider)) {
        setupProviderSelect.value = status.provider;
      }
      if (setupModelInput) setupModelInput.value = status.model || setupProviders.get(status.provider)?.model || '';
      if (setupBaseUrlInput) setupBaseUrlInput.value = status.base_url || setupProviders.get(status.provider)?.base_url || '';
      if (setupApiKeyInput) setupApiKeyInput.value = '';
      renderSetupModelOptions(setupProviders.get(status.provider), status.model || '');
      if (setupBaseUrlInput) setupBaseUrlInput.value = status.base_url || setupProviders.get(status.provider)?.base_url || '';
      syncSetupProviderFields({ useDefaults: false });
    }

    const label = status.provider_label || providerLabelFromSetup(status.provider);
    if (setupStatusTitle) {
      setupStatusTitle.textContent = status.summary_title || `${label} · ${status.model || 'model not set'}`;
    }
    renderSetupRoleStatuses(status.role_statuses || []);
    if (setupKeyStatus && !preserveForm) {
      if (status.requires_key) {
        setupKeyStatus.textContent = status.key_configured
          ? `${status.env_var} configured (${status.masked_key || 'masked'})`
          : `${status.env_var} is not configured yet`;
      } else {
        setupKeyStatus.textContent = 'No API key required for this provider';
      }
    }
    if (setupConfigPath) {
      setupConfigPath.textContent = status.config_path || '—';
      setupConfigPath.title = status.config_path || '';
    }
    if (setupEnvPath) {
      setupEnvPath.textContent = status.env_path || '—';
      setupEnvPath.title = status.env_path || '';
    }
    if (status.setup_ready) {
      setSetupPill('ready', 'ok');
      if (setupStatusEl) setupStatusEl.title = status.message || 'All chat agents have usable provider configuration.';
    } else {
      setSetupPill(`${status.ready_count || 0}/${status.role_count || 0} ready`, 'warn');
      if (setupStatusEl) setupStatusEl.title = status.message || 'Some chat agents need API configuration.';
    }
    if (announce && status.message) setComposerStatus(status.message, status.setup_ready ? 'ok' : 'warn');
    renderSettingsInfo();
  }

  function setupErrorMessage(err) {
    if (typeof err === 'string') return err;
    return err?.detail || err?.message || 'Setup request failed';
  }

  function shortSetupProblem(message = '') {
    const text = String(message || '').trim();
    if (!text) return 'Request failed';
    if (/invalid_api_key|incorrect api key|401/i.test(text)) return 'API key was rejected';
    if (/model.*not.*found|does not exist|not found|404/i.test(text)) return 'Model was not found';
    if (/quota|billing|insufficient/i.test(text)) return 'Billing or quota problem';
    if (/timeout|timed out/i.test(text)) return 'Connection timed out';
    if (/network|connection|dns|name resolution|failed to connect/i.test(text)) return 'Network connection failed';
    return text.length > 96 ? `${text.slice(0, 96)}...` : text;
  }

  async function loadSetupStatus(options = {}) {
    if (!setupForm) return;
    const quiet = Boolean(options?.quiet);
    if (!quiet) setSetupPill('checking');
    try {
      const resp = await fetch('/api/setup/status');
      const data = await resp.json();
      if (!resp.ok) throw data;
      applySetupStatus(data, {
        preserveForm: Boolean(options?.preserveForm),
        announce: !quiet,
      });
    } catch (e) {
      console.error(e);
      if (setupStatusTitle) setupStatusTitle.textContent = 'Setup unavailable';
      if (setupKeyStatus) setupKeyStatus.textContent = setupErrorMessage(e);
      setSetupPill('error', 'error');
      renderSettingsInfo();
    }
  }

  async function loadAppInfo() {
    try {
      const resp = await fetch('/api/info');
      const data = await resp.json();
      if (!resp.ok) throw data;
      latestAppInfo = data;
    } catch (e) {
      console.error(e);
      latestAppInfo = latestAppInfo || {};
    } finally {
      renderSettingsInfo();
    }
  }

  async function loadUpdateStatus(force = false) {
    try {
      const resp = await fetch(force ? '/api/update/check' : '/api/update', force ? { method: 'POST' } : {});
      const data = await resp.json();
      if (!resp.ok) throw data;
      if (data.error && !data.latest_version) {
        infoUpdatePill.textContent = 'offline';
        infoUpdateStatus.textContent = 'Could not check GitHub releases. Try again later.';
        return;
      }
      const dismissed = localStorage.getItem('pantheon:dismissed-update');
      updateBanner.hidden = !data.update_available || dismissed === data.latest_version;
      if (data.update_available) {
        infoUpdatePill.textContent = 'available';
        infoUpdateStatus.textContent = `${data.latest_version} is available (installed: v${data.current_version}). Update when your chats are idle.`;
        updateBannerText.textContent = `Pantheon ${data.latest_version} is available. Your current version is v${data.current_version}.`;
        updateBannerLink.href = data.release_url;
      } else {
        infoUpdatePill.textContent = 'current';
        infoUpdateStatus.textContent = `You have v${data.current_version}; no newer release has been published.`;
      }
      infoUpdateLink.href = data.update_available ? data.release_url : 'https://github.com/RyosukeSAMA/github-ai/blob/main/docs/setup.md#11-update-pantheon';
      infoUpdateLink.textContent = data.update_available ? 'View release' : 'How to update';
      if (data.error) infoUpdateStatus.textContent += ' (Showing the last successful check.)';
    } catch (e) {
      infoUpdatePill.textContent = 'error';
      infoUpdateStatus.textContent = 'Could not check for updates.';
    }
  }
  infoUpdateCheck?.addEventListener('click', () => loadUpdateStatus(true));
  updateBannerDismiss?.addEventListener('click', () => {
    const latest = updateBannerText.textContent.match(/Pantheon (v?\d+\.\d+\.\d+)/)?.[1];
    if (latest) localStorage.setItem('pantheon:dismissed-update', latest);
    updateBanner.hidden = true;
  });

  async function loadUsage() {
    try {
      const resp = await fetch('/api/usage');
      const data = await resp.json();
      if (!resp.ok) throw data;
      const totals = data.totals || {};
      infoUsageTotal.textContent = `${(totals.calls || 0).toLocaleString()} calls · ${(totals.input_tokens || 0).toLocaleString()} input tokens · ${(totals.output_tokens || 0).toLocaleString()} output tokens`;
      infoUsageModels.replaceChildren();
      for (const row of data.models || []) {
        const item = document.createElement('div');
        item.className = 'usage-model';
        const name = document.createElement('strong');
        name.textContent = `${row.provider} / ${row.model}`;
        const detail = document.createElement('span');
        detail.textContent = `${row.calls} calls · ${row.input_tokens.toLocaleString()} in / ${row.output_tokens.toLocaleString()} out${row.metered_calls < row.calls ? ` · ${row.calls - row.metered_calls} unmetered` : ''}`;
        item.append(name, detail);
        infoUsageModels.appendChild(item);
      }
    } catch (e) {
      infoUsageTotal.textContent = 'Usage statistics unavailable.';
    }
  }
  infoUsageRefresh?.addEventListener('click', loadUsage);

  async function checkSetup() {
    if (!setupForm) return;
    setSetupBusy(true);
    setSetupPill('checking');
    renderSetupCheckResult('Checking setup...');
    try {
      const resp = await fetch('/api/setup/check', { method: 'POST' });
      const data = await resp.json();
      if (!resp.ok) throw data;
      applySetupStatus(data, { preserveForm: true, announce: false });
      if (data.ok) {
        renderSetupCheckResult('Setup complete', [], 'ok');
        setComposerStatus('Local config looks ready', 'ok');
      } else {
        const problems = Array.isArray(data.problems) ? data.problems : [];
        const problem = problems[0] || 'Config needs attention';
        renderSetupCheckResult('Setup needs attention', problems.length ? problems : [problem], 'warn');
        setComposerStatus(problem, 'warn', true);
        setSetupPill('needs fix', 'warn');
      }
    } catch (e) {
      console.error(e);
      const message = setupErrorMessage(e);
      if (setupKeyStatus) setupKeyStatus.textContent = message;
      renderSetupCheckResult('Check failed', [message], 'error');
      setSetupPill('error', 'error');
      setComposerStatus(message, 'error', true);
    } finally {
      setSetupBusy(false);
    }
  }

  function setupRequestBody() {
    const provider = setupProviderSelect?.value || 'deepseek';
    return {
      provider,
      model: (
        setupUseCustomModel?.checked
          ? setupCustomModelInput?.value || ''
          : setupModelInput?.value || ''
      ).trim(),
      base_url: (setupBaseUrlInput?.value || '').trim(),
      api_key: (setupApiKeyInput?.value || '').trim(),
      apply_to_roles: setupApplyRoles ? setupApplyRoles.checked : true,
    };
  }

  async function testSetupApi() {
    if (!setupForm) return;
    setSetupBusy(true);
    setSetupPill('testing');
    renderSetupCheckResult('Testing API...');
    try {
      const resp = await fetch('/api/setup/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(setupRequestBody()),
      });
      const data = await resp.json();
      if (!resp.ok) throw data;
      if (data.ok) {
        renderSetupCheckResult('API connected', [], 'ok');
        setSetupPill('api ok', 'ok');
        setComposerStatus('API connection works', 'ok');
      } else {
        const problem = data.problem || 'API test failed';
        renderSetupCheckResult('API test failed', [problem], 'error');
        setSetupPill('api failed', 'error');
        setComposerStatus(shortSetupProblem(problem), 'error', true);
      }
    } catch (e) {
      console.error(e);
      const message = setupErrorMessage(e);
      if (setupKeyStatus) setupKeyStatus.textContent = message;
      renderSetupCheckResult('API test failed', [message], 'error');
      setSetupPill('api failed', 'error');
      setComposerStatus(shortSetupProblem(message), 'error', true);
    } finally {
      setSetupBusy(false);
    }
  }

  async function refreshSetupModels() {
    if (!setupProviderSelect) return;
    const providerId = setupProviderSelect.value;
    const existingProvider = setupProviders.get(providerId);
    const currentModel = (
      setupUseCustomModel?.checked
        ? setupCustomModelInput?.value || ''
        : setupModelInput?.value || ''
    ).trim();
    setSetupBusy(true);
    if (setupModelStatus) setupModelStatus.textContent = 'Refreshing available models...';
    try {
      const resp = await fetch('/api/setup/models', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: providerId,
          base_url: (setupBaseUrlInput?.value || '').trim(),
          api_key: (setupApiKeyInput?.value || '').trim(),
          current_model: currentModel,
        }),
      });
      const data = await resp.json();
      if (!resp.ok) throw data;
      const provider = data.provider || existingProvider;
      if (provider) setupProviders.set(providerId, provider);
      renderSetupModelOptions(provider, data.preserved_model || currentModel);
      if (setupModelStatus) setupModelStatus.textContent = setupModelStatusText(provider);
      renderSettingsModels();
      if (data.ok) {
        setComposerStatus(data.message || 'Models refreshed', 'ok');
      } else {
        setComposerStatus(shortSetupProblem(data.problem || data.message), 'warn', true);
      }
    } catch (e) {
      console.error(e);
      const message = setupErrorMessage(e);
      if (setupModelStatus) setupModelStatus.textContent = message;
      setComposerStatus(shortSetupProblem(message), 'error', true);
    } finally {
      setSetupBusy(false);
    }
  }

  async function saveSetup(event) {
    event.preventDefault();
    if (!setupProviderSelect) return;
    const body = setupRequestBody();
    setSetupBusy(true);
    setSetupPill('saving');
    try {
      const resp = await fetch('/api/setup/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await resp.json();
      if (!resp.ok) throw data;
      applySetupStatus(data);
      await loadRoles();
      renderSetupCheckResult('Local config saved', [
        'Saved provider/model choices to config/pantheon.yaml.',
        'Saved the API key to .env when a new key was provided.',
      ], 'ok');
      setComposerStatus('Local config saved', 'ok');
    } catch (e) {
      console.error(e);
      const message = setupErrorMessage(e);
      if (setupKeyStatus) setupKeyStatus.textContent = message;
      setSetupPill('error', 'error');
      setComposerStatus(message, 'error', true);
    } finally {
      setSetupBusy(false);
    }
  }

  if (setupProviderSelect) {
    populateSetupProviders();
    setupProviderSelect.addEventListener('change', () => syncSetupProviderFields({ useDefaults: true }));
    syncSetupProviderFields();
  }
  if (setupUseCustomModel) {
    setupUseCustomModel.addEventListener('change', () => {
      const custom = setupUseCustomModel.checked;
      setSetupCustomModel(custom);
      if (custom && setupCustomModelInput) {
        setupCustomModelInput.value = setupModelInput?.value || '';
        setupCustomModelInput.focus();
      }
    });
  }
  if (setupForm) setupForm.addEventListener('submit', saveSetup);
  if (setupCheckBtn) setupCheckBtn.addEventListener('click', checkSetup);
  if (setupTestBtn) setupTestBtn.addEventListener('click', testSetupApi);
  if (setupRefreshModelsBtn) setupRefreshModelsBtn.addEventListener('click', refreshSetupModels);
  [setupModelInput, setupCustomModelInput, setupBaseUrlInput, setupApiKeyInput].forEach((el) => {
    if (!el) return;
    el.addEventListener('input', clearSetupCheckResult);
    el.addEventListener('change', clearSetupCheckResult);
  });
  if (setupToggleKeyBtn && setupApiKeyInput) {
    setupToggleKeyBtn.addEventListener('click', () => {
      const showing = setupApiKeyInput.type === 'text';
      setupApiKeyInput.type = showing ? 'password' : 'text';
      setupToggleKeyBtn.textContent = showing ? 'Show' : 'Hide';
    });
  }

  // ---------- Local UI authentication ----------
  function setLoginStatus(message = '') {
    if (!loginStatus) return;
    loginStatus.textContent = message;
    loginStatus.hidden = !message;
  }

  function setAuthLocked(locked) {
    document.body.classList.toggle('auth-locked', Boolean(locked));
    if (loginScreen) loginScreen.hidden = !locked;
    if (locked) {
      setTimeout(() => loginPassword?.focus(), 0);
    }
  }

  function setSecurityPill(text, tone = '') {
    if (!securityStatusPill) return;
    securityStatusPill.textContent = text;
    securityStatusPill.classList.remove('ok', 'warn', 'error');
    if (tone) securityStatusPill.classList.add(tone);
  }

  function renderSecurityResult(title, lines = [], tone = '') {
    if (!securityResult) return;
    const items = Array.isArray(lines) ? lines.filter(Boolean) : [];
    securityResult.hidden = false;
    securityResult.classList.remove('ok', 'warn', 'error');
    if (tone) securityResult.classList.add(tone);
    securityResult.innerHTML = `
      <span class="setup-check-kicker">Status</span>
      <span class="setup-check-head">
        <span class="setup-check-light" aria-hidden="true"></span>
        <strong>${escapeHtml(title)}</strong>
      </span>
      ${items.length ? `<ul>${items.map((line) => `<li>${escapeHtml(line)}</li>`).join('')}</ul>` : ''}
    `;
  }

  function clearSecurityResult() {
    if (!securityResult) return;
    securityResult.hidden = true;
    securityResult.innerHTML = '';
    securityResult.classList.remove('ok', 'warn', 'error');
  }

  function syncSecurityEnabledFields() {
    if (!securityForm || !securityEnabled) return;
    securityForm.classList.toggle('security-disabled', !securityEnabled.checked);
  }

  function applyAuthStatus(data = {}) {
    authState = {
      enabled: Boolean(data.enabled),
      requested_enabled: Boolean(data.requested_enabled),
      configured: Boolean(data.configured),
      authenticated: data.authenticated !== false,
      username: data.username || 'admin',
      env_path: data.env_path || '',
      session_days: data.session_days || 7,
    };

    const shouldLock = authState.enabled && !authState.authenticated;
    setAuthLocked(shouldLock);
    if (loginUsername && authState.username && !loginUsername.value) loginUsername.value = authState.username;

    if (securityEnabled) securityEnabled.checked = Boolean(authState.enabled || authState.requested_enabled);
    if (securityUsername) securityUsername.value = authState.username || 'admin';
    if (securityPassword) securityPassword.value = '';
    if (securityEnvPath) {
      securityEnvPath.textContent = authState.env_path || '—';
      securityEnvPath.title = authState.env_path || '';
    }
    if (securitySession) {
      securitySession.textContent = authState.enabled
        ? `${authState.session_days || 7} days`
        : 'not required';
    }
    if (securityLogoutBtn) {
      securityLogoutBtn.disabled = !(authState.enabled && authState.authenticated);
    }

    if (securityStatusTitle) {
      if (authState.enabled) {
        securityStatusTitle.textContent = `Enabled · ${authState.username}`;
        setSecurityPill(authState.authenticated ? 'active' : 'login', authState.authenticated ? 'ok' : 'warn');
      } else if (authState.requested_enabled && !authState.configured) {
        securityStatusTitle.textContent = 'Password required';
        setSecurityPill('needs password', 'warn');
      } else {
        securityStatusTitle.textContent = 'Disabled';
        setSecurityPill('off');
      }
    }
    syncSecurityEnabledFields();
    renderSettingsInfo();
  }

  async function loadAuthStatus() {
    try {
      const resp = await fetch('/api/auth/status');
      const data = await resp.json();
      if (!resp.ok) throw data;
      applyAuthStatus(data);
      return data;
    } catch (e) {
      console.error(e);
      applyAuthStatus({ enabled: false, authenticated: true, username: 'admin' });
      return authState;
    }
  }

  async function submitLogin(event) {
    event.preventDefault();
    setLoginStatus('');
    if (loginSubmit) loginSubmit.disabled = true;
    try {
      const resp = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: loginUsername?.value || '',
          password: loginPassword?.value || '',
        }),
      });
      const data = await resp.json();
      if (!resp.ok) throw data;
      applyAuthStatus(data);
      if (loginPassword) loginPassword.value = '';
      await initProtectedData();
      setComposerStatus('Logged in', 'ok');
    } catch (e) {
      console.error(e);
      setLoginStatus(setupErrorMessage(e));
    } finally {
      if (loginSubmit) loginSubmit.disabled = false;
    }
  }

  async function saveSecurity(event) {
    event.preventDefault();
    if (!securityForm) return;
    clearSecurityResult();
    if (securitySaveBtn) securitySaveBtn.disabled = true;
    const body = {
      enabled: Boolean(securityEnabled?.checked),
      username: (securityUsername?.value || 'admin').trim(),
      password: securityPassword?.value || '',
    };
    if (body.enabled && !authState.configured && !body.password.trim()) {
      renderSecurityResult('Password required', ['Set a password the first time you enable local login.'], 'warn');
      if (securitySaveBtn) securitySaveBtn.disabled = false;
      return;
    }
    try {
      const resp = await fetch('/api/security/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await resp.json();
      if (!resp.ok) throw data;
      applyAuthStatus(data);
      renderSecurityResult(
        data.enabled ? 'Local login enabled' : 'Local login disabled',
        data.enabled
          ? ['Saved username and password hash to .env.', 'This browser is logged in now.']
          : ['Saved the disabled state to .env.'],
        'ok',
      );
      setComposerStatus(data.enabled ? 'Local login enabled' : 'Local login disabled', 'ok');
    } catch (e) {
      console.error(e);
      renderSecurityResult('Security save failed', [setupErrorMessage(e)], 'error');
      setComposerStatus(setupErrorMessage(e), 'error', true);
    } finally {
      if (securitySaveBtn) securitySaveBtn.disabled = false;
    }
  }

  async function logoutAuth() {
    if (securityLogoutBtn) securityLogoutBtn.disabled = true;
    try {
      const resp = await fetch('/api/auth/logout', { method: 'POST' });
      const data = await resp.json();
      if (!resp.ok) throw data;
      applyAuthStatus({ ...data, authenticated: false });
      renderSecurityResult('Logged out', ['Refresh or log in again to continue.'], 'ok');
    } catch (e) {
      console.error(e);
      renderSecurityResult('Logout failed', [setupErrorMessage(e)], 'error');
    } finally {
      if (securityLogoutBtn) securityLogoutBtn.disabled = false;
    }
  }

  // ---------- Local long-term memory ----------
  function memoryKindLabel(kind) {
    const labels = {
      note: 'note',
      user_profile: 'profile',
      project: 'project',
      agent: 'agent',
      task: 'task',
    };
    return labels[kind] || kind || 'note';
  }

  function memoryRoleLabel(role) {
    const labels = {
      '': 'global',
      global: 'global',
      hermes: 'Hermes',
      hephaestus: 'Hephaestus',
      athena: 'Athena',
      apollo: 'Apollo',
      chronos: 'Chronos',
    };
    return labels[role || ''] || role || 'global';
  }

  function formatMemoryTime(value) {
    const ts = Number(value || 0);
    if (!ts) return 'never';
    return new Date(ts * 1000).toLocaleString([], {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  function setMemoryPill(text, tone = '') {
    if (!memoryStatusPill) return;
    memoryStatusPill.textContent = text;
    memoryStatusPill.classList.remove('ok', 'warn', 'error');
    if (tone) memoryStatusPill.classList.add(tone);
  }

  function setMemoryBusy(isBusy) {
    if (memorySaveBtn) memorySaveBtn.disabled = isBusy;
    if (memoryRefreshBtn) memoryRefreshBtn.disabled = isBusy;
    if (memoryClearBtn) memoryClearBtn.disabled = isBusy;
  }

  function applyMemoryPayload(payload = {}) {
    const stats = payload.stats || {};
    const settings = payload.settings || stats;
    latestMemoryStats = stats;
    memoryItems = Array.isArray(payload.items) ? payload.items : memoryItems;
    memorySuggestions = Array.isArray(payload.suggestions) ? payload.suggestions : memorySuggestions;

    if (memoryEnabled) memoryEnabled.checked = settings.enabled !== false;
    if (memoryAutoCapture) memoryAutoCapture.checked = Boolean(settings.auto_capture);
    if (memoryPath) {
      memoryPath.textContent = stats.db_path || '—';
      memoryPath.title = stats.db_path || '';
    }
    if (memoryCount) memoryCount.textContent = String(stats.count ?? memoryItems.length ?? 0);
    if (memoryStatus) memoryStatus.classList.toggle('disabled', settings.enabled === false);
    if (memoryStatusTitle) {
      const count = stats.count ?? memoryItems.length ?? 0;
      const suggestions = stats.pending_suggestions ?? memorySuggestions.length ?? 0;
      memoryStatusTitle.textContent = settings.enabled === false
        ? `Disabled · ${count} saved · ${suggestions} suggested`
        : `Enabled · ${count} saved · ${suggestions} suggested`;
    }
    if (settings.enabled === false) setMemoryPill('off', 'warn');
    else if (settings.auto_capture) setMemoryPill('auto', 'ok');
    else setMemoryPill('manual', 'ok');
    if (memorySuggestionCount) {
      memorySuggestionCount.textContent = String(stats.pending_suggestions ?? memorySuggestions.length ?? 0);
    }
    renderMemorySuggestions();
    renderMemoryItems();
  }

  function renderMemorySuggestions() {
    if (!memorySuggestionList) return;
    if (!memorySuggestions.length) {
      memorySuggestionList.innerHTML = `
        <div class="memory-empty">
          No suggestions yet. Pantheon will suggest stable project facts or preferences here before saving them.
        </div>
      `;
      return;
    }
    memorySuggestionList.innerHTML = memorySuggestions.map((item) => `
      <article class="memory-item memory-suggestion" data-memory-suggestion-id="${escapeHtml(item.id)}">
        <div class="memory-item-head">
          <div class="memory-item-title">
            <span class="memory-kind suggested">${escapeHtml(memoryKindLabel(item.kind))}</span>
            <span class="memory-role">${escapeHtml(memoryRoleLabel(item.role))}</span>
          </div>
          <div class="memory-item-actions">
            <button class="ghost-btn memory-delete" type="button" data-memory-ignore="${escapeHtml(item.id)}">Ignore</button>
            <button class="primary-btn memory-delete" type="button" data-memory-accept="${escapeHtml(item.id)}">Save</button>
          </div>
        </div>
        <div class="memory-item-content">${escapeHtml(item.content)}</div>
        <div class="memory-item-meta">
          <span>${escapeHtml(item.reason || 'suggested')}</span>
          <span>source ${escapeHtml(item.source || 'suggested')}</span>
          <span>created ${formatMemoryTime(item.created_at)}</span>
        </div>
      </article>
    `).join('');
  }

  function renderMemoryItems() {
    if (!memoryList) return;
    if (!memoryItems.length) {
      memoryList.innerHTML = `
        <div class="memory-empty">
          No memories yet. Save a note here, or type <strong>/remember</strong> followed by something Pantheon should keep.
        </div>
      `;
      return;
    }
    memoryList.innerHTML = memoryItems.map((item) => {
      const meta = [
        item.source ? `source ${item.source}` : '',
        `role ${memoryRoleLabel(item.role)}`,
        item.usage_count ? `used ${item.usage_count}x` : 'not used yet',
        `updated ${formatMemoryTime(item.updated_at)}`,
      ].filter(Boolean);
      return `
        <article class="memory-item" data-memory-id="${escapeHtml(item.id)}">
          <div class="memory-item-head">
            <div class="memory-item-title">
              <span class="memory-kind">${escapeHtml(memoryKindLabel(item.kind))}</span>
              <span class="memory-role">${escapeHtml(memoryRoleLabel(item.role))}</span>
              <span class="memory-id">${escapeHtml(item.id)}</span>
            </div>
            <button class="ghost-btn memory-delete" type="button" data-memory-delete="${escapeHtml(item.id)}">Delete</button>
          </div>
          <div class="memory-item-content">${escapeHtml(item.content)}</div>
          <div class="memory-item-meta">
            ${meta.map((line) => `<span>${escapeHtml(line)}</span>`).join('')}
          </div>
        </article>
      `;
    }).join('');
  }

  async function loadMemory(query = null) {
    if (!memoryForm) return;
    const q = query == null ? (memorySearch?.value || '') : query;
    setMemoryPill('checking');
    try {
      const resp = await fetch(`/api/memory?query=${encodeURIComponent(q.trim())}`);
      const data = await resp.json();
      if (!resp.ok) throw data;
      applyMemoryPayload(data);
    } catch (e) {
      console.error(e);
      if (memoryStatusTitle) memoryStatusTitle.textContent = 'Memory unavailable';
      setMemoryPill('error', 'error');
      if (memoryList) {
        memoryList.innerHTML = `<div class="memory-empty">${escapeHtml(setupErrorMessage(e))}</div>`;
      }
    }
  }

  async function saveMemory(event = null) {
    if (event) event.preventDefault();
    const content = (memoryContent?.value || '').trim();
    if (!content) {
      setComposerStatus('Write a memory first', 'warn');
      memoryContent?.focus();
      return;
    }
    setMemoryBusy(true);
    setMemoryPill('saving');
    try {
      const resp = await fetch('/api/memory', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content,
          kind: memoryKind?.value || 'note',
          role: memoryRole?.value || '',
          source: 'manual',
        }),
      });
      const data = await resp.json();
      if (!resp.ok) throw data;
      if (memoryContent) memoryContent.value = '';
      applyMemoryPayload(data);
      setComposerStatus('Memory saved', 'ok');
    } catch (e) {
      console.error(e);
      setMemoryPill('error', 'error');
      setComposerStatus(setupErrorMessage(e), 'error', true);
    } finally {
      setMemoryBusy(false);
    }
  }

  async function saveMemorySettings() {
    if (!memoryForm) return;
    setMemoryPill('saving');
    try {
      const resp = await fetch('/api/memory/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          enabled: Boolean(memoryEnabled?.checked),
          auto_capture: Boolean(memoryAutoCapture?.checked),
        }),
      });
      const data = await resp.json();
      if (!resp.ok) throw data;
      applyMemoryPayload(data);
      setComposerStatus('Memory settings saved', 'ok');
    } catch (e) {
      console.error(e);
      setMemoryPill('error', 'error');
      setComposerStatus(setupErrorMessage(e), 'error', true);
    }
  }

  async function deleteMemory(memoryId) {
    if (!memoryId) return;
    setMemoryPill('deleting');
    try {
      const resp = await fetch(`/api/memory/${encodeURIComponent(memoryId)}`, { method: 'DELETE' });
      const data = await resp.json();
      if (!resp.ok) throw data;
      applyMemoryPayload(data);
      setComposerStatus('Memory deleted', 'ok');
    } catch (e) {
      console.error(e);
      setMemoryPill('error', 'error');
      setComposerStatus(setupErrorMessage(e), 'error', true);
    }
  }

  async function acceptMemorySuggestion(suggestionId) {
    if (!suggestionId) return;
    setMemoryPill('saving');
    try {
      const resp = await fetch(`/api/memory/suggestions/${encodeURIComponent(suggestionId)}/accept`, { method: 'POST' });
      const data = await resp.json();
      if (!resp.ok) throw data;
      applyMemoryPayload(data);
      setComposerStatus('Suggested memory saved', 'ok');
    } catch (e) {
      console.error(e);
      setMemoryPill('error', 'error');
      setComposerStatus(setupErrorMessage(e), 'error', true);
    }
  }

  async function ignoreMemorySuggestion(suggestionId) {
    if (!suggestionId) return;
    setMemoryPill('ignoring');
    try {
      const resp = await fetch(`/api/memory/suggestions/${encodeURIComponent(suggestionId)}/ignore`, { method: 'POST' });
      const data = await resp.json();
      if (!resp.ok) throw data;
      applyMemoryPayload(data);
      setComposerStatus('Memory suggestion ignored', 'ok');
    } catch (e) {
      console.error(e);
      setMemoryPill('error', 'error');
      setComposerStatus(setupErrorMessage(e), 'error', true);
    }
  }

  async function clearMemory() {
    if (!memoryItems.length && !latestMemoryStats?.count) return;
    if (!window.confirm('Clear all saved memories?')) return;
    setMemoryBusy(true);
    setMemoryPill('clearing');
    try {
      const resp = await fetch('/api/memory', { method: 'DELETE' });
      const data = await resp.json();
      if (!resp.ok) throw data;
      applyMemoryPayload(data);
      setComposerStatus('All memories cleared', 'ok');
    } catch (e) {
      console.error(e);
      setMemoryPill('error', 'error');
      setComposerStatus(setupErrorMessage(e), 'error', true);
    } finally {
      setMemoryBusy(false);
    }
  }

  async function rememberFromCommand(content) {
    const clean = String(content || '').trim();
    if (!clean) {
      openSettingsPane('memory');
      memoryContent?.focus();
      return true;
    }
    if (memoryContent) memoryContent.value = clean;
    if (memoryKind) memoryKind.value = 'note';
    if (memoryRole) memoryRole.value = '';
    await saveMemory();
    return true;
  }

  async function showMemoriesFromCommand(query) {
    openSettingsPane('memory');
    if (memorySearch) memorySearch.value = String(query || '').trim();
    await loadMemory(memorySearch?.value || '');
    return true;
  }

  async function forgetFromCommand(memoryId) {
    const id = String(memoryId || '').trim();
    if (!id) {
      openSettingsPane('memory');
      setComposerStatus('Copy a memory id, then use /forget <id>', 'warn', true);
      return true;
    }
    await deleteMemory(id);
    return true;
  }

  // ---------- Integrations ----------
  function integrationSectionTitle(section) {
    const labels = {
      mcp: 'MCP Servers',
      plugins: 'Plugins',
      skills: 'Skills',
      channels: 'Channels',
    };
    return labels[section] || section || 'Integrations';
  }

  function integrationSectionHint(section) {
    const hints = {
      mcp: 'External tools and data sources that agents can call.',
      plugins: 'Capability packs that bundle tools, skills, commands, or UI behavior.',
      skills: 'Reusable working methods that tell gods how to handle specific tasks.',
      channels: 'Places where users can send tasks into Pantheon.',
    };
    return hints[section] || '';
  }

  function integrationStatusLabel(status) {
    const labels = {
      ready: 'ready',
      planned: 'planned',
      disabled: 'off',
      error: 'error',
    };
    return labels[status] || status || 'unknown';
  }

  function integrationRoleLabel(role) {
    const meta = metaFor(role);
    return meta?.label || role;
  }

  function setIntegrationsPill(text, tone = '') {
    if (!integrationsStatusPill) return;
    integrationsStatusPill.textContent = text;
    integrationsStatusPill.classList.remove('ok', 'warn', 'error');
    if (tone) integrationsStatusPill.classList.add(tone);
  }

  function renderIntegrationNav() {
    if (!integrationNav) return;
    integrationNav.querySelectorAll('[data-integration-section]').forEach((btn) => {
      const section = btn.dataset.integrationSection;
      btn.classList.toggle('active', section === activeIntegrationSection);
      const countEl = btn.querySelector('small');
      const liveItems = integrationData[section]?.items;
      if (Array.isArray(liveItems)) {
        const ready = section === 'channels'
          ? liveItems.filter((item) => item.enabled).length
          : liveItems.filter((item) => item.enabled !== false && (section !== 'mcp' || !item.last_test || item.last_test.ok)).length;
        if (countEl) countEl.textContent = `${ready}/${liveItems.length}`;
        return;
      }
      const runtime = latestIntegrations?.runtime || {};
      const runtimeStats = {
        mcp: [runtime.mcp_ready, runtime.mcp_servers],
        plugins: [runtime.plugins_enabled, runtime.plugins],
        skills: [runtime.skills_enabled, runtime.skills],
      };
      if (runtimeStats[section]) {
        const [ready, total] = runtimeStats[section];
        if (countEl) countEl.textContent = `${Number(ready || 0)}/${Number(total || 0)}`;
        return;
      }
      const stats = latestIntegrations?.summary?.[section] || {};
      if (countEl) countEl.textContent = `${stats.ready || 0}/${stats.total || 0}`;
    });
  }

  function integrationRoleOptions(selected = []) {
    const roles = ['global', 'hermes', 'hephaestus', 'athena', 'apollo', 'chronos'];
    return roles.map((role) => `
      <label class="integration-role-option">
        <input type="checkbox" data-extension-role value="${role}" ${selected.includes(role) ? 'checked' : ''} />
        <span>${escapeHtml(integrationRoleLabel(role))}</span>
      </label>
    `).join('');
  }

  function integrationFetch(url, options = {}) {
    return fetch(url, options).then(async (resp) => {
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) throw data;
      return data;
    });
  }

  function renderPromptExtensionSection(kind) {
    const data = integrationData[kind] || { items: [] };
    const items = data.items || [];
    const label = kind === 'skills' ? 'Skill' : 'Plugin pack';
    const isSkill = kind === 'skills';
    const itemMarkup = items.length ? items.map((item) => {
      const enabled = item.enabled !== false;
      const roles = Array.isArray(item.roles) ? item.roles : [];
      const source = item.builtin ? 'built-in' : (item.source || 'local');
      const triggerTerms = Array.isArray(item.trigger_terms) ? item.trigger_terms : [];
      const actions = [
        isSkill && enabled
          ? `<button class="ws-copy-btn primary" type="button" data-skill-use="${escapeHtml(item.id)}">Use</button>`
          : '',
        `<button class="ws-copy-btn" type="button" data-extension-toggle="${escapeHtml(kind)}" data-extension-id="${escapeHtml(item.id)}" data-extension-enabled="${enabled ? 'false' : 'true'}">${enabled ? 'Disable' : 'Enable'}</button>`,
        item.editable !== false
          ? `<button class="ws-copy-btn" type="button" data-extension-edit="${escapeHtml(kind)}" data-extension-id="${escapeHtml(item.id)}">Edit</button>`
          : '',
        item.editable !== false
          ? `<button class="ws-copy-btn danger" type="button" data-extension-delete="${escapeHtml(kind)}" data-extension-id="${escapeHtml(item.id)}">Delete</button>`
          : '',
      ].filter(Boolean).join('');
      return `
        <article class="integration-item integration-live ${enabled ? '' : 'integration-disabled'}">
          <div class="integration-item-head">
            <div class="integration-item-title">
              <strong>${escapeHtml(item.name || item.id || label)}</strong>
              <span>${isSkill ? '$' : ''}${escapeHtml(item.id || '')} · v${escapeHtml(item.version || '1.0.0')} · ${escapeHtml(source)}</span>
            </div>
            <span class="setup-pill integration-pill ${enabled ? 'ok' : 'warn'}">${enabled ? 'active' : 'off'}</span>
          </div>
          <p>${escapeHtml(item.description || '')}</p>
          <div class="integration-tags">
            ${roles.map((role) => `<span>${escapeHtml(integrationRoleLabel(role))}</span>`).join('')}
            ${isSkill ? `<span>${escapeHtml(item.kind || 'role')}</span><span>${item.allow_implicit_invocation === false ? 'explicit only' : 'auto match'}</span>` : ''}
          </div>
          ${isSkill && triggerTerms.length ? `<div class="integration-triggers"><span>Triggers</span>${triggerTerms.slice(0, 6).map((term) => `<code>${escapeHtml(term)}</code>`).join('')}</div>` : ''}
          <details class="integration-instructions"><summary>View instructions</summary><pre>${escapeHtml(item.instructions || '')}</pre></details>
          <div class="integration-editor-actions">${actions}</div>
        </article>
      `;
    }).join('') : '<div class="memory-empty">Create your first local extension to change agent behavior.</div>';
    integrationList.innerHTML = `
      <div class="integration-section-head integration-action-head">
        <div>
          <span class="setup-kicker">${escapeHtml(label)} manager</span>
          <strong>${escapeHtml(integrationSectionHint(kind))}</strong>
        </div>
        <button class="ws-copy-btn" type="button" data-extension-new="${kind}">New ${escapeHtml(label)}</button>
      </div>
      <form class="integration-editor" data-extension-editor data-extension-kind="${kind}" hidden>
        <div class="integration-editor-head">
          <strong data-extension-editor-title>Create ${escapeHtml(label)}</strong>
          <button class="modal-close" type="button" data-extension-cancel>×</button>
        </div>
        <input type="hidden" data-extension-id />
        <label>Name<input class="setting-input" data-extension-name required maxlength="100" placeholder="e.g. Frontend review" /></label>
        <label>Description<input class="setting-input" data-extension-description maxlength="500" placeholder="What this extension helps with" /></label>
        <label>Instructions<textarea class="setting-input memory-textarea" data-extension-instructions required rows="5" placeholder="Tell the selected gods how to work..." ></textarea></label>
        ${isSkill ? `
          <label>Trigger phrases<input class="setting-input" data-extension-triggers placeholder="bug fix, review code, 修复问题" /></label>
          <label>Workflow type
            <select class="setting-input" data-extension-kind>
              <option value="role">Role</option>
              <option value="shared">Shared</option>
              <option value="council">Council</option>
            </select>
          </label>
          <label class="integration-check"><input type="checkbox" data-extension-implicit checked /> Allow automatic matching</label>
          <p class="settings-hint">Pantheon stores this as a portable SKILL.md folder. Disable automatic matching to require an explicit /skill command.</p>
        ` : ''}
        <div class="integration-role-grid"><span class="settings-h4">Apply to</span>${integrationRoleOptions(['global'])}</div>
        <div class="integration-editor-actions">
          <button class="ws-copy-btn" type="submit">Save ${escapeHtml(label)}</button>
          <button class="ws-copy-btn" type="button" data-extension-cancel>Cancel</button>
        </div>
      </form>
      ${itemMarkup}
    `;
  }

  const MCP_ROLES = [
    { id: 'hephaestus', label: 'Hephaestus' },
    { id: 'athena', label: 'Athena' },
    { id: 'apollo', label: 'Apollo' },
    { id: 'chronos', label: 'Chronos' },
  ];

  const MCP_PRESETS = {
    github: {
      name: 'GitHub',
      transport: 'streamable_http',
      url: 'https://api.githubcopilot.com/mcp/',
      credentialEnv: 'GITHUB_PERSONAL_ACCESS_TOKEN',
      bearerEnv: 'GITHUB_PERSONAL_ACCESS_TOKEN',
      roles: ['hephaestus', 'athena'],
    },
    context7: {
      name: 'Context7',
      transport: 'stdio',
      command: 'npx',
      args: ['-y', '@upstash/context7-mcp'],
      credentialEnv: 'CONTEXT7_API_KEY',
      roles: ['athena', 'hephaestus'],
    },
    figma: {
      name: 'Figma Desktop',
      transport: 'streamable_http',
      url: 'http://127.0.0.1:3845/mcp',
      roles: ['apollo', 'hephaestus'],
    },
    custom: {
      name: '',
      transport: 'stdio',
      roles: MCP_ROLES.map((role) => role.id),
    },
  };

  function mcpRoleOptions(selected = [], attribute = 'data-mcp-server-role') {
    return MCP_ROLES.map((role) => `
      <label class="integration-role-option">
        <input type="checkbox" ${attribute} value="${role.id}" ${selected.includes(role.id) ? 'checked' : ''} />
        <span>${role.label}</span>
      </label>
    `).join('');
  }

  function mcpMappingText(mapping = {}) {
    return Object.entries(mapping || {}).map(([key, value]) => `${key}=${value}`).join('\n');
  }

  function parseMcpMapping(value = '') {
    const mapping = {};
    String(value).split('\n').forEach((rawLine) => {
      const line = rawLine.trim();
      if (!line || line.startsWith('#')) return;
      const separator = line.indexOf('=');
      if (separator <= 0) return;
      const key = line.slice(0, separator).trim();
      const source = line.slice(separator + 1).trim();
      if (key && source) mapping[key] = source;
    });
    return mapping;
  }

  function mcpToolPolicy(server, tool) {
    const stored = server.tool_policies?.[tool.name];
    if (stored) return stored;
    return {
      enabled: true,
      roles: server.roles || MCP_ROLES.map((role) => role.id),
      approval: tool.annotations?.read_only === true ? 'auto' : 'ask',
    };
  }

  function mcpRiskLabel(tool) {
    if (tool.risk === 'read') return 'read only';
    if (tool.risk === 'write') return 'writes data';
    if (tool.risk === 'destructive') return 'destructive';
    return 'unknown risk';
  }

  function mcpToolMarkup(server, tool) {
    const policy = mcpToolPolicy(server, tool);
    const roles = Array.isArray(policy.roles) ? policy.roles : [];
    const key = `${server.id}:${tool.name}`;
    const schema = JSON.stringify(tool.input_schema || {}, null, 2);
    return `
      <section class="mcp-tool-item ${policy.enabled === false ? 'is-disabled' : ''}"
               data-mcp-tool-policy data-mcp-server-id="${escapeHtml(server.id)}"
               data-mcp-tool-name="${escapeHtml(tool.name)}">
        <div class="mcp-tool-head">
          <div class="mcp-tool-identity">
            <code>${escapeHtml(tool.name)}</code>
            <strong>${escapeHtml(tool.title || tool.name)}</strong>
          </div>
          <span class="mcp-risk ${escapeHtml(tool.risk || 'unknown')}">${mcpRiskLabel(tool)}</span>
        </div>
        ${tool.description ? `<p class="mcp-tool-description">${escapeHtml(tool.description)}</p>` : ''}
        <div class="mcp-tool-policy-grid">
          <label class="integration-check mcp-tool-enabled"><input type="checkbox" data-mcp-policy-enabled ${policy.enabled !== false ? 'checked' : ''} /> Tool enabled</label>
          <label>Approval
            <select class="setting-input" data-mcp-policy-approval>
              <option value="auto" ${policy.approval === 'auto' ? 'selected' : ''}>Run automatically</option>
              <option value="ask" ${policy.approval !== 'auto' ? 'selected' : ''}>Ask every time</option>
            </select>
          </label>
        </div>
        <div class="integration-role-grid mcp-tool-roles">
          <span class="settings-h4">Available to</span>
          ${mcpRoleOptions(roles, 'data-mcp-policy-role')}
        </div>
        <div class="integration-editor-actions">
          <button class="ws-copy-btn primary" type="button" data-mcp-policy-save>Save access</button>
        </div>
        <details class="mcp-tool-call">
          <summary>Schema and manual diagnostic</summary>
          <pre class="mcp-schema">${escapeHtml(schema)}</pre>
          <textarea class="setting-input" rows="2" data-mcp-call-args="${escapeHtml(key)}" placeholder='{"key":"value"}'>{}</textarea>
          <button class="ws-copy-btn" type="button" data-mcp-call="${escapeHtml(server.id)}" data-mcp-tool="${escapeHtml(tool.name)}">Run diagnostic</button>
          <pre class="mcp-call-result" data-mcp-result="${escapeHtml(key)}"></pre>
        </details>
      </section>
    `;
  }

  function renderMcpSection() {
    const data = integrationData.mcp || { items: [], available: false };
    const servers = data.items || [];
    const connectedCount = servers.filter((server) => server.last_test?.ok).length;
    const errorCount = servers.filter((server) => server.last_test?.error).length;
    const toolCount = servers.reduce((total, server) => total + (server.tools || []).length, 0);
    const serverMarkup = servers.length ? servers.map((server) => {
      const test = server.last_test || {};
      const status = server.enabled === false ? 'disabled' : test.ok ? 'connected' : test.error ? 'error' : 'untested';
      const tools = server.tools || [];
      const credentialNames = server.credential_env_vars || [];
      const credentialState = credentialNames.length
        ? `${server.credentials_ready ? 'credential ready' : 'credential missing'} · ${credentialNames.join(', ')}`
        : 'no credential configured';
      const endpoint = server.command
        ? `${server.command} ${(server.args || []).join(' ')}`
        : server.url || 'MCP endpoint';
      const instructions = server.server_metadata?.instructions || '';
      return `
        <article class="integration-item integration-live mcp-server-card ${status === 'error' ? 'integration-error' : ''}">
          <div class="integration-item-head">
            <div class="integration-item-title">
              <strong>${escapeHtml(server.name || server.id)}</strong>
              <span>${escapeHtml(server.id || '')} · ${escapeHtml(server.transport || 'stdio')} · ${tools.length} tools</span>
            </div>
            <span class="setup-pill integration-pill ${status === 'connected' ? 'ok' : status === 'error' ? 'error' : 'warn'}">${status}</span>
          </div>
          <p class="mcp-endpoint" title="${escapeHtml(endpoint)}">${escapeHtml(endpoint)}</p>
          <div class="mcp-server-meta">
            <span class="${server.credentials_ready === false ? 'warn' : ''}">${escapeHtml(credentialState)}</span>
            <span>${server.allow_agent_calls ? 'agent access on' : 'manual diagnostics only'}</span>
          </div>
          ${test.error ? `<div class="integration-error-text">${escapeHtml(test.error)}</div>` : ''}
          ${instructions ? `<details class="integration-instructions"><summary>Server instructions</summary><pre>${escapeHtml(instructions)}</pre></details>` : ''}
          <div class="integration-editor-actions mcp-server-actions">
            <button class="ws-copy-btn primary" type="button" data-mcp-test="${escapeHtml(server.id)}">Test connection</button>
            <button class="ws-copy-btn" type="button" data-mcp-edit="${escapeHtml(server.id)}">Edit</button>
            <button class="ws-copy-btn danger" type="button" data-mcp-delete="${escapeHtml(server.id)}">Delete</button>
          </div>
          <label class="integration-check mcp-agent-master"><input type="checkbox" data-mcp-agent-toggle="${escapeHtml(server.id)}" ${server.allow_agent_calls ? 'checked' : ''} /> Let agents use approved tools</label>
          <div class="mcp-tool-list">
            ${tools.length ? tools.map((tool) => mcpToolMarkup(server, tool)).join('') : '<div class="memory-empty">Test the connection to discover this server\'s tools.</div>'}
          </div>
        </article>
      `;
    }).join('') : '<div class="memory-empty">Add an MCP server, test it, then choose which gods can use each discovered tool.</div>';
    integrationList.innerHTML = `
      <div class="integration-section-head integration-action-head">
        <div>
          <span class="setup-kicker">MCP server manager</span>
          <strong>Connect external tools and give each god only the access it needs.</strong>
        </div>
        <button class="ws-copy-btn primary" type="button" data-mcp-new>New server</button>
      </div>
      <div class="mcp-summary" aria-label="MCP status summary">
        <span><strong>${servers.length}</strong> servers</span>
        <span><strong>${connectedCount}</strong> connected</span>
        <span><strong>${toolCount}</strong> tools</span>
        ${errorCount ? `<span class="error"><strong>${errorCount}</strong> errors</span>` : ''}
      </div>
      ${!data.available ? '<div class="integration-warning">MCP SDK is not installed. Install the project MCP dependency, then restart Pantheon.</div>' : ''}
      <form class="integration-editor mcp-editor" data-mcp-editor hidden>
        <div class="integration-editor-head"><strong data-mcp-editor-title>Connect MCP server</strong><button class="modal-close" type="button" data-mcp-cancel>×</button></div>
        <input type="hidden" data-mcp-id />
        <div class="mcp-preset-grid">
          <button type="button" data-mcp-preset="github"><strong>GitHub</strong><span>Repository tools</span></button>
          <button type="button" data-mcp-preset="context7"><strong>Context7</strong><span>Current code docs</span></button>
          <button type="button" data-mcp-preset="figma"><strong>Figma Desktop</strong><span>Local design tools</span></button>
          <button type="button" data-mcp-preset="custom"><strong>Custom</strong><span>stdio or HTTP</span></button>
        </div>
        <div class="mcp-editor-grid">
          <label>Name<input class="setting-input" data-mcp-name required maxlength="100" placeholder="e.g. GitHub" /></label>
          <label>Transport<select class="setting-input" data-mcp-transport><option value="stdio">Local command (stdio)</option><option value="streamable_http">Remote or local HTTP</option></select></label>
        </div>
        <div class="mcp-editor-fields" data-mcp-stdio-fields>
          <label>Command<input class="setting-input" data-mcp-command placeholder="npx" /></label>
          <label>Arguments<textarea class="setting-input memory-textarea" data-mcp-args rows="3" placeholder="One argument per line"></textarea></label>
          <label>Working directory<input class="setting-input" data-mcp-cwd placeholder="Optional local path" /></label>
        </div>
        <div class="mcp-editor-fields" data-mcp-http-fields hidden>
          <label>HTTP URL<input class="setting-input" data-mcp-url placeholder="https://example.com/mcp" /></label>
        </div>
        <div class="mcp-credential-fields">
          <label>Credential environment variable<input class="setting-input" data-mcp-credential-env placeholder="e.g. GITHUB_PERSONAL_ACCESS_TOKEN" /></label>
          <label>Credential value<input class="setting-input" data-mcp-credential-value type="password" autocomplete="new-password" placeholder="Saved to .env; leave blank to keep current value" /></label>
        </div>
        <div class="integration-role-grid">
          <span class="settings-h4">Default gods</span>
          ${mcpRoleOptions(MCP_ROLES.map((role) => role.id))}
        </div>
        <details class="mcp-advanced">
          <summary>Advanced connection settings</summary>
          <div class="mcp-advanced-fields">
            <label>Process environment mapping<textarea class="setting-input" data-mcp-env rows="3" placeholder="CHILD_VARIABLE=LOCAL_ENV_VARIABLE"></textarea></label>
            <label>HTTP header mapping<textarea class="setting-input" data-mcp-headers-env rows="3" placeholder="X-API-Key=LOCAL_ENV_VARIABLE"></textarea></label>
            <label>Bearer token environment variable<input class="setting-input" data-mcp-bearer-env placeholder="Optional for HTTP" /></label>
            <div class="mcp-editor-grid">
              <label>Startup timeout (seconds)<input class="setting-input" data-mcp-startup-timeout type="number" min="1" max="120" value="15" /></label>
              <label>Tool timeout (seconds)<input class="setting-input" data-mcp-tool-timeout type="number" min="1" max="600" value="60" /></label>
            </div>
          </div>
        </details>
        <div class="mcp-server-switches">
          <label class="integration-check"><input type="checkbox" data-mcp-enabled checked /> Enable server</label>
          <label class="integration-check"><input type="checkbox" data-mcp-agent-calls /> Let agents use approved tools</label>
        </div>
        <p class="settings-hint">Save, test the connection, then review each discovered tool. Secrets are stored in the local .env file, not in the MCP registry.</p>
        <div class="integration-editor-actions"><button class="ws-copy-btn primary" type="submit">Save server</button><button class="ws-copy-btn" type="button" data-mcp-cancel>Cancel</button></div>
      </form>
      ${serverMarkup}
    `;
  }

  function renderChannelsSection() {
    const channel = integrationData.channels?.items?.[0] || { enabled: false, token_configured: false };
    integrationList.innerHTML = `
      <div class="integration-section-head">
        <div><span class="setup-kicker">Incoming channels</span><strong>Send tasks from scripts or services into the same Pantheon Agent runtime.</strong></div>
      </div>
      <article class="integration-item integration-live">
        <div class="integration-item-head"><div class="integration-item-title"><strong>Webhook</strong><span>POST /api/channels/webhook</span></div><span class="setup-pill integration-pill ${channel.enabled ? 'ok' : 'warn'}">${channel.enabled ? 'active' : 'off'}</span></div>
        <p>Token-protected local webhook. It accepts <code>{ task, mode, role }</code> and returns the real agent result.</p>
        <form data-webhook-form>
          <label class="integration-check"><input type="checkbox" data-webhook-enabled ${channel.enabled ? 'checked' : ''} /> Enable webhook</label>
          <label>Token<input class="setting-input" data-webhook-token type="password" value="${escapeHtml(channel.revealed_token || '')}" placeholder="${channel.token_configured ? 'Token configured; leave blank to keep it' : 'Generate a secure token'}" /></label>
          <label class="integration-check"><input type="checkbox" data-webhook-rotate /> Generate a new token</label>
          <div class="integration-editor-actions"><button class="ws-copy-btn" type="submit">Save channel</button><button class="ws-copy-btn" type="button" data-webhook-copy-endpoint>Copy endpoint</button><button class="ws-copy-btn" type="button" data-webhook-copy-token>Copy token</button></div>
        </form>
        <pre class="integration-code">POST ${escapeHtml(channel.endpoint || '/api/channels/webhook')}\nAuthorization: Bearer &lt;token&gt;\nContent-Type: application/json\n\n{"task":"Ask Athena to compare SQLite and Postgres","mode":"auto"}</pre>
        <p class="settings-hint">For a remote IM platform, Pantheon must be reachable through a public HTTPS callback. Localhost alone cannot receive messages from that platform.</p>
      </article>
    `;
  }

  function renderIntegrationItems() {
    if (!integrationList) return;
    if (activeIntegrationSection === 'skills' || activeIntegrationSection === 'plugins') {
      renderPromptExtensionSection(activeIntegrationSection);
      return;
    }
    if (activeIntegrationSection === 'mcp' && integrationData.mcp) {
      renderMcpSection();
      return;
    }
    if (activeIntegrationSection === 'channels' && integrationData.channels) {
      renderChannelsSection();
      return;
    }
    const items = latestIntegrations?.sections?.[activeIntegrationSection] || [];
    integrationList.innerHTML = `<div class="integration-section-head"><div><span class="setup-kicker">${escapeHtml(integrationSectionTitle(activeIntegrationSection))}</span><strong>${escapeHtml(integrationSectionHint(activeIntegrationSection))}</strong></div></div>${items.map((item) => `<article class="integration-item"><strong>${escapeHtml(item.name || item.id)}</strong><p>${escapeHtml(item.summary || '')}</p></article>`).join('')}`;
  }

  async function loadIntegrationData(section = activeIntegrationSection) {
    const endpoints = { skills: '/api/skills', plugins: '/api/plugins', mcp: '/api/mcp/servers', channels: '/api/channels' };
    if (!endpoints[section]) return;
    try {
      integrationData[section] = await integrationFetch(endpoints[section]);
      renderIntegrationNav();
      renderIntegrationItems();
    } catch (e) {
      integrationList.innerHTML = `<div class="memory-empty">${escapeHtml(setupErrorMessage(e))}</div>`;
    }
  }

  async function loadSkillCatalog() {
    try {
      integrationData.skills = await integrationFetch('/api/skills');
      renderIntegrationNav();
      updateSlashCommandMenu();
    } catch (error) {
      console.error(error);
    }
  }

  function openExtensionEditor(kind, itemId = '') {
    renderIntegrationItems();
    const form = integrationList?.querySelector(`[data-extension-editor][data-extension-kind="${kind}"]`);
    if (!form) return;
    const item = (integrationData[kind]?.items || []).find((entry) => entry.id === itemId);
    form.hidden = false;
    form.querySelector('[data-extension-id]').value = item?.id || '';
    form.querySelector('[data-extension-editor-title]').textContent = item ? `Edit ${kind === 'skills' ? 'Skill' : 'Plugin pack'}` : `Create ${kind === 'skills' ? 'Skill' : 'Plugin pack'}`;
    form.querySelector('[data-extension-name]').value = item?.name || '';
    form.querySelector('[data-extension-description]').value = item?.description || '';
    form.querySelector('[data-extension-instructions]').value = item?.instructions || '';
    const triggerInput = form.querySelector('[data-extension-triggers]');
    if (triggerInput) triggerInput.value = (item?.trigger_terms || []).join(', ');
    const kindInput = form.querySelector('[data-extension-kind]');
    if (kindInput) kindInput.value = item?.kind || 'role';
    const implicitInput = form.querySelector('[data-extension-implicit]');
    if (implicitInput) implicitInput.checked = item?.allow_implicit_invocation !== false;
    const selected = Array.isArray(item?.roles) ? item.roles : ['global'];
    form.querySelectorAll('[data-extension-role]').forEach((checkbox) => { checkbox.checked = selected.includes(checkbox.value); });
    form.querySelector('[data-extension-name]')?.focus();
  }

  async function savePromptExtension(form) {
    const kind = form.dataset.extensionKind;
    const itemId = form.querySelector('[data-extension-id]').value;
    const roles = [...form.querySelectorAll('[data-extension-role]:checked')].map((el) => el.value);
    const payload = {
      name: form.querySelector('[data-extension-name]').value,
      description: form.querySelector('[data-extension-description]').value,
      instructions: form.querySelector('[data-extension-instructions]').value,
      roles,
      enabled: true,
      version: '1.0.0',
      trigger_terms: (form.querySelector('[data-extension-triggers]')?.value || '')
        .split(/[,\n]/)
        .map((value) => value.trim())
        .filter(Boolean),
      kind: form.querySelector('[data-extension-kind]')?.value || 'role',
      allow_implicit_invocation: form.querySelector('[data-extension-implicit]')?.checked !== false,
    };
    const endpoint = `/api/${kind}${itemId ? `/${encodeURIComponent(itemId)}` : ''}`;
    const data = await integrationFetch(endpoint, {
      method: itemId ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    integrationData[kind] = data;
    renderIntegrationNav();
    renderIntegrationItems();
    if (kind === 'skills') updateSlashCommandMenu();
    setComposerStatus(`${kind === 'skills' ? 'Skill' : 'Plugin pack'} saved`, 'ok');
  }

  async function togglePromptExtension(kind, itemId, enabled) {
    const data = await integrationFetch(`/api/${kind}/${encodeURIComponent(itemId)}/toggle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled }),
    });
    integrationData[kind] = data;
    renderIntegrationNav();
    renderIntegrationItems();
    if (kind === 'skills') updateSlashCommandMenu();
    setComposerStatus(`${kind === 'skills' ? 'Skill' : 'Plugin pack'} ${enabled ? 'enabled' : 'disabled'}`, 'ok');
  }

  async function deletePromptExtension(kind, itemId) {
    if (!window.confirm(`Delete this ${kind === 'skills' ? 'skill' : 'plugin pack'}?`)) return;
    integrationData[kind] = await integrationFetch(`/api/${kind}/${encodeURIComponent(itemId)}`, { method: 'DELETE' });
    renderIntegrationNav();
    renderIntegrationItems();
    if (kind === 'skills') updateSlashCommandMenu();
  }

  function prepareSkillInvocation(itemId) {
    const item = (integrationData.skills?.items || []).find((entry) => entry.id === itemId);
    if (!item || item.enabled === false) {
      setComposerStatus('This skill is not available', 'warn');
      return;
    }
    closeSettings();
    inputEl.value = `/skill ${item.id} `;
    autoResize();
    hideSlashCommandMenu();
    inputEl.focus();
    setComposerStatus(`${item.name} selected; describe the task`, 'ok', true);
  }

  function mcpServerPayload(server = {}, overrides = {}) {
    return {
      name: server.name || '',
      transport: server.transport || 'stdio',
      command: server.command || '',
      args: server.args || [],
      cwd: server.cwd || '',
      url: server.url || '',
      env: server.env || {},
      headers_env: server.headers_env || {},
      bearer_token_env_var: server.bearer_token_env_var || '',
      enabled: server.enabled !== false,
      allow_agent_calls: server.allow_agent_calls === true,
      roles: server.roles || MCP_ROLES.map((role) => role.id),
      tool_policies: server.tool_policies || {},
      startup_timeout_seconds: server.startup_timeout_seconds || 15,
      tool_timeout_seconds: server.tool_timeout_seconds || 60,
      ...overrides,
    };
  }

  function updateMcpEditorTransport(form) {
    const http = form.querySelector('[data-mcp-transport]')?.value === 'streamable_http';
    const stdioFields = form.querySelector('[data-mcp-stdio-fields]');
    const httpFields = form.querySelector('[data-mcp-http-fields]');
    if (stdioFields) stdioFields.hidden = http;
    if (httpFields) httpFields.hidden = !http;
    const command = form.querySelector('[data-mcp-command]');
    const url = form.querySelector('[data-mcp-url]');
    if (command) command.required = !http;
    if (url) url.required = http;
  }

  function setMcpEditorRoles(form, selected = []) {
    form.querySelectorAll('[data-mcp-server-role]').forEach((checkbox) => {
      checkbox.checked = selected.includes(checkbox.value);
    });
  }

  function applyMcpPreset(presetId) {
    const form = integrationList?.querySelector('[data-mcp-editor]:not([hidden])');
    const preset = MCP_PRESETS[presetId];
    if (!form || !preset) return;
    form.querySelector('[data-mcp-name]').value = preset.name || '';
    form.querySelector('[data-mcp-transport]').value = preset.transport || 'stdio';
    form.querySelector('[data-mcp-command]').value = preset.command || '';
    form.querySelector('[data-mcp-args]').value = (preset.args || []).join('\n');
    form.querySelector('[data-mcp-cwd]').value = '';
    form.querySelector('[data-mcp-url]').value = preset.url || '';
    form.querySelector('[data-mcp-credential-env]').value = preset.credentialEnv || '';
    form.querySelector('[data-mcp-credential-value]').value = '';
    form.querySelector('[data-mcp-env]').value = '';
    form.querySelector('[data-mcp-headers-env]').value = '';
    form.querySelector('[data-mcp-bearer-env]').value = preset.bearerEnv || '';
    form.querySelector('[data-mcp-enabled]').checked = true;
    form.querySelector('[data-mcp-agent-calls]').checked = false;
    setMcpEditorRoles(form, preset.roles || []);
    updateMcpEditorTransport(form);
    form.querySelector('[data-mcp-name]')?.focus();
  }

  function openMcpEditor(serverId = '') {
    renderIntegrationItems();
    const form = integrationList?.querySelector('[data-mcp-editor]');
    if (!form) return;
    const server = (integrationData.mcp?.items || []).find((item) => item.id === serverId);
    form.hidden = false;
    form.querySelector('[data-mcp-id]').value = server?.id || '';
    form.querySelector('[data-mcp-editor-title]').textContent = server ? 'Edit MCP server' : 'Connect MCP server';
    form.querySelector('[data-mcp-name]').value = server?.name || '';
    form.querySelector('[data-mcp-transport]').value = server?.transport || 'stdio';
    form.querySelector('[data-mcp-command]').value = server?.command || '';
    form.querySelector('[data-mcp-args]').value = (server?.args || []).join('\n');
    form.querySelector('[data-mcp-cwd]').value = server?.cwd || '';
    form.querySelector('[data-mcp-url]').value = server?.url || '';
    form.querySelector('[data-mcp-env]').value = mcpMappingText(server?.env || {});
    form.querySelector('[data-mcp-headers-env]').value = mcpMappingText(server?.headers_env || {});
    form.querySelector('[data-mcp-bearer-env]').value = server?.bearer_token_env_var || '';
    const quickCredential = server?.bearer_token_env_var
      || Object.values(server?.env || {})[0]
      || Object.values(server?.headers_env || {})[0]
      || '';
    form.querySelector('[data-mcp-credential-env]').value = quickCredential;
    form.querySelector('[data-mcp-credential-value]').value = '';
    form.querySelector('[data-mcp-startup-timeout]').value = server?.startup_timeout_seconds || 15;
    form.querySelector('[data-mcp-tool-timeout]').value = server?.tool_timeout_seconds || 60;
    form.querySelector('[data-mcp-enabled]').checked = server?.enabled !== false;
    form.querySelector('[data-mcp-agent-calls]').checked = server?.allow_agent_calls === true;
    setMcpEditorRoles(form, server?.roles || MCP_ROLES.map((role) => role.id));
    const transport = form.querySelector('[data-mcp-transport]');
    transport.onchange = () => updateMcpEditorTransport(form);
    updateMcpEditorTransport(form);
    form.querySelector('[data-mcp-name]')?.focus();
  }

  async function saveMcpServer(form) {
    const serverId = form.querySelector('[data-mcp-id]').value;
    const existing = (integrationData.mcp?.items || []).find((item) => item.id === serverId) || {};
    const roles = [...form.querySelectorAll('[data-mcp-server-role]:checked')].map((el) => el.value);
    if (!roles.length) throw { detail: 'Choose at least one default god for this MCP server.' };
    const payload = mcpServerPayload(existing, {
      name: form.querySelector('[data-mcp-name]').value,
      transport: form.querySelector('[data-mcp-transport]').value,
      command: form.querySelector('[data-mcp-command]').value,
      args: form.querySelector('[data-mcp-args]').value.split('\n').map((value) => value.trim()).filter(Boolean),
      cwd: form.querySelector('[data-mcp-cwd]').value,
      url: form.querySelector('[data-mcp-url]').value,
      env: parseMcpMapping(form.querySelector('[data-mcp-env]').value),
      headers_env: parseMcpMapping(form.querySelector('[data-mcp-headers-env]').value),
      bearer_token_env_var: form.querySelector('[data-mcp-bearer-env]').value.trim(),
      credential_env_var: form.querySelector('[data-mcp-credential-env]').value.trim(),
      credential_value: form.querySelector('[data-mcp-credential-value]').value,
      enabled: form.querySelector('[data-mcp-enabled]').checked,
      allow_agent_calls: form.querySelector('[data-mcp-agent-calls]').checked,
      roles,
      startup_timeout_seconds: Number(form.querySelector('[data-mcp-startup-timeout]').value) || 15,
      tool_timeout_seconds: Number(form.querySelector('[data-mcp-tool-timeout]').value) || 60,
    });
    const data = await integrationFetch(`/api/mcp/servers${serverId ? `/${encodeURIComponent(serverId)}` : ''}`, {
      method: serverId ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    integrationData.mcp = data;
    renderIntegrationNav();
    renderIntegrationItems();
    setComposerStatus('MCP server saved. Test it to discover and authorize tools.', 'ok');
  }

  async function testMcpServer(serverId) {
    setIntegrationsPill('testing');
    const data = await integrationFetch(`/api/mcp/servers/${encodeURIComponent(serverId)}/test`, { method: 'POST' });
    await loadIntegrationData('mcp');
    setIntegrationsPill(data.ok ? 'connected' : 'error', data.ok ? 'ok' : 'error');
    setComposerStatus(data.ok ? 'MCP connection ready' : `MCP test failed: ${data.error || 'unknown error'}`, data.ok ? 'ok' : 'error');
  }

  async function toggleMcpAgent(serverId, enabled) {
    const server = (integrationData.mcp?.items || []).find((item) => item.id === serverId);
    if (!server) return;
    const data = await integrationFetch(`/api/mcp/servers/${encodeURIComponent(serverId)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(mcpServerPayload(server, { allow_agent_calls: enabled })),
    });
    integrationData.mcp = data;
    renderIntegrationNav();
    renderIntegrationItems();
    setComposerStatus(`MCP agent calls ${enabled ? 'enabled' : 'disabled'}`, 'ok');
  }

  async function saveMcpToolPolicy(button) {
    const item = button.closest('[data-mcp-tool-policy]');
    if (!item) return;
    const serverId = item.dataset.mcpServerId;
    const toolName = item.dataset.mcpToolName;
    const roles = [...item.querySelectorAll('[data-mcp-policy-role]:checked')].map((el) => el.value);
    const data = await integrationFetch(
      `/api/mcp/servers/${encodeURIComponent(serverId)}/tools/${encodeURIComponent(toolName)}/policy`,
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          enabled: item.querySelector('[data-mcp-policy-enabled]').checked,
          roles,
          approval: item.querySelector('[data-mcp-policy-approval]').value,
        }),
      },
    );
    integrationData.mcp = data;
    renderIntegrationNav();
    renderIntegrationItems();
    setComposerStatus(`${toolName} access saved`, 'ok');
  }

  async function callMcpTool(button) {
    const serverId = button.dataset.mcpCall;
    const tool = button.dataset.mcpTool;
    const key = `${serverId}:${tool}`;
    const argsInput = integrationList.querySelector(`[data-mcp-call-args="${CSS.escape(key)}"]`);
    const resultEl = integrationList.querySelector(`[data-mcp-result="${CSS.escape(key)}"]`);
    let argumentsValue = {};
    try {
      argumentsValue = JSON.parse(argsInput?.value || '{}');
    } catch (e) {
      if (resultEl) resultEl.textContent = 'Arguments must be valid JSON.';
      return;
    }
    try {
      const data = await integrationFetch(`/api/mcp/servers/${encodeURIComponent(serverId)}/call`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tool, arguments: argumentsValue }),
      });
      if (resultEl) resultEl.textContent = JSON.stringify(data.result, null, 2);
    } catch (e) {
      if (resultEl) resultEl.textContent = setupErrorMessage(e);
    }
  }

  async function saveWebhook(form) {
    const data = await integrationFetch('/api/channels/webhook/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        enabled: form.querySelector('[data-webhook-enabled]').checked,
        token: form.querySelector('[data-webhook-token]').value,
        rotate_token: form.querySelector('[data-webhook-rotate]').checked,
      }),
    });
    data.revealed_token = data.token || '';
    integrationData.channels = { items: [data] };
    renderIntegrationItems();
    setComposerStatus(data.enabled ? 'Webhook enabled; copy the token now' : 'Webhook disabled', 'ok');
  }

  async function handleIntegrationClick(event) {
    const target = event.target.closest('button, input');
    if (!target) return;
    if (target.matches('[data-skill-use]')) return prepareSkillInvocation(target.dataset.skillUse);
    if (target.matches('[data-extension-new]')) return openExtensionEditor(target.dataset.extensionNew);
    if (target.matches('[data-extension-cancel]')) return renderIntegrationItems();
    if (target.matches('[data-extension-edit]')) return openExtensionEditor(target.dataset.extensionEdit, target.dataset.extensionId);
    if (target.matches('[data-extension-toggle]')) return togglePromptExtension(target.dataset.extensionToggle, target.dataset.extensionId, target.dataset.extensionEnabled === 'true');
    if (target.matches('[data-extension-delete]')) return deletePromptExtension(target.dataset.extensionDelete, target.dataset.extensionId);
    if (target.matches('[data-mcp-new]')) return openMcpEditor();
    if (target.matches('[data-mcp-preset]')) return applyMcpPreset(target.dataset.mcpPreset);
    if (target.matches('[data-mcp-cancel]')) return renderIntegrationItems();
    if (target.matches('[data-mcp-edit]')) return openMcpEditor(target.dataset.mcpEdit);
    if (target.matches('[data-mcp-test]')) return testMcpServer(target.dataset.mcpTest);
    if (target.matches('[data-mcp-delete]')) {
      if (!window.confirm('Delete this MCP server?')) return;
      integrationData.mcp = await integrationFetch(`/api/mcp/servers/${encodeURIComponent(target.dataset.mcpDelete)}`, { method: 'DELETE' });
      renderIntegrationNav();
      renderIntegrationItems();
      return;
    }
    if (target.matches('[data-mcp-agent-toggle]')) return toggleMcpAgent(target.dataset.mcpAgentToggle, target.checked);
    if (target.matches('[data-mcp-policy-save]')) return saveMcpToolPolicy(target);
    if (target.matches('[data-mcp-call]')) return callMcpTool(target);
    if (target.matches('[data-webhook-copy-endpoint]')) {
      await copyToClipboard(`${window.location.origin}/api/channels/webhook`);
      setComposerStatus('Webhook endpoint copied', 'ok');
    }
    if (target.matches('[data-webhook-copy-token]')) {
      const token = integrationList.querySelector('[data-webhook-token]')?.value || '';
      if (!token) {
        setComposerStatus('Save or rotate the webhook token first', 'warn');
        return;
      }
      await copyToClipboard(token);
      setComposerStatus('Webhook token copied', 'ok');
    }
  }

  async function handleIntegrationSubmit(event) {
    const extensionForm = event.target.closest('[data-extension-editor]');
    if (extensionForm) {
      event.preventDefault();
      await savePromptExtension(extensionForm);
      return;
    }
    const mcpForm = event.target.closest('[data-mcp-editor]');
    if (mcpForm) {
      event.preventDefault();
      await saveMcpServer(mcpForm);
      return;
    }
    const webhookForm = event.target.closest('[data-webhook-form]');
    if (webhookForm) {
      event.preventDefault();
      await saveWebhook(webhookForm);
    }
  }

  function applyIntegrationsPayload(payload = {}) {
    latestIntegrations = payload || {};
    const summary = latestIntegrations.summary || {};
    const readyTotal = Object.values(summary).reduce((sum, item) => sum + Number(item.ready || 0), 0);
    const itemTotal = Object.values(summary).reduce((sum, item) => sum + Number(item.total || 0), 0);
    const runtime = latestIntegrations.runtime || {};
    if (integrationsStatusTitle) {
      integrationsStatusTitle.textContent = `${runtime.skills_enabled || 0} skills · ${runtime.plugins_enabled || 0} plugins · ${runtime.mcp_ready || 0} MCP ready`;
    }
    setIntegrationsPill(itemTotal ? 'live' : 'empty', itemTotal ? 'ok' : 'warn');
    const paths = latestIntegrations.paths || {};
    [
      [integrationsConfigPath, paths.config_path],
      [integrationsEnvPath, paths.env_path],
      [integrationsPluginsPath, paths.plugins_path],
      [integrationsSkillsPath, paths.skills_path],
    ].forEach(([el, value]) => {
      if (!el) return;
      el.textContent = value || '—';
      el.title = value || '';
    });
    renderIntegrationNav();
    renderIntegrationItems();
  }

  async function loadIntegrations() {
    if (!integrationList) return;
    setIntegrationsPill('checking');
    try {
      const resp = await fetch('/api/integrations');
      const data = await resp.json();
      if (!resp.ok) throw data;
      applyIntegrationsPayload(data);
      await loadIntegrationData(activeIntegrationSection);
    } catch (e) {
      console.error(e);
      if (integrationsStatusTitle) integrationsStatusTitle.textContent = 'Integrations unavailable';
      setIntegrationsPill('error', 'error');
      integrationList.innerHTML = `<div class="memory-empty">${escapeHtml(setupErrorMessage(e))}</div>`;
    }
  }

  function openIntegrationsSection(section = 'mcp') {
    activeIntegrationSection = section;
    openSettingsPane('integrations');
    renderIntegrationNav();
    renderIntegrationItems();
    loadIntegrationData(section);
  }

  async function initProtectedData() {
    if (protectedDataLoaded) return;
    if (authState.enabled && !authState.authenticated) return;
    protectedDataLoaded = true;
    updatePreviewControls(false);
    renderFileInspectorEmpty();
    await Promise.allSettled([
      loadAppInfo(),
      loadWorkspaceInfo(),
      loadWorkspaceFiles(''),
      loadSetupStatus(),
      loadRoles(),
      loadMemory(),
      loadIntegrations(),
      loadSkillCatalog(),
      loadConversations(),
      loadUpdateStatus(),
      loadUsage(),
    ]);
  }

  if (loginForm) loginForm.addEventListener('submit', submitLogin);
  if (securityForm) securityForm.addEventListener('submit', saveSecurity);
  if (securityLogoutBtn) securityLogoutBtn.addEventListener('click', logoutAuth);
  if (securityEnabled) {
    securityEnabled.addEventListener('change', () => {
      syncSecurityEnabledFields();
      clearSecurityResult();
      if (securityEnabled.checked) securityPassword?.focus();
    });
  }
  [securityUsername, securityPassword].forEach((el) => {
    if (!el) return;
    el.addEventListener('input', clearSecurityResult);
  });
  if (memoryForm) memoryForm.addEventListener('submit', saveMemory);
  if (memoryRefreshBtn) memoryRefreshBtn.addEventListener('click', () => loadMemory());
  if (memoryClearBtn) memoryClearBtn.addEventListener('click', clearMemory);
  [memoryEnabled, memoryAutoCapture].forEach((el) => {
    if (!el) return;
    el.addEventListener('change', saveMemorySettings);
  });
  if (memorySearch) {
    memorySearch.addEventListener('input', () => {
      if (memorySearchTimer) clearTimeout(memorySearchTimer);
      memorySearchTimer = setTimeout(() => loadMemory(memorySearch.value), 180);
    });
  }
  if (memoryList) {
    memoryList.addEventListener('click', (event) => {
      const btn = event.target.closest('[data-memory-delete]');
      if (!btn) return;
      deleteMemory(btn.dataset.memoryDelete);
    });
  }
  if (memorySuggestionList) {
    memorySuggestionList.addEventListener('click', (event) => {
      const accept = event.target.closest('[data-memory-accept]');
      if (accept) {
        acceptMemorySuggestion(accept.dataset.memoryAccept);
        return;
      }
      const ignore = event.target.closest('[data-memory-ignore]');
      if (ignore) ignoreMemorySuggestion(ignore.dataset.memoryIgnore);
    });
  }
  if (integrationNav) {
    integrationNav.addEventListener('click', (event) => {
      const btn = event.target.closest('[data-integration-section]');
      if (!btn) return;
      activeIntegrationSection = btn.dataset.integrationSection || 'mcp';
      renderIntegrationNav();
      renderIntegrationItems();
      loadIntegrationData(activeIntegrationSection);
    });
  }
  if (integrationList) {
    integrationList.addEventListener('click', (event) => {
      handleIntegrationClick(event).catch((error) => {
        setComposerStatus(setupErrorMessage(error), 'error');
      });
    });
    integrationList.addEventListener('submit', (event) => {
      handleIntegrationSubmit(event).catch((error) => {
        setComposerStatus(setupErrorMessage(error), 'error');
      });
    });
  }

  // ---------- Display preferences (saved in localStorage) ----------
  const PREF_KEY = 'pantheon:display-prefs';
  const DEFAULT_PREFS = {
    theme: 'dark',       // 'dark' | 'light'
    fontSize: 'md',      // 'sm' | 'md' | 'lg'
    voiceLanguage: 'auto', // 'auto' | BCP 47 language tag
  };

  const VOICE_LANGUAGES = new Set([
    'auto',
    'zh-CN',
    'zh-TW',
    'en-US',
    'en-GB',
    'ja-JP',
    'ko-KR',
    'fr-FR',
    'de-DE',
    'es-ES',
  ]);

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
    document.body.classList.toggle('light', prefs.theme === 'light');
    // Font size
    document.body.classList.remove('font-sm', 'font-md', 'font-lg');
    document.body.classList.add(`font-${prefs.fontSize}`);
    const baseSize = prefs.fontSize === 'sm' ? '13px' : prefs.fontSize === 'lg' ? '16px' : '14px';
    document.documentElement.style.fontSize = baseSize;
    document.body.classList.remove(
      'no-bg-anim',
      'density-compact',
      'content-narrow',
      'content-standard',
      'content-wide',
      'code-wrap',
    );
    if (voiceLanguageSelect) {
      voiceLanguageSelect.value = VOICE_LANGUAGES.has(prefs.voiceLanguage) ? prefs.voiceLanguage : 'auto';
    }
  }

  function syncOptBtnActive(prefs) {
    $$('.opt-btn').forEach((btn) => {
      const action = btn.dataset.action;
      const value = btn.dataset.value;
      if (!action) return;
      let isActive = false;
      if (action === 'theme')      isActive = (value === prefs.theme);
      else if (action === 'fontSize')   isActive = (value === prefs.fontSize);
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
        };
        if (!validMap[action] || !validMap[action].includes(value)) return;
        prefs[action] = value;
        savePrefs(prefs);
        applyPrefs(prefs);
        syncOptBtnActive(prefs);
      });
    });
    if (voiceLanguageSelect) {
      voiceLanguageSelect.addEventListener('change', () => {
        const value = voiceLanguageSelect.value || 'auto';
        if (!VOICE_LANGUAGES.has(value)) return;
        const prefs = loadPrefs();
        prefs.voiceLanguage = value;
        savePrefs(prefs);
        applyPrefs(prefs);
        setComposerStatus(
          value === 'auto' ? 'Voice language follows browser' : `Voice language set to ${voiceLanguageLabel(value)}`,
          'ok',
        );
      });
    }
    applyPrefs(loadPrefs());
    syncOptBtnActive(loadPrefs());
  }

  function setWorkspaceState(label, state = 'idle') {
    if (!workspaceState) return;
    workspaceState.textContent = label;
    workspaceState.dataset.state = state;
  }

  function workspaceModeLabel() {
    if (currentMode === 'auto') return 'Auto routing';
    if (currentMode === 'multi') return 'Multi-role council';
    if (currentMode.startsWith('role:')) return `${metaFor(currentMode.slice(5)).label} direct`;
    return currentMode || 'Auto routing';
  }

  function updateWorkspaceTaskElapsed(finalLabel = '') {
    if (!wsTaskElapsedEl) return;
    if (!workspaceTaskStartedAt) {
      wsTaskElapsedEl.textContent = finalLabel || '0.0s';
      return;
    }
    const elapsed = ((Date.now() - workspaceTaskStartedAt) / 1000).toFixed(1);
    wsTaskElapsedEl.textContent = finalLabel ? `${elapsed}s · ${finalLabel}` : `${elapsed}s`;
  }

  function stopWorkspaceTaskTimer(finalLabel = '') {
    if (workspaceTaskTimer) {
      clearInterval(workspaceTaskTimer);
      workspaceTaskTimer = null;
    }
    updateWorkspaceTaskElapsed(finalLabel);
  }

  function startWorkspaceTask(title, modeLabel = workspaceModeLabel()) {
    if (wsTaskTitleEl) wsTaskTitleEl.textContent = titleFromPrompt(title) || 'Current task';
    if (wsTaskModeEl) wsTaskModeEl.textContent = modeLabel;
    workspaceTaskStartedAt = Date.now();
    stopWorkspaceTaskTimer();
    workspaceTaskTimer = setInterval(() => updateWorkspaceTaskElapsed(), 250);
    updateWorkspaceTaskElapsed();
  }

  function resetWorkspaceTask() {
    stopWorkspaceTaskTimer();
    workspaceTaskStartedAt = 0;
    if (wsTaskTitleEl) wsTaskTitleEl.textContent = 'Awaiting task';
    if (wsTaskModeEl) wsTaskModeEl.textContent = 'Idle';
    if (wsTaskElapsedEl) wsTaskElapsedEl.textContent = '0.0s';
  }

  function planItemsFromText(text) {
    const value = String(text || '').trim();
    if (!value) return [];
    const lines = value.split(/\n+/)
      .map((line) => line.replace(/^\s*(?:[-*•]|\d+[.)])\s*/, '').trim())
      .filter(Boolean);
    if (lines.length > 1) return lines.slice(0, 8);
    return [value];
  }

  function setWorkspacePlan(text, active = true) {
    if (!wsPlanEl) return;
    const items = planItemsFromText(text);
    if (!items.length) {
      wsPlanEl.innerHTML = '<span class="ws-empty">No plan yet</span>';
      wsPlanEl.classList.remove('active');
      return;
    }
    if (items.length === 1) {
      wsPlanEl.innerHTML = `<div class="ws-plan-text">${escapeHtml(items[0])}</div>`;
    } else {
      wsPlanEl.innerHTML = `<ol class="ws-roadmap">${items.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ol>`;
    }
    wsPlanEl.classList.toggle('active', Boolean(active));
  }

  function setWorkspacePlanPayload(data = {}) {
    if (!wsPlanEl) return;
    const steps = Array.isArray(data.steps) ? data.steps.filter((step) => step?.role) : [];
    if (!steps.length) {
      setWorkspacePlan(data.plan || '', true);
      return;
    }
    const reasoning = String(data.plan || '').trim();
    wsPlanEl.innerHTML = `
      ${reasoning ? `<p class="ws-plan-reasoning">${escapeHtml(reasoning)}</p>` : ''}
      <ol class="ws-roadmap">
        ${steps.map((step) => {
          const meta = metaFor(step.role);
          const task = step.task || step.description || 'Complete assigned work';
          const kind = String(step.kind || 'work').toLowerCase();
          const kindLabel = {
            work: 'Work',
            question: 'Question',
            review: 'Review',
            revision: 'Revision',
          }[kind] || 'Work';
          const dependencies = Array.isArray(step.depends_on) ? step.depends_on : [];
          const criteria = Array.isArray(step.acceptance_criteria)
            ? step.acceptance_criteria.filter(Boolean)
            : [];
          return `
            <li>
              <div class="ws-plan-step-head">
                <strong style="color: ${meta.color}">${escapeHtml(meta.label)}</strong>
                <span class="ws-plan-kind">${escapeHtml(kindLabel)}</span>
                ${dependencies.length ? `<span class="ws-plan-deps">after ${dependencies.map((item) => `#${escapeHtml(item)}`).join(', ')}</span>` : ''}
              </div>
              <span>${escapeHtml(task)}</span>
              ${step.deliverable ? `<small class="ws-plan-deliverable">Deliverable: ${escapeHtml(step.deliverable)}</small>` : ''}
              ${criteria.length ? `<small class="ws-plan-criteria">Done when: ${criteria.map((item) => escapeHtml(item)).join(' · ')}</small>` : ''}
            </li>
          `;
        }).join('')}
      </ol>
    `;
    wsPlanEl.classList.add('active');
  }

  function safeExternalHref(href) {
    const value = String(href || '').trim();
    const lower = value.toLowerCase();
    if (/^https?:\/\//i.test(value) || lower.startsWith('mailto:') || lower.startsWith('tel:')) {
      return value;
    }
    if (/^\/\//.test(value)) return `https:${value}`;
    return '';
  }

  window.addEventListener('message', (event) => {
    if (!wsPreviewFrame || event.source !== wsPreviewFrame.contentWindow) return;
    const data = event.data || {};
    if (data.type !== 'pantheon:open-preview-link') return;
    const href = safeExternalHref(data.href);
    if (!href) return;
    window.open(href, '_blank', 'noopener,noreferrer');
  });

  function setWorkspaceTabContent(tabName, hasContent) {
    const tab = workspaceTabs.find((item) => item.dataset.wsTab === tabName);
    if (tab) tab.classList.toggle('has-content', Boolean(hasContent));
  }

  function formatChronosTime(value) {
    if (!value) return 'not scheduled';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return date.toLocaleString([], {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  function formatChronosSchedule(job) {
    if (job.schedule_type === 'interval') {
      const seconds = Number(job.interval_seconds || 0);
      if (seconds >= 86400 && seconds % 86400 === 0) return `every ${seconds / 86400}d`;
      if (seconds >= 3600 && seconds % 3600 === 0) return `every ${seconds / 3600}h`;
      if (seconds >= 60 && seconds % 60 === 0) return `every ${seconds / 60}m`;
      return `every ${seconds || '?'}s`;
    }
    if (job.schedule_type === 'daily') {
      const hour = String(job.hour || 0).padStart(2, '0');
      const minute = String(job.minute || 0).padStart(2, '0');
      return `daily ${hour}:${minute}`;
    }
    return 'once';
  }

  function chronosJobStatus(job) {
    if (job.running) return 'running';
    if (!job.enabled) return job.last_status === 'done' ? 'done' : 'paused';
    return job.last_status || 'scheduled';
  }

  function renderChronosJobs(payload = {}) {
    if (!chronosJobsEl) return;
    chronosJobs = Array.isArray(payload.jobs) ? payload.jobs : chronosJobs;
    chronosRuns = Array.isArray(payload.runs) ? payload.runs : chronosRuns;
    setWorkspaceTabContent('activity', chronosJobs.length || chronosRuns.length);

    if (!chronosJobs.length) {
      chronosJobsEl.innerHTML = '<span class="ws-empty">No scheduled jobs yet</span>';
      return;
    }

    chronosJobsEl.innerHTML = chronosJobs.map((job) => {
      const status = chronosJobStatus(job);
      const paused = status === 'paused' || !job.enabled;
      const statusClass = paused ? 'is-paused' : status === 'error' ? 'is-error' : '';
      const modeLabel = job.mode === 'auto'
        ? 'Auto'
        : job.mode === 'multi'
          ? 'Multi-role'
          : metaFor(String(job.mode || '').replace('role:', '')).label;
      const pauseAction = paused ? 'resume' : 'pause';
      const pauseLabel = paused ? 'Resume' : 'Pause';
      return `
        <article class="chronos-job ${statusClass}" data-job-id="${escapeHtml(job.id)}">
          <div class="chronos-job-head">
            <div>
              <div class="chronos-job-title">${escapeHtml(job.title || 'Scheduled task')}</div>
              <div class="chronos-job-meta">
                <span>${escapeHtml(formatChronosSchedule(job))}</span>
                <span>${escapeHtml(modeLabel)}</span>
                <span>${escapeHtml(String(job.run_count || 0))} runs</span>
              </div>
            </div>
            <span class="chronos-job-pill">${escapeHtml(status)}</span>
          </div>
          <div class="chronos-job-prompt">${escapeHtml(job.prompt || '')}</div>
          <div class="chronos-job-meta">
            <span>next ${escapeHtml(formatChronosTime(job.next_run_at_iso))}</span>
            ${job.last_run_at_iso ? `<span>last ${escapeHtml(formatChronosTime(job.last_run_at_iso))}</span>` : ''}
          </div>
          ${job.last_output ? `<div class="chronos-job-prompt">${escapeHtml(job.last_output)}</div>` : ''}
          ${job.last_error ? `<div class="chronos-job-prompt">${escapeHtml(job.last_error)}</div>` : ''}
          <div class="chronos-job-actions">
            <button class="ws-copy-btn" type="button" data-chronos-action="run">Run now</button>
            <button class="ws-copy-btn" type="button" data-chronos-action="${escapeHtml(pauseAction)}">${escapeHtml(pauseLabel)}</button>
            <button class="ws-copy-btn" type="button" data-chronos-action="delete">Delete</button>
          </div>
        </article>
      `;
    }).join('');
  }

  async function loadChronosJobs(options = {}) {
    if (!chronosJobsEl) return;
    const silent = Boolean(options.silent);
    try {
      const resp = await fetch('/api/chronos/jobs');
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) throw new Error(data.detail || `HTTP ${resp.status}`);
      renderChronosJobs(data);
    } catch (e) {
      chronosJobsEl.innerHTML = `<span class="ws-empty">${escapeHtml(e.message || 'Could not load Chronos jobs')}</span>`;
      if (!silent) setComposerStatus(e.message || 'Could not load Chronos jobs', 'error', true);
    }
  }

  async function runChronosAction(jobId, action) {
    if (!jobId || !action) return;
    try {
      const method = action === 'delete' ? 'DELETE' : 'POST';
      if (action === 'run') setWorkspaceState('Running Chronos job', 'running');
      const endpoint = action === 'delete'
        ? `/api/chronos/jobs/${encodeURIComponent(jobId)}`
        : `/api/chronos/jobs/${encodeURIComponent(jobId)}/${action}`;
      const resp = await fetch(endpoint, { method });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) throw new Error(data.detail || `HTTP ${resp.status}`);
      renderChronosJobs(data);
      const ranWithError = action === 'run' && data.job?.last_status === 'error';
      setComposerStatus(
        ranWithError ? 'Chronos job failed' : action === 'run' ? 'Chronos job ran' : `Chronos job ${action}d`,
        ranWithError ? 'error' : 'ok',
        ranWithError,
      );
      if (action === 'run') setWorkspaceState(ranWithError ? 'Error' : 'Ready', ranWithError ? 'error' : 'ready');
    } catch (e) {
      setWorkspaceState('Error', 'error');
      setComposerStatus(e.message || 'Chronos action failed', 'error', true);
      loadChronosJobs({ silent: true });
    }
  }

  if (chronosRefreshBtn) {
    chronosRefreshBtn.addEventListener('click', () => loadChronosJobs());
  }

  if (chronosJobsEl) {
    chronosJobsEl.addEventListener('click', (event) => {
      const btn = event.target.closest('[data-chronos-action]');
      if (!btn) return;
      const card = btn.closest('[data-job-id]');
      runChronosAction(card?.dataset.jobId, btn.dataset.chronosAction);
    });
  }

  function previewActionButtons() {
    return [wsOpenPreviewBtn, wsReloadPreviewBtn, wsDownloadPreviewBtn].filter(Boolean);
  }

  function updatePreviewControls(enabled = workspacePreviewKind !== 'empty') {
    previewActionButtons().forEach((btn) => { btn.disabled = !enabled; });
    if (wsPreviewViewport) {
      const device = workspacePreviewDevice === 'mobile' ? 'Mobile' : 'Desktop';
      wsPreviewViewport.textContent = `${device} · ${Math.round(workspacePreviewScale * 100)}%`;
    }
    wsPreviewDeviceBtns.forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.previewDevice === workspacePreviewDevice);
    });
    if (wsPreviewShell) {
      wsPreviewShell.dataset.device = workspacePreviewDevice;
      wsPreviewShell.style.setProperty('--preview-scale', String(workspacePreviewScale));
    }
    if (wsPreviewZoom && wsPreviewZoom.value !== String(workspacePreviewScale)) {
      wsPreviewZoom.value = String(workspacePreviewScale);
    }
  }

  function setPreviewLabel(label) {
    workspacePreviewLabel = String(label || 'preview.html')
      .replace(/[^\w.-]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 80) || 'preview.html';
    if (!workspacePreviewLabel.endsWith('.html')) workspacePreviewLabel += '.html';
  }

  function htmlHasAuthorStyle(html) {
    const value = String(html || '');
    return /<style[\s>]/i.test(value) ||
           /<link\b[^>]*rel=["']?stylesheet/i.test(value) ||
           /\sstyle\s*=/i.test(value);
  }

  function isCompleteHtmlDocument(html) {
    return /<!doctype\s+html|<html[\s>]|<head[\s>]|<body[\s>]/i.test(String(html || ''));
  }

  function setPreviewHint(hint = '') {
    workspacePreviewHint = hint;
    if (!wsPreviewHint) return;
    wsPreviewHint.textContent = hint;
    wsPreviewHint.hidden = !hint;
  }

  function addWorkspaceStepAction(stepEl, label, tabName) {
    if (!stepEl || !label || !tabName) return;
    let actions = stepEl.querySelector('.ws-step-actions');
    if (!actions) {
      actions = document.createElement('div');
      actions.className = 'ws-step-actions';
      const text = stepEl.querySelector('.ws-step-text');
      if (text) text.appendChild(actions);
    }
    if (actions.querySelector(`[data-ws-open="${CSS.escape(tabName)}"]`)) return;
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'ws-step-action';
    btn.dataset.wsOpen = tabName;
    btn.textContent = label;
    btn.addEventListener('click', () => {
      openWorkspace();
      activateWorkspaceTab(tabName);
    });
    actions.appendChild(btn);
  }

  function latestWorkspaceStep(role) {
    const steps = Array.from(wsStepsEl.querySelectorAll(`.ws-step[data-role="${CSS.escape(role)}"]`));
    return steps[steps.length - 1] || null;
  }

  function addWorkspaceStepActionByRole(role, label, tabName) {
    addWorkspaceStepAction(latestWorkspaceStep(role), label, tabName);
  }

  function terminalTimestamp() {
    return new Date().toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  }

  function renderWorkspaceTerminal() {
    if (!wsOutputEl) return;
    if (!workspaceConsoleText.trim()) {
      wsOutputEl.textContent = 'No terminal output yet';
      wsOutputEl.dataset.empty = 'true';
      return;
    }
    wsOutputEl.textContent = workspaceConsoleText;
    delete wsOutputEl.dataset.empty;
    wsOutputEl.scrollTop = wsOutputEl.scrollHeight;
  }

  function pushWorkspaceLine(text) {
    if (!text) return;
    if (workspaceConsoleText && !workspaceConsoleText.endsWith('\n')) {
      workspaceConsoleText += '\n';
    }
    workspaceConsoleText += `[${terminalTimestamp()}] ${text}\n`;
    renderWorkspaceTerminal();
  }

  function clearWorkspaceTerminalHints() {
    if (!wsTerminalHints) return;
    wsTerminalHints.hidden = true;
    wsTerminalHints.innerHTML = '';
  }

  function workspacePathBasename(path) {
    const parts = String(path || '').split('/').filter(Boolean);
    return parts[parts.length - 1] || path || 'file';
  }

  function workspacePathDirname(path) {
    const parts = String(path || '').split('/').filter(Boolean);
    parts.pop();
    return parts.join('/');
  }

  function renderWorkspaceTerminalHtmlHint(paths) {
    if (!wsTerminalHints || !paths.length) return;
    const uniquePaths = Array.from(new Set(paths));
    const firstPath = uniquePaths[0];
    const label = uniquePaths.length === 1 ? workspacePathBasename(firstPath) : `${uniquePaths.length} HTML files`;
    wsTerminalHints.hidden = false;
    wsTerminalHints.innerHTML = `
      <div class="ws-terminal-hint-card">
        <div>
          <span>Created ${escapeHtml(label)}</span>
          <small>Preview available</small>
        </div>
        <div class="ws-terminal-hint-actions">
          <button class="ws-copy-btn" data-terminal-preview="${escapeHtml(firstPath)}" type="button">Preview</button>
          <button class="ws-copy-btn" data-terminal-files="${escapeHtml(firstPath)}" type="button">Files</button>
        </div>
      </div>
    `;
    setWorkspaceTabContent('terminal', true);
  }

  function appendWorkspaceStream(text) {
    if (!text) return;
    workspaceStreamText += text;
    workspaceConsoleText += text;
    renderWorkspaceTerminal();
    syncWorkspaceArtifacts();
  }

  const ARTIFACT_EXT_BY_LANG = {
    html: 'html',
    htm: 'html',
    css: 'css',
    js: 'js',
    javascript: 'js',
    mjs: 'mjs',
    ts: 'ts',
    typescript: 'ts',
    jsx: 'jsx',
    tsx: 'tsx',
    python: 'py',
    py: 'py',
    json: 'json',
    markdown: 'md',
    md: 'md',
    yaml: 'yaml',
    yml: 'yml',
    bash: 'sh',
    shell: 'sh',
    sh: 'sh',
    text: 'txt',
    txt: 'txt',
  };

  function formatBytes(text) {
    const bytes = new Blob([text || '']).size;
    if (bytes < 1024) return `${bytes} B`;
    return `${(bytes / 1024).toFixed(1)} KB`;
  }

  function formatFileSize(size) {
    const value = Number(size || 0);
    if (value < 1024) return `${value} B`;
    if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
    return `${(value / 1024 / 1024).toFixed(1)} MB`;
  }

  function setComposerStatus(message = '', tone = '', persist = false) {
    if (!composerStatus) return;
    if (composerStatusTimer) {
      clearTimeout(composerStatusTimer);
      composerStatusTimer = null;
    }
    composerStatus.textContent = message;
    composerStatus.dataset.tone = tone || '';
    composerStatus.hidden = !message;
    if (composerStatusDot) composerStatusDot.hidden = !message;
    if (message && !persist) {
      composerStatusTimer = setTimeout(() => {
        if (voiceListening) return;
        composerStatus.textContent = '';
        composerStatus.hidden = true;
        if (composerStatusDot) composerStatusDot.hidden = true;
      }, 2600);
    }
  }

  function fileExtension(name = '') {
    const clean = String(name || '').split('?')[0].split('#')[0];
    const idx = clean.lastIndexOf('.');
    return idx === -1 ? '' : clean.slice(idx + 1).toLowerCase();
  }

  function fileKindLabel(file) {
    const ext = fileExtension(file.name);
    if (ext) return ext.slice(0, 5);
    if ((file.type || '').startsWith('text/')) return 'txt';
    return 'file';
  }

  function isTextAttachment(file) {
    const type = file.type || '';
    const ext = fileExtension(file.name);
    return type.startsWith('text/') ||
      type === 'application/json' ||
      type === 'application/xml' ||
      type === 'application/javascript' ||
      type === 'application/x-javascript' ||
      TEXT_ATTACHMENT_EXTENSIONS.has(ext);
  }

  function attachmentPublicMeta(item) {
    return {
      id: item.id,
      name: item.name,
      type: item.type,
      size: item.size,
      kind: item.kind,
      truncated: Boolean(item.truncated),
      included: item.included != null ? Boolean(item.included) : Boolean(item.content),
      note: item.note || '',
    };
  }

  function renderAttachmentChips(items = pendingAttachments) {
    if (!attachmentListEl) return;
    attachmentListEl.innerHTML = '';
    attachmentListEl.hidden = !items.length;
    items.forEach((item) => {
      const chip = document.createElement('div');
      chip.className = `attachment-chip ${item.content ? '' : 'is-meta'}`.trim();
      chip.dataset.attachmentId = item.id;
      const status = item.content
        ? `${formatFileSize(item.size)} · included${item.truncated ? ' · truncated' : ''}`
        : `${formatFileSize(item.size)} · metadata only`;
      chip.innerHTML = `
        <span class="attachment-icon">${escapeHtml(item.kind || fileKindLabel(item))}</span>
        <span class="attachment-body">
          <span class="attachment-name">${escapeHtml(item.name)}</span>
          <span class="attachment-meta">${escapeHtml(item.note || status)}</span>
        </span>
        <button class="attachment-remove" type="button" title="Remove attachment" aria-label="Remove ${escapeHtml(item.name)}">×</button>
      `;
      const remove = chip.querySelector('.attachment-remove');
      if (remove) {
        remove.addEventListener('click', () => {
          pendingAttachments = pendingAttachments.filter((att) => att.id !== item.id);
          renderAttachmentChips();
          setComposerStatus(pendingAttachments.length ? `${pendingAttachments.length} attachment${pendingAttachments.length > 1 ? 's' : ''} ready` : 'Attachments cleared', pendingAttachments.length ? 'ok' : '');
        });
      }
      attachmentListEl.appendChild(chip);
    });
  }

  async function attachmentFromFile(file) {
    const item = {
      id: `att-${Date.now()}-${attachmentSeq++}`,
      name: file.name || 'untitled',
      type: file.type || '',
      size: file.size || 0,
      kind: fileKindLabel(file),
      content: '',
      truncated: false,
      note: '',
    };
    if (!isTextAttachment(file)) {
      item.note = 'metadata only';
      return item;
    }
    try {
      const text = await file.slice(0, MAX_ATTACHMENT_TEXT_CHARS).text();
      item.content = text;
      item.truncated = file.size > new Blob([text]).size;
      item.note = item.truncated ? 'included · truncated' : 'included';
      return item;
    } catch (_) {
      item.note = 'could not read';
      return item;
    }
  }

  async function addAttachmentFiles(fileList) {
    const files = Array.from(fileList || []);
    if (!files.length) return;
    const remaining = Math.max(0, MAX_ATTACHMENTS - pendingAttachments.length);
    if (!remaining) {
      setComposerStatus(`Attachment limit is ${MAX_ATTACHMENTS} files`, 'warn');
      return;
    }
    const selected = files.slice(0, remaining);
    setComposerStatus(`Reading ${selected.length} attachment${selected.length > 1 ? 's' : ''}...`, '', true);
    const next = await Promise.all(selected.map(attachmentFromFile));
    pendingAttachments = pendingAttachments.concat(next);
    renderAttachmentChips();
    const skipped = files.length - selected.length;
    setComposerStatus(
      skipped ? `${next.length} added, ${skipped} skipped` : `${next.length} attachment${next.length > 1 ? 's' : ''} ready`,
      skipped ? 'warn' : 'ok',
    );
  }

  function clearPendingAttachments() {
    pendingAttachments = [];
    renderAttachmentChips();
    if (attachmentInput) attachmentInput.value = '';
  }

  function attachmentPromptContext(attachments = []) {
    if (!attachments.length) return '';
    const lines = [
      '',
      '',
      '[Attached context from the user]',
      'Use the following attachment contents and metadata as task context. If an attachment is metadata only, say that you cannot inspect its internal content from this UI yet.',
    ];
    attachments.forEach((item, index) => {
      lines.push('');
      lines.push(`--- Attachment ${index + 1}: ${item.name} ---`);
      lines.push(`Type: ${item.type || 'unknown'}`);
      lines.push(`Size: ${formatFileSize(item.size)}`);
      if (item.content) {
        lines.push(`Included text${item.truncated ? ' (truncated)' : ''}:`);
        lines.push('````text');
        lines.push(item.content);
        lines.push('````');
      } else {
        lines.push('Content: metadata only; the file was not readable as plain text in the browser.');
      }
    });
    return lines.join('\n');
  }

  function renderUserAttachments(attachments = []) {
    if (!attachments.length) return '';
    const chips = attachments.map((item) => {
      const meta = item.included
        ? `${formatFileSize(item.size)} · attached${item.truncated ? ' · truncated' : ''}`
        : `${formatFileSize(item.size)} · metadata`;
      return `
        <span class="attachment-chip is-meta">
          <span class="attachment-icon">${escapeHtml(item.kind || fileKindLabel(item))}</span>
          <span class="attachment-body">
            <span class="attachment-name">${escapeHtml(item.name)}</span>
            <span class="attachment-meta">${escapeHtml(meta)}</span>
          </span>
        </span>
      `;
    }).join('');
    return `<div class="message-attachments">${chips}</div>`;
  }

  function formatModified(ts) {
    if (!ts) return '';
    try {
      return new Date(ts * 1000).toLocaleString([], {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch (_) {
      return '';
    }
  }

  function extractCodeFences(text) {
    const fences = [];
    const re = /```([^\n`]*)\n([\s\S]*?)```/g;
    let match;
    while ((match = re.exec(text)) !== null) {
      fences.push({
        info: (match[1] || '').trim(),
        code: (match[2] || '').trim(),
        raw: match[0] || '',
        start: match.index,
        end: re.lastIndex,
      });
    }
    return fences;
  }

  const HTML_TAG_RE = /<!doctype html|<html[\s>]|<head[\s>]|<body[\s>]|<style[\s>]|<script[\s>]|<(main|section|article|header|footer|nav|div|form|button|input|textarea|select|canvas|svg|ul|ol|li|h[1-6]|p|a|img|table|video|audio)(\s|>)/i;

  function looksLikeHtmlSnippet(code, info = '') {
    const lang = String(info || '').trim().split(/\s+/)[0].toLowerCase();
    if (['html', 'htm', 'markup'].includes(lang)) return true;
    const value = String(code || '').trim();
    if (!value) return false;
    return HTML_TAG_RE.test(value);
  }

  function sliceHtmlLikeText(text) {
    const value = String(text || '');
    const match = value.match(HTML_TAG_RE);
    return match && match.index != null ? value.slice(match.index).trim() : '';
  }

  function artifactKindFor(info, code) {
    const lang = String(info || '').trim().split(/\s+/)[0].toLowerCase();
    const normalized = lang.replace(/[{}]/g, '');
    if (looksLikeHtmlSnippet(code, info) && (!ARTIFACT_EXT_BY_LANG[normalized] || ['text', 'txt', 'plaintext'].includes(normalized))) {
      return { lang: 'html', ext: 'html' };
    }
    if (ARTIFACT_EXT_BY_LANG[normalized]) {
      return { lang: normalized, ext: ARTIFACT_EXT_BY_LANG[normalized] };
    }
    if (looksLikeHtmlSnippet(code, info)) return { lang: 'html', ext: 'html' };
    if (/<style[\s>]|^[\s\S]*\{[\s\S]*:[\s\S]*;[\s\S]*\}/i.test(code)) return { lang: 'css', ext: 'css' };
    if (/\b(function|const|let|var|import|export)\b/.test(code)) return { lang: 'js', ext: 'js' };
    if (/^\s*[\[{]/.test(code)) return { lang: 'json', ext: 'json' };
    return { lang: normalized || 'text', ext: 'txt' };
  }

  function filenameFromFence(info, ext, index) {
    const fileMatch = String(info || '').match(/([A-Za-z0-9_./~-]+\.(?:html|htm|css|js|mjs|ts|tsx|jsx|py|json|md|ya?ml|txt|sh))/i);
    if (fileMatch) return fileMatch[1].split('/').pop();
    const baseByExt = {
      html: 'preview',
      css: 'style',
      js: 'script',
      mjs: 'script',
      ts: 'script',
      jsx: 'component',
      tsx: 'component',
      py: 'main',
      json: 'data',
      md: 'notes',
      yaml: 'config',
      yml: 'config',
      sh: 'script',
      txt: 'artifact',
    };
    const base = baseByExt[ext] || 'artifact';
    return index === 0 && ext === 'html' ? `${base}.${ext}` : `${base}-${index + 1}.${ext}`;
  }

  function uniqueArtifactName(name, seen) {
    if (!seen.has(name)) {
      seen.add(name);
      return name;
    }
    const dot = name.lastIndexOf('.');
    const base = dot === -1 ? name : name.slice(0, dot);
    const ext = dot === -1 ? '' : name.slice(dot);
    let n = 2;
    let next = `${base}-${n}${ext}`;
    while (seen.has(next)) {
      n += 1;
      next = `${base}-${n}${ext}`;
    }
    seen.add(next);
    return next;
  }

  function artifactLabel(kind) {
    const map = {
      css: 'CSS',
      html: 'HTML',
      htm: 'HTML',
      js: 'JavaScript',
      json: 'JSON',
      jsx: 'React',
      md: 'Markdown',
      mjs: 'JavaScript',
      py: 'Python',
      sh: 'Shell',
      ts: 'TypeScript',
      tsx: 'React TS',
      txt: 'Text',
      yaml: 'YAML',
      yml: 'YAML',
    };
    return map[kind] || String(kind || 'file').toUpperCase();
  }

  function artifactLanguage(kind) {
    const map = {
      htm: 'html',
      md: 'markdown',
      mjs: 'javascript',
      py: 'python',
      sh: 'bash',
      ts: 'typescript',
      tsx: 'typescript',
      yml: 'yaml',
    };
    return map[kind] || kind || 'plaintext';
  }

  function normalizeArtifactName(name, kind = 'txt') {
    const safe = String(name || '').split('/').pop().replace(/[^\w.-]+/g, '-').replace(/^-+|-+$/g, '');
    if (!safe) return `artifact.${kind || 'txt'}`;
    return /\.[A-Za-z0-9]+$/.test(safe) ? safe : `${safe}.${kind || 'txt'}`;
  }

  function artifactTitle(artifact) {
    if (artifact.kind === 'html') return htmlTitle(artifact.content);
    return artifact.name || `${artifactLabel(artifact.kind)} file`;
  }

  function narrativeWithoutFences(raw, fences) {
    if (!fences.length) return String(raw || '').trim();
    let out = '';
    let cursor = 0;
    fences.forEach((fence) => {
      out += String(raw || '').slice(cursor, fence.start);
      cursor = fence.end;
    });
    out += String(raw || '').slice(cursor);
    return out.replace(/\n{3,}/g, '\n\n').trim();
  }

  function messageArtifactsFromText(text) {
    const raw = String(text || '');
    const fences = extractCodeFences(raw);
    const seen = new Set();
    const artifacts = [];
    fences.forEach(({ info, code }, index) => {
      if (!code || !code.trim()) return;
      const kind = artifactKindFor(info, code);
      const name = uniqueArtifactName(filenameFromFence(info, kind.ext, index), seen);
      artifacts.push({
        name,
        kind: kind.ext,
        lang: kind.lang,
        content: code.trim(),
        source: 'fence',
      });
    });

    if (!artifacts.length) {
      const html = extractHtmlFromText(raw);
      if (html) {
        artifacts.push({
          name: uniqueArtifactName('preview.html', seen),
          kind: 'html',
          lang: 'html',
          content: html,
          source: 'html',
        });
      }
    }

    let narrative = narrativeWithoutFences(raw, artifacts.length ? fences : []);
    if (!fences.length && artifacts.length && artifacts[0].source === 'html') {
      narrative = '';
    }

    return {
      artifacts: artifacts.slice(0, 12),
      narrative,
    };
  }

  function extractHtmlFromText(text) {
    const fences = extractCodeFences(text);
    const htmlFence = fences.find(({ info, code }) => artifactKindFor(info, code).ext === 'html');
    if (htmlFence) return htmlFence.code;

    const partialFence = String(text || '').match(/```(?:html|HTML)[^\n]*\n([\s\S]*)$/);
    if (partialFence && !partialFence[1].includes('```')) return partialFence[1].trim();

    const direct = String(text || '').match(/(?:<!doctype html[\s\S]*?<\/html>|<html[\s\S]*?<\/html>)/i);
    if (direct) return direct[0].trim();

    return looksLikeHtmlSnippet(text) ? sliceHtmlLikeText(text) : '';
  }

  function ensurePreviewDocument(html) {
    if (!html) return '';
    const previewTheme = document.body.classList.contains('light') ? 'light' : 'dark';
    const previewGuard = `
<base href="about:srcdoc">
<script>
  document.addEventListener('click', function (event) {
    var link = event.target.closest && event.target.closest('a[href]');
    if (!link) return;
    var href = (link.getAttribute('href') || '').trim();
    var lower = href.toLowerCase();
    var isHash = href.charAt(0) === '#';
    var isExternal = /^https?:\\/\\//i.test(href) || /^\\/\\//.test(href) || lower.startsWith('mailto:') || lower.startsWith('tel:');
    if (!href || href === '#' || lower.startsWith('javascript:')) {
      event.preventDefault();
      return;
    }
    if (isHash) {
      var id = href.slice(1);
      try { id = decodeURIComponent(id); } catch (_) {}
      var target = document.getElementById(id);
      if (target) {
        event.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
      return;
    }
    if (isExternal) {
      event.preventDefault();
      var targetHref = href.charAt(0) === '/' && href.charAt(1) === '/' ? 'https:' + href : href;
      if (window.parent && window.parent !== window) {
        window.parent.postMessage({ type: 'pantheon:open-preview-link', href: targetHref }, '*');
        return;
      }
      window.open(targetHref, '_blank', 'noopener,noreferrer');
      return;
    }
    event.preventDefault();
  }, true);
</script>`;
    if (/<head[\s>]/i.test(html)) {
      return html.replace(/<head([^>]*)>/i, `<head$1>${previewGuard}`);
    }
    if (/<html[\s>]/i.test(html)) {
      return html.replace(/<html([^>]*)>/i, `<html$1><head>${previewGuard}</head>`);
    }
    const fragmentPreviewStyle = `
<style id="pantheon-fragment-preview-style">
  *, *::before, *::after { box-sizing: border-box; }
  html { min-height: 100%; }
  body.pantheon-fragment-preview {
    min-height: 100vh;
    margin: 0;
    display: grid;
    place-items: center;
    padding: 28px;
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    line-height: 1.6;
  }
  body.pantheon-fragment-preview.light {
    color: #1f2430;
    background-color: #f8faff;
    background-image:
      linear-gradient(120deg, rgba(99, 102, 241, 0.13), transparent 38%),
      linear-gradient(240deg, rgba(168, 85, 247, 0.10), transparent 42%),
      linear-gradient(rgba(99, 102, 241, 0.055) 1px, transparent 1px),
      linear-gradient(90deg, rgba(99, 102, 241, 0.055) 1px, transparent 1px);
    background-size: auto, auto, 32px 32px, 32px 32px;
  }
  body.pantheon-fragment-preview.dark {
    color: #eef2ff;
    background-color: #090b16;
    background-image:
      linear-gradient(125deg, rgba(99, 102, 241, 0.16), transparent 40%),
      linear-gradient(250deg, rgba(45, 212, 191, 0.10), transparent 46%),
      linear-gradient(rgba(148, 163, 184, 0.08) 1px, transparent 1px),
      linear-gradient(90deg, rgba(148, 163, 184, 0.08) 1px, transparent 1px);
    background-size: auto, auto, 32px 32px, 32px 32px;
  }
  .pantheon-fragment-card {
    width: min(560px, 100%);
    min-height: 168px;
    display: grid;
    align-content: center;
    gap: 16px;
    padding: 26px;
    border-radius: 8px;
    border: 1px solid rgba(148, 163, 184, 0.28);
    box-shadow: 0 18px 54px rgba(15, 23, 42, 0.12);
    backdrop-filter: blur(18px);
    -webkit-backdrop-filter: blur(18px);
  }
  body.light .pantheon-fragment-card {
    background: rgba(255, 255, 255, 0.72);
  }
  body.dark .pantheon-fragment-card {
    background: rgba(12, 15, 29, 0.72);
    border-color: rgba(148, 163, 184, 0.18);
    box-shadow: 0 18px 54px rgba(0, 0, 0, 0.24);
  }
  .pantheon-fragment-card > :first-child { margin-top: 0; }
  .pantheon-fragment-card > :last-child { margin-bottom: 0; }
  a {
    color: #6366f1;
    font-weight: 700;
    text-decoration: none;
    border-bottom: 1px solid rgba(99, 102, 241, 0.35);
  }
  a:hover { color: #4f46e5; border-bottom-color: currentColor; }
  .pantheon-fragment-card > a:only-child {
    justify-self: start;
    display: inline-flex;
    align-items: center;
    min-height: 42px;
    padding: 0 15px;
    border: 1px solid rgba(99, 102, 241, 0.34);
    border-radius: 8px;
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.14), rgba(168, 85, 247, 0.10));
    box-shadow: 0 8px 22px rgba(99, 102, 241, 0.12);
  }
  body.dark .pantheon-fragment-card > a:only-child {
    color: #a5b4fc;
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.20), rgba(45, 212, 191, 0.10));
    box-shadow: none;
  }
  img, video, canvas, svg, iframe { max-width: 100%; }
  pre {
    max-width: 100%;
    overflow: auto;
    padding: 14px;
    border-radius: 8px;
    background: rgba(15, 23, 42, 0.08);
  }
  code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
</style>`;
    return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  ${previewGuard}
  ${fragmentPreviewStyle}
  <title>Pantheon Preview</title>
</head>
<body class="pantheon-fragment-preview ${previewTheme}">
  <main class="pantheon-fragment-card">
    ${html}
  </main>
</body>
</html>`;
  }

  function collectWorkspaceArtifacts(text) {
    const seen = new Set();
    const artifacts = [];
    extractCodeFences(text).forEach(({ info, code }, index) => {
      if (!code) return;
      const kind = artifactKindFor(info, code);
      const name = uniqueArtifactName(filenameFromFence(info, kind.ext, index), seen);
      artifacts.push({ name, kind: kind.ext, content: code });
    });

    const html = extractHtmlFromText(text);
    if (html && !artifacts.some((item) => item.kind === 'html')) {
      artifacts.unshift({
        name: uniqueArtifactName('preview.html', seen),
        kind: 'html',
        content: html,
      });
    }
    return artifacts.slice(0, 16);
  }

  function displayWorkspacePath(path) {
    return path ? `/${path}` : '/';
  }

  function workspaceFileKind(item) {
    if (item.kind === 'directory') return 'dir';
    const parts = String(item.name || '').split('.');
    return parts.length > 1 ? parts.pop().slice(0, 4) : 'file';
  }

  function languageForFile(name) {
    const ext = String(name || '').split('.').pop().toLowerCase();
    const map = {
      css: 'css',
      html: 'html',
      htm: 'html',
      js: 'javascript',
      json: 'json',
      md: 'markdown',
      py: 'python',
      sh: 'bash',
      toml: 'toml',
      ts: 'typescript',
      tsx: 'typescript',
      yaml: 'yaml',
      yml: 'yaml',
    };
    return map[ext] || 'plaintext';
  }

  function renderWorkspaceBreadcrumb(path) {
    if (!wsFilesPathEl) return;
    const parts = String(path || '').split('/').filter(Boolean);
    const crumbs = [{ label: workspaceRootName || 'workspace', path: '' }];
    parts.forEach((part, index) => {
      crumbs.push({ label: part, path: parts.slice(0, index + 1).join('/') });
    });
    wsFilesPathEl.innerHTML = crumbs.map((crumb, index) => `
      <button class="ws-crumb${index === crumbs.length - 1 ? ' active' : ''}" data-path="${escapeHtml(crumb.path)}" type="button">
        ${escapeHtml(crumb.label)}
      </button>
    `).join('<span class="ws-crumb-sep">/</span>');
  }

  function renderFileInspectorEmpty(label = 'Select a file to preview it here.') {
    workspaceSelectedFileData = null;
    if (wsFileSelectedKind) wsFileSelectedKind.textContent = 'FILE';
    if (wsFileSelectedName) wsFileSelectedName.textContent = 'No file selected';
    if (wsFileSelectedMeta) wsFileSelectedMeta.textContent = 'Select a file to inspect it.';
    [wsCopyFilePathBtn, wsCopyFileContentBtn, wsPreviewFileBtn].forEach((btn) => {
      if (btn) btn.disabled = true;
    });
    if (wsFileViewEl) {
      wsFileViewEl.innerHTML = `<code>${escapeHtml(label)}</code>`;
      wsFileViewEl.dataset.empty = 'true';
    }
  }

  function renderFileInspector(data) {
    workspaceSelectedFileData = data;
    const kind = workspaceFileKind(data).toUpperCase();
    const meta = [
      formatFileSize(data.size),
      data.encoding || '',
      formatModified(data.modified),
    ].filter(Boolean).join(' · ');
    if (wsFileSelectedKind) wsFileSelectedKind.textContent = kind;
    if (wsFileSelectedName) wsFileSelectedName.textContent = data.name || data.path;
    if (wsFileSelectedMeta) wsFileSelectedMeta.textContent = meta || data.path;
    if (wsCopyFilePathBtn) wsCopyFilePathBtn.disabled = false;
    if (wsCopyFileContentBtn) wsCopyFileContentBtn.disabled = false;
    if (wsPreviewFileBtn) wsPreviewFileBtn.disabled = !data.previewable;

    const lang = languageForFile(data.name || data.path);
    wsFileViewEl.dataset.empty = 'false';
    wsFileViewEl.setAttribute('data-lang', lang);
    wsFileViewEl.innerHTML = `<code class="language-${escapeHtml(lang)}">${escapeHtml(data.content || '')}</code>`;
    if (window.hljs) {
      const code = wsFileViewEl.querySelector('code');
      try { window.hljs.highlightElement(code); } catch (_) {}
    }
  }

  function setWorkspacePreviewEmpty(label = 'No preview') {
    if (!wsPreviewFrame || !wsPreviewStatus || !wsPreviewEmpty) return;
    workspacePreviewHtml = '';
    workspacePreviewKind = 'empty';
    workspacePreviewOpenUrl = '';
    setPreviewLabel('preview.html');
    setPreviewHint('');
    wsPreviewFrame.removeAttribute('src');
    wsPreviewFrame.removeAttribute('srcdoc');
    wsPreviewEmpty.hidden = false;
    const strong = wsPreviewEmpty.querySelector('strong');
    if (strong) strong.textContent = label;
    else wsPreviewEmpty.textContent = label;
    wsPreviewStatus.textContent = label;
    updatePreviewControls(false);
    setWorkspaceTabContent('preview', false);
  }

  function renderWorkspacePreview() {
    if (!wsPreviewFrame || !wsPreviewStatus || !wsPreviewEmpty) return;
    const html = extractHtmlFromText(workspaceStreamText);
    if (!html) {
      if (workspacePreviewKind === 'stream' || workspacePreviewKind === 'empty') {
        setWorkspacePreviewEmpty('No preview');
      }
      return;
    }

    const doc = ensurePreviewDocument(html);
    if (doc !== workspacePreviewHtml || workspacePreviewKind !== 'stream') {
      workspacePreviewHtml = doc;
      workspacePreviewKind = 'stream';
      workspacePreviewOpenUrl = '';
      setPreviewLabel('generated-preview.html');
      wsPreviewFrame.removeAttribute('src');
      wsPreviewFrame.srcdoc = doc;
    }
    wsPreviewEmpty.hidden = true;
    wsPreviewStatus.textContent = `generated preview · ${formatBytes(doc)}`;
    setPreviewHint(isCompleteHtmlDocument(html) && !htmlHasAuthorStyle(html) ? 'unstyled HTML' : '');
    updatePreviewControls(true);
    setWorkspaceTabContent('preview', true);

    if (workspaceAutoPreview && !workspacePreviewActivated) {
      activateWorkspaceTab('preview');
      workspacePreviewActivated = true;
    }
  }

  function setWorkspacePreviewFile(item) {
    if (!wsPreviewFrame || !wsPreviewStatus || !wsPreviewEmpty || !item.previewable) return;
    const url = `/api/workspace/preview?path=${encodeURIComponent(item.path)}`;
    workspacePreviewHtml = '';
    workspacePreviewKind = 'file';
    workspacePreviewOpenUrl = url;
    setPreviewLabel(item.name || 'preview.html');
    setPreviewHint(isCompleteHtmlDocument(item.content || '') && !htmlHasAuthorStyle(item.content || '') ? 'unstyled HTML' : '');
    wsPreviewFrame.removeAttribute('srcdoc');
    wsPreviewFrame.src = url;
    wsPreviewEmpty.hidden = true;
    wsPreviewStatus.textContent = `${item.name} · ${item.size || 0} B`;
    updatePreviewControls(true);
    setWorkspaceTabContent('preview', true);
    activateWorkspaceTab('preview');
  }

  function setWorkspacePreviewHtml(html, label = 'message preview') {
    if (!wsPreviewFrame || !wsPreviewStatus || !wsPreviewEmpty) return;
    const doc = ensurePreviewDocument(html);
    workspacePreviewHtml = doc;
    workspacePreviewKind = 'manual';
    workspacePreviewOpenUrl = '';
    setPreviewLabel(`${label}.html`);
    setPreviewHint(isCompleteHtmlDocument(html) && !htmlHasAuthorStyle(html) ? 'unstyled HTML' : '');
    wsPreviewFrame.removeAttribute('src');
    wsPreviewFrame.srcdoc = doc;
    wsPreviewEmpty.hidden = true;
    wsPreviewStatus.textContent = `${label} · ${formatBytes(doc)}`;
    updatePreviewControls(true);
    setWorkspaceTabContent('preview', true);
    openWorkspace();
    activateWorkspaceTab('preview');
  }

  async function currentPreviewHtml() {
    if (workspacePreviewHtml) return workspacePreviewHtml;
    if (workspacePreviewKind === 'file' && workspacePreviewOpenUrl) {
      const resp = await fetch(workspacePreviewOpenUrl);
      if (resp.ok) return await resp.text();
    }
    return '';
  }

  async function downloadCurrentPreview() {
    const html = await currentPreviewHtml();
    if (!html) return;
    const url = URL.createObjectURL(new Blob([html], { type: 'text/html' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = workspacePreviewLabel || 'preview.html';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  async function reloadCurrentPreview() {
    if (!wsPreviewFrame || workspacePreviewKind === 'empty') return;
    if (workspacePreviewKind === 'file' && workspacePreviewOpenUrl) {
      wsPreviewFrame.src = `${workspacePreviewOpenUrl}${workspacePreviewOpenUrl.includes('?') ? '&' : '?'}t=${Date.now()}`;
      return;
    }
    if (workspacePreviewHtml) {
      const html = workspacePreviewHtml;
      wsPreviewFrame.removeAttribute('srcdoc');
      requestAnimationFrame(() => { wsPreviewFrame.srcdoc = html; });
    }
  }

  function htmlTitle(html) {
    const match = String(html || '').match(/<title[^>]*>([\s\S]*?)<\/title>/i);
    return match ? cleanDisplayText(match[1]) : 'Generated HTML page';
  }

  function renderArtifactCard(artifact, label = 'generated file') {
    const kind = artifact.kind || 'txt';
    const lang = artifactLanguage(kind);
    const name = normalizeArtifactName(artifact.name, kind);
    const content = String(artifact.content || '');
    const title = artifact.title || artifactTitle({ ...artifact, name, kind, content });
    const previewButton = kind === 'html'
      ? '<button class="artifact-btn primary" type="button" data-artifact-preview>Preview</button>'
      : '';
    return `
      <div class="artifact-card ${kind}" data-artifact-kind="${escapeHtml(kind)}" data-artifact-name="${escapeHtml(name)}">
        <div class="artifact-main">
          <span class="artifact-icon">${escapeHtml(artifactLabel(kind))}</span>
          <span class="artifact-copy">
            <strong>${escapeHtml(title)}</strong>
            <span>${escapeHtml(name)} · ${escapeHtml(label)} · ${formatBytes(content)}</span>
          </span>
        </div>
        <div class="artifact-actions">
          ${previewButton}
          <button class="artifact-btn" type="button" data-artifact-copy>Copy</button>
          <button class="artifact-btn" type="button" data-artifact-save>Save to Files</button>
        </div>
        <details class="artifact-source">
          <summary>Show source</summary>
          <pre data-lang="${escapeHtml(lang)}"><code class="language-${escapeHtml(lang)} artifact-code">${escapeHtml(content)}</code></pre>
        </details>
      </div>
    `;
  }

  function renderArtifactList(artifacts, label = 'generated file') {
    if (!artifacts.length) return '';
    return `<div class="artifact-list">${artifacts.map((artifact) => renderArtifactCard(artifact, label)).join('')}</div>`;
  }

  function renderHtmlArtifact(html, label = 'HTML page') {
    return renderArtifactCard({
      name: 'preview.html',
      kind: 'html',
      lang: 'html',
      content: html,
      title: htmlTitle(html),
    }, label);
  }

  function renderAssistantContent(text) {
    const raw = String(text == null ? '' : text);
    const { artifacts, narrative } = messageArtifactsFromText(raw);
    if (!artifacts.length) return renderMarkdown(raw);
    const renderedNarrative = narrative ? `<div class="msg-narrative">${renderMarkdown(narrative)}</div>` : '';
    return `${renderedNarrative}${renderArtifactList(artifacts, 'message artifact')}`;
  }

  function previewHtmlFromText(text, label = 'message HTML') {
    const html = extractHtmlFromText(text);
    if (!html) return false;
    setWorkspacePreviewHtml(html, label);
    return true;
  }

  function standaloneHtmlInput(text) {
    const raw = String(text || '').trim();
    if (!raw) return '';
    const html = extractHtmlFromText(raw);
    if (!html) return '';
    if (html === raw) return html;
    if (/^```(?:html|HTML)?[^\n]*\n[\s\S]*```$/.test(raw)) return html;
    return '';
  }

  function renderWorkspaceFiles() {
    if (!wsFilesEl) return;
    renderWorkspaceBreadcrumb(workspaceCwd);
    if (wsFilesUpBtn) wsFilesUpBtn.disabled = workspaceParent == null;
    if (!workspaceFiles.length) {
      wsFilesEl.innerHTML = '<li class="ws-file-empty">No files in this folder</li>';
      setWorkspaceTabContent('files', true);
      return;
    }
    wsFilesEl.innerHTML = workspaceFiles.map((item) => `
      <li class="ws-file${item.path === workspaceSelectedFile ? ' selected' : ''}" data-path="${escapeHtml(item.path)}" data-kind="${escapeHtml(item.kind)}" title="${escapeHtml(item.path || item.name)}">
        <span class="ws-file-kind">${escapeHtml(workspaceFileKind(item))}</span>
        <span class="ws-file-copy">
          <span class="ws-file-name">${escapeHtml(item.name)}</span>
          <span class="ws-file-meta">${escapeHtml(item.kind === 'directory' ? 'folder' : `${formatFileSize(item.size)}${item.previewable ? ' · previewable' : ''}`)}</span>
        </span>
        <span class="ws-file-modified">${escapeHtml(formatModified(item.modified))}</span>
      </li>
    `).join('');
    setWorkspaceTabContent('files', true);
  }

  function syncWorkspaceArtifacts() {
    workspaceArtifacts = collectWorkspaceArtifacts(workspaceStreamText);
    renderWorkspacePreview();
  }

  async function loadWorkspaceInfo() {
    try {
      const resp = await fetch('/api/workspace');
      if (!resp.ok) return;
      const data = await resp.json();
      workspaceRootName = data.name || '';
      if (wsFileViewEl && !wsFileViewEl.dataset.touched) {
        wsFileViewEl.textContent = `Workspace: ${data.root || workspaceRootName || '/'}`;
      }
    } catch (_) {}
  }

  async function loadWorkspaceFiles(path = workspaceCwd) {
    if (!wsFilesEl) return false;
    try {
      wsFilesEl.innerHTML = '<li class="ws-file-empty">Loading files…</li>';
      const resp = await fetch(`/api/workspace/files?path=${encodeURIComponent(path || '')}`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      workspaceCwd = data.cwd || '';
      workspaceParent = data.parent == null ? null : data.parent;
      workspaceFiles = Array.isArray(data.items) ? data.items : [];
      if (!workspaceTerminalCwd) workspaceTerminalCwd = workspaceCwd;
      renderWorkspaceFiles();
      renderWorkspaceTerminalCwd();
      return true;
    } catch (e) {
      wsFilesEl.innerHTML = `<li class="ws-file-empty">Could not load files: ${escapeHtml(e.message || e)}</li>`;
      return false;
    }
  }

  async function readWorkspaceFile(path) {
    if (!path || !wsFileViewEl) return;
    try {
      wsFileViewEl.dataset.touched = 'true';
      wsFileViewEl.textContent = 'Loading file…';
      const resp = await fetch(`/api/workspace/file?path=${encodeURIComponent(path)}`);
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(data.detail || `HTTP ${resp.status}`);
      }
      const data = await resp.json();
      workspaceSelectedFile = data.path;
      renderFileInspector(data);
      renderWorkspaceFiles();
      if (data.previewable) {
        setWorkspacePreviewFile(data);
      }
    } catch (e) {
      wsFileViewEl.textContent = `Could not read file: ${e.message || e}`;
    }
  }

  if (wsFilesPathEl) {
    wsFilesPathEl.addEventListener('click', (event) => {
      const crumb = event.target.closest('[data-path]');
      if (!crumb) return;
      workspaceSelectedFile = '';
      renderFileInspectorEmpty();
      loadWorkspaceFiles(crumb.dataset.path || '');
    });
  }

  if (wsOpenPreviewBtn) {
    wsOpenPreviewBtn.addEventListener('click', () => {
      if (workspacePreviewKind === 'file' && workspacePreviewOpenUrl) {
        window.open(workspacePreviewOpenUrl, '_blank', 'noopener');
        return;
      }
      if (!workspacePreviewHtml) return;
      const url = URL.createObjectURL(new Blob([workspacePreviewHtml], { type: 'text/html' }));
      window.open(url, '_blank', 'noopener');
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    });
  }

  if (wsReloadPreviewBtn) {
    wsReloadPreviewBtn.addEventListener('click', reloadCurrentPreview);
  }

  if (wsDownloadPreviewBtn) {
    wsDownloadPreviewBtn.addEventListener('click', downloadCurrentPreview);
  }

  if (wsPreviewZoom) {
    wsPreviewZoom.addEventListener('change', () => {
      workspacePreviewScale = Number(wsPreviewZoom.value) || 1;
      updatePreviewControls();
    });
  }

  wsPreviewDeviceBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      workspacePreviewDevice = btn.dataset.previewDevice || 'desktop';
      updatePreviewControls();
    });
  });

  if (wsRefreshFilesBtn) {
    wsRefreshFilesBtn.addEventListener('click', () => loadWorkspaceFiles(workspaceCwd));
  }

  if (wsFilesUpBtn) {
    wsFilesUpBtn.addEventListener('click', () => {
      if (workspaceParent != null) {
        workspaceSelectedFile = '';
        renderFileInspectorEmpty();
        loadWorkspaceFiles(workspaceParent);
      }
    });
  }

  if (wsFilesEl) {
    wsFilesEl.addEventListener('click', async (event) => {
      const itemEl = event.target.closest('[data-path]');
      if (!itemEl) return;
      const item = workspaceFiles.find((entry) => entry.path === itemEl.dataset.path);
      if (!item) return;
      if (item.kind === 'directory') {
        workspaceSelectedFile = null;
        renderFileInspectorEmpty();
        await loadWorkspaceFiles(item.path);
        return;
      }
      await readWorkspaceFile(item.path);
    });
  }

  if (wsCopyFilePathBtn) {
    wsCopyFilePathBtn.addEventListener('click', async () => {
      const text = workspaceSelectedFileData?.path || workspaceSelectedFile || '';
      const ok = await copyToClipboard(text);
      flashCopied(wsCopyFilePathBtn, ok ? 'Copied' : 'Failed');
    });
  }

  if (wsCopyFileContentBtn) {
    wsCopyFileContentBtn.addEventListener('click', async () => {
      const ok = await copyToClipboard(workspaceSelectedFileData?.content || '');
      flashCopied(wsCopyFileContentBtn, ok ? 'Copied' : 'Failed');
    });
  }

  if (wsPreviewFileBtn) {
    wsPreviewFileBtn.addEventListener('click', () => {
      if (workspaceSelectedFileData?.previewable) setWorkspacePreviewFile(workspaceSelectedFileData);
    });
  }

  if (wsTerminalHints) {
    wsTerminalHints.addEventListener('click', async (event) => {
      const previewBtn = event.target.closest('[data-terminal-preview]');
      const filesBtn = event.target.closest('[data-terminal-files]');
      const path = previewBtn?.dataset.terminalPreview || filesBtn?.dataset.terminalFiles || '';
      if (!path) return;
      openWorkspace();
      if (filesBtn) {
        await loadWorkspaceFiles(workspacePathDirname(path));
        await readWorkspaceFile(path);
        activateWorkspaceTab('files');
        return;
      }
      await readWorkspaceFile(path);
      activateWorkspaceTab('preview');
    });
  }

  function renderWorkspaceTerminalCwd() {
    if (wsTerminalCwdEl) {
      wsTerminalCwdEl.textContent = displayWorkspacePath(workspaceTerminalCwd);
    }
  }

  function appendWorkspaceConsole(text) {
    if (!text) return;
    workspaceConsoleText += text;
    renderWorkspaceTerminal();
  }

  function addWorkspaceCommandHistory(command) {
    const value = String(command || '').trim();
    if (!value) return;
    if (workspaceCommandHistory[workspaceCommandHistory.length - 1] !== value) {
      workspaceCommandHistory.push(value);
      if (workspaceCommandHistory.length > 80) workspaceCommandHistory.shift();
    }
    workspaceCommandHistoryIndex = workspaceCommandHistory.length;
  }

  function setWorkspaceCommandDraft(value) {
    if (!wsCommandInput) return;
    wsCommandInput.value = value;
    autoResizeWorkspaceCommand();
    requestAnimationFrame(() => {
      wsCommandInput.selectionStart = wsCommandInput.value.length;
      wsCommandInput.selectionEnd = wsCommandInput.value.length;
    });
  }

  function showWorkspaceCommandHistory(direction) {
    if (!wsCommandInput || !workspaceCommandHistory.length) return false;
    const value = wsCommandInput.value || '';
    const cursor = wsCommandInput.selectionStart || 0;
    const singleLine = !value.includes('\n');
    if (!singleLine) {
      if (direction < 0 && cursor > 0) return false;
      if (direction > 0 && cursor < value.length) return false;
    }
    workspaceCommandHistoryIndex = Math.max(
      0,
      Math.min(workspaceCommandHistory.length, workspaceCommandHistoryIndex + direction),
    );
    setWorkspaceCommandDraft(workspaceCommandHistory[workspaceCommandHistoryIndex] || '');
    return true;
  }

  function dangerousWorkspaceCommandLabel(command) {
    const value = String(command || '');
    const checks = [
      { label: 'rm -rf deletes files recursively', re: /\brm\s+-[^\n;|&]*[rR][^\n;|&]*[fF]|\brm\s+-[^\n;|&]*[fF][^\n;|&]*[rR]/ },
      { label: 'git reset --hard discards local changes', re: /\bgit\s+reset\s+--hard\b/ },
      { label: 'git clean can remove untracked files', re: /\bgit\s+clean\s+-[^\n;|&]*[fF]/ },
      { label: 'force checkout can discard file changes', re: /\bgit\s+checkout\s+-[^\n;|&]*[fF]/ },
    ];
    const match = checks.find((item) => item.re.test(value));
    return match ? match.label : '';
  }

  function confirmWorkspaceCommand(command) {
    const label = dangerousWorkspaceCommandLabel(command);
    if (!label) return true;
    return window.confirm(`This command may be destructive:\n\n${label}\n\n${command}\n\nRun it anyway?`);
  }

  function cleanShellPathToken(token) {
    let value = String(token || '').trim().replace(/[;|&]+$/g, '');
    value = value.replace(/^['"]|['"]$/g, '');
    return value.replace(/[;|&]+$/g, '');
  }

  function htmlTargetsFromWorkspaceCommand(command) {
    const value = String(command || '');
    const paths = [];
    const addPath = (token) => {
      const cleaned = cleanShellPathToken(token);
      if (!/\.(?:html|htm)$/i.test(cleaned)) return;
      paths.push(normalizeWorkspacePath(workspaceTerminalCwd, cleaned));
    };

    const redirectRe = /(?:^|[\s;|&])(?:>{1,2})\s*("[^"]+\.(?:html|htm)"|'[^']+\.(?:html|htm)'|[^\s;|&]+\.(?:html|htm))/gi;
    const teeRe = /\btee(?:\s+-a)?\s+("[^"]+\.(?:html|htm)"|'[^']+\.(?:html|htm)'|[^\s;|&]+\.(?:html|htm))/gi;
    const touchRe = /\btouch\s+("[^"]+\.(?:html|htm)"|'[^']+\.(?:html|htm)'|[^\s;|&]+\.(?:html|htm))/gi;
    const copyMoveRe = /\b(?:cp|mv)\s+.+?\s+("[^"]+\.(?:html|htm)"|'[^']+\.(?:html|htm)'|[^\s;|&]+\.(?:html|htm))(?:\s|$)/gi;
    [redirectRe, teeRe, touchRe, copyMoveRe].forEach((re) => {
      let match;
      while ((match = re.exec(value)) !== null) addPath(match[1]);
    });

    return Array.from(new Set(paths.filter(Boolean)));
  }

  function normalizeWorkspacePath(base, target) {
    const raw = String(target || '').trim();
    if (!raw || raw === '~') return '';
    const parts = raw.startsWith('/') ? [] : String(base || '').split('/').filter(Boolean);
    for (const part of raw.replace(/^\/+/, '').split('/')) {
      if (!part || part === '.') continue;
      if (part === '..') parts.pop();
      else parts.push(part);
    }
    return parts.join('/');
  }

  async function handleWorkspaceCd(command) {
    const match = String(command || '').trim().match(/^cd(?:\s+(.+))?$/);
    if (!match) return false;
    const nextPath = normalizeWorkspacePath(workspaceTerminalCwd, match[1] || '');
    const previousCwd = workspaceCwd;
    const ok = await loadWorkspaceFiles(nextPath);
    if (ok) {
      workspaceTerminalCwd = workspaceCwd;
      renderWorkspaceTerminalCwd();
      pushWorkspaceLine(`cwd changed to ${displayWorkspacePath(workspaceTerminalCwd)}`);
    } else {
      workspaceCwd = previousCwd;
      pushWorkspaceLine(`cd failed: ${displayWorkspacePath(nextPath)}`);
    }
    return true;
  }

  function parseSSEFrame(frame) {
    if (!frame.trim()) return null;
    const lines = frame.split('\n');
    let event = 'message';
    let dataLines = [];
    for (const line of lines) {
      if (line.startsWith('event:')) event = line.slice(6).trim();
      else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
    }
    try {
      return { event, data: JSON.parse(dataLines.join('\n')) };
    } catch (_) {
      return null;
    }
  }

  async function runWorkspaceCommand(command) {
    const trimmed = String(command || '').trim();
    if (!trimmed || workspaceTerminalRunning) return;
    const htmlTargets = htmlTargetsFromWorkspaceCommand(trimmed);
    clearWorkspaceTerminalHints();
    appendWorkspaceConsole(`\n${displayWorkspacePath(workspaceTerminalCwd)} $ ${trimmed}\n`);
    if (await handleWorkspaceCd(trimmed)) return;

    workspaceTerminalRunning = true;
    if (wsRunCommandBtn) wsRunCommandBtn.disabled = true;
    if (wsCommandInput) wsCommandInput.disabled = true;
    setWorkspaceState('Terminal', 'running');

    try {
      const resp = await fetch('/api/workspace/terminal/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          command: trimmed,
          cwd: workspaceTerminalCwd,
          timeout_seconds: 120,
        }),
      });
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(data.detail || `HTTP ${resp.status}`);
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
          const parsed = parseSSEFrame(frame);
          if (!parsed) continue;
          const { event, data } = parsed;
          if (event === 'stdout') appendWorkspaceConsole(data.text || '');
          else if (event === 'stderr') appendWorkspaceConsole(data.text || '');
          else if (event === 'error') appendWorkspaceConsole(`\n${data.message || 'terminal error'}\n`);
          else if (event === 'exit') {
            appendWorkspaceConsole(`\n[exit ${data.returncode}]\n`);
            const returnCode = Number(data.returncode);
            setWorkspaceState(returnCode === 0 ? 'Ready' : 'Terminal error', returnCode === 0 ? 'ready' : 'error');
            await loadWorkspaceFiles(workspaceCwd);
            if (returnCode === 0) renderWorkspaceTerminalHtmlHint(htmlTargets);
          }
        }
      }
    } catch (e) {
      appendWorkspaceConsole(`\nTerminal error: ${e.message || e}\n`);
      setWorkspaceState('Error', 'error');
    } finally {
      workspaceTerminalRunning = false;
      if (wsRunCommandBtn) wsRunCommandBtn.disabled = false;
      if (wsCommandInput) {
        wsCommandInput.disabled = false;
        wsCommandInput.focus();
      }
    }
  }

  if (wsCommandForm) {
    wsCommandForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const command = wsCommandInput ? wsCommandInput.value : '';
      const trimmed = String(command || '').trim();
      if (!trimmed || workspaceTerminalRunning) return;
      if (!confirmWorkspaceCommand(trimmed)) return;
      addWorkspaceCommandHistory(trimmed);
      if (wsCommandInput) wsCommandInput.value = '';
      autoResizeWorkspaceCommand();
      activateWorkspaceTab('terminal');
      await runWorkspaceCommand(trimmed);
    });
  }

  function autoResizeWorkspaceCommand() {
    if (!wsCommandInput) return;
    wsCommandInput.style.height = 'auto';
    wsCommandInput.style.height = `${Math.min(wsCommandInput.scrollHeight, 140)}px`;
  }

  if (wsCommandInput) {
    wsCommandInput.addEventListener('input', autoResizeWorkspaceCommand);
    wsCommandInput.addEventListener('keydown', (event) => {
      if (event.key === 'ArrowUp' && !event.shiftKey && !event.metaKey && !event.ctrlKey && !event.altKey) {
        if (showWorkspaceCommandHistory(-1)) event.preventDefault();
        return;
      }
      if (event.key === 'ArrowDown' && !event.shiftKey && !event.metaKey && !event.ctrlKey && !event.altKey) {
        if (showWorkspaceCommandHistory(1)) event.preventDefault();
        return;
      }
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        wsCommandForm.dispatchEvent(new Event('submit'));
      }
    });
  }

  function resetWorkspace() {
    workspaceStreamText = '';
    workspaceConsoleText = '';
    mcpWorkspaceCalls.clear();
    clearWorkspaceTerminalHints();
    workspacePreviewHtml = '';
    workspacePreviewKind = 'empty';
    workspacePreviewOpenUrl = '';
    workspaceArtifacts = [];
    workspaceAutoPreview = false;
    workspacePreviewActivated = false;
    resetWorkspaceTask();
    setWorkspaceState('Idle');
    setWorkspaceTabContent('preview', false);
    setWorkspacePlan('', false);
    wsStepsEl.innerHTML = '<li class="ws-step-empty">No steps yet</li>';
    renderWorkspaceTerminal();
    setWorkspacePreviewEmpty('No preview');
    activateWorkspaceTab('activity');
  }
  resetWorkspace();

  function skillBadgeMarkup(skills = [], className = 'skill-badge') {
    return (Array.isArray(skills) ? skills : [])
      .filter((item) => item && (item.id || item.name))
      .map((item) => {
        const id = item.id || item.name;
        const label = item.name || id;
        const invocation = item.invocation ? ` · ${item.invocation}` : '';
        return `<span class="${className}" title="$${escapeHtml(id)}${escapeHtml(invocation)}">${escapeHtml(label)}</span>`;
      })
      .join('');
  }

  function addWorkspaceStep(role, task, skills = []) {
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
        <div class="ws-step-head">
          <span class="ws-step-role" style="color: ${meta.color}">${meta.icon} ${escapeHtml(meta.label)}</span>
          <span class="ws-step-status">running</span>
        </div>
        <div class="ws-step-task">${escapeHtml(task || 'thinking…')}</div>
        ${skills.length ? `<div class="ws-step-skills">${skillBadgeMarkup(skills, 'ws-step-skill')}</div>` : ''}
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

  function setWorkspaceStepNote(stepEl, text = '', tone = '') {
    if (!stepEl) return;
    let note = stepEl.querySelector('[data-step-note]');
    if (!note) {
      note = document.createElement('div');
      note.className = 'ws-step-note';
      note.dataset.stepNote = '';
      stepEl.querySelector('.ws-step-text')?.appendChild(note);
    }
    note.classList.toggle('mcp-error', tone === 'error');
    note.classList.toggle('mcp-result', tone === 'result');
    note.textContent = String(text || '').slice(0, 700);
    note.hidden = !text;
  }

  function addWorkspaceAgentMessage(data = {}) {
    const empty = wsStepsEl.querySelector('.ws-step-empty');
    if (empty) empty.remove();
    const messageType = String(data.type || 'handoff').toLowerCase();
    const labels = {
      handoff: 'handoff',
      question: 'question',
      review_request: 'review request',
      revision_request: 'revision request',
      result: 'result',
    };
    const from = metaFor(data.from_role || 'hermes');
    const to = metaFor(data.to_role || 'hermes');
    const li = document.createElement('li');
    li.className = `ws-step ws-agent-message message-${messageType}`;
    li.dataset.messageId = data.message_id || '';
    li.dataset.messageType = messageType;
    const criteria = Array.isArray(data.acceptance_criteria)
      ? data.acceptance_criteria.filter(Boolean)
      : [];
    li.innerHTML = `
      <span class="ws-step-dot"></span>
      <div class="ws-step-text">
        <div class="ws-step-head">
          <span class="ws-step-role">${escapeHtml(from.label)} <span class="ws-agent-arrow">→</span> ${escapeHtml(to.label)}</span>
          <span class="ws-step-status">${escapeHtml(labels[messageType] || messageType)}</span>
        </div>
        <div class="ws-step-task">${escapeHtml(data.summary || 'Structured collaboration message')}</div>
        ${data.deliverable ? `<div class="ws-agent-deliverable">Deliverable: ${escapeHtml(data.deliverable)}</div>` : ''}
        ${criteria.length ? `<div class="ws-agent-criteria">Done when: ${criteria.map((item) => escapeHtml(item)).join(' · ')}</div>` : ''}
      </div>
    `;
    wsStepsEl.appendChild(li);
    wsStepsEl.scrollTop = wsStepsEl.scrollHeight;
    return li;
  }

  function ensureWorkspaceMcpCall(data = {}) {
    const callId = String(data.call_id || '');
    if (callId && mcpWorkspaceCalls.has(callId)) return mcpWorkspaceCalls.get(callId);
    const role = data.role || 'local';
    const server = data.server_name || data.server_id || 'MCP server';
    const tool = data.tool_title || data.tool || 'tool';
    const stepEl = addWorkspaceStep(role, `${server} · ${tool}`);
    stepEl.classList.add('ws-step-mcp');
    if (callId) stepEl.dataset.mcpCallId = callId;
    const roleEl = stepEl.querySelector('.ws-step-role');
    if (roleEl) roleEl.textContent = `MCP · ${metaFor(role).label}`;
    const statusEl = stepEl.querySelector('.ws-step-status');
    if (statusEl) statusEl.textContent = 'calling';
    const argumentsText = JSON.stringify(data.arguments || {});
    if (argumentsText !== '{}') setWorkspaceStepNote(stepEl, `Arguments: ${argumentsText}`, 'result');
    if (callId) mcpWorkspaceCalls.set(callId, stepEl);
    return stepEl;
  }

  function updateWorkspaceMcpCall(data = {}, status = 'calling') {
    const callId = String(data.call_id || '');
    const stepEl = ensureWorkspaceMcpCall(data);
    const taskEl = stepEl.querySelector('.ws-step-task');
    if (data.server_name && taskEl) {
      taskEl.textContent = `${data.server_name} · ${data.tool_title || data.tool || 'tool'}`;
    }
    if (status === 'approval') {
      stepEl.classList.add('approval');
      const statusEl = stepEl.querySelector('.ws-step-status');
      if (statusEl) statusEl.textContent = 'approval needed';
      setWorkspaceStepNote(stepEl, `${mcpRiskLabel({ risk: data.risk })}. Review the request to continue.`);
      return stepEl;
    }
    if (status === 'calling') {
      stepEl.classList.remove('approval');
      const statusEl = stepEl.querySelector('.ws-step-status');
      if (statusEl) statusEl.textContent = 'calling';
      return stepEl;
    }
    const duration = Number(data.duration_ms || 0);
    updateWorkspaceStepElement(stepEl, status === 'error' ? 'error' : 'done', duration);
    if (status === 'error') {
      setWorkspaceStepNote(stepEl, data.error || 'MCP tool call failed', 'error');
    } else if (data.result_preview) {
      setWorkspaceStepNote(
        stepEl,
        `${data.result_preview}${data.truncated ? ' [truncated]' : ''}`,
        'result',
      );
    }
    if (callId) mcpWorkspaceCalls.delete(callId);
    return stepEl;
  }

  function updateWorkspaceStepElement(li, status, durationMs = 0) {
    if (!li) return null;
    li.classList.remove('running', 'long-wait');
    li.classList.add(status);
    const statusEl = li.querySelector('.ws-step-status');
    if (statusEl) statusEl.textContent = status;
    if (li._tickInterval) clearInterval(li._tickInterval);
    const t = li.querySelector('[data-time]');
    if (t && durationMs) t.textContent = `${(durationMs / 1000).toFixed(1)}s`;
    const note = li.querySelector('[data-step-note]');
    if (note) note.hidden = true;
    return li;
  }

  function updateWorkspaceStepProgress(li, data = {}) {
    if (!li) return;
    const detail = String(data.detail || '').trim();
    const waiting = Number(data.waiting_seconds || 0);
    const taskEl = li.querySelector('.ws-step-task');
    const statusEl = li.querySelector('.ws-step-status');
    let note = li.querySelector('[data-step-note]');
    if (!note) {
      note = document.createElement('div');
      note.className = 'ws-step-note';
      note.dataset.stepNote = '';
      note.hidden = true;
      li.querySelector('.ws-step-text')?.appendChild(note);
    }
    if (detail && taskEl) taskEl.textContent = detail;
    const roleLabel = metaFor(li.dataset.role || '').label || 'The agent';
    if (statusEl) statusEl.textContent = waiting >= 10 ? 'model wait' : 'running';
    li.classList.toggle('long-wait', waiting >= 90);
    if (waiting >= 90) {
      note.textContent = `${roleLabel} is still waiting for the model. The workflow is running and does not need your reply. You can Stop and retry.`;
      note.hidden = false;
    } else if (waiting >= 30) {
      note.textContent = `${roleLabel} is waiting for the model response. No reply is required.`;
      note.hidden = false;
    } else {
      note.hidden = true;
    }
  }

  function updateWorkspaceStep(role, status, durationMs) {
    const safeRole = role && window.CSS && CSS.escape ? CSS.escape(role) : String(role || '').replace(/"/g, '\\"');
    const li = (safeRole ? wsStepsEl.querySelector(`.ws-step[data-role="${safeRole}"]:last-of-type`) : null) ||
               (safeRole ? wsStepsEl.querySelector(`.ws-step[data-role="${safeRole}"]`) : null) ||
               wsStepsEl.querySelector('.ws-step.running:last-of-type') ||
               wsStepsEl.querySelector('.ws-step.running');
    return updateWorkspaceStepElement(li, status, durationMs);
  }

  function finishRunningWorkspaceSteps(status = 'done') {
    wsStepsEl.querySelectorAll('.ws-step.running').forEach((li) => {
      li.classList.remove('running');
      li.classList.add(status);
      const statusEl = li.querySelector('.ws-step-status');
      if (statusEl) statusEl.textContent = status;
      if (li._tickInterval) clearInterval(li._tickInterval);
    });
  }

  // ---------- Conversations ----------
  const SESSIONS_KEY = 'pantheon:chat-sessions';
  let conversationRevision = null;
  let conversationSyncTimer = null;
  let conversationSyncing = false;

  function mergeConversations(local, remote) {
    const merged = new Map();
    for (const session of [...remote, ...local]) {
      const previous = merged.get(session.id);
      if (!previous || (session.updatedAt || 0) > (previous.updatedAt || 0)) merged.set(session.id, session);
    }
    return [...merged.values()].sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
  }

  async function loadConversations() {
    try {
      const resp = await fetch('/api/conversations');
      const data = await resp.json();
      if (!resp.ok || data.schema_version !== 1 || !Array.isArray(data.sessions)) throw data;
      conversationRevision = data.revision;
      const browserSessions = data.sessions.length && sessions.length === 1 &&
        sessions[0].title === 'New chat' && !sessions[0].messages.length ? [] : sessions;
      const merged = mergeConversations(browserSessions, data.sessions);
      const needsSave = JSON.stringify(merged) !== JSON.stringify(data.sessions);
      sessions = merged;
      const selected = sessions.some((s) => s.id === activeSessionId) ? activeSessionId : sessions[0]?.id;
      renderSessions();
      if (selected && !isStreaming) activateSession(selected, true);
      infoConversationPill.textContent = 'saved';
      infoConversationStatus.textContent = `${sessions.length} conversations saved on this device. Export a backup before moving computers.`;
      if (needsSave) scheduleConversationSync();
    } catch (e) {
      infoConversationPill.textContent = 'browser only';
      infoConversationStatus.textContent = 'Could not save to the local server. Chats remain in this browser; export a backup.';
    }
  }

  function scheduleConversationSync() {
    if (conversationRevision === null) return;
    clearTimeout(conversationSyncTimer);
    conversationSyncTimer = setTimeout(flushConversationSync, 700);
  }

  async function flushConversationSync() {
    if (conversationSyncing || conversationRevision === null) return;
    conversationSyncing = true;
    const snapshot = JSON.stringify(sessions);
    try {
      const resp = await fetch('/api/conversations', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ schema_version: 1, expected_revision: conversationRevision, sessions: JSON.parse(snapshot) }),
      });
      if (resp.status === 409) {
        const latest = await fetch('/api/conversations');
        if (!latest.ok) throw Error('Could not reconcile conversations');
        const data = await latest.json();
        conversationRevision = data.revision;
        sessions = mergeConversations(sessions, data.sessions);
        try { localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions)); } catch (_) {}
        renderSessions();
        scheduleConversationSync();
        return;
      }
      if (!resp.ok) throw Error((await resp.json()).detail || 'Save failed');
      const data = await resp.json();
      conversationRevision = data.revision;
      infoConversationPill.textContent = 'saved';
      infoConversationStatus.textContent = `${sessions.length} conversations saved on this device. Export a backup before moving computers.`;
      if (snapshot !== JSON.stringify(sessions)) scheduleConversationSync();
    } catch (e) {
      infoConversationPill.textContent = 'save error';
      infoConversationStatus.textContent = `Could not save to the local server: ${e.message || 'unknown error'}. Export a backup.`;
    } finally {
      conversationSyncing = false;
    }
  }

  function downloadConversationBackup() {
    saveActiveSession();
    const backup = JSON.stringify({ schema_version: 1, exported_at: new Date().toISOString(), sessions }, null, 2);
    const blob = new Blob([backup], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `pantheon-conversations-${new Date().toISOString().slice(0, 10)}.json`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  async function importConversationBackup(file) {
    if (!file || file.size > 10 * 1024 * 1024) {
      infoConversationStatus.textContent = 'Choose a Pantheon JSON backup smaller than 10 MB.';
      return;
    }
    try {
      const data = JSON.parse(await file.text());
      if (data.schema_version !== 1 || !Array.isArray(data.sessions) || data.sessions.length > 200) throw Error('Unsupported backup format');
      const imported = data.sessions.map((session) => {
        if (!session || typeof session.title !== 'string' || session.title.length > 200 ||
            typeof session.mode !== 'string' || session.mode.length > 100 ||
            typeof session.overrides !== 'object' || session.overrides === null || Array.isArray(session.overrides) ||
            !Number.isInteger(session.createdAt) || session.createdAt < 0 ||
            !Number.isInteger(session.updatedAt) || session.updatedAt < 0 ||
            !Array.isArray(session.messages) || session.messages.length > 2000 ||
            !session.messages.every((m) => m && ['user', 'assistant', 'error', 'hermes', 'hephaestus', 'athena', 'apollo', 'chronos'].includes(m.role) && typeof m.text === 'string' && m.text.length <= 200000)) {
          throw Error('Invalid conversation in backup');
        }
        // Imports are copies; existing conversations are never overwritten.
        return { ...session, id: createSession().id };
      });
      if (sessions.length + imported.length > 200) throw Error('Import would exceed 200 conversations');
      saveActiveSession();
      sessions = [...imported, ...sessions].sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
      persistSessions();
      renderSessions();
      infoConversationStatus.textContent = `Imported ${imported.length} conversations. Existing chats were preserved.`;
    } catch (e) {
      infoConversationStatus.textContent = `Import failed: ${e.message || 'invalid file'}`;
    } finally {
      infoBackupFile.value = '';
    }
  }
  infoBackupExport?.addEventListener('click', downloadConversationBackup);
  infoBackupImport?.addEventListener('click', () => infoBackupFile.click());
  infoBackupFile?.addEventListener('change', () => importConversationBackup(infoBackupFile.files?.[0]));
  infoConversationRetry?.addEventListener('click', loadConversations);

  function cloneJSON(value, fallback) {
    try { return JSON.parse(JSON.stringify(value == null ? fallback : value)); }
    catch (_) { return fallback; }
  }

  function createSession(title = 'New chat') {
    const now = Date.now();
    return {
      id: `chat-${now}-${Math.random().toString(16).slice(2)}`,
      title,
      mode: 'auto',
      overrides: {},
      messages: [],
      createdAt: now,
      updatedAt: now,
    };
  }

  function titleFromPrompt(text) {
    const normalized = String(text || '').replace(/\s+/g, ' ').trim();
    if (!normalized) return '';
    return normalized.length > 34 ? `${normalized.slice(0, 34)}...` : normalized;
  }

  function sessionTitleFromMessages(messages, fallback = 'New chat') {
    const firstUser = (messages || []).find((item) => item.role === 'user' && item.text);
    return firstUser ? titleFromPrompt(firstUser.text) : fallback;
  }

  function sessionModeLabel(session) {
    const mode = session.mode || 'auto';
    if (mode === 'auto') return 'Auto routing';
    if (mode === 'multi') return 'Multi-role council';
    if (mode.startsWith('role:')) return `${metaFor(mode.slice(5)).label} direct`;
    return mode;
  }

  function sessionMeta(session) {
    const overrideCount = Object.keys(session.overrides || {}).length;
    return overrideCount
      ? `${sessionModeLabel(session)} · ${overrideCount} model override${overrideCount > 1 ? 's' : ''}`
      : sessionModeLabel(session);
  }

  function loadSessions() {
    let loaded = [];
    try {
      loaded = JSON.parse(localStorage.getItem(SESSIONS_KEY) || '[]');
    } catch (_) {
      loaded = [];
    }
    if (!Array.isArray(loaded) || !loaded.length) {
      const legacyMessages = loadHistory();
      const first = createSession(legacyMessages.length ? 'Current chat' : 'New chat');
      first.messages = legacyMessages;
      first.title = sessionTitleFromMessages(legacyMessages, first.title);
      loaded = [first];
    }
    sessions = loaded.map((session) => ({
      ...createSession(),
      ...session,
      mode: session.mode || 'auto',
      overrides: session.overrides || {},
      messages: Array.isArray(session.messages) ? session.messages : [],
    })).sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
    sessions.forEach((session) => {
      if ((!session.messages || !session.messages.length) && /^New chat \d+$/.test(session.title || '')) {
        session.title = 'New chat';
      }
    });
    activeSessionId = sessions[0]?.id || null;
  }

  function persistSessions() {
    try { localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions)); } catch (_) {}
    scheduleConversationSync();
  }

  function renderSessions() {
    if (!chatListEl) return;
    chatListEl.innerHTML = '';
    for (const session of sessions) {
      const btn = document.createElement('button');
      btn.className = 'chat-row';
      btn.type = 'button';
      btn.dataset.session = session.id;
      btn.classList.toggle('active', session.id === activeSessionId);
      btn.innerHTML = `
        <span class="chat-row-mark"></span>
        <span class="chat-row-body">
          <span class="chat-row-title">${escapeHtml(session.title || 'New chat')}</span>
          <span class="chat-row-meta">${escapeHtml(sessionMeta(session))}</span>
        </span>
      `;
      btn.addEventListener('click', () => activateSession(session.id));
      chatListEl.appendChild(btn);
    }
  }

  function saveActiveSession() {
    if (!activeSessionId || isRestoringSession) return;
    const session = sessions.find((item) => item.id === activeSessionId);
    if (!session) return;
    const messages = snapshotChat();
    session.messages = messages;
    session.mode = currentMode;
    session.overrides = cloneJSON(roleOverrides, {});
    session.title = sessionTitleFromMessages(messages, session.title || 'New chat');
    session.updatedAt = Date.now();
    persistSessions();
  }

  function titleActiveSessionFromPrompt(prompt) {
    const session = sessions.find((item) => item.id === activeSessionId);
    if (!session) return;
    const hasUserMessage = (session.messages || []).some((item) => item.role === 'user');
    if (hasUserMessage) return;
    const title = titleFromPrompt(prompt);
    if (!title) return;
    session.title = title;
    session.updatedAt = Date.now();
    persistSessions();
    renderSessions();
  }

  function restoreMessages(messages) {
    chatEl.innerHTML = '';
    if (!messages || !messages.length) {
      recreateWelcome();
      return;
    }
    messages.forEach((item, i) => {
      if (item.role === 'user') {
        addUserMessage(item.text, { attachments: item.attachments || [] });
      } else if (item.role === 'error') {
        addErrorMessage(item.text);
      } else {
        addMessage(item.role, renderAssistantContent(item.text), {
          icon: metaFor(item.role).icon,
          label: metaFor(item.role).label,
          roleColor: metaFor(item.role).color,
          rawText: item.text,
        });
      }
      const last = chatEl.lastElementChild;
      if (last) last.style.setProperty('--msg-delay', `${Math.min(i, 8) * 40}ms`);
      decorateMessageCopyBtn(last);
      decorateMessageHtmlPreviewBtn(last);
      decorateHtmlPreviewBtns(last);
    });
  }

  function activateSession(sessionId, force = false) {
    if (isStreaming || (!force && sessionId === activeSessionId)) return;
    if (!force) saveActiveSession();
    const session = sessions.find((item) => item.id === sessionId);
    if (!session) return;
    activeSessionId = session.id;
    roleOverrides = cloneJSON(session.overrides, {});
    isRestoringSession = true;
    setMode(session.mode || 'auto');
    restoreMessages(session.messages || []);
    resetWorkspace();
    inputEl.placeholder = currentMode === 'role:chronos' ? 'Ask Chronos to schedule a task…' : 'Ask the Pantheon…';
    renderSettingsModels();
    isRestoringSession = false;
    renderSessions();
    persistSessions();
  }

  function startNewSession() {
    if (isStreaming) return;
    saveActiveSession();
    const session = createSession('New chat');
    sessions.unshift(session);
    activeSessionId = session.id;
    roleOverrides = {};
    isRestoringSession = true;
    setMode('auto');
    turns = [];
    chatEl.innerHTML = '';
    recreateWelcome();
    resetWorkspace();
    inputEl.placeholder = 'Ask the Pantheon…';
    renderSettingsModels();
    isRestoringSession = false;
    saveActiveSession();
    renderSessions();
  }

  newChatBtn.addEventListener('click', startNewSession);

  function recreateWelcome() {
    const w = document.createElement('div');
    w.className = 'welcome';
    w.id = 'welcome';

    // Build a compact role switcher from the loaded roles.
    const godCards = roles.map((r) => {
      const meta = metaFor(r.name);
      const tagline = r.note ? 'Scheduling' : roleKind(r.name);
      return `
        <div class="welcome-god" style="--god-color: ${meta.color}" title="${escapeHtml(r.description || meta.label)}">
          ${avatarHtml(meta, 'wg-icon')}
          <span class="wg-copy">
            <span class="wg-name" style="color: ${meta.color}">${escapeHtml(meta.label)}</span>
            <span class="wg-role">${escapeHtml(tagline)}</span>
          </span>
        </div>
      `;
    }).join('');

    w.innerHTML = `
      <p class="welcome-eyebrow">New session</p>
      <h2>Start with a concrete task.</h2>
      <p class="welcome-tagline">Choose a mode on the left, or use one of these prompts to test the workflow.</p>
      ${godCards ? `<div class="welcome-pantheon">${godCards}</div>` : ''}
      <div class="welcome-divider">Examples</div>
      <div class="welcome-examples">
        <button class="example-chip" data-prompt="Write a Python function to check if a string is a palindrome">Write a palindrome checker</button>
        <button class="example-chip" data-prompt="Compare PostgreSQL and MongoDB for a new project">Compare Postgres vs MongoDB</button>
        <button class="example-chip" data-prompt="Write a Midjourney prompt for a cyberpunk shrine at night">Draft a cyberpunk shrine prompt</button>
        <button class="example-chip" data-prompt="调研 Python Web 框架趋势并写一个 FastAPI demo">调研并写 FastAPI demo</button>
      </div>
    `;
    chatEl.appendChild(w);
    // Re-bind example chips
    w.querySelectorAll('.example-chip').forEach((chip) => {
      chip.addEventListener('click', () => {
        hideSlashCommandMenu();
        inputEl.value = chip.dataset.prompt || '';
        autoResize();
        inputEl.focus();
      });
    });
    // Click a god card to switch to that role.
    w.querySelectorAll('.welcome-god').forEach((card, i) => {
      card.style.cursor = 'pointer';
      card.addEventListener('click', () => {
        if (roles[i]) {
          setMode(`role:${roles[i].name}`);
          inputEl.focus();
        }
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
    const isAssistantRole = role !== 'user' && role !== 'error';
    const modelInfo = roleModelInfo(role);
    const status = opts.status || (isAssistantRole ? 'ready' : role === 'error' ? 'error' : 'sent');
    const duration = formatDuration(opts.durationMs);
    msg.className = isAssistantRole ? `msg assistant ${role}` : `msg ${role}`;
    msg.dataset.role = role;
    msg.dataset.label = opts.label || meta.label;
    msg.dataset.status = status;
    if (modelInfo?.model) msg.dataset.model = modelInfo.model;
    if (opts.rawText != null) msg.dataset.rawText = String(opts.rawText);
    msg.style.setProperty('--god-color', opts.roleColor || meta.color);
    msg.innerHTML = `
      ${messageAvatarHtml(meta, opts.icon)}
      <div class="msg-body">
        <div class="msg-meta">
          <div class="msg-meta-main">
            <span class="msg-role" style="color: ${opts.roleColor || meta.color}">${escapeHtml(opts.label || meta.label)}</span>
            <span class="msg-kind">${escapeHtml(opts.kind || messageKindLabel(role))}</span>
          </div>
          <div class="msg-meta-side">
            ${messageModelHtml(role)}
            <span class="msg-duration" ${duration ? '' : 'hidden'}>${escapeHtml(duration)}</span>
            <span class="msg-status" data-status="${escapeHtml(status)}">${escapeHtml(status)}</span>
            <span class="msg-time">${new Date().toLocaleTimeString()}</span>
            <span class="msg-actions"></span>
          </div>
        </div>
        <div class="msg-content">${contentHTML}</div>
      </div>
    `;
    chatEl.appendChild(msg);
    chatEl.scrollTop = chatEl.scrollHeight;
    highlightCode(msg);
    return msg;
  }

  const USER_MESSAGE_COLLAPSE_LINES = 6;

  function decorateUserMessageCollapse(msg) {
    if (!msg?.classList?.contains('user')) return;
    const task = msg.querySelector('.task-message');
    const text = task?.querySelector('p');
    if (!task || !text || task.dataset.collapseReady === 'true') return;
    task.dataset.collapseReady = 'true';

    requestAnimationFrame(() => {
      const styles = getComputedStyle(text);
      const fontSize = Number.parseFloat(styles.fontSize) || 14;
      const lineHeight = Number.parseFloat(styles.lineHeight) || fontSize * 1.55;
      if (text.scrollHeight <= lineHeight * USER_MESSAGE_COLLAPSE_LINES + 2) return;

      task.classList.add('is-collapsed');
      const button = document.createElement('button');
      button.className = 'task-expand-btn';
      button.type = 'button';
      button.textContent = 'Show more';
      button.setAttribute('aria-expanded', 'false');
      button.addEventListener('click', () => {
        const collapsed = task.classList.toggle('is-collapsed');
        button.textContent = collapsed ? 'Show more' : 'Show less';
        button.setAttribute('aria-expanded', String(!collapsed));
      });
      task.appendChild(button);
    });
  }

  function addUserMessage(text, opts = {}) {
    const html = opts.htmlArtifact ? opts.htmlArtifact : '';
    const attachments = (opts.attachments || []).map(attachmentPublicMeta);
    const attachmentHtml = renderUserAttachments(attachments);
    const skillHtml = opts.skill
      ? `<span class="task-skill" title="Explicit skill">${escapeHtml(opts.skill)}</span>`
      : '';
    const content = html
      ? `<div class="task-message">${skillHtml}<p>${escapeHtml(text)}</p></div>${attachmentHtml}${renderHtmlArtifact(html, opts.artifactLabel || 'input HTML')}`
      : `<div class="task-message">${skillHtml}<p>${escapeHtml(text)}</p></div>${attachmentHtml}`;
    const msg = addMessage('user', content, {
      icon: 'U',
      label: 'You',
      roleColor: 'var(--accent)',
      rawText: text,
    });
    if (attachments.length) msg.dataset.attachments = JSON.stringify(attachments);
    decorateUserMessageCollapse(msg);
    return msg;
  }

  function addErrorMessage(text) {
    return addMessage('error', `<div>${escapeHtml(text)}</div>`, {
      icon: '!', label: 'Error', roleColor: 'var(--accent-err)'
    });
  }

  function parseNumberedChoiceReply(text) {
    const source = String(text || '');
    if (!/(?:推荐|建议选择|recommended|recommend|请选择|请回复|choose|reply)/i.test(source)) {
      return null;
    }
    const choices = {};
    source.split(/\r?\n/).forEach((line) => {
      const normalized = line
        .replace(/^\s*[-*]\s*/, '')
        .replace(/^\s*#{1,6}\s*/, '')
        .replace(/\*\*/g, '')
        .trim();
      const match = normalized.match(
        /^(?:(?:选项|方案|option|choice)\s*)?([1-4])\s*[.、:：)\]]\s*(.+)$/i,
      );
      if (!match || choices[match[1]]) return;
      choices[match[1]] = match[2].trim();
    });
    return choices['1'] && choices['2'] ? choices : null;
  }

  function continuationForNumericChoice(text) {
    const selection = String(text || '').trim();
    if (!/^[1-4]$/.test(selection)) return null;

    const messages = Array.from(chatEl.querySelectorAll('.msg'));
    let assistantIndex = -1;
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      if (messages[index].classList.contains('assistant')) {
        assistantIndex = index;
        break;
      }
      if (messages[index].classList.contains('user')) return null;
    }
    if (assistantIndex < 0) return null;

    const assistant = messages[assistantIndex];
    const previousAnswer = String(
      assistant.dataset.rawText || assistant.querySelector('.msg-content')?.innerText || '',
    ).trim();
    const choices = parseNumberedChoiceReply(previousAnswer);
    if (!choices || !choices[selection]) return null;

    let originalTask = '';
    for (let index = assistantIndex - 1; index >= 0; index -= 1) {
      if (!messages[index].classList.contains('user')) continue;
      originalTask = String(
        messages[index].dataset.rawText || messages[index].querySelector('.msg-content')?.innerText || '',
      ).trim();
      break;
    }
    if (!originalTask) return null;

    const selectedChoice = choices[selection];
    return {
      selection,
      selectedChoice,
      agentTask: `Continue the task using the user's numbered selection.\n\nOriginal task:\n${originalTask.slice(0, 8000)}\n\nPrevious answer with choices:\n${previousAnswer.slice(0, 8000)}\n\nUser selected:\n${selection}. ${selectedChoice}\n\nContinue from this selection. Do not ask the user to repeat the original context.`,
    };
  }

  function createStepBlock(roleName, skills = []) {
    const meta = metaFor(roleName);
    const msg = addMessage(roleName, `
      <div class="step-block" data-step-block>
        <div class="step-block-header">
          <span class="step-role" style="color: ${meta.color}">${escapeHtml(roleKind(roleName))}</span>
          ${skillBadgeMarkup(skills, 'msg-skill')}
          <span class="step-status streaming">streaming…</span>
        </div>
        <div class="step-block-body" data-step-body>
          <span class="streaming-cursor"></span>
        </div>
      </div>
    `, { icon: meta.icon, label: meta.label, roleColor: meta.color, status: 'running' });
    if (skills.length) msg.dataset.skills = JSON.stringify(skills);
    return msg;
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

  function updateMessageStatus(msgEl, status, durationMs = 0) {
    if (!msgEl) return;
    msgEl.dataset.status = status;
    const statusEl = msgEl.querySelector('.msg-status');
    if (statusEl) {
      statusEl.textContent = status;
      statusEl.dataset.status = status;
    }
    const durationEl = msgEl.querySelector('.msg-duration');
    const duration = formatDuration(durationMs);
    if (durationEl) {
      durationEl.textContent = duration;
      durationEl.hidden = !duration;
    }
  }

  function backfillMessageModelPills(root = chatEl) {
    if (!root) return;
    root.querySelectorAll('.msg.assistant').forEach((msgEl) => {
      if (msgEl.querySelector('.msg-model')) return;
      const roleName = msgEl.dataset.role || '';
      const modelInfo = roleModelInfo(roleName);
      if (!modelInfo) return;
      const side = msgEl.querySelector('.msg-meta-side');
      if (!side) return;
      const modelEl = document.createElement('span');
      modelEl.className = 'msg-model';
      modelEl.title = modelInfo.model;
      modelEl.textContent = `${modelInfo.label}${modelInfo.overridden ? ' · override' : ''}`;
      const before = side.querySelector('.msg-duration') || side.querySelector('.msg-status') || side.firstChild;
      side.insertBefore(modelEl, before);
      msgEl.dataset.model = modelInfo.model;
    });
  }

  function finalizeStep(msgEl, finalContent) {
    const body = msgEl.querySelector('[data-step-body]');
    const status = msgEl.querySelector('.step-status');
    if (body) {
      const cursor = body.querySelector('.streaming-cursor');
      if (cursor) cursor.remove();
      if (finalContent != null) {
        msgEl.dataset.rawText = String(finalContent);
        body.innerHTML = renderAssistantContent(finalContent);
        highlightCode(body);
      }
    }
    if (status) {
      status.classList.remove('streaming');
      status.textContent = 'done';
      status.style.color = 'var(--accent-3)';
    }
    updateMessageStatus(msgEl, 'done');
  }

  // ---------- SSE send ----------
  function setSendState(streaming) {
    sendBtn.disabled = false;
    sendBtn.classList.toggle('is-stopping', streaming);
    sendBtn.querySelector('.send-text').textContent = streaming ? 'Stop' : 'Send';
    updatePromptEnhanceButton();
  }

  function updatePromptEnhanceButton() {
    if (!enhancePromptBtn) return;
    const canUndo = Boolean(
      promptBeforeEnhance && enhancedPromptValue && inputEl.value === enhancedPromptValue,
    );
    enhancePromptBtn.disabled = isStreaming || promptEnhancing;
    enhancePromptBtn.classList.toggle('is-loading', promptEnhancing);
    enhancePromptBtn.classList.toggle('is-active', canUndo);
    enhancePromptBtn.setAttribute('aria-busy', String(promptEnhancing));
    enhancePromptBtn.setAttribute('aria-pressed', String(canUndo));
    const label = promptEnhancing
      ? 'Enhancing prompt'
      : canUndo
        ? 'Undo prompt enhancement'
        : 'Enhance prompt with the configured Hermes model';
    enhancePromptBtn.title = label;
    enhancePromptBtn.setAttribute('aria-label', label);
  }

  function clearPromptEnhancement({ clearStatus = false } = {}) {
    const hadEnhancement = Boolean(promptBeforeEnhance || enhancedPromptValue);
    promptBeforeEnhance = '';
    enhancedPromptValue = '';
    updatePromptEnhanceButton();
    if (clearStatus && hadEnhancement) setComposerStatus('');
  }

  async function enhanceCurrentPrompt() {
    if (isStreaming || promptEnhancing) return;
    if (promptBeforeEnhance && inputEl.value === enhancedPromptValue) {
      const original = promptBeforeEnhance;
      clearPromptEnhancement({ clearStatus: true });
      inputEl.value = original;
      autoResize();
      inputEl.focus();
      inputEl.setSelectionRange(original.length, original.length);
      setComposerStatus('Original prompt restored', 'ok');
      return;
    }

    const sourcePrompt = inputEl.value;
    if (!sourcePrompt.trim()) {
      setComposerStatus('Write a prompt before enhancing it', 'warn');
      inputEl.focus();
      return;
    }

    promptEnhancing = true;
    updatePromptEnhanceButton();
    setComposerStatus('Enhancing prompt with Hermes…', '', true);
    try {
      const response = await fetch('/api/prompt/enhance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: sourcePrompt, mode: currentMode }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
      const enhanced = String(data.prompt || '').trim();
      if (!enhanced) throw new Error('The model returned an empty prompt');
      if (inputEl.value !== sourcePrompt) {
        setComposerStatus('Draft changed; enhancement was not applied', 'warn');
        return;
      }

      promptBeforeEnhance = sourcePrompt;
      enhancedPromptValue = enhanced;
      inputEl.value = enhanced;
      autoResize();
      inputEl.focus();
      inputEl.setSelectionRange(enhanced.length, enhanced.length);
      setComposerStatus('Prompt enhanced · click the wand to undo', 'ok', true);
    } catch (error) {
      setComposerStatus(error.message || 'Could not enhance prompt', 'error', true);
    } finally {
      promptEnhancing = false;
      updatePromptEnhanceButton();
    }
  }

  function taskLooksPreviewable(task) {
    return /\b(html|web|website|webpage|page|landing|frontend|ui)\b/i.test(task) ||
           /网页|页面|网站|前端|落地页/.test(task);
  }

  async function sendAsk(task, opts = {}) {
    if (isStreaming) return;
    const agentTask = opts.agentTask || task;
    const attachments = opts.attachments || [];
    isStreaming = true;
    abortCtrl = new AbortController();
    setSendState(true);
    providerDot.classList.add('connecting');
    clearGodHighlight();

    titleActiveSessionFromPrompt(task);
    addUserMessage(task, { attachments, skill: opts.skill || '' });
    resetWorkspace();
    startWorkspaceTask(task, workspaceModeLabel());
    workspaceAutoPreview = taskLooksPreviewable(agentTask);
    openWorkspace();
    setWorkspaceState('Running', 'running');
    pushWorkspaceLine(`Task started: ${titleFromPrompt(task)}`);
    if (opts.skill) pushWorkspaceLine(`Explicit skill requested: $${opts.skill}`);
    if (opts.numericChoice) {
      pushWorkspaceLine(
        `Continuing with choice ${opts.numericChoice.selection}: ${opts.numericChoice.selectedChoice}`,
      );
    }
    const startTime = Date.now();
    const initialRole = currentMode.startsWith('role:') ? currentMode.slice(5) : 'hermes';
    const initialDetail = currentMode.startsWith('role:')
      ? `Preparing ${metaFor(initialRole).label} direct task`
      : 'Analyzing the task and building the execution plan';
    setWorkspacePlan(initialDetail, true);
    let planningWorkspaceStep = addWorkspaceStep(initialRole, initialDetail);
    let currentWorkspaceStep = planningWorkspaceStep;

    // Determine initial highlight
    if (currentMode === 'auto')        highlightGod('hermes');
    else if (currentMode === 'multi')  highlightGod('hermes');
    else if (currentMode.startsWith('role:')) highlightGod(currentMode.slice(5));

    let currentMsg = null;
    let currentStepStreamed = false;

    try {
      const resp = await fetch('/api/ask/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task: agentTask,
          user_task: task,
          mode: currentMode,
          skill: opts.skill || undefined,
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
            pushWorkspaceLine('Stream connected');
            if (data.memory_saved_count) {
              pushWorkspaceLine(`Memory saved from user message: ${data.memory_saved_count}`);
              loadMemory();
            }
            if (data.memory_suggestion_count) {
              pushWorkspaceLine(`Memory suggestion created: ${data.memory_suggestion_count}`);
              loadMemory();
            }
            if (data.memory_count) {
              pushWorkspaceLine(`Memory matched: ${data.memory_count}`);
            }
            break;
          case 'phase': {
            const stage = data.stage || 'running';
            const labels = {
              preparing: 'Preparing',
              planning: 'Planning',
              executing: 'Running',
              synthesizing: 'Synthesizing',
            };
            setWorkspaceState(labels[stage] || 'Running', 'running');
            if ((stage === 'preparing' || stage === 'planning') && planningWorkspaceStep) {
              updateWorkspaceStepProgress(planningWorkspaceStep, {
                detail: data.detail,
                waiting_seconds: 0,
              });
              const statusEl = planningWorkspaceStep.querySelector('.ws-step-status');
              if (statusEl) statusEl.textContent = stage;
            }
            pushWorkspaceLine(`${labels[stage] || 'Running'}: ${data.detail || stage}`);
            break;
          }
          case 'progress': {
            const liveStep = currentWorkspaceStep || planningWorkspaceStep;
            updateWorkspaceStepProgress(liveStep, data);
            const index = Number(data.index);
            const total = Number(data.total);
            const stepLabel = Number.isFinite(index) && total > 0
              ? ` · Step ${index + 1}/${total}`
              : '';
            const waiting = Number(data.waiting_seconds || 0);
            setWorkspaceState(waiting >= 10 ? `Model wait${stepLabel}` : `Running${stepLabel}`, 'running');
            break;
          }
          case 'plan':
            // Display Hermes's plan in workspace
            if (data.plan || (Array.isArray(data.steps) && data.steps.length)) {
              setWorkspacePlanPayload(data);
              pushWorkspaceLine('Hermes planned the route');
            }
            if (planningWorkspaceStep) {
              updateWorkspaceStepElement(planningWorkspaceStep, 'done');
              if (currentWorkspaceStep === planningWorkspaceStep) currentWorkspaceStep = null;
              planningWorkspaceStep = null;
            }
            if (data.memory_count) {
              pushWorkspaceLine(`Memory context injected: ${data.memory_count}`);
            }
            if (Array.isArray(data.skills) && data.skills.length) {
              pushWorkspaceLine(`Skills selected: ${data.skills.map((item) => `$${item.id || item.name}`).join(', ')}`);
            }
            break;
          case 'step_start': {
            const r = data.role;
            highlightGod(r);
            if (currentMsg) finalizeStep(currentMsg, null);  // close previous
            currentMsg = createStepBlock(r, data.skills || []);
            currentStepStreamed = false;
            currentWorkspaceStep = addWorkspaceStep(
              r,
              data.task || data.description || '',
              data.skills || [],
            );
            const index = Number(data.index);
            const total = Number(data.total);
            if (Number.isFinite(index) && total > 0) {
              setWorkspaceState(`Step ${index + 1}/${total}`, 'running');
            }
            pushWorkspaceLine(`${metaFor(r).label} started: ${data.task || data.description || 'thinking'}`);
            break;
          }
          case 'agent_message': {
            addWorkspaceAgentMessage(data);
            const from = metaFor(data.from_role || 'hermes').label;
            const to = metaFor(data.to_role || 'hermes').label;
            const label = String(data.type || 'handoff').replaceAll('_', ' ');
            pushWorkspaceLine(`${from} → ${to}: ${label}`);
            break;
          }
          case 'step_chunk': {
            if (currentMsg) appendToStep(currentMsg, data.text || '');
            if (data.text) {
              currentStepStreamed = true;
              appendWorkspaceStream(data.text);
            }
            break;
          }
          case 'mcp_call_start': {
            updateWorkspaceMcpCall(data, 'calling');
            setWorkspaceState('Using MCP', 'running');
            pushWorkspaceLine(`${metaFor(data.role).label} called ${data.server_id} · ${data.tool}`);
            break;
          }
          case 'mcp_approval_required': {
            updateWorkspaceMcpCall(data, 'approval');
            setWorkspaceState('Approval needed', 'running');
            pushWorkspaceLine(`Approval needed: ${data.server_name || data.server_id} · ${data.tool}`);
            openMcpApproval(data);
            break;
          }
          case 'mcp_approval_resolved': {
            if (data.approved) {
              updateWorkspaceMcpCall(data, 'calling');
              setWorkspaceState('Using MCP', 'running');
              pushWorkspaceLine(`Allowed once: ${data.tool}`);
            } else {
              const stepEl = ensureWorkspaceMcpCall(data);
              stepEl.classList.remove('approval');
              const statusEl = stepEl.querySelector('.ws-step-status');
              if (statusEl) statusEl.textContent = 'denied';
              setWorkspaceStepNote(stepEl, data.reason || 'Denied by user', 'error');
              pushWorkspaceLine(`Denied: ${data.tool}`);
            }
            if (pendingMcpApproval?.approval_id === data.approval_id) {
              pendingMcpApproval = null;
              closeMcpApproval();
            }
            break;
          }
          case 'mcp_call_done': {
            updateWorkspaceMcpCall(data, 'done');
            setWorkspaceState('Running', 'running');
            pushWorkspaceLine(`MCP finished: ${data.server_id} · ${data.tool}`);
            break;
          }
          case 'mcp_call_error': {
            updateWorkspaceMcpCall(data, 'error');
            setWorkspaceState('Running', 'running');
            pushWorkspaceLine(`MCP failed: ${data.tool} · ${data.error || 'unknown error'}`);
            break;
          }
          case 'step_done': {
            if (currentMsg) finalizeStep(currentMsg, data.content);
            if (currentMsg) updateMessageStatus(currentMsg, 'done', data.duration_ms || 0);
            if (!currentStepStreamed && data.content) appendWorkspaceStream(data.content);
            if (data.content) previewHtmlFromText(data.content, 'generated HTML');
            if (currentMsg) decorateMessageHtmlPreviewBtn(currentMsg);
            updateWorkspaceStepElement(currentWorkspaceStep, 'done', data.duration_ms || 0);
            currentWorkspaceStep = null;
            if (extractHtmlFromText(data.content || '')) addWorkspaceStepActionByRole(data.role, 'Preview', 'preview');
            pushWorkspaceLine(`${metaFor(data.role).label} finished`);
            syncWorkspaceArtifacts();
            if (data.role === 'chronos') loadChronosJobs({ silent: true });
            break;
          }
          case 'step_error': {
            if (currentMsg) {
              finalizeStep(currentMsg, '❌ ' + (data.error || 'unknown'));
              updateMessageStatus(currentMsg, 'error');
              const s = currentMsg.querySelector('.step-status');
              if (s) { s.style.color = 'var(--accent-err)'; s.textContent = 'error'; }
            }
            updateWorkspaceStepElement(currentWorkspaceStep, 'error', data.duration_ms || 0);
            currentWorkspaceStep = null;
            pushWorkspaceLine(`${metaFor(data.role).label} failed: ${data.error || 'unknown error'}`);
            setWorkspaceState('Error', 'error');
            break;
          }
          case 'summary_start':
            if (currentMsg) finalizeStep(currentMsg, null);
            currentMsg = createStepBlock('hermes', data.skills || []);
            currentStepStreamed = false;
            currentWorkspaceStep = addWorkspaceStep(
              'hermes',
              data.task || data.description || 'Synthesize final answer',
              data.skills || [],
            );
            setWorkspaceState('Synthesizing', 'running');
            pushWorkspaceLine('Hermes started final synthesis');
            break;
          case 'summary_chunk':
            if (currentMsg) appendToStep(currentMsg, data.text || '');
            if (data.text) {
              currentStepStreamed = true;
              appendWorkspaceStream(data.text);
            }
            break;
          case 'summary_done':
            if (currentMsg) finalizeStep(currentMsg, data.content);
            if (currentMsg) updateMessageStatus(currentMsg, 'done', data.duration_ms || 0);
            if (!currentStepStreamed && data.content) appendWorkspaceStream(data.content);
            if (data.content) previewHtmlFromText(data.content, 'generated HTML');
            if (currentMsg) decorateMessageHtmlPreviewBtn(currentMsg);
            updateWorkspaceStepElement(currentWorkspaceStep, 'done', data.duration_ms || 0);
            currentWorkspaceStep = null;
            if (extractHtmlFromText(data.content || '')) addWorkspaceStepActionByRole('hermes', 'Preview', 'preview');
            pushWorkspaceLine('Hermes finished final synthesis');
            syncWorkspaceArtifacts();
            break;
          case 'done':
            providerDot.classList.remove('connecting');
            providerDot.classList.add('online');
            finishRunningWorkspaceSteps('done');
            setWorkspaceState(workspacePreviewHtml ? 'Preview ready' : 'Ready', 'ready');
            stopWorkspaceTaskTimer('done');
            pushWorkspaceLine('Task complete');
            if (data.memory_saved_count) {
              pushWorkspaceLine(`Memory saved from user message: ${data.memory_saved_count}`);
            }
            if (data.memory_suggestion_count) {
              pushWorkspaceLine(`Memory suggestion created: ${data.memory_suggestion_count}`);
            }
            if (data.memory_count) {
              pushWorkspaceLine(`Memory context used: ${data.memory_count}`);
            }
            loadChronosJobs({ silent: true });
            loadMemory();
            break;
          case 'error':
            addErrorMessage(data.message || 'Unknown error');
            pushWorkspaceLine(`Request failed: ${data.message || 'Unknown error'}`);
            finishRunningWorkspaceSteps('error');
            setWorkspaceState('Error', 'error');
            stopWorkspaceTaskTimer('error');
            break;
        }
      }
    } catch (e) {
      if (e.name === 'AbortError') {
        pushWorkspaceLine('Task stopped');
        finishRunningWorkspaceSteps('stopped');
        setWorkspaceState('Stopped', 'idle');
        stopWorkspaceTaskTimer('stopped');
      } else {
        console.error(e);
        addErrorMessage(String(e.message || e));
        pushWorkspaceLine(`Request failed: ${e.message || e}`);
        finishRunningWorkspaceSteps('error');
        setWorkspaceState('Error', 'error');
        stopWorkspaceTaskTimer('error');
      }
    } finally {
      if (pendingMcpApproval && !mcpApprovalResolving) {
        await decideMcpApproval(false);
      }
      clearGodHighlight();
      isStreaming = false;
      abortCtrl = null;
      setSendState(false);
      providerDot.classList.remove('connecting');
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
      console.log(`[pantheon] request completed in ${elapsed}s`);
    }
  }

  function previewLocalHtmlInput(text, html) {
    titleActiveSessionFromPrompt(text);
    addUserMessage(text, { htmlArtifact: html, artifactLabel: 'input HTML' });
    resetWorkspace();
    startWorkspaceTask('Local HTML preview', 'No agent call');
    openWorkspace();
    setWorkspacePlan('Render the pasted HTML fragment locally\nPrepare a sandboxed preview\nKeep external links clickable', true);
    const step = addWorkspaceStep('local', 'Render pasted HTML fragment');
    setWorkspacePreviewHtml(html, 'input HTML');
    updateWorkspaceStep('local', 'done', 0);
    addWorkspaceStepAction(step, 'Preview', 'preview');
    setWorkspaceState('Preview ready', 'ready');
    stopWorkspaceTaskTimer('ready');
    pushWorkspaceLine('Local HTML preview ready');
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
      backfillMessageModelPills();
      if (chatEl.querySelector('#welcome') && !chatEl.querySelector('.msg')) {
        chatEl.innerHTML = '';
        recreateWelcome();
      }
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

  function setVoiceButtonState(listening) {
    voiceListening = listening;
    if (!voiceBtn) return;
    voiceBtn.classList.toggle('is-active', listening);
    voiceBtn.setAttribute('aria-pressed', listening ? 'true' : 'false');
    voiceBtn.title = listening ? 'Stop voice input' : 'Voice input';
  }

  function speechRecognitionCtor() {
    return window.SpeechRecognition || window.webkitSpeechRecognition || null;
  }

  function selectedVoiceLanguage() {
    const prefs = loadPrefs();
    const value = VOICE_LANGUAGES.has(prefs.voiceLanguage) ? prefs.voiceLanguage : 'auto';
    return value === 'auto' ? (navigator.language || 'zh-CN') : value;
  }

  function voiceLanguageLabel(value) {
    const labels = {
      auto: 'Auto',
      'zh-CN': '中文（普通话）',
      'zh-TW': '中文（繁體）',
      'en-US': 'English (US)',
      'en-GB': 'English (UK)',
      'ja-JP': '日本語',
      'ko-KR': '한국어',
      'fr-FR': 'Français',
      'de-DE': 'Deutsch',
      'es-ES': 'Español',
    };
    return labels[value] || value || 'Auto';
  }

  function ensureSpeechRecognition() {
    if (voiceRecognition) return voiceRecognition;
    const Recognition = speechRecognitionCtor();
    if (!Recognition) return null;
    voiceRecognition = new Recognition();
    voiceRecognition.continuous = true;
    voiceRecognition.interimResults = true;
    voiceRecognition.lang = selectedVoiceLanguage();
    voiceRecognition.onstart = () => {
      setVoiceButtonState(true);
      setComposerStatus('Listening...', 'ok', true);
    };
    voiceRecognition.onresult = (event) => {
      let interim = '';
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        const transcript = result[0]?.transcript || '';
        if (result.isFinal) voiceFinalText += `${transcript.trim()} `;
        else interim += transcript;
      }
      const pieces = [voiceBaseText, voiceFinalText.trim(), interim.trim()].filter(Boolean);
      inputEl.value = pieces.join(voiceBaseText ? ' ' : '');
      autoResize();
    };
    voiceRecognition.onerror = (event) => {
      voiceLastError = true;
      const message = event.error === 'not-allowed'
        ? 'Microphone permission denied'
        : `Voice input error: ${event.error || 'unknown'}`;
      setComposerStatus(message, 'error');
      setVoiceButtonState(false);
    };
    voiceRecognition.onend = () => {
      const hadText = Boolean(voiceFinalText.trim());
      setVoiceButtonState(false);
      if (hadText) setComposerStatus('Voice text inserted', 'ok');
      else if (!voiceLastError) setComposerStatus('No voice captured', 'warn');
      voiceLastError = false;
      voiceBaseText = '';
      voiceFinalText = '';
    };
    return voiceRecognition;
  }

  function startVoiceInput() {
    const recognition = ensureSpeechRecognition();
    if (!recognition) {
      setComposerStatus('Voice input is not supported in this browser', 'warn');
      return;
    }
    voiceBaseText = inputEl.value.trimEnd();
    voiceFinalText = '';
    voiceLastError = false;
    const language = selectedVoiceLanguage();
    setComposerStatus(`Starting voice input · ${voiceLanguageLabel(language)}`, '', true);
    try {
      recognition.lang = language;
      recognition.start();
    } catch (_) {
      setComposerStatus('Voice input is already starting', 'warn');
    }
  }

  function stopVoiceInput() {
    if (!voiceRecognition) return;
    try { voiceRecognition.stop(); } catch (_) {}
    setVoiceButtonState(false);
  }

  function openWorkspaceTab(tabName) {
    openWorkspace();
    activateWorkspaceTab(tabName);
  }

  function openSettingsPane(tabName) {
    openSettings();
    activateSettingsTab(tabName);
    if (tabName === 'security') loadAuthStatus();
    if (tabName === 'memory') loadMemory();
    if (tabName === 'integrations') loadIntegrations();
  }

  function slashRoleAliases(roleName) {
    const aliases = {
      hermes: ['/her', '/router'],
      hephaestus: ['/he', '/build', '/code'],
      athena: ['/ath', '/research'],
      apollo: ['/apo', '/creative'],
      chronos: ['/schedule', '/timer'],
    };
    return aliases[roleName] || [];
  }

  function slashCommandItems() {
    const baseCommands = [
      {
        id: 'help',
        command: '/help',
        title: 'Browse commands',
        hint: 'Show this command menu',
        keywords: 'commands menu slash',
        keepInput: true,
        run: () => {
          inputEl.value = '/';
          autoResize();
          updateSlashCommandMenu();
          setComposerStatus('Type after / to filter commands', 'ok', true);
        },
      },
      {
        id: 'new',
        command: '/new',
        aliases: ['/chat'],
        title: 'New chat',
        hint: 'Start a fresh conversation',
        keywords: 'session conversation reset',
        run: () => {
          clearPendingAttachments();
          startNewSession();
          setComposerStatus('New chat started', 'ok');
        },
      },
      {
        id: 'auto',
        command: '/auto',
        title: 'Auto routing',
        hint: 'Let Hermes choose the best route',
        keywords: 'mode route hermes',
        run: () => {
          setMode('auto');
          setComposerStatus('Mode switched to Auto', 'ok');
        },
      },
      {
        id: 'multi',
        command: '/multi',
        aliases: ['/council'],
        title: 'Multi-role council',
        hint: 'Force a multi-agent collaboration',
        keywords: 'mode collaboration council',
        run: () => {
          setMode('multi');
          setComposerStatus('Mode switched to Multi-role', 'ok');
        },
      },
      {
        id: 'workspace',
        command: '/workspace',
        aliases: ['/ws'],
        title: 'Workspace',
        hint: 'Open Activity in the right panel',
        keywords: 'activity right panel',
        run: () => {
          openWorkspaceTab('activity');
          setComposerStatus('Workspace opened', 'ok');
        },
      },
      {
        id: 'preview',
        command: '/preview',
        title: 'Preview',
        hint: 'Open the webpage preview panel',
        keywords: 'html web page iframe',
        run: () => {
          openWorkspaceTab('preview');
          setComposerStatus('Preview opened', 'ok');
        },
      },
      {
        id: 'files',
        command: '/files',
        title: 'Files',
        hint: 'Browse generated workspace files',
        keywords: 'workspace artifacts saved',
        run: () => {
          openWorkspaceTab('files');
          setComposerStatus('Files opened', 'ok');
        },
      },
      {
        id: 'terminal',
        command: '/terminal',
        aliases: ['/term'],
        title: 'Terminal',
        hint: 'Open the workspace terminal',
        keywords: 'shell command run',
        run: () => {
          openWorkspaceTab('terminal');
          setComposerStatus('Terminal opened', 'ok');
        },
      },
      {
        id: 'settings',
        command: '/settings',
        aliases: ['/config'],
        title: 'Settings',
        hint: 'Open local configuration',
        keywords: 'setup model display security info',
        run: () => {
          openSettingsPane('setup');
          setComposerStatus('Settings opened', 'ok');
        },
      },
      {
        id: 'setup',
        command: '/setup',
        title: 'Setup',
        hint: 'Configure provider, model, and API key',
        keywords: 'api key provider local config',
        run: () => {
          openSettingsPane('setup');
          setComposerStatus('Setup opened', 'ok');
        },
      },
      {
        id: 'models',
        command: '/models',
        title: 'Models',
        hint: 'Adjust per-god model overrides',
        keywords: 'roles gods provider override',
        run: () => {
          openSettingsPane('models');
          setComposerStatus('Models opened', 'ok');
        },
      },
      {
        id: 'security',
        command: '/security',
        title: 'Security',
        hint: 'Manage the local login lock',
        keywords: 'login password session auth',
        run: () => {
          openSettingsPane('security');
          setComposerStatus('Security opened', 'ok');
        },
      },
      {
        id: 'memory',
        command: '/memory',
        aliases: ['/memories'],
        title: 'Memory',
        hint: 'Open saved long-term memories',
        keywords: 'remember recall context long term',
        run: () => {
          openSettingsPane('memory');
          setComposerStatus('Memory opened', 'ok');
        },
      },
      {
        id: 'integrations',
        command: '/integrations',
        aliases: ['/ext'],
        title: 'Integrations',
        hint: 'Open MCP, plugins, skills, and channels',
        keywords: 'mcp plugins skills channels extensions',
        run: () => {
          openIntegrationsSection('mcp');
          setComposerStatus('Integrations opened', 'ok');
        },
      },
      {
        id: 'mcp',
        command: '/mcp',
        title: 'MCP',
        hint: 'Open external tool servers',
        keywords: 'tools data source server integrations',
        run: () => {
          openIntegrationsSection('mcp');
          setComposerStatus('MCP integrations opened', 'ok');
        },
      },
      {
        id: 'plugins',
        command: '/plugins',
        title: 'Plugins',
        hint: 'Open installed capability packs',
        keywords: 'extensions packs integrations',
        run: () => {
          openIntegrationsSection('plugins');
          setComposerStatus('Plugins opened', 'ok');
        },
      },
      {
        id: 'skills',
        command: '/skills',
        title: 'Skills',
        hint: 'Open reusable agent skills',
        keywords: 'instructions methods slash commands',
        run: () => {
          openIntegrationsSection('skills');
          setComposerStatus('Skills opened', 'ok');
        },
      },
      {
        id: 'skill',
        command: '/skill',
        title: 'Use a skill',
        hint: 'Choose an installed workflow for the next task',
        keywords: 'invoke workflow explicit',
        keepInput: true,
        run: () => {
          inputEl.value = '/';
          autoResize();
          updateSlashCommandMenu();
          setComposerStatus('Choose a Skill below, then describe the task', 'ok', true);
        },
      },
      {
        id: 'channels',
        command: '/channels',
        title: 'Channels',
        hint: 'Open chat and webhook entry points',
        keywords: 'dingtalk wecom feishu webhook message',
        run: () => {
          openIntegrationsSection('channels');
          setComposerStatus('Channels opened', 'ok');
        },
      },
      {
        id: 'remember',
        command: '/remember',
        title: 'Remember',
        hint: 'Save the text after this command',
        keywords: 'memory save note preference',
        run: () => {
          openSettingsPane('memory');
          memoryContent?.focus();
          setComposerStatus('Type /remember followed by what Pantheon should keep', 'ok', true);
        },
      },
      {
        id: 'forget',
        command: '/forget',
        title: 'Forget',
        hint: 'Delete a memory by id',
        keywords: 'memory delete remove',
        run: () => {
          openSettingsPane('memory');
          setComposerStatus('Copy a memory id, then use /forget <id>', 'warn', true);
        },
      },
      {
        id: 'display',
        command: '/display',
        title: 'Display',
        hint: 'Change theme, text size, and voice language',
        keywords: 'theme font voice language',
        run: () => {
          openSettingsPane('display');
          setComposerStatus('Display opened', 'ok');
        },
      },
      {
        id: 'info',
        command: '/info',
        title: 'Info',
        hint: 'Show versions, paths, and diagnostics',
        keywords: 'about version support diagnostics',
        run: () => {
          openSettingsPane('info');
          setComposerStatus('Info opened', 'ok');
        },
      },
      {
        id: 'attach',
        command: '/attach',
        aliases: ['/file'],
        title: 'Attach file',
        hint: 'Open the file picker',
        keywords: 'upload attachment',
        run: () => {
          runComposerToolAction('attach');
          setComposerStatus('Choose files to attach', 'ok', true);
        },
      },
      {
        id: 'voice',
        command: '/voice',
        aliases: ['/mic'],
        title: 'Voice input',
        hint: 'Start or stop speech-to-text',
        keywords: 'microphone dictation speech',
        run: () => {
          runComposerToolAction('voice');
        },
      },
      {
        id: 'export',
        command: '/export',
        title: 'Export chat',
        hint: 'Download the current chat as Markdown',
        keywords: 'download markdown',
        run: () => {
          exportChat();
          setComposerStatus('Markdown export created', 'ok');
        },
      },
    ];

    const roleCommands = roles
      .map((role) => {
        const meta = metaFor(role.name);
        return {
          id: `role-${role.name}`,
          command: `/${role.name}`,
          aliases: slashRoleAliases(role.name),
          title: role.name === 'chronos' ? 'Chronos scheduling' : `${meta.label} direct mode`,
          hint: role.name === 'chronos'
            ? 'Send the next task to the local scheduler'
            : `Send the next task directly to ${meta.label}`,
          keywords: `${meta.label} ${role.name} god role direct ${roleKind(role.name)}`,
          run: () => {
            setMode(`role:${role.name}`);
            setComposerStatus(`Mode switched to ${meta.label}`, 'ok');
          },
        };
      });

    const reserved = new Set(
      [...baseCommands, ...roleCommands]
        .flatMap((item) => [item.command, ...(item.aliases || [])])
        .map((command) => command.toLowerCase())
    );
    const skillCommands = (integrationData.skills?.items || [])
      .filter((item) => item.enabled !== false && item.id && !reserved.has(`/${item.id}`.toLowerCase()))
      .map((item) => ({
        id: `skill-${item.id}`,
        command: `/${item.id}`,
        title: item.name || item.id,
        hint: `${(item.roles || []).map(integrationRoleLabel).join(' + ') || 'Pantheon'} · ${item.allow_implicit_invocation === false ? 'explicit only' : 'auto available'}`,
        keywords: `skill workflow ${(item.trigger_terms || []).join(' ')} ${(item.roles || []).join(' ')}`,
        keepInput: true,
        run: () => prepareSkillInvocation(item.id),
      }));

    return [...baseCommands, ...skillCommands, ...roleCommands];
  }

  function slashCommandMatchState() {
    if (!inputEl || !slashCommandMenu) return null;
    const raw = inputEl.value || '';
    const cursor = inputEl.selectionStart == null ? raw.length : inputEl.selectionStart;
    if (cursor !== raw.length || !raw.startsWith('/') || raw.includes('\n')) return null;
    const query = raw.slice(1);
    if (/\s/.test(query)) return null;
    if (/[/.]/.test(query)) return null;
    const normalizedQuery = query.toLowerCase();
    const items = slashCommandItems().filter((item) => {
      if (!normalizedQuery) return true;
      const commands = [item.command, ...(item.aliases || [])].map((value) => value.toLowerCase());
      if (commands.some((value) => value.slice(1).startsWith(normalizedQuery))) return true;
      const haystack = [
        item.title,
        item.hint,
        item.keywords,
        ...commands,
      ].join(' ').toLowerCase();
      return haystack.includes(normalizedQuery);
    });
    return { query: normalizedQuery, items };
  }

  function hideSlashCommandMenu() {
    slashCommandOpen = false;
    slashCommandQuery = '';
    slashCommandMatches = [];
    slashCommandIndex = -1;
    if (slashCommandMenu) slashCommandMenu.hidden = true;
  }

  function setActiveSlashCommand(index) {
    if (!slashCommandMatches.length) return;
    slashCommandIndex = (index + slashCommandMatches.length) % slashCommandMatches.length;
    slashCommandMenu.querySelectorAll('.slash-command-item').forEach((btn, i) => {
      const active = i === slashCommandIndex;
      btn.classList.toggle('active', active);
      btn.setAttribute('aria-selected', active ? 'true' : 'false');
      if (active) btn.scrollIntoView({ block: 'nearest' });
    });
  }

  function renderSlashCommandMenu(items) {
    if (!slashCommandMenu) return;
    if (!items.length) {
      slashCommandMenu.innerHTML = '<div class="slash-command-empty">No command found. Try /help.</div>';
      slashCommandMenu.hidden = false;
      slashCommandOpen = true;
      return;
    }
    slashCommandMenu.innerHTML = `
      <div class="slash-command-list">
        ${items.map((item, index) => `
          <button
            class="slash-command-item ${index === slashCommandIndex ? 'active' : ''}"
            type="button"
            role="option"
            aria-selected="${index === slashCommandIndex ? 'true' : 'false'}"
            data-command-id="${escapeHtml(item.id)}"
          >
            <span class="slash-command-name">${escapeHtml(item.command)}</span>
            <span class="slash-command-main">
              <span class="slash-command-title">${escapeHtml(item.title)}</span>
              <span class="slash-command-hint">${escapeHtml(item.hint)}</span>
            </span>
          </button>
        `).join('')}
      </div>
    `;
    slashCommandMenu.querySelectorAll('.slash-command-item').forEach((btn, index) => {
      btn.addEventListener('mousedown', (event) => event.preventDefault());
      btn.addEventListener('mouseenter', () => setActiveSlashCommand(index));
      btn.addEventListener('click', () => {
        runSlashCommandById(btn.dataset.commandId);
      });
    });
    slashCommandMenu.hidden = false;
    slashCommandOpen = true;
  }

  function updateSlashCommandMenu() {
    const state = slashCommandMatchState();
    if (!state) {
      hideSlashCommandMenu();
      return;
    }
    if (state.query !== slashCommandQuery) {
      slashCommandQuery = state.query;
      slashCommandIndex = -1;
    }
    slashCommandMatches = state.items;
    if (slashCommandIndex >= slashCommandMatches.length) slashCommandIndex = -1;
    renderSlashCommandMenu(slashCommandMatches);
  }

  function runSlashCommand(command) {
    if (!command) return false;
    hideSlashCommandMenu();
    if (!command.keepInput) {
      inputEl.value = '';
      autoResize();
    }
    command.run();
    inputEl.focus();
    return true;
  }

  function runSlashCommandById(commandId) {
    const command = slashCommandItems().find((item) => item.id === commandId);
    return runSlashCommand(command);
  }

  function slashCommandFromInput(value) {
    const raw = String(value || '').trim();
    if (!raw.startsWith('/')) return null;
    const token = raw.split(/\s+/)[0].toLowerCase();
    return slashCommandItems().find((item) => {
      const commands = [item.command, ...(item.aliases || [])].map((cmd) => cmd.toLowerCase());
      return commands.includes(token);
    }) || (/^\/[a-z][a-z0-9_-]*$/i.test(token) ? false : null);
  }

  function tryRunMemorySlashCommand(value) {
    const raw = String(value || '').trim();
    const match = raw.match(/^\/(remember|memory|memories|forget)(?:\s+([\s\S]+))?$/i);
    if (!match || !match[2]) return false;
    const command = match[1].toLowerCase();
    const arg = match[2].trim();
    inputEl.value = '';
    autoResize();
    hideSlashCommandMenu();
    if (command === 'remember') {
      rememberFromCommand(arg);
      return true;
    }
    if (command === 'forget') {
      forgetFromCommand(arg);
      return true;
    }
    showMemoriesFromCommand(arg);
    return true;
  }

  function skillSubmissionFromInput(value) {
    const raw = String(value || '').trim();
    let match = raw.match(/^\/skill(?:\s+\$?([a-z0-9][a-z0-9-]*))?(?:\s+([\s\S]+))?$/i);
    if (!match) {
      const direct = raw.match(/^\/([a-z0-9][a-z0-9-]*)\s+([\s\S]+)$/i);
      if (!direct) return null;
      const directItem = (integrationData.skills?.items || []).find(
        (item) => String(item.id || '').toLowerCase() === direct[1].toLowerCase()
      );
      if (!directItem) return null;
      match = [direct[0], direct[1], direct[2]];
    }
    const itemId = String(match[1] || '').toLowerCase();
    if (!itemId) {
      setComposerStatus('Choose a Skill from /help or the Skills panel', 'warn', true);
      openIntegrationsSection('skills');
      return { handled: true };
    }
    const item = (integrationData.skills?.items || []).find(
      (entry) => String(entry.id || '').toLowerCase() === itemId
    );
    if (!item || item.enabled === false) {
      setComposerStatus(`Skill not available: $${itemId}`, 'warn', true);
      return { handled: true };
    }
    const task = String(match[2] || '').trim();
    if (!task) {
      inputEl.value = `/skill ${item.id} `;
      autoResize();
      setComposerStatus(`${item.name} selected; describe the task`, 'ok', true);
      return { handled: true };
    }
    return { handled: false, item, task };
  }

  function tryRunSlashCommand(value) {
    if (tryRunMemorySlashCommand(value)) return true;
    const command = slashCommandFromInput(value);
    if (command === null) return false;
    if (command) return runSlashCommand(command);
    const token = String(value || '').trim().split(/\s+/)[0] || '/';
    setComposerStatus(`Unknown command: ${token}. Type /help.`, 'warn');
    updateSlashCommandMenu();
    inputEl.focus();
    return true;
  }

  function handleSlashCommandKeydown(event) {
    if (!slashCommandOpen) return false;
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveSlashCommand(slashCommandIndex < 0 ? 0 : slashCommandIndex + 1);
      return true;
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveSlashCommand(slashCommandIndex < 0 ? slashCommandMatches.length - 1 : slashCommandIndex - 1);
      return true;
    }
    if (event.key === 'Tab' || (event.key === 'Enter' && !event.shiftKey)) {
      event.preventDefault();
      if (slashCommandMatches.length) runSlashCommand(slashCommandMatches[Math.max(slashCommandIndex, 0)]);
      else setComposerStatus('No slash command matched', 'warn');
      return true;
    }
    if (event.key === 'Escape') {
      event.preventDefault();
      hideSlashCommandMenu();
      return true;
    }
    return false;
  }

  // ---------- Wire up events ----------
  if (voiceBtn) {
    voiceBtn.setAttribute('aria-pressed', 'false');
  }

  function runComposerToolAction(action, event = null) {
    if (!action) return;
    if (event) {
      if (event.__pantheonToolHandled) return;
      event.__pantheonToolHandled = true;
      event.preventDefault();
      event.stopPropagation();
      if (event.type === 'click' && Date.now() - lastComposerToolPointerAt < 600) return;
      if (event.type === 'pointerdown' || event.type === 'mousedown') lastComposerToolPointerAt = Date.now();
    }
    if (action === 'attach' && attachmentInput) {
      attachmentInput.click();
      return;
    }
    if (action === 'voice') {
      if (voiceListening) stopVoiceInput();
      else startVoiceInput();
    }
  }

  window.pantheonComposerTool = (event, action) => runComposerToolAction(action, event);

  function bindComposerToolButton(btn, action) {
    if (!btn) return;
    btn.addEventListener('pointerdown', (event) => runComposerToolAction(action, event));
    btn.addEventListener('click', (event) => runComposerToolAction(action, event));
  }

  bindComposerToolButton(attachBtn, 'attach');
  bindComposerToolButton(voiceBtn, 'voice');

  if (attachmentInput) {
    attachmentInput.addEventListener('change', () => {
      addAttachmentFiles(attachmentInput.files);
      attachmentInput.value = '';
    });
  }

  if (enhancePromptBtn) {
    enhancePromptBtn.addEventListener('click', enhanceCurrentPrompt);
  }

  if (composerForm) {
    composerForm.addEventListener('dragover', (event) => {
      if (!Array.from(event.dataTransfer?.types || []).includes('Files')) return;
      event.preventDefault();
      composerForm.classList.add('is-dragging');
    });
    composerForm.addEventListener('dragleave', () => {
      composerForm.classList.remove('is-dragging');
    });
    composerForm.addEventListener('drop', (event) => {
      if (!event.dataTransfer?.files?.length) return;
      event.preventDefault();
      composerForm.classList.remove('is-dragging');
      addAttachmentFiles(event.dataTransfer.files);
    });
  }

  composerForm.addEventListener('submit', (e) => {
    e.preventDefault();
    if (isStreaming) {
      if (abortCtrl) abortCtrl.abort();
      return;
    }
    if (voiceListening) stopVoiceInput();
    const skillSubmission = skillSubmissionFromInput(inputEl.value);
    if (skillSubmission?.handled) return;
    if (!skillSubmission && tryRunSlashCommand(inputEl.value)) return;
    const attachments = pendingAttachments.map((item) => ({ ...item }));
    const text = skillSubmission?.task
      || inputEl.value.trim()
      || (attachments.length ? '请根据我上传的附件进行分析。' : '');
    if (!text) return;
    inputEl.value = '';
    autoResize();
    clearPendingAttachments();
    const localHtml = standaloneHtmlInput(text);
    if (localHtml && !attachments.length) {
      previewLocalHtmlInput(text, localHtml);
      return;
    }
    const numericChoice = !skillSubmission && !attachments.length
      ? continuationForNumericChoice(text)
      : null;
    const agentTask = numericChoice?.agentTask || `${text}${attachmentPromptContext(attachments)}`;
    sendAsk(text, {
      agentTask,
      attachments,
      skill: skillSubmission?.item?.id || '',
      numericChoice,
    });
  });

  inputEl.addEventListener('keydown', (e) => {
    if (handleSlashCommandKeydown(e)) return;
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      composerForm.dispatchEvent(new Event('submit'));
    }
  });

  inputEl.addEventListener('input', () => {
    autoResize();
    updateSlashCommandMenu();
  });
  inputEl.addEventListener('focus', updateSlashCommandMenu);
  inputEl.addEventListener('blur', () => {
    setTimeout(() => hideSlashCommandMenu(), 120);
  });
  function autoResize() {
    if (!promptEnhancing && enhancedPromptValue && inputEl.value !== enhancedPromptValue) {
      clearPromptEnhancement({ clearStatus: true });
    }
    inputEl.style.height = 'auto';
    inputEl.style.height = Math.min(inputEl.scrollHeight, 200) + 'px';
  }

  $$('.example-chip').forEach((chip) => {
    chip.addEventListener('click', () => {
      hideSlashCommandMenu();
      inputEl.value = chip.dataset.prompt || '';
      autoResize();
      inputEl.focus();
    });
  });

  // ---------- Copy to clipboard helper ----------
  async function copyToClipboard(text) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (e) {
      // Fallback: use a textarea
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand('copy'); document.body.removeChild(ta); return true; }
      catch (_) { document.body.removeChild(ta); return false; }
    }
  }
  function flashCopied(btn, label = '✓') {
    const original = btn.textContent;
    btn.textContent = label;
    btn.classList.add('copied');
    setTimeout(() => {
      btn.textContent = original;
      btn.classList.remove('copied');
    }, 1200);
  }

  // Wire the workspace copy-output button
  if (wsCopyBtn) {
    wsCopyBtn.addEventListener('click', async () => {
      const text = wsOutputEl && wsOutputEl.dataset.empty !== 'true' ? wsOutputEl.textContent : '';
      const ok = await copyToClipboard(text);
      flashCopied(wsCopyBtn, ok ? 'Copied' : 'Failed');
    });
  }

  if (wsClearOutputBtn) {
    wsClearOutputBtn.addEventListener('click', () => {
      workspaceConsoleText = '';
      clearWorkspaceTerminalHints();
      renderWorkspaceTerminal();
      flashCopied(wsClearOutputBtn, 'Cleared');
    });
  }

  // Add a copy button to every message that's already on screen
  function decorateMessageCopyBtn(msgEl) {
    if (!msgEl || msgEl.querySelector('.msg-copy-btn')) return;
    const actions = msgEl.querySelector('.msg-actions') || msgEl.querySelector('.msg-meta');
    if (!actions) return;
    const btn = document.createElement('button');
    btn.className = 'msg-copy-btn';
    btn.title = 'Copy message text';
    btn.textContent = 'Copy';
    btn.addEventListener('click', async () => {
      const content = msgEl.querySelector('.msg-content');
      const text = msgEl.dataset.rawText || (content ? content.innerText : '');
      const ok = await copyToClipboard(text);
      flashCopied(btn, ok ? 'Copied' : 'Failed');
    });
    actions.appendChild(btn);
  }

  function decorateMessageHtmlPreviewBtn(msgEl) {
    if (!msgEl || msgEl.querySelector('.msg-html-preview-btn')) return;
    if (msgEl.classList.contains('user') || msgEl.classList.contains('error')) return;
    const actions = msgEl.querySelector('.msg-actions') || msgEl.querySelector('.msg-meta');
    const content = msgEl.querySelector('.msg-content');
    if (!actions || !content) return;
    if (content.querySelector('.artifact-card, .html-artifact, .code-preview-btn')) return;

    const text = msgEl.dataset.rawText || content.innerText || content.textContent || '';
    if (!extractHtmlFromText(text)) return;

    const btn = document.createElement('button');
    btn.className = 'msg-copy-btn msg-html-preview-btn';
    btn.title = 'Preview HTML in Workspace';
    btn.textContent = 'Preview';
    btn.addEventListener('click', () => {
      const latest = msgEl.dataset.rawText || content.innerText || content.textContent || text;
      previewHtmlFromText(latest, 'message HTML');
    });
    actions.appendChild(btn);
  }

  function artifactContentFromCard(artifact) {
    const code = artifact.querySelector('.artifact-code, .html-artifact-code');
    return code ? code.textContent || '' : '';
  }

  function artifactNameFromCard(artifact) {
    return normalizeArtifactName(
      artifact.dataset.artifactName || 'artifact.txt',
      artifact.dataset.artifactKind || 'txt',
    );
  }

  function artifactSavePath(name) {
    return `pantheon-artifacts/${normalizeArtifactName(name)}`;
  }

  function nextArtifactPath(path, attempt) {
    if (attempt <= 1) return path;
    const slash = path.lastIndexOf('/');
    const dir = slash === -1 ? '' : path.slice(0, slash + 1);
    const file = slash === -1 ? path : path.slice(slash + 1);
    const dot = file.lastIndexOf('.');
    const base = dot === -1 ? file : file.slice(0, dot);
    const ext = dot === -1 ? '' : file.slice(dot);
    return `${dir}${base}-${attempt}${ext}`;
  }

  async function saveArtifactToWorkspace(name, content) {
    const basePath = artifactSavePath(name);
    let lastError = null;
    for (let attempt = 1; attempt <= 8; attempt += 1) {
      const path = nextArtifactPath(basePath, attempt);
      const resp = await fetch('/api/workspace/file', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path, content, overwrite: false }),
      });
      if (resp.ok) return await resp.json();
      const data = await resp.json().catch(() => ({}));
      lastError = data.detail || `HTTP ${resp.status}`;
      if (resp.status !== 409) break;
    }
    throw new Error(lastError || 'Could not save file');
  }

  function decorateArtifactBtns(root) {
    if (!root) return;
    root.querySelectorAll('.artifact-card, .html-artifact').forEach((artifact) => {
      if (artifact.dataset.bound === 'true') return;
      artifact.dataset.bound = 'true';
      const content = artifactContentFromCard(artifact);
      const name = artifactNameFromCard(artifact);
      const kind = artifact.dataset.artifactKind || (looksLikeHtmlSnippet(content, 'html') ? 'html' : 'txt');
      const previewBtn = artifact.querySelector('[data-artifact-preview], [data-html-preview]');
      const copyBtn = artifact.querySelector('[data-artifact-copy], [data-html-copy]');
      const saveBtn = artifact.querySelector('[data-artifact-save]');
      if (previewBtn) {
        previewBtn.addEventListener('click', () => setWorkspacePreviewHtml(content, 'message HTML'));
      }
      if (copyBtn) {
        copyBtn.addEventListener('click', async () => {
          const ok = await copyToClipboard(content);
          flashCopied(copyBtn, ok ? 'Copied' : 'Failed');
        });
      }
      if (saveBtn) {
        saveBtn.addEventListener('click', async () => {
          saveBtn.disabled = true;
          try {
            const saved = await saveArtifactToWorkspace(name, content);
            flashCopied(saveBtn, 'Saved');
            pushWorkspaceLine(`Saved ${displayWorkspacePath(saved.path)}`);
            setWorkspaceTabContent('files', true);
            await loadWorkspaceFiles(workspacePathDirname(saved.path));
            await readWorkspaceFile(saved.path);
            openWorkspace();
            activateWorkspaceTab(kind === 'html' ? 'preview' : 'files');
          } catch (e) {
            flashCopied(saveBtn, 'Failed');
            pushWorkspaceLine(`Save failed: ${e.message || e}`);
          } finally {
            saveBtn.disabled = false;
          }
        });
      }
    });
  }

  function codeBlockLanguage(codeEl) {
    const cls = codeEl.className || '';
    const match = cls.match(/language-([\w-]+)/);
    if (match) return match[1];
    const pre = codeEl.closest('pre');
    return pre ? pre.dataset.lang || '' : '';
  }

  function decorateHtmlPreviewBtns(root) {
    if (!root) return;
    root.querySelectorAll('pre code').forEach((code) => {
      const pre = code.closest('pre');
      if (!pre || pre.dataset.previewDecorated === 'true') return;
      if (pre.closest('.artifact-card, .html-artifact')) return;
      const codeText = code.textContent || '';
      const lang = codeBlockLanguage(code);
      if (!looksLikeHtmlSnippet(codeText, lang)) return;

      pre.dataset.previewDecorated = 'true';
      pre.classList.add('has-actions');
      const actions = document.createElement('div');
      actions.className = 'code-actions';
      const previewBtn = document.createElement('button');
      previewBtn.className = 'code-preview-btn';
      previewBtn.type = 'button';
      previewBtn.textContent = 'Preview';
      previewBtn.title = 'Preview this HTML in Workspace';
      previewBtn.addEventListener('click', () => {
        setWorkspacePreviewHtml(code.textContent || codeText, 'message HTML');
      });
      actions.appendChild(previewBtn);
      pre.appendChild(actions);
    });
  }

  // ---------- Chat history (localStorage) ----------
  const HISTORY_KEY = 'pantheon:chat-history';
  // Serialize the visible chat DOM into a plain-text transcript.
  function snapshotChat() {
    const items = [];
    chatEl.querySelectorAll('.msg').forEach((msg) => {
      const isUser = msg.classList.contains('user');
      const isError = msg.classList.contains('error');
      const content = msg.querySelector('.msg-content');
      const text = (msg.dataset.rawText || (content ? content.innerText : '')).trim();
      if (!text) return;
      let role = msg.dataset.role || 'assistant';
      if (isUser) role = 'user';
      else if (isError) role = 'error';
      else if (!msg.dataset.role) {
        // Pick the role from class names other than 'msg', 'user', 'error'
        for (const cls of msg.classList) {
          if (cls !== 'msg' && cls !== 'user' && cls !== 'error' && cls !== 'assistant') {
            role = cls; break;
          }
        }
      }
      let attachments = [];
      if (msg.dataset.attachments) {
        try {
          const parsed = JSON.parse(msg.dataset.attachments);
          attachments = Array.isArray(parsed) ? parsed : [];
        } catch (_) {
          attachments = [];
        }
      }
      items.push({ role, text, ...(attachments.length ? { attachments } : {}) });
    });
    return items;
  }
  function saveHistory() {
    try { localStorage.setItem(HISTORY_KEY, JSON.stringify(snapshotChat())); } catch (_) {}
  }
  function loadHistory() {
    try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]'); }
    catch (_) { return []; }
  }
  function clearHistory() {
    try { localStorage.removeItem(HISTORY_KEY); } catch (_) {}
  }

  // Restore history on load
  function restoreHistory() {
    const items = loadHistory();
    if (!items.length) return;
    chatEl.innerHTML = '';
    items.forEach((item, i) => {
      if (item.role === 'user') {
        addUserMessage(item.text, { attachments: item.attachments || [] });
      } else if (item.role === 'error') {
        addErrorMessage(item.text);
      } else {
        addMessage(item.role, renderAssistantContent(item.text), {
          icon: metaFor(item.role).icon,
          label: metaFor(item.role).label,
          roleColor: metaFor(item.role).color,
          rawText: item.text,
        });
      }
      const last = chatEl.lastElementChild;
      if (last) last.style.setProperty('--msg-delay', `${Math.min(i, 8) * 50}ms`);
      decorateMessageCopyBtn(last);
    });
  }

  // Hook into the existing flow: after addUserMessage / addMessage, save + decorate.
  const chatObserver = new MutationObserver((mutations) => {
    for (const m of mutations) {
      for (const node of m.addedNodes) {
        if (node.nodeType === 1 && node.classList && node.classList.contains('msg')) {
          decorateMessageCopyBtn(node);
          decorateMessageHtmlPreviewBtn(node);
          decorateHtmlPreviewBtns(node);
        }
      }
    }
    saveActiveSession();
    renderSessions();
  });
  chatObserver.observe(chatEl, { childList: true, subtree: true });

  // ---------- Keyboard shortcuts ----------
  document.addEventListener('keydown', (e) => {
    const mod = e.metaKey || e.ctrlKey;
    if (mod && e.key === ',') {
      e.preventDefault();
      toggleSettings();
      return;
    }
    if (mod && e.key === '/') {
      e.preventDefault();
      toggleWorkspace();
      return;
    }
    if (mod && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      toggleRoutingMode();
      return;
    }
    if (e.key === 'Escape') {
      if (!settingsPanel.hidden) { closeSettings(); e.preventDefault(); }
      if (!workspaceEl.hidden) { closeWorkspace(); e.preventDefault(); }
      const tag = (e.target.tagName || '').toLowerCase();
      if (tag === 'input' || tag === 'textarea' || e.target.isContentEditable) e.target.blur();
    }
  });

  // ---------- Export chat as Markdown ----------
  function exportChat() {
    const items = snapshotChat();
    const lines = ['# Pantheon Chat Export', '', `*Exported: ${new Date().toLocaleString()}*`, ''];
    for (const item of items) {
      const who = item.role === 'user' ? 'You'
        : item.role === 'error' ? 'Error'
        : (metaFor(item.role).label || item.role);
      lines.push(`## ${who}`, '', item.text, '');
    }
    const md = lines.join('\n');
    const blob = new Blob([md], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `pantheon-chat-${Date.now()}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }
  // Expose for now (no UI button yet — keyboard-only via Cmd+Shift+E)
  document.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key.toLowerCase() === 'e') {
      e.preventDefault();
      exportChat();
    }
  });
  if (exportChatBtn) {
    exportChatBtn.addEventListener('click', () => exportChat());
  }

  // Init
  setProvider('connecting…', 'connecting');
  wireOptBtns();
  loadSessions();
  renderSessions();
  if (activeSessionId) activateSession(activeSessionId, true);
  else setMode('auto');
  loadAuthStatus().then(() => initProtectedData());
  setInterval(() => {
    if (protectedDataLoaded && (!authState.enabled || authState.authenticated)) loadUpdateStatus();
  }, 6 * 60 * 60 * 1000);
})();
