"""Reproducible SetuBid notice deduplication experiment (standard library only)."""
import csv, hashlib, json, math, re, sqlite3, statistics, time
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/"data_2"; OUT=ROOT/"setubid"
TOK=re.compile(r"[a-z]{2,}"); NUM=re.compile(r"\b(?:rs|inr|rupees)?\s*[\d,]+(?:\.\d+)?\s*(?:lakh|crore|cr|only)?\b",re.I)
DATE=re.compile(r"\b\d{1,4}[-/. ](?:\d{1,2}|[a-z]{3,9})[-/. ,]*\d{2,4}\b",re.I)
REF=re.compile(r"\b(?:ref(?:erence)?|tender)\s*(?:no|number)?\s*[:#-]?\s*[a-z0-9/-]{5,}\b",re.I)
BOILER=re.compile(r"(national procurement aggregation service|state procurement cell|this notice is published.*?information)",re.I)
P=4294967311; K=256; BANDS=16; ROWS=4
A=[(1103515245*(i+1)+12345)%P for i in range(K)]; B=[(214013*(i+7)+2531011)%P for i in range(K)]
def norm(row):
    text=(row["title"]+" "+row["body"]).lower()
    text=BOILER.sub(" ",text); text=REF.sub(" REF ",text); text=DATE.sub(" DATE ",text); text=NUM.sub(" MONEY ",text)
    words=TOK.findall(text)
    return frozenset(" ".join(words[i:i+3]) for i in range(max(0,len(words)-2)))
def h(x): return int.from_bytes(hashlib.blake2b(x.encode(),digest_size=8).digest(),"big")%P
def sig(s):
    vals=[h(x) for x in s]
    return tuple(min((a*x+b)%P for x in vals) if vals else P for a,b in zip(A,B))
def jac(a,b): return len(a&b)/len(a|b) if a|b else 0.0
def mh(a,b): return sum(x==y for x,y in zip(a,b))/K
def key(s,band):
    start=band*ROWS
    return hashlib.blake2b(",".join(map(str,s[start:start+ROWS])).encode(),digest_size=8).hexdigest()
def curve(s): return 1-(1-s**ROWS)**BANDS
def load():
    rows=[]
    for f in sorted((DATA/"notices").glob("*.csv")):
        with f.open(encoding="utf-8",newline="") as x: rows.extend(csv.DictReader(x))
    for r in rows: r["features"]=norm(r); r["signature"]=sig(r["features"])
    return rows
def labelled(rows):
    by={r["notice_id"]:r for r in rows}; out=[]
    with (DATA/"labelled_pairs.csv").open(newline="",encoding="utf-8") as f:
        for p in csv.DictReader(f):
            a,b=by[p["notice_id_a"]],by[p["notice_id_b"]]
            out.append((p["label"],jac(a["features"],b["features"]),mh(a["signature"],b["signature"])))
    return out
def persist(rows, hot_limit=50):
    db=OUT/"setubid.db"; db.unlink(missing_ok=True); con=sqlite3.connect(db)
    con.executescript("CREATE TABLE notice(notice_id TEXT PRIMARY KEY,portal_id TEXT,title TEXT,feature_count INT);CREATE TABLE lsh_band(band INT,band_key TEXT,notice_id TEXT,PRIMARY KEY(band,band_key,notice_id));CREATE INDEX ix_lsh_lookup ON lsh_band(band,band_key);CREATE TABLE hot_bucket(band INT,band_key TEXT,bucket_size INT,PRIMARY KEY(band,band_key));")
    buckets=defaultdict(list)
    for r in rows:
        for b in range(BANDS): buckets[(b,key(r["signature"],b))].append(r["notice_id"])
    hot={k:v for k,v in buckets.items() if len(v)>hot_limit}
    con.executemany("INSERT INTO notice VALUES(?,?,?,?)",[(r["notice_id"],r["portal_id"],r["title"],len(r["features"])) for r in rows])
    con.executemany("INSERT INTO hot_bucket VALUES(?,?,?)",[(b,k,len(v)) for (b,k),v in hot.items()])
    con.executemany("INSERT INTO lsh_band VALUES(?,?,?)",[(b,k,n) for (b,k),v in buckets.items() if (b,k) not in hot for n in v]); con.commit()
    return buckets,hot
