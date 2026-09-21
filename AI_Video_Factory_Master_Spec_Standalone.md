# AI VIDEO FACTORY — MASTER PROJECT SPECIFICATION
## Standalone Version (Not Hermes-Specific)

### Purpose
Build a modular, free-tier-oriented AI Video Factory that converts a user's high-level request such as "Create a 10-minute horror story" into a complete video production pipeline.

The system must:
1. Accept niche/topic, duration, language, aspect ratio, quality, model, clip duration, audio/voiceover, subtitles, and visual style.
2. Generate the story.
3. Generate a Character Bible and Visual Bible.
4. Break the story into acts and scenes.
5. Optimize scenes for short text-to-video generation.
6. Compile provider-ready prompts.
7. Manage generation jobs and free-tier quotas.
8. Operate an authorized browser/provider session.
9. Download and validate generated clips.
10. Retry failed scenes using repaired prompts.
11. Pause safely when quota is exhausted.
12. Resume later without regenerating valid completed clips.
13. Assemble all valid clips with FFmpeg.
14. Produce a final video and project report.

### Important Free-Tier Rule
Do not design the system to bypass provider quotas, CAPTCHAs, 2FA, anti-bot controls, rate limits, account restrictions, or terms of service.

Multiple accounts may only be supported when the provider explicitly permits their use. Implement an Authorized Account Pool and configurable quota manager, not quota circumvention.

Never hard-code a provider limit throughout the application. Store provider limits in configuration.

---

# 1. CORE ARCHITECTURE

Recommended stack:
- Frontend: React + TypeScript
- Backend: Python + FastAPI
- Database: SQLite for V1
- Browser automation: Playwright
- Video processing: FFmpeg
- Configuration: JSON/YAML
- AI/LLM: provider abstraction
- Testing: pytest + frontend test framework
- Optional Docker

Architecture:

USER
  ↓
VIDEO FACTORY UI
  ↓
PROJECT CONFIG
  ↓
STORY ENGINE
  ↓
CHARACTER BIBLE
  ↓
VISUAL BIBLE
  ↓
SCENE PLANNER
  ↓
SCENE COMPLEXITY OPTIMIZER
  ↓
PROMPT COMPILER
  ↓
PROMPT QA
  ↓
FREE-TIER QUOTA MANAGER
  ↓
GENERATION QUEUE
  ↓
VIDEO PROVIDER ADAPTER
  ↓
DOWNLOAD MANAGER
  ↓
VIDEO QA
  ↓
RETRY / REPAIR
  ↓
FFMPEG ASSEMBLY
  ↓
FINAL VIDEO

The video provider must be an adapter. SnapGen should not be hard-coded into the entire application.

---

# 2. USER PROJECT CONFIGURATION

A project should support:

- Project name
- Niche/category
- Topic
- Target duration
- Language
- Aspect ratio
- Resolution/quality
- Video model
- Clip duration
- Visual style
- Voiceover
- Voice selection
- Subtitle option
- Background music option
- Output format
- Generation priority
- Optional/mandatory scene settings

Example:

{
  "project": "My Horror Story",
  "language": "English",
  "target_duration": 600,
  "aspect_ratio": "16:9",
  "resolution": "720p",
  "model": "veo3.1-fast",
  "clip_duration": 8,
  "input_mode": "text-to-video",
  "references": false
}

The duration engine calculates the required generation units automatically.

Example:
600 seconds / 8 seconds = 75 generation units.

Do not assume every provider supports the same durations.

---

# 3. STORY ENGINE

The story engine should create:

1. Title
2. Logline
3. Synopsis
4. Main story
5. Acts
6. Scenes
7. Narration/dialogue
8. Scene timing
9. Character involvement
10. Environment
11. Emotional progression
12. Ending

The story should be generated BEFORE scene prompts.

The system should estimate narration duration and align visual scene duration with narration timing.

---

# 4. CHARACTER BIBLE

For every important character generate:

- Name
- Age
- Gender
- Height
- Body type
- Face
- Skin tone
- Hair
- Eyes
- Clothing
- Accessories
- Props
- Personality
- Expression style
- Movement style
- Voice description
- Continuity rules

Character DNA must be available to the prompt compiler so visual identity remains consistent.

Do not use vague placeholders such as:
"[same character as before]"

When provider prompts require full context, insert the required Character DNA directly.

---

# 5. VISUAL BIBLE

Generate a project-wide Visual Bible:

- Art direction
- Rendering style
- Color behavior
- Lighting
- Camera language
- Lens/cinematic behavior
- Environment style
- Texture
- Composition
- Character rendering
- Background rendering
- Motion rules
- Negative constraints

The system must preserve the same visual identity throughout the project.

---

# 6. SCENE PLANNER

Each scene should contain:

