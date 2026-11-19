import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const req=createRequire(path.join(root,'package.json'));
const React=req('react'),{renderToStaticMarkup}=req('react-dom/server');
const {createServer}=await import(pathToFileURL(req.resolve('vite')).href);
const {default:react}=await import(pathToFileURL(req.resolve('@vitejs/plugin-react')).href);
const server=await createServer({root,configFile:false,envDir:false,publicDir:false,cacheDir:path.join(root,'.qa_cache'),plugins:[react()],server:{middlewareMode:true,watch:null},appType:'custom'});
const load=city=>JSON.parse(fs.readFileSync(path.join(root,`public/data/${city}_mayor_tracker.json`),'utf8'));
try {
 const {default:View}=await server.ssrLoadModule('/src/components/MayorTrackerView.jsx');
 const {default:Shared}=await server.ssrLoadModule('/src/components/SharedPolicyTracker.jsx');
 const {cityPresentation,officialCityUrl}=await server.ssrLoadModule('/src/components/cityPolicyPresentation.js');
 const render=(Component,props)=>renderToStaticMarkup(React.createElement(Component,props));
 for(const city of ['kyoto','osaka','nagoya','yokohama','kobe']) {
  const data=load(city),before=JSON.stringify(data),adapter=cityPresentation(city);
  for(const value of [`http://www.city.${city}.lg.jp/x`,`https://www.city.${city}.lg.jp:443/x`,`https://user@www.city.${city}.lg.jp/x`,`https://www.city.${city}.lg.jp.evil.example/x`,'javascript:alert(1)']) assert.equal(officialCityUrl(city,value),null);
  assert.equal(officialCityUrl(city,`https://www.city.${city}.lg.jp/x`),`https://www.city.${city}.lg.jp/x`);
  if(city!=='kyoto') {
   const foreign={id:'P-03',headline:'foreign policy',stage_level:4,latest_update:{kind:'construction_paused',source_url:'https://www.city.kyoto.lg.jp/x'}};
   assert.ok(adapter.progress({...foreign,latest_update:undefined}).steps.every(s=>s.state!=='confirmed'&&s.state!=='paused'));
   assert.equal(adapter.officialUrl('https://www.city.kyoto.lg.jp/x'),null);
  }
  if(city==='kyoto'||city==='kobe') {
   assert.equal((render(View,{data,cityCode:city}).match(/data-policy-card=/g)||[]).length,data.pledges.length);
   for(const p of data.pledges) {
    const html=render(View,{data,cityCode:city,initialSearch:`?view=mayor&policy=${p.id}`});
    assert.ok(html.includes(p.headline));
    assert.ok(html.includes('出典・確認履歴'));
    assert.equal((html.match(/data-budget-relation=/g)||[]).length,p.budget_records?.length || 0);
    if(city==='kobe')assert.ok(!html.includes('準備予算案を見る'));
    if(city==='kobe')for(const statement of p.debate_statements || []) {
      const url=statement.official_url || statement.url;
      if(url)assert.ok(html.includes(url.replaceAll('&','&amp;')),'suppressed debate URL retained as text');
      if(url && !adapter.officialUrl(url))assert.ok(!html.includes(`href="${url}"`));
    }
   }
  }
  assert.equal(JSON.stringify(data),before);
 }
 // Same component can render another configured city without enabling its route.
 const osaka=load('osaka');assert.equal((render(Shared,{data:osaka,cityCode:'osaka'}).match(/data-policy-card=/g)||[]).length,4);
 const missing={mayor_info:{},pledges:[{id:'P-03',headline:'missing evidence',stage_level:5}]};
 const html=render(Shared,{data:missing,cityCode:'kobe',initialSearch:'?policy=P-03'});
 assert.ok(html.includes('予算資料未確認'));assert.ok(!html.includes('data-budget-relation='));assert.ok(!html.includes('data-stage-state="confirmed"'));
 const broken=load('kobe');broken.pledges[0].election_promise.bulletin_url='https://evil.example/x';
 broken.pledges[0].budget_records[0].doc_url='javascript:alert(1)';
 const bad=render(Shared,{data:broken,cityCode:'kobe',initialSearch:'?policy=KOBE-M01'});
 assert.ok(!bad.includes('href="javascript:'));assert.ok(!bad.includes('href="https://evil.example'));
 const inventory=JSON.parse(fs.readFileSync(path.join(root,'../docs/mayor-evidence-inventory.json'),'utf8'));
 assert.equal(inventory.total,40);assert.equal(inventory.policies.length,40);
 assert.equal(new Set(inventory.policies.map(p=>`${p.city}:${p.policy_id}`)).size,40);
 console.log('PASS: shared display, 40-policy inventory, city isolation, no inferred completion, safe links, missing budgets and unchanged input data.');
} finally {await server.close();}
