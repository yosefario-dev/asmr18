import sys,yaml,click,os,shutil,subprocess,concurrent.futures,time
from pathlib import Path
from colorama import init,Fore,Style
from asmr18.downloader import ASMR18Downloader,DownloadError
from asmr18.database import DownloadDB
from asmr18.logger import Logger
from asmr18.utils import check_for_updates,create_archive,format_bytes,format_time
init(autoreset=True)
__version__="0.0.5"
CONFIG_DIR=Path.home()/".asmr18"
CONFIG_FILE=CONFIG_DIR/"config.yaml"
UPDATE_CHECK_FILE=CONFIG_DIR/"last_update_check"
def should_check_update()->bool:
    if not UPDATE_CHECK_FILE.exists():return True
    try:last_check=float(UPDATE_CHECK_FILE.read_text().strip());return time.time()-last_check>86400
    except:return True
def mark_update_checked():
    try:CONFIG_DIR.mkdir(exist_ok=True);UPDATE_CHECK_FILE.write_text(str(time.time()))
    except:pass
def auto_check_update(quiet=False):
    if not should_check_update():return
    try:
        nv=check_for_updates(__version__)
        if nv and not quiet:click.echo(f"\n{Fore.YELLOW}[!]{Style.RESET_ALL} New version available: v{nv} (current: v{__version__})");click.echo(f"{Fore.CYAN}[*]{Style.RESET_ALL} Run: {Fore.GREEN}asmr18 --update{Style.RESET_ALL} to update\n")
        mark_update_checked()
    except:pass
def update_package(force=False):
    click.echo(f"\n{Fore.CYAN}[*] Checking for updates...{Style.RESET_ALL}")
    nv=check_for_updates(__version__)
    if not nv:click.echo(f"{Fore.GREEN}[+]{Style.RESET_ALL} Already up to date! (v{__version__})");return
    click.echo(f"{Fore.GREEN}[+]{Style.RESET_ALL} New version available: v{nv}");click.echo(f"    Current version: v{__version__}")
    if not force:
        if not click.confirm(f"\n{Fore.YELLOW}Update to v{nv}?{Style.RESET_ALL}",default=True):click.echo(f"{Fore.CYAN}[*]{Style.RESET_ALL} Update cancelled");return
    click.echo(f"\n{Fore.CYAN}[*]{Style.RESET_ALL} Updating asmr18...")
    SYSTEM_INSTALL=Path("/opt/asmr18-downloader");USER_INSTALL=Path.home()/".local/share/asmr18-downloader"
    if SYSTEM_INSTALL.exists():install_dir=SYSTEM_INSTALL;needs_sudo=True
    elif USER_INSTALL.exists():install_dir=USER_INSTALL;needs_sudo=False
    else:click.echo(f"{Fore.YELLOW}[!]{Style.RESET_ALL} Installation directory not found, trying pip update...");needs_sudo=False;install_dir=None
    try:
        if install_dir and install_dir.exists():
            venv_python=install_dir/"venv"/"bin"/"python";venv_pip=install_dir/"venv"/"bin"/"pip"
            if venv_python.exists()and venv_pip.exists():
                click.echo(f"{Fore.CYAN}[*]{Style.RESET_ALL} Updating package in virtual environment...")
                cmd=[str(venv_pip),"install","--upgrade","asmr18"]
                if needs_sudo:click.echo(f"{Fore.YELLOW}[!]{Style.RESET_ALL} System installation detected - sudo required");cmd=["sudo"]+cmd
                result=subprocess.run(cmd,capture_output=True,text=True)
                if result.returncode==0:click.echo(f"{Fore.GREEN}[+]{Style.RESET_ALL} Successfully updated to v{nv}!");click.echo(f"{Fore.CYAN}[*]{Style.RESET_ALL} Restart your terminal or run the command again to use the new version")
                else:
                    click.echo(f"{Fore.RED}[-]{Style.RESET_ALL} Update failed!")
                    if result.stderr:click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} {result.stderr}")
                    click.echo(f"\n{Fore.CYAN}[*]{Style.RESET_ALL} Trying alternative update method...")
                    alt_cmd=[str(venv_pip),"install","--upgrade","git+https://github.com/yosefario-dev/asmr18.git"]
                    if needs_sudo:alt_cmd=["sudo"]+alt_cmd
                    alt_result=subprocess.run(alt_cmd,capture_output=True,text=True)
                    if alt_result.returncode==0:click.echo(f"{Fore.GREEN}[+]{Style.RESET_ALL} Successfully updated to v{nv}!")
                    else:click.echo(f"{Fore.RED}[-]{Style.RESET_ALL} Alternative update also failed");click.echo(f"\n{Fore.YELLOW}Manual update required:{Style.RESET_ALL}");click.echo("  Run the install script again:");click.echo("  curl -sSL https://raw.githubusercontent.com/yosefario-dev/asmr18/main/install.sh | sh")
            else:raise FileNotFoundError("Virtual environment not found")
        else:
            click.echo(f"{Fore.CYAN}[*]{Style.RESET_ALL} Updating via pip...");result=subprocess.run(["pip","install","--upgrade","asmr18"],capture_output=True,text=True)
            if result.returncode==0:click.echo(f"{Fore.GREEN}[+]{Style.RESET_ALL} Successfully updated to v{nv}!");click.echo(f"{Fore.CYAN}[*]{Style.RESET_ALL} Restart your terminal or run the command again to use the new version")
            else:click.echo(f"{Fore.RED}[-]{Style.RESET_ALL} Update failed!");click.echo(f"\n{Fore.YELLOW}Manual update:{Style.RESET_ALL}");click.echo("  pip install --upgrade asmr18");click.echo("  OR");click.echo("  curl -sSL https://raw.githubusercontent.com/yosefario-dev/asmr18/main/install.sh | sh")
    except Exception as e:click.echo(f"{Fore.RED}[-]{Style.RESET_ALL} Update failed: {e}");click.echo(f"\n{Fore.YELLOW}Manual update:{Style.RESET_ALL}");click.echo("  curl -sSL https://raw.githubusercontent.com/yosefario-dev/asmr18/main/install.sh | sh")
