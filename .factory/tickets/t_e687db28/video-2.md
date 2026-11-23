# t_e687db28 / video-2

## Prompt as dispatched

````
---
factory: {base: factory/t_e687db28/video-1, inputs: [artifacts/t_cc35d411/capture-2]}
---

# Task: voc12_demo UX demo — segment A (ACQUIRE), round 2: fix A2 title chip span

Round 2 of the compose-A card (t_e687db28). `video-1` (base branch) already built the ACQUIRE segment:
HyperFrames overlays on the QA-approved capture-2 clip, delivered a silent 1920×1080@30 H.264 MP4. The
reviewer (testing, round 1) verified **10 of 11 acceptance checks PASS** and requested exactly **one
change**:

> **A2 title chip missing for 20–25 s (MinIO half).** The spec requires `A2 · Upload in MinIO` constant
> across the full A2 shot (global 15–25 s). Pixel-verified: chip present @16.5 s / @19.2 s, **absent
> @21.0 s / @24.5 s**. The chip lives in `compositions/a2.html` with local `data-start=0 data-duration=5`
> (i.e. global 15–20 s only); `a2x.html` (the 20–25 s half) carries no chip. Fix: the chip must be at
> `y=252` for **global 15–24.967 s** (no geometry conflict — folders callout is x425–1060 y315–450, MinIO
> table controls end at y228), re-render via `npx hyperframes render --quality delivery`, and re-attach.

Everything else (A1/A3 chips, all callouts, hostname cover, caption bar, v2 copy, numbers) is verified
correct — **do not touch it**. Your job: one minimal change + full re-render + re-verification.

## Base branch state (factory/t_e687db28/video-1)

Project in `video/segment-a/`: `index.html`, `hyperframes.json`, `meta.json`, `observed.json`,
`package.json`, `.gitignore`, `compositions/{a1,a3,a2,a2x,captions}.html`, `assets/segment-a.mp4`
(source clip, sha256 `8e94e88aa489949c671175e0c979b173b0215ce71eebc2b9fa51635a35b6ec3f` — byte-identical
to the QA-approved capture-2 artifact, also mounted read-only at
`/inputs/artifacts/t_cc35d411/capture-2/out/segment-a.mp4`; verify, never modify), `renders/` (gitignored).

Timeline wiring in `index.html` (already correct — **no change needed there**):
- `#a2` → `compositions/a2.html`, `data-start=15 data-duration=5` (global 15–20 s, log half)
- `#a2x` → `compositions/a2x.html`, `data-start=15 data-duration=9.967` (global 15–24.967 s, full A2 shot)

Current `compositions/a2.html` (relevant parts):

```html
<div id="chip-a2" class="clip" data-start="0" data-duration="5" data-track-index="2">
  <div class="chip"><span class="dot"></span>A2 · Upload in MinIO</div>
</div>
```
plus `.chip` / `.chip .dot` CSS (top: 252px, right: 36px, …) and timeline lines
`tl.fromTo("#chip-a2 .chip", { opacity: 0, y: -10 }, { opacity: 1, y: 0, duration: 0.25, ease: "power2.out" }, 0.1);`
and `tl.to("#chip-a2 .chip", { opacity: 0, duration: 0.2, ease: "power2.in" }, 4.78);`

`compositions/a2x.html` currently contains only `#cover-hostname` (local 3.55–5.0 = global 18.55–20.0 s,
track 2) and `#co-a2-folders` (local 5–9.967 = global 20–24.967 s, track 2) — **no chip**.

## Required changes (the ONLY code changes)

1. `compositions/a2x.html`:
   - Add the chip CSS (`.chip` and `.chip .dot`) — copy it verbatim from `compositions/a2.html`
     (top: 252px, right: 36px, same fonts/colors/border/box-shadow — the chip must be visually
     identical to the one that was on 15–20 s).
   - Add the chip as a clip spanning the whole composition window:
     `<div id="chip-a2" class="clip" data-start="0" data-duration="9.967" data-track-index="3">`
     containing `<div class="chip"><span class="dot"></span>A2 · Upload in MinIO</div>`
     (track 3 — the existing clips in this file both use track 2 and both overlap the chip in time).
   - GSAP: fade the chip in at local 0.1 s exactly as before
     (`tl.fromTo("#chip-a2 .chip", { opacity: 0, y: -10 }, { opacity: 1, y: 0, duration: 0.25, ease: "power2.out" }, 0.1);`)
     and **no fade-out** — it must stay fully visible until the end of the composition (the video ends
     at 24.967 s, so a final fade is pointless; the reviewer probes @21.0 s and @24.5 s must see it).
2. `compositions/a2.html`: remove the `#chip-a2` clip element, its two GSAP timeline lines, and the now
   unused `.chip` / `.chip .dot` CSS rules. Everything else in a2.html (the `#co-a2-sample` and
   `#co-a2-uploadok` callouts at local 0.6+4.4, track 3) stays exactly as is.
