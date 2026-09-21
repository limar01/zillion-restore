# AI VIDEO FACTORY — META AI / VIBES AI VIDEO ENGINE
## Master Project Specification
### 8-Second Text-to-Video + Reference Images + Automated Audio/Lip-Sync Pipeline

---

# 1. PURPOSE

Build a modular AI Video Factory around a Meta AI / Vibes-style video generation engine with the following target workflow:

USER REQUEST
→ STORY
→ CHARACTER BIBLE
→ VISUAL BIBLE
→ SCENE PLAN
→ REFERENCE IMAGES
→ 8-SECOND VIDEO GENERATION
→ VIDEO QA
→ VOICEOVER
→ SFX
→ BGM
→ LIP-SYNC
→ SUBTITLES
→ FFmpeg EDITING
→ FINAL VIDEO

The major provider assumptions for this version are:

- Video generation unit: 8 seconds
- Generated video has no audio
- Reference images may be used
- No assumed daily generation limit
- Audio must be generated/added separately
- Voiceover must be synchronized with scenes
- SFX must be generated/selected and synchronized
- BGM must be generated/selected and mixed
- Lip-sync must be a separate pipeline stage
- The system must remain provider-agnostic so another video engine can be added later

Do not hard-code these assumptions into every module. Put provider capabilities in configuration.

---

# 2. CORE CONCEPT

The user should think:

"Create a 10-minute Filipino horror story."

The system should automatically think:

600 seconds
÷
8-second video units
=
75 base video units

Then automatically generate:

- story
- narration
- characters
- visual references
- scenes
- 8-second visual clips
- voiceover
- dialogue timing
- SFX
- BGM
- subtitles
- lip-sync instructions
- final assembly

The user should NOT manually calculate scenes or 8-second clips.

---

# 3. AUDIO-FIRST + VIDEO-FIRST SYNCHRONIZATION

Because the provider creates silent video, audio must be treated as a first-class production layer.

Do NOT simply generate video first and attach random audio afterward.

The system should maintain a shared timeline.

Example:

SCENE 01
00:00–00:08
Video
Narration
Dialogue
SFX
BGM
Lip-sync

SCENE 02
00:08–00:16
Video
Narration
Dialogue
SFX
BGM
Lip-sync

Every media asset should have:

- start time
- end time
- duration
- scene ID
- character ID where applicable
- layer type
- synchronization status

---

# 4. MEDIA LAYERS

The final video timeline should support:

VIDEO
VOICEOVER
DIALOGUE
SFX
BGM
AMBIENCE
SUBTITLES
LIP-SYNC
TRANSITIONS

Layer priority:

1. Video
2. Dialogue
3. Voiceover
4. SFX
5. Ambience
6. BGM
7. Subtitles
8. Lip-sync metadata/rendering

---

# 5. PROJECT CONFIGURATION

Support:

- Project name
- Niche
- Topic
- Target duration
- Language
- Aspect ratio
- Resolution
- Visual style
- Model
- Clip duration
- Reference image usage
- Voiceover
- Voice type
- Voice speed
- Voice pitch
- SFX
- BGM
- Ambience
- Lip-sync
- Subtitles
- Output format

Example:

{
  "project": "My Horror Story",
  "target_duration": 600,
  "language": "English",
  "aspect_ratio": "16:9",
  "resolution": "720p",
  "video_model": "meta-ai-vibes",
  "clip_duration": 8,
  "reference_images": true,
  "audio_generation": true,
  "voiceover": true,
  "sfx": true,
  "bgm": true,
  "lip_sync": true,
  "subtitles": true
}

---

# 6. STORY ENGINE

Generate:

- title
- logline
- synopsis
- complete story
- acts
- scenes
- narration
- dialogue
- emotional progression
- visual actions
- sound events
- ending

The story must be designed for short visual clips.

Avoid creating scenes that require a single 8-second generation to communicate too many events.

---

# 7. CHARACTER BIBLE

Generate complete Character DNA:

