import sqlite3,json
from pathlib import Path
from datetime import datetime
from typing import List,Dict,Optional
class DownloadDB:
    def __init__(self,db_path:Path=None):
        self.db_path=db_path or(Path.home()/".asmr18"/"downloads.db")
        self.db_path.parent.mkdir(parents=True,exist_ok=True)
        self.conn=None;self._init_db()
    def _init_db(self):
        self.conn=sqlite3.connect(str(self.db_path))
        self.conn.row_factory=sqlite3.Row
        c=self.conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS downloads(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL UNIQUE,
            work_id TEXT,
            title TEXT,
            status TEXT DEFAULT 'pending',
            output_path TEXT,
            file_size INTEGER,
            started_at TEXT,
            completed_at TEXT,
            error TEXT,
            metadata TEXT,
            retry_count INTEGER DEFAULT 0
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS download_files(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            download_id INTEGER,
            file_path TEXT,
            file_size INTEGER,
            downloaded_bytes INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            FOREIGN KEY(download_id) REFERENCES downloads(id)
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS stats(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            total_downloads INTEGER DEFAULT 0,
            successful_downloads INTEGER DEFAULT 0,
            failed_downloads INTEGER DEFAULT 0,
            total_bytes INTEGER DEFAULT 0,
            total_time_seconds REAL DEFAULT 0
        )''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_url ON downloads(url)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_work_id ON downloads(work_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_status ON downloads(status)')
        self.conn.commit()
    def add_download(self,url:str,work_id:str=None,title:str=None,metadata:dict=None)->int:
        c=self.conn.cursor()
        try:
            c.execute('INSERT INTO downloads(url,work_id,title,started_at,metadata)VALUES(?,?,?,?,?)',
                (url,work_id,title,datetime.now().isoformat(),json.dumps(metadata)if metadata else None))
            self.conn.commit()
            return c.lastrowid
        except sqlite3.IntegrityError:
            c.execute('SELECT id FROM downloads WHERE url=?',(url,))
            return c.fetchone()[0]
    def update_download(self,download_id:int,status:str=None,output_path:str=None,file_size:int=None,error:str=None,completed:bool=False):
        c=self.conn.cursor();up=[]
        if status:up.append(('status',status))
        if output_path:up.append(('output_path',output_path))
        if file_size:up.append(('file_size',file_size))
        if error:up.append(('error',error))
        if completed:up.append(('completed_at',datetime.now().isoformat()))
        if not up:return
        sq='UPDATE downloads SET '+','.join(f'{k}=?'for k,_ in up)+' WHERE id=?'
        c.execute(sq,[v for _,v in up]+[download_id])
        self.conn.commit()
    def increment_retry(self,download_id:int):
        c=self.conn.cursor()
        c.execute('UPDATE downloads SET retry_count=retry_count+1 WHERE id=?',(download_id,))
        self.conn.commit()
    def get_download(self,url:str)->Optional[Dict]:
        c=self.conn.cursor()
        c.execute('SELECT * FROM downloads WHERE url=?',(url,))
        r=c.fetchone()
        return dict(r)if r else None
    def is_completed(self,url:str)->bool:
        d=self.get_download(url)
        return d and d['status']=='completed'
    def get_history(self,limit:int=50)->List[Dict]:
        c=self.conn.cursor()
        c.execute('SELECT * FROM downloads ORDER BY started_at DESC LIMIT ?',(limit,))
        return[dict(r)for r in c.fetchall()]
    def get_stats(self)->Dict:
        c=self.conn.cursor()
        c.execute('SELECT COUNT(*)as total,SUM(CASE WHEN status="completed"THEN 1 ELSE 0 END)as completed,SUM(CASE WHEN status="failed"THEN 1 ELSE 0 END)as failed,SUM(file_size)as total_size FROM downloads')
        r=c.fetchone()
        return dict(r)if r else{}
    def add_file(self,download_id:int,file_path:str,file_size:int=0)->int:
        c=self.conn.cursor()
        c.execute('INSERT INTO download_files(download_id,file_path,file_size,created_at)VALUES(?,?,?,?)',
            (download_id,file_path,file_size,datetime.now().isoformat()))
        self.conn.commit()
        return c.lastrowid
    def update_file_progress(self,file_id:int,downloaded_bytes:int,status:str=None):
        c=self.conn.cursor();up=['downloaded_bytes=?']
        vl=[downloaded_bytes]
        if status:up.append('status=?');vl.append(status)
        c.execute(f'UPDATE download_files SET {",".join(up)} WHERE id=?',vl+[file_id])
        self.conn.commit()
    def get_file_progress(self,download_id:int,file_path:str)->Optional[Dict]:
        c=self.conn.cursor()
        c.execute('SELECT * FROM download_files WHERE download_id=? AND file_path=?',(download_id,file_path))
        r=c.fetchone()
        return dict(r)if r else None
    def cleanup_old(self,days:int=90):
        c=self.conn.cursor()
        c.execute("DELETE FROM downloads WHERE started_at<datetime('now','-'||?||' days')",(days,))
        self.conn.commit()
    def close(self):
        if self.conn:self.conn.close()