- Scene ID
- Act
- Purpose
- Duration
- Location
- Time of day
- Characters
- Character actions
- Emotion
- Dialogue/narration
- Camera
- Lighting
- Environment
- Props
- Transition
- Prompt
- QA status
- Generation status

Supported scene types:

- HOOK
- ESTABLISHING
- CHARACTER_INTRODUCTION
- DIALOGUE
- REACTION
- ACTION
- TRANSITION
- MONTAGE
- CLIMAX
- RESOLUTION

---

# 7. SCENE COMPLEXITY OPTIMIZER

Short AI video generation becomes less reliable when a scene contains too many simultaneous actions.

Before generating a scene:

- Identify the primary action.
- Identify the primary camera movement.
- Limit unnecessary character movement.
- Prefer one main location.
- Reduce simultaneous events.
- Avoid excessive object interaction.
- Preserve important visual continuity.
- Split overloaded scenes when necessary.

Each scene receives a risk score.

Example:

LOW RISK:
One character walks through a hallway while the camera slowly follows.

MEDIUM RISK:
Two characters talk while one performs a simple action.

HIGH RISK:
Five characters fight, vehicles move, weather changes, camera rotates, and multiple objects interact.

High-risk scenes should be simplified before generation.

---

# 8. PROMPT COMPILER

Convert each scene into one complete provider-ready prompt.

The compiled prompt should combine:

- Character DNA
- Visual DNA
- Environment
- Action
- Emotion
- Camera
- Lighting
- Composition
- Props
- Motion
- Continuity requirements
- Negative constraints

Avoid unnecessary prompt complexity.

The prompt compiler should support provider-specific formatting through adapters.

---

# 9. CONTINUITY ENGINE

Track:

- Character appearance
- Clothing
- Props
- Location
- Time of day
- Weather
- Lighting
- Camera logic
- Story state
- Previous scene ending
- Next scene requirement

Before a scene is generated, compare it against the previous scene.

Flag continuity conflicts.

---

# 10. GENERATION QUEUE

Generation job states:

PENDING
READY
SUBMITTED
GENERATING
COMPLETED
DOWNLOADING
DOWNLOADED
VALIDATING
VALID
FAILED
RETRY
BLOCKED
QUOTA_WAIT

Jobs must survive application restarts.

Completed valid scenes must never be regenerated automatically.

---

# 11. FREE-TIER QUOTA MANAGER

Provider configuration must define:

- Daily generation limit
- Clip duration limits
- Resolution limits
- Model limits
- Reset behavior
- Account restrictions
- Concurrent generation limit

The manager tracks:

- Account
- Provider
- Used quota
- Remaining quota
- Reset time
- Last generation
- Current status

When quota is exhausted:

1. Stop generation.
2. Mark jobs QUOTA_WAIT.
3. Save state.
4. Display reason.
5. Wait until the configured reset condition.
6. Resume only when permitted.

Never attempt to defeat a quota.

---

# 12. AUTHORIZED ACCOUNT POOL

If the provider permits multiple accounts, support:

- Account registration
- Account status
- Authorized session state
- Quota state
- Cooldown
- Error count
- Last use
- Provider permissions

Authentication should remain user-controlled.

Do not automate CAPTCHA solving.

Do not bypass 2FA.

Do not store passwords in plaintext.

Use secure session storage.

---

# 13. PROVIDER INTERFACE

Create a generic interface such as:

VideoGenerationProvider

Required operations:

- authenticate()
- check_session()
- get_capabilities()
- get_quota()
- submit_generation()
- get_generation_status()
- download_result()
- detect_error()
- detect_quota_exhaustion()
- close_session()

Implement:

MockVideoProvider
SnapGenProvider

The mock provider must be used for development and testing.

Never waste real free-tier generations during automated tests.

---

# 14. BROWSER AUTOMATION

Use Playwright.

Requirements:

- Stable selectors
- Semantic selectors where possible
- Avoid coordinate-based clicking
- Detect login state
- Detect generation state
- Detect errors
- Detect quota messages
- Detect downloadable result
- Recover from page reloads
- Preserve session state securely

The system must stop and request user intervention when authentication, 2FA, CAPTCHA, or other human verification is required.

---

# 15. DOWNLOAD MANAGER

For each generated video:

- Download
- Verify file exists
- Verify file size
- Verify readable video stream
- Record checksum
- Store metadata
- Associate with scene ID

Never mark a scene valid until the file passes validation.

---

# 16. VIDEO QA

Validate:

- File exists
- Duration
- Resolution
- Aspect ratio
- Codec
- Container
- Corruption
- Audio if expected
- Black frames
- Empty output
- Minimum file size

QA result should contain:

- status
- severity
- issue
- recommendation
- timestamp

---

# 17. RETRY / REPAIR ENGINE

Do not blindly regenerate failed scenes.

Analyze the failure.

Possible repairs:

- simplify action
- reduce characters
- simplify camera movement
- remove conflicting instructions
- shorten prompt
- fix continuity
- reduce visual complexity

