'use strict';
// Provider identity stays separate from role portraits, model IDs and connection health.
// Only bundled assets are used; a model refresh never downloads or guesses a logo.
const providerAssets = Object.freeze({
  deepseek: 'provider-deepseek.png',
  openai: 'provider-openai.png',
  anthropic: 'provider-anthropic.png',
  ollama: 'provider-ollama.svg',
});
const modelPickers = new WeakMap();
let modelPickerSequence = 0;

function providerMark(provider) {
  const id = typeof provider === 'string' ? provider : provider?.id;
  const mark = document.createElement('span');
  mark.className = 'provider-mark';
  mark.dataset.provider = id || 'custom';
  mark.setAttribute('aria-hidden', 'true');
  if (Object.hasOwn(providerAssets, id)) {
    const image = document.createElement('img');
    image.src = providerAssets[id]; image.alt = ''; image.draggable = false;
    image.addEventListener('error', () => mark.replaceChildren(desktopIcon('service')), {once: true});
    mark.append(image);
  } else mark.append(desktopIcon('service'));
  return mark;
}

function providerOption(select, provider) {
  const option = document.createElement('option');
  option.value = provider.id; option.label = provider.label || provider.id;
  const content = document.createElement('span'); content.className = 'provider-option';
  content.append(providerMark(provider), document.createTextNode(option.label));
  option.append(content); select.append(option);
}

function prepareProviderSelect(select) {
  select.replaceChildren(); select.classList.add('provider-select');
  // Retain native select semantics, keyboard navigation and the existing change contract.
  if (CSS.supports('appearance', 'base-select')) {
    const button = document.createElement('button'); button.type = 'button';
    button.append(document.createElement('selectedcontent')); select.append(button);
  }
}

function providerEndpointNote(provider, value) {
  if (!provider) return '';
  let host = '';
  try { host = new URL(value || provider.base_url).hostname; } catch {}
  if (provider.id === 'ollama') {
    const local = ['localhost', '127.0.0.1', '[::1]'].includes(host);
    return 'Model runtime · ' + (local ? 'Local endpoint' : 'Remote endpoint');
  }
  const official = {openai: 'api.openai.com', anthropic: 'api.anthropic.com', deepseek: 'api.deepseek.com'};
  if (host && host !== official[provider.id]) return 'Custom endpoint · ' + (provider.id === 'openai' ? 'OpenAI-compatible' : (provider.label || provider.id) + ' connection');
  return 'Provider API · Connections are saved independently';
}

