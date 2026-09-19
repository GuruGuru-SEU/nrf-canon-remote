import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {chromium} from 'playwright';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const out=path.join(root,'output/electrical');
const tmp=path.join(root,'tmp/docs/schematic-qa');
await fs.mkdir(tmp,{recursive:true});
const manifest=JSON.parse(await fs.readFile(path.join(out,'schematic-manifest.json'),'utf8'));
const browser=await chromium.launch({channel:'chrome',headless:true});
const results={svg:[],desktop:{},mobile:{}};
try {
  const page=await browser.newPage({viewport:{width:1700,height:1400}});
  for(const sheet of manifest.sheets){
    await page.goto(pathToFileURL(path.join(out,'schematic-assets',sheet.file)).href);
    await page.evaluate(()=>{const svg=document.querySelector('svg');svg.style.width='1680px';svg.style.height='auto';});
    const supplierTexts=await page.locator('svg text').allTextContents();
    const expectedLabels=sheet.supplier_labels.map(l=>l.text);
    for(const label of new Set(expectedLabels)){
      assert.equal(supplierTexts.filter(t=>t===label).length,expectedLabels.filter(t=>t===label).length,
        sheet.file+' supplier label coverage: '+label);
    }
    const quality=await page.evaluate(()=>{
      const svg=document.querySelector('svg'), bounds=svg.getBoundingClientRect();
      const texts=[...svg.querySelectorAll('text')].map(t=>({text:t.textContent,r:t.getBoundingClientRect().toJSON()}));
      const overlaps=[],outside=[];
      for(let i=0;i<texts.length;i++){
        const a=texts[i];
        if(a.r.left<bounds.left-1||a.r.right>bounds.right+1||a.r.top<bounds.top-1||a.r.bottom>bounds.bottom+1)outside.push(a.text);
        for(let j=i+1;j<texts.length;j++){
          const b=texts[j];
          const w=Math.min(a.r.right,b.r.right)-Math.max(a.r.left,b.r.left),h=Math.min(a.r.bottom,b.r.bottom)-Math.max(a.r.top,b.r.top);
          if(w>1&&h>1)overlaps.push([a.text,b.text]);
        }
      }
      return {texts:texts.length,overlaps,outside,ratio:bounds.width/bounds.height};
    });
    assert.deepEqual(quality.overlaps,[],sheet.file+' text overlaps');
    assert.deepEqual(quality.outside,[],sheet.file+' clipped labels');
    assert.ok(quality.ratio>1.3&&quality.ratio<1.7,sheet.file+' unexpected page bounds');
    await page.locator('svg').screenshot({path:path.join(tmp,sheet.file.replace('.svg','.png'))});
    results.svg.push({file:sheet.file,...quality});
  }
  await page.setViewportSize({width:1512,height:1080});
  const url=pathToFileURL(path.join(out,'schematic-drawing-v0.1.html')).href;
  const errors=[],requests=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(/^https?:/.test(r.url()))requests.push(r.url());});
  await page.goto(url);
  assert.equal(await page.locator('.sheet.active').count(),1);
  for(let i=0;i<7;i++){
    await page.locator('.sheets-nav a').nth(i).click();
    assert.equal(await page.locator('.sheet.active').getAttribute('id'),'sheet-'+(i+1));
    assert.equal(await page.locator('#notes-list li').count(),4);
    assert.ok((await page.locator('#download').getAttribute('href')).endsWith(manifest.sheets[i].file));
  }
  await page.locator('#reference').fill('Q100');await page.locator('#search button').click();
  assert.equal(await page.locator('.sheet.active').getAttribute('id'),'sheet-2');
  assert.equal(await page.locator('.sheet.active .found').textContent(),'Q100');
  await page.locator('#reference').fill('U200');await page.locator('#search button').click();
  assert.equal(await page.locator('#search-result a').count(),3);
  await page.locator('#reference').fill('no-such-part');await page.locator('#search button').click();
  assert.match(await page.locator('#search-result').textContent(),/未找到/);
  await page.locator('.sheets-nav a').nth(0).click();await page.locator('#fit').click();
  await page.locator('#reference').fill('');
  await page.locator('#search-result').evaluate(e=>e.replaceChildren());
  const old=await page.locator('#stage').evaluate(e=>e.clientWidth);
  await page.locator('#zoom-in').click();
  const enlarged=await page.locator('#stage').evaluate(e=>e.clientWidth);
  assert.ok(enlarged>old*1.2);
  await page.locator('#fit').click();
  await page.screenshot({path:path.join(tmp,'viewer-desktop.png'),fullPage:true});
  results.desktop={pages:7,zoomWorks:true,partSearchWorks:true,externalRequests:requests,consoleErrors:errors};
  assert.deepEqual(errors,[]);assert.deepEqual(requests,[]);

  // SVGs remain available in the document for printing all sheets and without JS.
  await page.emulateMedia({media:'print'});
  assert.equal(await page.locator('.sheet:visible').count(),7);
  await page.emulateMedia({media:'screen'});
  await page.setViewportSize({width:390,height:844});
  await page.locator('#sheet-select').selectOption('5');
  assert.equal(await page.locator('.sheet.active').getAttribute('id'),'sheet-6');
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  await page.locator('#zoom-in').click();
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  await page.screenshot({path:path.join(tmp,'viewer-mobile.png'),fullPage:true});
  results.mobile={pageNavigation:true,noDocumentOverflow:true};
  for(const file of ['schematic-v0.1.html','bom-v0.1.html']){
    await page.goto(pathToFileURL(path.join(out,file)).href);
    assert.equal(await page.locator('header nav a[href="schematic-drawing-v0.1.html"]').count(),1);
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,file+' mobile overflow');
  }
  const nojs=await browser.newPage({javaScriptEnabled:false});
  await nojs.goto(url);assert.equal(await nojs.locator('.sheet:visible').count(),7);
  await fs.writeFile(path.join(tmp,'results.json'),JSON.stringify(results,null,2));
  console.log('Passed: 7 SVGs, no overlapping/clipped text, viewer navigation/zoom/search, mobile, print and no-JS fallback.');
}finally{await browser.close();}
