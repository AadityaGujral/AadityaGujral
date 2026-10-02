import json,sqlite3,zlib,base64,csv,uuid,pathlib
ROOT=pathlib.Path(__file__).resolve().parent
SCHEMA='https://developer.microsoft.com/json-schemas/fabric/'
def write(path,obj):
 p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,indent=2)+'\n')
def schema(path):return SCHEMA+path+'/schema.json'
con=sqlite3.connect(ROOT.parent/'sql_collections/collections.db');con.row_factory=sqlite3.Row
rows=[dict(r) for r in con.execute('select * from account_summary')]
for r in rows:
 for k in ['original_balance_cents','collected_cents','outstanding_cents']:r[k.replace('_cents','')]=r.pop(k)/100
 r['score_band']='Below 580' if r['credit_score']<580 else '580-669' if r['credit_score']<670 else '670+'
data={'Accounts':rows}
for table,file in [('Payments','payments'),('Contacts','contact_attempts'),('Collectors','collectors')]:
 with open(ROOT.parent/f'sql_collections/data/{file}.csv') as f: rr=list(csv.DictReader(f))
 for r in rr:
  for k,v in list(r.items()):
   if k.endswith('_cents'):r[k[:-6]]=int(v)/100 if v else None;del r[k]
   elif k.endswith('_id'):r[k]=int(v)
   elif not v:r[k]=None
 data[table]=rr
import datetime
data['Dates']=[{'Date':str(datetime.date(2026,1,1)+datetime.timedelta(days=i)),'month_label':(datetime.date(2026,1,1)+datetime.timedelta(days=i)).strftime('%b'),'month_number':(datetime.date(2026,1,1)+datetime.timedelta(days=i)).month} for i in range(181)]
measures={
'Account Count':('COUNTROWS(Accounts)','#,0'),
'Total Placed':('SUM(Accounts[original_balance])','$#,0'),
'Total Collected':('SUM(Accounts[collected])','$#,0'),
'Outstanding Balance':('SUM(Accounts[outstanding])','$#,0'),
'Recovery Rate':('DIVIDE([Total Collected], [Total Placed])','0.0%'),
'90+ DPD Exposure':('CALCULATE([Outstanding Balance], KEEPFILTERS(Accounts[days_past_due] >= 90))','$#,0'),
'90+ Exposure Share':('DIVIDE([90+ DPD Exposure], [Outstanding Balance])','0.0%'),
'RPC Accounts':('CALCULATE([Account Count], KEEPFILTERS(Accounts[rpc_count] > 0))','#,0'),
'RPC Coverage':('DIVIDE([RPC Accounts], [Account Count])','0.0%'),
'RPC Contacts':('SUM(Accounts[rpc_count])','#,0'),
'Dollars per RPC':('DIVIDE([Total Collected], [RPC Contacts])','$#,0.00'),
'Contact Attempts':('SUM(Accounts[attempts])','#,0'),
'PTP Accounts':('CALCULATE([Account Count], KEEPFILTERS(Accounts[ptp_count] > 0))','#,0'),
'PTP Coverage':('DIVIDE([PTP Accounts], [Account Count])','0.0%'),
'Unpaid Accounts':('CALCULATE([Account Count], KEEPFILTERS(Accounts[payment_count] = 0))','#,0'),
'Period Collections':('SUM(Payments[amount])','$#,0'),
'Period Contacts':('COUNTROWS(Contacts)','#,0'),
'Period RPC Contacts':('CALCULATE([Period Contacts], KEEPFILTERS(Contacts[outcome] IN {"RPC", "PTP"}))','#,0'),
'Period RPC Conversion':('DIVIDE([Period RPC Contacts], [Period Contacts])','0.0%')}
tables=[]
for name,rr in data.items():
 keys=list(rr[0]);cols=[];types=[]
 for k in keys:
  vals=[r[k] for r in rr if r[k] is not None];v=vals[0]
  dtype='int64' if isinstance(v,int) else 'double' if isinstance(v,float) else 'dateTime' if k.endswith('_date') or k=='Date' else 'string'
  col={'name':k,'dataType':dtype,'sourceColumn':k,'summarizeBy':'none'}
  if dtype=='dateTime':col['formatString']='yyyy-MM-dd'
  if name=='Dates' and k=='Date':col['isKey']=True
  if name=='Dates' and k=='month_label':col['sortByColumn']='month_number'
  cols.append(col);types.append('{"'+k+'", '+{'int64':'Int64.Type','double':'type number','dateTime':'type date','string':'type text'}[dtype]+'}')
 raw=json.dumps([[r[k] for k in keys] for r in rr],separators=(',',':')).encode();c=zlib.compressobj(wbits=-15);enc=base64.b64encode(c.compress(raw)+c.flush()).decode()
 expression=['let',f' Source = Json.Document(Binary.Decompress(Binary.FromText("{enc}", BinaryEncoding.Base64), Compression.Deflate)),',f' Rows = Table.FromRows(Source, {json.dumps(keys)}),',' Typed = Table.TransformColumnTypes(Rows, {'+', '.join(types)+'}, "en-US")','in Typed']
 t={'name':name,'columns':cols,'partitions':[{'name':name,'mode':'import','source':{'type':'m','expression':expression}}]}
 if name=='Accounts':t['measures']=[{'name':k,'expression':e,'formatString':fmt} for k,(e,fmt) in measures.items()]
 tables.append(t)
 with open(ROOT/f'{name}.csv','w') as f:w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rr)