3. `index.html`, `a1.html`, `a3.html`, `captions.html`, `hyperframes.json`, `meta.json`, `observed.json`,
   `assets/segment-a.mp4`: **unchanged**. (a2x already spans global 15–24.967 s, so no timeline rewiring.)

## Hard rules (inherited from the card + round 1 — still all in force)

- Never re-render / speed-change / crop / alter the captured UI. Base = `assets/segment-a.mp4` untouched.
- Silent segment: no audio track. No external images/footage — overlays are text/chips/boxes only
  (licensing: no VOC image content may be introduced).
- No numbers other than the conf literal `1000` (A1 caption) and `jpeg_uploaded = 1000` (A2 line 2).
  Never render the raw `manual__…` run id; never caption the MinIO side-panel bucket totals
  (2734 Objects / 113.8 MiB) — they are reference-only.
- The hostname cover (global 18.55–20.0 s) must keep hiding the lazy-rendered internal log URL row.
- Renders are never committed (`video/segment-a/renders/` stays gitignored).

## Build, check, render

1. `npx hyperframes check` in `video/segment-a/` — must pass 0 errors / 0 warnings.
2. Snapshot review on a preview: extract frames and verify (a) the chip is present, opaque and in the
   same position (y=252, right side) at **global 16.5 s, 19.2 s, 21.0 s and 24.5 s** (pixel probe in the
   chip zone vs the base clip — non-zero diff px at all four), (b) no other overlay changed position or
   timing, (c) chip legible over both the light Airflow UI and the dark MinIO UI, (d) nothing on-screen
   text covered.
3. Delivery render: `npx hyperframes render --quality delivery -o video/segment-a/renders/segment-a.mp4`
4. Commit the project change to this window's branch (`factory/t_e687db28/video-2`) — source files only,
   working tree clean, renders uncommitted.

## Acceptance (report each, with evidence)

- ffprobe spec line of the new MP4: h264, 1920×1080, 30 fps, 24.967 s (±1 frame), ≤ 50 MB, exactly one
  (video-only, silent) stream.
- sha256 of the rendered MP4; sha256 of `assets/segment-a.mp4` (must equal `8e94e88a…ec3f`).
- Chip fix: per-timestamp status (16.5 / 19.2 / 21.0 / 24.5 s) with the pixel evidence; confirm the chip
  is constant global 15–24.967 s at y=252 and the `a2.html` half now carries no chip of its own.
- Regression spot-check: hostname cover still hides the URL row (e.g. 0 blue-link px in the URL band at
  19.2 s); all other round-1-passing overlays byte-identical in timing/geometry (state this explicitly).
- Branch tip SHA of `factory/t_e687db28/video-2`.

End your final message with: (a) the one-line chip-fix status + regression spot-check result, (b)
ffprobe + sha256 lines (render + source asset), (c) branch tip SHA.
````

## Result (final output, verdict: none)

````
Done. Round-2 fix complete, rendered, verified, committed.

## (a) Chip-fix status + regression spot-check

**Chip fix — PASS at all four probe points.** Chip moved from `a2.html` (was local 0–5 s = global 15–20 s only) to `a2x.html` as `#chip-a2` clip `data-start=0 data-duration=9.967` on track 3, with the CSS copied verbatim (`top:252px; right:36px`) and the same fade-in at local 0.1 s — **no fade-out**, so it holds to the last frame. Probes ran on lossless snapshot frames **and** on frames extracted from the delivery MP4 itself (vs the base clip, thr=24, chip zone x1500–1900 y240–320):

| t (global) | chip-zone diff px (render vs base) | chip top edge | verdict |
|---|---|---|---|
| 16.5 s | 18 408 / 18 505 | y=252 | present, opaque, light Airflow UI |
| 19.2 s | 18 408 / 18 499 | y=252 | present, opaque, light Airflow UI |
| 21.0 s | 17 559 / 17 545 | y=252 | present, opaque, dark MinIO UI |
| 24.5 s | 17 559 / 17 546 | y=252 | present, opaque, dark MinIO UI |

Compositionally verified in the rendered frames: cyan dot 8×8 px at x1602–1609, white text x1622–1860 (13 px gap — nothing covered), chip box ≈ x1582–1883, y252–303, inside the safe area clear of the folders callout (x425–1060, y315–450) and the table controls (end y228). Vision-model transcription of native-res crops read "A2 : Upload in MinIO" on both the light (16.5/19.2) and dark (21.0) UIs. `a2.html` now carries no chip (diff: clip, both GSAP lines, `.chip`/`.chip .dot` CSS removed; the two callouts byte-identical).

