import time,requests,zipfile,shutil
from pathlib import Path
from typing import Callable,Any,Optional
from functools import wraps
class RateLimiter:
    def __init__(self,rate_limit_mbps:float=None):
        self.rate_limit=rate_limit_mbps*(1024*1024)if rate_limit_mbps else None
        self.last_time=time.time()
        self.bytes_sent=0
    def limit(self,chunk_size:int):
        if not self.rate_limit:return
        self.bytes_sent+=chunk_size
        el=time.time()-self.last_time
        if el>0:
            cr=self.bytes_sent/el
            if cr>self.rate_limit:
                sl=(self.bytes_sent/self.rate_limit)-el
                if sl>0:time.sleep(sl)
    def reset(self):
        self.last_time=time.time()
        self.bytes_sent=0
def retry_with_backoff(max_retries:int=3,base_delay:float=2.0,max_delay:float=60.0,backoff_factor:float=2.0):
    def decorator(func:Callable)->Callable:
        @wraps(func)
        def wrapper(*args,**kwargs)->Any:
            rt=0
            while rt<=max_retries:
                try:return func(*args,**kwargs)
                except Exception as e:
                    rt+=1
                    if rt>max_retries:raise
                    dl=min(base_delay*(backoff_factor**(rt-1)),max_delay)
                    time.sleep(dl)
            return None
        return wrapper
    return decorator
def check_for_updates(current_version:str)->Optional[str]:
    try:
        r=requests.get('https://api.github.com/repos/yosefario-dev/asmr18/releases/latest',timeout=5)
        if r.status_code==200:
            lt=r.json().get('tag_name','').lstrip('v')
            if lt and lt!=current_version:return lt
    except:pass
    return None
def create_archive(source_dir:Path,archive_name:str=None)->Optional[Path]:
    if not source_dir.exists():return None
    an=archive_name or f"{source_dir.name}.zip"
    ap=source_dir.parent/an
    try:
        with zipfile.ZipFile(ap,'w',zipfile.ZIP_DEFLATED)as zf:
            for f in source_dir.rglob('*'):
                if f.is_file():zf.write(f,f.relative_to(source_dir))
        return ap
    except Exception:return None
def format_bytes(bt:int)->str:
    for u in['B','KB','MB','GB','TB']:
        if bt<1024.0:return f"{bt:.2f} {u}"
        bt/=1024.0
    return f"{bt:.2f} PB"
def format_speed(bps:float)->str:
    return f"{format_bytes(int(bps))}/s"
def format_time(sec:float)->str:
    if sec<60:return f"{int(sec)}s"
    elif sec<3600:return f"{int(sec//60)}m {int(sec%60)}s"
    else:return f"{int(sec//3600)}h {int((sec%3600)//60)}m"
def validate_url(url:str)->bool:
    return url.startswith('http')and'asmr18.fans'in url
def get_partial_size(fp:Path)->int:
    return fp.stat().st_size if fp.exists()else 0
