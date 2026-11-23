# t_31cfb2ff / video-1

## Prompt as dispatched

````
---
factory:
  function: video_production
  base: HEAD
  inputs:
    - artifacts/t_e687db28/video-2
    - artifacts/t_dbf6286a/video-2
    - artifacts/t_61fa2737/video-3
    - artifacts/t_3735e1d8/video-3
---

# [voc12 demo] ASSEMBLY — intro/outro + segments A–D into the final video (card t_31cfb2ff, window video-1)

Role: assemble the final ~2-minute demo video for the operator. Use the hyperframes skill. All inputs are
artifact MP4s mounted read-only under `/inputs/artifacts/<card>/<window>/` — there is no staging access.

## Card snapshot

Title: [voc12 demo] ASSEMBLY — intro/outro + A-D into final video, then operator review

Card body (abridged; full body on the Kanban card):
- `factory: {function: video_production, base: HEAD}` (D project pulled from the sibling local branch — see below)
- Tasks: (1) HyperFrames intro 10 s: title "airflow-ml" + confirmed value statement, 16:9 1080p30;
  (2) HyperFrames outro 10 s: value statement + confirmed CTA + attribution "Dataset: PASCAL VOC 2012 (Flickr)";
  (3) concatenate intro → A → B → C → D → outro (no re-encoding of segment content; conform to one codec profile);
  (4) audio: VO mix from the v2 lines per shot + music bed under intro/outro only; captions preserved;
  (5) final MP4: 1920x1080 @ 30 fps H.264, total 2:00–2:15, ≤ 50 MB.
- Acceptance: single file; segment order intro/A/B/C/D/outro; every on-screen number already verified upstream
  against observed.json (do not introduce new numbers); no full-screen VOC images; attribution present in the
  outro. The operator reviews the final video on the card (approve / send back / re-cut).

## Operator final copy (verbatim — the unblock comment on t_31cfb2ff, 2026-11-23 21:29; this is the FINAL copy)

1. Intro value statement: **"From raw dataset to duplicate-checked, split-ready data — one platform."**
   (V1 reworded: this run reports near-duplicates but does not remove them, so "deduplicated" over-promises.)
2. Outro CTA: **C1 "Bring your dataset — leave with split-ready train/val/test."**
   Attribution line (fixed): **"Dataset: PASCAL VOC 2012 (Flickr)"**.
3. Sound bed: confirmed — VO (v2 lines per shot) + light music under intro/outro only; segments A–D stay
   silent with on-screen captions (no diegetic sound, no music under A–D).
4. CF-1: **soften both.** D1 VO: **"Near-duplicates are flagged, and every split stays cluster-aware."**
   D2 caption: **"near-dup-checked, cluster-aware splits"**.
5. C3 VO: re-word to **"The near-duplicate table, straight from the report."**

Disclosed adaptation (operator, apply consistently): the operator's V1 reword rationale applies to the v2
intro/outro VO lines too — the v2 storyboard's CF-1 flag states CF-1 applies to "deduplicated" in the I1 line.
So in VO lines I1 and O1, read "deduplicated" as "duplicate-checked" (see VO table below). Everything else in
the v2 VO lines is verbatim.

## Inputs (mounted read-only; verify sha256 of each before use; copy into the project tree where needed)