Retry limits must be configurable.

---

# 18. MANDATORY VS OPTIONAL SCENES

Every scene may be:

MANDATORY
OPTIONAL

If an optional scene repeatedly fails, the system may skip it and continue.

If a mandatory scene fails beyond the retry limit, the project should pause and report the problem.

---

# 19. FFmpeg ASSEMBLY

The assembly engine should:

1. Sort clips by scene order.
2. Validate compatibility.
3. Normalize when required.
4. Concatenate clips.
5. Add narration.
6. Add background music.
7. Mix audio.
8. Add subtitles.
9. Render final video.
10. Validate final output.

Keep intermediate files.

Generate a final project report.

---

# 20. NICHE TEMPLATE SYSTEM

Templates must be modular.

Initial templates:

### Drama / Romance
Hook → Meet → Relationship → Conflict → Separation → Climax → Resolution

### Horror
Normal World → Strange Event → Investigation → Escalation → Reveal → Climax → Ending

### Finance
Hook → Problem → Explanation → Example → Mistake → Solution → CTA

### Stickman
Simple characters → Simple backgrounds → Simple movement → Exaggerated actions

### Kids Stories
Original characters → Simple story → Clear conflict → Safe resolution

### Animal Stories
Animal protagonist → Problem → Adventure → Resolution

### Motivation
Problem → Struggle → Turning Point → Lesson → Action

### Comedy
Setup → Misunderstanding → Escalation → Punchline → Resolution

### Educational
Question → Explanation → Demonstration → Example → Summary

### History
Context → Event → Development → Consequence → Summary

### Mystery
Question → Clues → Investigation → Reveal → Resolution

New niche templates must be addable without modifying the core engine.

---

# 21. PROJECT PERSISTENCE

Store:

- project.json
- story
- characters
- visual bible
- scenes
- prompts
- jobs
- QA results
- quota state
- provider state
- downloaded videos
- final output
- logs

Suggested structure:

AI_VIDEO_FACTORY/
├── app/
│   ├── ui/
│   ├── api/
│   ├── core/
│   ├── providers/
│   ├── story/
│   ├── scenes/
│   ├── prompts/
│   ├── queue/
│   ├── accounts/
│   ├── quota/
│   ├── downloader/
│   ├── qa/
│   └── assembly/
├── projects/
├── config/
├── database/
├── logs/
├── tests/
└── README.md

---

# 22. DASHBOARD

The UI should display:

- Projects
- Create project
- Current project
- Story
- Characters
- Scenes
- Prompts
- Generation progress
- Queue
- Quota
- Provider/account status
- Failed scenes
- QA results
- Final video
- Logs

Scene table should show:

Scene | Duration | Prompt | Status | QA | Retry | Video

---

# 23. SECURITY

Never:

- store passwords in plaintext
- expose session cookies in UI
- log secrets
- commit credentials
- bypass authentication controls
- bypass provider restrictions

Use:

- environment variables
- secure session storage
- secret redaction
- permission checks
- safe logging

---

# 24. TESTING

Create:

- unit tests
- integration tests
- provider mock tests
- queue tests
- quota tests
- persistence tests
- prompt compiler tests
- scene optimizer tests
- video QA tests
- FFmpeg tests
- browser automation tests using mock/staging behavior where possible

Test failures including:

- network interruption
- browser crash
- provider error
- quota exhaustion
- invalid download
- corrupt video
- application restart
- partial project completion

---

# 25. FINAL REPORT

Generate:

- Project ID
- Target duration
- Actual duration
- Number of scenes
- Number of generation units
- Successful generations
- Failed generations
- Retries
- Skipped optional scenes
- Quota usage
- Total clips
- Final video path
- QA status
- Errors
- Warnings

---

# 26. DEVELOPMENT RULES

Before coding:

1. Inspect the existing repository.
2. Identify current architecture.
3. Do not overwrite working code blindly.
4. Produce a technical implementation plan.
5. Implement incrementally.
6. Test each module.
7. Integrate only after module tests pass.
8. Keep provider-specific code isolated.
9. Avoid hard-coded provider limits.
10. Keep all project state persistent.
11. Prefer simple reliable implementations over unnecessary complexity.

---

# 27. ACCEPTANCE CRITERIA

The system is considered functional when a user can:

1. Create a project.
2. Select a niche.
3. Enter a topic.
4. Select duration.
5. Generate a story.
6. Generate character and visual bibles.
7. Generate a complete scene plan.
8. Generate provider-ready prompts.
9. Queue generation.
10. Track quota.
11. Generate clips through an authorized provider session.
12. Download clips.
13. Validate clips.
14. Retry failed scenes with optimized prompts.
15. Pause on quota exhaustion.
16. Resume later.
17. Assemble the final video.
18. Review QA.
19. Export the final video.

The implementation should be modular enough to add other video providers later.
