# Codize V2 Character System Blueprint

## Status

**Document purpose:** Canonical visual, animation, customization, and unlock blueprint for the Codize V2 character system.

**Scope:** This document defines how **every Codize character** should be designed and produced. It intentionally does **not** lock the exact species-specific design of future characters. Instead, it defines the shared blueprint each base character must follow so that new characters can be added without changing Codize’s UX, teaching model, animation system, or accessory architecture.

**Starter character:** `Codybara` is the default starter character. Codybara should begin with a deliberately simple base appearance and little or no equipped customization so that accessories earned or selected later feel meaningful.

**Related authority:** The Codize V2 Product Thesis and Exact UX Specification govern how the conversational AI behaves, teaches, scaffolds, responds, and uses the character in the interface. This document does **not** redefine those teaching rules. It defines the **visual character system that expresses them**. The approved Figma controls current layout/composition: https://www.figma.com/design/QBGSdTLG7iQ2xEFzU7v0Li/Codize-V2-Product-Design

**Current navigation decision:** Character switching/customization is a dedicated secondary `Character` destination above Settings. Settings contains presentation controls such as sound/animation/reduced motion; it does not own character selection.

---

# 1. Character System Thesis

Codize characters should make the product feel:

- welcoming to beginners;
- memorable;
- alive;
- playful without becoming childish;
- lightly game-like without turning the learning experience into a reward treadmill;
- emotionally readable without becoming distracting;
- distinct from generic AI assistant products;
- coherent with Codize’s beginner-first, project-based learning experience.

The character is the **face of Codize’s mentor**, not the source of the product’s intelligence.

The underlying Codize system still determines:

- what the student is currently doing;
- what Codize knows;
- when the student should think;
- when Codize should teach;
- when Codize should provide a hint;
- when Codize should stay quiet;
- what project evidence exists;
- what learner support is appropriate.

The character visually communicates that state.

The character system should therefore follow one central rule:

> **The character adds warmth, clarity, identity, and reward to Codize without becoming the thing the student is trying to please.**

The student should care about building and learning.

The character makes that experience more enjoyable.

---

# 2. Core Character-System Principles

## 2.1 Every character is cosmetic, not pedagogically stronger

Unlocking a new character must never grant:

- better AI answers;
- different access to learning features;
- stronger hints;
- easier verification;
- higher scores;
- hidden advantages;
- faster project progression.

Characters may have different visual personalities, animation styles, and aesthetic flavor, but the **same Codize teaching rules apply underneath all of them**.

A student choosing one character over another is choosing:

> “Which companion do I want with me?”

not:

> “Which character gives me the best abilities?”

---

## 2.2 The character is a companion, not the coder

Character design should reinforce the role:

> guide, mentor, observer, thinking partner

and should avoid implying:

> magical code generator, autonomous engineer, omniscient AI, superhero that builds the project for you.

The character should look like it is:

- listening;
- thinking;
- observing;
- explaining;
- reacting;
- celebrating;
- helping the user slow down and reason.

It should **not** constantly be shown furiously typing entire applications.

---

## 2.3 The system is inspired by classic pixel dialogue, not copied from a specific game

The aesthetic can take inspiration from:

- classic pixel-art RPG dialogue;
- expressive sprite portraits;
- limited animation;
- retro interface charm;
- text-blip speech systems;
- simple readable silhouettes.

However, Codize should develop its own:

- character proportions;
- sprite language;
- animation style;
- UI framing;
- sound identity;
- palette system;
- dialogue presentation.

Do not directly copy Undertale characters, sprites, animations, fonts, or sounds.

---

## 2.4 Every character must work at small sizes

Codize characters will often appear beside conversation text.

Therefore the base character cannot depend on:

- tiny costume details;
- complex facial features;
- high-frequency textures;
- intricate patterns;
- many small colors;
- subtle gradients.

The character should remain recognizable when displayed as a small sprite.

The silhouette should do most of the identity work.

---

## 2.5 Accessories should enhance a character, not complete it

Every base character must already feel finished and recognizable with **zero accessories equipped**.

Accessories are additive.

Bad model:

```text
base character
=
unfinished blank body

+
accessories
=
actual character
```

Correct model:

```text
base character
=
complete recognizable mascot

+
accessories
=
personalization and earned expression
```

---

# 3. Character Progression Model

The character system has three layers.

## Layer 1 — Starter character

The user begins with:

> **Codybara**

Codybara should use the standard base-character blueprint and begin with:

- the core body design;
- the core palette;
- standard facial features;
- all required base animations;
- zero or very few starter accessories.

The user should immediately feel that Codybara is a real character, while also seeing clear room for future customization.

The starter should not look “poor,” “low rarity,” or intentionally inferior.

It is the **canonical starting companion**, not the weak character.

---

## Layer 2 — Accessories

Accessories can be:

- available by default;
- unlocked through meaningful achievements;
- unlocked through major project milestones;
- unlocked through demonstrated independent habits;
- granted for special product events later if appropriate.

Accessories should give the user more ownership over the character without changing Codize’s educational behavior.

---

## Layer 3 — New characters

New characters should be rarer and more meaningful than accessories.

A new character should normally represent:

- sustained use;
- a meaningful project milestone;
- a major learning milestone;
- a significant achievement;
- completing a major build;
- demonstrating an important habit independently several times.

The player should not unlock a brand-new character every few minutes.

Characters should feel substantial.

---

# 4. Universal Base Character Blueprint

Every Codize character should be designed from the following blueprint.

---

# 4.1 Species