- name
- age
- gender
- height
- body
- face
- skin
- hair
- eyes
- clothing
- accessories
- props
- personality
- expression style
- movement style
- voice
- dialogue behavior
- lip-sync requirements

For characters that speak:

Create a Voice Profile:

- voice identity
- gender presentation
- approximate age
- accent
- language
- pitch
- speed
- emotional range
- speaking style

Character DNA must remain consistent across all reference images and scenes.

---

# 8. REFERENCE IMAGE ENGINE

Because the provider may support reference images, create a dedicated Reference Image Pipeline.

Generate or prepare:

1. Main character reference
2. Supporting character references
3. Location references
4. Key prop references
5. Visual style reference
6. Optional expression reference
7. Optional pose reference

Each reference must have:

- asset ID
- character/location ID
- prompt
- source
- resolution
- aspect ratio
- version
- QA status

Reference images should be reused across scenes whenever appropriate.

The system should NOT unnecessarily generate new references for every scene.

---

# 9. VISUAL BIBLE

Create a project-wide Visual Bible:

- art direction
- rendering style
- color language
- lighting
- camera
- lens behavior
- environment
- texture
- character style
- background style
- motion rules
- composition
- continuity rules

Reference images + Visual Bible + Character DNA should form the visual consistency layer.

---

# 10. 8-SECOND SCENE ENGINE

The provider's basic generation unit is 8 seconds.

Every scene must be compiled into an 8-second visual generation specification.

A scene should normally contain:

- one main action
- one main camera movement
- limited character movement
- limited simultaneous events
- one main location where practical

Example:

BAD:
A woman runs, falls, gets up, fights two men, grabs a phone, looks outside, and a car explodes.

GOOD:
A frightened woman slowly backs toward a dark hallway as the camera pushes toward her face.

Complex story events should be split across multiple 8-second clips.

---

# 11. SCENE TYPES

Support:

HOOK
ESTABLISHING
CHARACTER_INTRODUCTION
DIALOGUE
REACTION
ACTION
TRANSITION
MONTAGE
CLIMAX
RESOLUTION

---

# 12. SCENE DATA MODEL

Each scene should contain:

- scene_id
- act
- sequence
- duration
- location
- time_of_day
- characters
- references
- action
- emotion
- narration
- dialogue
- camera
- lighting
- props
- SFX events
- BGM state
- ambience
- lip_sync_required
- subtitle_text
- prompt
- QA
- generation_status

---

# 13. PROMPT COMPILER

Compile one complete prompt for each 8-second generation unit.

Prompt should combine:

- Character DNA
- Visual DNA
- Reference image instructions
- Environment
- Action
- Emotion
- Camera
- Lighting
- Composition
- Props
- Motion
- Continuity
- Negative constraints

Avoid unnecessary prompt bloat.

The prompt compiler should understand that the video engine produces NO AUDIO.

Therefore prompts should focus on visuals and should NOT depend on spoken dialogue being generated by the video model.

---

# 14. CONTINUITY ENGINE

Track:

- character appearance
- clothing
- hairstyle
- props
- location
- weather
- time
- lighting
- camera direction
- emotional state
- story state
- previous scene ending
- next scene requirement

Use reference images whenever possible to reinforce visual consistency.

---

# 15. AUDIO PRODUCTION ENGINE

This is the major addition for the Meta AI / Vibes version.

The system must automatically create a separate audio production pipeline.

Audio pipeline:

SCRIPT
→ AUDIO PLAN
→ VOICEOVER
→ DIALOGUE
→ SFX
→ AMBIENCE
→ BGM
→ MIX
→ SYNC
→ FINAL VIDEO

---

# 16. VOICEOVER ENGINE

Generate narration based on the final script.

For each narration segment store:

- text
- speaker
- start time
- expected duration
- actual duration
- emotion
- voice
- pitch
- speed
- audio file
- QA status

The system must calculate actual voice duration.

If narration is too long for the planned visual timeline:

Option A:
Adjust voice speed within safe limits.

Option B:
Split the narration.

Option C:
Extend/restructure scene timing.

Do not force unnatural speech speed merely to fit an 8-second clip.

