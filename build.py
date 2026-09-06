# Automatic builder for TyDL
import subprocess, shutil, os
from wopw import *
def Shell(ShellExec): return subprocess.run(ShellExec, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout
progress = lambda text: print(f'{color.fg.blue}==>{color.cls} {font.bold}{text}{font.cls}')
progress('Building TyDL')
cache = Shell(['pyinstaller', '--onefile', 'main.py', '--add-data', 'dl-lib.py:.', '--add-data', 'Config:.'] + sum([['--hidden-import', i] for i in ['xml.etree.ElementTree', 'mutagen.flac', 'mutagen.mp4']], [])).strip().split('INFO: Build complete! The results are available in: ')[::-1][0] # dl-lib.py is a data file, so its imports are invisible to pyinstaller's static analysis - must be declared as hidden imports
progress('Build complete, cleaning up')
shutil.move(f'{cache}/main', 'TyDL')
shutil.rmtree('dist', ignore_errors=True); shutil.rmtree('build', ignore_errors=True); os.remove('main.spec')
print(f'{font.bold}{color.fg.green}Build complete, result: ./TyDL{color.cls}')
