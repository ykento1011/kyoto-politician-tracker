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
const data=JSON.parse(fs.readFileSync(path.join(root,'public/data/kobe_mayor_tracker.json'),'utf8'));
const policy=data.pledges.find(p=>p.id==='KOBE-M01');
const server=await createServer({root,configFile:false,envDir:false,publicDir:false,
  cacheDir:path.join(root,'.qa_cache'),plugins:[react()],server:{middlewareMode:true,watch:null},appType:'custom'});
try {
  const {default:MayorTrackerView}=await server.ssrLoadModule('/src/components/MayorTrackerView.jsx');
  const markup=renderToStaticMarkup(React.createElement(MayorTrackerView,{data:{...data,pledges:[policy]},cityCode:'kobe'}));
  assert.equal((markup.match(/data-budget-relation="unconfirmed"/g)||[]).length,1);
  assert.equal((markup.match(/data-budget-aggregation="excluded"/g)||[]).length,1);
  for(const text of ['14億2,000万円','原典未確認','集計対象外','未照合','掲載答弁記録','10件']) assert.ok(markup.includes(text),text);
  for(const text of ['財源内訳：','8億5,000万円','5億7,000万円','関連予算総額']) assert.ok(!markup.includes(text),text);
  assert.ok(markup.includes(policy.budget_records[0].doc_url));
  const full=renderToStaticMarkup(React.createElement(MayorTrackerView,{data,cityCode:'kobe'}));
  assert.equal((full.match(/data-budget-relation=/g)||[]).length,1);
  for(const other of data.pledges.filter(p=>p.id!=='KOBE-M01')) assert.ok(full.includes(other.budget_records[0].amount_display));
  console.log('PASS: Kobe M01 retained/excluded; unverified funding hidden; other four legacy budget cards retained.');
} finally {await server.close();}