---

# 17. DIALOGUE ENGINE

For dialogue scenes:

Store:

- character
- dialogue text
- start
- end
- voice
- emotion
- speaking intensity
- lip-sync requirement

Dialogue should be aligned with the character visible in the scene.

If multiple characters speak:

Create separate dialogue segments.

---

# 18. LIP-SYNC ENGINE

Lip-sync is a separate processing stage.

Pipeline:

CHARACTER VIDEO
+
DIALOGUE AUDIO
→
LIP-SYNC ENGINE
→
LIP-SYNC VIDEO

The system should support a pluggable lip-sync provider.

Possible provider categories:

- local lip-sync models
- external API
- browser-based tool
- future provider adapters

Do not hard-code one lip-sync provider into the core architecture.

If no reliable lip-sync provider is available:

- preserve the original video
- mark lip-sync as pending/optional
- do not destroy the valid source clip

---

# 19. LIP-SYNC RULES

Lip-sync should only be applied when:

- character is visible
- character is speaking
- face/mouth is sufficiently visible
- dialogue exists

Do NOT lip-sync:

- narration over a non-speaking character
- background characters
- scenes where mouth is hidden
- scenes without dialogue

Scene metadata should define:

lip_sync_required = true/false

---

# 20. SFX ENGINE

Automatically detect potential sound events from the scene plan.

Examples:

- door opening
- footsteps
- rain
- thunder
- phone notification
- explosion
- impact
- glass breaking
- crowd
- vehicle
- wind
- heartbeat

For each SFX:

- type
- start
- duration
- intensity
- source
- audio file
- volume
- pan
- QA

SFX must be synchronized with visual events.

---

# 21. AMBIENCE ENGINE

Generate or select background ambience:

Examples:

- forest
- city
- classroom
- office
- bedroom
- rain
- ocean
- nighttime
- horror ambience

Ambience should loop or extend without obvious repetition.

---

# 22. BGM ENGINE

Generate or select background music based on:

- genre
- emotional state
- scene type
- pacing
- intensity

Examples:

Horror:
low drone → tension → climax

Romance:
soft acoustic → emotional build → resolution

Motivation:
calm → inspirational build → uplifting ending

Finance:
clean modern → energetic educational

BGM should automatically duck under narration/dialogue.

---

# 23. AUDIO MIXER

Use FFmpeg or a dedicated audio processing layer.

Mix:

VOICEOVER
+
DIALOGUE
+
SFX
+
AMBIENCE
+
BGM

Apply:

- volume normalization
- ducking
- fades
- crossfades
- stereo positioning where appropriate
- silence control

Voice/dialogue must remain intelligible over BGM.

---

# 24. SUBTITLE ENGINE

Generate subtitles from:

- narration
- dialogue

Support:

- SRT
- VTT
- burned-in subtitles

Subtitle timing must come from actual audio timing, not only estimated script timing.

---

# 25. MASTER TIMELINE

Create a single timeline database.

Example:

TIME      VIDEO       VOICE       SFX       BGM       SUBTITLE
00:00     Scene 01   Narration   Rain      Horror    Text
00:08     Scene 02   Dialogue    Door      Horror    Text
00:16     Scene 03   Narration   Footstep  Tension   Text

Every asset references the timeline.

---

# 26. VIDEO + AUDIO SYNC ENGINE

After video generation:

1. Validate clip duration.
2. Determine actual duration.
3. Match scene timeline.
4. Align narration.
5. Align dialogue.
6. Align SFX.
7. Align BGM.
8. Generate subtitles.
9. Apply lip-sync where required.
10. Revalidate.

If the provider produces exactly 8 seconds, use that as the default generation unit.

If provider behavior changes, capabilities configuration controls the engine.

---

# 27. GENERATION QUEUE

States:

PENDING
READY
SUBMITTED
GENERATING
COMPLETED
DOWNLOADING
DOWNLOADED
VALIDATING
VALID
AUDIO_PENDING
LIPSYNC_PENDING
FINALIZING
FAILED
RETRY
BLOCKED