Each character should be based primarily on **one clearly recognizable animal**.

The animal should:

- have a readable silhouette;
- support expressive pixel animation;
- be recognizable at small size;
- have a natural personality association that can complement Codize;
- remain visually appealing without accessories;
- be distinct from existing Codize characters.

Possible broad animal families include:

- mammals;
- birds;
- reptiles;
- amphibians;
- aquatic animals;
- insects or arthropods when they remain friendly/readable;
- unusual animals that create memorable silhouettes.

Do not require every character to be traditionally “cute.”

Some can feel:

- clever;
- sleepy;
- curious;
- focused;
- energetic;
- quirky;
- stoic.

However, no character should feel threatening or hostile in the normal mentor role.

---

# 4.2 Name

Every character should have a name that combines:

> **animal identity + coding / software / computing reference**

The naming should be:

- easy to pronounce;
- short enough to remember;
- understandable even if the pun is not immediately obvious;
- distinct from other characters;
- playful without becoming painfully forced.

`Codybara` establishes the general naming spirit.

Future character naming should not force a bad coding pun merely to follow a formula.

A strong name is more important than perfect consistency.

---

# 4.3 Silhouette

The silhouette is one of the most important design requirements.

Each character needs:

### One dominant body shape

Examples of shape language:

- rounded;
- long;
- triangular;
- tall;
- squat;
- wide;
- compact;
- winged;
- tail-dominant.

### One or two signature silhouette features

Examples:

- ears;
- tail;
- horns;
- wings;
- long neck;
- shell;
- large cheeks;
- distinctive snout;
- unusual body posture.

A character should be identifiable from a filled-black silhouette alone.

### Silhouette test

Before finalizing a character:

1. remove color;
2. remove facial details;
3. remove accessories;
4. fill the entire sprite with one color;
5. compare it with existing characters.

If it is difficult to tell which character it is, the base design needs stronger shape identity.

---

# 4.4 Proportions

Codize characters should use a consistent family of proportions without forcing every species into the exact same body.

General target:

```text
head:
large enough for readable expression

body:
compact enough for chat placement

limbs:
simplified

face:
high visual priority

accessory zones:
intentionally preserved
```

The head should usually occupy roughly:

> **35–55% of the perceived sprite height**

depending on the species.

This is not a hard mathematical rule.

The purpose is to keep facial expressions readable in conversation.

---

# 4.5 Face

Every character needs a face that works with minimal pixels.

Required expressive elements:

- eyes;
- mouth or equivalent expression mechanism;
- optional eyebrows / brow pixels;
- optional cheeks;
- species-specific expressive feature where useful.

The face must support at minimum:

- neutral;
- attentive;
- talking;
- thinking;
- happy / affirming;
- concerned;
- focused;
- confused / uncertain.

Avoid hyper-detailed anime-style facial animation.

The charm should come from a small number of carefully chosen pixels.

---

# 4.6 Default orientation

Each character should have one canonical conversation orientation.

Recommended:

> **three-quarter front view**

This gives enough visibility for:

- facial expression;
- body language;
- accessories;
- directional head movement.

A pure side profile can make dialogue less personable.

A completely flat front view can make movement stiff.

Species may justify exceptions.

---

# 4.7 Default posture

Base posture should communicate:

> **relaxed attention**

The character should look like it is ready to:

- listen;
- respond;
- think;
- guide.

Avoid a permanent action pose.

Avoid permanent excitement.

Avoid crossed arms or body language that can read as judgmental.

---

# 5. Pixel-Art Aesthetic

## 5.1 General visual language

Characters should use:

- crisp pixel edges;
- deliberate pixel clusters;
- limited anti-aliasing;
- no blurry raster scaling;
- no pseudo-pixel filter applied to normal illustrations;
- strong readable color blocks;
- restrained shading;
- consistent outline logic.

The art should look like it was **designed as pixel art**, not converted into pixel art afterward.

---

## 5.2 Native sprite size

Choose one shared native production size for the character system.

Recommended working target:

> **32 × 32 px base conversation sprite canvas**

with some characters allowed to occupy less than the entire canvas.

For larger expressive scenes, an optional:

> **64 × 64 px high-detail sprite**

may exist.

The final design system should choose one production standard and keep it consistent.

### Important

Characters should be displayed at integer scaling factors when possible:

```text
32px native
→ 128px
→ 96px
→ 128px
```

Avoid fractional scaling that produces soft pixel edges.

---

# 5.3 Outline system

Choose a consistent outline system for all characters.

Recommended:

- dark colored outline rather than absolute black;
- 1 px native outline on important exterior edges;
- selective interior outlines;
- no outlining every tiny interior region.

The outline color can vary slightly by character palette while remaining within the Codize family.

---

# 5.4 Shading

Use simple pixel shading.

Recommended:

```text
base color
+
one shadow tone
+
one highlight tone
```

Not every area needs all three.

Avoid complex rendered lighting.

Codize character lighting should remain stable across UI surfaces unless a special illustration intentionally changes the scene.

---

# 5.5 Palette

Every base character should have:

### Core palette

Approximately:

- 2–4 body colors;
- 1 outline color;
- 1–2 facial/detail colors;
- optional small accent color.

A base character generally should not require more than roughly **6–9 active colors** before accessories.

This keeps sprites readable and makes accessories easier to integrate.

---

# 6. Character Personality Blueprint

This document does not replace the Codize Teaching Policy.

Character personality is **presentation flavor**, not a different teaching engine.

Every character should share the fundamental Codize mentor traits:

