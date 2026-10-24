"""Render a clip through a gitSynth JSFX using REAPER from the command line.

Writes a small REAPER project (one track: the clip, then the plugin), runs
REAPER headless to render it, and saves the result in results/render/.

The plugin is loaded from REAPER's Effects folder through the gitSynth-dev
link, which points at this project's jsfx folder, so the current code is
tested. REAPER must be closed: a second copy can fight the first over the
audio device, so the script refuses to run while REAPER is open.

Usage:
  python tools/render.py CLIP [--plugin gitSynth-part1.jsfx] [--out NAME]
                         [--set slider_name=value ...] [--channels 2]
Example:
  python tools/render.py clips/04-dynamics.wav --set mix=0 --out dry-check
"""
import argparse
import os
import re
import subprocess
import sys
import uuid

import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAPER = r"C:\Program Files\REAPER (x64)\reaper.exe"
EFFECTS_LINK = "gitSynth-dev"
WAV24_CFG = "ZXZhdxgAAQ=="   # REAPER render format: WAV, 24-bit


def reaper_running():
    """True if any process name or path mentions REAPER."""
    ps = ("Get-Process | Where-Object { $_.ProcessName -like '*reaper*' -or "
          "$_.Path -like '*REAPER*' } | Select-Object -ExpandProperty Id")
    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                         capture_output=True, text=True).stdout
    return bool(out.strip())


def slider_defaults(path):
    """Slider number -> (name, default), from the JSFX's slider lines."""
    found = {}
    pat = re.compile(r"^slider(\d+):(?:(\w+)=)?([-\d.]+)<")
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            m = pat.match(line)
            if m:
                found[int(m.group(1))] = (m.group(2), float(m.group(3)))
    return found


def build_rpp(clip, plugin, values, out_wav, channels, length):
    slider_line = " ".join(
        ("%g" % values[i]) if i in values else "-" for i in range(1, 65))
    return f"""<REAPER_PROJECT 0.1 "7.82/win64" 0
  SAMPLERATE 48000 1 0
  MASTER_NCH {channels} 2
  RENDER_FILE "{out_wav}"
  RENDER_PATTERN ""
  RENDER_FMT 0 {channels} 48000
  RENDER_1X 0
  RENDER_RANGE 1 0 0 18 1000
  RENDER_RESAMPLE 3 0 1
  RENDER_ADDTOPROJ 0
  RENDER_STEMS 0
  RENDER_DITHER 0
  <RENDER_CFG
    {WAV24_CFG}
  >
  <TRACK {{{uuid.uuid4()}}}
    NAME render
    NCHAN {channels}
    <FXCHAIN
      SHOW 0
      LASTSEL 0
      DOCKED 0
      BYPASS 0 0 0
      <JS "{EFFECTS_LINK}/{plugin}" ""
        {slider_line}
      >
      FLOATPOS 0 0 0 0
      FXID {{{uuid.uuid4()}}}
      WAK 0 0
    >
    <ITEM
      POSITION 0
      LENGTH {length:.6f}
      <SOURCE WAVE
        FILE "{clip}"
      >
    >
  >
>
"""


def render(clip, plugin="gitSynth-part1.jsfx", out=None, settings=None,
           channels=2, timeout=600):
    if reaper_running():
        sys.exit("REAPER is open; close it before rendering.")
    clip = os.path.abspath(clip)
    jsfx = os.path.join(ROOT, "jsfx", plugin)
    sliders = slider_defaults(jsfx)
    by_name = {name: num for num, (name, _) in sliders.items() if name}
    values = {num: default for num, (_, default) in sliders.items()}
    for key, val in (settings or {}).items():
        if key not in by_name:
            sys.exit(f"{plugin} has no slider named {key!r}")
        values[by_name[key]] = float(val)

    out = out or os.path.splitext(os.path.basename(clip))[0]
    out_dir = os.path.join(ROOT, "results", "render")
    os.makedirs(out_dir, exist_ok=True)
    out_wav = os.path.join(out_dir, out + ".wav")
    rpp = os.path.join(out_dir, out + ".rpp")
    if os.path.exists(out_wav):
        os.remove(out_wav)
    with open(rpp, "w", encoding="utf-8") as fh:
        fh.write(build_rpp(clip, plugin, values, out_wav, channels,
                           sf.info(clip).duration))
    # Start REAPER minimised and without taking focus, so a render does not
    # pull the screen reader away from what Rich is doing.
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 7    # SW_SHOWMINNOACTIVE
    subprocess.run([REAPER, "-newinst", "-nosplash", "-renderproject", rpp],
                   timeout=timeout, startupinfo=si)
    if not os.path.exists(out_wav):
        sys.exit(f"REAPER did not write {out_wav}")
    return out_wav


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clip")
    ap.add_argument("--plugin", default="gitSynth-part1.jsfx")
    ap.add_argument("--out")
    ap.add_argument("--set", nargs="*", default=[], metavar="NAME=VALUE")
    ap.add_argument("--channels", type=int, default=2)
    a = ap.parse_args()
    settings = dict(s.split("=", 1) for s in a.set)
    print(render(a.clip, a.plugin, a.out, settings, a.channels))


if __name__ == "__main__":
    main()
