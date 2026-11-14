# creatorsmoment.1 – automated quiz Reels

Instagram account **creatorsmoment.1** (managed in Metricool, brand/blogId `8082055`, timezone Europe/Berlin).
This repo hosts the finished videos (Metricool pulls them from the public raw URL) and the pipeline that builds them.

Raw URL pattern: `https://raw.githubusercontent.com/fredericrakee-hash/creatormoment-videos/main/videos/<file>.mp4`

## Format (agreed with the owner, Fitim)
- **Quiz video** (30–45 s, English): a realistic 3D scene (Blender/Cycles) shows a real piece of technology doing
  something surprising (planes, ships, trains, rockets, tanks, cars, everyday tech …). Narrator explains what happens,
  then asks *"what is this called / why does this happen?"* with **4 options A–D**. The narrator **reads each option
  aloud and each one appears as it is read**. End: "Comment your answer… solution in two days… follow".
- **Solution video** 2 days later: `pipeline/answer.py` (reuses the clean action clip, reveals the right option in green,
  explains in 2–4 sentences, optional bonus follow-up question).
- Look: **realistic, grown-up, cinematic** – NOT cartoonish. Golden-hour sky (Nishita/multiple scattering), telephoto
  camera with slight shake, cinematic grade + grain (`grade.py`), subtle white typography, realistic UI elements
  (cockpit displays, radar data tags, etc.). No bright cartoon boxes, no stars, no outlined comic text.
- Voice: kokoro-onnx **`am_michael`**, natural speed (1.0), lightly energetic text. The owner disliked
  am_puck / am_fenrir / af_bella (too annoying). Alert/robot voices: `am_onyx` with radio filter.
- Captions: post text in English with the question + options A–D + "answer in 2 days" + ~10 hashtags.
- Mark posts `isAiGenerated: true` (Instagram requires it).
- Rotate the position of the correct answer (A/B/C/D) – never the same letter several times in a row.
- **Never give the answer away**: the narration, captions, on-screen text and post text must not use any word of the
  correct option (e.g. say "metal panels", not "grids", when the answer is "Grid fins").
- Facts must be correct. Double-check every claim with a web search before rendering.

## Review rule (first week, until the owner says otherwise)
Every post is created in Metricool as **draft (`draft: true`)** – the owner reviews and un-drafts it himself.
Never publish without draft during this phase.

## Daily plan
- 2 new quiz videos per day, posted at the best Metricool times (`getBestTimeToPostByNetwork`, usually ~10:00 and ~18:00).
- Before scheduling, call `getScheduledPosts` and never put two posts closer than 3 hours to each other; pick the next best free slot instead.
- Plus the solution videos that are due (quiz posted 2 days earlier), e.g. at ~12:00–13:00.
- Log everything in `quizzes.json`.

## How to build a new quiz (cloud session, 2 CPU cores, no GPU)
1. `bash pipeline/setup.sh`  (installs bpy, kokoro-onnx, downloads voice model; ~3 min)
2. Pick a topic not yet in `quizzes.json`; research it (WebSearch) and write a short script + 4 options.
3. `cp -r quizzes/q001 /home/claude/work/qNNN` and adapt:
   - `voice.py` – lines (v1…v5 story, v6 question, oA–oD options, v7 outro) → writes `audio/*.wav` + durations.
   - `scene.py` – the 3D scene (models built from primitives/bmesh, PBR materials, Nishita sky, cloud deck, camera
     path). Timeline functions drive the animation. Test with `TT=8,19 PCT=30 SPP=8 python3 scene.py -- test`
     and LOOK at the frames before the long render. Full render:
     `PCT=50 SPP=10 STEP=2 python3 scene.py -- frames` (renders every 2nd frame, ~7–9 s each → ~50–60 min).
     Run it in the background and poll; keep the turn alive (sleep ≤ 10 min per call) until done.
   **Smooth 30 fps (the owner noticed judder from simple frame blending):** export each shot's rendered
   15 fps frames (ungraded, scaled to 1080x1920) to a clip, run
   `minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1`, extract to `interp/<shot>/%05d.jpg`,
   and additionally render the REAL odd frames (`STEP=1 IFROM=.. ITO=..`) for fast-motion moments (parts
   unfolding, legs deploying) where interpolation ghosts. The compositor prefers real frames, then interpolated ones
   (see quizzes/q002/comp.py `_src`). Never interpolate across a hard cut.
     `python3 scene.py -- meta` writes screen positions for overlays.
   - `comp.py` – overlays (title, captions, data tags/HUD, quiz card with options appearing in sync with `oA–oD`
     start times) – set `DUR`, `END3D`, `SUBS`, `OPTS`.
   - `mix.py` – ambience, risers/hits, alerts, quiz bed, narration placement (keep the times in sync with comp.py).
4. `python3 comp.py stills 5,15,33` → look at them. Then `python3 comp.py v.mp4`, mux audio, compress
   (`-crf 24`, keeps it < 15 MB), save as `videos/qNNN-<topic>.mp4`.
5. Also save a **clean** (graded, no overlays) 10–14 s action clip as `videos/qNNN-clean.mp4` (see q001 for how)
   – the solution video reuses it.
6. Write `quizzes/qNNN/spec.json` (see q001) and add the entry to `quizzes.json`.
7. git add/commit/push, then `createScheduledPost` with the raw URL (draft: true), REEL, isAiGenerated true.

## Solution video
`python3 pipeline/answer.py quizzes/qNNN/spec.json videos/qNNN-answer.mp4` (~5 min), push, schedule as draft.