- patient;
- curious;
- non-judgmental;
- attentive;
- encouraging;
- thoughtful;
- capable;
- willing to admit uncertainty;
- focused on helping the student think.

Each individual character may then emphasize **one or two flavor traits**.

Examples of allowable flavor dimensions:

```text
calm ↔ energetic
reserved ↔ expressive
dry humor ↔ openly playful
methodical ↔ curious
soft-spoken ↔ enthusiastic
```

The variation should affect:

- facial expressions;
- idle animation style;
- celebration animation;
- tiny flavor lines where allowed;
- visual posture.

It must **not** change:

- truthfulness;
- teaching rules;
- amount of required reasoning;
- project access;
- safety rules;
- learning requirements.

---

# 7. Required Animation Set

Every character released into Codize must ship with a complete baseline animation pack.

A character is not complete if it only has one idle sprite.

---

# 7.1 Animation A — Neutral Idle

## Purpose

Default state when Codize is present but not actively talking.

## Emotional meaning

> “I’m here.”

## Suggested motion

Choose species-appropriate subtle movement such as:

- breathing;
- blinking;
- ear twitch;
- tail movement;
- feather movement;
- small sway;
- tiny posture shift.

## Loop length

Recommended:

> **2.0–4.0 seconds**

Avoid obvious repetitive bouncing every half-second.

## Frames

Recommended:

> **4–8 unique frames**

depending on the motion style.

## Important

Idle should be visually calm enough that it can remain on screen for several minutes without becoming annoying.

---

# 7.2 Animation B — Waiting for Student Answer

## Purpose

Used after Codize asks a question and the student is deciding what to say.

This should be distinguishable from passive neutral idle.

## Emotional meaning

> “Take your time. I’m listening.”

## Possible motion

- attentive blink;
- slight head tilt;
- ears orient toward the input;
- subtle lean;
- tail resting;
- occasional tiny glance toward the input area.

## Avoid

- tapping impatiently;
- looking annoyed;
- checking a watch;
- exaggerated sighing;
- anything that pressures the student.

## Loop

Recommended:

> **3–6 seconds**

with subtle randomized pauses where technically practical.

---

# 7.3 Animation C — Talking

## Purpose

Used while Codize dialogue is appearing.

## Emotional meaning

> “I’m speaking.”

## Motion

Could include:

- mouth movement;
- subtle head bounce;
- tiny body movement;
- occasional blink;
- species-specific speaking gesture.

The mouth does not need to match phonemes.

This is not lip synchronization.

## Timing

Talking animation should continue only while text is being revealed or the speech state is active.

When dialogue finishes:

```text
talking
→ brief settle
→ waiting/idle
```

## Audio relationship

The optional Codize text-blip sound should align with the dialogue reveal system, not necessarily every mouth frame.

---

# 7.4 Animation D — Thinking

## Purpose

Used when Codize is:

- analyzing project context;
- processing a repository change;
- preparing a response;
- deciding the next instructional action;
- loading information where a character state is appropriate.

## Emotional meaning

> “I’m considering this.”

## Motion ideas

Species-specific possibilities:

- looking upward;
- paw/chin gesture;
- ears shift;
- eyes track;
- slow tilt;
- floating pixel ellipsis;
- small orbiting cursor/spark;
- tail pauses then moves.

## Loop length

Recommended:

> **1.5–3 seconds**

## Important UX rule

Thinking animation must not falsely imply that an operation will finish instantly.

For longer operations, pair it with honest progress/loading UI.

---

# 7.5 Animation E — Positive Confirmation

## Purpose

Used after a genuinely useful student action or realization.

Examples:

- student improves an overly broad request;
- student identifies an unexpected change;
- student proposes a useful test;
- student correctly explains a causal relationship.

## Emotional meaning

> “Yes. That thinking is useful.”

## Motion

Possible:

- small nod;
- quick smile;
- tiny hop;
- ear perk;
- subtle sparkle;
- tail motion.

## Duration

Recommended:

> **0.6–1.5 seconds**

Usually play once rather than loop indefinitely.

## Important

Do not fire this animation after every button click.

Reserve it for meaningful moments.

---

# 7.6 Animation F — Concern / Caution

## Purpose

Used when Codize is signaling:

- the requested change is becoming too broad;
- the student is about to combine several risky systems;
- something changed unexpectedly;
- a high-risk area needs more thought;
- blind reprompting is beginning.

## Emotional meaning

> “Something here deserves attention.”

## Motion

Possible:

- ears lower slightly;
- expression narrows;
- small head tilt;
- posture becomes more focused;
- tiny alert mark;
- brief pause.

## Avoid

- angry expression;
- scolding;
- dramatic alarm;
- red flashing;
- making the student feel punished.

---

# 7.7 Animation G — Uncertain / “Let’s Inspect”

## Purpose

Used when Codize does not know something conclusively.

Examples:

- repository evidence is incomplete;
- Codize sees an unexpected change but cannot determine intent;
- the student says they do not know;
- a result is ambiguous.

## Emotional meaning

> “We don’t know yet.”

This animation is especially important because uncertainty is a core Codize product value.

## Motion

Possible:

- head tilt;
- asymmetric ears;
- small question-mark bubble;
- eyes shifting toward evidence;
- gentle shrug-like motion.

The visual should communicate curiosity, not failure.

---

# 7.8 Animation H — Recovery Focus

## Purpose

Used when the user enters **Something broke** / Recovery Mode.

## Emotional meaning

> “Okay. Let’s work through this.”

## Visual difference

The character becomes slightly more focused than normal.

Possible:

- posture sits/stands straighter;
- eyes more attentive;
- idle animation becomes less playful;
- tool/accessory may subtly change only if universally available;
- expression becomes calm and concentrated.

## Important

Do not transform the character into a different “battle mode.”

Recovery is not combat.

It is investigation.

---

# 7.9 Animation I — Celebration

## Purpose

For major accomplishments.

Examples:

- first working feature;
- first V1 completion;
- major independent debugging success;
- significant achievement unlock;
- new character unlock.

## Motion

More expressive than ordinary confirmation.

Possible:

- larger hop;
- spin;
- confetti pixels;
- enthusiastic tail/wing movement;
- brief character-specific pose.

## Duration

Recommended:

> **1–3 seconds**

## Frequency

Rare.

Celebration loses meaning if used constantly.

---

# 7.10 Animation J — Unlock Reveal

## Purpose

Used when:

- a new accessory is earned;
- a new character is unlocked.

## Structure

Recommended:

```text
character reacts
↓
unlock item appears
↓
short reveal effect
↓
item name / achievement reason
↓
Equip now / Later
```

The reveal should be fun but fast.

Never block the user for a long animation.

---

# 7.11 Animation K — Enter / Exit

Optional but strongly recommended.

Used when:

- Build conversation begins;
- character appears in onboarding;
- switching characters;
- opening a major mentor surface.

Keep this very short.

Example:

```text
2–5 frames
0.25–0.6 sec
```

Avoid elaborate transitions every time a route changes.

---

# 8. Animation State Machine

The system should not trigger animations randomly without semantic state.

Conceptual state model:

```text
OFFSCREEN
    ↓
ENTER
    ↓
IDLE
    ├── user question asked → WAITING
    ├── Codize speaking → TALKING
    ├── response generation → THINKING
    ├── meaningful success → POSITIVE
    ├── caution condition → CONCERN
    ├── uncertainty → UNCERTAIN
    ├── recovery mode → RECOVERY_FOCUS
    └── major milestone → CELEBRATION
```

Temporary states return to the correct persistent state afterward.

Example:

```text
WAITING
↓
student submits
↓
THINKING
↓
TALKING
↓
WAITING
```

This behavior should be defined by product state, not by the language model inventing animation commands in free text.

---

# 9. Animation Personality Variation

All characters use the same semantic animation states.

However, the motion can be species-specific.

For example, a generic `thinking` state could be expressed differently:

```text
Character A
tilts head and flicks ear

Character B
tucks wings and looks upward

Character C
slowly sways tail while eyes move

Character D
briefly retracts into shell and peeks out
```

The **meaning stays identical**.

The expression differs.

This gives characters identity without creating different product behavior.

---

# 10. Reduced Motion

Every animation must have a reduced-motion equivalent.

When reduced motion is enabled:

### Replace loops with

- mostly static poses;
- occasional blink if appropriate;
- simple expression swaps;
- opacity changes only where safe;
- no repeated bouncing or large movement.

### Thinking

Instead of a moving body:

```text
static thinking pose
+
subtle ellipsis indicator
```

### Talking

Could use:

```text
two-frame mouth/expression change
```

or static pose while text appears.

### Celebration

Use a quick static expression + small non-moving badge.

The character must remain understandable without animation.

---

# 11. Accessory System

Accessories are a major part of the character progression system.

The system must be designed **before** characters are drawn so later accessories do not require redrawing every sprite from scratch.

---

# 11.1 Accessory philosophy

Accessories should represent:

- personalization;
- playful identity;
- meaningful progress;
- achievements;
- memorable project milestones.

They should not represent:

- educational power;
- competitive advantage;
- pay-to-win;
- fake skill rank.

---

# 11.2 Accessory slots

Recommended universal slot system:

### HEAD

Examples:

- hats;
- headbands;
- crowns;
- beanies;
- headphones;
- small helmets.

### FACE

Examples:

- glasses;
- goggles;
- tiny cosmetic face details.

### NECK

Examples:

- scarf;
- tie;
- collar accessory;
- medal.

### BODY

Examples:

- hoodie;
- jacket;
- vest;
- shirt overlay;
- cape attachment when compatible.

### BACK

Examples:

- backpack;
- small wings as cosmetic accessory only;
- code-themed pack;
- decorative object.

### HELD / PAW / HAND

Examples:

- notebook;
- pencil;
- tiny keyboard;
- mug;
- debugging magnifier;
- book.

Not every species will support a held-item slot.

### EFFECT

Examples:

- small pixel sparkles;
- tiny orbiting cursor;
- subtle code particles;
- achievement aura.

Effects should remain restrained in chat.

---

# 11.3 Accessory slot compatibility

Not every accessory must fit every character.

Each accessory should declare:

```text
supported slots
supported characters
anchor profile
layer
animation compatibility
```

Prefer designing many accessories to work across several characters.

But do not distort an animal’s anatomy simply to make a hat fit.

---

# 11.4 Accessory anchor points

Every character sprite should define stable anchor points.

Conceptual anchor set:

```text
HEAD_CENTER
HEAD_TOP
FACE_CENTER
LEFT_EAR
RIGHT_EAR
NECK_CENTER
BODY_CENTER
BACK_CENTER
LEFT_HAND_OR_PAW
RIGHT_HAND_OR_PAW
GROUND_CENTER
EFFECT_ORIGIN
```

Not every character uses every anchor.

Accessories attach to these anchors rather than arbitrary coordinates.

Animation frames must preserve anchor consistency.

---

# 11.5 Layering

Recommended sprite layering:

