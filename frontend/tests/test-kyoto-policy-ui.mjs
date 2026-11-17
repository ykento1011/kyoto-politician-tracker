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
 const {policyPresentation,policyDocumentNote,policyProgress,officialKyotoUrl,readPolicyRoute,policyRouteHref}=await server.ssrLoadModule('/src/components/kyotoPolicyPresentation.js');
 const render=(Component,props)=>renderToStaticMarkup(React.createElement(Component,props));
 const list=render(View,{data,cityCode:'kyoto'});
 assert.equal((list.match(/data-policy-card=/g)||[]).length,14);
 assert.equal((list.match(/data-important-uncertainty/g)||[]).length,14);
 assert.ok(list.includes('src="/councilors/kyoto/matsui_koji.jpg"'));
 for(const value of [data.mayor_info.name,data.mayor_info.title,data.mayor_info.term]) assert.ok(list.includes(value));
 assert.equal((list.match(/data-policy-progress=/g)||[]).length,14);
 assert.equal((list.match(/data-stage=/g)||[]).length,70);
 const progress=data.pledges.map(policyProgress);
 assert.deepEqual(progress[0].steps.map(s=>s.state),['legacy','legacy','confirmed','hold','unverified']);
 assert.equal(progress[0].steps[2].short,'予算案のみ');
 assert.ok(progress[0].steps[2].note.includes('予算議決'));
 assert.equal(progress[1].steps[3].state,'hold');
 assert.equal(progress[2].steps[3].state,'legacy');
 assert.equal(progress[2].steps[4].state,'paused');
 for(let i=3;i<14;i++) assert.ok(progress[i].steps.every(s=>['legacy','unverified'].includes(s.state)));
 // A registration, even stage 5, cannot promote evidence into verified success.
 for(const stage_level of [1,2,3,4,5,0,6,null,'4']) {
   const state=policyProgress({id:'P-99',headline:'Unreviewed',stage_level});
   assert.ok(state.steps.every(s=>['legacy','unverified'].includes(s.state)));
   assert.equal(state.reference,Number.isInteger(stage_level)&&stage_level>=1&&stage_level<=5?stage_level:null);
 }
 for(const id of ['P-01','P-02','P-03']) {
   const badSource=structuredClone(data.pledges.find(p=>p.id===id));
   if(id==='P-01') badSource.budget_records.forEach(r=>r.is_broken=true);
   if(id==='P-02') badSource.election_promise.is_broken=true;
   if(id==='P-03') badSource.latest_update.source_url='https://example.com/changed';
   assert.ok(policyProgress(badSource).steps.every(s=>s.state!=='confirmed'&&s.state!=='paused'));
 }
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
   assert.ok(html.includes('5段階の意味と確認状況'));
   if(p.election_promise?.quote) assert.ok(html.includes(p.election_promise.quote));
   if(p.milestone) assert.ok(html.includes(p.milestone.title));
   if(p.legislative_bill) assert.ok(html.includes(p.legislative_bill.bill_number));
   for(const record of p.budget_records) {assert.ok(html.includes(record.amount_display));assert.ok(html.includes(record.doc_url));}
 }
 assert.equal(records,27);
 const p4=data.pledges.find(p=>p.id==='P-04');
 const note=policyDocumentNote(p4);
 assert.equal(note.fact_type,'budget_proposal');
 assert.equal(note.sha256,'4c3d5f1210dd2928c180d7e4237b50c80cd6467675e6b0ee2ca97c4395c373cb');
 assert.equal(officialKyotoUrl(note.url),note.url);
 const proposal=render(Detail,{pledge:p4,mayorInfo:data.mayor_info});
 for(const text of ['4億1,880万円（418,800千円）','認可保育施設','収入減約9.3億円','追加経費約4.2億円','約13.5億円','予算案作成時点の予定','予算成立・実際の施行・利用実績はこの資料だけでは確認できません','印刷p.103／PDF物理1','集計に加算せず']) assert.ok(proposal.includes(text),text);
 assert.ok(proposal.includes(`href="${note.url}"`));
 assert.ok(policyProgress(p4).steps.every(s=>s.state!=='confirmed'));
 for(const p of data.pledges.filter(p=>p.id!=='P-04')) {
   assert.equal(policyDocumentNote(p),null);
   assert.ok(!render(Detail,{pledge:p,mayorInfo:data.mayor_info}).includes('data-source-fact='));
 }
 const totals=render(Totals,{data});
 for(const value of ['85.7%','12/14','91億1,549万円','9,115,487,000']) assert.ok(!totals.includes(value),value);
 for(const value of ['このトラッカーの見方・作り方','公約達成率でも市長への評価でもなく','6. 更新・原典確認・訂正の方法','全件の照合が完了しているわけではありません']) assert.ok(totals.includes(value));
 assert.ok(render(View,{data,cityCode:'kyoto',initialSearch:'?view=mayor&mayorSection=summary'}).includes('このトラッカーの見方・作り方'));
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
