# voc12 demo — final assembly (card t_31cfb2ff)

- `intro/` (I1, 10 s / 300 fr) and `outro/` (O1, 10 s / 300 fr): HyperFrames projects; copy = operator final copy
  (t_31cfb2ff unblock comment 2026-11-23). Render: `npx hyperframes render --quality delivery -o renders/<name>.mp4`.
- `vo_lines.tsv`: the 13 VO lines (v2 storyboard + operator overrides) with global start times.
  VO synthesised with `npx hyperframes tts` (Kokoro-82M, voice `am_michael`) → `audio/vo_<ID>.wav`; speed 1.0 except
  A1 1.05 (avoid overlapping A3), B3 1.05 (clean final word), O1 1.08 (end ≤ 125.8 s). Words never changed.
- `make_music.py`: procedurally synthesised instrumental bed → `audio/music_intro.wav`, `audio/music_outro.wav`.
- `assemble.sh` (run from repo root): verifies inputs, concat demuxer `-c copy -auto_convert 0` intro→A→B→C→D→outro
  (video packets byte-identical to sources), mixes VO + music (intro 0–10 s and last 10 s only), muxes AAC 192k
  48 kHz with `-c:v copy` → `renders/voc12_demo_final.mp4`.
- `audio/` and `renders/` are git-ignored.
