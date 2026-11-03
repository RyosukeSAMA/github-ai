'use strict';
const fs=require('node:fs/promises');
const {createReadStream}=require('node:fs');
const path=require('node:path');
const {createHash,randomUUID}=require('node:crypto');
const {selectRelease,compareVersions}=require('./releases.cjs');
const API='https://api.github.com/repos/RyosukeSAMA/github-ai/releases?per_page=50';
const PREFIX='/RyosukeSAMA/github-ai/releases/download/';
const MAX_DOWNLOAD=1200*1024*1024;
function assetURL(value){
  const url=new URL(value);
  if(url.protocol!=='https:'||url.hostname!=='github.com'||!url.pathname.startsWith(PREFIX)||url.username||url.password||url.search||url.hash)throw new Error('The installer is not from the official Pantheon release repository.');
  return url.href;
}
async function checksum(file){const hash=createHash('sha256');for await(const chunk of createReadStream(file))hash.update(chunk);return hash.digest('hex');}
async function limitedText(response,limit){let size=0;const chunks=[];if(!response.body)throw new Error('Update metadata is empty.');for await(const chunk of response.body){size+=chunk.length;if(size>limit)throw new Error('Update metadata exceeds its size limit.');chunks.push(Buffer.from(chunk));}return Buffer.concat(chunks).toString('utf8');}
class UpdateManager{
  constructor({directory,version,platform=process.platform,arch=process.arch,fetchImpl=fetch,onChange=()=>{}}){
    Object.assign(this,{directory,version,platform,arch,fetchImpl,onChange});this.state={phase:'idle',version,available:false,channel:'stable'};this.releases=[];this.controller=null;this.checking=null;this.downloadDone=Promise.resolve();
  }
  snapshot(){return structuredClone(this.state);}
  change(value){Object.assign(this.state,value);this.onChange(this.snapshot());}
  async request(url,signal){
    let current=url;
    for(let redirects=0;redirects<6;redirects++){
      const parsed=new URL(current),allowed=['github.com','api.github.com','release-assets.githubusercontent.com','objects.githubusercontent.com'];
      if(parsed.protocol!=='https:'||!allowed.includes(parsed.hostname)||parsed.username||parsed.password)throw new Error('Unsafe update download redirect.');
      const response=await this.fetchImpl(current,{headers:{accept:parsed.hostname==='api.github.com'?'application/vnd.github+json':'application/octet-stream'},redirect:'manual',signal});
      if([301,302,303,307,308].includes(response.status)){const location=response.headers.get('location');await response.body?.cancel();if(!location)throw new Error('Update redirect has no destination.');current=new URL(location,current).href;continue;}
      if(!response.ok)throw new Error('Update service returned HTTP '+response.status+'.');return response;
    }throw new Error('Too many update download redirects.');
  }
  async check(channel='stable'){
    if(!['stable','beta'].includes(channel))throw new Error('Choose the Stable or Beta update channel.');
    if(this.controller)throw new Error('Finish or cancel the current download first.');
    if(this.checking)return this.checking;
    this.checking=(async()=>{
      this.change({phase:'checking',channel,error:null});
      try{
        const response=await this.request(API,AbortSignal.timeout(15000));
        const releases=JSON.parse(await limitedText(response,4*1024*1024));if(!Array.isArray(releases))throw new Error('Invalid release metadata.');this.releases=releases;
        const result=selectRelease(releases,this.version,this.platform,this.arch,channel);
        this.change({...result,phase:result.available?'available':'current',error:null});return this.snapshot();
      }catch(error){this.change({phase:'failed',available:false,error:error.message});throw error;}
    })();try{return await this.checking;}finally{this.checking=null;}
  }
  async expectedHash(asset,release,signal){
    if(/^sha256:[a-f0-9]{64}$/i.test(asset.digest||''))return asset.digest.slice(7).toLowerCase();
    const manifest=release.assets?.find(item=>item.name==='SHA256SUMS.txt');
    if(!manifest)throw new Error('No verified checksum is published. Use the official release page for this version.');
    const response=await this.request(assetURL(manifest.browser_download_url),signal),raw=await limitedText(response,1024*1024);
    const row=raw.split(/\r?\n/).map(line=>/^([a-f0-9]{64})\s+\*?(.+)$/i.exec(line.trim())).find(match=>match?.[2]===asset.name);
    if(!row)throw new Error('The installer has no matching checksum.');return row[1].toLowerCase();
  }
  async download(assetId,{rollback=false}={}){
    if(this.controller||this.checking)throw new Error('An update operation is already running.');
    const release=this.releases.find(item=>!item.draft&&item.assets?.some(asset=>asset.id===assetId));
    const asset=release?.assets.find(item=>item.id===assetId);
    const candidate=release&&selectRelease([release],'0.0.0',this.platform,this.arch,this.state.channel);
    if(!asset||!candidate.assets?.some(item=>item.id===assetId)||!/^Pantheon-[A-Za-z0-9._-]+$/.test(asset.name))throw new Error('Choose a listed installer for this computer.');
    const order=compareVersions(release.tag_name,this.version);
    if(rollback?order!==-1:order!==1)throw new Error(rollback?'Choose an earlier version for recovery.':'Choose a newer version to update.');
    if(!Number.isSafeInteger(asset.size)||asset.size<=0||asset.size>MAX_DOWNLOAD)throw new Error('Installer size is outside the download limit.');
    const controller=new AbortController();this.controller=controller;
    let resolveDownload;this.downloadDone=new Promise(resolve=>{resolveDownload=resolve;});
    const temporary=path.join(this.directory,randomUUID()+'.partial');let handle;
    this.change({phase:'downloading',error:null,downloaded:0,total:asset.size,asset_name:asset.name,download_version:release.tag_name,rollback});
    try{
      const signal=AbortSignal.any([controller.signal,AbortSignal.timeout(10*60*1000)]);
      const expected=await this.expectedHash(asset,release,signal);await fs.mkdir(this.directory,{recursive:true,mode:0o700});
      if((await fs.lstat(this.directory)).isSymbolicLink())throw new Error('Update cache cannot be a symbolic link.');
      handle=await fs.open(temporary,'wx',0o600);
      const response=await this.request(assetURL(asset.browser_download_url),signal),hash=createHash('sha256');let size=0,last=0;
      if(!response.body)throw new Error('Installer download is empty.');
      for await(const chunk of response.body){
        signal.throwIfAborted();size+=chunk.length;if(size>asset.size||size>MAX_DOWNLOAD)throw new Error('Installer exceeds its published size.');
        hash.update(chunk);await handle.write(chunk);if(Date.now()-last>150){last=Date.now();this.change({downloaded:size});}
      }
      signal.throwIfAborted();if(size!==asset.size||hash.digest('hex')!==expected)throw new Error('Installer verification failed. The incomplete file was removed; retry the download.');
      await handle.sync();await handle.close();handle=null;
      const file=path.join(this.directory,asset.name);await fs.rename(temporary,file);
      const record={id:randomUUID(),version:release.tag_name,name:asset.name,sha256:expected,size,path:file,downloaded_at:Date.now(),rollback};
      const records=(await this.history()).filter(item=>item.name!==record.name);records.unshift(record);
      const index=path.join(this.directory,randomUUID()+'.index');await fs.writeFile(index,JSON.stringify(records.slice(0,20)),{mode:0o600});await fs.rename(index,path.join(this.directory,'downloads.json'));
      this.change({phase:'downloaded',downloaded:size,record:{id:record.id,name:record.name,version:record.version,size},error:null});return this.snapshot();
    }catch(error){this.change({phase:controller.signal.aborted?'cancelled':'failed',error:controller.signal.aborted?'Download cancelled.':error.message});throw error;}
    finally{try{await handle?.close();await fs.rm(temporary,{force:true});}finally{this.controller=null;resolveDownload();}}
  }
  cancel(){this.controller?.abort();}
  async shutdown(){this.cancel();await this.downloadDone;}
  async cleanIncomplete(){try{if((await fs.lstat(this.directory)).isSymbolicLink())throw new Error('Update cache cannot be a symbolic link.');for(const name of await fs.readdir(this.directory))if(/^[a-f0-9-]{36}\.partial$/.test(name))await fs.rm(path.join(this.directory,name),{force:true});}catch(error){if(error.code!=='ENOENT')throw error;}}
  async history(){try{const records=JSON.parse(await fs.readFile(path.join(this.directory,'downloads.json'),'utf8'));return Array.isArray(records)?records:[];}catch{return [];}}
  async verifiedFile(id){
    const record=(await this.history()).find(item=>item.id===id);if(!record||path.dirname(record.path)!==this.directory||path.basename(record.path)!==record.name)throw new Error('Installer is not in the update cache.');
    const stat=await fs.lstat(record.path);if(!stat.isFile()||stat.isSymbolicLink()||stat.size!==record.size||await checksum(record.path)!==record.sha256)throw new Error('The cached installer changed. Download it again.');return record.path;
  }
  recoveryVersions(){return this.releases.filter(item=>!item.draft&&compareVersions(item.tag_name,this.version)===-1).map(item=>selectRelease([item],'0.0.0',this.platform,this.arch,this.state.channel)).filter(item=>item.assets?.length).slice(0,8);}
}
module.exports={UpdateManager,assetURL,checksum};
