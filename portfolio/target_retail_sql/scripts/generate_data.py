"""Deterministic synthetic retail fixture. Python standard library only."""
import csv, random
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261004

def generate():
    rng = random.Random(SEED)
    data = ROOT / 'data'
    data.mkdir(exist_ok=True)
    def write(name, fields, rows):
        with (data / f'{name}.csv').open('w', newline='') as f:
            w=csv.writer(f); w.writerow(fields); w.writerows(rows)
    cats=['Grocery','Beauty','Apparel','Home','Electronics','Toys']
    write('categories',['category_id','category_name'],enumerate(cats,1))
    states=[('NY','Northeast'),('NJ','Northeast'),('MA','Northeast'),('IL','Midwest'),('MN','Midwest'),('OH','Midwest'),('TX','South'),('FL','South'),('GA','South'),('CA','West'),('WA','West'),('AZ','West')]
    stores=[(i,f'Synthetic Store {i:02}',*states[(i-1)%12],rng.randrange(70000,150001,1000)) for i in range(1,25)]
    write('stores',['store_id','store_name','state','region','floor_sqft'],stores)
    customers=[(i,date(2024,1,1)+timedelta(days=rng.randrange(730)),rng.choice(states)[0]) for i in range(1,10001)]
    write('customers',['customer_id','signup_date','home_state'],customers)
    bounds=[(199,2499),(499,4999),(999,7999),(999,14999),(1999,59999),(499,9999)]
    products=[]
    for i in range(1,301):
        cat=(i-1)//50+1; low,high=bounds[cat-1]
        price=rng.randrange(low,high)//100*100+99
        cost=round(price*rng.uniform(.48,.82))
        products.append((i,cat,f'{cats[cat-1]} Item {(i-1)%50+1:02}',price,cost))
    write('products',['product_id','category_id','product_name','list_price_cents','unit_cost_cents'],products)
    eligible=[[] for _ in range(730)]
    for cid,signup,_ in customers:
        eligible[(signup-date(2024,1,1)).days].append(cid)
    pools=[]; active=[]
    for bucket in eligible:
        active=active+bucket; pools.append(active)
    # Weighted holiday demand and customer/store heterogeneity are planted assumptions.
    day_weights=[1.65 if (date(2024,1,1)+timedelta(days=d)).month in (11,12) else 1 for d in range(731)]
    orders=[]; items=[]
    for oid in range(1,120001):
        day=rng.choices(range(731),weights=day_weights,k=1)[0]
        dt=date(2024,1,1)+timedelta(days=day)
        pool=pools[min(day,729)]
        cid=rng.choice(pool)
        # Some customers receive greater sampling weight without using real identities.
        if rng.random()<.30:
            frequent=[x for x in pool[:800]]
            cid=rng.choice(frequent)
        sid=rng.choices(range(1,25),weights=[1+.03*i for i in range(24)],k=1)[0]
        channel=rng.choices(['store','pickup','delivery'],[.65,.22,.13],k=1)[0]
        status='cancelled' if rng.random()<.025 else 'completed'
        orders.append((oid,cid,sid,dt,channel,status))
        for line,pid in enumerate(rng.sample(range(1,301),rng.randint(1,5)),1):
            product=products[pid-1]; qty=rng.choices([1,2,3],[.75,.20,.05],k=1)[0]
            discount=round(product[3]*rng.choice([0,0,0,.05,.10,.20]))
            ret=qty if status=='completed' and rng.random()<(.08 if product[1]==3 else .025) else 0
            items.append((oid,line,pid,qty,ret,product[3],product[4],discount))
    write('orders',['order_id','customer_id','store_id','order_date','channel','status'],orders)
    write('order_items',['order_id','line_id','product_id','quantity','returned_qty','unit_price_cents','unit_cost_cents','discount_cents'],items)
    print(f'Generated {len(orders):,} orders; {len(items):,} lines; seed {SEED}')

if __name__=='__main__': generate()