| Clip | Path | Size (B) | sha256 | Spec |
|------|------|----------|--------|------|
| A (approved, stream-copy) | /inputs/artifacts/t_e687db28/video-2/video/segment-a/renders/segment-a.mp4 | 2,570,887 | dfddde5d453822e48e2aaa28f6e5d94c119cf7468a94b8c14f1e9ed9b2648db4 | h264 High 1920×1080 yuv420p 30/1, 750 fr, 25.000 s, silent |
| B (approved, stream-copy) | /inputs/artifacts/t_dbf6286a/video-2/video/segment-b/renders/segment-b.mp4 | 2,275,189 | bff3008c40adcd14db6b9714fd981872261b3ff7928e8e336340daa5b05a1f25 | h264 High 1920×1080 30/1, 902 fr, 30.066667 s, silent |
| C (approved, stream-copy) | /inputs/artifacts/t_61fa2737/video-3/video/segment-c/renders/segment-c.mp4 | 1,860,410 | 0bf35a0b9aeb9a60d90483ee143a75f2ca55c4bcd1499edc444d1577d310ad83 | h264 High 1920×1080 yuv420p 30/1, 831 fr, 27.70 s, silent |
| D (approved render — DIFF REFERENCE ONLY, superseded by the re-render below) | /inputs/artifacts/t_3735e1d8/video-3/video/segment-d/renders/segment-d.mp4 | 1,227,770 | aefe3362aa866fcab07df70025858733c1556a2adcca20d4bbbf44ba84bea2ab | h264 High 1920×1080 yuv420p 30/1, 692 fr, 23.066667 s, silent |
| D base capture clip (input to the D re-render) | /inputs/artifacts/t_3735e1d8/video-3/video/segment-d/assets/capture-5.mp4 | 738,724 | 05e5671544fbbc6c55f214dc7bdd58ee0296519c54b11f1e866f7da539350955 | QA-approved capture-5 base |

## How to get the segment-D project (base is HEAD)

The tree at base HEAD does not contain segment D's HyperFrames project (it was composed on the unmerged
sibling branch `factory/t_3735e1d8/video-3`). That branch exists in this repo: extract the project from it,
read-only, into your working tree:

    git archive factory/t_3735e1d8/video-3 video/segment-d | tar -x

This materializes `video/segment-d/` (project sources + SOURCE.md; renders/assets are git-ignored there and
arrive via the /inputs mount). Do not modify or commit to that branch. Fallback if the branch is not visible
in the in-sandbox repo: do NOT invent a D project — continue assembly with the approved D render from /inputs
(as-is, D2 caption still "split-safe"), and flag it prominently in your final message.

## Tasks (in order)

### 1. Re-render segment D with the softened D2 caption (only change allowed)
- First extract the D project as described above (`git archive factory/t_3735e1d8/video-3 video/segment-d |
  tar -x`). Then, in `video/segment-d/`: place the D base clip from /inputs into the project's assets (per
  SOURCE.md), verify sha256 == 05e5671544fbbc6c55f214dc7bdd58ee0296519c54b11f1e866f7da539350955.
- Edit the D2 caption line: replace the text `split-safe` so line 2 reads exactly
  `1000 images, near-dup-checked, cluster-aware splits`. Keep the wording exact. Keep the existing caption-bar
  geometry (bar ≈ x580–1339, y884–991, line-2 font 28 px): if the softened line does not fit at 28 px, reduce
  the line's font size minimally (not below 24 px) or tighten tracking — do not move the bar, do not wrap to a
  new bar line, and do not change any other overlay.
- `npx hyperframes check`, snapshot review (verify by your own frame/snapshot inspection that the D2 caption
  shows the new line and everything else is unchanged), then
  `npx hyperframes render --quality delivery -o video/segment-d/renders/segment-d.mp4`
  (same profile as before: h264 High 1080p30 yuv420p, silent, 692 frames).
- Verify the re-render against the approved /inputs D render: frame count 692; per-frame pixel diff must be
  ZERO outside the D2 caption-bar zone (local time ≥ 12.5 s) and, inside that zone, confined to the caption
  bar. Report the diff scope in your final message.

### 2. Build the HyperFrames intro and outro (10 s each, exactly 300 frames each @ 30 fps)
- `video/final/intro/` (I1): title card `airflow-ml` (large) + value statement
  "From raw dataset to duplicate-checked, split-ready data — one platform."
- `video/final/outro/` (O1): value statement + CTA "Bring your dataset — leave with split-ready train/val/test."
  + attribution line "Dataset: PASCAL VOC 2012 (Flickr)" (small, legible).
- Design: dark theme consistent with the segments' dark Airflow UI; clean typography; subtle motion OK;
  all text fully inside the frame; 1920×1080 16:9. No VOC images, no new numbers (the attribution's "2012"
  is the fixed dataset name), no training/eval content.