rels=[]
for fr,fc,to,tc in [('Accounts','collector_id','Collectors','collector_id'),('Payments','account_id','Accounts','account_id'),('Contacts','account_id','Accounts','account_id'),('Payments','payment_date','Dates','Date'),('Contacts','contact_date','Dates','Date')]:
 rels.append({'name':str(uuid.uuid5(uuid.NAMESPACE_URL,fr+fc)),'fromTable':fr,'fromColumn':fc,'toTable':to,'toColumn':tc,'fromCardinality':'many','toCardinality':'one','crossFilteringBehavior':'oneDirection'})
write('Collections.SemanticModel/model.bim',{'name':'Collections','compatibilityLevel':1567,'model':{'culture':'en-US','defaultPowerBIDataSourceVersion':'powerBI_V3','sourceQueryCulture':'en-US','tables':tables,'relationships':rels}})
write('Collections.SemanticModel/definition.pbism',{'$schema':schema('item/semanticModel/definitionProperties/1.0.0'),'version':'1.0'})
write('Collections.pbip',{'$schema':schema('pbip/pbipProperties/1.0.0'),'version':'1.0','artifacts':[{'report':{'path':'Collections.Report'}}]})
write('Collections.Report/definition.pbir',{'$schema':schema('item/report/definitionProperties/2.0.0'),'version':'4.0','datasetReference':{'byPath':{'path':'../Collections.SemanticModel'}}})
write('Collections.Report/definition/version.json',{'$schema':schema('item/report/definition/versionMetadata/1.0.0'),'version':'2.0.0'})
write('Collections.Report/definition/report.json',{'$schema':schema('item/report/definition/report/3.1.0'),'themeCollection':{'customTheme':{'name':'CollectionsTheme','type':'RegisteredResources','reportVersionAtImport':{'visual':'2.1.0','page':'2.0.0','report':'3.1.0'}}},'resourcePackages':[{'name':'RegisteredResources','type':'RegisteredResources','items':[{'name':'CollectionsTheme','path':'CollectionsTheme.json','type':'CustomTheme'}]}]})
pages=['Executive','Collectors','Risk','AccountDetail']
write('Collections.Report/definition/pages/pages.json',{'$schema':schema('item/report/definition/pagesMetadata/1.0.0'),'pageOrder':pages,'activePageName':'Executive'})
def field(t,k,measure=False):return {('Measure' if measure else 'Column'):{'Expression':{'SourceRef':{'Entity':t}},'Property':k}}
def proj(t,k,m=False):return {'field':field(t,k,m),'queryRef':t+'.'+k,'nativeQueryRef':k}
def lit(v):return {'expr':{'Literal':{'Value':v}}}
counters={}
def visual(page,typ,x,y,w,h,roles=None,title=None,objects=None):
 n=counters.get(page,0)+1;counters[page]=n;name=f'{page}{n:02}'
 v={'visualType':typ}
 if roles:v['query']={'queryState':{role:{'projections':[proj(*p) for p in ps]} for role,ps in roles.items()}}
 if title:v['visualContainerObjects']={'title':[{'properties':{'show':lit('true'),'text':lit("'"+title+"'"),'fontSize':lit('12D')}}]}
 if objects:v['objects']=objects
 write(f'Collections.Report/definition/pages/{page}/visuals/{name}/visual.json',{'$schema':schema('item/report/definition/visualContainer/2.1.0'),'name':name,'position':{'x':x,'y':y,'width':w,'height':h,'z':n,'tabOrder':n},'visual':v})
