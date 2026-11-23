#!/usr/bin/env bash
# voc12 demo — final assembly (card t_31cfb2ff). Run from the repo root after:
#   video/segment-d/renders/segment-d.mp4, video/final/{intro,outro}/renders/*.mp4 rendered (npx hyperframes render --quality delivery),
#   video/final/audio/vo_<ID>.wav synthesised for every line of vo_lines.tsv, music beds from make_music.py.
# 1) verify inputs, 2) concat intro→A→B→C→D→outro with the concat demuxer, -c copy, -auto_convert 0
#    (all six clips share identical SPS/PPS extradata, so packets stay byte-identical — no in-band parameter sets),
# 3) build one full-length audio track (VO at global starts + music under intro/outro only), 4) mux AAC, -c:v copy.
set -euo pipefail
F=video/final; R=$F/renders; mkdir -p $R
A=/inputs/artifacts/t_e687db28/video-2/video/segment-a/renders/segment-a.mp4
B=/inputs/artifacts/t_dbf6286a/video-2/video/segment-b/renders/segment-b.mp4
C=/inputs/artifacts/t_61fa2737/video-3/video/segment-c/renders/segment-c.mp4
D=video/segment-d/renders/segment-d.mp4
sha256sum -c - <<SUMS
dfddde5d453822e48e2aaa28f6e5d94c119cf7468a94b8c14f1e9ed9b2648db4  $A
bff3008c40adcd14db6b9714fd981872261b3ff7928e8e336340daa5b05a1f25  $B
0bf35a0b9aeb9a60d90483ee143a75f2ca55c4bcd1499edc444d1577d310ad83  $C
SUMS

CLIPS=($F/intro/renders/intro.mp4 $A $B $C $D $F/outro/renders/outro.mp4)
probe() { ffprobe -v error -select_streams v -show_entries stream=codec_name,profile,level,width,height,pix_fmt,r_frame_rate,sample_aspect_ratio,time_base,refs,codec_tag_string,color_range,color_space,color_primaries,color_transfer -of csv=p=0 "$1"; ffprobe -v error -select_streams v -show_entries stream=extradata -show_data "$1" | md5sum; }
REF=$(probe "${CLIPS[0]}")
for c in "${CLIPS[@]}"; do [ "$(probe "$c")" == "$REF" ] || { echo "profile mismatch: $c" >&2; exit 1; }; done

LIST=$R/concat.txt; : > $LIST
for c in "${CLIPS[@]}"; do echo "file '$(realpath "$c")'" >> $LIST; done
ffmpeg -v error -y -f concat -safe 0 -auto_convert 0 -i $LIST -c copy -an $R/master_silent.mp4
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 $R/master_silent.mp4)
OUTRO_START=$(python3 -c "print($DUR-10)")

# Audio graph: each VO line delayed to its global start; music beds (-15 dB, 0.8 s fades) at 0 s and at DUR-10 s.
IN=(); FG=""; MIX=""; n=0
while IFS=$'\t' read -r id t line; do
  [[ "$id" == \#* || -z "$id" ]] && continue
  IN+=(-i $F/audio/vo_$id.wav)
  ms=$(python3 -c "print(round($t*1000))")
  FG+="[$n:a]aresample=48000,aformat=channel_layouts=stereo,adelay=${ms}|${ms}[v$n];"; MIX+="[v$n]"; n=$((n+1))
done < $F/vo_lines.tsv
IN+=(-i $F/audio/music_intro.wav -i $F/audio/music_outro.wav)
om=$(python3 -c "print(round($OUTRO_START*1000))")
FG+="[$n:a]volume=-15dB,afade=t=in:d=0.8,afade=t=out:st=9.2:d=0.8[mi];"; MIX+="[mi]"; n=$((n+1))
FG+="[$n:a]volume=-15dB,afade=t=in:d=0.8,afade=t=out:st=9.2:d=0.8,adelay=${om}|${om}[mo];"; MIX+="[mo]"; n=$((n+1))
FG+="${MIX}amix=inputs=$n:normalize=0:duration=longest,volume=6.5dB,alimiter=limit=0.84:level=0,apad,atrim=0:$DUR[out]"
ffmpeg -v error -y "${IN[@]}" -filter_complex "$FG" -map "[out]" -ar 48000 -c:a pcm_s16le $F/audio/mix_full.wav

ffmpeg -v error -y -i $R/master_silent.mp4 -i $F/audio/mix_full.wav -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 192k -ar 48000 \
  -movflags +faststart -shortest $R/voc12_demo_final.mp4
ffprobe -v error -show_entries format=duration,size:stream=index,codec_type,codec_name,profile,width,height,r_frame_rate,sample_rate,channels,bit_rate -of compact $R/voc12_demo_final.mp4
sha256sum $R/voc12_demo_final.mp4