def candidates(rows,buckets,hot,mitigate):
    result={}; work=[]
    for r in rows:
        ids=set()
        for b in range(BANDS):
            bk=(b,key(r["signature"],b))
            if not(mitigate and bk in hot): ids.update(buckets[bk])
        ids.discard(r["notice_id"]);result[r["notice_id"]]=ids;work.append(len(ids))
    return result,work
def components(rows,candidate_map,threshold=.75):
    parent={r["notice_id"]:r["notice_id"] for r in rows}
    def find(x):
        while parent[x]!=x:
            parent[x]=parent[parent[x]]; x=parent[x]
        return x
    def union(a,b):
        a,b=find(a),find(b)
        if a!=b: parent[b]=a
    by={r["notice_id"]:r for r in rows}
    for a,ids in candidate_map.items():
        for b in ids:
            if b>a and jac(by[a]["features"],by[b]["features"])>=threshold: union(a,b)
    groups=defaultdict(list)
    for notice_id in parent: groups[find(notice_id)].append(notice_id)
    return groups
def card_ids(rows,candidate_map,old_cards):
    groups=components(rows,candidate_map)
    result={}
    for members in groups.values():
        prior=[old_cards[m] for m in members if m in old_cards]
        card_id=prior[0] if prior else "CARD-"+hashlib.sha256(("setubid-card-v1:"+min(members)).encode()).hexdigest()[:24]
        result.update({notice_id:card_id for notice_id in members})
    return result
def lookup_benchmark(db,buckets):
    con=sqlite3.connect(db)
    keys=list(buckets)[: min(100,len(buckets))]
    indexed=[]; scanned=[]
    for band,band_key in keys:
        started=time.perf_counter()
        rows=list(con.execute("SELECT notice_id FROM lsh_band WHERE band=? AND band_key=?",(band,band_key)))
        indexed.append((time.perf_counter()-started,len(rows)))
        started=time.perf_counter()
        rows=list(con.execute("SELECT notice_id FROM lsh_band NOT INDEXED WHERE band=? AND band_key=?",(band,band_key)))
        scanned.append((time.perf_counter()-started,len(rows)))
    plan_index=[list(x) for x in con.execute("EXPLAIN QUERY PLAN SELECT notice_id FROM lsh_band WHERE band=0 AND band_key=?",(keys[0][1],))]
    plan_scan=[list(x) for x in con.execute("EXPLAIN QUERY PLAN SELECT notice_id FROM lsh_band NOT INDEXED WHERE band=0 AND band_key=?",(keys[0][1],))]
    con.close()
    return {"lookups":len(keys),"indexed":{"mean_ms":round(statistics.mean(x[0] for x in indexed)*1000,4),"rows_returned":sum(x[1] for x in indexed),"plan":plan_index},"forced_scan":{"mean_ms":round(statistics.mean(x[0] for x in scanned)*1000,4),"rows_returned":sum(x[1] for x in scanned),"plan":plan_scan},"physical_rows_examined":"SQLite does not expose per-query B-tree visit counts; EXPLAIN QUERY PLAN is the reproducible access-path evidence."}