def load_config()->dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE,'r')as f:return yaml.safe_load(f)or{}
        except:return{}
    return{}
def save_config(cfg:dict):
    CONFIG_DIR.mkdir(exist_ok=True)
    try:
        with open(CONFIG_FILE,'w')as f:yaml.dump(cfg,f,default_flow_style=False)
        click.echo(f"{Fore.GREEN}[+]{Style.RESET_ALL} Config saved to {CONFIG_FILE}")
    except Exception as e:click.echo(f"{Fore.RED}[-]{Style.RESET_ALL} Failed: {e}",err=True)
def list_config():
    click.echo(f"\n{Fore.CYAN}[*] Current Configuration{Style.RESET_ALL}\n")
    if CONFIG_FILE.exists():
        cfg=load_config()
        if cfg:
            for key,val in cfg.items():click.echo(f"  {Fore.GREEN}{key}{Style.RESET_ALL}: {val}")
            click.echo(f"\n{Fore.CYAN}Config file:{Style.RESET_ALL} {CONFIG_FILE}")
        else:click.echo(f"  {Fore.YELLOW}(empty){Style.RESET_ALL}")
    else:click.echo(f"  {Fore.YELLOW}No config file found{Style.RESET_ALL}\n  Default: {CONFIG_FILE}")
def reset_config():
    if CONFIG_FILE.exists():
        try:
            CONFIG_FILE.unlink()
            click.echo(f"{Fore.GREEN}[+]{Style.RESET_ALL} Config reset successfully")
            if CONFIG_DIR.exists()and not any(CONFIG_DIR.iterdir()):CONFIG_DIR.rmdir()
        except Exception as e:click.echo(f"{Fore.RED}[-]{Style.RESET_ALL} Failed: {e}",err=True)
    else:click.echo(f"{Fore.YELLOW}[!]{Style.RESET_ALL} No config file to reset")
def show_stats():
    db=DownloadDB()
    st=db.get_stats()
    click.echo(f"\n{Fore.CYAN}=== Download Statistics ==={Style.RESET_ALL}\n")
    click.echo(f"{Fore.GREEN}Total Downloads:{Style.RESET_ALL} {st.get('total',0)}")
    click.echo(f"{Fore.GREEN}Completed:{Style.RESET_ALL} {st.get('completed',0)}")
    click.echo(f"{Fore.RED}Failed:{Style.RESET_ALL} {st.get('failed',0)}")
    ts=st.get('total_size')or 0
    click.echo(f"{Fore.CYAN}Total Size:{Style.RESET_ALL} {format_bytes(ts)}")
    db.close()