**Regression spot-check — PASS.**
- Hostname cover: in the exact cover rect (x660–1900, y341–362) at 19.2 s the delivery frame has **0 blue-link px** (base clip: 4120) — the lazy URL row is fully hidden; cover clip/timing in `a2x.html` untouched.
- All other round-1-passing overlays are byte-identical in timing/geometry: `git diff` touches **only** `a2.html` (−30) and `a2x.html` (+31) — `index.html`, `a1.html`, `a3.html`, `captions.html`, `hyperframes.json`, `meta.json`, `observed.json` untouched; the `cover-hostname` and `co-a2-folders` clips and their GSAP lines in `a2x.html` are unchanged; `npx hyperframes timeline` confirms `chip-a2 15–24.967 s` and all other clips at their round-1 spans.
- `npx hyperframes check`: **0 errors**; 5 pre-existing warnings only (`film_silent` by design for this segment + 20 px callout-label floors on round-1-approved overlays) — none introduced by the chip change.

## (b) ffprobe + sha256

```
# video/segment-a/renders/segment-a.mp4 (delivery render, --quality delivery)
codec_name=h264  codec_type=video  width=1920  height=1080
r_frame_rate=30/1  avg_frame_rate=30/1  nb_frames=750
duration=25.000000 s   (spec 24.967 s = 749.01 frames → 750, within ±1 frame)
size=2570887 B (2.45 MB ≤ 50 MB)   nb_streams=1 (video-only, silent: no audio stream)

sha256(render)    = dfddde5d453822e48e2aaa28f6e5d94c119cf7468a94b8c14f1e9ed9b2648db4
sha256(assets/segment-a.mp4) = 8e94e88aa489949c671175e0c979b173b0215ce71eebc2b9fa51635a35b6ec3f  ✓
sha256(/inputs/artifacts/t_cc35d411/capture-2/out/segment-a.mp4) = 8e94e88a…ec3f  ✓ (byte-identical, never modified; local assets/ copy is gitignored working material)
```

## (c) Branch tip

`factory/t_e687db28/video-2` → **`efc4d4821ed293eefebe411616013688fc5837e8`** (parent `c64b083`); commit contains exactly the two source files — working tree clean, `renders/` (and `assets/`, `.hyperframes/`) uncommitted per the gitignore.
````

## Dispatch record

```json
{
  "argv0": "/home/dev-runner/.local/bin/omp",
  "artifacts": [],
  "base_ref": "factory/t_e687db28/video-1",
  "base_sha": "c64b08376e9cdf0d62215af0091a985cc449e651",
  "binary": "/home/dev-runner/.local/bin/omp",
  "branch": "factory/t_e687db28/video-2",
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
      "comfyui": {
        "port": 8188
      },
      "egress-proxy": {
        "port": 8889
      },
      "h3-jobs": {
        "port": 8288
      },
      "llama-swap": {
        "port": 8080
      }
    },
    "via": "function_default"
  },
  "exit_file": "/srv/software-factory/.dispatch/t_e687db28--video-2.exit",
  "function": "video_production",
  "function_class": "work",
  "harness": "omp-video",
  "home_seed": [
    ".omp/agent/models.yml",
    ".omp/agent/config.yml",
    ".omp/agent/mcp.json",
    ".omp/plugins",
    ".pi/agent/pi-llama-swap.json",
    ".agents/skills/hyperframes",
    ".agents/skills/hyperframes-cli",
    ".agents/skills/hyperframes-registry"
  ],
  "inputs": [
    {
      "dst": "/inputs/artifacts/t_cc35d411/capture-2",
      "src": "/srv/factory-artifacts/t_cc35d411/capture-2"
    }
  ],
  "install_roots": [
    "/home/dev-runner/.local",
    "/home/dev-runner/.omp/mcp",
    "/run/media/shantanu/Volume/Tools/pi-llama-swap"
  ],
  "job_dir": "/srv/factory-jobs/t_e687db28--video-2",
  "mode": "print",
  "project": "airflow-ml",
  "project_real": "/run/media/shantanu/Volume/Projects/airflow-ml",
  "prompt_file": "/srv/software-factory/.dispatch/t_e687db28--video-2.md",
  "prompt_sha256_prefix": "b40044d890cedaa3",
  "resolved_via": "function_default",
  "result": {
    "sha256": "9cc88c68c7eb371f9fcc3fb3a46a7bb4aaaa6bf2b8e16bed15d88d21eafb5e35",
    "stored": "/srv/factory-artifacts/t_e687db28/video-2/result.md",
    "truncated": false,
    "verdict": null
  },
  "resume_session": null,
  "routing_sha256_prefix": "a1ce7f45d24409f3",
  "secrets": [],
  "spec_sha256": "99df92671f657b1f255f850c680f975a316d43e2123962c77ca66076c93079a5",
  "staging": null,
  "stream": "omp-json",
  "ticket": "t_e687db28",
  "transcript": "/srv/factory-jobs/t_e687db28--video-2/transcript.log",
  "transcript_sha256": "1758d04d7ad1482342f5e12cd853c8593f45ff31f0788ffe08025e37a9b96d1a",
  "window": "video-2",
  "workdir": "/run/media/shantanu/Volume/Projects/airflow-ml",
  "workdir_rel": "."
}
```