function attachModelPicker(input, getProvider) {
  const number = ++modelPickerSequence;
  const wrapper = document.createElement('div'); wrapper.className = 'model-picker';
  input.before(wrapper); wrapper.append(input); input.removeAttribute('list');
  const mark = document.createElement('span'); mark.className = 'model-picker-mark';
  const toggle = document.createElement('button'); toggle.type = 'button'; toggle.className = 'model-picker-toggle';
  toggle.setAttribute('aria-label', 'Browse ' + input.getAttribute('aria-label'));
  toggle.append(desktopIcon('chevron')); wrapper.prepend(mark); wrapper.append(toggle);
  const menu = document.createElement('div'); menu.className = 'model-menu'; menu.id = 'model-menu-' + number;
  menu.setAttribute('popover', 'auto'); menu.setAttribute('role', 'listbox');
  menu.setAttribute('aria-label', input.getAttribute('aria-label') + ' choices'); wrapper.append(menu);
  input.setAttribute('role', 'combobox'); input.setAttribute('aria-autocomplete', 'list');
  input.setAttribute('aria-expanded', 'false'); input.setAttribute('aria-controls', menu.id);
  toggle.setAttribute('aria-controls', menu.id); toggle.setAttribute('aria-expanded', 'false');
  let active = -1, options = [];
  const isOpen = () => menu.matches(':popover-open');
  const close = () => { if (isOpen()) menu.hidePopover(); };
  const sync = () => {
    mark.replaceChildren(providerMark(getProvider()));
    input.title = input.value;
    if (isOpen()) close();
  };
  const position = () => {
    const rect = wrapper.getBoundingClientRect(), width = Math.min(Math.max(rect.width, 300), innerWidth - 32);
    menu.style.width = width + 'px'; menu.style.left = Math.max(16, Math.min(rect.left, innerWidth - width - 16)) + 'px';
    const below = innerHeight - rect.bottom - 16, above = rect.top - 16, upward = below < 200 && above > below;
    menu.style.maxHeight = Math.min(340, Math.max(100, upward ? above - 8 : below - 8)) + 'px';
    menu.style.top = (upward ? Math.max(16, rect.top - menu.getBoundingClientRect().height - 6) : rect.bottom + 6) + 'px';
  };
  const activate = index => {
    active = index;
    options.forEach((option, i) => { option.classList.toggle('active', i === active); });
    if (options[active]) { input.setAttribute('aria-activedescendant', options[active].id); options[active].scrollIntoView({block: 'nearest'}); }
    else input.removeAttribute('aria-activedescendant');
  };
  const choose = id => {
    input.value = id; close(); input.focus({preventScroll: true});
    input.dispatchEvent(new Event('input', {bubbles: true}));
    close(); input.title = id;
  };
  const show = (filter = false) => {
    if (input.disabled || !input.isConnected || !input.closest('dialog[open]')) return;
    const provider = getProvider(), query = filter ? input.value.trim().toLowerCase() : '';
    const catalog = provider?.models || [], matches = catalog.filter(model => !query || (model.id + ' ' + (model.label || '')).toLowerCase().includes(query));
    menu.replaceChildren(); options = [];
    const heading = document.createElement('div'); heading.className = 'model-menu-heading';
    heading.append(providerMark(provider), document.createTextNode((provider?.label || provider?.id || 'Connection') + ' models'));
    menu.append(heading);
    const add = (model, custom = false) => {
      const option = document.createElement('button'); option.type = 'button'; option.className = 'model-menu-option';
      option.id = menu.id + '-option-' + options.length; option.tabIndex = -1; option.setAttribute('role', 'option');
      option.setAttribute('aria-selected', String(model.id === input.value)); option.dataset.model = model.id;
      const copy = document.createElement('span'), name = document.createElement('strong'), detail = document.createElement('small');
      name.textContent = model.label || model.id;
      detail.textContent = custom ? 'Custom model ID · availability not tested' : model.label && model.label !== model.id ? model.id : model.available === false ? 'Not in latest provider list · verify access' : model.available === true ? 'Listed by provider · API access not tested' : 'Catalog model · API access not tested';
      copy.append(name, detail); option.append(providerMark(provider), copy);
      option.addEventListener('mousedown', event => event.preventDefault());
      option.addEventListener('click', event => {event.preventDefault(); choose(model.id);});
      menu.append(option); options.push(option);
    };
    for (const model of matches) add(model);
    const typed = input.value.trim();
    if (typed && !catalog.some(model => model.id === typed)) add({id: typed, label: typed}, true);
    if (!options.length) {const empty = document.createElement('p'); empty.className = 'model-menu-empty'; empty.textContent = 'No matching models. Enter a custom model ID.'; menu.append(empty);}
    if (!isOpen()) menu.showPopover();
    position(); activate(options.findIndex(option => option.dataset.model === input.value));
  };
  menu.addEventListener('toggle', () => {
    const open = isOpen(); input.setAttribute('aria-expanded', String(open)); toggle.setAttribute('aria-expanded', String(open));
    if (!open) {active = -1; input.removeAttribute('aria-activedescendant');}
  });
  toggle.addEventListener('mousedown', event => event.preventDefault());
  toggle.addEventListener('click', event => {event.preventDefault(); if (isOpen()) close(); else {input.focus({preventScroll: true}); show();}});
  input.addEventListener('input', () => { input.title = input.value; show(true); });
  input.addEventListener('keydown', event => {
    if (['ArrowDown', 'ArrowUp'].includes(event.key)) {
      event.preventDefault(); if (!isOpen()) show();
      activate(!options.length ? -1 : active < 0 ? (event.key === 'ArrowDown' ? 0 : options.length - 1) : (active + (event.key === 'ArrowDown' ? 1 : -1) + options.length) % options.length);
    } else if (event.key === 'Enter' && isOpen()) {
      event.preventDefault(); event.stopPropagation(); if (options[active]) choose(options[active].dataset.model); else close();
    } else if (event.key === 'Escape' && isOpen()) { event.preventDefault(); event.stopPropagation(); close(); }
    else if (event.key === 'Tab') close();
  });
  input.addEventListener('blur', () => setTimeout(() => {if (document.activeElement !== input) close();}, 0));
  input.closest('dialog')?.addEventListener('close', close, {once: true});
  modelPickers.set(input, {sync, close}); sync();
}

function refreshModelPicker(input) { modelPickers.get(input)?.sync(); }

// Top-layer menus close when their anchor moves; resize never changes the choice.
function closeModelMenus() {document.querySelectorAll('.model-menu:popover-open').forEach(menu => menu.hidePopover());}
window.addEventListener('resize', closeModelMenus);
document.addEventListener('scroll', event => {if (event.target.classList?.contains('dialog-scroll')) closeModelMenus();}, true);
