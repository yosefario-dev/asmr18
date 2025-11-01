import logging,sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime
class Logger:
    def __init__(self,name:str="asmr18",log_dir:Path=None,verbose:bool=False,quiet:bool=False):
        self.logger=logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG if verbose else logging.INFO)
        self.logger.handlers.clear()
        self.quiet=quiet
        if not quiet:
            ch=logging.StreamHandler(sys.stdout)
            ch.setLevel(logging.DEBUG if verbose else logging.INFO)
            cf=logging.Formatter('[%(levelname)s] %(message)s')
            ch.setFormatter(cf)
            self.logger.addHandler(ch)
        log_dir=log_dir or(Path.home()/".asmr18"/"logs")
        log_dir.mkdir(parents=True,exist_ok=True)
        fh=RotatingFileHandler(log_dir/f"asmr18_{datetime.now().strftime('%Y%m%d')}.log",maxBytes=10*1024*1024,backupCount=5,encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        ff=logging.Formatter('%(asctime)s [%(levelname)s] %(message)s',datefmt='%Y-%m-%d %H:%M:%S')
        fh.setFormatter(ff)
        self.logger.addHandler(fh)
    def debug(self,msg:str):self.logger.debug(msg)
    def info(self,msg:str):self.logger.info(msg)
    def warning(self,msg:str):self.logger.warning(msg)
    def error(self,msg:str):self.logger.error(msg)
    def critical(self,msg:str):self.logger.critical(msg)