```text
BACK_EFFECT
BACK_ACCESSORY
BASE_CHARACTER_BACK
BASE_CHARACTER
BODY_ACCESSORY
NECK_ACCESSORY
FACE_ACCESSORY
HEAD_ACCESSORY
HELD_ITEM
FRONT_EFFECT
```

Species-specific exceptions can exist.

Layer order must be documented for every character.

---

# 11.6 Accessory-safe design zones

Every base character should intentionally leave visual breathing room around likely accessory areas.

For example:

- head silhouette should support at least some headwear;
- face should have room for glasses where anatomically reasonable;
- neck/body transition should allow scarf/collar layers;
- held-item characters should have a clear hand/paw anchor.

Do not design a base character so overloaded with permanent detail that accessories become unreadable.

---

# 11.7 Starter accessory policy

Codybara should begin visually minimal.

Recommended starter state:

```text
Base Codybara
+
0 or 1 very small default identity element
```

Do not equip multiple achievement-style accessories at first launch.

The starting character should visually communicate:

> “This is yours to grow.”

without looking unfinished.

---

# 12. Unlock Philosophy

Codize should reward **meaningful progress**, not product compliance.

Good unlock triggers include:

- completing a real project milestone;
- finishing a first V1;
- independently catching an unexpected AI change;
- proposing a useful test before Codize asks;
- debugging through investigation instead of blind patching;
- demonstrating a learned habit independently multiple times;
- connecting a project checkpoint to Git history;
- transferring a concept to a new task;
- completing a meaningful recovery.

Avoid rewards for:

- opening the app every day;
- clicking through required forms;
- submitting empty/low-effort responses;
- spending arbitrary amounts of time in Codize;
- maintaining a daily streak;
- simply clicking “Continue” many times.

---

# 12.1 Accessory unlock scale

Accessories should be relatively common.

Example cadence:

```text
small meaningful achievement
→ accessory

larger milestone
→ special accessory / effect

major sustained milestone
→ character
```

---

# 12.2 Character unlock scale

New characters should require something more substantial than ordinary accessories.

Possible categories:

### Project milestone

Example:

> complete a first usable V1.

### Independence milestone

Example:

> repeatedly demonstrate important habits without prompts.

### Recovery milestone

Example:

> successfully diagnose multiple bugs through evidence-first recovery.

### Transfer milestone

Example:

> apply previously learned reasoning in a different project context.

The exact achievements can be defined later.

---

# 13. Character Unlock Presentation

When a new character is unlocked:

```text
[celebration animation]

NEW COMPANION UNLOCKED

[Character silhouette → reveal]

Character Name

Unlocked because:
[plain-language achievement reason]

[Use this character]

[Keep current character]
```

Do not frame another character as objectively “better.”

Avoid:

```text
Epic
Legendary
Mythic
+20 Intelligence
```

unless Codize later deliberately adopts a collectible-rarity system. The current product thesis does not require one.

---

# 14. Accessory Unlock Presentation

Accessory unlock:

```text
NEW ACCESSORY

[item preview]

Unlocked for:
Caught an unexpected change before Codize pointed it out.

[Equip]

[Later]
```

The reason should connect the cosmetic reward to a real accomplishment.

---

# 15. Dedicated Character Customization Destination

Character customization lives in its own signed-in destination rather than inside Settings.

Conceptual navigation:

```text
Project
Build
Learning
History

Character
Settings
```

Possible Character page structure:

```text
CHARACTER

Current companion
[Codybara preview]

Characters
[selector grid]

Accessories
[customize]
```

Settings separately owns:

```text
Dialogue sounds      ON / OFF
Character animations ON / REDUCED
Reduced motion       SYSTEM / ON / OFF
```

## 15.1 Character selector

Character grid:

```text
Codybara
Selected

Character B
Unlocked

Character C
Locked
Complete: [achievement description]

Character D
Locked
???
```

Some future characters can remain mystery silhouettes until unlocked if that feels fun. However, if an unlock requirement is important for motivation, show it clearly.

## 15.2 Character preview

Selecting a character before confirming should open a preview. Preview should demonstrate:

- neutral idle;
- talking;
- thinking;
- success.

## 15.3 Accessory customization

Customization surface:

```text
[large character preview]

HEAD
[ accessory grid ]

FACE
[ accessory grid ]

NECK
[ accessory grid ]

BODY
[ accessory grid ]

BACK
[ accessory grid ]

HELD
[ accessory grid ]

EFFECT
[ accessory grid ]

[Save]
```

Changing an accessory updates the preview immediately.

## 15.4 Accessory limits

To prevent visual clutter:

- one accessory per physical slot;
- maximum one effect;
- optional global maximum of roughly 3–5 visible accessories at once.

The exact limit can be tested visually. A user should not be able to turn the character into an unreadable pile of overlapping cosmetics.

---

# 16. Character Presence Across Codize

The character should not occupy the same amount of space everywhere.

---

## Landing Page

Presence:

> **Large / defining**

Purpose:

- establish brand;
- communicate personality;
- demonstrate conversation;
- visually explain project-growth + student-growth thesis.

---

## First-Time Onboarding

Presence:

> **Large to medium**

Purpose:

- make first interaction feel welcoming;
- guide project idea capture;
- introduce Codize as a companion.

---

## Build Conversation

Presence:

> **Medium / persistent**

This is the main character environment.

The character should:

- talk;
- wait;
- think;
- react;
- guide.

---

## Recovery Mode

Presence:

> **Medium / emotionally important**

The character can use the recovery-focused state.

