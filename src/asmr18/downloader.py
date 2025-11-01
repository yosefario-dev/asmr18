import re,json,unicodedata,subprocess,requests,time
from pathlib import Path
from typing import List,Dict,Optional
from datetime import datetime
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from tqdm import tqdm
from asmr18.logger import Logger
from asmr18.database import DownloadDB
from asmr18.utils import retry_with_backoff,RateLimiter,validate_url,get_partial_size
class DownloadError(Exception):pass
class ASMR18Downloader:
    def __init__(self,url:str,output_dir:str="downloads",use_ffmpeg:bool=True,verbose:bool=False,template:str="[{id}] {title}",logger:Logger=None,db:DownloadDB=None,dry_run:bool=False,rate_limit:float=None,max_retries:int=3):
        if not validate_url(url):raise DownloadError(f"Invalid URL: {url}")
        self.url=url;self.output_dir=Path(output_dir);self.output_dir.mkdir(parents=True,exist_ok=True)
        self.use_ffmpeg=use_ffmpeg;self.verbose=verbose;self.template=template
        self.logger=logger or Logger(verbose=verbose,quiet=False)
        self.db=db or DownloadDB()
        self.dry_run=dry_run;self.max_retries=max_retries
        self.rate_limiter=RateLimiter(rate_limit)if rate_limit else None
        self.session=requests.Session()
        self.session.headers.update({'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36','Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8','Accept-Language':'ja,en-US;q=0.9,en;q=0.8','Referer':'https://asmr18.fans/'})
        self.metadata={};self.chapters=[];self.video_files=[];self.download_id=None;self.start_time=None
    def log(self,msg:str,lvl:str="info"):
        if lvl=="error":self.logger.error(msg)
        elif lvl=="warning":self.logger.warning(msg)
        elif lvl=="debug":self.logger.debug(msg)
        else:self.logger.info(msg)
    def sanitize_filename(self,fn:str,mx:int=180)->str:
        rp={'♡':'','♥':'','❤':'','💕':'','💖':'','～':'-','〜':'-','＜':'(','＞':')','｜':'-','／':'-','＼':'-','：':'-','；':'-','＊':'','？':'','！':'','"':'','"':'','"':'','「':'[','」':']','『':'[','』':']','【':'[','】':']','　':' ','\u3000':' '}
        for o,n in rp.items():fn=fn.replace(o,n)
        cl=[]
        for c in fn:
            ct=unicodedata.category(c)
            if ct.startswith(('L','N'))or ct in('Zs','Pd','Ps','Pe','Pc'):cl.append(c)
            elif c in('.','-','_',' ','[',']','(',')',
'&'):cl.append(c)
        fn=''.join(cl)
        for c in'<>:"/\\|?*':fn=fn.replace(c,'')
        fn=''.join(c for c in fn if ord(c)>=32 and ord(c)not in range(127,160))
        fn=re.sub(r'\s+',' ',fn);fn=re.sub(r'-+','-',fn);fn=fn.strip(' -._')
        if len(fn)>mx:fn=fn[:mx].rsplit(' ',1)[0]
        return fn or'video'
    @retry_with_backoff(max_retries=3)
    def fetch_page(self)->str:
        self.log(f"Fetching: {self.url}")
        try:r=self.session.get(self.url,timeout=30);r.raise_for_status();return r.text
        except requests.RequestException as e:raise DownloadError(f"Failed to fetch page: {e}")
    def deobfuscate_js(self,pc:str)->Optional[str]:
        m=re.search(r"eval\(function\(p,a,c,k,e,d\)\{.*?\}\((.*?)\)\)",pc,re.DOTALL)
        if not m:return None
        km=re.search(r"'([^']+)'\.split\('\|'\)",m.group(1))
        if not km:return None
        kw=km.group(1).split('|')
        cm=re.search(r"^'([^']*)'",m.group(1))
        if not cm:return None
        pk=cm.group(1)
        def rpl(mt):
            v=mt.group(1)
            try:idx=int(v)if v.isdigit()else int(v,36);return kw[idx]if 0<=idx<len(kw)and kw[idx]else v
            except:return v
        return re.sub(r'\b(\w+)\b',rpl,pk)
    def extract_m3u8(self,html:str)->Optional[str]:
        self.log("Extracting m3u8 URL")
        pm=re.search(r"eval\(function\(p,a,c,k,e,d\)\{.*?\}\(.*?\)\)",html,re.DOTALL)
        if pm:
            up=self.deobfuscate_js(pm.group(0))
            if up:
                mm=re.search(r'https?://[^\'"]+\.m3u8',up)
                if mm:return mm.group(0)
        cm=re.search(r'https?://cdn\d+\.cloudintech\.net/[^\'"<>]+\.m3u8',html)
        if cm:return cm.group(0)
        rm=re.search(r'RJ\d+',html)
        if rm:
            rc=rm.group(0)
            for tu in[f"https://cdn3.cloudintech.net/file/{rc}/{rc}.m3u8",f"https://cdn3.cloudintech.net/file/{rc}/1.m3u8"]:
                self.log(f"Testing: {tu}")
                try:
                    if self.session.head(tu,timeout=5).status_code==200:self.log("Found URL");return tu
                except:continue
        return None
    def extract_metadata(self,html:str)->Dict:
        self.log("Extracting metadata")
        sp=BeautifulSoup(html,'html.parser');md={}
        te=sp.find('h1')
        if te:md['title']=te.get_text().strip()
        rm=re.search(r'RJ\d+',html)
        if rm:md['id']=rm.group(0)
        de=sp.find('div',id='post-time')
        if de:md['date']=de.get_text().strip()
        pt=sp.find('div',id='post-tag')
        if pt:
            for sn in pt.find_all('span'):
                tx=sn.get_text()
                if'声優'in tx:md['cv']=self._extract_links(sn,'/cv/')
                elif'サークル'in tx:md['circle']=self._extract_links(sn,'/circle/')
                elif'シナリオ'in tx:md['scenario']=self._extract_links(sn,'/scenario/')
                elif'イラスト'in tx:md['illustrator']=self._extract_links(sn,'/illustrator/')
                elif'ジャンル'in tx:md['genres']=self._extract_links(sn,'/genre/')
        ce=sp.find('div',id='post-category')
        if ce:
            cl=ce.find('a')
            if cl:md['category']=cl.get_text().strip()
        ve=sp.find('video',id=re.compile(r'player\d+'))
        if ve and ve.get('poster'):md['poster']=ve.get('poster')
        self.metadata=md;return md
    def _extract_links(self,se,up:str)->List[str]:
        lk=[];sb=se.find_next_sibling('a')
        while sb and sb.name=='a'and up in sb.get('href',''):
            lk.append(sb.get_text().strip());sb=sb.find_next_sibling('a')
            if sb and sb.find_previous_sibling('span')!=se:break
        return lk
    def extract_chapters(self,html:str)->List[Dict]:
        self.log("Extracting chapters")
        sp=BeautifulSoup(html,'html.parser');ch=[]
        cd=sp.find('div',id='chapter')
        if cd:
            for lk in cd.find_all('a',href='#'):
                tv=lk.get('data-value');ct=lk.get_text().strip()
                mt=re.match(r'(\d+)\.(.+)',ct)
                if mt:
                    cn=mt.group(1);ct=mt.group(2).strip()
                    tm=re.search(r'(\d{2}):(\d{2}):(\d{2})',ct)
                    ts=f"{tm.group(1)}:{tm.group(2)}:{tm.group(3)}"if tm else None
                    ch.append({'number':cn,'title':ct,'time_seconds':int(tv)if tv else None,'timestamp':ts})
        self.chapters=ch;return ch
    def extract_videos(self,html:str)->List[Dict]:
        self.log("Extracting videos")
        sp=BeautifulSoup(html,'html.parser');vs=[]
        for ti in sp.find_all('input',{'name':'tab_item'}):
            tid=ti.get('id')
            if not tid:continue
            cd=sp.find('div',{'id':f'{tid}_content'})
            if not cd:continue
            ve=cd.find('video')
            if not ve:continue
            lb=sp.find('label',{'for':tid})
            lt=lb.get_text().strip()if lb else tid
            vs.append({'id':ve.get('id'),'tab_id':tid,'label':lt,'poster':ve.get('poster')})
        mu=self.extract_m3u8(html)
        if mu and vs:vs[0]['m3u8_url']=mu;self.log(f"Found: {mu}")
        self.video_files=vs;return vs
    def download_manifest(self,mu:str)->Optional[str]:
        try:r=self.session.get(mu,timeout=10);r.raise_for_status();return r.text
        except Exception as e:self.log(f"Manifest error: {e}","error");return None
    def parse_m3u8(self,mn:str,bu:str)->List[str]:
        sg=[]
        for ln in mn.strip().split('\n'):
            ln=ln.strip()
            if ln and not ln.startswith('#'):
                if ln.endswith('.m3u8'):
                    vu=urljoin(bu,ln);vm=self.download_manifest(vu)
                    if vm:return self.parse_m3u8(vm,vu.rsplit('/',1)[0]+'/')
                else:sg.append(urljoin(bu,ln))
        return sg
    def download_ffmpeg(self,mu:str,of:Path)->bool:
        self.log("Downloading with ffmpeg")
        cmd=['ffmpeg','-i',mu,'-c','copy','-bsf:a','aac_adtstoasc',str(of),'-y','-loglevel','warning'if not self.verbose else'info','-stats']
        try:subprocess.run(cmd,check=True);return True
        except(subprocess.CalledProcessError,FileNotFoundError):return False
    def download_manual(self,mu:str,of:Path)->bool:
        self.log("Manual download")
        if self.dry_run:self.log("[DRY RUN] Would download manually");return True
        mn=self.download_manifest(mu)
        if not mn:return False
        bu=mu.rsplit('/',1)[0]+'/';sg=self.parse_m3u8(mn,bu)
        if not sg:self.log("No segments found","error");return False
        self.log(f"Found {len(sg)} segments")
        td=self.output_dir/'temp_segments';td.mkdir(exist_ok=True);sf=[]
        rt=0
        with tqdm(total=len(sg),desc="Downloading",unit="seg",disable=not self.verbose)as pb:
            for i,su in enumerate(sg):
                sf_path=td/f"seg_{i:05d}.ts";sf.append(sf_path)
                ps=get_partial_size(sf_path)
                if sf_path.exists()and ps>0:pb.update(1);continue
                ok=False
                while not ok and rt<self.max_retries:
                    try:
                        hd={'Range':f'bytes={ps}-'}if ps>0 else{}
                        r=self.session.get(su,stream=True,timeout=30,headers=hd);r.raise_for_status()
                        md='ab'if ps>0 else'wb'
                        with open(sf_path,md)as f:
                            for ch in r.iter_content(8192):
                                f.write(ch)
                                if self.rate_limiter:self.rate_limiter.limit(len(ch))
                        ok=True;pb.update(1)
                    except Exception as e:
                        rt+=1
                        if rt>=self.max_retries:self.log(f"Segment failed after {rt} retries: {e}","error");return False
                        time.sleep(2**rt)
        self.log("Merging segments")
        with open(of,'wb')as out:
            for s in sf:
                with open(s,'rb')as i:out.write(i.read())
        for s in sf:s.unlink()
        td.rmdir();return True
    def download_poster(self,poster_url:str)->Optional[Path]:
        if not poster_url:return None
        self.log("Downloading poster")
        try:
            r=self.session.get(poster_url,timeout=30);r.raise_for_status()
            ext=poster_url.split('.')[-1].split('?')[0][:4]
            pf=self.output_dir/f"temp_poster.{ext}"
            with open(pf,'wb')as f:f.write(r.content)
            return pf
        except Exception as e:self.log(f"Poster error: {e}","error");return None
    def embed_metadata(self,vf:Path)->bool:
        self.log("Embedding metadata")
        poster_url=self.metadata.get('poster')
        pf=self.download_poster(poster_url)if poster_url else None
        mf=self.output_dir/'temp_metadata.txt'
        if self.chapters:
            with open(mf,'w',encoding='utf-8')as f:
                f.write(";FFMETADATA1\n")
                for i,ch in enumerate(self.chapters):
                    if ch['time_seconds']is not None:
                        start_ms=ch['time_seconds']*1000
                        if i+1<len(self.chapters)and self.chapters[i+1]['time_seconds']is not None:
                            end_ms=self.chapters[i+1]['time_seconds']*1000
                        else:
                            end_ms=start_ms+36000000
                        f.write(f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={start_ms}\nEND={end_ms}\ntitle={ch['title']}\n\n")
        tf=vf.with_suffix('.tmp.mp4')
        if pf and pf.exists():
            cmd=['ffmpeg','-i',str(vf),'-i',str(pf)]
            if self.chapters and mf.exists():cmd.extend(['-i',str(mf),'-map_metadata','2'])
            cmd.extend(['-map','0:a','-map','1:v','-c:a','copy','-c:v','copy','-disposition:v:0','attached_pic',str(tf),'-y','-loglevel','error'])
        elif self.chapters and mf.exists():
            cmd=['ffmpeg','-i',str(vf),'-i',str(mf),'-map_metadata','1','-codec','copy',str(tf),'-y','-loglevel','error']
        else:
            if pf and pf.exists():pf.unlink()
            if mf.exists():mf.unlink()
            return True
        try:
            subprocess.run(cmd,check=True);vf.unlink();tf.rename(vf)
            if pf and pf.exists():pf.unlink()
            if mf.exists():mf.unlink()
            self.log("Metadata embedded");return True
        except(subprocess.CalledProcessError,FileNotFoundError):
            self.log("Embed failed","error")
            if tf.exists():tf.unlink()
            if pf and pf.exists():pf.unlink()
            if mf.exists():mf.unlink()
            return False
    def generate_filename(self,vi:Dict)->str:
        vr={'id':self.metadata.get('id','unknown'),'title':self.metadata.get('title','untitled'),'cv':', '.join(self.metadata.get('cv',[])),'circle':', '.join(self.metadata.get('circle',[])),'label':vi.get('label','')}
        try:fn=self.template.format(**vr)
        except KeyError:fn=f"[{vr['id']}] {vr['title']}"
        return self.sanitize_filename(fn)+'.mp4'
    def save_metadata(self):
        if not self.metadata:return
        mf=self.output_dir/f"{self.metadata.get('id','metadata')}_info.json"
        with open(mf,'w',encoding='utf-8')as f:json.dump({'url':self.url,'metadata':self.metadata,'chapters':self.chapters,'video_files':self.video_files,'download_date':datetime.now().isoformat()},f,ensure_ascii=False,indent=2)
        self.log(f"Metadata: {mf.name}")
    def download(self,skip_existing:bool=False)->bool:
        self.start_time=time.time()
        try:
            if self.db.is_completed(self.url):
                ex=self.db.get_download(self.url)
                self.log(f"Already downloaded: {ex.get('title')} at {ex.get('output_path')}","warning")
                if not skip_existing:return True
            html=self.fetch_page();self.extract_metadata(html)
            self.log(f"Title: {self.metadata.get('title','N/A')}")
            self.log(f"ID: {self.metadata.get('id','N/A')}")
            self.extract_chapters(html);self.log(f"Chapters: {len(self.chapters)}")
            self.extract_videos(html);self.log(f"Videos: {len(self.video_files)}")
            if self.dry_run:
                self.log("[DRY RUN] Would download the following:")
                for i,vi in enumerate(self.video_files):
                    fn=self.generate_filename(vi)
                    self.log(f"  {i+1}. {fn}")
                return True
            self.download_id=self.db.add_download(self.url,self.metadata.get('id'),self.metadata.get('title'),self.metadata)
            self.db.update_download(self.download_id,status='downloading')
            self.save_metadata();sc=0;fl=[]
            for i,vi in enumerate(self.video_files):
                self.log(f"Video {i+1}/{len(self.video_files)}: {vi['label']}")
                mu=vi.get('m3u8_url')
                if not mu:self.log("No m3u8 URL found","error");fl.append(vi['label']);continue
                fn=self.generate_filename(vi);of=self.output_dir/fn
                self.log(f"Output: {fn}")
                if skip_existing and of.exists():
                    fs=of.stat().st_size
                    self.log(f"File exists ({fs} bytes), skipping");sc+=1;continue
                ok=False;rt=0
                while not ok and rt<self.max_retries:
                    try:
                        ok=self.download_ffmpeg(mu,of)if self.use_ffmpeg else False
                        if not ok:ok=self.download_manual(mu,of)
                        if ok:
                            fs=of.stat().st_size if of.exists()else 0
                            self.log(f"Download complete ({fs} bytes)");sc+=1
                            self.embed_metadata(of)
                            break
                    except Exception as e:
                        rt+=1
                        self.log(f"Download attempt {rt} failed: {e}","error")
                        if rt<self.max_retries:
                            dl=2**rt
                            self.log(f"Retrying in {dl}s...","warning")
                            time.sleep(dl)
                        else:
                            self.log(f"Failed after {rt} attempts","error")
                            fl.append(vi['label'])
                            self.db.increment_retry(self.download_id)
            el=time.time()-self.start_time
            self.log(f"Completed: {sc}/{len(self.video_files)} in {int(el)}s")
            if sc==len(self.video_files):
                self.db.update_download(self.download_id,status='completed',output_path=str(self.output_dir),completed=True)
                return True
            else:
                er=f"Failed: {', '.join(fl)}"
                self.db.update_download(self.download_id,status='failed',error=er)
                return False
        except Exception as e:
            self.log(f"Critical error: {e}","error")
            if self.download_id:self.db.update_download(self.download_id,status='failed',error=str(e))
            return False
