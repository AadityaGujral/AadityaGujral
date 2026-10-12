"""Local PySpark medallion pipeline using schema-enforced JSON and Parquet.

Parquet is used rather than Delta so the project runs without proprietary or
network-fetched Spark extensions. Incremental idempotency is implemented by
unioning prior silver state and deduplicating on stable event_id.
"""
from __future__ import annotations
import json, platform, shutil, uuid
from pathlib import Path
from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F
from .schemas import ACCOUNT_SCHEMA, EVENT_SCHEMA

ROOT=Path(__file__).resolve().parents[1]

def spark_session():
    return (SparkSession.builder.master('local[2]').appName('collections-medallion-portfolio')
            .config('spark.ui.enabled','false').config('spark.sql.shuffle.partitions','8')
            .config('spark.driver.host','127.0.0.1').config('spark.driver.bindAddress','127.0.0.1')
            .config('spark.driver.memory','2g').getOrCreate())

def quality_rules(df, accounts):
    typed=(df.withColumn('event_timestamp',F.expr('try_cast(event_ts as timestamp)'))
             .withColumn('event_date',F.to_date('event_timestamp'))
             .withColumn('event_month',F.date_format('event_timestamp','yyyy-MM')))
    known=accounts.select('account_id').withColumn('known_account',F.lit(True))
    typed=typed.join(F.broadcast(known),'account_id','left')
    reason=(F.when(F.col('_corrupt_record').isNotNull(),'corrupt_json')
        .when(F.col('event_id').isNull(),'missing_event_id')
        .when(~F.coalesce(F.col('known_account'),F.lit(False)),'unknown_account')
        .when(F.col('event_timestamp').isNull(),'invalid_timestamp')
        .when(~F.col('event_type').isin('payment','contact'),'invalid_event_type')
        .when(F.col('amount_cents').isNull() | (F.col('amount_cents')<0),'invalid_amount')
        .when((F.col('event_type')=='payment') & (F.col('amount_cents')<=0),'nonpositive_payment')
        .when((F.col('event_type')=='contact') & F.col('channel').isNull(),'missing_contact_channel'))
    return typed.withColumn('quarantine_reason',reason)

def process_batch(spark,batch_name,root=ROOT):
    root=Path(root);raw=root/'data/raw';lake=root/'lake'
    accounts=spark.read.schema(ACCOUNT_SCHEMA).option('header',True).csv(str(raw/'accounts.csv')).cache()
    events=(spark.read.schema(EVENT_SCHEMA).option('mode','PERMISSIVE')
            .option('columnNameOfCorruptRecord','_corrupt_record').json(str(raw/batch_name/'events_*.jsonl'))
            .withColumn('ingest_batch',F.lit(batch_name)).withColumn('ingested_at',F.current_timestamp()))
    bronze=lake/'bronze'/batch_name
    events.write.mode('overwrite').parquet(str(bronze))
    classified=quality_rules(events,accounts).cache()
    quarantine=classified.filter(F.col('quarantine_reason').isNotNull())
    valid=classified.filter(F.col('quarantine_reason').isNull()).drop('known_account','quarantine_reason','_corrupt_record','event_ts')
    accepted_current=valid.count()
    # Prefer the latest ingest batch for redelivered event IDs.
    prior_path=lake/'silver'/'events_batch_01'
    if prior_path.exists():
        spark.catalog.refreshByPath(str(prior_path))
        valid=valid.unionByName(spark.read.parquet(str(prior_path)))
    w=Window.partitionBy('event_id').orderBy(F.col('ingest_batch').desc())
    silver=valid.withColumn('_row_number',F.row_number().over(w)).filter('_row_number=1').drop('_row_number').cache()
    current_path=lake/'silver'/f'events_{batch_name}'
    staging_path=lake/'silver'/f'_staging_{batch_name}_{uuid.uuid4().hex}'
    # Write to a distinct path, then publish by rename. This avoids stale file
    # indexes and partial partition replacement on repeat local executions.
    silver.write.mode('overwrite').partitionBy('event_month').parquet(str(staging_path))
    expected_count=silver.count()
    written_count=spark.read.parquet(str(staging_path)).count()
    if written_count!=expected_count:
        raise AssertionError(f'silver staging count {written_count} != expected {expected_count}')
    if current_path.exists():shutil.rmtree(current_path)
    staging_path.replace(current_path)
    spark.catalog.refreshByPath(str(current_path))
    quarantine.write.mode('append').partitionBy('ingest_batch').parquet(str(lake/'quarantine'/'events'))
    account_out=lake/'silver'/'accounts'
    accounts.write.mode('overwrite').parquet(str(account_out))
    metrics={'batch':batch_name,'raw_rows':events.count(),'accepted_rows_before_cross_batch_dedup':accepted_current,
             'quarantined_rows':quarantine.count(),'silver_rows_after_merge':silver.count(),
             'distinct_event_ids_after_merge':silver.select('event_id').distinct().count()}
    classified.unpersist();silver.unpersist();accounts.unpersist()
    return metrics

