# # For Python embedding, use dl-lib.py - this is somewhat interface to interact with user
import sys, time, importlib, requests, os, re, json, glob, base64, ast, shutil, subprocess
from wopw import *; DL_Lib = importlib.import_module('dl-lib') # to import dl module with `-` in name; equivalent to/is import
class TidalKError(Exception): pass
class Main:
    # Variables
    # Classes
    class Configuration:
        EnableLogs = True # Default (recommended) - bool: True; Used to enable/disable logs globally (settings like LogsSettings will be ignored and treated as False)
        DefaultQuality = 'Hi-Res (Lossless 24-bit)' # Default (recommended) - str: 'Hi-Res (Lossless 24-bit)'; Quality that content is gonna be downloaded if not specified (use -q low/medium/high/max or just read the README already)
        class LogsSettings:
            LogLevel = 2 # Default (recommended) - int: 2; 0: Errors only; 1: Errors & Warnings only; 2: All
            ColoredLogs = True # Default (recommended) - bool: True; When bool: False; activity Logs() will return logs unchanged
    class Version:
        ManageVersion = 3
        Version = 1.0
        SubVersion = 1
        SubComment = ''
        BuildType = 'Stable' # Could be: Unstable (a default release, but may contain major/small bugs), Stable, Alpha (early versions, mostly very unstable or contains unfinished parts)
        __build_type_show__ = {'Alpha': 'ALPH', 'Stable': 'STBL', 'Unstable': 'BETA'}[BuildType]
        BuildShow = f'{ManageVersion}{__build_type_show__}-{SubVersion}{SubComment}'
    class GlobalCache: Logs, LogsCount, Config = '', 0, {}
    class Activities:
        @staticmethod
        def Log(level: str, content: str):
            if Main.Configuration.EnableLogs:
                if level not in [['error'], ['warning', 'error'], ['debug', 'warning', 'error']][Main.Configuration.LogsSettings.LogLevel]: return None
                cache = f'{time.localtime().tm_year} {(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][time.localtime().tm_mon-1])} {time.localtime().tm_mday} {time.localtime().tm_hour}:{time.localtime().tm_min}:{time.localtime().tm_sec}'
                gc.LogsCount += 1; gc.Logs += f'\n{gc.LogsCount}  {cache}  {level}   {content}'
            return None
        @staticmethod
        def Logs():
            'Returns a colored logs. If in preferences ColoredLogs are set to False, gc.Logs (raw logs) will be returned'
            if Main.Configuration.LogsSettings.ColoredLogs: return gc.Logs.replace('error   ', f'{color.fg.red}error{color.cls}    ').replace('warning   ', f'{color.fg.yellow}warning{color.cls}  ').replace('debug   ', f'{color.fg.blue}debug{color.cls}    ')
            return gc.Logs
        def io(filename: str, mode: str, content: str | None = None):
            with open(filename, mode) as file:
                if mode == 'r': return file.read()
                file.write(content)
                return None
        def FetchArguments():
            cache, cache2 = sys.argv, {}
            for cache1 in range(len(cache) - 1):
                if cache[cache1].startswith('-'):
                    key = cache[cache1].lstrip('-')
                    if key == 'l': cache2.setdefault(key, []).append(cache[cache1+1])
                    else: cache2[key] = cache[cache1+1]
            return cache2
        def DownloadLinks(Links: list, Token: str, Country: str, Quality: str, OutputDir: str = None):
            for link in Links: DL_Lib.act.DownloadAlbumMaster([link, Token, Country, Quality, OutputDir]) # token seeds gc on first link only, mid-run refreshes stay in gc
        def ArgExists(Content, args):
            try: return args[Content]
            except: return False
        def ArgBool(Content, args):
            try: return args[Content].strip().lower() in ('true', '1', 'yes')
            except: return False
        def PullToken(http: requests.Session, browser: str) -> dict: # pulls token out of: brave, chrome, firefox (& librewolf), edge, chromium (not forked)
            def jwt_exp(token):
                try: part = token.split('.')[1]; return int(json.loads(base64.urlsafe_b64decode(part + '=' * (-len(part) % 4))).get('exp', 0))
                except: return 0
            engine, paths = gc.Config['BrowserRoots'].get(browser, (None, None))
            if engine is None: raise TidalKError(f'Browser is not supported for automatic token pulling, read README for supported or enter token manually into auth.json in repo root')
            candidates = set()
            root = os.path.expanduser(os.path.expandvars(paths[1] if os.name == 'nt' else paths[0] if sys.platform == 'darwin' else paths[2]))
            if os.path.isdir(root):
                for pattern in gc.Config['ScanPatterns'][engine]:
                    for f in glob.glob(f'{root}/{pattern}'):
                        try:
                            for m in re.finditer(gc.Config['TokenRegex'].encode(), open(f, 'rb').read()):
                                try: candidates.add(m.group(1).decode('ascii'))
                                except UnicodeDecodeError: pass
                        except OSError: continue
            candidates = sorted(candidates, key=jwt_exp, reverse=True)
            if not candidates: raise TidalKError(f'No token found, log in to continue (free API is not available)')
            stale = None
            for token in candidates:
                try: r = http.get(f'{gc.Config['API_BaseURL']}/sessions', headers={'Authorization': f'Bearer {token}'}, timeout=15); body = r.json() if r.status_code == 200 else None
                except: body = None
                if not body or not body.get('userId') or 'automotive' in str(body.get('client', {}).get('name', '')).lower(): continue
                if (exp := jwt_exp(token)) < time.time() + 60: stale = (token, exp, body); continue
                country = body.get('countryCode', 'US')
                act.io(AuthFile, 'w', json.dumps({'token': token, 'expires_at': exp, 'country_code': country, 'user_id': body.get('userId')}))
                try: os.chmod(AuthFile, 0o600)
                except OSError: pass
                return {'token': token, 'expires_at': exp, 'country_code': country}
            if stale: raise TidalKError(f'Token invalid (browser pulled token is expired), try reopenning the page: https://tidal.com')
            raise TidalKError(f'Token invalid, try relogging into your account: https://tidal.com')
        def OpenBrowser(browser: str, URL: str = 'https://tidal.com'):
            browser = str(browser or '').lower()
            apps = {'brave': 'Brave Browser', 'chrome': 'Google Chrome', 'librewolf': 'LibreWolf', 'edge': 'Microsoft Edge', 'chromium': 'Chromium', 'firefox': 'Firefox'}
            commands = {
                'brave': ('brave-browser', 'brave'), 'chrome': ('google-chrome', 'google-chrome-stable', 'chrome'),
                'librewolf': ('librewolf',), 'edge': ('microsoft-edge', 'microsoft-edge-stable', 'msedge'),
                'chromium': ('chromium', 'chromium-browser'), 'firefox': ('firefox',)
            }
            winpaths = { # windows browsers are not on PATH, standard install dirs instead (%VAR% expanded via os.path.expandvars)
                'brave': (r'%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe', r'%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe'),
                'chrome': (r'%ProgramFiles%\Google\Chrome\Application\chrome.exe', r'%ProgramFiles(X86)%\Google\Chrome\Application\chrome.exe'),
                'librewolf': (r'%ProgramFiles%\LibreWolf\librewolf.exe', r'%LOCALAPPDATA%\LibreWolf\librewolf.exe'),
                'edge': (r'%ProgramFiles(X86)%\Microsoft\Edge\Application\msedge.exe', r'%ProgramFiles%\Microsoft\Edge\Application\msedge.exe'),
                'chromium': (r'%LOCALAPPDATA%\Chromium\Application\chrome.exe',), 'firefox': (r'%ProgramFiles%\Mozilla Firefox\firefox.exe',)
            }
            if browser not in apps: raise TidalKError(f'Browser is not supported: {browser or "unknown"}')
            try:
                if sys.platform == 'darwin':
                    subprocess.run(['open', '-a', apps[browser], URL], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return None
                executable = next((shutil.which(i) for i in commands[browser] if shutil.which(i)), None) # PATH first (typical linux)
                if executable is None and os.name == 'nt': executable = next((i for i in map(os.path.expandvars, winpaths[browser]) if os.path.isfile(i)), None)
                if not executable: raise TidalKError(f'Browser is not installed or cannot be launched: {browser}')
                subprocess.Popen([executable, URL], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return None
            except (OSError, subprocess.SubprocessError) as e: raise TidalKError(f'Could not open browser {browser}: {e}')
        def RefreshToken(browser: str):
            browser = str(browser or '').lower()
            act.OpenBrowser(browser)
            try: input(f'Browser opened in {browser}. Refresh or log in to Tidal, then press Enter to continue: ')
            except EOFError: raise TidalKError('Token refresh cancelled')
            return act.PullToken(requests.Session(), browser)
        def SelectQuality():
            try:
                print(f'{font.bold}Select the audio quality for downloading:{font.cls}\n')
                for i, (cache, cache1) in enumerate(gc.Config['QualityFormats'].items()): print(f'{i}: {font.bold}{cache}{font.cls} {font.italic}({cache1}){font.cls}')
                cache = int(input('\nSelect: '))
                for i, (cache1, cache2) in enumerate(gc.Config['QualityFormats'].items()):
                    if cache == i: gc.Args['q'] = cache2; return
            except ValueError: pass # catch if input gets non-int and just use def quality
            print(f'{err} no valid quality format was selected, defaulted to {font.bold}"{Main.Configuration.DefaultQuality}"{font.cls}'); gc.Args['q'] = Main.Configuration.DefaultQuality
        # Init
gc = Main.GlobalCache
act = Main.Activities
gc.Config = ast.literal_eval(act.io('Config', 'r'))
AuthFile = f'{os.path.dirname(os.path.abspath(__file__))}/{gc.Config['AuthFile']}'
progress = lambda text: print(f'{color.fg.blue}==>{color.cls} {font.bold}{text}{font.cls}')
err = f'{color.fg.red}error:{color.cls}'
warn = f'{color.fg.yellow}warning:{color.cls}'
gc.Logs, gc.Args = f'TyDL Interaction Interface {Main.Version.Version} {Main.Version.SubVersion} ({Main.Version.BuildShow})', act.FetchArguments()
# Main
if gc.Args == {} or not all(i in list(gc.Args.keys()) for i in ['t', 'l']): print(f'{font.bold}{color.fg.red}Wrong usage!{color.cls}\n\n{font.bold}{sys.argv[0]} -t [browser with logged in tidal.com] -l [album or track link] -q [low/medium/high/max] -o [output dir (default: ~/Music/TyDL Library)]{font.cls} ...\n\nTyDL (Interaction Interface) {Main.Version.Version} {font.italic}({Main.Version.BuildShow}){font.cls}'); exit()
try: gc.Args['q']
except KeyError: gc.Args['q'] = Main.Configuration.DefaultQuality # very lazy but working adapter to set def quality if not included by user
Bar = lambda now, total, width=24: '#' * min(width, int(width * now / max(total, 1)))
try: DL_Lib.act.QualityOppositeConv(gc.Args['q']) # convert quality (dl-lib QualityOppositeConv activity)
except: print(f'{err}: Quality was specified but doesnt match anything in static config'); act.SelectQuality()
DL_Lib.gc.OnTrack = lambda i, n, title: (print(), progress(f'[{i}/{n}] {title}'))
DL_Lib.gc.OnBytes = lambda seg, segs, written, expected: print(f'\r    [{color.fg.cyan}{Bar(written, expected or 1):<24}{color.cls}] {written}/{expected or "?"} b  seg {seg}/{segs}', end='', flush=True)
try:
    try: auth = json.loads(act.io(AuthFile, 'r'))
    except: auth = {}
    if not auth.get('token') or auth.get('expires_at', 0) < time.time() + 60: print(f'{warn} token is invalid, pulling new'); auth = act.PullToken(requests.Session(), gc.Args['t'])
    progress(f'Token pulled, valid till {time.strftime('%H:%M', time.localtime(auth['expires_at']))}, country {auth['country_code']}')
    DL_Lib.gc.Browser, DL_Lib.gc.RefreshToken = gc.Args['t'], act.RefreshToken
    act.DownloadLinks(gc.Args['l'], auth['token'], auth['country_code'], gc.Args['q'], gc.Args.get('o'))
    print(); progress('Album/s downloaded')
except (TidalKError, PermissionError) as e: print(f'{err} {e}'); exit(1)
# TidalK is a scraped project, basically evolved into this, still has some old refs, gonna fix in 1.1+ of Version prob