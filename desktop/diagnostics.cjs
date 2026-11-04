'use strict';
// Construct a fresh allowlisted object: never serialize config, logs, API errors or prompts.
function diagnosticSummary({version,versions,platform,arch,osRelease,backend,reachable=false,sessions=[],runs=[]}){
  const versionText=value=>typeof value==='string'&&/^[0-9A-Za-z.+-]{1,80}$/.test(value)?value:'unknown';
  const counts={};for(const status of ['queued','running','stopping','completed','failed','interrupted','cancelled'])counts[status]=runs.filter(run=>run.status===status).length;
  return {format:1,created_at:new Date().toISOString(),app_version:versionText(version),runtime:{electron:versionText(versions.electron),chrome:versionText(versions.chrome),node:versionText(versions.node)},system:{platform:versionText(platform),arch:versionText(arch),release:versionText(osRelease)},service:{selected:!!backend,remote:!!backend?.remote,desktop_owned:!!backend?.owned,reachable:!!reachable},counts:{tasks:sessions.length,runs:runs.length,run_status:counts},omitted:['credentials','configuration','prompts','messages','files','project names and paths','server addresses','raw logs and errors']};
}
module.exports={diagnosticSummary};
