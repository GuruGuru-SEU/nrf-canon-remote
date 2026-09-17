import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import MarkdownIt from 'markdown-it';
import {build} from 'esbuild';
import {chromium} from 'playwright';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const dir = path.join(root, 'output/electrical');
const repo = 'https://github.com/GuruGuru-SEU/nrf-canon-remote/blob/main/';
const site = 'https://guruguru-seu.github.io/nrf-canon-remote/electrical/';
const pages = [
  {source:'原理图-v0.1.md', file:'schematic-v0.1.html', label:'原理图', description:'nRF52832 遥控器文字原理图、引脚分配与 PCB 布局原则。'},
  {source:'BOM-v0.1.md', file:'bom-v0.1.html', label:'BOM', description:'nRF52832 遥控器完整电气 BOM，包含单台用量、采购状态和器件用途。'},
];
const esc = s => s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const css = await fs.readFile(path.join(root, 'scripts/electrical_docs.css'), 'utf8');
const md = new MarkdownIt({html:false, linkify:false, typographer:false});
let browser;

async function renderDiagrams(sources) {
  if (!sources.length) return [];
  const bundle = await build({stdin:{contents:"import mermaid from 'mermaid'; window.mermaid = mermaid;",resolveDir:root},
    bundle:true,write:false,format:'iife',platform:'browser',minify:true,logLevel:'silent'});
  browser = await chromium.launch({channel:'chrome',headless:true});
  const page = await browser.newPage({viewport:{width:1400,height:1000}});
  await page.setContent('<html><head><meta charset="utf-8"></head><body></body></html>');
  await page.addScriptTag({content:bundle.outputFiles[0].text});
  await page.evaluate(() => window.mermaid.initialize({
    startOnLoad:false,securityLevel:'strict',theme:'base',
    themeVariables:{primaryColor:'#eef7f5',primaryBorderColor:'#9abbb5',primaryTextColor:'#173b38',
      lineColor:'#668d87',fontFamily:'Arial, PingFang SC, Microsoft YaHei, sans-serif',fontSize:'16px'},
    flowchart:{htmlLabels:false,curve:'basis',useMaxWidth:true,nodeSpacing:25,rankSpacing:40},
  }));
  const diagrams=[];
  for (let i=0;i<sources.length;i++) {
    // Stack the long signal chain vertically so labels remain readable on a document page.
    const code=sources[i].replace(/^flowchart LR\s*$/m,'flowchart TB');
    const svg = await page.evaluate(async ({code,index}) => (await window.mermaid.render('power-flow-'+index,code)).svg,{code,index:i});
    diagrams.push(svg.replace('<svg ', '<svg role="img" aria-label="遥控器电源与功能框图" '));
  }
  await browser.close();browser=undefined;
  return diagrams;
}