def build_gold(spark,root=ROOT):
    root=Path(root);lake=root/'lake';out=root/'outputs'
    events=spark.read.parquet(str(lake/'silver'/'events_batch_02')).cache()
    accounts=spark.read.parquet(str(lake/'silver'/'accounts')).cache()
    enriched=events.join(F.broadcast(accounts),'account_id','inner')
    monthly=(enriched.groupBy('event_month','region','product')
      .agg(F.countDistinct('account_id').alias('active_accounts'),
           F.sum(F.when(F.col('event_type')=='payment',1).otherwise(0)).alias('payment_events'),
           F.sum(F.when(F.col('event_type')=='contact',1).otherwise(0)).alias('contact_attempts'),
           F.sum(F.when(F.col('contact_result').isin('right_party_contact','promise_to_pay'),1).otherwise(0)).alias('right_party_contacts'),
           F.sum(F.when(F.col('contact_result')=='promise_to_pay',1).otherwise(0)).alias('promises_to_pay'),
           F.sum(F.when(F.col('event_type')=='payment',F.col('amount_cents')).otherwise(0)).alias('payments_cents'))
      .withColumn('rpc_rate',F.col('right_party_contacts')/F.when(F.col('contact_attempts')>0,F.col('contact_attempts')))
      .withColumn('ptp_rate',F.col('promises_to_pay')/F.when(F.col('right_party_contacts')>0,F.col('right_party_contacts'))))
    account_perf=(enriched.groupBy('account_id','region','product','assigned_team','starting_balance_cents')
      .agg(F.sum(F.when(F.col('event_type')=='payment',F.col('amount_cents')).otherwise(0)).alias('payments_cents'),
           F.sum(F.when(F.col('event_type')=='contact',1).otherwise(0)).alias('contact_attempts'),
           F.max(F.when(F.col('event_type')=='payment',F.col('event_date'))).alias('last_payment_date'))
      .withColumn('recovery_rate',F.least(F.lit(1.0),F.col('payments_cents')/F.col('starting_balance_cents')))
      .withColumn('remaining_balance_cents',F.greatest(F.lit(0),F.col('starting_balance_cents')-F.col('payments_cents'))))
    channel=(enriched.filter(F.col('event_type')=='contact').groupBy('channel')
      .agg(F.count('*').alias('attempts'),F.sum(F.when(F.col('contact_result').isin('right_party_contact','promise_to_pay'),1).otherwise(0)).alias('right_party_contacts'),
           F.sum(F.when(F.col('contact_result')=='promise_to_pay',1).otherwise(0)).alias('promises_to_pay'))
      .withColumn('rpc_rate',F.col('right_party_contacts')/F.col('attempts'))
      .withColumn('ptp_per_attempt',F.col('promises_to_pay')/F.col('attempts')))
    for name,df,parts in [('monthly_kpis',monthly,['event_month']),('account_performance',account_perf,[]),('channel_performance',channel,[])]:
        writer=df.write.mode('overwrite');
        if parts:writer=writer.partitionBy(*parts)
        writer.parquet(str(lake/'gold'/name))
        csv_dir=out/f'_{name}_csv'
        df.orderBy(*([F.col('event_month'),F.col('region'),F.col('product')] if name=='monthly_kpis' else [F.col(df.columns[0])])).coalesce(1).write.mode('overwrite').option('header',True).csv(str(csv_dir))
        next(csv_dir.glob('part-*.csv')).replace(out/f'{name}.csv')
        shutil.rmtree(csv_dir)
    summary=(account_perf.agg(F.sum('starting_balance_cents').alias('starting_balance_cents'),F.sum('payments_cents').alias('payments_cents'),
                              F.sum('remaining_balance_cents').alias('remaining_balance_cents'),F.count('*').alias('accounts')).first().asDict())
    summary['events']=events.count();summary['payment_events']=events.filter("event_type='payment'").count();summary['contact_events']=events.filter("event_type='contact'").count()
    events.unpersist();accounts.unpersist()
    return summary

def run(root=ROOT):
    root=Path(root)
    if (root/'lake').exists():shutil.rmtree(root/'lake')
    if (root/'outputs').exists():shutil.rmtree(root/'outputs')
    (root/'outputs').mkdir()
    spark=spark_session();spark.sparkContext.setLogLevel('ERROR')
    # A long-lived local JVM can retain file indexes across repeat executions.
    spark.catalog.clearCache()
    try:
        batches=[process_batch(spark,b,root) for b in ['batch_01','batch_02']]
        # Reopen Spark for Gold so renamed local Parquet paths receive a fresh
        # file index rather than inheriting staging-path metadata.
        spark.stop()
        spark=spark_session();spark.sparkContext.setLogLevel('ERROR')
        summary=build_gold(spark,root)
        (root/'outputs'/'batch_metrics.json').write_text(json.dumps(batches,indent=2)+'\n')
        (root/'outputs'/'portfolio_summary.json').write_text(json.dumps(summary,indent=2,default=str)+'\n')
        result={'batches':batches,'summary':summary,'spark_version':spark.version,
                'spark_master':spark.sparkContext.master,'python_version':platform.python_version(),
                'shuffle_partitions':spark.conf.get('spark.sql.shuffle.partitions')}
        (root/'outputs'/'pipeline_execution.json').write_text(json.dumps(result,indent=2,default=str)+'\n')
        return result
    finally:spark.stop()

if __name__=='__main__':print(json.dumps(run(),indent=2,default=str))
