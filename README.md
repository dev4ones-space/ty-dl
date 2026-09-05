# TyDL _(tidal-dl)_
### A Hi-Res Lossless _(up to 24bit 192kHz)_ CLI Tidal downloader.

#### Automatically pull your Tidal token from prefered browser _(because of that most of downloaders dont support more that `LOSSLESS` because ignored by Tidal API)_

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
python3 main.py -q {low/medium/high/max quality} -t {browser where tidal account is logged in} -l {album link}
```

# Build 
```shell
python3 build.py
```

# Example
#### Downloading album "The Life Of Pablo" _(https://tidal.com/album/57273408)_ & pulling token from Brave browser
```
python3 main.py -t brave -l https://tidal.com/album/57273408
==> Token pulled, valid till 03:49, country GB

==> [1/20] Ultralight Beam
    [########################] 59047/59047 b  seg 82/8282
==> [2/20] Father Stretch My Hands Pt. 1
    [########################] 12217/12217 b  seg 36/3636
==> [3/20] Pt. 2
    [########################] 176926/176926 b  seg 34/34
==> [4/20] Famous
    [########################] 15575/15575 b  seg 51/5151
==> [5/20] Feedback
    [########################] 282741/282741 b  seg 38/38
==> [6/20] Low Lights
    [########################] 260249/260249 b  seg 34/34
==> [7/20] Highlights
    [########################] 8871/8871 b  seg 52/521/52
==> [8/20] Freestyle 4
    [########################] 241091/241091 b  seg 32/32
==> [9/20] I Love Kanye
    [########################] 47512/47512 b  seg 13/1313
==> [10/20] Waves
    [########################] 131189/131189 b  seg 47/47
==> [11/20] FML
    [########################] 21626/21626 b  seg 61/6161
==> [12/20] Real Friends
    [########################] 238790/238790 b  seg 64/64
==> [13/20] Wolves
    [########################] 111404/111404 b  seg 77/77
==> [14/20] Frank's Track
    [########################] 120389/120389 b  seg 11/11
==> [15/20] Siiiiiiiiilver Surffffeeeeer Intermission
    [########################] 31407/31407 b  seg 16/1616
==> [16/20] 30 Hours
    [########################] 195488/195488 b  seg 82/82
==> [17/20] No More Parties In LA
    [########################] 233766/233766 b  seg 95/95
==> [18/20] Facts (Charlie Heat Version)
    [########################] 55793/55793 b  seg 52/5252
==> [19/20] Fade
    [########################] 88316/88316 b  seg 50/5050
==> [20/20] Saint Pablo
    [########################] 34484/34484 b  seg 95/9595
==> Album/s downloaded
```