All states must persist across application restarts.

---

# 28. NO DAILY LIMIT ASSUMPTION

Unlike the free-tier SnapGen version, do not build the core around a daily quota.

Instead use a generic ProviderCapacityManager.

Track:

- concurrent generation limits
- temporary rate limits
- provider errors
- session limits
- cooldowns
- generation availability

If no daily quota exists:

quota mode = NONE

If provider later introduces limits:

the provider configuration can enable them.

---

# 29. PROVIDER ABSTRACTION

Create:

VideoGenerationProvider

Methods:

authenticate()
check_session()
get_capabilities()
get_quota()
get_reference_support()
submit_generation()
get_generation_status()
download_result()
detect_error()
detect_rate_limit()
close_session()

Provider implementation:

MetaVibesProvider

Also maintain:

MockVideoProvider

The mock provider must be used for automated tests.

---

# 30. BROWSER AUTOMATION

If the provider workflow is browser-based:

Use Playwright.

Requirements:

- stable selectors
- session persistence
- login detection
- reference image upload
- prompt submission
- generation status
- download
- error detection
- rate-limit detection

Do not bypass:

- CAPTCHA
- 2FA
- account restrictions
- anti-bot protections

User authentication remains user-controlled.

---

# 31. REFERENCE IMAGE UPLOAD

The automation layer must support:

- selecting scene references
- uploading reference images
- verifying upload
- associating reference asset IDs
- submitting generation

If the provider supports only certain reference-image counts or formats, discover capabilities dynamically or store them in provider configuration.

---

# 32. DOWNLOAD MANAGER

For every clip:

- download
- verify file
- verify size
- verify duration
- verify video stream
- checksum
- metadata
- associate with scene

Never mark a clip valid before QA.

---

# 33. VIDEO QA

Validate:

- file exists
- duration
- resolution
- aspect ratio
- codec
- corruption
- black frames
- empty output
- file size
- reference consistency where automated checks are available

---

# 34. AUDIO QA

Validate:

- audio exists where expected
- duration
- sample rate
- channels
- clipping
- silence
- voice intelligibility
- BGM level
- SFX level
- sync offset

---

# 35. LIP-SYNC QA

Validate:

- speaking character identified
- dialogue exists
- mouth visible
- lip-sync output generated
- output duration matches video
- no obvious processing failure

If QA fails:

Keep original video.

Mark lip-sync as failed.

Do not destroy the source asset.

---

# 36. RETRY / REPAIR ENGINE

Do not blindly repeat generation.

Analyze failure.

Possible visual repairs:

- simplify action
- simplify camera
- reduce characters
- simplify environment
- improve reference usage
- shorten prompt

Possible audio repairs:

- adjust voice speed
- split narration
- lower BGM
- reposition SFX
- regenerate voice segment

Possible lip-sync repairs:

- crop/prepare face better
- reduce dialogue segment
- retry lip-sync
- use alternate provider

---

# 37. NICHE TEMPLATES

Support:

Drama/Romance
Horror
Finance
Stickman
Kids Stories
Animal Stories
Motivation
Comedy
Educational
History
Mystery

Each template should control:

- story structure
- pacing
- visual style
- audio style
- SFX style
- BGM style
- narration behavior
- dialogue behavior
- lip-sync frequency

---

# 38. PROJECT STRUCTURE

AI_VIDEO_FACTORY/

├── app/
│   ├── ui/
│   ├── api/
│   ├── core/
│   ├── providers/
│   ├── story/
│   ├── scenes/
│   ├── prompts/
│   ├── references/
│   ├── queue/
│   ├── audio/
│   │   ├── voice/
│   │   ├── dialogue/
│   │   ├── sfx/
│   │   ├── ambience/
│   │   ├── bgm/
│   │   └── mixer/
│   ├── lipsync/
│   ├── subtitles/
│   ├── downloader/
│   ├── qa/
│   └── assembly/
├── projects/
│   └── project_id/
│       ├── story/
│       ├── characters/
│       ├── references/
│       ├── scenes/
│       ├── prompts/
│       ├── video/
│       ├── audio/
│       ├── lipsync/
│       ├── subtitles/
│       ├── qa/
│       └── output/
├── config/
├── database/
├── logs/
├── tests/
└── README.md