- For each: `npx hyperframes check` + snapshot review (verify every line of copy is present, legible,
  untruncated), then `npx hyperframes render --quality delivery -o <folder>/renders/<name>.mp4`
  (names: `intro.mp4`, `outro.mp4`).

### 3. Concatenate (no re-encoding of approved segment content)
- Conform intro/outro to the segments' profile (h264 High, yuv420p, 30/1, 1920×1080, 1:1 SAR): if a HyperFrames
  render already matches, stream-copy it; otherwise re-encode intro/outro only to the matching profile.
- Concatenate, in order: intro → A → B → C → D (the NEW re-render from task 1) → outro, via the ffmpeg concat
  demuxer with `-c copy` (verify identical codec parameters first; the D re-render must match the profile of
  the other D render — if not, conform the new D render, not A/B/C).
- Result: one silent 1080p30 master ≈ 125.83 s (10 + 25.000 + 30.066667 + 27.70 + 23.066667 + 10).

### 4. Audio: VO mix + music bed under intro/outro only
- Synthesize VO (TTS; neutral, professional English voice; one WAV per line) for exactly the lines in the
  table below — verbatim, no re-wording. If the sandbox has no TTS capability, do NOT fake a voice: deliver
  with the music bed only and state it explicitly in your final message with the exact lines that were not voiced.
- Music: one light, soft, instrumental (no lyrics) bed, mixed quiet under the VO; present ONLY during
  0–10 s (intro) and the final 10 s (outro, 115.833–125.833 s); no music anywhere under A–D.
- Build one full-length audio track (VO placed at the global start times below; music at the two windows) and
  mux it onto the silent master with AAC (48 kHz, ~160–192 k) and `-c:v copy` →
  **`video/final/renders/voc12_demo_final.mp4`**.

#### VO lines and placement (v2 storyboard VO, operator overrides applied; times are GLOBAL seconds in the final video)

| # | Line (verbatim) | Global start |
|---|-----------------|--------------|
| I1 | Meet airflow-ml. In the next two minutes: one raw dataset in — duplicate-checked, split-ready data out, on one platform. | 0.4 |
| A1 | One trigger starts it all: voc12_demo on a 1,000-image sample of PASCAL VOC 2012. | 10.4 |
| A3 | On the Grid, one row per run — one cell per task. | 19.4 |
| A2 | The upload job lands the sample in MinIO — images and annotations, in the standard VOC layout. | 25.4 |
| B1 | First checkpoint: verify_upload confirms every image has its annotation. | 35.4 |
| B2 | Every count lands in the task log — pairs uploaded, images verified. | 43.9 |
| B3 | Next, ingest_voc12 loads the verified sample into the dataset. | 56.4 |
| C1 | Now dedup: embed_fastdup turns each image into an embedding, then groups the near-duplicates. | 65.4 |
| C2 | Dedup publishes a report with the run — stored under the run's prefix, right next to the data. | 75.4 |
| C3 | The near-duplicate table, straight from the report. | 84.4 |
| D1 | Last step: cluster_split groups the images, then splits each cluster across train, val, and test — near-duplicates are flagged, and every split stays cluster-aware. | 93.1 |
| D2 | Five tasks, all green — raw sample in, split-ready dataset out, on one platform. | 105.6 |
| O1 | That's airflow-ml: raw dataset in, duplicate-checked and split-ready out. Bring your dataset — leave with split-ready train/val/test. | 116.1 |

Placement rules: start each line at its global time; if a line's TTS duration overruns into the next line's
start, overlap is acceptable (VO may slightly cross a shot cut); never let O1 end after 125.8 s. If a line is
too long for its shot window, prefer a slightly faster TTS rate over truncation — never drop or re-word words.

### 5. Final deliverable
- `video/final/renders/voc12_demo_final.mp4`: 1920×1080 @ 30 fps H.264, one AAC audio track,
  total duration inside 2:00–2:15 (expected ≈ 2:05.8), file size ≤ 50 MB.

