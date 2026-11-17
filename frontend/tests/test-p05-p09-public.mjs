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
const policies=data.pledges.filter(p=>['P-05','P-09'].includes(p.id));
const server=await createServer({root,configFile:false,envDir:false,publicDir:false,
  cacheDir:path.join(root,'.qa_cache'),plugins:[react()],server:{middlewareMode:true,watch:null},appType:'custom'});
try {
  const {KyotoPolicyDetail:Detail,KyotoPolicyTotals:Totals}=await server.ssrLoadModule('/src/components/KyotoPolicyTracker.jsx');
  const markup=renderToStaticMarkup(React.createElement(React.Fragment,null,...policies.map(p=>React.createElement(Detail,{key:p.id,pledge:p,mayorInfo:data.mayor_info})),React.createElement(Totals,{data})));
  assert.equal((markup.match(/data-budget-role="delta"/g)||[]).length,3);
  assert.equal((markup.match(/data-budget-role="after_change"/g)||[]).length,1);
  assert.equal((markup.match(/data-budget-aggregation="included"/g)||[]).length,2);
  for(const text of ['4億6,232万9,000円','＋2億5,800万円','令和7年度9月補正','令和8年度9月補正','＋25億円','10億円','35億円','補正後額','今回の照合対象外']) assert.ok(markup.includes(text),text);
  assert.ok(!markup.includes('財源内訳：'));
  for(const p of policies)for(const record of p.budget_records.filter(r=>r.amount_role)) assert.ok(markup.includes(record.doc_url));
  console.log('PASS: P-05/P-09 annual history, sources, selection and exact JPY display.');
} finally {await server.close();}
