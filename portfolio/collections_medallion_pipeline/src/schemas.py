from pyspark.sql.types import *

ACCOUNT_SCHEMA=StructType([
    StructField('account_id',LongType(),False),StructField('opened_date',DateType(),False),
    StructField('region',StringType(),False),StructField('product',StringType(),False),
    StructField('starting_balance_cents',LongType(),False),StructField('assigned_team',StringType(),False)])
EVENT_SCHEMA=StructType([
    StructField('event_id',StringType(),True),StructField('account_id',LongType(),True),
    StructField('event_ts',StringType(),True),StructField('event_type',StringType(),True),
    StructField('channel',StringType(),True),StructField('contact_result',StringType(),True),
    StructField('amount_cents',LongType(),True),StructField('source_system',StringType(),True),
    StructField('_corrupt_record',StringType(),True)])
