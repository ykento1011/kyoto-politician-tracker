import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const req=createRequire(path.join(root,'package.json'));
const React=req('react'),{renderToStaticMarkup}=req('react-dom/server');
const {createServer}=await import(pathToFileURL(req.resolve('vite')).href);
const {default:react}=await import(pathToFileURL(req.resolve('@vitejs/plugin-react')).href);
const data=JSON.parse(fs.readFileSync(path.join(root,'public/data/kyoto_mayor_tracker.json'),'utf8'));
const before=JSON.stringify(data);
const server=await createServer({root,configFile:false,envDir:false,publicDir:false,cacheDir:path.join(root,'.qa_cache'),plugins:[react()],server:{middlewareMode:true,watch:null},appType:'custom'});
try {
 const {default:View,LegacyMayorTrackerView:Legacy}=await server.ssrLoadModule('/src/components/MayorTrackerView.jsx');
 const {KyotoPolicyDetail:Detail,KyotoPolicyTotals:Totals}=await server.ssrLoadModule('/src/components/KyotoPolicyTracker.jsx');
 const {policyPresentation,officialKyotoUrl,readPolicyRoute,policyRouteHref}=await server.ssrLoadModule('/src/components/kyotoPolicyPresentation.js');
 const render=(Component,props)=>renderToStaticMarkup(React.createElement(Component,props));
 const list=render(View,{data,cityCode:'kyoto'});
 assert.equal((list.match(/data-policy-card=/g)||[]).length,14);
 assert.equal((list.match(/data-important-uncertainty/g)||[]).length,14);
 for(const hidden of ['85.7%','91億1,549万円','2億7,100万円','2億6,900万円','議88','議145','契約可決・着工']) assert.ok(!list.includes(hidden),hidden);
 for(const visible of ['準備予算案を見る','議決根拠を確認中','令和10年度中の開始は不可','2026-11-05','新たな開始時期は未定']) assert.ok(list.includes(visible),visible);
 assert.equal((list.match(/target="_blank"/g)||[]).length,3);
 for(const p of data.pledges.slice(3)) {
   const result=policyPresentation(p); assert.equal(result.status,'根拠を確認中');assert.equal(result.source,null);
 }
 let records=0;
 for(const p of data.pledges) {
   const html=render(Detail,{pledge:p,mayorInfo:data.mayor_info});
   records+=(html.match(/data-budget-relation=/g)||[]).length;
   assert.ok(html.includes(p.headline));
   if(p.election_promise?.quote) assert.ok(html.includes(p.election_promise.quote));
   if(p.milestone) assert.ok(html.includes(p.milestone.title));
   if(p.legislative_bill) assert.ok(html.includes(p.legislative_bill.bill_number));
   for(const record of p.budget_records) {assert.ok(html.includes(record.amount_display));assert.ok(html.includes(record.doc_url));}
 }
 assert.equal(records,27);
 const totals=render(Totals,{data});
 for(const value of ['85.7%','12/14','91億1,549万円','9,115,487,000','48億8,215万8,000円','確定済み件数・公約達成率ではありません']) assert.ok(totals.includes(value),value);
 // Failed presentation guards never promote a replacement source.
 const bad=structuredClone(data.pledges[0]); bad.budget_records[0].doc_url='https://example.com/other.pdf';
 assert.equal(policyPresentation(bad).source,null);
 bad.budget_records.reverse(); assert.equal(policyPresentation(bad).source,null);
 assert.equal(policyPresentation({id:'P-99',headline:'Missing'}).source,null);
 for(const host of ['www.city.kyoto.lg.jp','www2.city.kyoto.lg.jp']) {
   assert.equal(officialKyotoUrl(`https://${host}/x.pdf#page=2`),`https://${host}/x.pdf#page=2`);
   for(const url of [`http://${host}/x`,`https://user@${host}/x`,`https://user:password@${host}/x`,`https://${host}:443/x`,`https://${host}:8443/x`,`https://${host}:/x`,`https://${host}.example.com/x`,`https://sub.${host}/x`]) assert.equal(officialKyotoUrl(url),null,url);
 }
 for(const url of ['javascript:alert(1)','https://example.com/x','https://www3.city.kyoto.lg.jp/x','https://www2-city.kyoto.lg.jp/x',null]) assert.equal(officialKyotoUrl(url),null);
 // A retained historic contract link is neither a current source nor new verification.
 const p3=structuredClone(data.pledges.find(p=>p.id==='P-03'));
 const contract='https://www2.city.kyoto.lg.jp/shikai/img/honkaigi/gian/R7-9/G07-104.pdf';
 assert.equal(p3.milestone.evidence_url,contract);
 assert.ok(render(Detail,{pledge:p3,mayorInfo:data.mayor_info}).includes(`href="${contract}"`));
 assert.equal(policyPresentation(p3).source.url,'https://www.city.kyoto.lg.jp/kyoiku/page/0000347372.html');
 p3.milestone.is_broken=true;
 assert.ok(!render(Detail,{pledge:p3,mayorInfo:data.mayor_info}).includes(`href="${contract}"`));
 // Existing non-Kyoto render path is identical, including its evidence UI.
 for(const city of ['kobe','osaka','nagoya','yokohama']) {
   const cityData=JSON.parse(fs.readFileSync(path.join(root,`public/data/${city}_mayor_tracker.json`),'utf8'));
   assert.equal(render(View,{data:cityData,cityCode:city}),render(Legacy,{data:cityData,cityCode:city}));
 }
 const route={policy:'P-03',section:'',query:'給食',category:'教育'};
 assert.deepEqual(readPolicyRoute(policyRouteHref(route,'?view=mayor&city=kyoto')),route);
 assert.ok(policyRouteHref(route,'?city=kyoto').includes('city=kyoto'));
 const deepLink=render(View,{data,cityCode:'kyoto',initialSearch:'?view=mayor&policy=P-03'});
 assert.ok(deepLink.includes('policy-budget'));assert.ok(!deepLink.includes('data-policy-list'));
 assert.ok(render(View,{data,cityCode:'kyoto',initialSearch:'?policy=unknown'}).includes('政策が見つかりません'));
 assert.equal(JSON.stringify(data),before);
 console.log('PASS: Kyoto four-field overview, all 14 details/27 budgets, holds, null-safe sources, unchanged totals/data and four-city legacy SSR.');
} finally {await server.close();}
