// Dependency-free, local-only Chromium capture and interaction checks.
// Run from a repository root (the checkout to capture) with the chrome-headless-shell path and a mode:
//   check          assertions + README screenshots (docs/screenshots/dashboard-*.png) + docs/screenshots/ui-checks.json
//   keyviews:NAME  only the three comparison crops -> docs/screenshots/before_after/NAME-{desktop-top,phone-cells-dark,phone-empty}.png
// The script may be run against an older checkout (e.g. `git archive <rev> dashboard | tar -x`) to capture a "before".
import {spawn} from 'node:child_process';
import {createServer} from 'node:http';
import {readFile, writeFile, mkdir} from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
const mode = process.argv[3] || 'check';
const keyLabel = mode.startsWith('keyviews:') ? mode.slice(9) : null;
assert.ok(mode === 'check' || /^[a-z0-9-]+$/.test(keyLabel || ''), 'mode must be check or keyviews:<name>');
const root = process.cwd(), out = path.join(root, 'docs/screenshots');
const server = createServer(async (req,res) => {
  const u = new URL(req.url, 'http://127.0.0.1');
  if (u.pathname === '/timeout.json') return;
  if (u.pathname === '/empty.json') { res.setHeader('Content-Type','application/json'); res.end(JSON.stringify({view:'detail',cells:[],suppressed:[]})); return; }
  if (u.pathname === '/slow.json') { await new Promise(r=>setTimeout(r,1500)); u.pathname='/dashboard/data/aggregates.sample.json'; }
  const file = path.resolve(root, '.' + (u.pathname.endsWith('/') ? u.pathname+'index.html' : u.pathname));
  if (!file.startsWith(root + path.sep)) {res.writeHead(403).end();return;}
  try { const data=await readFile(file); res.setHeader('Content-Type',file.endsWith('.json')?'application/json':file.endsWith('.html')?'text/html':'application/octet-stream'); res.end(data); }
  catch {res.writeHead(404).end();}
});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const base=`http://127.0.0.1:${server.address().port}`;
await mkdir('server/var/ui',{recursive:true});
await mkdir(path.join(out,'before_after'),{recursive:true});
const browser=spawn(process.argv[2],['--no-sandbox','--disable-gpu','--hide-scrollbars','--disable-background-networking','--disable-component-update','--no-first-run','--remote-debugging-address=127.0.0.1','--remote-debugging-port=0',`--user-data-dir=${root}/server/var/ui/profile`,'about:blank'],{env:{...process.env,TMPDIR:`${root}/server/var/ui`},stdio:['ignore','ignore','pipe']});
let ws, seq=0; const pending=new Map(), errors=[];
try {
 const endpoint=await new Promise((resolve,reject)=>{let log=''; browser.stderr.on('data',d=>{log+=d; const m=log.match(/DevTools listening on (ws:\/\/[^\s]+)/);if(m)resolve(m[1]);}); browser.on('error',reject); browser.on('exit',c=>reject(Error(`Chromium exited ${c}`)));});
 const port=new URL(endpoint).port;
 const target=await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`,{method:'PUT'})).json();
 ws=new WebSocket(target.webSocketDebuggerUrl);
 await new Promise(r=>ws.addEventListener('open',r,{once:true}));
 ws.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result);}if(m.method==='Runtime.exceptionThrown')errors.push(m.params);});
 const cdp=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
 const evaluate=async expression=>{const r=await cdp('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
 const wait=async expression=>{for(let i=0;i<400;i++){if(await evaluate(expression))return;await new Promise(r=>setTimeout(r,50));}throw Error(`Timed out: ${expression}`);};
 const go=async (query='',width=1440)=>{await cdp('Emulation.setDeviceMetricsOverride',{width,height:960,deviceScaleFactor:1,mobile:false});await cdp('Page.navigate',{url:base+'/dashboard/?'+query});await wait('document.readyState==="complete" && (document.querySelector("#content") && !document.querySelector("#content").hidden || document.querySelector("#load-error") && !document.querySelector("#load-error").hidden)');};
 const shot=async (name,{y=0,maxHeight=Infinity}={})=>{const m=await cdp('Page.getLayoutMetrics');const r=await cdp('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:0,y,width:m.cssContentSize.width,height:Math.min(maxHeight,m.cssContentSize.height-y),scale:1}});await writeFile(path.join(out,name),Buffer.from(r.data,'base64'));};
 const top=async sel=>evaluate(`Math.round(document.querySelector(${JSON.stringify(sel)}).getBoundingClientRect().top + scrollY)`);
 await cdp('Page.enable');await cdp('Runtime.enable');

 if(keyLabel) {
  // 1) desktop: header, section links, hero and the signature slope chart
  await go('theme=light',1440);
  await shot(`before_after/${keyLabel}-desktop-top.png`,{maxHeight:(await top('#cells-card'))-8});
  // 2) phone, dark: scatter axis and the first leaderboard cards
  await go('theme=dark',390);
  const y0=(await top('#scatter-wrap'))-40;
  await shot(`before_after/${keyLabel}-phone-cells-dark.png`,{y:y0,maxHeight:1300});
  // 3) phone: an aggregate with no cells at all
  await go('data=/empty.json&theme=light',390);
  await shot(`before_after/${keyLabel}-phone-empty.png`,{maxHeight:1100});
  console.log(`keyviews:${keyLabel}: 3 crops written`);
 } else {
  const report=[];
  for(const [device,width] of [['desktop',1440],['phone',390]])for(const theme of ['light','dark']) {
   await go(`theme=${theme}`,width);
   await shot(`dashboard-${device}-${theme}.png`,{maxHeight:device==='phone'?3000:Infinity});
   if(device==='phone') assert.ok(await evaluate('document.querySelector("#reset-filters").getBoundingClientRect().height >= 44'));
   const contrast=await evaluate(`(() => {
    const css=getComputedStyle(document.documentElement);
    const rgb=name=>css.getPropertyValue(name).trim().slice(1).match(/../g).map(x=>parseInt(x,16)/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4);
    const lum=name=>rgb(name).reduce((s,x,i)=>s+x*[.2126,.7152,.0722][i],0);
    const pairs=['--ink','--ink-2','--muted','--accent','--over-text','--under-text'].flatMap(fg=>['--surface','--surface-2','--page'].map(bg=>[fg,bg]));
    pairs.push(['--syn-ink','--syn-bg'],['--pub-ink','--pub-bg']);
    return Math.min(...pairs.map(([fg,bg])=>(Math.max(lum(fg),lum(bg))+.05)/(Math.min(lum(fg),lum(bg))+.05)));
   })()`);
   assert.ok(contrast>=4.5, `AA text contrast: ${theme} ${contrast}`);
   // slope: the SYNTHETIC watermark sits below every rank label
   assert.ok(await evaluate(`(() => { const t=[...document.querySelectorAll("#slope text")].find(x=>x.textContent==="SYNTHETIC SAMPLE"); const low=Math.max(...[...document.querySelectorAll("#slope .slope-label")].map(x=>x.getBoundingClientRect().bottom)); return t && t.getBoundingClientRect().top >= low; })()`), `slope watermark overlap ${device}`);
   // scatter: both ends of the log cost axis carry a price label
   assert.ok(await evaluate(`[...document.querySelectorAll("#scatter text")].filter(t=>/^\\$/.test(t.textContent)).length >= 3`), `scatter ticks ${device}`);
   report.push({device,theme,width,minTextContrast:+contrast.toFixed(2),overflow:await evaluate('document.documentElement.scrollWidth > innerWidth')});
  }
  // phone cards: secondary metrics in two columns from 360px, one column below
  await go('theme=light',390);
  assert.ok(await evaluate('(() => { const o=document.querySelectorAll("#board tbody tr:first-child td.opt"); return o[0].getBoundingClientRect().top === o[1].getBoundingClientRect().top; })()'), 'two metric columns at 390');
  await go('theme=light',320);
  assert.ok(await evaluate('(() => { const o=document.querySelectorAll("#board tbody tr:first-child td.opt"); return o[1].getBoundingClientRect().top > o[0].getBoundingClientRect().top; })()'), 'one metric column at 320');
  for(const width of [320,375,640,768,1024]){await go('theme=light',width);assert.equal(await evaluate('document.documentElement.scrollWidth > innerWidth'),false,`overflow at ${width}`);}
  // scroll regions: focusable only while they overflow
  await go('theme=light',1440);
  assert.equal(await evaluate('document.querySelector("#board-scroll").hasAttribute("tabindex")'),false,'no dead tab stop at 1440');
  await go('theme=light',768);
  assert.equal(await evaluate('document.querySelector("#board-scroll").getAttribute("role")'),'region');
  await evaluate('document.querySelector("#board-scroll").focus()');
  assert.equal(await evaluate('document.activeElement.id'),'board-scroll');
  await go('theme=dark');
  await evaluate('document.querySelector(".slope-g").focus()');
  await cdp('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape'});
  assert.equal(await evaluate('getComputedStyle(document.querySelector("#slope-tip")).display'),'none');
  await cdp('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
  assert.equal(await evaluate('getComputedStyle(document.querySelector(".mark-line")).transitionDuration'),'0s');
  await evaluate('document.querySelector("#scatter").focus()');
  await cdp('Input.dispatchKeyEvent',{type:'keyDown',key:'ArrowRight'});
  assert.ok(await evaluate('document.querySelector("#scatter-live").textContent'));
  await cdp('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape'});
  assert.equal(await evaluate('getComputedStyle(document.querySelector("#scatter-tip")).display'),'none');
  await cdp('Emulation.setEmulatedMedia',{features:[]});
  await evaluate('document.querySelector("#reset-filters").click()');
  assert.equal(await evaluate('document.querySelector("#f-l2").value'),'all');
  await evaluate('document.querySelector("#f-src").value="benchmark";document.querySelector("#f-src").dispatchEvent(new Event("change"))');
  assert.ok(await evaluate('document.querySelector("#filter-summary").textContent.includes("공개")'));
  assert.ok(await evaluate('/^스냅샷 \\d{4}-\\d\\d-\\d\\d \\d\\d:\\d\\d UTC/.test(document.querySelector("#snapshot-meta").textContent)'),'snapshot time format');
  await go('view=overview&theme=light',390);assert.equal(await evaluate('document.querySelector("#gate-card").hidden'),false);await shot('dashboard-overview-phone.png');
  await go('data=/empty.json&theme=light',390);
  assert.equal(await evaluate('document.querySelector("#board-empty").hidden'),false);assert.equal(await evaluate('document.querySelector("#empty-sample").hidden'),false);
  assert.equal(await evaluate('document.querySelector("#main").innerText.includes("?")'),false,'no raw "?" placeholders in an empty aggregate');
  assert.equal(await evaluate('document.querySelector("#f-src").selectedOptions[0].textContent'),'데이터 없음');
  assert.equal(await evaluate('document.querySelector(".section-nav a[href=\\"#seed-card\\"]").hidden'),true,'no link to a hidden section');
  await shot('dashboard-empty-phone.png');
  await go('data=/missing.json&theme=light',390);assert.equal(await evaluate('document.querySelector("#main").getAttribute("aria-busy")'),'false');
  assert.equal(await evaluate('document.querySelector("#view-pill").hidden'),true,'no empty view pill on error');
  await shot('dashboard-error-phone.png');
  await evaluate('document.querySelector("#retry-load").click()');
  await wait('document.readyState==="complete" && document.querySelector("#load-error") && !document.querySelector("#load-error").hidden');
  await evaluate('document.querySelector("#error-sample").click()');
  await wait('document.querySelector("#content") && !document.querySelector("#content").hidden');
  await go('data=/timeout.json&theme=light',390);
  assert.equal(await evaluate('document.querySelector("#load-error").hidden'),false);
  assert.equal(await evaluate('document.querySelector("#main").getAttribute("aria-busy")'),'false');
  assert.ok(await evaluate('document.querySelector("#load-error-msg").textContent.includes("15초")'),'timeout message');
  await cdp('Page.navigate',{url:base+'/dashboard/?data=/slow.json&theme=light'});
  await wait('document.querySelector("#loading") && !document.querySelector("#loading").hidden');
  assert.ok(await evaluate('document.querySelector("#strip").classList.contains("pending") && document.querySelector("#view-pill").hidden'),'neutral loading strip, no empty pill');
  await shot('dashboard-loading-phone.png');
  await wait('!document.querySelector("#content").hidden');
  assert.equal(errors.length,0,JSON.stringify(errors));
  assert.ok(report.every(x=>!x.overflow));
  await writeFile(path.join(out,'ui-checks.json'),JSON.stringify({mode,viewports:report,javascriptErrors:errors.length,checks:['320/375/390/640/768/1024/1440px no page overflow','light/dark text tokens AA >= 4.5','slope watermark below rank labels','scatter cost axis labelled at both ends','phone cards: two metric columns >= 360px, one at 320px','table scroll region focusable only when it overflows (1440 no, 768 yes)','scatter arrows and Escape','slope Escape','reduced motion','filter reset and source change','snapshot time as UTC','overview gate','empty dataset: no raw "?", layer select says no data, no link to hidden section','HTTP error: no empty pill, retry and sample recovery','15s timeout message','loading: neutral strip, no empty pill']},null,2)+'\n');
  console.log('check: screenshots and checks complete');
 }
} finally {ws?.close();browser.kill('SIGTERM');await new Promise(r=>browser.exitCode!==null?r():browser.once('exit',r));await new Promise(r=>server.close(r));}
