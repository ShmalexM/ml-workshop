from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
app=Path.home()/'Applications/ML Workshop.app'
# Both paths are constants authored by us; shell quoting also supports spaces.
import shlex
command=shlex.join([str(ROOT/'.venv/bin/python'),str(ROOT/'scripts/launch.py')])
source='''on run
    try
        do shell script %s
    on error messageText
        display dialog messageText with title "ML Workshop" buttons {"OK"} default button "OK" with icon caution
    end try
end run
''' % ('"'+command.replace('\\','\\\\').replace('"','\\"')+'"')
script=ROOT/'scripts/launcher.applescript';script.write_text(source)
if app.exists():raise SystemExit('Launcher already exists; refusing to overwrite.')
app.parent.mkdir(exist_ok=True)
subprocess.run(['/usr/bin/osacompile','-o',str(app),str(script)],check=True)
icon=ROOT/'assets/Workshop.icns'
if icon.exists():
    import shutil
    shutil.copyfile(icon,app/'Contents/Resources/applet.icns')
    subprocess.run(['/usr/bin/codesign','--force','--sign','-',str(app)],check=True)
link=Path.home()/'Desktop/ML Workshop.app'
if not link.exists():link.symlink_to(app)
print(app)