---

## Project Home

Presence:

> **Small / contextual**

Possible:

- small greeting;
- current companion near “Up Next”;
- brief reaction.

Do not let the mascot compete with the primary next action.

---

## Learning Screen

Presence:

> **Medium**

Useful for:

- celebrating learning milestones;
- viewing unlocks;
- character progression.

---

## History

Presence:

> **Minimal**

History information should dominate.

---

## Character destination

Presence:

> **Large inside customization preview**

This is the primary home for character switching and accessories.

## Settings

Presence:

> **Minimal / none**

Settings contains presentation controls, not the character customization workspace.

---

# 17. Character Dialogue Sound

The character system can use an original retro text-blip sound.

The sound is tied to the **character dialogue system**, not general interface clicks.

## Required settings

```text
Dialogue sounds: ON / OFF
```

Potential future option:

```text
Dialogue sound volume
```

## Sound behavior

The sound should:

- be subtle;
- be short;
- support the pixel character identity;
- stop when text is skipped/revealed instantly;
- not fire continuously during very long technical blocks;
- respect mute preferences.

Different characters may eventually have slightly different **original** text-blip timbres.

If implemented:

- all must remain quiet and non-annoying;
- the difference should be personality flavor, not readability impact.

---

# 18. Character-Specific Audio Variation

Optional later system.

Each character could define:

```text
speech_blip_family
pitch_range
variation_count
```

Example conceptual behavior:

```text
Character A:
soft low blips

Character B:
lighter short blips

Character C:
slightly mechanical chirps
```

Do not make characters speak full voiced dialogue by default.

The pixel text sound preserves the user’s reading speed and keeps production manageable.

---

# 19. Character Visual Reactions Must Follow Product Truth

Character expression should never imply stronger certainty than Codize has.

Bad:

```text
huge victory animation
"Perfect!"
```

when a student has merely saved a prompt.

Better:

```text
small nod
"That request is much more specific."
```

Major celebration should follow a major known milestone.

Likewise, if Codize is uncertain:

- use uncertain/thinking expression;
- do not use confident success expression.

Visual tone must align with product truth.

---

# 20. Character Asset Package

Every released character should ship with the same structured asset package.

Recommended conceptual directory:

```text
characters/
  <character_id>/
    character.json

    base/
      neutral.png
      palette.png

    animations/
      enter/
      idle/
      waiting/
      talking/
      thinking/
      positive/
      concern/
      uncertain/
      recovery/
      celebration/
      unlock/

    accessories/
      anchors.json
      compatibility.json

    previews/
      portrait.png
      selector.png
      silhouette.png
```

Exact implementation format can change.

The important part is consistent organization.

---

# 21. Character Metadata Blueprint

Every character should eventually have structured metadata.

Conceptual example:

```json
{
  "id": "character_id",
  "display_name": "Character Name",
  "species": "animal species",
  "unlock_type": "starter | achievement | milestone",
  "unlock_key": "optional_unlock_key",
  "palette_id": "palette_name",
  "default_animation": "idle",
  "supported_accessory_slots": [
    "head",
    "face",
    "neck",
    "body",
    "back",
    "held",
    "effect"
  ],
  "anchor_profile": "character_id_v1",
  "speech_blip_profile": "default",
  "reduced_motion_profile": "character_id_reduced"
}
```

The client should not determine achievement eligibility from this cosmetic metadata alone.

Unlock authority should come from the appropriate product state.

---

# 22. Animation Metadata Blueprint

Conceptual:

```json
{
  "animation": "thinking",
  "loop": true,
  "fps": 6,
  "frames": 8,
  "duration_ms": 2200,
  "reduced_motion_asset": "thinking_static",
  "accessory_anchor_profile": "thinking_v1"
}
```

Again, this is conceptual architecture, not an implementation requirement yet.

---

# 23. Accessory Metadata Blueprint

Conceptual:

```json
{
  "id": "accessory_id",
  "display_name": "Accessory Name",
  "slot": "head",
  "unlock_key": "achievement_key",
  "compatible_characters": ["*"],
  "layer": "head_accessory",
  "anchor": "HEAD_TOP",
  "animation_support": "all"
}
```

If an accessory does not work during a specific animation, define an alternate asset or hide it only when absolutely necessary.

The system should not visibly pop accessories on and off during ordinary animation.

---

# 24. Base Character Production Template

When designing a new Codize character, complete this template.

---

## Character Identity

**Working name:**  
`TBD`

**Species:**  
`TBD`

**Coding-name connection:**  
`TBD`

**Primary personality flavor:**  
`TBD`

**Secondary personality flavor:**  
`TBD`

---

## Silhouette

**Dominant body shape:**  
`TBD`

**Signature silhouette feature #1:**  
`TBD`

**Signature silhouette feature #2:**  
`TBD`

**How it remains distinct from existing characters:**  
`TBD`

---

## Proportions

**Head/body relationship:**  
`TBD`

**Default orientation:**  
`TBD`

**Default posture:**  
`TBD`

---

## Base Appearance

**Primary body color:**  
`TBD`

**Secondary body color:**  
`TBD`

**Outline color:**  
`TBD`

**Accent color:**  
`TBD`

**Face treatment:**  
`TBD`

**Permanent design feature:**  
`TBD`

**Details intentionally left open for accessories:**  
`TBD`

---

## Accessory Support

Supported slots:

- [ ] Head
- [ ] Face
- [ ] Neck
- [ ] Body
- [ ] Back
- [ ] Held
- [ ] Effect

Special accessory constraints:

`TBD`

Required anchor points:

`TBD`

---

## Required Animation Interpretation

### Enter

Describe how this species enters:

`TBD`

### Neutral Idle

`TBD`

### Waiting

`TBD`

### Talking

`TBD`

### Thinking

`TBD`

### Positive Confirmation

`TBD`

### Concern

`TBD`

### Uncertain

`TBD`

### Recovery Focus

`TBD`

### Celebration

`TBD`

### Unlock Reveal

`TBD`

---

## Reduced-Motion Behavior

`TBD`

---

## Dialogue Sound Flavor

Optional character-specific blip profile:

`TBD`

---

## Unlock

**Unlock category:**  
`TBD`

**Meaningful achievement represented:**  
`TBD`

**Why this character is appropriate for that achievement:**  
`TBD`

---

# 25. Base Character Acceptance Checklist

A new character cannot ship until all items pass.

## Identity

- [ ] Species is clearly recognizable.
- [ ] Name is memorable and readable.
- [ ] Coding reference is understandable or charming.
- [ ] Character does not feel like a copy of an existing game mascot.
- [ ] Character is visually distinct from all existing Codize characters.

## Base Design

- [ ] Looks complete with zero accessories.
- [ ] Silhouette works without color.
- [ ] Face reads at chat size.
- [ ] Palette is limited and coherent.
- [ ] Character fits the Codize pixel-art family.
- [ ] Character leaves room for accessories.

## Animation

- [ ] Neutral idle complete.
- [ ] Waiting complete.
- [ ] Talking complete.
- [ ] Thinking complete.
- [ ] Positive confirmation complete.
- [ ] Concern complete.
- [ ] Uncertain complete.
- [ ] Recovery focus complete.
- [ ] Celebration complete.
- [ ] Unlock reveal complete.
- [ ] Reduced-motion equivalents complete.

## Accessories

- [ ] Anchor points documented.
- [ ] Layer order documented.
- [ ] Supported slots documented.
- [ ] Core animation frames preserve accessory anchors.
- [ ] At least several test accessories render correctly.
- [ ] No common accessory visibly clips during required animations.

## UX

- [ ] Readable at desktop chat size.
- [ ] Readable at mobile chat size.
- [ ] Does not distract from the primary student action.
- [ ] Waiting animation does not create pressure.
- [ ] Thinking state reads differently from waiting.
- [ ] Concern state does not look angry.
- [ ] Celebration is noticeable but brief.
- [ ] Character remains understandable with sound disabled.
- [ ] Character remains understandable with motion reduced.

---

# 26. Accessory Acceptance Checklist

Every accessory should pass:

- [ ] Clearly fits one accessory slot.
- [ ] Does not obscure the character’s eyes or important expression unless intentionally designed as facewear.
- [ ] Does not destroy silhouette readability.
- [ ] Works at small chat size.
- [ ] Has documented compatible characters.
- [ ] Has documented layer and anchor.
- [ ] Works in all required animations or has variants.
- [ ] Does not imply pedagogical power.
- [ ] Unlock condition reflects a meaningful accomplishment if achievement-gated.
- [ ] Can be unequipped.
- [ ] User can preview it before saving.

---

# 27. Starter Codybara System Requirements

This section defines **Codybara’s role**, not Codybara’s final art direction.

Codybara should:

- be the default character for every new user;
- follow the universal base-character blueprint;
- be visually complete without cosmetics;
- start with minimal accessories;
- support the full accessory system;
- support all required animation states;
- have the clearest possible “friendly beginner guide” readability;
- serve as the reference implementation for future character animation anchors and accessory architecture.

Codybara should **not**:

- look like a low-tier character waiting to be replaced;
- start covered in decorative items;
- require unlocks for basic expressions;
- use animation systems future characters cannot reasonably match.

The first Codybara production pass should effectively establish:

> **the technical and artistic character standard every later animal inherits.**

---

# 28. New Character Design Philosophy

A new character should exist because it adds a genuinely different visual identity.

Do not create another character merely because the achievement system needs more rewards.

A strong new character should bring at least several of:

- distinct silhouette;
- distinctive movement;
- different animation personality;
- interesting accessory opportunities;
- recognizable animal behavior;
- memorable code-related name;
- a thematic connection to the achievement that unlocks it.

Quality matters more than character count.

A small cast of highly expressive characters is better than dozens of forgettable ones.

---

# 29. Character Personality Without Fragmenting Codize

Different characters can feel different while Codize remains one product.

Example:

```text
Character A
calm, slow idle, subtle nods

Character B
curious, more head movement, energetic celebration

Character C
methodical, deliberate thinking animation, understated success

Character D
playful, expressive ears/tail, humorous idle motion
```

However, if all four respond to the same student situation, the **instructional substance stays equivalent**.

The character may change the presentation flavor slightly.

It may not change the educational outcome.

---

# 30. Achievement-to-Cosmetic Mapping

The cosmetic system should reinforce the skills Codize values.

Examples of achievement categories:

## BUILD

Real project milestones.

Potential reward:

- accessories;
- occasional character.

## THINK

Independent reasoning moments.

Potential reward:

- thoughtful / knowledge-themed accessories.

## CHECK

Testing and inspection habits.

Potential reward:

- inspection-themed cosmetic.

## RECOVER

Debugging without blind patch loops.

Potential reward:

- recovery-themed cosmetic.

## UNDERSTAND

Explaining causal relationships or transferring concepts.

Potential reward:

- learning-themed cosmetic.

## INDEPENDENCE

Codize successfully fading help.