---

# 39. DASHBOARD

UI should display:

- Projects
- Story
- Characters
- References
- Scenes
- Video generation
- Voiceover
- SFX
- BGM
- Lip-sync
- Subtitles
- Timeline
- QA
- Final output

Progress example:

STORY       ██████████ 100%
CHARACTERS  ██████████ 100%
REFERENCES  ██████████ 100%
VIDEO       ███████░░░ 70%
VOICE       ██████████ 100%
SFX         ████████░░ 80%
BGM         ██████████ 100%
LIPSYNC     ██████░░░░ 60%
ASSEMBLY    ░░░░░░░░░░ 0%

---

# 40. PROJECT PERSISTENCE

Store:

- project configuration
- story
- character bible
- visual bible
- reference assets
- scene plans
- prompts
- video jobs
- audio jobs
- lip-sync jobs
- subtitle jobs
- timeline
- QA results
- provider state
- final output

The application must survive restart without losing progress.

---

# 41. SECURITY

Never:

- store passwords in plaintext
- expose session cookies
- log secrets
- commit credentials
- bypass authentication

Use:

- environment variables
- secure session storage
- secret redaction
- permission controls

---

# 42. TESTING

Create tests for:

- story generation
- scene planning
- prompt compilation
- reference management
- video generation
- queue
- persistence
- voiceover
- dialogue
- SFX
- BGM
- timeline
- subtitles
- lip-sync
- audio mixing
- FFmpeg assembly
- final QA

Use MockVideoProvider.

Do not waste real generation resources during automated tests.

---

# 43. FINAL ASSEMBLY

Final assembly should:

1. Order video clips.
2. Apply lip-sync outputs where available.
3. Align voiceover.
4. Align dialogue.
5. Add SFX.
6. Add ambience.
7. Add BGM.
8. Duck BGM under speech.
9. Add subtitles.
10. Add transitions where appropriate.
11. Normalize audio.
12. Render final video.
13. Validate final output.

---

# 44. FINAL REPORT

Generate:

- project ID
- target duration
- actual duration
- scenes
- video clips
- reference images
- voice segments
- dialogue segments
- SFX
- BGM
- lip-sync jobs
- subtitle status
- failed jobs
- retries
- skipped optional jobs
- final QA
- output path

---

# 45. DEVELOPMENT RULES

Before coding:

1. Inspect repository.
2. Inspect existing architecture.
3. Do not overwrite working code blindly.
4. Create implementation plan.
5. Build modules independently.
6. Test each module.
7. Integrate incrementally.
8. Keep provider-specific code isolated.
9. Keep audio and video timelines synchronized.
10. Persist all state.
11. Use mock providers for testing.

---

# 46. ACCEPTANCE CRITERIA

The system is complete when a user can:

1. Enter a topic.
2. Select niche.
3. Select target duration.
4. Generate story.
5. Generate Character Bible.
6. Generate Visual Bible.
7. Generate reference images.
8. Generate 8-second visual clips.
9. Track every scene.
10. Generate voiceover.
11. Generate dialogue.
12. Generate SFX.
13. Add ambience.
14. Add BGM.
15. Generate subtitles.
16. Apply lip-sync to speaking characters.
17. Synchronize all media.
18. Assemble final video.
19. Run final QA.
20. Export the finished video.

---

# 47. KEY DESIGN PRINCIPLE

This version is NOT simply a video generator.

It is a complete:

AI STORY
+
VISUAL GENERATION
+
REFERENCE IMAGE
+
VOICE
+
DIALOGUE
+
SFX
+
AMBIENCE
+
BGM
+
LIP-SYNC
+
SUBTITLE
+
VIDEO EDITING
+
QA

pipeline.

The Meta AI / Vibes engine is only the visual generation provider.

The AI Video Factory remains the main orchestration system.