def show_history(limit:int=20):
    db=DownloadDB()
    hs=db.get_history(limit)
    if not hs:click.echo(f"\n{Fore.YELLOW}No download history{Style.RESET_ALL}");db.close();return
    click.echo(f"\n{Fore.CYAN}=== Download History (last {len(hs)}) ==={Style.RESET_ALL}\n")
    for h in hs:
        st=h['status']
        sc=Fore.GREEN if st=='completed'else(Fore.RED if st=='failed'else Fore.YELLOW)
        click.echo(f"{sc}[{st.upper()}]{Style.RESET_ALL} {h.get('title','N/A')}")
        click.echo(f"  ID: {h.get('work_id','N/A')} | Started: {h.get('started_at','N/A')[:19]}")
        if h.get('output_path'):click.echo(f"  Path: {h['output_path']}")
        if h.get('error'):click.echo(f"  {Fore.RED}Error: {h['error']}{Style.RESET_ALL}")
        click.echo()
    db.close()
def cleanup_db(days:int=90):
    db=DownloadDB()
    db.cleanup_old(days)
    click.echo(f"{Fore.GREEN}[+]{Style.RESET_ALL} Cleaned up entries older than {days} days")
    db.close()
def check_updates():
    click.echo(f"{Fore.CYAN}[*]{Style.RESET_ALL} Checking for updates...")
    nv=check_for_updates(__version__)
    if nv:
        click.echo(f"{Fore.GREEN}[+]{Style.RESET_ALL} New version available: v{nv}")
        click.echo(f"    Current: v{__version__}")
        click.echo(f"\n{Fore.CYAN}[*]{Style.RESET_ALL} Run: {Fore.GREEN}asmr18 --update{Style.RESET_ALL} to update")
    else:click.echo(f"{Fore.GREEN}[+]{Style.RESET_ALL} You're up to date! (v{__version__})")