Potential reward:

- rarer accessories;
- character unlock candidates.

These categories can guide future achievement design without forcing a visible XP system.

---

# 31. No Grind Requirement

Students should never think:

> “I need to spam Codize interactions to unlock the animal I want.”

Unlock logic should not be based on:

- message count;
- number of prompts copied;
- minutes in app;
- days logged in;
- raw number of clicks.

If a desirable character requires repeated evidence, those repetitions should naturally come from real project work.

---

# 32. Character Switching

Changing characters should be frictionless.

Character destination:

```text
Current companion
[Codybara]

Change character
Customize accessories
```

Selecting a new character:

1. preview;
2. optional animation sample;
3. `Use this character`;
4. immediate replacement across Codize.

Switching characters should not:

- reset learning state;
- reset project state;
- reset chat history;
- change AI behavior;
- alter unlock progress.

---

# 33. Accessory Persistence

Customization should persist across sessions.

Recommended conceptual scope:

> **user-level cosmetic preference**

rather than project-specific.

If the user switches projects, their chosen companion remains.

Future option:

> save different outfits

is possible but not required for V2.

---

# 34. Character Unlock Persistence

Once earned, a character should remain unlocked.

Do not remove unlocks because:

- a streak ended;
- a project was deleted;
- support returned after the student struggled;
- a later task was difficult.

Learning is not linear.

Cosmetics should not punish regression or difficulty.

---

# 35. Figma Requirements for Character System

Before final character art exists, the Codize V2 Figma should reserve the correct functional areas.

Create placeholder components for:

### `Character / Large`

Landing / onboarding.

### `Character / Conversation`

Build / recovery.

### `Character / Small`

Project Home / compact surfaces.

### `Character / Portrait`

Character selector.

### `Character / Customization Preview`

Dedicated Character destination.

### Animation-state placeholders

- Idle
- Waiting
- Talking
- Thinking
- Positive
- Concern
- Uncertain
- Recovery
- Celebration

The placeholder should preserve the expected sprite footprint so final character art can be swapped in without redesigning layouts.

---

# 36. Recommended Character-System Figma Frames

Create character-design frames separate from product screens.

Suggested:

```text
CHARACTER SYSTEM

01 — Base character proportions
02 — Silhouette comparison
03 — Pixel palette
04 — Neutral idle frames
05 — Waiting animation
06 — Talking animation
07 — Thinking animation
08 — Positive animation
09 — Concern animation
10 — Uncertain animation
11 — Recovery focus
12 — Celebration
13 — Unlock reveal
14 — Reduced-motion states
15 — Accessory anchors
16 — Accessory layer order
17 — Head accessories
18 — Face accessories
19 — Neck accessories
20 — Body accessories
21 — Back accessories
22 — Held accessories
23 — Effects
24 — Character selector
25 — Customization screen
26 — Unlock presentation
```

Every future character can duplicate this template.

---

# 37. Production Priority

Do not design a large cast immediately.

Recommended sequence:

```text
1. Finalize character-system blueprint
2. Design Codybara base
3. Produce Codybara required animation set
4. Validate chat readability
5. Implement accessory anchors
6. Create 3–5 test accessories
7. Test desktop + mobile
8. Implement customization UX
9. Implement achievement unlock plumbing
10. Only then design character #2
```

Why:

If five characters are drawn before the animation/accessory architecture is proven, every character may need expensive rework.

Codybara should be the **reference implementation**.

---

# 38. Minimum Character MVP

The first character-system release does not need dozens of cosmetics.

Minimum useful package:

### Codybara

- complete base sprite;
- idle;
- waiting;
- talking;
- thinking;
- positive;
- concern;
- uncertain;
- recovery;
- celebration;
- reduced-motion variants.

### Accessories

Approximately:

- 2–3 head options;
- 1–2 face options;
- 1 neck option;
- 1 body option;
- 1 held item;
- 1 subtle effect.

Some can begin locked.

### Character destination

- character preview;
- character selection;
- accessory selection;
- equipped/unlocked/locked states.

### Settings / Presentation

- dialogue sounds toggle;
- animation toggle / reduced motion.

### Unlocks

A few meaningful achievement-based cosmetic unlocks.

New characters can arrive after the core experience proves fun.

---

# 39. Longer-Term Character System

Later possibilities:

- more animal companions;
- additional outfits;
- seasonal but non-pressure cosmetics;
- special first-V1 character unlock;
- project-completion accessories;
- character-specific idle variations;
- unlockable dialogue-blip profiles;
- character portrait reactions in Learning;
- optional character room / collection screen;
- project trophies visible near the companion;
- small celebratory scenes after important milestones.

These should remain secondary to building and learning.

---

# 40. Final Character Blueprint

Every Codize character should ultimately be:

> **A small, highly readable, original pixel-art animal companion with a strong silhouette, expressive face, complete animation language, stable accessory anchors, a finished accessory-free base appearance, and a personality expressed primarily through motion and visual flavor rather than different teaching behavior.**

Every character must support the same semantic states:

```text
IDLE
WAITING
TALKING
THINKING
POSITIVE
CONCERN
UNCERTAIN
RECOVERY
CELEBRATION
UNLOCK
```

Every character must support customization without being visually dependent on it.

Every unlock should celebrate meaningful growth rather than app usage.

Codybara establishes the system.

Accessories let the student make the companion feel like theirs.

New characters give longer-term progression something memorable to unlock.

And throughout the experience, the character should reinforce one idea:

> **Codize is here to help the student become more capable, not to become the thing doing the work for them.**
