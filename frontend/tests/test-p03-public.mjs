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
const policy=data.pledges.find(p=>p.id==='P-03');
const server=await createServer({root,configFile:false,envDir:false,publicDir:false,
  cacheDir:path.join(root,'.qa_cache'),plugins:[react()],server:{middlewareMode:true,watch:null},appType:'custom'});
try {
  const {default:MayorTrackerView}=await server.ssrLoadModule('/src/components/MayorTrackerView.jsx');
  const markup=renderToStaticMarkup(React.createElement(MayorTrackerView,{data:{...data,pledges:[policy]},cityCode:'kyoto'}));
  assert.equal((markup.match(/data-budget-relation="unconfirmed"/g)||[]).length,1);
  assert.equal((markup.match(/data-budget-relation="contextual"/g)||[]).length,1);
  assert.equal((markup.match(/公式資料（PDF）を確認/g)||[]).length,2);
  assert.equal((markup.match(/公式資料（HTML）を確認/g)||[]).length,1);
  for(const text of ['約1億9,000万円','1億2,400万円','印刷p.188','物理16','2026-11-05',
    '令和10年度中','新たな開始時期は未定','整備工事が一時停止','過去の契約・実施記録',
    'これまでの到達段階','98億3,016万円','全額の原典確認を済ませた総額ではありません']) assert.ok(markup.includes(text),text);
  for(const text of ['財源内訳：','4,000万円','7,000万円','1,400万円','data-budget-relation="direct"']) assert.ok(!markup.includes(text),text);
  assert.ok(markup.includes(policy.milestone.title));
  assert.ok(markup.includes(policy.latest_update.source_url));
  for(const record of policy.budget_records) assert.ok(markup.includes(record.doc_url));
  console.log('PASS: public P-03 evidence, aggregate definition, history and latest progress; offline SSR.');
} finally {await server.close();}
