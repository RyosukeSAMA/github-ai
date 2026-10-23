'use strict';
// Small, local SVG set: no icon font, external request, or platform-dependent glyphs.
const DESKTOP_ICONS = {
  newTask: '<path d="M13 5H6a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2v-7"/><path d="m16 3 5 5-9 9-5 1 1-5Z"/><path d="m14 5 5 5"/>',
  work: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  tasks: '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="m7 8 1 1 2-2m3 1h4M7 13h3m3 0h4M7 17h3m3 0h4"/>',
  library: '<rect x="3" y="4" width="5" height="16" rx="1"/><path d="M11 4v16m4-15 4-1 3 15-4 1ZM5.5 8h0m0 8h0"/>',
  files: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9Z"/><path d="M14 3v6h6M8 13h8m-8 4h5"/>',
  folder: '<path d="M3 7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/><path d="M3 10h18"/>',
  route: '<path d="M7 5h10M7 12h10M7 19h10M12 5v14"/><circle cx="5" cy="5" r="2"/><circle cx="19" cy="12" r="2"/><circle cx="5" cy="19" r="2"/>',
  council: '<circle cx="12" cy="6" r="3"/><path d="M7 21v-2a5 5 0 0 1 10 0v2M4 10a3 3 0 0 0 0 6m16-6a3 3 0 0 1 0 6M2 21v-1a4 4 0 0 1 3-4m17 5v-1a4 4 0 0 0-3-4"/>',
  build: '<path d="m12 3 8 4.5v9L12 21l-8-4.5v-9Z"/><path d="m4 7.5 8 4.5 8-4.5M12 12v9M8 5.3l8 4.5"/>',
  repair: '<path d="m14 7 3-3a5 5 0 0 0-6 6L3 18a2 2 0 0 0 3 3l8-8a5 5 0 0 0 6-6l-3 3Z"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  capabilities: '<path d="m12 2 3 7 7 3-7 3-3 7-3-7-7-3 7-3Z"/>',
  models: '<path d="M4 6h5m4 0h7M4 12h9m4 0h3M4 18h2m4 0h10"/><circle cx="11" cy="6" r="2"/><circle cx="15" cy="12" r="2"/><circle cx="8" cy="18" r="2"/>',
  service: '<path d="M8 3v5m8-5v5M6 8h12v3a6 6 0 0 1-12 0Zm6 9v4"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
  chevron: '<path d="m6 9 6 6 6-6"/>',
  close: '<path d="m6 6 12 12M18 6 6 18"/>',
  more: '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>',
  layout: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16M9 10h12"/>',
  focus: '<path d="M8 3H5a2 2 0 0 0-2 2v3m13-5h3a2 2 0 0 1 2 2v3M3 16v3a2 2 0 0 0 2 2h3m8 0h3a2 2 0 0 0 2-2v-3"/><circle cx="12" cy="12" r="3"/>',
  context: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M15 4v16m3-10h0m0 4h0"/>',
  command: '<path d="M9 7V5a2 2 0 1 0-2 2h10a2 2 0 1 0-2-2v14a2 2 0 1 0 2-2H7a2 2 0 1 0 2 2Z"/>',
  moon: '<path d="M20.5 14a9 9 0 0 1-10.5-10.5A9 9 0 1 0 20.5 14Z"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/>',
  approval: '<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6Z"/><path d="m8.5 12 2.5 2.5 4.5-5"/>',
  terminal: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="m7 9 3 3-3 3m6 0h4"/>',
  copy: '<rect x="8" y="8" width="12" height="13" rx="2"/><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"/>',
  edit: '<path d="m16 3 5 5-11 11-7 2 2-7Z"/><path d="m14 5 5 5"/>',
  attach: '<path d="m8 13 7-7a3 3 0 0 1 4 4l-9 9a5 5 0 0 1-7-7l9-9m-7 12 8-8"/>',
  send: '<path d="m21 3-7 18-4-8-8-4Z"/><path d="M21 3 10 13"/>',
  play: '<path d="m8 4 12 8-12 8Z"/>',
  stop: '<rect x="6" y="6" width="12" height="12" rx="2"/>',
  open: '<path d="M14 3h7v7m0-7L10 14"/><path d="M10 4H5a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h13a2 2 0 0 0 2-2v-5"/>',
};
function desktopIcon(name) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 24 24'); svg.setAttribute('fill', 'none');
  svg.setAttribute('stroke', 'currentColor'); svg.setAttribute('stroke-width', '1.7');
  svg.setAttribute('stroke-linecap', 'round'); svg.setAttribute('stroke-linejoin', 'round');
  svg.setAttribute('aria-hidden', 'true'); svg.setAttribute('focusable', 'false');
  svg.classList.add('ui-icon'); svg.innerHTML = DESKTOP_ICONS[name] || DESKTOP_ICONS.capabilities;
  return svg;
}
function setIconButton(button, icon, label, shortcut = '') {
  button.classList.add('icon-button'); button.dataset.icon = icon;
  button.dataset.tooltip = label; button.dataset.shortcut = shortcut;
  button.setAttribute('aria-label', label); button.removeAttribute('title');
  button.replaceChildren(desktopIcon(icon));
  if (activeTooltipButton === button) showButtonTooltip(button);
  return button;
}
const buttonTooltip = document.createElement('div');
buttonTooltip.id = 'button-tooltip'; buttonTooltip.role = 'tooltip'; buttonTooltip.hidden = true;
document.body.append(buttonTooltip);
let activeTooltipButton = null, tooltipDelay = null, tooltipHideDelay = null;
function hideButtonTooltip() {
  clearTimeout(tooltipDelay); clearTimeout(tooltipHideDelay);
  if (activeTooltipButton) {
    const ids = (activeTooltipButton.getAttribute('aria-describedby') || '').split(' ').filter(id => id && id !== buttonTooltip.id);
    if (ids.length) activeTooltipButton.setAttribute('aria-describedby', ids.join(' '));
    else activeTooltipButton.removeAttribute('aria-describedby');
  }
  activeTooltipButton = null; buttonTooltip.hidden = true;
}
function showButtonTooltip(button) {
  hideButtonTooltip();
  if (!button.isConnected || !button.getClientRects().length || button.disabled) return;
  activeTooltipButton = button;
  const label = document.createElement('span'); label.textContent = button.dataset.tooltip;
  buttonTooltip.replaceChildren(label);
  if (button.dataset.shortcut) {
    const key = document.createElement('kbd'); key.textContent = button.dataset.shortcut; buttonTooltip.append(key);
  }
  const ids = (button.getAttribute('aria-describedby') || '').split(' ').filter(Boolean);
  button.setAttribute('aria-describedby', [...new Set([...ids, buttonTooltip.id])].join(' '));
  buttonTooltip.hidden = false;
  const rect = button.getBoundingClientRect(), tip = buttonTooltip.getBoundingClientRect();
  buttonTooltip.style.left = Math.max(8, Math.min(innerWidth - tip.width - 8, rect.left + rect.width / 2 - tip.width / 2)) + 'px';
  buttonTooltip.style.top = (rect.bottom + tip.height + 12 < innerHeight ? rect.bottom + 8 : Math.max(8, rect.top - tip.height - 8)) + 'px';
}
function scheduleTooltipHide() { clearTimeout(tooltipDelay); clearTimeout(tooltipHideDelay); tooltipHideDelay = setTimeout(hideButtonTooltip, 160); }
document.addEventListener('pointerover', event => {
  if (event.pointerType === 'touch') return;
  const button = event.target.closest('button[data-tooltip]');
  if (!button || button === activeTooltipButton || button.contains(event.relatedTarget)) return;
  clearTimeout(tooltipDelay); clearTimeout(tooltipHideDelay);
  tooltipDelay = setTimeout(() => showButtonTooltip(button), 220);
});
document.addEventListener('pointerout', event => {
  const button = event.target.closest('button[data-tooltip]');
  if (button && !button.contains(event.relatedTarget) && !buttonTooltip.contains(event.relatedTarget)) scheduleTooltipHide();
});
buttonTooltip.addEventListener('pointerenter', () => clearTimeout(tooltipHideDelay));
buttonTooltip.addEventListener('pointerleave', scheduleTooltipHide);
document.addEventListener('focusin', event => {
  const button = event.target.closest('button[data-tooltip]');
  if (button) showButtonTooltip(button); else hideButtonTooltip();
});
document.addEventListener('focusout', event => { if (event.target === activeTooltipButton) hideButtonTooltip(); });
document.addEventListener('keydown', event => { if (event.key === 'Escape') hideButtonTooltip(); });
document.addEventListener('click', hideButtonTooltip);
document.addEventListener('scroll', hideButtonTooltip, true);
window.addEventListener('resize', hideButtonTooltip);
document.querySelectorAll('button[data-icon]').forEach(button => setIconButton(button, button.dataset.icon, button.getAttribute('aria-label'), button.dataset.shortcut));