## House rules
- Never commit renders or assets: `video/segment-d/renders/`, `video/segment-d/assets/`,
  `video/final/**/renders/` and any audio WAV files must stay git-ignored. The base HEAD tree may lack
  .gitignore entries the compose branches added — if they are missing, add them first (e.g.
  `video/**/renders/`, `video/**/assets/`, `video/final/**/renders/`, `video/final/audio/`), and verify with
  `git status` that no render/asset/audio file is tracked before committing. Commit the source: the D caption
  edit, the intro/outro HyperFrames projects, SOURCE.md updates, the VO line list, and any assembly script.
  The dispatcher records the branch tip.
- No full-screen VOC imagery anywhere; no training/evaluation/URL-based content; do not add on-screen text or
  numbers beyond the specified intro/outro copy (the D2 caption wording carries no numbers; keep "1000 images"
  as-is — it is upstream-verified).
- Segments A/B/C are byte-frozen approved content: stream-copy only, zero re-encoding.
- Your final message (becomes result.md) must contain: the final MP4 path + sha256 + ffprobe facts (codec,
  profile, resolution, fps, duration, size, video+audio streams); the expected-vs-actual duration; the D
  re-render diff scope vs the approved D render; the VO/music status (which lines were voiced, which TTS,
  music windows); and the branch tip SHA.

````

## Result (final output, verdict: none)

````
# voc12 demo: final video assembled (card t_31cfb2ff, window video-1)

The final video is built, in order intro → A → B → C → D → outro, with all 13 voiceover lines and music under the intro and outro only. Segments A, B and C are stream-copied: the final file's 3,775 video packets are byte-identical to the six source clips (packet-by-packet md5 compared). The segment-D project came from the remote-tracking ref `origin/factory/t_3735e1d8/video-3`; there's no local branch of that name, but the remote ref was there. So D was re-rendered with the new caption and the fallback (the old "split-safe" render) wasn't needed.

## Final MP4
- **Path:** `video/final/renders/voc12_demo_final.mp4`
- **sha256:** `f98e6f13ce2c573034d2bed021e88a3914e7ee978d63934fdcf802e353360ce0`
- **Video:** H.264 High, level 4.0, 1920×1080, 1:1 SAR, yuv420p, 30/1 fps, 3,775 frames
- **Audio:** AAC-LC, 48 kHz stereo, encoded at a 192k target. The average reported is about 137 kb/s because long stretches under A–D are silent.
- **Duration:** 125.833 s, which is 2:05.8 (expected 125.833 s; actual matches exactly, inside 2:00–2:15)
- **Size:** 13,536,324 B (12.9 MiB, limit 50 MB)
- **Loudness:** −17.2 LUFS integrated, true peak −1.5 dBFS. It decodes cleanly.
- **Cuts:** 0 / 10 / 35 / 65.067 / 92.767 / 115.833 s. I spot-checked frames either side of each cut.
- **Concat setting:** `-auto_convert 0`. With ffmpeg's default, 22 keyframes picked up an extra 44 bytes of codec headers. All six clips share identical codec parameters (same SPS/PPS), so turning it off is safe and keeps the packets exact.

## Segment D re-render compared with the approved D render
- **Caption:** line 2 now reads exactly `1000 images, near-dup-checked, cluster-aware splits`.
- **Font size:** at 28 px the line pushed the bar out to about 782 px wide, so that line alone is now 27 px with −0.1 px letter-spacing. The bar measures x580–1339, y884–991, the same as before. Nothing else changed: the D1 caption and every other overlay are untouched.
- **New render:** `video/segment-d/renders/segment-d.mp4`, sha256 `a4186ebb…5998d`. It has 692 frames, the same profile and codec parameters as the approved render, and `check` reports 0 errors.
- **Pixel diff between the two projects (lossless PNG render of both):**
  - Differences appear only in frames 376–691 (local time from 12.533 s) and only inside the caption bar.
  - Once the fade-in finishes, the difference is just the line-2 text area (x623–1296, y946–981).
  - Outside the bar, no pixel differs in any of the 692 frames.
- **Pixel diff between the two delivery MP4s:** frames 0–375 are bit-identical. From frame 376, faint encoder noise appears across the whole frame (about 61 dB PSNR outside the bar). That comes from re-encoding, not from any content change; the lossless comparison above shows the content outside the bar is identical.

