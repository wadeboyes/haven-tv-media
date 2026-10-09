"""Bake the next N days of departures for Haven's nearby stops from TransLink SEQ GTFS.
Source: https://gtfsrt.api.translink.com.au/GTFS/SEQ_GTFS.zip (CC BY 4.0, no key).
Output: departures.json, small enough for the TV to load. Run daily (GitHub Action)."""
import csv, io, json, zipfile, datetime, sys, urllib.request
from zoneinfo import ZoneInfo
TZ=ZoneInfo('Australia/Brisbane')
STOPS={'10228':'bus-city','4981':'bus-east','600251':'train-city','600250':'train-cleveland'}
DAYS=int(sys.argv[1]) if len(sys.argv)>1 else 8
ZIP=sys.argv[2] if len(sys.argv)>2 else None
def open_zip():
    if ZIP: return zipfile.ZipFile(ZIP)
    data=urllib.request.urlopen('https://gtfsrt.api.translink.com.au/GTFS/SEQ_GTFS.zip',timeout=120).read()
    return zipfile.ZipFile(io.BytesIO(data))
z=open_zip()
def rd(n): return csv.DictReader(io.TextIOWrapper(z.open(n),encoding='utf-8-sig'))
routes={r['route_id']:r for r in rd('routes.txt')}
trips={r['trip_id']:r for r in rd('trips.txt')}
cal={r['service_id']:r for r in rd('calendar.txt')}
exc={}
for r in rd('calendar_dates.txt'): exc.setdefault(r['date'],{})[r['service_id']]=r['exception_type']
today=datetime.datetime.now(TZ).date()
dates=[today+datetime.timedelta(days=i) for i in range(-1,DAYS)]  # include yesterday for after midnight trips
wd=['monday','tuesday','wednesday','thursday','friday','saturday','sunday']
def active(sid,d):
    ds=d.strftime('%Y%m%d'); e=exc.get(ds,{}).get(sid)
    if e=='1': return True
    if e=='2': return False
    c=cal.get(sid)
    return bool(c) and c['start_date']<=ds<=c['end_date'] and c[wd[d.weekday()]]=='1'
st=[]
f=io.TextIOWrapper(z.open('stop_times.txt'),encoding='utf-8-sig'); r=csv.reader(f); h=next(r)
it,isd,idp=h.index('trip_id'),h.index('stop_id'),h.index('departure_time')
for row in r:
    if row[isd] in STOPS: st.append((row[isd],row[it],row[idp]))
out=[]
now=datetime.datetime.now(TZ)
for sid,tid,dep in st:
    t=trips[tid]; ro=routes[t['route_id']]
    hh,mm,ss=map(int,dep.split(':'))
    for d in dates:
        if not active(t['service_id'],d): continue
        when=datetime.datetime(d.year,d.month,d.day,tzinfo=TZ)+datetime.timedelta(hours=hh,minutes=mm,seconds=ss)
        if when<now-datetime.timedelta(minutes=5) or when>now+datetime.timedelta(days=DAYS): continue
        out.append({'s':sid,'t':int(when.timestamp()),'r':ro['route_short_name'],'h':t.get('trip_headsign',''),'id':tid})
out.sort(key=lambda x:(x['t'],x['s']))
fi=next(rd('feed_info.txt'))
doc={'generatedAt':int(now.timestamp()),'source':'Translink SEQ GTFS, CC BY 4.0','feedVersion':fi.get('feed_start_date','')+'..'+fi.get('feed_end_date',''),
     'stops':STOPS,'departures':out}
json.dump(doc,open('departures.json','w'),separators=(',',':'),ensure_ascii=False)
print(len(out),'departures')
