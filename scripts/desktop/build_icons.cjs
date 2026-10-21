'use strict';
// Rasterize the existing brand mark inside the editable native icon frame.
// Run after installing desktop dependencies and Playwright Chromium.
const fs = require('node:fs/promises');
const path = require('node:path');
const {createRequire} = require('node:module');
const repo = path.resolve(__dirname, '../..');
const requireDesktop = createRequire(path.join(repo, 'desktop/package.json'));
const {chromium} = requireDesktop('playwright');
const assets = path.join(repo, 'desktop/assets');

async function main() {
  const source = await fs.readFile(path.join(assets, 'icon.svg'), 'utf8');
  const mark = await fs.readFile(path.join(repo, 'docs/images/pantheon-mark.png'));
  const svg = source.replace('../../docs/images/pantheon-mark.png', 'data:image/png;base64,' + mark.toString('base64'));
  const browser = await chromium.launch(process.env.PANTHEON_ICON_BROWSER ? {executablePath:process.env.PANTHEON_ICON_BROWSER} : {});
  const images = new Map();
  try {
    const page = await browser.newPage();
    for (const size of [16, 24, 32, 48, 64, 128, 256, 512, 1024]) {
      const base64 = await page.evaluate(async ({svg, size}) => {
        const img = new Image();
        img.src = 'data:image/svg+xml;base64,' + btoa(svg);
        await img.decode();
        const canvas = document.createElement('canvas');
        canvas.width = canvas.height = size;
        canvas.getContext('2d').drawImage(img, 0, 0, size, size);
        return canvas.toDataURL('image/png').split(',')[1];
      }, {svg, size});
      images.set(size, Buffer.from(base64, 'base64'));
    }
  } finally {
    await browser.close();
  }
  await fs.writeFile(path.join(assets, 'icon.png'), images.get(1024));
  await fs.writeFile(path.join(repo, 'docs/desktop/icon-preview.png'), images.get(256));

  const chunks = [['icp4',16],['icp5',32],['icp6',64],['ic07',128],['ic08',256],['ic09',512],['ic10',1024],['ic11',32],['ic12',64],['ic13',256],['ic14',512]].map(([type,size]) => {
    const png = images.get(size), header = Buffer.alloc(8);
    header.write(type); header.writeUInt32BE(png.length + 8, 4);
    return Buffer.concat([header, png]);
  });
  const icnsHeader = Buffer.alloc(8);
  icnsHeader.write('icns'); icnsHeader.writeUInt32BE(8 + chunks.reduce((sum,chunk)=>sum+chunk.length,0), 4);
  await fs.writeFile(path.join(assets, 'icon.icns'), Buffer.concat([icnsHeader, ...chunks]));

  const icoSizes = [16,24,32,48,64,128,256], icoHeader = Buffer.alloc(6);
  icoHeader.writeUInt16LE(1, 2); icoHeader.writeUInt16LE(icoSizes.length, 4);
  let offset = 6 + icoSizes.length * 16;
  const entries = icoSizes.map(size => {
    const png = images.get(size), entry = Buffer.alloc(16);
    entry[0] = entry[1] = size === 256 ? 0 : size;
    entry.writeUInt16LE(1, 4); entry.writeUInt16LE(32, 6);
    entry.writeUInt32LE(png.length, 8); entry.writeUInt32LE(offset, 12); offset += png.length;
    return entry;
  });
  await fs.writeFile(path.join(assets, 'icon.ico'), Buffer.concat([icoHeader, ...entries, ...icoSizes.map(size=>images.get(size))]));
  console.log('Built rounded PNG, macOS ICNS and Windows ICO from desktop/assets/icon.svg.');
}
main().catch(error=>{console.error(error);process.exitCode=1;});
