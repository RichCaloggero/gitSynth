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


def run_hidden(args, timeout):
    """Run a program on a separate, invisible Windows desktop and wait.

    REAPER ignores requests to start minimised, so its window would come to
    the front and take the screen reader's focus. A program started on
    another desktop cannot show anything on Rich's desktop. If it has not
    finished within `timeout` seconds it is ended.
    """
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    class STARTUPINFOW(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR),
                    ("lpDesktop", wintypes.LPWSTR), ("lpTitle", wintypes.LPWSTR),
                    ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD),
                    ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD),
                    ("dwXCountChars", wintypes.DWORD), ("dwYCountChars", wintypes.DWORD),
                    ("dwFillAttribute", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                    ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD),
                    ("lpReserved2", ctypes.c_void_p), ("hStdInput", wintypes.HANDLE),
                    ("hStdOutput", wintypes.HANDLE), ("hStdError", wintypes.HANDLE)]

    class PROCESS_INFORMATION(ctypes.Structure):
        _fields_ = [("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE),
                    ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD)]

    user32.CreateDesktopW.restype = wintypes.HANDLE
    desk_name = "gitsynth-render"
    desk = user32.CreateDesktopW(desk_name, None, None, 0, 0x10000000, None)  # GENERIC_ALL
    if not desk:
        raise OSError(ctypes.get_last_error(), "could not create the hidden desktop")
    try:
        si = STARTUPINFOW()
        si.cb = ctypes.sizeof(si)
        si.lpDesktop = desk_name
        pi = PROCESS_INFORMATION()
        cmd = subprocess.list2cmdline(args)
        if not kernel32.CreateProcessW(None, ctypes.create_unicode_buffer(cmd), None, None,
                                       False, 0, None, None, ctypes.byref(si), ctypes.byref(pi)):
            raise OSError(ctypes.get_last_error(), "could not start " + args[0])
        try:
            if kernel32.WaitForSingleObject(pi.hProcess, int(timeout * 1000)) != 0:
                kernel32.TerminateProcess(pi.hProcess, 1)
                raise TimeoutError(f"{args[0]} did not finish within {timeout} s; ended it")
        finally:
            kernel32.CloseHandle(pi.hThread)
            kernel32.CloseHandle(pi.hProcess)
    finally:
        user32.CloseDesktop(desk)


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


def slider_values(plugin, settings):
    """All slider values for a plugin: its defaults, then the settings given."""
    sliders = slider_defaults(os.path.join(ROOT, "jsfx", plugin))
    by_name = {name: num for num, (name, _) in sliders.items() if name}
    values = {num: default for num, (_, default) in sliders.items()}
    for key, val in (settings or {}).items():
        if key not in by_name:
            sys.exit(f"{plugin} has no slider named {key!r}")
        values[by_name[key]] = float(val)
    return values


def track_rpp(name, clip, plugin, values, channels):
    slider_line = " ".join(
        ("%g" % values[i]) if i in values else "-" for i in range(1, 65))
    return f"""  <TRACK {{{uuid.uuid4()}}}
    NAME "{name}"
    SEL 1
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
      LENGTH {sf.info(clip).duration:.6f}
      <SOURCE WAVE
        FILE "{clip}"
      >
    >
  >
"""


def project_rpp(tracks, render_file, pattern, stems, channels):
    """stems 0: render the master mix to render_file; 1: render each
    (selected) track to render_file/pattern, pattern "$track" = track name."""
    return f"""<REAPER_PROJECT 0.1 "7.82/win64" 0
  SAMPLERATE 48000 1 0
  MASTER_NCH {channels} 2
  RENDER_FILE "{render_file}"
  RENDER_PATTERN "{pattern}"
  RENDER_FMT 0 {channels} 48000
  RENDER_1X 0
  RENDER_RANGE 1 0 0 18 1000
  RENDER_RESAMPLE 3 0 1
  RENDER_ADDTOPROJ 0
  RENDER_STEMS {stems}
  RENDER_DITHER 0
  <RENDER_CFG
    {WAV24_CFG}
  >
{"".join(tracks)}>
"""


def out_dir():
    d = os.path.join(ROOT, "results", "render")
    os.makedirs(d, exist_ok=True)
    return d


def render(clip, plugin="gitSynth-part1.jsfx", out=None, settings=None,
           channels=2, timeout=600):
    """Render one clip; returns the WAV path."""
    if reaper_running():
        sys.exit("REAPER is open; close it before rendering.")
    clip = os.path.abspath(clip)
    out = out or os.path.splitext(os.path.basename(clip))[0]
    out_wav = os.path.join(out_dir(), out + ".wav")
    rpp = os.path.join(out_dir(), out + ".rpp")
    if os.path.exists(out_wav):
        os.remove(out_wav)
    track = track_rpp("render", clip, plugin, slider_values(plugin, settings), channels)
    with open(rpp, "w", encoding="utf-8") as fh:
        fh.write(project_rpp([track], out_wav, "", 0, channels))
    run_hidden([REAPER, "-newinst", "-nosplash", "-renderproject", rpp], timeout)
    if not os.path.exists(out_wav):
        sys.exit(f"REAPER did not write {out_wav}")
    return out_wav


def render_batch(jobs, batch_name, channels=2, timeout=1200):
    """Render several clips in one REAPER run, one track each, as stems.

    jobs: list of (clip, plugin, settings, out_name). Returns the WAV paths,
    in the same order. Rendering together means REAPER starts only once.
    """
    if reaper_running():
        sys.exit("REAPER is open; close it before rendering.")
    tracks, wavs = [], []
    for clip, plugin, settings, name in jobs:
        tracks.append(track_rpp(name, os.path.abspath(clip), plugin,
                                slider_values(plugin, settings), channels))
        wav = os.path.join(out_dir(), name + ".wav")
        if os.path.exists(wav):
            os.remove(wav)
        wavs.append(wav)
    rpp = os.path.join(out_dir(), batch_name + ".rpp")
    with open(rpp, "w", encoding="utf-8") as fh:
        fh.write(project_rpp(tracks, out_dir(), "$track", 1, channels))
    run_hidden([REAPER, "-newinst", "-nosplash", "-renderproject", rpp], timeout)
    master = os.path.join(out_dir(), "Master.wav")   # REAPER adds a full mix too
    if os.path.exists(master):
        os.remove(master)
    missing = [w for w in wavs if not os.path.exists(w)]
    if missing:
        sys.exit("REAPER did not write: " + ", ".join(missing))
    return wavs


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
