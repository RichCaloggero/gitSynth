# gitSynth: Test Clip Recording Checklist

These clips are used to tune and measure the pitch tracker offline. Record every clip exactly as listed, so that later measurements can compare each clip with the notes you were asked to play.

Expected time: 45 to 60 minutes.

## Setup (do this once)

- Guitar:
  - Tune to standard tuning at A = 440 Hz, and tune again partway through the session.
  - Use fresh or recently changed strings if possible.
  - Turn the guitar's volume and tone knobs fully up.
  - Choose the pickup you will normally use with the synth and keep it for every clip. If you change pickups, write it down (see "Notes file" below).
- Signal path:
  - Plug the guitar straight into the interface's instrument (Hi-Z) input.
  - Use no pedals, amp sim, compressor, noise gate, EQ or any other effect.
  - Put no input FX (record FX) on the REAPER track.
- REAPER and file format:
  - Project sample rate: 48 kHz.
  - Recording format: WAV, 24-bit.
  - One mono track recording input 1 (or whichever input the guitar is on).
- Level:
  - Set the interface gain so the hardest notes peak between about -12 and -6 dBFS.
  - Nothing may clip. If any clip goes into the red, record it again.
- Silence:
  - Leave about 2 seconds of silence at the start and end of every clip.
- Mistakes:
  - If you play a wrong note, record the whole clip again. Do not edit it.
- Metronome:
  - You can use REAPER's click for timing, but it must not end up in the recording.

## Naming and location

- Save every clip as a separate mono WAV in the `clips` folder inside the project folder.
- Use exactly the file names listed below.

## Clips

Fret numbers count up from the open string, with the open string as fret 0. String names run from low to high: low E, A, D, G, B, high E.

### 01-open-strings.wav
- Play each open string once, from low E to high E.
- Pick at medium strength and let each string ring for about 3 seconds.
- Mute each string with your hand, then wait about 1 second before playing the next one.

### 02a to 02f: chromatic, one file per string
- File names:
  - 02a-chromatic-lowE.wav
  - 02b-chromatic-A.wav
  - 02c-chromatic-D.wav
  - 02d-chromatic-G.wav
  - 02e-chromatic-B.wav
  - 02f-chromatic-highE.wav
- On that one string, play every fret from 0 to 12, one note at a time, going up.
- Pick each note once at medium strength and let it ring for about 1 second (60 BPM, one note per beat).
- Lift the finger, or mute, between notes so that the notes do not overlap.

### 03-high-register.wav
- On the B string, play frets 12 up to the highest fret, one note at a time, going up, at the same 60 BPM pace.
- Then do the same on the high E string, from fret 12 up to the highest fret.

### 04-dynamics.wav
- A string, fret 5 (the note D3): play 4 very soft notes, then 4 medium, then 4 as hard as you can. Let each note ring for about 1 second.
- High E string, fret 5 (the note A4): repeat the same pattern of 4 soft, 4 medium and 4 hard.

### 05-long-decay.wav
- Play each of these notes once at medium strength and let it ring until it is completely silent. Do not mute it.
  - Low E open.
  - A string, fret 7.
  - G string, fret 9.
  - High E string, fret 12.

### 06-mutes-and-staccato.wav
- D string, fret 7: play 4 notes. Let each ring about 1 second, then stop it by easing off the fretting finger.
- Same note: 4 more notes, each stopped with a palm mute after about 1 second.
- Same note: 8 short staccato notes at about 120 BPM.
- Repeat all three parts on the low E string, open.

### 07-bends.wav
- G string, fret 7:
  - Bend up a half step, hold for 1 second, release, and let the note ring for 1 second.
  - Then do the same with a whole step.
- B string, fret 8: half-step bend, then whole-step bend, the same way.
- High E string, fret 10: half-step bend, then whole-step bend, the same way.
- Finally, on the G string at fret 7, play one slow bend that takes about 2 seconds to reach a whole step, then release slowly.

### 08-vibrato.wav
- B string, fret 8: hold the note with slow, wide vibrato for about 3 seconds.
- B string, fret 8: hold the note with fast, narrow vibrato for about 3 seconds.
- G string, fret 9: repeat the slow vibrato and then the fast vibrato.
- Low E string, fret 5: slow vibrato for about 3 seconds.

### 09-legato.wav
- G string: pick fret 5 once, then trill between frets 5 and 7 with hammer-ons and pull-offs for about 3 seconds, without picking again.
- High E string: the same trill between frets 8 and 10.
- A string: pick fret 3, then slide up to fret 8 without picking again. Hold for 1 second, then slide back down to fret 3.
- D string: pick fret 2, then slide up to fret 7 the same way, and slide back down.

### 10a to 10c: scale runs
- File names:
  - 10a-scale-slow.wav at 80 BPM.
  - 10b-scale-medium.wav at 120 BPM.
  - 10c-scale-fast.wav at 160 BPM.
- Play the A minor pentatonic scale over two octaves in 5th position, starting on the low E string at fret 5.
- Go up and then back down, playing 8th notes (two notes per beat) with alternate picking.

### 11-melody.wav
- About 30 seconds of a melody you would actually want to play with a flute sound, played naturally and with expression.

### 12-same-note-different-strings.wav
- Play the note E4 four times, letting each ring for about 2 seconds:
  - High E string open.
  - B string, fret 5.
  - G string, fret 9.
  - D string, fret 14.

### 13-harmonics.wav
- Play natural harmonics on the low E string at fret 12, then fret 7, then fret 5. Let each ring for 2 seconds.
- Repeat on the G string.
- This clip tests whether the tracker gets the octave wrong.

### 14-noise-floor.wav
- About 10 seconds of silence with the guitar plugged in and its volume fully up.
- Rest your hand lightly on the strings so they do not ring.
- This clip is used to set the gate threshold.

### 15-chords.wav (optional)
- Strum E major, A major and G major, letting each ring for 2 seconds.
- This clip checks that the synth fails gracefully when given a chord, rather than making a mess.

## Notes file

Save a plain text file named `clips/notes.txt` containing:

- The guitar's make and model.
- The pickup and switch position used.
- The interface used.
- Any clip that departs from this checklist, and how it departs.

## Final checklist

- All files are mono 48 kHz 24-bit WAV.
- No clip clips, and the hardest notes peak around -12 to -6 dBFS.
- No effects anywhere in the signal path.
- About 2 seconds of silence at each end of every clip.
- File names match this list exactly.
- `notes.txt` is filled in.