## Intro and outro
- **Files:** `video/final/intro/` and `video/final/outro/`, 300 frames each, same profile as the segments, so both were stream-copied with no re-encode.
- **Look:** dark navy with Inter type and a cyan accent, matching the segments' caption chips.
- **Copy:** exactly the operator's final copy. The attribution `Dataset: PASCAL VOC 2012 (Flickr)` is 28 px.
- **Checks:** all text stays inside the title-safe area (checked by measuring) and `check` reports 0 errors.

## Voiceover and music
- **All 13 lines are voiced:** I1, A1, A3, A2, B1, B2, B3, C1, C2, C3, D1, D2, O1. The TTS is HyperFrames' built-in local engine (Kokoro-82M, voice `am_michael`), using the wording in the table; the I1/O1 "duplicate-checked" adaptation is applied.
- **Speed:** 1.0× except A1 at 1.05× (so it doesn't run into A3), B3 at 1.05× (at 1.0× the last word sounded clipped), and O1 at 1.08× (so it ends by 125.8 s).
- **Word check:** I transcribed every line back and nothing is missing. The transcriber misheard some code names ("dedup", "fastdup", "MinIO"), so those are worth one listen.
- **Placement:** every line starts at its listed time, and none overlaps the next. O1's speech ends at 125.61 s and its audio file at 125.74 s.
- **Music:** a soft synthesised bed (no samples, no vocals), mixed about 15 dB down. It plays only from 0–10 s and 115.833–125.833 s, with 0.8 s fades. Under A–D it is absent: the gaps between lines measure as digital silence.

## Repo
- **Branch tip:** `factory/t_31cfb2ff/video-1` @ `ec23bfb86d1aa9dc04dfb5ddc86c3495bac50851`
- **Committed:** the D caption edit and SOURCE.md notes, the intro/outro projects, `vo_lines.tsv`, `make_music.py`, `assemble.sh` and `.gitignore` rules.
- **Not committed:** renders, assets and audio are git-ignored and the working tree is clean. The sibling D branch was not touched.

I skipped the step of opening the interactive preview before rendering, because this run was unattended. The intro, outro and D projects can be opened in the HyperFrames desktop app for further edits. The video is ready for the operator's review on the card.
````

## Dispatch record

```json
{
  "argv0": "/home/dev-runner/.local/bin/claude",
  "artifacts": [
    {
      "attachable": true,
      "path": "video/final/intro/renders/intro.mp4",
      "sha256": "e6c5268b6ac4f1cc6f884bc223efa0a6bb68e3ea39558627cabe4de765baff1e",
      "size": 1694183,
      "stored": "/srv/factory-artifacts/t_31cfb2ff/video-1/video/final/intro/renders/intro.mp4"
    },
    {
      "attachable": true,
      "path": "video/final/outro/renders/outro.mp4",
      "sha256": "d6b6abede758cea177254cfcf21c13ab5260e795027909fa0cd318944f99daad",
      "size": 1652758,
      "stored": "/srv/factory-artifacts/t_31cfb2ff/video-1/video/final/outro/renders/outro.mp4"
    },
    {
      "attachable": true,
      "path": "video/final/renders/master_silent.mp4",
      "sha256": "a00cf81538792c7d0a93e5c9ecdab0a9717866d01711d29553bf55dbaf511371",
      "size": 11291698,
      "stored": "/srv/factory-artifacts/t_31cfb2ff/video-1/video/final/renders/master_silent.mp4"
    },
    {
      "attachable": true,
      "path": "video/final/renders/voc12_demo_final.mp4",
      "sha256": "f98e6f13ce2c573034d2bed021e88a3914e7ee978d63934fdcf802e353360ce0",
      "size": 13536324,
      "stored": "/srv/factory-artifacts/t_31cfb2ff/video-1/video/final/renders/voc12_demo_final.mp4"
    },
    {
      "attachable": true,
      "path": "video/segment-d/assets/capture-5.mp4",
      "sha256": "05e5671544fbbc6c55f214dc7bdd58ee0296519c54b11f1e866f7da539350955",
      "size": 738724,
      "stored": "/srv/factory-artifacts/t_31cfb2ff/video-1/video/segment-d/assets/capture-5.mp4"
    },
    {
      "attachable": true,
      "path": "video/segment-d/renders/segment-d.mp4",
      "sha256": "a4186ebbbd86c08fd92ecc1c103341069a601a50b393d5c66b442c7c5b85998d",
      "size": 1244479,
      "stored": "/srv/factory-artifacts/t_31cfb2ff/video-1/video/segment-d/renders/segment-d.mp4"
    }
  ],
  "base_ref": "HEAD",
  "base_sha": "c67e84814f84aef441d624115e847f0646c9ddb6",
  "binary": "/home/dev-runner/.local/bin/claude",
  "branch": "factory/t_31cfb2ff/video-1",
  "executor": {
    "image": "localhost/factory-media@sha256:5f4bca470357e918a7cf7b21eb8f12a5d580369f68013007b72aeeff13bf0e4c",
    "isolation": "container",
    "key": "sandbox-media",
    "kind": "podman",
    "limits": {
      "cpus": "8",
      "memory": "16g",
      "pids": 8192,
      "shm": "2g"
    },
    "services": {
      "egress-proxy": {
        "port": 8889
      }
    },
    "via": "function_default"
  },
  "exit_file": "/srv/software-factory/.dispatch/t_31cfb2ff--video-1.exit",
  "function": "video_production",
  "function_class": "work",
  "harness": "claude-video",
  "home_seed": [
    ".claude/settings.json",
    ".claude/plugins",
    ".claude.json",
    ".claude/skills/hyperframes",
    ".claude/skills/hyperframes-cli",
    ".claude/skills/hyperframes-registry"
  ],
  "inputs": [
    {
      "dst": "/inputs/artifacts/t_e687db28/video-2",
      "src": "/srv/factory-artifacts/t_e687db28/video-2"
    },
    {
      "dst": "/inputs/artifacts/t_dbf6286a/video-2",
      "src": "/srv/factory-artifacts/t_dbf6286a/video-2"
    },
    {
      "dst": "/inputs/artifacts/t_61fa2737/video-3",
      "src": "/srv/factory-artifacts/t_61fa2737/video-3"
    },
    {
      "dst": "/inputs/artifacts/t_3735e1d8/video-3",
      "src": "/srv/factory-artifacts/t_3735e1d8/video-3"
    }
  ],
  "install_roots": [
    "/home/dev-runner/.npm-global",
    "/home/dev-runner/.local"
  ],
  "job_dir": "/srv/factory-jobs/t_31cfb2ff--video-1",
  "mode": "print",
  "project": "airflow-ml",
  "project_real": "/run/media/shantanu/Volume/Projects/airflow-ml",
  "prompt_file": "/srv/software-factory/.dispatch/t_31cfb2ff--video-1.md",
  "prompt_sha256_prefix": "1fd78aa40b50e20c",
  "resolved_via": "function_default",
  "result": {
    "sha256": "7488d7bbbd524ff2e45139e860e9dbdf4b9a556ac32d2b62cae7038f464c7544",
    "stored": "/srv/factory-artifacts/t_31cfb2ff/video-1/result.md",
    "truncated": false,
    "verdict": null
  },
  "resume_session": null,
  "routing_sha256_prefix": "a1ce7f45d24409f3",
  "secrets": [
    "ANTHROPIC_API_KEY",
    "CLAUDE_CODE_OAUTH_TOKEN"
  ],
  "spec_sha256": "61fffff43964eb351791874c38c0fa5cad9bffe85952b554a96169138c13ff59",
  "staging": null,
  "stream": null,
  "ticket": "t_31cfb2ff",
  "transcript": "/srv/factory-jobs/t_31cfb2ff--video-1/transcript.log",
  "transcript_sha256": "8bed64cdd3ee8462f1e553e86250b903171e4ed8082cd0c01324fc2a0e5db144",
  "window": "video-1",
  "workdir": "/run/media/shantanu/Volume/Projects/airflow-ml",
  "workdir_rel": "."
}
```
