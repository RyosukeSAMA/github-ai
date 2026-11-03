'use strict';
const fs=require('node:fs/promises');
const path=require('node:path');
const {execFile}=require('node:child_process');
const {promisify}=require('node:util');
const {createHash,randomUUID}=require('node:crypto');
const exec=promisify(execFile);
class MaintenanceManager{
  constructor({directory,command,flush,reconnect,onChange=()=>{}}){Object.assign(this,{directory,command,flush,reconnect,onChange});this.busy=new Set();}
  async index(){try{const records=JSON.parse(await fs.readFile(path.join(this.directory,'backups.json'),'utf8'));return Array.isArray(records)?records.filter(item=>item&&typeof item.id==='string'&&typeof item.path==='string'&&typeof item.workspace==='string'):[];}catch{return [];}}
  async saveIndex(records){await fs.mkdir(this.directory,{recursive:true,mode:0o700});const temporary=path.join(this.directory,randomUUID()+'.json');await fs.writeFile(temporary,JSON.stringify(records),{mode:0o600});await fs.rename(temporary,path.join(this.directory,'backups.json'));}
  async list(workspace){return (await this.index()).filter(item=>item.workspace===workspace).map(({id,name,created_at,includes_secrets,reason,size,rollback})=>({id,name,created_at,includes_secrets,reason,size,rollback:!!rollback}));}
  async offline(backend,args){const {stdout}=await exec(this.command.executable,[...this.command.args,'--workspace',backend.workspace,...args],{env:backend.env,windowsHide:true,timeout:120000,maxBuffer:1024*1024});return JSON.parse(stdout.trim());}
  async inspect(backend,file){return this.offline(backend,['--inspect-backup',file]);}
  async perform(backend,operation,file,{includeSecrets=false,reason='manual'}={}){
    if(!['backup','restore'].includes(operation))throw new Error('Unsupported maintenance operation.');
    if(!backend?.owned||backend.remote)throw new Error('Backup and restore require an idle local service owned by Desktop. Manage reused or remote services on their host.');
    if(this.busy.has(backend.workspace))throw new Error('This workspace already has a maintenance operation.');
    this.busy.add(backend.workspace);let stopped=false,result,operationError;
    try{
      this.onChange(backend,{phase:'preparing',operation});await this.flush(backend);
      const status=await backend.request('/api/desktop/sessions');
      if(status.runs.some(run=>['queued','running','stopping'].includes(run.status)))throw new Error('Wait for active tasks to finish before backup or restore.');
      backend.maintenance=true;this.onChange(backend,{phase:'working',operation});await backend.stop();stopped=true;
      const args=['--'+operation,file,...(operation==='backup'&&includeSecrets?['--include-secrets']:[])];
      result=await this.offline(backend,args);
      if(operation==='backup'){
        const record={id:randomUUID(),workspace:backend.workspace,name:path.basename(file),path:file,created_at:Date.now(),includes_secrets:includeSecrets,reason,size:(await fs.stat(file)).size};
        const records=await this.index();records.unshift(record);await this.saveIndex(records.slice(0,200));result={...result,backup_id:record.id};
      }
    }catch(error){operationError=error;}
    finally{
      try{if(stopped)await this.reconnect(backend,{restored:operation==='restore'&&!operationError});}
      catch(error){operationError=new Error((operationError?operationError.message+' ':'')+'The workspace could not reconnect: '+error.message);}
      finally{backend.maintenance=false;this.busy.delete(backend.workspace);this.onChange(backend,{phase:operationError?'failed':'complete',operation,error:operationError?.message});}
    }
    if(operationError)throw operationError;return result;
  }
  async automaticBackup(backend){
    const key=createHash('sha256').update(backend.workspace).digest('hex').slice(0,12);
    const file=path.join(this.directory,'before-update-'+key+'-'+Date.now()+'.zip');await fs.mkdir(this.directory,{recursive:true,mode:0o700});
    return this.perform(backend,'backup',file,{reason:'before update'});
  }
  async revealFile(id,workspace){const record=(await this.index()).find(item=>item.id===id&&item.workspace===workspace);if(!record)throw new Error('Choose a backup belonging to this workspace.');return record.path;}
}
module.exports={MaintenanceManager};
