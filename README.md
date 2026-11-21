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
- Captions: post text in English with the question + options A–D + "solution tomorrow" + ~10 hashtags.
- Mark posts `isAiGenerated: true` (Instagram requires it).
- Rotate the position of the correct answer (A/B/C/D) – never the same letter several times in a row.
- **Never give the answer away**: the narration, captions, on-screen text and post text must not use any word of the
  correct option (e.g. say "metal panels", not "grids", when the answer is "Grid fins").
- Facts must be correct. Double-check every claim with a web search before rendering.

## Publishing rule (changed by the owner on 2026-11-14)
Posts are scheduled **directly (`draft: false`)** – no drafts, no manual approval. The owner reviews afterwards.

## Daily plan (changed by the owner on 2026-11-16)
- **Exactly 3 posts per day** in the slots ~10:00, ~14:00, ~18:00.
- **Solutions come the NEXT DAY** (not after 2 days). New videos and captions must say
  "The solution comes tomorrow" / "Solution tomorrow" (q001–q006 still say "in two days" – that's fine, they are answered as planned).
- Rule: solutions(day D) = quizzes(day D-1); new quizzes(day D) = 3 - solutions(day D).
  This automatically alternates 2 quizzes + 1 solution / 1 quiz + 2 solutions.
- Transition: Tue 17.11 = solutions #1-#3, Wed 18.11 = solutions #4-#6, **Thu 19.11 = 2 quizzes only (q007, q008)**,
  Fri 20.11 = 2 solutions (q007, q008) + 1 quiz, Sat = 1 solution + 2 quizzes, and so on.
- Put the solutions in the earlier slots and quizzes in the later ones when possible (e.g. 10:00 + 14:00 solutions,
  18:00 quiz), but any order is fine. Never more than 3 posts on a day.
- Log everything in `quizzes.json`. Entries with status "in_progress" are being built by another session: never touch them,
  never reuse their topic or slot.

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
     Slow scenes (space etc.) can be rendered with `STEP=3` and interpolated 10→30 fps with `pipeline/interp3.py` (same args) – saves ~1/3 render time.
     Subtitles can be timed automatically from the voice lines with `pipeline/subs.py` (`make_subs`, see quizzes/q013/comp.py).
     Helper: `python3 pipeline/interp.py <qdir> "A:0:234,B:234:537,..."` (shot:first_frame:end_frame) builds `interp/<shot>/`
     from the even frames at render resolution (fast; the grade upscales). If a shot starts on an odd frame, copy the next even frame to it first.
   - `comp.py` – overlays (title, captions, data tags/HUD, quiz card with options appearing in sync with `oA–oD`
     start times) – set `DUR`, `END3D`, `SUBS`, `OPTS`.
   - `mix.py` – ambience, risers/hits, alerts, quiz bed, narration placement (keep the times in sync with comp.py).
4. `python3 comp.py stills 5,15,33` → look at them. Then `python3 comp.py v.mp4`, mux audio, compress
   (`-crf 24`, keeps it < 15 MB), save as `videos/qNNN-<topic>.mp4`.
   If crf 24 comes out > 15 MB (grain + fine detail can push it to 100 MB), use the 2-pass helper:
   `bash pipeline/enc2pass.sh v.mp4 audio/mix.wav videos/qNNN-<topic>.mp4 2200` (kbit/s; ~2000–2300 → 12–14 MB for 45–50 s).
5. Also save a **clean** (graded, no overlays) 10–14 s action clip as `videos/qNNN-clean.mp4` (see q001 for how)
   – the solution video reuses it.
6. Write `quizzes/qNNN/spec.json` (see q001) and add the entry to `quizzes.json`.
7. git add/commit/push, then `createScheduledPost` with the raw URL (draft: false), REEL, isAiGenerated true.

## Solution video
`python3 pipeline/answer.py quizzes/qNNN/spec.json videos/qNNN-answer.mp4` (~5–10 min), push, schedule it (draft: false).

**Show the explanation visually (owner request 2026-11-21):** every solution video must SHOW what the narrator explains,
not just subtitles. Write `quizzes/qNNN/explain.py` with `SCENES = [scene0, scene1, …]` (one animated diagram per
sentence in `spec["explain"]`), drawn with `pipeline/explain_kit.py` (lines/arrows that draw on, labels, tags, check/cross,
bars, waves, and `k.clip(frac)` to show a frame of the clean 3D clip with annotations). answer.py then shows a green answer
banner + the diagram panel while each sentence is spoken. Check with
`STILLS=16,20,25 python3 pipeline/answer.py quizzes/qNNN/spec.json /tmp/aNNN` (prints the timeline, saves PNGs) and LOOK
at the stills before the full render. Examples: quizzes/q009–q011/explain.py. Clean, grown-up infographic style; no emoji.
Write explain.py when building the quiz (you know the topic best then), or at the latest when building the solution.

## Story votes (account shortsfilm) – set up 2026-11-16
- GitHub Action `.github/workflows/votes.yml` runs hourly, reads comments via the Instagram API (secret `IG_TOKEN`) and writes only counts to `votes/results/<media_id>.json` and `votes/results/latest.json` (field `winner`, `tie`).
- A post takes part when its caption has a line `VOTE: OPTION1 / OPTION2` (2-4 options). Comments count if they name exactly one option (word anywhere, or letter A/B/... in a short comment). One vote per person, latest comment wins.
- Tie: Claude decides and the next episode says "It was a tie, so fate decided."
- The token is extended automatically every Monday. If the Action fails, tell the owner.
