import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const root=process.argv[2] || path.dirname(new URL(import.meta.url).pathname);
const output=path.join(root,'outputs/excel_dashboard');
await fs.mkdir(output,{recursive:true});
const input=JSON.parse(await fs.readFile(path.join(root,'inputs.json'),'utf8'));
const wb=Workbook.create();
const dash=wb.worksheets.add('Dashboard'),analysis=wb.worksheets.add('Analysis'),accounts=wb.worksheets.add('Accounts'),payments=wb.worksheets.add('Payments');
const navy='#203C59',blue='#235789',gold='#B87521',light='#EDF2F7';
const money='"$"#,##0;("$"#,##0);"$"0';
const serial=d=>(Date.parse(d)-Date.UTC(1899,11,30))/86400000;
const lastA=input.accounts.length+4,lastP=input.payments.length+4;
const ar=col=>`'Accounts'!$${col}$5:$${col}$${lastA}`;
const pr=col=>`'Payments'!$${col}$5:$${col}$${lastP}`;
function set(s,c,v){s.getRange(c).values=[[v]];}
function formula(s,c,v){s.getRange(c).formulas=[[v]];}
function section(s,range,title){s.getRange(range).format.fill=light;set(s,range.split(':')[0],title);s.getRange(range).format.font.bold=true;}
function headers(s,range,values){s.getRange(range).values=[values];s.getRange(range).format={fill:navy,font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,rowHeight:36,horizontalAlignment:'center',verticalAlignment:'center'};}
for(const s of [dash,analysis,accounts,payments]){s.showGridLines=false;s.getRange('A1:O60').format.font={name:'Arial',size:10,color:'#253343'};s.getRange('A1:O60').format.rowHeight=23;s.getRange('A1:O60').format.columnWidth=15;}
dash.tabColor=navy;analysis.tabColor=blue;
set(dash,'A2','Collections Performance Dashboard');dash.getRange('A2').format.font={size:16,bold:true,color:navy};
set(dash,'A3','Aditya Gujral');set(dash,'I3','Synthetic data as of Jun 30, 2026');
set(analysis,'A2','Collections analysis and forecast');analysis.getRange('A2').format.font={size:14,bold:true};
set(accounts,'A1','Synthetic account snapshots');set(accounts,'A2','Source: SQL collections project, seed 42, Jun 30, 2026. Dollar amounts in USD.');
set(accounts,'A3','Contact counts are staged from SQL; payment totals and balances calculate here.');
const accountRows=input.accounts.map(a=>[String(a.account_id),a.collector_name,a.portfolio,a.region,a.credit_score,serial(a.placed_date),a.original_balance_cents/100,a.days_past_due,a.attempts,a.rpc_count,a.ptp_count]);
headers(accounts,'A4:O4',['Account ID','Collector','Portfolio','Region','Credit score','Placed date','Placed balance','Days past due','Attempts','RPC contacts','PTP contacts','Collected','Outstanding','Aging bucket','RPC reached']);
accounts.getRange(`A5:K${lastA}`).values=accountRows;
accounts.getRange(`L5:O${lastA}`).formulas=input.accounts.map((a,i)=>{const r=i+5;return [`=SUMIFS(${pr('D')},${pr('B')},A${r})`,`=G${r}-L${r}`,`=IF(H${r}=0,"0 Current",IF(H${r}<=30,"1 1-30",IF(H${r}<=60,"2 31-60",IF(H${r}<=90,"3 61-90",IF(H${r}<=120,"4 91-120","5 121+")))))`,`=IF(J${r}>0,1,0)`];});
accounts.getRange(`A4:O${lastA}`).format.font={name:'Arial',size:10};accounts.getRange(`F5:F${lastA}`).setNumberFormat('mm/dd/yy');
for(const col of ['G','L','M'])accounts.getRange(`${col}5:${col}${lastA}`).setNumberFormat(money);
accounts.getRange(`A5:A${lastA}`).setNumberFormat('@');accounts.getRange('C1:C60').format.columnWidth=19;accounts.getRange('N1:N60').format.columnWidth=17;accounts.tables.add(`A4:O${lastA}`,true,'AccountsTable');accounts.freezePanes.freezeRows(4);accounts.freezePanes.freezeColumns(1);
set(payments,'A1','Synthetic posted payments');set(payments,'A2','Source: SQL payments.csv. All dates fall between placement and Jun 30, 2026.');
headers(payments,'A4:D4',['Payment ID','Account ID','Payment date','Amount (USD)']);payments.getRange(`A5:D${lastP}`).values=input.payments.map(p=>[String(p.payment_id),String(p.account_id),serial(p.payment_date),p.amount_cents/100]);
payments.getRange(`A4:D${lastP}`).format.font={name:'Arial',size:10};payments.getRange(`C5:C${lastP}`).setNumberFormat('mm/dd/yy');payments.getRange(`D5:D${lastP}`).setNumberFormat(money);payments.tables.add(`A4:D${lastP}`,true,'PaymentsTable');payments.freezePanes.freezeRows(4);
section(analysis,'A5:C5','Portfolio KPIs');
const kpis=[['Accounts',`=COUNTA(${ar('A')})`],['Placed balance',`=SUM(${ar('G')})`],['Collected',`=SUM(${ar('L')})`],['Outstanding',`=SUM(${ar('M')})`],['Recovery rate','=IF(B7=0,"n.a.",B8/B7)'],['90+ DPD exposure',`=SUMIFS(${ar('M')},${ar('H')},">=90")`],['RPC account coverage',`=IF(B6=0,"n.a.",SUM(${ar('O')})/B6)`],['Dollars per RPC contact',`=IF(SUM(${ar('J')})=0,"n.a.",B8/SUM(${ar('J')}))`]];
for(let i=0;i<kpis.length;i++){set(analysis,`A${i+6}`,kpis[i][0]);formula(analysis,`B${i+6}`,kpis[i][1]);}
analysis.getRange('A1:A60').format.columnWidth=26;analysis.getRange('B7:B9').setNumberFormat(money);analysis.getRange('B11').setNumberFormat(money);analysis.getRange('B13').setNumberFormat(money);analysis.getRange('B10').setNumberFormat('0.0%');analysis.getRange('B12').setNumberFormat('0.0%');
headers(analysis,'A16:H16',['Collector','Accounts','Placed','Collected','Recovery %','RPC coverage','$/RPC','Rank']);
const names=['Alex','Casey','Jordan','Morgan','Riley','Taylor','Unassigned'];
names.forEach((name,i)=>{let r=17+i;set(analysis,`A${r}`,name);analysis.getRange(`B${r}:H${r}`).formulas=[[`=COUNTIFS(${ar('B')},A${r})`,`=SUMIFS(${ar('G')},${ar('B')},A${r})`,`=SUMIFS(${ar('L')},${ar('B')},A${r})`,`=IF(C${r}=0,"n.a.",D${r}/C${r})`,`=IF(B${r}=0,"n.a.",SUMIFS(${ar('O')},${ar('B')},A${r})/B${r})`,`=IF(SUMIFS(${ar('J')},${ar('B')},A${r})=0,"n.a.",D${r}/SUMIFS(${ar('J')},${ar('B')},A${r}))`,`=IF(B${r}=0,"n.a.",1+COUNTIFS($E$17:$E$23,">"&E${r}))`]];});
analysis.getRange('C17:D23').setNumberFormat(money);analysis.getRange('G17:G23').setNumberFormat(money);analysis.getRange('E17:F23').setNumberFormat('0.0%');
headers(analysis,'A27:C27',['Aging bucket','Accounts','Outstanding']);
['0 Current','1 1-30','2 31-60','3 61-90','4 91-120','5 121+'].forEach((b,i)=>{let r=28+i;set(analysis,`A${r}`,b);analysis.getRange(`B${r}:C${r}`).formulas=[[`=COUNTIFS(${ar('N')},A${r})`,`=SUMIFS(${ar('M')},${ar('N')},A${r})`]];});analysis.getRange('C28:C33').setNumberFormat(money);
headers(analysis,'A37:F37',['Month','Collected','Plan input','Variance','Plan attainment','Chart month']);
for(let i=0;i<6;i++){let r=38+i;set(analysis,`A${r}`,serial(`2026-0${i+1}-01`));set(analysis,`C${r}`,500000);set(analysis,`F${r}`,['Jan','Feb','Mar','Apr','May','Jun'][i]);formula(analysis,`B${r}`,`=SUMIFS(${pr('D')},${pr('C')},">="&A${r},${pr('C')},"<"&EDATE(A${r},1))`);formula(analysis,`D${r}`,`=B${r}-C${r}`);formula(analysis,`E${r}`,`=IF(C${r}=0,"n.a.",B${r}/C${r})`);}
analysis.getRange('A38:A43').setNumberFormat('mmm-yy');analysis.getRange('B38:D43').setNumberFormat(money);analysis.getRange('E38:E43').setNumberFormat('0.0%');analysis.getRange('C38:C43').format={fill:'#FFF2CC',font:{color:'#235789'}};
set(analysis,'H38','Plan inputs are illustrative.');set(analysis,'H39','They are not employer targets.');
headers(analysis,'A48:F48',['Forecast month','Starting balance','Receipt baseline','Growth input','Forecast receipts','Ending balance']);
for(let i=0;i<3;i++){let r=49+i;set(analysis,`A${r}`,serial(`2026-0${i+7}-01`));set(analysis,`D${r}`,0.02);formula(analysis,`B${r}`,i?`=F${r-1}`:'=B9');formula(analysis,`C${r}`,i?`=E${r-1}`:'=AVERAGE(B41:B43)');formula(analysis,`E${r}`,`=IF(ISNUMBER(D${r}),MIN(B${r},C${r}*(1+D${r})),"Missing growth")`);formula(analysis,`F${r}`,`=IF(ISNUMBER(E${r}),B${r}-E${r},"Missing growth")`);}
analysis.getRange('A49:A51').setNumberFormat('mmm-yy');analysis.getRange('B49:C51').setNumberFormat(money);analysis.getRange('E49:F51').setNumberFormat(money);analysis.getRange('D49:D51').setNumberFormat('0.0%');analysis.getRange('D49:D51').format={fill:'#FFF2CC',font:{color:'#235789'}};analysis.getRange('D49:D51').dataValidation={rule:{type:'decimal',operator:'between',formula1:-1,formula2:1}};
set(analysis,'H49','Baseline: Apr–Jun receipts average.');set(analysis,'H50','Growth is an editable assumption.');set(analysis,'H51','Forecast capped at remaining balance.');
set(analysis,'H7','Recovery = collected / placed.');set(analysis,'H8','90+ DPD includes day 90.');set(analysis,'H9','RPC coverage = accounts reached / accounts.');set(analysis,'H10','$/RPC uses RPC contacts as denominator.');
analysis.getRange('H1:H60').format.columnWidth=24;
analysis.getRange('D38:D43').conditionalFormats.add('cellIs',{operator:'lessThan',formula:0,format:{font:{color:'#A34B21'},fill:'#FFF1E8'}});
// Independent terminal source reconciliations, not inputs to the forecast.
headers(analysis,'H55:J55',['Reconciliation','Workbook','Source delta']);
set(analysis,'H56','Placed balance');formula(analysis,'I56','=B7');formula(analysis,'J56',`=I56-${input.controls.placed}`);
set(analysis,'H57','Payment receipts');formula(analysis,'I57','=B8');formula(analysis,'J57',`=I57-SUM(${pr('D')})`);analysis.getRange('I56:J57').setNumberFormat('0.00');
const cards=[['A5','A6','Accounts',6],['F5','F6','Placed balance',7],['K5','K6','Collected',8],['A9','A10','Outstanding',9],['F9','F10','Recovery rate',10],['K9','K10','90+ DPD exposure',11]];
for(const [label,value,title,row] of cards){set(dash,label,title);formula(dash,value,`='Analysis'!B${row}`);dash.getRange(label).format.font={bold:true,color:navy};dash.getRange(value).format.font={size:16,bold:true,color:navy};if(row===10)dash.getRange(value).setNumberFormat('0.0%');else if(row!==6)dash.getRange(value).setNumberFormat(money);}
headers(dash,'A14:F14',['Collector','Accounts','Collected','Recovery %','RPC coverage','Rank']);
for(let i=0;i<7;i++){let r=15+i,source=17+i;dash.getRange(`A${r}:F${r}`).formulas=[['A','B','D','E','F','H'].map(c=>`='Analysis'!${c}${source}`)];}dash.getRange('C15:C21').setNumberFormat(money);dash.getRange('D15:E21').setNumberFormat('0.0%');
section(dash,'I34:N34','July–September forecast');
set(dash,'I36','Forecast receipts');formula(dash,'L36',"=SUM('Analysis'!E49:E51)");dash.getRange('L36').setNumberFormat(money);
set(dash,'I38','Ending balance');formula(dash,'L38',"='Analysis'!F51");dash.getRange('L38').setNumberFormat(money);
set(dash,'I40','Edit growth on Analysis.');set(dash,'I41','Forecast uses trailing 3 months.');
// Chart ranges bind to formula results on Analysis.
function chart(type,ranges,title,start,end){const c=dash.charts.add(type,ranges);c.title=title;c.titleTextStyle.fontSize=13;c.titleTextStyle.typeface='Arial';c.hasLegend=false;c.xAxis={axisType:'textAxis',textStyle:{typeface:'Arial',fontSize:11}};c.yAxis={numberFormatCode:'$0.0,,"M"',numberFormatSourceLinked:false,textStyle:{typeface:'Arial',fontSize:11}};c.setPosition(start,end);for(const s of c.series.items){s.fill=blue;if(type==='line')s.line={fill:blue,style:'solid',width:2};}return c;}
chart('bar',[analysis.getRange('A27:A33'),analysis.getRange('C27:C33')],'Outstanding by aging (USD millions)','H14','O30');
chart('line',[analysis.getRange('F37:F43'),analysis.getRange('B37:B43')],'Monthly collections (USD millions)','A25','G44');
dash.getRange('A46').values=[['Collections measure cash receipts. Synthetic portfolio contains no fees or adjustments.']];
dash.getRange('A47').values=[['Forecast assumes no new placements. Plan and growth inputs are illustrative.']];
wb.recalculate();
const actual=analysis.getRange('B6:B13').values.flat();
for(const [index,key] of [[0,'accounts'],[1,'placed'],[2,'collected'],[3,'outstanding'],[5,'exposure90']])if(Math.abs(actual[index]-input.controls[key])>.011)throw Error(`Reconciliation ${key}: ${actual[index]}`);
const before=analysis.getRange('E49').values[0][0];set(analysis,'D49',.1);wb.recalculate();const after=analysis.getRange('E49').values[0][0];if(!(after>before))throw Error('Forecast edit did not recalculate');set(analysis,'D49',0);wb.recalculate();if(Math.abs(analysis.getRange('E49').values[0][0]-analysis.getRange('C49').values[0][0])>.01)throw Error('Zero growth');set(analysis,'D49',null);wb.recalculate();if(analysis.getRange('E49').values[0][0]!=='Missing growth')throw Error('Missing growth');set(analysis,'D49',.02);wb.recalculate();
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:30},summary:'formula error scan'});
if(!errors.ndjson.includes('matched 0 entries'))throw Error(errors.ndjson);
console.log(errors.ndjson);
console.log((await wb.inspect({kind:'table',range:'Analysis!A5:C13',include:'values,formulas',tableMaxRows:9,tableMaxCols:3,maxChars:3000})).ndjson);
for(const [s,range,name] of [[dash,'A1:O48','dashboard'],[analysis,'A1:K58','analysis'],[accounts,'A1:O13','accounts'],[payments,'A1:F13','payments']]){const blob=await wb.render({sheetName:s.name,range,scale:1.5,format:'png'});await fs.writeFile(path.join(output,name+'.png'),new Uint8Array(await blob.arrayBuffer()));}
const xlsx=await SpreadsheetFile.exportXlsx(wb);await xlsx.save(path.join(output,'Aditya_Gujral_Collections_Dashboard.xlsx'));
await fs.writeFile(path.join(output,'validation.json'),JSON.stringify({source:'SQL collections project, seed 42',accounts:input.accounts.length,payments:input.payments.length,kpis:actual,checks:['SQL control reconciliation','growth assumption update','zero growth','missing growth input','formula error scan'],engine:'Artifact Tool; native Excel not available'},null,2));
console.log('Workbook exported');