def uninstall(force=False):
    """Uninstall asmr18"""
    click.echo(f"\n{Fore.CYAN}[*] ASMR18 Uninstaller{Style.RESET_ALL}\n")
    SYSTEM_INSTALL=Path("/opt/asmr18-downloader")
    SYSTEM_BIN=Path("/usr/local/bin/asmr18")
    USER_INSTALL=Path.home()/".local/share/asmr18-downloader"
    USER_BIN=Path.home()/".local/bin/asmr18"
    found=[];types=[]
    if SYSTEM_INSTALL.exists()or SYSTEM_BIN.exists():found.append("system");types.append(("system",SYSTEM_INSTALL,SYSTEM_BIN,True))
    if USER_INSTALL.exists()or USER_BIN.exists():found.append("user");types.append(("user",USER_INSTALL,USER_BIN,False))
    if not found:click.echo(f"{Fore.RED}[-]{Style.RESET_ALL} No installation found!\n");click.echo("Checked locations:");click.echo("  - /opt/asmr18-downloader");click.echo("  - /usr/local/bin/asmr18");click.echo(f"  - {USER_INSTALL}");click.echo(f"  - {USER_BIN}");sys.exit(1)
    click.echo(f"{Fore.YELLOW}[!]{Style.RESET_ALL} Found installation(s): {', '.join(found)}\n")
    if len(types)>1:
        click.echo("Multiple installations detected:")
        click.echo("  1) Remove system installation (requires sudo)")
        click.echo("  2) Remove user installation")
        click.echo("  3) Remove both")
        if not force:choice=click.prompt("Select option",type=click.IntRange(1,3),default=3)
        else:choice=3
        if choice==1:types=[t for t in types if t[0]=="system"]
        elif choice==2:types=[t for t in types if t[0]=="user"]
    if not force:
        click.echo(f"\n{Fore.YELLOW}[!]{Style.RESET_ALL} This will remove ASMR18 Downloader")
        if any(t[3]for t in types):click.echo(f"{Fore.YELLOW}[!]{Style.RESET_ALL} System files (may require sudo password)")
        if not click.confirm("Continue?",default=False):click.echo(f"{Fore.CYAN}[*]{Style.RESET_ALL} Cancelled");sys.exit(0)
    for itype,idir,bfile,needs_sudo in types:
        click.echo(f"\n{Fore.CYAN}[*]{Style.RESET_ALL} Removing {itype} installation...")
        try:
            if idir.exists():
                if needs_sudo:subprocess.run(["sudo","rm","-rf",str(idir)],check=True);click.echo(f"{Fore.GREEN}[+]{Style.RESET_ALL} Removed {idir}")
                else:shutil.rmtree(idir);click.echo(f"{Fore.GREEN}[+]{Style.RESET_ALL} Removed {idir}")
            if bfile.exists():
                if needs_sudo:subprocess.run(["sudo","rm","-f",str(bfile)],check=True);click.echo(f"{Fore.GREEN}[+]{Style.RESET_ALL} Removed {bfile}")
                else:bfile.unlink();click.echo(f"{Fore.GREEN}[+]{Style.RESET_ALL} Removed {bfile}")
        except subprocess.CalledProcessError:click.echo(f"{Fore.RED}[-]{Style.RESET_ALL} Failed (sudo required or permission denied)");sys.exit(1)
        except Exception as e:click.echo(f"{Fore.RED}[-]{Style.RESET_ALL} Error: {e}");sys.exit(1)
    desktop=Path.home()/".local/share/applications/asmr18-downloader.desktop"
    if desktop.exists():
        try:desktop.unlink();click.echo(f"{Fore.GREEN}[+]{Style.RESET_ALL} Removed desktop entry")
        except:pass
    if CONFIG_DIR.exists():
        if force or click.confirm(f"\nRemove configuration directory ({CONFIG_DIR})?",default=False):
            try:shutil.rmtree(CONFIG_DIR);click.echo(f"{Fore.GREEN}[+]{Style.RESET_ALL} Configuration removed")
            except Exception as e:click.echo(f"{Fore.RED}[-]{Style.RESET_ALL} Failed to remove config: {e}")
        else:click.echo(f"{Fore.CYAN}[*]{Style.RESET_ALL} Configuration kept at {CONFIG_DIR}")
    click.echo(f"\n{Fore.GREEN}[+]{Style.RESET_ALL} Uninstallation complete!")
    if shutil.which("asmr18"):click.echo(f"{Fore.YELLOW}[!]{Style.RESET_ALL} Command 'asmr18' still in PATH. Restart terminal or run: hash -r")
    else:click.echo(f"{Fore.GREEN}[+]{Style.RESET_ALL} Command 'asmr18' removed from PATH")