def text(page,value,y=16,size='22px'):
 visual(page,'textbox',24,y,1232,54,objects={'general':[{'properties':{'paragraphs':[{'textRuns':[{'value':value,'textStyle':{'fontFamily':'Segoe UI','fontSize':size,'color':'#18344C'}}]}]}}]})
def cards(page,names):visual(page,'cardVisual',24,170,1232,110,{'Data':[('Accounts',n,True) for n in names]})
def chart(page,typ,t,c,m,x,y,w=598,h=320):visual(page,typ,x,y,w,h,{'Category':[(t,c,False)],'Y':[('Accounts',m,True)]},m+' by '+c.replace('_',' '))
for page in pages:
 write(f'Collections.Report/definition/pages/{page}/page.json',{'$schema':schema('item/report/definition/page/2.0.0'),'name':page,'displayName':{'AccountDetail':'Account detail'}.get(page,page),'displayOption':'FitToPage','width':1280,'height':720})
 text(page,'COLLECTIONS / '+page.upper())
 text(page,'Synthetic data | Snapshot: June 30, 2026 | Balances fixed at snapshot; trends reflect dated activity.',72,'13px')
 for i,(t,k) in enumerate([('Accounts','portfolio'),('Accounts','region'),('Collectors','collector_name')]):
  visual(page,'slicer',24+i*410,108,392,62,{'Values':[(t,k,False)]},objects={'data':[{'properties':{'mode':lit("'Dropdown'")}}]})
cards('Executive',['Total Placed','Total Collected','Outstanding Balance','Recovery Rate'])
chart('Executive','lineChart','Dates','month_label','Period Collections',24,300)
chart('Executive','clusteredBarChart','Accounts','portfolio','Recovery Rate',658,300)
text('Executive','Use page tabs to explore collectors, aging, and individual accounts. All dollar amounts are USD.',648,'13px')
cards('Collectors',['Account Count','Recovery Rate','RPC Coverage','Dollars per RPC'])
chart('Collectors','clusteredBarChart','Collectors','collector_name','Recovery Rate',24,300,598,260)
visual('Collectors','tableEx',658,300,598,350,{'Values':[('Collectors','collector_name',False)]+[('Accounts',x,True) for x in ['Account Count','Total Collected','Recovery Rate','RPC Coverage','PTP Coverage']]},'Collector comparison')
text('Collectors','RPC coverage = accounts reached / assigned accounts. Dollars per RPC uses all RPC and PTP contacts.',648,'13px')
cards('Risk',['90+ DPD Exposure','90+ Exposure Share','Unpaid Accounts','PTP Coverage'])
chart('Risk','clusteredColumnChart','Accounts','aging_bucket','Outstanding Balance',24,300)
chart('Risk','clusteredBarChart','Accounts','score_band','Outstanding Balance',658,300)
text('Risk','90+ includes day 90; aging bucket 61–90 also includes day 90. Score bands describe credit scores, not model predictions.',648,'13px')
# Account selector makes the detail page usable without reliance on untested drillthrough actions.
visual('AccountDetail','slicer',24,170,300,82,{'Values':[('Accounts','account_id',False)]},'Select account')
visual('AccountDetail','cardVisual',350,170,906,110,{'Data':[('Accounts',m,True) for m in ['Total Placed','Total Collected','Outstanding Balance']]})
visual('AccountDetail','tableEx',24,300,1232,150,{'Values':[('Accounts',c,False) for c in ['account_id','portfolio','region','collector_name','credit_score','days_past_due','aging_bucket','attempts','rpc_count','ptp_count']]},'Account attributes')
visual('AccountDetail','tableEx',24,470,598,220,{'Values':[('Payments',c,False) for c in ['payment_id','payment_date','amount']]},'Payment history')
visual('AccountDetail','tableEx',658,470,598,220,{'Values':[('Contacts',c,False) for c in ['contact_id','contact_date','outcome','promise_due_date','promise_amount']]},'Contact history')
print('Built',len(tables),'tables,',len(measures),'measures,',sum(counters.values()),'visuals')

write("Collections.Report/StaticResources/RegisteredResources/CollectionsTheme.json", {"name":"CollectionsTheme","dataColors":["#137C80","#365B9A","#E9A23B","#7355A5","#26B49A","#B85A67"],"background":"#F3F6FA","foreground":"#18344C","tableAccent":"#137C80","textClasses":{"title":{"fontFace":"Segoe UI","fontSize":12,"color":"#18344C"},"label":{"fontFace":"Segoe UI","fontSize":11,"color":"#426174"},"callout":{"fontFace":"Segoe UI","fontSize":28,"color":"#18344C"}}})
