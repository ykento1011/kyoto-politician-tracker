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
const policy=data.pledges.find(p=>p.id==='P-07');
const server=await createServer({root,configFile:false,envDir:false,publicDir:false,
  cacheDir:path.join(root,'.qa_cache'),plugins:[react()],server:{middlewareMode:true,watch:null},appType:'custom'});
try {
  const {default:MayorTrackerView}=await server.ssrLoadModule('/src/components/MayorTrackerView.jsx');
  const markup=renderToStaticMarkup(React.createElement(MayorTrackerView,{data:{...data,pledges:[policy]},cityCode:'kyoto'}));
  assert.equal((markup.match(/data-budget-aggregation="excluded"/g)||[]).length,5);
  for(const text of ['7億1,500万円','9,900万円','3,650万円','2,500万円','0円','債務負担行為','2億4,400万円','集計対象外','原典','91億1,516万円']) assert.ok(markup.includes(text),text);
  assert.ok(!markup.includes('財源内訳：'));
  for(const record of policy.budget_records) assert.ok(markup.includes(record.doc_url));
  console.log('PASS: P-07 evidence, aggregation exclusion and sources; offline SSR.');
} finally {await server.close();}
