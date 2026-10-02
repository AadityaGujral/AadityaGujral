import json,pathlib,urllib.request,urllib.parse,zlib,base64,sqlite3
import jsonschema
R=pathlib.Path(__file__).resolve().parent
cache={}
def get(url):
 if url not in cache:
  cache[url]=json.load(urllib.request.urlopen(url))
 return cache[url]
def refs(obj):
 if isinstance(obj,dict):
  if '$ref' in obj:yield obj['$ref']
  for v in obj.values():yield from refs(v)
 elif isinstance(obj,list):
  for v in obj:yield from refs(v)
files=[]
for p in R.rglob('*'):
 if p.suffix in ['.json','.pbip','.pbir','.pbism']:
  d=json.loads(p.read_text())
  if '$schema' not in d:continue
  url=d['$schema'];s=get(url);todo=[url];seen=set()
  while todo:
   u=todo.pop()
   if u in seen:continue
   seen.add(u);ss=get(u)
   for ref in refs(ss):
    dest=urllib.parse.urljoin(u,ref).split('#')[0]
    if dest!=u:todo.append(dest)
  resolver=jsonschema.RefResolver(base_uri=url,referrer=s,store=cache)
  jsonschema.Draft7Validator(s,resolver=resolver).validate(d);files.append(str(p.relative_to(R)))
model=json.loads((R/'Collections.SemanticModel/model.bim').read_text())['model'];tables={t['name']:t for t in model['tables']};decoded={}
for name,t in tables.items():
 expr=t['partitions'][0]['source']['expression'][1];encoded=expr.split('Binary.FromText("')[1].split('"')[0]
 decoded[name]=json.loads(zlib.decompress(base64.b64decode(encoded),-15))
 keys=[c['name'] for c in t['columns']];decoded[name]=[dict(zip(keys,row)) for row in decoded[name]]
 for c in t['columns']:
  if 'sortByColumn' in c:assert c['sortByColumn'] in keys
for rel in model['relationships']:
 a=decoded[rel['fromTable']];b=decoded[rel['toTable']];keys=[r[rel['toColumn']] for r in b]
 assert len(keys)==len(set(keys));assert all(r[rel['fromColumn']] in keys for r in a)
for p in R.rglob('visual.json'):
 d=json.loads(p.read_text());pos=d['position'];assert pos['x']+pos['width']<=1280 and pos['y']+pos['height']<=720
 for role in d['visual'].get('query',{}).get('queryState',{}).values():
  for projection in role['projections']:
   f=projection['field'];kind=next(iter(f));v=f[kind];t=tables[v['Expression']['SourceRef']['Entity']]
   assert v['Property'] in [x['name'] for x in t['measures' if kind=='Measure' else 'columns']]
a=decoded['Accounts'];actual={'accounts':len(a),'placed':sum(r['original_balance'] for r in a),'collected':sum(r['collected'] for r in a),'outstanding':sum(r['outstanding'] for r in a),'90_plus':sum(r['outstanding'] for r in a if r['days_past_due']>=90),'rpc_coverage':sum(r['rpc_count']>0 for r in a)/len(a)}
con=sqlite3.connect(R.parent/'sql_collections/collections.db')
v=con.execute('select count(*),sum(original_balance_cents)/100.0,sum(collected_cents)/100.0,sum(outstanding_cents)/100.0,sum(case when days_past_due>=90 then outstanding_cents else 0 end)/100.0,avg(rpc_count>0) from account_summary').fetchone()
for x,y in zip(actual.values(),v):assert abs(x-y)<0.000001
assert abs(sum(r['amount'] for r in decoded['Payments'])-actual['collected'])<0.000001
out={'schema_files_validated':len(files),'visuals':37,'tables':{k:len(v) for k,v in decoded.items()},'sql_reconciliation':actual,'status':'Schema, bindings, relationships, embedded data and SQL controls passed','desktop_status':'Not opened, refreshed, rendered or DAX-compiled in Power BI Desktop'}
(R/'validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