function relativeLink(href, spec) {
  if (/^(?:[a-z][a-z0-9+.-]*:|#)/i.test(href)) return href;
  if (href === 'schematic-drawing-v0.1.html') return href;
  const hashIndex=href.indexOf('#');
  const file=decodeURIComponent(hashIndex<0?href:href.slice(0,hashIndex));
  const hash=hashIndex<0?'':href.slice(hashIndex);
  const target=path.resolve(dir,file);
  const other=pages.find(p=>path.resolve(dir,p.source)===target);
  if(other) return other.file+hash;
  const rel=path.relative(root,target).split(path.sep).join('/');
  if(rel.startsWith('../')) throw new Error('Link escapes repository: '+href);
  return repo+rel.split('/').map(encodeURIComponent).join('/')+hash;
}

function makeHtml(spec, tokens, diagrams) {
  const headings=[],ids=new Map();
  let title='',diagramIndex=0;
  for(let i=0;i<tokens.length;i++) {
    const t=tokens[i];
    if(t.type==='heading_open') {
      const text=tokens[i+1].children.filter(c=>['text','code_inline'].includes(c.type)).map(c=>c.content).join('');
      if(t.tag==='h1') title=text;
      const base=text.toLowerCase().replace(/[^\p{L}\p{N}\s-]/gu,'').trim().replace(/\s+/g,'-');
      const count=ids.get(base)||0;ids.set(base,count+1);
      const id=base+(count?'-'+count:'');t.attrSet('id',id);
      if(['h2','h3'].includes(t.tag))headings.push({text,id,sub:t.tag==='h3'});
    }
    if(t.type==='inline') for(const c of t.children||[]) {
      if(c.type==='link_open') c.attrSet('href',relativeLink(c.attrGet('href'),spec));
    }
  }
  const defaultFence=md.renderer.rules.fence;
  md.renderer.rules.fence=(ts,index,options,env,self)=> {
    if(ts[index].info.trim()==='mermaid') return '<figure class="diagram">'+diagrams[diagramIndex++]+'<figcaption>电源与功能框图</figcaption></figure>';
    return defaultFence(ts,index,options,env,self);
  };
  md.renderer.rules.table_open=()=>'<div class="table-scroll" tabindex="0" role="region" aria-label="可横向滚动的数据表"><table>';
  md.renderer.rules.table_close=()=>'</table></div>';
  const content=md.renderer.render(tokens,md.options,{});
  md.renderer.rules.fence=defaultFence;
  const nav='<a href="schematic-drawing-v0.1.html">图纸</a>'+pages.map(p=>`<a ${p===spec?'aria-current="page"':''} href="${p.file}">${p.label}</a>`).join('');
  const toc=headings.map(h=>`<a class="${h.sub?'sub':''}" href="#${esc(h.id)}">${esc(h.text)}</a>`).join('');
  return `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(title)} | nRF Canon Remote</title>
<meta name="description" content="${esc(spec.description)}"><meta name="color-scheme" content="light">
<link rel="canonical" href="${site+spec.file}"><style>${css}</style></head>
<body><a class="skip" href="#document">跳至正文</a>
<header class="topbar"><a class="project" href="../preview.html"><span class="project-mark">nRF</span><span>CANON REMOTE<small>GuruGuru-SEU / 电气设计</small></span></a><nav aria-label="设计文档">${nav}</nav></header>
<div class="layout"><aside><div class="toc-label">文档目录 <span>v0.1</span></div><details open class="toc"><summary>查看目录</summary><nav aria-label="文档目录">${toc}</nav></details><a class="source" href="${repo+'output/electrical/'+encodeURIComponent(spec.source)}">查看 Markdown 源文件 ↗</a></aside>
<main id="document"><div class="doc-meta"><span class="draft">设计草案</span><span>版本 v0.1</span><span>用于团队审阅</span></div><article>${content}</article><footer>nRF Canon Remote · 电气设计 v0.1</footer></main></div>
<script>
const toc=document.querySelector('.toc');
const mq=matchMedia('(max-width: 900px)');
function adapt(){toc.open=!mq.matches;} adapt(); mq.addEventListener('change',adapt);
const links=[...document.querySelectorAll('.toc a')];
const observer=new IntersectionObserver(entries=>{for(const e of entries)if(e.isIntersecting){for(const a of links)a.classList.toggle('active',decodeURIComponent(a.hash.slice(1))===e.target.id);}},{rootMargin:'-80px 0px -65% 0px'});
document.querySelectorAll('article h2, article h3').forEach(h=>observer.observe(h));
</script></body></html>\n`;
}

try {
  for(const spec of pages) {
    const source=await fs.readFile(path.join(dir,spec.source),'utf8');
    const tokens=md.parse(source,{});
    const diagrams=await renderDiagrams(tokens.filter(t=>t.type==='fence'&&t.info.trim()==='mermaid').map(t=>t.content));
    const output=makeHtml(spec,tokens,diagrams);
    await fs.writeFile(path.join(dir,spec.file),output);
    console.log(`${spec.file}: ${tokens.filter(t=>t.type==='table_open').length} tables / ${diagrams.length} diagrams / ${Buffer.byteLength(output)} bytes`);
  }
} finally {
  if(browser)await browser.close();
}
