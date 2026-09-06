# TyDL _(tidal-dl)_
### A Hi-Res Lossless _(up to 24bit 192kHz)_ CLI Tidal downloader.

#### Automatically pull your Tidal token from preferred browser, refreshes token automatically when expired by opening tidal.com in that browser _(for more automated mass-downloading)_

#### Supports Windows, macOS, Linux

#### Dependencies: python (3.12+) installed, python modules: `mutagen requests`

#### Supported token pulling: Brave, Firefox (LibreWolf too), Edge, Chrome, Chromium

#### Logic from [tidarr](https://github.com/cstaelen/tidarr), was rewritten fully

# Setup
1. **Clone repo**:
```shell
git clone https://github.com/dev4ones-space/ty-dl.git && cd tidal-dl
```
2. **Install following dependencies**:
```text
mutagen requests
```


# Usage
```shell
python3 main.py -t {browser where tidal.com account} -l {album link} 
```

# Build 
```shell
python3 build.py
```
## Showcase of downloading
#### Downloading ""