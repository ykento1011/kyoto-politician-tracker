import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
process.chdir(root);
const req=createRequire(path.join(root,'package.json'));
const React=req('react'),{renderToStaticMarkup}=req('react-dom/server');
const {createServer}=await import(pathToFileURL(req.resolve('vite')).href);
const {default:react}=await import(pathToFileURL(req.resolve('@vitejs/plugin-react')).href);
const data=JSON.parse(fs.readFileSync(path.join(root,'public/data/kyoto_mayor_tracker.json'),'utf8'));
const server=await createServer({root,configFile:false,envDir:false,publicDir:false,
 cacheDir:path.join(root,'.qa_cache'),plugins:[react()],server:{middlewareMode:true,watch:null},appType:'custom'});
try {
 const {KyotoPolicyDetail:Detail,KyotoPolicyTotals:Totals}=await server.ssrLoadModule('/src/components/KyotoPolicyTracker.jsx');
 const render=p=>renderToStaticMarkup(React.createElement(React.Fragment,null,React.createElement(Detail,{pledge:p,mayorInfo:data.mayor_info}),React.createElement(Totals,{data})));
 const a=render(data.pledges[0]),b=render(data.pledges[1]);
 assert.ok(a.includes('公約達成率でも市長への評価でもなく'));
 assert.ok(JSON.stringify(data.kpis).includes('85.7%'));
 assert.ok(JSON.stringify(data).includes('91億1,549万円'));
 for(const markup of [a,b]) {
   assert.ok(markup.includes('data-legislative-status="hold"'));
   assert.ok(markup.includes('未確認の登録議案'));
   assert.ok(!markup.includes('確定エビデンス'));
   assert.ok(!markup.includes('bg-emerald-100 text-emerald-800'));
 }
 assert.ok(a.includes('導入準備（予算案確認）'));
 assert.ok(!a.includes('予算化・実証中'));
 assert.ok(a.includes('関連する別施策（制度実施の根拠ではありません）'));
 assert.ok(a.includes('EX100'));
 assert.ok(a.includes('2億7,100万円') && a.includes('2億6,900万円'));
 assert.ok(a.includes('data-budget-relation="direct"') && a.includes('data-budget-relation="contextual"'));
 assert.ok(b.includes('data-progress-held'));
 assert.ok(!b.includes('政策ライフサイクル進捗'));
 assert.ok(!b.includes('条例改正案可決・国協議中'));
 assert.ok(!b.includes('85.7%') && !b.includes('91億1,549万円'));
 const p3=render(data.pledges[2]);
 assert.ok(p3.includes('整備工事が一時停止') && p3.includes('過去の契約・実施記録'));
 assert.ok(!p3.includes('data-policy-evidence="review"'));
 // Unannotated policies continue down the existing UI path.
 for(const p of data.pledges.slice(2)) assert.ok(!render(p).includes('data-policy-evidence="review"'));
 // Missing result must not reintroduce a default "passed" badge in reviewed records.
 const missing=structuredClone(data.pledges[0]); delete missing.legislative_bill.result;
 assert.ok(!render(missing).includes('bg-emerald-100 text-emerald-800'));
 console.log('PASS: P-01/P-02 held evidence, contextual milestone, budgets, KPI and legacy paths (offline SSR)');
} finally {await server.close();}