@click.command()
@click.argument('url',required=False)
@click.option('-o','--output',default='downloads',help='Output directory',type=click.Path(file_okay=False,dir_okay=True,writable=True))
@click.option('-v','--verbose',is_flag=True,help='Verbose logging')
@click.option('-q','--quiet',is_flag=True,help='Quiet mode')
@click.option('--no-ffmpeg',is_flag=True,help='Disable ffmpeg')
@click.option('--template',default='[{id}] {title}',help='Filename template',show_default=True)
@click.option('--batch',type=click.Path(exists=True,file_okay=True,dir_okay=False,readable=True),help='Batch file with URLs')
@click.option('--skip-existing',is_flag=True,help='Skip existing files')
@click.option('--dry-run',is_flag=True,help='Preview without downloading')
@click.option('--rate-limit',type=float,help='Bandwidth limit in MB/s')
@click.option('--max-retries',type=int,default=3,help='Max retry attempts',show_default=True)
@click.option('--parallel',type=int,default=1,help='Parallel downloads in batch mode',show_default=True)
@click.option('--archive',is_flag=True,help='Create zip archive after download')
@click.option('--save-config','save_config_flag',is_flag=True,help='Save current settings to config')
@click.option('--list-config','list_config_flag',is_flag=True,help='Show current configuration')
@click.option('--reset-config','reset_config_flag',is_flag=True,help='Reset configuration to defaults')
@click.option('--stats','stats_flag',is_flag=True,help='Show download statistics')
@click.option('--history',type=int,help='Show download history (limit)')
@click.option('--cleanup',type=int,help='Cleanup old DB entries (days)')
@click.option('--check-update','check_update_flag',is_flag=True,help='Check for updates')
@click.option('--update','update_flag',is_flag=True,help='Update to latest version')
@click.option('--uninstall','uninstall_flag',is_flag=True,help='Uninstall asmr18')
@click.option('--force',is_flag=True,help='Force operation without confirmation')
@click.option('--version','version_flag',is_flag=True,help='Show version information')
def main(url,output,verbose,quiet,no_ffmpeg,template,batch,skip_existing,dry_run,rate_limit,max_retries,parallel,archive,save_config_flag,list_config_flag,reset_config_flag,stats_flag,history,cleanup,check_update_flag,update_flag,uninstall_flag,force,version_flag):
    """ASMR18.fans Downloader - Download content with metadata extraction and chapter support.

    Examples:
      asmr18 "https://asmr18.fans/boys/rj01439456/"
      asmr18 "URL" -o ~/Downloads/ASMR --rate-limit 5
      asmr18 --batch urls.txt --parallel 3
      asmr18 --dry-run "URL"
      asmr18 --stats
      asmr18 --history 10
      asmr18 --check-update
      asmr18 --update
    """
    if version_flag:click.echo(f"ASMR18 Downloader v{__version__}");return
    if check_update_flag:check_updates();return
    if update_flag:update_package(force=force);return
    if uninstall_flag:uninstall(force=force);return
    if list_config_flag:list_config();return
    if reset_config_flag:reset_config();return
    if stats_flag:show_stats();return
    if history is not None:show_history(history or 20);return
    if cleanup:cleanup_db(cleanup);return
    auto_check_update(quiet=quiet)
    cfg=load_config()
    use_ffmpeg=not no_ffmpeg if no_ffmpeg else cfg.get('use_ffmpeg',True)
    output_dir=output if output!='downloads'else cfg.get('output_dir','downloads')
    template_str=template if template!='[{id}] {title}'else cfg.get('template','[{id}] {title}')
    skip_existing_flag=skip_existing or cfg.get('skip_existing',False)
    verbose_flag=verbose or(cfg.get('verbose',False)if not quiet else False)
    rate_limit_val=rate_limit or cfg.get('rate_limit')
    max_retries_val=max_retries if max_retries!=3 else cfg.get('max_retries',3)
    parallel_val=parallel if parallel!=1 else cfg.get('parallel',1)
    if save_config_flag:
        sc={'output_dir':output_dir,'use_ffmpeg':use_ffmpeg,'template':template_str,'skip_existing':skip_existing_flag,'verbose':verbose_flag,'max_retries':max_retries_val,'parallel':parallel_val}
        if rate_limit_val:sc['rate_limit']=rate_limit_val
        save_config(sc)
    if not url and not batch:click.echo(f"{Fore.RED}[-]{Style.RESET_ALL} Error: Provide URL or --batch");click.echo("Usage: asmr18 [URL] or asmr18 --batch [FILE]");sys.exit(1)
    if not quiet:click.echo(f"\n{Fore.CYAN}[*] ASMR18 Downloader v{__version__}{Style.RESET_ALL}\n")
    lg=Logger(verbose=verbose_flag,quiet=quiet)
    db=DownloadDB()
    if batch:download_batch(batch,output_dir,use_ffmpeg,template_str,skip_existing_flag,verbose_flag,quiet,lg,db,dry_run,rate_limit_val,max_retries_val,parallel_val,archive)
    else:
        ok=download_single(url,output_dir,use_ffmpeg,template_str,skip_existing_flag,verbose_flag,quiet,lg,db,dry_run,rate_limit_val,max_retries_val)
        if ok and archive and not dry_run:
            click.echo(f"\n{Fore.CYAN}[*]{Style.RESET_ALL} Creating archive...")
            ap=create_archive(Path(output_dir))
            if ap:click.echo(f"{Fore.GREEN}[+]{Style.RESET_ALL} Archive created: {ap}")
            else:click.echo(f"{Fore.RED}[-]{Style.RESET_ALL} Archive creation failed")
    db.close()
