'use strict';
const fs = require('node:fs/promises');
const path = require('node:path');
const crypto = require('node:crypto');
const {spawn, execFile} = require('node:child_process');
const {promisify} = require('node:util');
const exec = promisify(execFile);
function remoteURL(value) {
  const url = new URL(value);
  if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash || url.pathname !== '/') throw new Error('Use an HTTPS server origin without a path, credentials, or query.');
  return url.origin;
}
function apiPath(value, allowTerminal = false) {
  if (typeof value !== 'string' || value.length > 3000 || !/^\/api\/[a-z]/.test(value) || /[\\\r\n#]/.test(value)) throw new Error('Invalid API path');
  const parsed = new URL(value, 'http://localhost');
  if (parsed.origin !== 'http://localhost' || parsed.pathname.includes('..')) throw new Error('Invalid API path');
  const allowed = /^\/api\/(desktop|setup|connections|models|roles|tasks|usage|budgets|workflow|memory|skills|plugins|mcp|chronos|media|channels|integrations|info|workspace|onboarding|update)(\/|$)/;
  const decoded=decodeURIComponent(parsed.pathname);if(/[\\\r\n]/.test(decoded)||decoded.split('/').includes('..'))throw new Error('Invalid API path');
  if (decoded === '/api/workspace/file' || decoded === '/api/workspace/preview') throw new Error('Use the desktop file review API.');
  if (!allowTerminal && /^\/api\/workspace\/terminal(?:\/|$)/.test(decoded))throw new Error('Terminal commands require native confirmation.');
  if (!allowed.test(decoded)) throw new Error('API operation is not exposed to the desktop');
  return value;
}
function requestTimeout(target){return /^\/api\/media\/(generate|transcribe)(?:\?|$)/.test(target)?300000:target.includes('/api/mcp/servers/')&&target.endsWith('/test')?180000:30000;}
class Backend {
  constructor({executable, args = [], env = process.env}) { this.executable = executable; this.args = args; this.env = env; this.owned = false; this.child = null; this.token = ''; this.cookie = ''; }
  async identity() {
    const challenge = crypto.randomBytes(20).toString('hex');
    const value = await this.request('/api/desktop/identity?challenge='+challenge);
    if (value.challenge !== challenge || value.api_version !== 1) throw new Error('Incompatible Pantheon desktop service');
    return value;
  }
  async local(workspace) {
    this.workspace = await fs.realpath(workspace); this.remote = false;
    const {stdout} = await exec(this.executable, [...this.args, '--workspace', this.workspace, '--locate'], {env: this.env, timeout: 20000, windowsHide: true});
    const locations = JSON.parse(stdout.trim());
    let metadata, lock;
    try { metadata = JSON.parse(await fs.readFile(locations.descriptor, 'utf8')); lock = JSON.parse(await fs.readFile(locations.runtime_lock, 'utf8')); } catch {}
    if (metadata && lock && metadata.pid === lock.pid && metadata.workspace === this.workspace && Number.isInteger(metadata.port) && metadata.port > 0 && metadata.port <= 65535) {
      try {
        if (process.platform !== 'win32' && ((await fs.stat(locations.descriptor)).mode & 0o077)) throw new Error('Runtime capability file permissions are too broad');
        this.base = 'http://127.0.0.1:'+metadata.port; this.token = metadata.token;
        const identity = await this.identity();
        if (identity.instance_id === metadata.instance_id && identity.workspace === this.workspace) { this.info = identity; return this; }
      } catch { this.token = ''; }
    }
    if (lock?.pid) {
      let alive = false;
      try { process.kill(lock.pid, 0); alive = true; } catch (error) { alive = error.code === 'EPERM'; }
      if (alive) throw new Error('A different or older Pantheon service owns this workspace. Update or stop that service before opening it in Desktop.');
    }
    this.token = crypto.randomBytes(36).toString('base64url');
    this.child = spawn(this.executable, [...this.args, '--workspace', this.workspace], {env: {...this.env, PANTHEON_DESKTOP_TOKEN: this.token}, stdio: ['ignore','pipe','pipe'], windowsHide: true});
    this.owned = true;
    const ready = await new Promise((resolve, reject) => {
      let buffer = '', stderr = '';
      const timeout = setTimeout(() => { this.child.kill(); reject(new Error('Pantheon core did not start within 30 seconds.')); }, 30000);
      const finish = (error, value) => { clearTimeout(timeout); error ? reject(error) : resolve(value); };
      this.child.once('error', error => finish(error));
      this.child.once('exit', code => { if (!this.info) finish(new Error('Pantheon core exited before startup ('+code+'). '+stderr.slice(-500))); });
      this.child.stderr.on('data', data => { stderr = (stderr + data.toString()).slice(-3000); });
      this.child.stdout.on('data', data => {
        buffer += data.toString();
        while (buffer.includes('\n')) {
          const index = buffer.indexOf('\n'), line = buffer.slice(0,index); buffer = buffer.slice(index+1);
          try { const value = JSON.parse(line); if (Number.isInteger(value.port) && value.instance_id) finish(null,value); } catch {}
        }
      });
    });
    this.base = 'http://127.0.0.1:'+ready.port;
    let error;
    for (let i=0; i<80; i++) {
      try { const value = await this.identity(); if (value.workspace !== this.workspace || value.instance_id !== ready.instance_id) throw new Error('Core identity mismatch'); this.info = value; return this; }
      catch (value) { error = value; await new Promise(resolve => setTimeout(resolve,100)); }
    }
    this.child.kill(); throw error;
  }
  async connectRemote(value) {
    this.base = remoteURL(value.url); this.remote = true; this.owned = false;
    const response = await fetch(this.base+'/api/auth/login', {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({username:value.username,password:value.password}), signal:AbortSignal.timeout(15000), redirect:'error'});
    if (!response.ok) throw new Error('Remote sign-in failed. Check server authentication and credentials.');
    this.cookie = response.headers.getSetCookie().map(value => value.split(';')[0]).join('; ');
    this.info = await this.identity(); this.workspace = this.info.workspace; return this;
  }
  async response(target, options = {}, signal, allowTerminal = false) {
    const safePath = apiPath(target, allowTerminal), method = options.method || 'GET';
    if (!['GET','POST','PUT','PATCH','DELETE'].includes(method)) throw new Error('Unsupported method');
    if (options.body && JSON.stringify(options.body).length > 40000000) throw new Error('Request is too large');
    return fetch(this.base+safePath, {method, headers:{'content-type':'application/json', ...(this.token ? {'x-pantheon-desktop-token':this.token} : {}), ...(this.cookie ? {cookie:this.cookie} : {})}, body:options.body === undefined ? undefined : JSON.stringify(options.body), redirect:'error', signal:signal || AbortSignal.timeout(requestTimeout(safePath))});
  }
  async request(target, options) {
    const response = await this.response(target, options);
    const value = await response.json();
    if (!response.ok) { const error = new Error(typeof value.detail === 'string' ? value.detail : JSON.stringify(value.detail || 'Request failed')); error.status = response.status; throw error; }
    return value;
  }
  async stop() {
    if (this.owned && this.child && this.child.exitCode === null) {
      const child = this.child;
      await new Promise(resolve => {
        const timer = setTimeout(() => { child.kill('SIGKILL'); resolve(); }, 12000);
        child.once('exit', () => { clearTimeout(timer); resolve(); }); child.kill('SIGTERM');
      });
    }
  }
}
module.exports = {Backend, apiPath, remoteURL,requestTimeout};
