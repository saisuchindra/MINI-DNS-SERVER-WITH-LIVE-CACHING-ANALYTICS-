import sqlite3
from pathlib import Path
from threading import Lock
from datetime import datetime, timezone

class Repository:
    def __init__(self, url):
        path=url.removeprefix("sqlite:///"); Path(path).parent.mkdir(parents=True,exist_ok=True)
        self.conn=sqlite3.connect(path, check_same_thread=False); self.conn.row_factory=sqlite3.Row; self.lock=Lock(); self._init()
    def _init(self):
        with self.conn:
            self.conn.execute('''CREATE TABLE IF NOT EXISTS dns_queries (id TEXT PRIMARY KEY,timestamp TEXT,domain TEXT,record_type TEXT,protocol TEXT,cache_status TEXT,response_source TEXT,response_time_ms REAL,status TEXT,ip_address TEXT,ttl INTEGER,simulation_mode INTEGER,flow TEXT)''')
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_queries_timestamp ON dns_queries(timestamp)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_queries_domain ON dns_queries(domain)")
            self.conn.execute('''CREATE TABLE IF NOT EXISTS simulations (id TEXT PRIMARY KEY,start_time TEXT,end_time TEXT,mode TEXT,status TEXT,query_count INTEGER)''')
    def add_query(self, x):
        with self.lock, self.conn:
            self.conn.execute("INSERT INTO dns_queries VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (x['query_id'],x['timestamp'],x['domain'],x['record_type'],x['protocol'],x['status'],x['source'],x['response_time_ms'],x['result_status'],','.join(x['ip_addresses']),x['ttl'],x['simulation_mode'], '|'.join(x['flow'])))
    def get_query(self, ident):
        row=self.conn.execute("SELECT * FROM dns_queries WHERE id=?",(ident,)).fetchone(); return dict(row) if row else None
    def recent(self, limit=50, offset=0): return [dict(x) for x in self.conn.execute("SELECT * FROM dns_queries ORDER BY timestamp DESC LIMIT ? OFFSET ?",(limit,offset))]
    def all(self): return [dict(x) for x in self.conn.execute("SELECT * FROM dns_queries")] 
    def start_simulation(self, ident, timestamp):
        with self.lock, self.conn: self.conn.execute("INSERT INTO simulations VALUES(?,?,?,?,?,?)",(ident,timestamp,None,"automatic","running",0))
    def finish_simulation(self, ident, timestamp, status, count):
        with self.lock, self.conn: self.conn.execute("UPDATE simulations SET end_time=?,status=?,query_count=? WHERE id=?",(timestamp,status,count,ident))