def write_curve():
    points=[(i/100,curve(i/100)) for i in range(101)]
    with (OUT/"retrieval_curve.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["jaccard_similarity","survival_probability"]); w.writerows(points)
    poly=" ".join(f"{50+s*620:.1f},{370-p*320:.1f}" for s,p in points)
    marker_s,marker_p=.75,curve(.75)
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="720" height="420" viewBox="0 0 720 420">
<rect width="100%" height="100%" fill="white"/><text x="360" y="28" text-anchor="middle" font-family="sans-serif" font-size="18">LSH candidate survival</text>
<line x1="50" y1="370" x2="670" y2="370" stroke="#222"/><line x1="50" y1="50" x2="50" y2="370" stroke="#222"/>
<polyline points="{poly}" fill="none" stroke="#146c94" stroke-width="3"/><line x1="{50+marker_s*620}" y1="50" x2="{50+marker_s*620}" y2="370" stroke="#c0392b" stroke-dasharray="6 4"/>
<circle cx="{50+marker_s*620}" cy="{370-marker_p*320}" r="6" fill="#c0392b"/><text x="{50+marker_s*620+8}" y="{370-marker_p*320-10}" font-family="sans-serif" font-size="13">s=0.75, p={marker_p:.3f}</text>
<text x="360" y="410" text-anchor="middle" font-family="sans-serif">true Jaccard similarity</text><text x="15" y="210" transform="rotate(-90 15 210)" text-anchor="middle" font-family="sans-serif">candidate survival probability</text>
</svg>'''
    (OUT/"retrieval_curve.svg").write_text(svg,encoding="utf-8")
def main():
    OUT.mkdir(exist_ok=True); started=time.time(); rows=load(); labels=labelled(rows)
    old_cards={}
    old_db=OUT/"setubid.db"
    if old_db.exists():
        old_con=sqlite3.connect(old_db)
        try: old_cards=dict(old_con.execute("SELECT notice_id,card_id FROM notice"))
        except sqlite3.OperationalError: pass
        old_con.close()
    buckets,hot=persist(rows); base,work0=candidates(rows,buckets,hot,False); after,work1=candidates(rows,buckets,hot,True)
    cards=card_ids(rows,after,old_cards)
    con=sqlite3.connect(OUT/"setubid.db")
    con.execute("ALTER TABLE notice ADD COLUMN card_id TEXT")
    con.executemany("UPDATE notice SET card_id=? WHERE notice_id=?",[(card,n) for n,card in cards.items()])
    con.execute("CREATE INDEX ix_notice_card ON notice(card_id)")
    con.commit(); con.close()
    write_curve(); benchmark=lookup_benchmark(OUT/"setubid.db",buckets)
    same=[]
    with (DATA/"labelled_pairs.csv").open(newline="",encoding="utf-8") as f:
        for p in csv.DictReader(f):
            if p["label"]=="same":same.append((p["notice_id_a"],p["notice_id_b"]))
    recall0=sum(b in base[a] for a,b in same)/len(same);recall1=sum(b in after[a] for a,b in same)/len(same)
    err=[abs(e-m) for _,e,m in labels]; q=lambda xs,p:sorted(xs)[int((len(xs)-1)*p)]
    groups={}
    for label in ("same","different"):
        x=[(e,m) for l,e,m in labels if l==label];groups[label]={"pairs":len(x),"exact_mean":round(statistics.mean(z[0] for z in x),3),"minhash_mean":round(statistics.mean(z[1] for z in x),3)}
    result={"notices":len(rows),"representation":"normalised 3-word shingles; boilerplate, references, dates and money replaced by placeholders","signature_size":K,"accuracy_requirement":"95% worst-case MinHash error <= 0.125; 64 hashes gives 1.96*sqrt(.25/64)=0.1225","labelled":{"mae":round(statistics.mean(err),4),"p95_abs_error":round(q(err,.95),4),"groups":groups},"lsh":{"bands":BANDS,"rows_per_band":ROWS,"probability":{str(s):round(curve(s),3) for s in (.3,.5,.75,.9)},"operating_point":"exact Jaccard merge threshold 0.75; false merge cost is 20x false duplicate cost","same_pair_recall_before":round(recall0,4),"same_pair_recall_after_hot_bucket_mitigation":round(recall1,4)},"work":{"before":{"mean":round(statistics.mean(work0),2),"p95":q(work0,.95),"max":max(work0),"candidate_pairs":sum(work0)//2},"after":{"mean":round(statistics.mean(work1),2),"p95":q(work1,.95),"max":max(work1),"candidate_pairs":sum(work1)//2},"hot_buckets":len(hot),"hot_bucket_rows":sum(len(v) for v in hot.values()),"runtime_seconds":round(time.time()-started,2)},"stable_cards":{"cards":len(set(cards.values())),"mapping_persisted":"notice.card_id is retained when an existing notice reappears; new notices joining an existing component reuse its card_id"},"database_lookup":benchmark}
    (OUT/"evidence.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    with (OUT/"bucket_distribution.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f);w.writerow(["band","bucket_size","is_hot"])
        for (b,k),v in buckets.items():w.writerow([b,len(v),int((b,k) in hot)])
    print(json.dumps(result,indent=2))
if __name__=="__main__":main()
