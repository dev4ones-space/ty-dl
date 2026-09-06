# #
import sys, time, ast, subprocess, requests, base64, json, re, os
from pathlib import Path; from xml.etree import ElementTree as ET; from wopw import *
class Main:
    # Variables
    # Classes
    class Configuration:
        EnableLogs = True # Default (recommended) - bool: True; Used to enable/disable logs globally (settings like LogsSettings will be ignored and treated as False)
        class LogsSettings:
            LogLevel = 2 # Default (recommended) - int: 2; 0: Errors only; 1: Errors & Warnings only; 2: All
            ColoredLogs = True # Default (recommended) - bool: True; When bool: False; activity Logs() will return logs unchanged
    class Version:
        ManageVersion = 2
        Version = 1.0
        SubVersion = 2
        SubComment = ''
        BuildType = 'Stable' # Could be: Unstable (a default release, but may contain major/small bugs), Stable, Alpha (early versions, mostly very unstable or contains unfinished parts)
        __build_type_show__ = {'Alpha': 'ALPH', 'Stable': 'STBL', 'Unstable': 'BETA'}[BuildType]
        BuildShow = f'{ManageVersion}{__build_type_show__}-{SubVersion}{SubComment}'
    class GlobalCache: Logs, LogsCount, Config, Token, Country, OnTrack, OnBytes, Browser, RefreshToken = '', 0, {}, '', '', None, None, None, None # OnTrack(i, total, title); OnBytes(seg, segs, written, expected) — set by interface for progress display
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
            if Main.Configuration.LogsSettings.ColoredLogs: return gc.Logs.replace('error   ', f'{color.fg.red}error{color.cls}    ').replace('warning   ', f'{color.fg.yellow}warning{color.cls}  ').replace('debug   ', f'{color.fg.blue}debug{color.cls}    ')
            return gc.Logs
        def io(filename: str, mode: str, content: str = None):
            with open(filename, mode) as file:
                if mode == 'r': return file.read()
                file.write(content)
                return None
        def ReadConfig(): gc.Config = ast.literal_eval(act.io('Config', 'r'))
        def QualityOppositeConv(Content: str = None):
            cache, cache1, cache2 = {cache: cache1 for cache1, cache in gc.Config['QualityFormats'].items()}, gc.Config['QualityFormats'], gc.Config['QualityFormats_CLI'] # api: ft; tf: api; cli: api
            cache.update(cache1); cache.update(cache2); return cache[Content] # merged dicts in all formats, return
        def API_Get(Path: str, Params: str = None, Token: str = None): # PermissionError (not valid tk)
            Path = '/' + Path.lstrip('/') # normalize: call sites pass both 'albums/x' and '/sessions'
            for attempt in range(2):
                conf = {'CN': gc.Country, 'TK': gc.Token} # to make sure future code will not require removing and recoding hardcoded paths
                cache = requests.get(f'{gc.Config['API_BaseURL']}{Path}', params={'countryCode': conf['CN'], **(Params or {})}, timeout=gc.Config['API_Timeout'], headers={'Authorization': f'Bearer {conf['TK']}'})
                if cache.status_code != 401:
                    cache.raise_for_status(); return cache.json()
                if attempt or not gc.RefreshToken: raise PermissionError('API had responded with 401, meaning recheck the token')
                auth = gc.RefreshToken(gc.Browser)
                if not auth or not auth.get('token'): raise PermissionError('Token refresh did not return a valid token')
                gc.Token, gc.Country = auth['token'], auth.get('country_code') or gc.Country
        def FetchAlbumData(AlbumID: str): return act.API_Get(f'albums/{AlbumID}') # very simple album fetcher shi
        def FetchAlbumTracksMetadata(AlbumID: str, AlbumData: dict): # very very strange thingy, mostly not my code in this act
            cache, cache1 = [], 0
            while True:
                cache2 = act.API_Get(f'albums/{AlbumID}/items', {'limit': 100, 'offset': cache1}) # page
                batch = cache2.get('items') or []
                for i in batch:
                    if str(i.get('type', 'track')).lower() == 'track' and i.get('item'): item = i['item']; item.setdefault('album', AlbumData); cache.append(item)
                cache1 += 100
                if cache1 >= cache2.get("totalNumberOfItems", 0) or not batch: return cache
        def TrackInfo(TrackID: str, QualityFT: str): return act.API_Get(f'tracks/{TrackID}/playbackinfopostpaywall', {'audioquality': act.QualityOppositeConv(QualityFT), 'playbackmode': 'STREAM', 'assetpresentation': 'FULL'}) # very basic shi, just fetching track data, from that we can see quality available for track (on service, so if token is limited it will download in `LOSSLESS` regardless params) & other refernces that are we gonna use for downloading
        def RouteToTrackManifest(TrackInfo: dict): # not my code, only adapted
            quality = TrackInfo.get("audioQuality", "UNKNOWN")
            manifest = base64.b64decode(TrackInfo["manifest"]).decode()  # blob -> text
            mime = TrackInfo.get("manifestMimeType", "")
            info = {"quality": quality}

            if mime == "application/dash+xml":
                # flavor B: xml; every find/findall needs the MPD namespace prefixed
                root = ET.fromstring(manifest)
                rep = root.find(f"{gc.Config['DashXML']}Period/{gc.Config['DashXML']}AdaptationSet/{gc.Config['DashXML']}Representation")
                if rep is None:
                    raise ValueError('RouteToTrackManifest: DASH manifest has no Representation')
                info["sample_rate"] = rep.get("audioSamplingRate")
                m = re.search(r",(\d+)$", rep.get("id", ""))  # "...,24" -> bit depth
                if m:
                    info["bit_depth"] = m.group(1)
                template = rep.find(f"{gc.Config['DashXML']}SegmentTemplate")
                if template is None or not template.get("media"):
                    raise ValueError('RouteToTrackManifest: DASH manifest has no SegmentTemplate')
                # segment count: every <S> is "duration d, repeated r more times" -> 1 + r
                count = sum(1 + int(s.get("r", "0"))
                            for s in template.findall(f"{gc.Config['DashXML']}SegmentTimeline/{gc.Config['DashXML']}S"))
                start = int(template.get("startNumber", "1"))
                urls = []
                if template.get("initialization"):  # mp4 header first, always
                    urls.append(template.get("initialization"))
                urls.extend(template.get("media").replace("$Number$", str(n))  # <- synthesized
                            for n in range(start, start + count))
                codecs = rep.get("codecs", "")
            else:
                # flavor A: plain json was hiding inside the base64
                body = json.loads(manifest)
                codecs = body.get("codecs", "")
                urls = body.get("urls", [])
                if body.get("sampleRate"):
                    info["sample_rate"] = str(body["sampleRate"])
                if body.get("bitDepth"):
                    info["bit_depth"] = str(body["bitDepth"])
            ext = ".flac" if codecs == "flac" else ".m4a"
            return urls, ext, info
        def FetchFrontCover(AlbumData: dict):
            cover = (AlbumData or {}).get("cover")
            if not cover: return None
            try:
                cache = requests.get(f"https://resources.tidal.com/images/{str(cover).replace('-', '/')}/1280x1280.jpg", timeout=30)
                if cache.status_code == 200 and cache.content[:2] == b'\xff\xd8': return cache.content
            except requests.RequestException: pass
            return None
        def DownloadHiRes(URLsList: list, OutPath: Path): # this activity has been heavily (+-80%) assisted by GLM5.3 xhigh
            OutPath.parent.mkdir(parents=True, exist_ok=True)
            cache = OutPath.with_name(OutPath.name + '.part')
            with open(cache, 'wb') as cache1:
                for u, url in enumerate(URLsList, 1):  # url[0] is the mp4 init segment for DASH, the file for bts
                    for attempt in range(4):  # retry transient cdn failures: 1s, 2s, 3s backoff
                        pos = cache1.tell()  # truncate on retry: a failed attempt may have written partial bytes
                        try:
                            with requests.get(url, stream=True, timeout=(15, 120)) as cache3:
                                cache3.raise_for_status()
                                expected = int(cache3.headers.get("Content-Length", 0))
                                written = 0
                                for chunk in cache3.iter_content(chunk_size=256 * 1024):
                                    cache1.write(chunk)
                                    written += len(chunk)
                                    if gc.OnBytes: gc.OnBytes(u, len(URLsList), written, expected)
                                if expected and written != expected:
                                    raise RuntimeError(f'DownloadHiRes: Truncated segment: {written}/{expected} b')
                            break
                        except Exception:
                            cache1.seek(pos); cache1.truncate()
                            if attempt == 3: raise
                            time.sleep(1 + attempt)
            os.replace(cache, OutPath)
        def FetchLyrics_APIbyTIDAL(TrackID: int): # tidal basically provides lyrics for song using many different lyrics providers, sadly has token auth unline album cover fetch
            try: return (act.API_Get(f'tracks/{TrackID}/lyrics') or {}).get('lyrics')
            except Exception: return None
        def TrackFilename(TrackMetadata: dict):
            unknown = gc.Config.get('Unsigned(TrackFilename)', 'Unknown'); album = TrackMetadata.get('album') or {}
            artist = act.SafeFilename(((album.get('artist') or TrackMetadata.get('artist') or {}).get('name')) or unknown)
            title = str(TrackMetadata.get('title') or unknown)
            version = TrackMetadata.get('version')
            if version and str(version).lower() not in title.lower(): title = f'{title} ({version})'
            return f'{artist}/{act.SafeFilename(album.get("title") or unknown)}/{TrackMetadata.get("trackNumber") or 0:02d} {act.SafeFilename(title)} - {artist}'
        def SafeFilename(Content: str, Fallback: str = 'Unknown'): return re.sub(r'\s+', ' ', ''.join(c if c not in '<>:"/\\|?*' and ord(c) >= 32 else '_' for c in str(Content or ''))).strip('. ')[:180] or Fallback
        def MP4_Boxes(data: bytes, start: int, end: int): # generator over ISOBMFF boxes: (type, payload_start, payload_len); handles size==0 (till end) & size==1 (largesize)
            while start + 8 <= end:
                size = int.from_bytes(data[start:start+4], 'big'); hdr = 8
                if size == 1: size, hdr = int.from_bytes(data[start+8:start+16], 'big'), 16
                elif size == 0: size = end - start
                if size < hdr or start + size > end: return # corrupt/unknown layout
                yield data[start+4:start+8], start+hdr, size-hdr
                start += size
        def MP4_TrunSizes(data: bytes, start: int, end: int): # sample sizes inside one moof: tfhd default + trun per-sample (dash flac = 1 track, frames packed in the mdat that follows)
            sizes, default_size = [], 0
            for typ, s, l in act.MP4_Boxes(data, start, end):
                if typ != b'traf': continue
                for typ1, s1, l1 in act.MP4_Boxes(data, s, s+l):
                    if typ1 == b'tfhd': # fullbox: version/flags(4) track_id(4), then optional fields by flag bit
                        flags = int.from_bytes(data[s1+1:s1+4], 'big'); p = s1+8
                        if flags & 0x01: p += 8 # base_data_offset
                        if flags & 0x02: p += 4 # default_sample_description_index
                        if flags & 0x08: p += 4 # default_sample_duration
                        if flags & 0x10: default_size = int.from_bytes(data[p:p+4], 'big') # default_sample_size
                    elif typ1 == b'trun': # fullbox: version/flags(4) sample_count(4), then optional fields, then per-sample entries
                        flags = int.from_bytes(data[s1+1:s1+4], 'big'); p = s1+8
                        count = int.from_bytes(data[s1+4:s1+8], 'big')
                        if flags & 0x01: p += 4 # data_offset
                        if flags & 0x04: p += 4 # first_sample_flags
                        for _ in range(count):
                            if flags & 0x100: p += 4 # sample_duration
                            if flags & 0x200: sizes.append(int.from_bytes(data[p:p+4], 'big')); p += 4 # sample_size
                            elif default_size: sizes.append(default_size)
                            else: raise ValueError('MP4_TrunSizes: sample size unknown (no trun sizes, no tfhd default)')
                            if flags & 0x400: p += 4 # sample_flags
                            if flags & 0x800: p += 4 # sample_composition_time_offset
                        if p > s1 + l1: raise ValueError('MP4_TrunSizes: trun parsing ran past the box')
            return sizes
        def MP4ToFlac(data: bytes) -> bytes: # fmp4 (init + fragments, exactly what DownloadHiRes saves) -> native flac stream; raises ValueError on unexpected layout (caller falls back to ffmpeg)
            limit = min([p for p in (data.find(b'moof'), data.find(b'mdat')) if p > 0] or [len(data)]) # dfLa lives in the init segment, before any fragment data
            i = data.find(b'dfLa', 0, limit) # flac-in-mp4: SampleEntry(fLaC) > dfLa box: fullbox(4) + flac block header(4) + STREAMINFO(34)
            if i < 0 or i + 46 > limit or data[i+8] & 0x7f or int.from_bytes(data[i+9:i+12]) != 34: raise ValueError('MP4ToFlac: no STREAMINFO in init segment')
            frames, pending = [], []
            for typ, s, l in act.MP4_Boxes(data, 0, len(data)):
                if typ == b'moof': pending = act.MP4_TrunSizes(data, s, s+l)
                elif typ == b'mdat' and pending: # samples are packed at mdat payload start, in trun order
                    p = s
                    for size in pending:
                        if p + size > s + l: raise ValueError('MP4ToFlac: mdat shorter than trun sample sizes')
                        frames.append(data[p:p+size]); p += size
                    pending = []
            if not frames: raise ValueError('MP4ToFlac: no samples in fragments')
            return b'fLaC' + b'\x80\x00\x00\x22' + data[i+12:i+46] + b''.join(frames)
        def RemuxToFlac(Path: Path):
            data = open(Path, 'rb').read()
            if data[:4] == b'fLaC': return False
            cache = Path.with_name(Path.stem + '.tmp' + Path.suffix) # suffix must stay .flac: ffmpeg guesses the output format from it
            try:
                open(cache, 'wb').write(act.MP4ToFlac(data)); os.replace(cache, Path); return True
            except Exception: pass
            try:
                r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(Path), '-c', 'copy', str(cache)], capture_output=True, timeout=900)
                if r.returncode == 0 and cache.stat().st_size > 0: os.replace(cache, Path); return True
            except Exception: pass
            cache.unlink(missing_ok=True); return False
        def FetchAdvancedCredits(AlbumID: str):
            try:
                cache = act.API_Get(f'albums/{AlbumID}/items/credits', {'limit': 100})
                return {(i.get('item') or {}).get('id'): i.get('credits') or [] for i in cache.get('items') or [] if i.get('item')}
            except Exception: return {}
        def EmbedTags(Path: Path, TrackMetadata: dict, AlbumData: dict, Cover: bytes = None, Lyrics: str = None, Credits: list = None):
            try:
                with open(Path, 'rb') as f: head = f.read(4)
                title = TrackMetadata.get('title', '?'); artist = (TrackMetadata.get('artist') or {}).get('name', '?')
                tno, dno = TrackMetadata.get('trackNumber') or 0, TrackMetadata.get('volumeNumber') or 1
                if head == b'fLaC':
                    from mutagen.flac import FLAC, Picture
                    f = FLAC(str(Path))
                    f['title'] = [title]; f['album'] = [AlbumData.get('title', '')]
                    f['artist'] = [a['name'] for a in TrackMetadata.get('artists', [])] or [artist]; f['albumartist'] = [artist]
                    f['tracknumber'] = [f'{tno}/{AlbumData.get("numberOfTracks", 0)}']; f['discnumber'] = [f'{dno}/{AlbumData.get("numberOfVolumes", 1)}']
                    if AlbumData.get('releaseDate'): f['date'] = [AlbumData['releaseDate']]
                    if TrackMetadata.get('isrc'): f['isrc'] = [TrackMetadata['isrc']]
                    if Lyrics: f['lyrics'] = [Lyrics]
                    for c in Credits or []: # credit type -> tag: Composer -> COMPOSER
                        key = re.sub(r'[^A-Z0-9_]', '', str(c.get('type', '')).upper()); names = list(dict.fromkeys(p.get('name') for p in c.get('contributors', []) if p.get('name')))
                        if key and names: f[key] = names
                    if Cover:
                        pic = Picture(); pic.type, pic.mime, pic.desc, pic.data = 3, 'image/jpeg', 'cover', Cover # type 3 = front cover
                        f.clear_pictures(); f.add_picture(pic)
                    f.save()
                else:
                    from mutagen.mp4 import MP4, MP4Cover
                    f = MP4(str(Path))
                    f['\xa9nam'] = [title]; f['\xa9alb'] = [AlbumData.get('title', '')]; f['\xa9ART'] = [artist]; f['aART'] = [artist]
                    f['trkn'] = [(tno, AlbumData.get('numberOfTracks', 0))]; f['disk'] = [(dno, AlbumData.get('numberOfVolumes', 1))]
                    if AlbumData.get('releaseDate'): f['\xa9day'] = [AlbumData['releaseDate']]
                    if TrackMetadata.get('isrc'): f['\xa9isr'] = [TrackMetadata['isrc']]
                    if Lyrics: f['\xa9lyr'] = [Lyrics]
                    for c in Credits or []: # mp4 has one slot for writers: Composer -> ©wrt
                        if str(c.get('type', '')).lower() == 'composer':
                            names = list(dict.fromkeys(p.get('name') for p in c.get('contributors', []) if p.get('name')))
                            if names: f['\xa9wrt'] = names
                    if Cover: f['covr'] = [MP4Cover(Cover, imageformat=MP4Cover.FORMAT_JPEG)]
                    f.save()
            except ImportError: act.Log('warning', 'mutagen module not found, not metadata tags will be applied')
        def DownloadTrack(TrackMetadata: dict, QualityFT: str, AlbumData: dict = None, Cover: bytes = None, CreditsMap: dict = None, OutputDir: str = None): # steps 3-8 for one track; ext appended (never with_suffix: titles may contain dots); OutputDir is the library root, full path is OutputDir/Artist/Album/track, defaults to Config['OutputDir'] (~>Music/TyDL Library)
            OutputDir = os.path.expanduser(OutputDir or gc.Config.get('OutputDir', '~/Music/TyDL Library'))
            AlbumData = AlbumData or TrackMetadata.get('album') or {}
            urls, ext, info = act.RouteToTrackManifest(act.TrackInfo(TrackMetadata['id'], QualityFT))
            OutPath = Path(OutputDir) / f'{act.TrackFilename(TrackMetadata)}{ext}'
            if OutPath.exists(): act.Log('debug', f'skip (exists): {OutPath}'); return OutPath
            act.Log('debug', f'{info["quality"]} — {len(urls)} url(s) -> {OutPath.name}')
            act.DownloadHiRes(urls, OutPath)
            if ext == '.flac' and act.RemuxToFlac(OutPath): act.Log('debug', f'remuxed to native flac: {OutPath.name}')
            act.EmbedTags(OutPath, TrackMetadata, AlbumData, Cover, act.FetchLyrics_APIbyTIDAL(TrackMetadata['id']), (CreditsMap or {}).get(TrackMetadata['id']))
            return OutPath
        def DownloadAlbumMaster(Content: list): # content: [album link/trackid, token, country, qualityFT, outputdir (optional, defaults to Config['OutputDir'])]; token/country only seed gc when unset — a mid-run refresh (401 -> gc.RefreshToken) stays for next calls, switching accounts mid-run = set gc.Token/gc.Country directly
            link = str(Content[0])
            if not gc.Token: gc.Token, gc.Country = Content[1], Content[2]
            QualityFT = Content[3] if len(Content) > 3 else list(gc.Config['QualityFormats'])[-1] # default: highest quality in config
            OutputDir = Content[4] if len(Content) > 4 else None
            cache = re.search(r'(album|track)/(\d+)', link)
            if not cache: raise ValueError(f'DownloadAlbumMaster: Album link not valid')
            if cache.group(1) == 'track': return [act.DownloadSingleTrack(cache.group(2), QualityFT, OutputDir)]
            return act.DownloadAlbum(act.FetchAlbumData(cache.group(2)), QualityFT, OutputDir)
        def DownloadAlbum(AlbumData: dict, QualityFT: str, OutputDir: str = None): # cover + credits are per album — fetch once, then loop tracks
            tracks, Cover, CreditsMap = act.FetchAlbumTracksMetadata(AlbumData['id'], AlbumData), act.FetchFrontCover(AlbumData), act.FetchAdvancedCredits(AlbumData['id']); cache = []
            for i, track in enumerate(tracks, 1):
                if gc.OnTrack: gc.OnTrack(i, len(tracks), track.get('title', '?'))
                act.Log('debug', f'[{i}/{len(tracks)}] {track.get('title', '?')}')
                cache.append(act.DownloadTrack(track, QualityFT, AlbumData, Cover, CreditsMap, OutputDir))
            return cache
        def DownloadSingleTrack(TrackID: str, QualityFT: str, OutputDir: str = None):
            track = act.API_Get(f'tracks/{TrackID}'); album = track.get('album') or {}
            if gc.OnTrack: gc.OnTrack(1, 1, track.get('title', '?'))
            return act.DownloadTrack(track, QualityFT, album, act.FetchFrontCover(album), act.FetchAdvancedCredits(album.get('id')), OutputDir)
# Init
gc = Main.GlobalCache
act = Main.Activities
progress = lambda text: print(f'{color.fg.blue}==>{color.cls} {font.bold}{text}{font.cls}')
err, warn = f'{color.fg.red}error:{color.cls}', f'{color.fg.yellow}warning:{color.cls}'
gc.Logs = f'TyDL Downloader {Main.Version.Version} {Main.Version.SubVersion} ({Main.Version.BuildShow})'; act.ReadConfig()
# Main