def download_single(url,output_dir,use_ffmpeg,template,skip_existing,verbose,quiet,logger,db,dry_run,rate_limit,max_retries)->bool:
    try:
        if not quiet:click.echo(f"{Fore.CYAN}[*]{Style.RESET_ALL} Starting download...")
        dl=ASMR18Downloader(url=url,output_dir=output_dir,use_ffmpeg=use_ffmpeg,verbose=verbose,template=template,logger=logger,db=db,dry_run=dry_run,rate_limit=rate_limit,max_retries=max_retries)
        ok=dl.download(skip_existing=skip_existing)
        if ok:
            if not quiet:click.echo(f"\n{Fore.GREEN}[+]{Style.RESET_ALL} Complete! Output: {Path(output_dir).absolute()}")
            return True
        else:
            if not quiet:click.echo(f"\n{Fore.RED}[-]{Style.RESET_ALL} Failed!")
            return False
    except DownloadError as e:click.echo(f"\n{Fore.RED}[-]{Style.RESET_ALL} Error: {e}",err=True);return False
    except KeyboardInterrupt:click.echo(f"\n\n{Fore.YELLOW}[!]{Style.RESET_ALL} Cancelled");sys.exit(130)
    except Exception as e:click.echo(f"\n{Fore.RED}[-]{Style.RESET_ALL} Error: {e}",err=True);return False
def download_batch(batch_file,output_dir,use_ffmpeg,template,skip_existing,verbose,quiet,logger,db,dry_run,rate_limit,max_retries,parallel,archive):
    try:
        with open(batch_file,'r',encoding='utf-8')as f:urls=[l.strip()for l in f if l.strip()and not l.startswith('#')]
        if not urls:click.echo(f"{Fore.RED}[-]{Style.RESET_ALL} No URLs in batch file!");sys.exit(1)
        if not quiet:click.echo(f"{Fore.CYAN}[*]{Style.RESET_ALL} Found {len(urls)} URL(s)")
        if parallel>1:
            if not quiet:click.echo(f"{Fore.CYAN}[*]{Style.RESET_ALL} Parallel downloads: {parallel}")
            sc=0;fl=[]
            with concurrent.futures.ThreadPoolExecutor(max_workers=parallel)as ex:
                ft={ex.submit(download_single,u,output_dir,use_ffmpeg,template,skip_existing,verbose,True,logger,db,dry_run,rate_limit,max_retries):u for u in urls}
                for i,fu in enumerate(concurrent.futures.as_completed(ft),1):
                    u=ft[fu]
                    try:
                        if fu.result():sc+=1
                        else:fl.append(u)
                        if not quiet:click.echo(f"{Fore.CYAN}[*]{Style.RESET_ALL} Progress: {i}/{len(urls)}")
                    except Exception as e:
                        fl.append(u)
                        if not quiet:click.echo(f"{Fore.RED}[-]{Style.RESET_ALL} Error downloading {u}: {e}")
        else:
            sc=0;fl=[]
            for i,u in enumerate(urls,1):
                if not quiet:click.echo(f"\n{Fore.CYAN}{'='*60}\n[{i}/{len(urls)}] {u}\n{'='*60}{Style.RESET_ALL}")
                if download_single(u,output_dir,use_ffmpeg,template,skip_existing,verbose,quiet,logger,db,dry_run,rate_limit,max_retries):sc+=1
                else:fl.append(u)
        if not quiet:
            click.echo(f"\n{Fore.CYAN}{'='*60}\nBatch Summary\n{'='*60}{Style.RESET_ALL}")
            click.echo(f"Total: {len(urls)}")
            click.echo(f"{Fore.GREEN}[+]{Style.RESET_ALL} Success: {sc}")
            click.echo(f"{Fore.RED}[-]{Style.RESET_ALL} Failed: {len(fl)}")
            if fl:
                click.echo(f"\n{Fore.RED}Failed URLs:{Style.RESET_ALL}")
                for u in fl:click.echo(f"  - {u}")
        if archive and sc>0 and not dry_run:
            click.echo(f"\n{Fore.CYAN}[*]{Style.RESET_ALL} Creating archive...")
            ap=create_archive(Path(output_dir))
            if ap:click.echo(f"{Fore.GREEN}[+]{Style.RESET_ALL} Archive created: {ap}")
            else:click.echo(f"{Fore.RED}[-]{Style.RESET_ALL} Archive creation failed")
    except KeyboardInterrupt:click.echo(f"\n\n{Fore.YELLOW}[!]{Style.RESET_ALL} Cancelled");sys.exit(130)
    except Exception as e:click.echo(f"\n{Fore.RED}[-]{Style.RESET_ALL} Error: {e}",err=True);sys.exit(1)
if __name__=='__main__':main()
