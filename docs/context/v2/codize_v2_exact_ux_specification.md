# Codize V2 Exact UX Specification

## Status

**Document type:** Canonical UX behavior specification for Codize V2.

**Stage:** Post-Figma UX synchronization; pre-implementation and pre-migration.

**Primary purpose:** Define exactly what a student sees, what Codize says, what actions are available, how the system responds, what state changes behind the scenes, and which UX patterns are forbidden. This revision is synchronized to the approved V2 Figma direction closely enough to drive repository mapping and implementation planning without treating old V1 screens as authority.

**Product thesis dependency:** This specification assumes the `Codize V2 Product Thesis` is the product-level source of truth for why Codize exists and what it is trying to teach.

**Design hierarchy:**

1. **Product Thesis** defines why Codize exists and the product principles that must not be violated.
2. **Exact UX Specification** defines the expected behavior, flow, copy intent, and interaction structure.
3. **Character System Blueprint** governs character assets, animation, customization, accessories, and cosmetic unlock rules without redefining this behavior.
4. **Technical Architecture and State Model** maps this behavior into deterministic state, domain boundaries, security, compatibility, and implementation sequencing.
5. **Schema and Persistence Design** is subordinate to the architecture and fixes the physical MVP persistence design.
6. **Future Learning / Teaching Policy** will settle exact evidence qualification, fading, reintroduction, and high-risk teaching minimums.

The **approved Figma** defines visual layout, sizing, hierarchy, styling, responsive behavior, motion intent, and component appearance only: https://www.figma.com/design/QBGSdTLG7iQ2xEFzU7v0Li/Codize-V2-Product-Design

The old V2 Journey and Screen/Surface Map are design-process references, not implementation authority. If a future Figma change alters behavior, synchronize this document intentionally rather than allowing visuals or old V1 docs to silently redefine the product.

---

# 0. North-Star UX Principle

The student should experience Codize as:

> **A knowledgeable coding mentor who helps me build my own project with the coding AI I already use, teaches me one useful thing when I need it, remembers where I am, and gets out of the way as I improve.**

The student should **not** experience Codize as:

- a course they must complete before building;
- a generic AI chat box;
- an eight-stage software-development workflow;
- a project-management dashboard;
- a quiz app attached to an AI coder;
- a tool that makes every five-minute code change take twenty minutes;
- another coding agent that writes everything for them;
- a compliance system that forces students to fill boxes.

The core interaction rule is:

> **One project. One current change. One useful habit at a time.**

The core visibility rule is:

> **At any moment, show one primary cognitive task.**

The core adaptation rule is:

> **If the student already demonstrates a behavior, do not ask them to perform it again just because the workflow normally contains that step.**

---

# 1. UX Goals

Codize V2 should optimize for the following outcomes in this order.

## 1.1 Immediate comprehensibility

A beginner should know what to do next without understanding Codize terminology.

The interface should favor language like:

> What do you want to build?

> What are you changing right now?

> What should stay working?

> How did it go?

> Something broke?

Avoid making the student first understand terms like:

- phase;
- provenance;
- evidence;
- gate;
- archetype;
- verification stage;
- lifecycle state;
- assignment artifact.

Those concepts may exist internally.

## 1.2 Fast path to building

A first-time student should reach a real coding-agent prompt quickly. The first session should not feel like onboarding paperwork.

## 1.3 Just-in-time teaching

Teach concepts when the student's project creates a reason for them.

## 1.4 Student agency

Codize recommends and explains. The student ultimately owns ordinary project decisions.

## 1.5 Structured independence

Codize should begin more directive and gradually become quieter as the student shows they can scope, prompt, inspect, test, and debug independently.

## 1.6 Low-friction tool switching

The student continues using Codex, Claude Code, Cursor, ChatGPT, Replit, or another coding agent. Codize must minimize the cost of moving between Codize and that agent.

## 1.7 Truthful system behavior

Codize distinguishes what it knows from what it infers. It should never imply that generated code is correct, secure, understood, or verified when the evidence does not support that claim.

---

# 2. UX Vocabulary

The student-facing vocabulary should remain plain.

| Internal idea | Preferred student-facing language |
|---|---|
| Assignment | Current change / what you're working on |
| Scope | What you're changing |
| No-touch boundary | What should stay working / what AI should leave alone |
| Acceptance criteria | What "done" should look like |
| Verification | Try it / check it |
| Evidence | What happened / what you observed |
| Provenance | Where this came from, usually hidden unless useful |
| Change Map | What changed |
| Review | Look at the change / inspect it |
| Recovery workflow | Something broke / get unstuck |
| Competency | Habit or concept |
| Mastery | Avoid as a precise claim |
| Independent | Recently demonstrated without help |
| Roadmap | Build plan |
| Phase | Usually hidden |

The product should teach technical terms such as `localStorage`, event handler, API, database, authentication, branch, and commit when those terms are useful. The product should not expose internal Codize ontology for its own sake.

---

# 3. Surface Types

Codize should use a small set of repeated surface patterns.

## 3.1 Full page

Used for destinations that deserve their own navigation context.

Examples:

- Landing;
- Project Home;
- Build;
- Build Plan;
- Learning;
- History;
- GitHub setup;
- Character;
- Settings.

## 3.2 Build mode

A state inside the Build workspace, not a separate route unless implementation requires it.

Examples:

- idea setup;
- current-change confirmation;
- teaching interaction;
- prompt preparation;
- handoff;
- return;
- check;
- inspection;
- understanding;
- recovery.

## 3.3 Structured card

Used inside Build when a decision benefits from clearer structure than a normal chat bubble.

Examples:

- first-version proposal;
- prompt preview;
- effort selector;
- change summary;
- recovery evidence summary;
- achievement;
- concept explanation.

## 3.4 Inline expansion

Used for optional depth without leaving the current context.

Examples:

- Need help?;
- Why does this matter?;
- Why is this prompt structured this way?;
- Another hint.

## 3.5 Inspection drawer

Used when the student needs to look at code, a diff, or a change while keeping the Build conversation visible.

Desktop: side drawer or split pane.

Mobile: full-width subview with clear back navigation.

## 3.6 Celebration state

Used sparingly for meaningful milestones, especially first-version completion or genuine independence achievements.

## 3.7 Modal

Avoid for core reasoning. Use only for short confirmations, connection permission explanations, destructive actions, or unavoidable external integration steps.

Never put a multi-step learning experience in a modal.

---

# 4. Primary Information Architecture

Signed-in Codize should have four primary project destinations:

```text
Project
Build
Learning
History
```

Secondary destinations:

```text
Character
Settings
```

`Something broke` is **not** a sidebar/navigation destination. It is a contextual action available on Project Home, in Return/failure states, and inside Build when recovery is relevant.

Conceptual route map:

```text
/
/login
/signup

/app
/app/projects
/app/project/:projectId
/app/project/:projectId/build
/app/project/:projectId/plan
/app/project/:projectId/learning
/app/project/:projectId/history
/app/project/:projectId/connect
/character
/settings
```

The route design is conceptual, not implementation-locked. The important behavior is that Prompt, Check, Inspection, Understanding, and Recovery do **not** feel like separate apps or routes to the student.

---

# 5. Global App Shell

## Goal

Give the student persistent orientation without turning Codize into a dashboard-heavy app.

## Desktop structure

```text
┌──────────────┬──────────────────────────────────────────┐
│ CODIZE       │ Current project                          │
│              │                                          │
│ Project      │                                          │
│ Build        │              Current surface             │
│ Learning     │                                          │
│ History      │                                          │
│              │                                          │
│              │                                          │
│ Character    │                                          │
│ Settings     │                                          │
└──────────────┴──────────────────────────────────────────┘

Character and Settings sit at the bottom of the sidebar. Do not use a decorative divider line merely to push them downward.
```

## Mobile structure

Preferred bottom navigation:

```text
Project | Build | Learning | History
```

`Something broke` should remain reachable through a visible contextual action on Project Home and Build/Return states, not as a sidebar item and not hidden in Settings or an overflow menu.

## Persistent project context

When a project is active, the shell may show:

- project name;
- project switcher affordance;
- optional connection state icon for GitHub;
- optional agent indicator when relevant.

Do not show:

- phase number;
- workflow stage count;
- mastery percentage;
- multiple competing progress meters.

## Character presence

Character is not equally prominent everywhere.

- Landing: prominent.
- Build: prominent.
- Recovery: prominent.
- Project Home: small/contextual.
- Learning: moderate.
- History: minimal.
- Character: large inside customization/preview, otherwise secondary.
- Settings: none or nearly none.

---

# 6. Public Landing Page

**Conceptual route:** `/`

## Goal

Explain the value proposition within roughly five seconds and make the student want to start building.

## Entry condition

Unauthenticated visitor.

## Hero content

### Headline

# **Build something real with AI. Learn how it works as you go.**

### Supporting copy

> Codize helps you turn your idea into manageable changes, work with coding agents like Codex, Claude, and Cursor, and actually understand what you're building instead of blindly accepting AI-generated code.

### Primary CTA

**Start Building Free**

### Secondary CTA

**See How Codize Works**

### Character line

> “AI can build faster than you can learn. I'll help you keep up.”

The character line may type in with the original Codize retro dialogue sound if sound is enabled.

## Core hero visual

The key visual is project growth beside learning growth.

Suggested content:

```text
WHAT YOU'RE BUILDING
Idea → First screen → Saved data → Features → Bigger systems

WHAT YOU'RE LEARNING
Clear prompts → Events → Inspection → Testing → Debugging
```

The character can visually move between the tracks.

The visual should communicate direction and balance, not fake measurable percentages.

## Problem section

Headline:

## **AI makes coding easier. Losing control of your project is easier too.**

Visual story:

```text
"Build my whole app"
        ↓
AI generates a lot of code
        ↓
Something breaks
        ↓
"Fix it"
        ↓
AI changes even more
        ↓
"Fix it again"
        ↓
"I don't even know how my own app works."
```

Supporting copy:

> **Codize teaches you a better way without making you learn everything before you start building.**

## Better-path section

Headline:

## **Your idea stays yours. Codize helps you build it one piece at a time.**

Visual:

```text
YOUR IDEA
   ↓
ONE CHANGE
   ↓
ONE USEFUL THING
   ↓
BUILD WITH YOUR AI
   ↓
CHECK WHAT HAPPENED
   ↓
KEEP BUILDING
```

Supporting copy:

> Codize introduces planning, prompting, testing, debugging, GitHub, and programming concepts when they actually become useful in your project.

## Product demo section

Animated mock interaction:

**Codize**

> What do you want to build?

**Student**

> A volleyball stat tracker for my team.

**Codize**

> Cool. Let's start with one working piece. What should someone be able to do first?

**Student**

> Add players.

**Codize**

> Perfect. Let's make that first AI prompt specific.

Follow with:

```text
Codize
  ↓
creates a deliberate prompt
  ↓
Codex / Claude / Cursor
  ↓
project changes
  ↓
Codize helps you check + understand it
```

## Works-with-your-AI section

Headline:

## **Keep your coding AI. Use it better.**

Copy:

> Codize does not replace your coding agent. It helps you learn how to direct and supervise it.

Show Codex, Claude, Cursor, ChatGPT, Replit, and an “other tools” treatment without implying permanent exclusive support for any specific product.

## Differentiation section

Headline:

## **Not another chatbot telling you what to do.**

Three pillars:

### Knows your project

> Codize remembers your goals, working features, recent changes, and what you're building next.

### Learns how you learn

> It gives more support when something is new and gets out of the way when you're ready to handle it yourself.

### Connects thinking to real code

> Your intentions, coding-agent prompts, GitHub changes, tests, and understanding stay connected instead of disappearing across separate AI chats.

## Recovery preview

Headline:

## **When something breaks, stop the patch loop.**

Tiny flow:

```text
What worked before?
↓
What changed?
↓
What do we know?
↓
What should we check first?
```

## Final CTA

# **Build with AI without getting lost in your own code.**

**Start Building Free**

## System behavior

The public landing page does not need authenticated project data.

## Do not

- lead with “anti-vibe coding” as the only message;
- shame students for using AI;
- imply Codize writes the app for them;
- use fake learning percentages;
- explain the entire pedagogy before the CTA;
- overload the hero with feature cards;
- present school/district/instructor messaging as the primary student pitch.

---

# 7. Authentication

**Conceptual routes:** `/signup`, `/login`

## Goal

Get the user into the product with minimal interruption.

## What the user sees

- Codize brand;
- short signup/login form;
- familiar authentication methods if supported;
- link between signup and login.

## Copy intent

Avoid turning authentication into onboarding.

After successful signup:

> “You're in. Let's build something.”

## Do not ask here

- coding level;
- GitHub familiarity;
- preferred language;
- learning goals;
- agent choice;
- project architecture;
- school information;
- full name unless necessary for account functionality.

## Next state

First-time entry choice.

---

# 8. First-Time Entry Choice

**Location:** First signed-in app state.

## Goal

Route the student to the shortest relevant path.

## What the user sees

Character centered or prominently placed.

Copy:

# **What brings you here?**

Three large choices:

### **I have an idea I want to build**

Supporting hint:

> Start from an idea, even if you have barely coded before.

### **I'm already building something**

Supporting hint:

> Bring an existing project and keep going from where you are.

### **Something broke**

Supporting hint:

> Figure out what happened before asking AI for another patch.

## Available actions

Select one path.

## System behavior

Store entry path as session context, not as a permanent student identity.

## Next states

- New Idea flow;
- Existing Project flow;
- Recovery-first flow.

## Visual notes

This should feel like a choice of starting point, not a placement test.

## Do not

- ask for skill level first;
- show ten project types;
- show a dashboard before a project exists;
- use technical labels such as “greenfield” or “brownfield.”

---

# 9. New Idea - Idea Capture

**Surface type:** Build mode.

## Goal

Understand what the student wants to create in their own words.

## Entry condition

Student chose **I have an idea I want to build**.

## What the user sees

Header/context:

> New Project

Character message:

> **“What do you want to build?”**

Large text input.

Optional placeholder:

> “A volleyball stat tracker for my team...”

## Available actions

- type idea;
- submit;
- optional examples link if the field is empty for a while.

## System behavior

Codize may infer candidate capabilities from the description but must not silently treat those inferences as confirmed project truth.

Store:

- raw idea text;
- candidate project summary;
- candidate features;
- uncertainty where relevant.

## Response behavior

Codize reflects the idea back briefly.

Example:

> “Got it. A volleyball tracker where you can add players and record their stats.”

Then ask one product-level question:

> **“What would you most want someone to be able to do first?”**

Possible suggested chips may appear based on the idea:

```text
Add players
Record stats
See totals
I'm not sure
```

Student may also type their own response.

## Socratic rule

Ask about desired behavior, not technical architecture.

## Need Help behavior

If the student says “I don't know,” Codize can suggest 2 to 4 first-user actions inferred from the idea and ask which feels most important.

## State writes

- `project.idea_raw`
- `project.goal_summary_candidate`
- `project.desired_first_user_action`

## Next state

First-Version Shaping.

## Do not

- ask which framework they want;
- ask for database choice;
- ask for architecture;
- ask for every desired feature in separate fields;
- generate a full plan before understanding what the student cares about.

---

# 10. First-Version Shaping

**Surface type:** Build mode with structured card.

## Goal

Prevent the first large one-shot build while preserving the student's ambition.

## Entry condition

Codize has enough context to identify a plausible first version.

## What the user sees

Character:

> “You can absolutely get there. I'd start with a smaller first version so you can get something working and understand each piece as you add it.”

Structured card:

```text
FIRST VERSION

✓ Add players
✓ Record basic stats
✓ Show totals
✓ Save stats on this device

SAVE FOR LATER

○ Accounts
○ Team sharing
○ AI analysis
```

Primary action:

**Looks good**

Secondary action:

**Change this**

Optional action:

**Why start smaller?**

## System behavior

Codize proposes a first version using:

- student's stated goal;
- project complexity;
- likely prerequisite ordering;
- learner context if known;
- risk level.

The proposal is a recommendation, not hidden truth.

## Why-start-smaller expansion

Keep concise:

> “Smaller changes are easier to check and easier to debug. You still get to build the full idea. We're just making sure the project doesn't become more complicated faster than you can understand it.”

## Change-this behavior

Student can:

- move an item from Later to First Version;
- move an item from First Version to Later;
- add an item;
- remove an item;
- type a different priority.

Codize may respond Socratically if the change dramatically increases complexity.

## State writes

- `project.v1_scope.confirmed_items`
- `project.v1_scope.saved_for_later`
- `project.v1_scope.student_overrides`

## Next states

- Build Plan Proposal;
- Guided Resistance if student insists on a very broad V1.

## Do not

- say “you are not ready” without explanation;
- hide saved ideas;
- force a generic beginner project;
- automatically discard ambitious features;
- make the student complete a scope worksheet.

---

# 11. Guided Resistance

**Surface type:** Build mode with complexity card.

## Goal

Teach why a huge one-shot build is hard to supervise without turning Codize into a gatekeeper.

## Entry condition

Student rejects a reasonable first-version recommendation and insists on combining several major systems at once.

## What the user sees

Character:

> “You can do that. Before we send one giant prompt, look at how many parts would change together.”

Card:

```text
THIS PROMPT TOUCHES

UI
Player data
Statistics
Accounts
Authentication
Database
Sharing
AI
```

Question:

> **“If all of these changed together and something broke, where would you start looking?”**

Input or choices:

- student answer;
- **Need help?**

## If the student recognizes the problem

Codize:

> “Exactly. Let's keep the same app and get one working piece first.”

Action:

**Break it into pieces**

## If the student still insists

Offer:

**Build it all anyway**

Codize response:

> “Okay. I still would not recommend this as the easiest way to stay in control. Let's at least define what this version must accomplish so you have something concrete to check afterward.”

The system increases support for the change.

## System behavior

Record that the student overrode the sequencing recommendation. Do not mark this as failure or deduct progress.

## State writes

- `project.v1_scope.override = true`
- `current_change.complexity = elevated`
- `learner_context.guidance_override_history += event`

## Next state

Build Plan Proposal with higher scaffolding, or return to First-Version Shaping.

## Do not

- shame the student;
- block ordinary ambitious work solely because Codize prefers smaller changes;
- produce a giant prompt without at least establishing observable goals;
- make the override button look like a dangerous red destructive action unless the actual change is dangerous.

---

# 12. Build Plan Proposal

**Surface type:** Build mode with structured card.

## Goal

Give the student a simple sequence without making the plan the center of every session.

## What the user sees

Character:

> “Here's the order I'd start with. You can change it.”

Card:

```text
VOLLEYBALL TRACKER

1. Create the basic app
2. Add players
3. Record stats
4. Show totals
5. Save stats on this device
```

Actions:

**Use this plan**

**Edit plan**

**Why this order?**

## Edit behavior

Student can reorder, add, remove, or defer items.

Codize may explain dependencies when useful.

Example:

> “Saving data is easier to understand after the player list already exists, because then you can see exactly what is being saved and loaded.”

## System behavior

Create a lightweight plan with current and future work. Plan is not a rigid phase system.

## State writes

- `project.plan.items`
- `project.plan.current_item`
- `project.plan.saved_for_later`

## Next state

Project Home.

## Do not

- create 20 microtasks;
- expose internal archetypes;
- lock later tasks;
- imply the sequence can never change;
- keep the full plan permanently expanded on Home.

---

# 13. Project Home

**Conceptual route:** `/app/project/:projectId`

## Goal

Answer one question:

> **What should I work on next?**

## Entry conditions

Project exists.

## What the user sees

Example:

```text
VOLLEYBALL TRACKER

You've built:
Players + player list

────────────────────────────

UP NEXT

Record player stats

Add controls for kills, assists,
blocks, and errors.

[ Continue building ]

────────────────────────────

Something not working?
[ Something broke ]

────────────────────────────

Build plan ›
Recent changes ›
```

If nothing has been built yet:

> “Nothing yet. Let's get the first piece working.”

## Character behavior

Small presence only.

Possible short contextual message:

> “Ready for the next piece?”

Do not turn Home into another chat transcript.

## Primary action

**Continue building**

## Secondary actions

- Something broke;
- Build plan;
- Recent changes;
- project switcher.

## System behavior

Home calculates the most appropriate current-change summary from confirmed plan state and any active unresolved change.

If a change is already in progress, the CTA becomes:

**Continue current change**

and the summary reflects where the student left off.

## Empty state

If a project exists but no plan exists due to interrupted onboarding:

> “Let's finish deciding what to build first.”

CTA:

**Continue setup**

## State writes

None on view unless user takes an action.

## Next states

- Build workspace;
- Recovery mode;
- Build Plan;
- History.

## Do not

- show multiple competing next-step cards;
- show a mastery score;
- show the full project thesis visual from the public landing page;
- duplicate “Up Next,” “Start Here,” “Current Assignment,” and “Recommended Starting Point.”

---

# 14. Build Plan Page

**Conceptual route:** `/app/project/:projectId/plan`

## Goal

Provide optional project-wide orientation and allow plan edits without making planning mandatory every session.

## What the user sees

```text
VOLLEYBALL TRACKER

FIRST VERSION

✓ Basic app
● Add players
○ Record stats
○ Show totals
○ Save data

LATER

○ Accounts
○ Team sharing
○ AI analysis
```

## Available actions

- reorder future items;
- add an item;
- move item to Later;
- move saved item into the active plan;
- open “Why this order?”;
- choose a different next item.

## System behavior

When the user changes sequence, Codize checks for meaningful dependencies.

If no issue:

> “Got it.”

If a dependency matters:

> “You can move online sharing earlier, but it depends on accounts and shared storage. Do you still want to move it?”

Actions:

**Keep my order**

**Use recommended order**

## Do not

- block reordering without a genuine dependency or safety reason;
- show hidden future curriculum requirements;
- make all items look equally important;
- present the plan as a fixed course syllabus.

---

# 15. Build Workspace

**Conceptual route:** `/app/project/:projectId/build`

## Goal

Serve as the main mentoring workspace for planning the current change, preparing the coding-agent prompt, returning from the agent, checking the result, understanding important concepts, and recovering from problems.

## Core layout

Header:

- project name;
- current change label;
- optional agent indicator;
- optional GitHub connection status.

Main area:

- Codize character;
- conversational messages;
- one active structured card or question at a time.

Persistent contextual actions:

- Something broke;
- Ask about my project;
- optional current-change summary.

## Important implementation principle

Build is not a generic free-form chat. It is an orchestrated state machine rendered conversationally.

The system owns:

- current workflow state;
- intervention type;
- support level;
- what information has been revealed;
- which transitions are valid.

The model owns:

- natural wording;
- project-specific examples;
- Socratic phrasing within allowed policy.

## Do not

- expose ten panels at once;
- allow the LLM to invent arbitrary new workflow stages;
- show the full chat history as the only source of orientation;
- put the entire Prompt Builder and all post-build questions on one screen.

---

# 16. Current-Change Confirmation

**Surface type:** Build mode.

## Goal

Make the current task unmistakable before reasoning about it.

## Entry condition

Student begins or resumes a plan item.

## What the user sees

```text
YOU'RE WORKING ON

Record player stats

Add controls for kills, assists,
blocks, and errors.

[ Start ]
[ Choose something else ]
```

If resuming:

```text
CURRENT CHANGE

Record player stats

You're at: preparing the prompt

[ Continue ]
```

## System behavior

Current change is loaded from project plan or student override.

## Choose-something-else behavior

Opens a simple selection of plan items plus:

**Something else...**

If the student chooses a new change, Codize may ask one short question to understand it, then update current change.

## State writes

- `current_change.id`
- `current_change.goal`
- `current_change.status = active`

## Next state

Learning Engine Decision.

## Do not

- show the whole plan by default;
- force an explanation of why they chose the task unless needed;
- show a stage count such as “Step 1 of 8.”

---

# 17. Learning Engine Decision

**Surface type:** Invisible system decision.

## Goal

Determine whether Codize should teach, ask, remind, or stay quiet before prompt preparation.

## Inputs

- current change;
- project state;
- change complexity;
- new concepts likely introduced;
- learner model;
- previous independent behavior;
- support recently needed;
- chosen coding agent;
- whether existing working features could be affected;
- risk level.

## Possible decisions

### SKIP

No new intervention needed.

Proceed to Prompt Preparation.

### HABIT_INTERVENTION

Examples:

- define done;
- protect what works;
- inspect scope;
- choose effort.

### CONCEPT_INTERVENTION

Examples:

- localStorage;
- event handlers;
- client/server;
- API;
- authentication.

### HIGH_RISK_SLOWDOWN

Use more than one safety-relevant check if necessary.

## Rules

- Prefer no intervention if the student already demonstrates the target behavior.
- Do not introduce a new concept merely because it can be taught.
- Do not teach syntax trivia unless it blocks progress.
- Do not use learner difficulty as punishment.
- Asking for help must not reduce future opportunities.

## State writes

- `current_intervention.type`
- `current_intervention.target`
- `current_intervention.support_level`

---

# 18. First Habit Intervention - Define “Done”

**Surface type:** Build question card.

## Goal

Teach the student to make an AI prompt observable and checkable.

## Entry condition

Typically first AI-assisted change or evidence shows the student still makes vague goals.

## Character copy

> “One quick thing before we ask your coding AI.”

Learning line:

> **“A good AI prompt says what ‘done’ looks like.”**

Question:

> **“When this part is finished, what should you actually be able to do?”**

Input field.

Secondary action:

**Need help?**

## Example student response

> “Add a player.”

## Vague-answer response

Do not reject it with a red error.

Codize:

> “You're close. What would you actually type or click if it were working?”

Student:

> “Type their name and number and click Add.”

Codize:

> “Exactly.”

## Completeness logic

Use deterministic minimum criteria where possible:

- nonblank;
- describes an observable behavior or output;
- not only a restatement of the task title.

Semantic assistance may flag vagueness, but Codize should not pretend there is one perfect answer.

## State writes

- `current_change.done_looks_like`
- learner evidence: `define_done = guided/practiced/independent` depending on support.

## Next state

Prompt Preparation.

---

# 19. Boundary Intervention - Protect What Works

## Goal

Teach students to preserve unrelated working behavior when adding new features.

## Entry condition

Project already contains working features that the current change does not obviously need to modify.

## Character copy

> “You already have something working now.”

Question:

> **“What's one thing your coding AI should leave alone while it adds this?”**

Input.

**Need help?**

## Example

Student:

> “The player form.”

Codize:

> “Good. We'll make that boundary explicit.”

## If the student already included a boundary earlier

Skip the question.

Optional character reaction:

> “You already protected the player form. Nice.”

Do not require another field.

## State writes

- `current_change.no_touch_boundaries`
- learner evidence for boundary setting.

---

# 20. Need Help System

**Surface type:** Inline expansion.

## Goal

Keep Socratic teaching helpful rather than frustrating.

## Entry condition

Student clicks **Need help?** on a reasoning question.

## Support ladder

### Level 1 - Nudge

Example:

> “Think about something that already works.”

Action:

**Try again**

Optional:

**Another hint**

### Level 2 - Guided clue

> “Your player form already works. Does adding stat totals need to change how players are created?”

Action:

**Try again**

Optional:

**Work through it with me**

### Level 3 - Teach

> “Probably not. A useful boundary would be to tell the coding AI to leave the player form unchanged. That helps prevent unrelated rewrites.”

Then return to the original question with support.

## System behavior

Record support level used.

Do not treat help as failure.

## State writes

- `learner_evidence.support_used`
- `current_intervention.hint_level`

## Do not

- reveal the full answer on first hint;
- force repeated attempts indefinitely;
- say “think harder”;
- use red incorrect states for open reasoning questions;
- lower a visible level because help was used.

---

# 21. Prompt Preparation

**Surface type:** Build mode.

## Goal

Construct a strong coding-agent prompt from the student's decisions and known project context.

## System inputs

- project summary;
- current change;
- done looks like;
- boundaries;
- stack if known;
- relevant known working behavior;
- selected coding agent;
- student-authored wording where available.

## What the user sees

Character:

> “Here's the prompt I built from what you decided.”

Prompt Preview card.

## Rules

Codize may improve clarity, ordering, and specificity.

Codize should not silently add major product requirements the student did not choose.

Codize should not ask the coding agent to rewrite unrelated parts “for cleanliness.”

---

# 22. Prompt Preview Card

## Goal

Give the student a clear final prompt they can inspect, edit, and understand.

## Example

```text
YOUR PROMPT

I'm building a volleyball stat tracker.

Right now, add controls for recording:
- kills;
- assists;
- blocks;
- errors.

Keep the existing player form and player list
working the same way.

When finished, clicking each control should
update that player's total.
```

Metadata row:

> Agent: Claude Code

Actions:

**Edit**

**Why is this prompt structured this way?**

Primary action appears after effort decision if needed:

**Copy & Build**

## Edit behavior

Student edits the prompt directly.

If they remove a previously confirmed boundary or observable result, Codize should not immediately block. It may ask:

> “You removed the part about keeping the player form unchanged. Was that intentional?”

Choices:

**Yes**

**Put it back**

## State writes

- `current_change.prompt.final_text`
- `current_change.prompt.student_edits`

---

# 23. “Why Is This Prompt Structured This Way?”

**Surface type:** Inline expansion.

## Goal

Teach prompt structure only to students who care or when the system thinks a short explanation is useful.

## Content

### Project context

> Helps your coding agent understand what already exists.

### Current change

> Keeps the prompt focused on one piece of the project.

### Done looks like

> Gives you something real to check afterward.

### Leave alone

> Protects working parts that do not need to change.

## Behavior

Expansion does not navigate away.

Student can collapse it and continue.

## Do not

- require this lesson;
- use advanced prompt-engineering terminology unless student asks;
- make the explanation longer than the prompt itself.

---

# 24. Coding Agent Selection

**Surface type:** Contextual setup card, shown when agent is unknown or user chooses to change it.

## Goal

Know which external tool the student uses so Codize can tailor handoff and agent-specific guidance.

## Timing rule

When the active project has no saved agent preference, **agent selection is the first Build question** before current-change teaching, prompt preparation, or effort guidance. Before the student chooses, do not display a fake/preselected agent badge in the Build header. When the agent is already known, skip this setup unless the student chooses to change tools.

## Copy

> **“What coding AI are you using?”**

Choices may include:

- Codex;
- Claude Code;
- Cursor;
- ChatGPT;
- Replit;
- Other.

Optional:

**Help me choose**

## Help-me-choose behavior

Ask at most 1 to 2 practical questions, such as whether the student is working in a local code editor, browser-based environment, or chat. Do not produce an overwhelming product comparison.

## State writes

- `user_or_project.agent_preference`
- `agent_familiarity` if learned.

## Do not

- imply one specific commercial tool is required;
- hard-code product settings that may change without a maintained mapping layer.

---

# 25. Effort / Reasoning Level Teaching

**Surface type:** Small structured card.

## Goal

Teach the student to match reasoning effort to task complexity in a transferable way, then map that concept to the selected coding agent.

## Student-facing abstraction

# **How much thinking does this prompt need?**

### Quick

> Small, obvious, low-risk change.

### Standard

> Normal feature with a few connected pieces.

### Deep

> Tricky debugging, architecture, unfamiliar systems, security-sensitive work, or a major refactor.

## First meaningful exposure: student answers first

Codize briefly introduces the three categories, then asks:

> **“What effort level do you think this prompt needs in [selected agent]?”**

The options appear with **no answer preselected**. The student chooses one and presses **Submit**.

### Correct / reasonable choice

Codize confirms the choice and explains the task evidence that makes it appropriate. Then, if a maintained mapping exists, Codize shows the current tool/model/reasoning recommendation for the selected coding agent.

Example structure:

```text
CORRECT
Standard fits because this change has a few connected pieces,
but it is still bounded feature work.

AGENT RECOMMENDATION
[Current model / reasoning setting from maintained agent metadata]
```

### Incorrect / unreasonable choice

Codize should not reveal the answer immediately. It should explain why the chosen category does not fit and give one Socratic hint focused on the task's complexity/risk.

The student gets **one retry**.

If the retry is still unreasonable, Codize reveals the recommended category, explains why, and shows the agent-specific mapping if available.

Do not turn this into repeated quiz punishment.

## Later exposure

Ask the student first only when effort is worth thinking about. If they consistently make reasonable choices, skip the card. Reintroduce it for novel/high-risk tasks when useful.

## Agent-specific mapping rules

- The durable lesson is **Quick / Standard / Deep**, not memorizing a vendor label.
- Model names and reasoning controls can change.
- Agent-specific recommendations must come from maintained metadata/configuration, not model memory alone.
- If Codize does not know the current setting names for a tool, teach the general category and do not invent UI instructions.

## State writes

- `current_change.effort_category`
- attempted category / retry result where useful for learner evidence
- learner evidence for effort selection

---

# 26. Agent Handoff

**Surface type:** Build mode.

## Goal

Make leaving Codize and returning obvious.

## What the user sees

```text
READY FOR CLAUDE CODE

YOUR PROMPT
[ full visible prompt text ]

[ Copy Prompt ]

Open Claude Code and let it finish this change.
Come back when it's done.

[ I'm back ]
```

The student must be able to see the exact prompt immediately before copying it.

If clipboard integration is unavailable, provide a selectable prompt with copy affordance.

## Optional reminders

For beginners using an agent that needs explicit execution instructions, Codize can show a concise agent-specific note.

## System behavior

Mark current change as waiting for external execution.

Record prompt version and baseline repository commit if GitHub is connected.

## State writes

- `current_change.status = awaiting_agent`
- `current_change.prompt_sent_at`
- `current_change.baseline_commit` if available.

## Do not

- ask the student to paste a long report before they leave;
- show all later checking steps in advance;
- make Codize pretend it executed the code.

---

# 27. GitHub Introduction

**Surface type:** Build card or post-success card.

## Goal

Explain why connecting the repository benefits the student before asking for permissions.

## Recommended timing

For a brand-new student, after the first meaningful working change or when manual handoff becomes relevant.

For an existing project, earlier.

## Copy

# **Want me to keep track of what your coding AI changes automatically?**

> “Connecting your project lets me compare what you asked for with what actually changed.”

Actions:

**Connect GitHub**

**Not yet**

## If Connect GitHub

Ask:

> **“How familiar are you with GitHub?”**

Choices:

- I use it already;
- A little;
- What's GitHub?

## Beginner explanation

> “Think of GitHub like checkpoints for your project. It keeps a history of your code, so you can see what changed and go back when something breaks.”

## State writes

- `github_intro_seen`
- `github_familiarity`

## Do not

- force connection before the user understands why;
- use “Git is a distributed version-control system...” as first explanation;
- imply Codize needs write access if read access is enough.

---

# 28. GitHub Connection Setup

**Conceptual route:** `/app/project/:projectId/connect`

## Goal

Connect the correct repository with minimal permissions and teach just enough GitHub to make the connection meaningful.

## What the user sees

Step 1:

> **Connect your project**

Short explanation based on familiarity level.

Step 2:

GitHub authorization/install flow.

Step 3:

Repository selection.

Step 4:

Connection confirmation.

Example confirmation:

```text
✓ CONNECTED

Repository
maya/volleyball-tracker

Codize can read:
✓ Files
✓ Commit history
✓ Changes

Codize cannot:
✗ Silently change your code
```

Exact permissions depend on technical implementation and should be truthfully rendered.

## Beginner checkpoint teaching

After first successful connection and when a stable change exists:

> “You just finished something that works. This is a good checkpoint.”

Explain:

```text
commit = a saved checkpoint in your project's history
repository = your project plus that history
```

## Error states

### Authorization canceled

> “No problem. Your project is still here. You can connect GitHub later.”

### No repositories visible

> “I couldn't find a repository I can access. You may need to create one or give Codize access to the right repository.”

Provide a beginner-friendly path, not raw OAuth error text.

### Repository changed externally

Explain clearly and allow reconnecting.

## Do not

- request broad write permissions by default;
- assume every beginner already has a GitHub repository;
- trap the user if connection fails;
- mix GitHub setup with a long Git course.

---

# 29. Return From Coding Agent

**Surface type:** Build mode.

## Goal

Quickly learn the student's current outcome and route to checking, inspection, or recovery.

## Entry condition

Student clicks **I'm back**, returns to the browser tab, or Codize detects an updated connected repository and the user reopens Build.

## What the user sees

Character:

# **How did it go?**

Options:

**It worked**

**Something's wrong**

**I'm not sure**

If GitHub is connected, Codize may already have loaded the diff, but should not front-load it unless relevant.

## Branches

### It worked

Proceed to Check.

### Something's wrong

Proceed to Recovery Mode.

### I'm not sure

Proceed to Inspection/Check hybrid.

## State writes

- `current_change.student_reported_outcome`

## Do not

- ask the student to summarize every file manually if the repo already exposes it;
- accept “AI said done” as proof of success.

---

# 30. Check - Guided First Version

**Surface type:** Build check card.

## Goal

Teach the distinction between AI claiming completion and the student observing behavior.

## Early beginner version

Codize:

> “Let's actually try it once before we move on.”

Card:

```text
TRY THIS

Add Alex with jersey #7.

What happened?

[ Worked ]
[ Partly worked ]
[ Didn't work ]
[ I'm not sure ]
```

The suggested check must be tightly tied to the student's own “done looks like” statement.

## Later version

Ask first:

> **“What would you try yourself to see whether this works?”**

Input.

**Need help?**

After student proposes a check, they run it and report what happened.

## System behavior

The learning engine chooses whether Codize supplies a check, asks the student to originate one, or skips explicit prompting because the student already demonstrated testing.

## State writes

- `current_change.check.plan`
- `current_change.check.source = codize/student`
- `current_change.check.result`
- learner evidence for testing.

## Do not

- call the change “verified” solely because the student clicked Worked;
- turn every check into a multi-test QA suite;
- give five edge cases when one simple behavioral check is enough.

---

# 31. Connected Change Summary

**Surface type:** Structured card inside Build.

## Goal

Compare what the student intended with what the repository shows without making Codize the final judge.

## Entry condition

Repository is connected and a meaningful diff exists.

## Example

```text
WHAT CHANGED

You asked for:
Player totals

Changed:
✓ StatsPanel.jsx
✓ PlayerCard.jsx

Also changed:
? storage.js

Were you expecting storage.js to change?

[ Yes ]
[ No ]
[ I'm not sure ]
```

## Experienced-student version

Before Codize highlights the suspicious file:

> **“Anything surprising in what changed?”**

Student inspects first.

After their response, Codize may reveal:

> “I also noticed `storage.js` changed, even though the prompt was about totals.”

## System behavior

Codize may classify changes as likely expected, potentially out-of-scope, or unknown, but the UI should preserve uncertainty.

## State writes

- `current_change.diff_summary`
- `student_judgment` for notable changes.

## Do not

- say “storage.js should not have changed” unless that is actually established;
- hide uncertainty;
- require students to manually categorize every line of a diff.

---

# 32. Diff / Code Inspection Drawer

**Surface type:** Drawer or split pane.

## Goal

Let the student inspect relevant code without losing the Build conversation context.

## Desktop layout

```text
┌────────────────────────────┬────────────────────────────┐
│ CODIZE                     │ CHANGE INSPECTION          │
│                            │                            │
│ "Why do you think this     │ storage.js                 │
│ changed?"                  │                            │
│                            │ - old code                 │
│ [answer...]                │ + changed code             │
└────────────────────────────┴────────────────────────────┘
```

## Mobile layout

Full-screen code subview with:

- file name;
- changed sections;
- beginner-friendly summary toggle;
- back to conversation.

## Available views

- beginner summary;
- actual diff;
- relevant file context.

The beginner summary must be labeled as an interpretation, not source truth.

## Socratic behavior

If inspection itself is the learning target, ask the student what they notice before showing Codize's interpretation.

If inspection is not the target and the diff is large, Codize may reduce clerical burden by highlighting the relevant area.

## Do not

- replace the real code with only an AI summary;
- dump a massive raw diff without navigation;
- automatically decide the student's judgment.

---

# 33. Tiny Understanding Interaction

**Surface type:** Inline concept card plus question.

## Goal

Build a causal mental model when a new concept or important relationship appears.

## Entry conditions

At least one is true:

- meaningful new programming concept;
- student confusion;
- consequential relationship;
- good transfer opportunity;
- learning engine specifically chooses it.

## Example

Card:

# **One thing worth knowing**

> “When you click Add, JavaScript runs code connected to that click. That's called an event handler.”

Question:

> **“What action causes the player-adding code to run?”**

Student:

> Clicking Add.

Codize:

> “Yep.”

## Question progression

Use learner level to progress:

- concrete;
- causal;
- predictive;
- transfer.

## Need Help

Available when the question is challenging.

## State writes

- concept encountered;
- support used;
- response evidence;
- confidence only if the student explicitly gives confidence, not inferred as mastery.

## Do not

- force understanding checks after every trivial change;
- award fake mastery percentage;
- make the student explain every line of code;
- give a five-question quiz when one causal question is enough.

---

# 34. Change Completion

**Surface type:** Short Build completion state.

## Goal

Close the current change, update memory, and move the student forward without ceremony.

## Example

> **“Nice. Player totals are working.”**

Small summary if useful:

```text
DONE
✓ Player totals
✓ Checked with Alex #7
```

Optional small achievement if genuinely earned.

Primary action:

**Back to Project**

Secondary:

**Keep building** if a clear next plan item exists.

## System behavior

Update:

- project truth;
- build history;
- known working behavior;
- current plan item completion;
- learner evidence;
- unresolved uncertainty.

Do not mark uncertain behavior as confirmed.

## State writes

- `current_change.status = complete`
- history entry;
- plan progress;
- learner model updates.

---

# 35. Later / Adaptive Build Flow

## Goal

Make Codize visibly less repetitive over time.

## Example early behavior

Codize asks:

- what done looks like;
- what should stay untouched;
- what effort to use;
- what to test.

## Example later behavior

Student writes:

> “Add filters. Keep storage untouched. I think Standard effort is enough.”

Codize recognizes:

- scope is bounded;
- boundary exists;
- effort is plausible.

Codize response:

> “Looks good.”

Prompt Preview appears directly.

No redundant questions.

## Adaptation rules

- Fade per habit, not globally.
- Reintroduce support when context becomes novel or risky.
- Asking for help does not permanently lower a student.
- One good answer does not permanently mark mastery.
- Use varied evidence across different changes before treating behavior as recently independent.

## Visual expression of fading

The character may literally speak less.

Early:

> “Before you send that, let's make 'done' specific.”

Later:

> “Anything you'd change about this prompt?”

Later:

Character gives a small approval reaction and no extra question.

---

# 36. “Something Broke” Entry

**Surface type:** Persistent contextual action.

## Goal

Make recovery available immediately without requiring the student to find a special module.

## Entry points

- global **Something broke** action;
- Return state -> **Something's wrong**;
- Codize notices evidence of a failed check and offers recovery;
- first-time entry choice -> **Something broke**.

## Transition behavior

Same Build workspace.

Header changes subtly:

```text
RECOVERY
Let's figure out what happened before we change more code.
```

Character remains the same mentor.

## Do not

- navigate to a giant separate recovery dashboard;
- auto-generate a fix prompt immediately;
- scold the student for having a bug.

---

# 37. Recovery Mode - Symptom Capture

## Goal

Turn “it broke” into a concrete observed problem.

## Character opening

> “Okay. Let's figure out one thing before changing more code.”

First question:

> **“What were you trying to do when it stopped working?”**

Then:

> **“What happened instead?”**

Then, when useful:

> **“Was this working before the most recent change?”**

One question at a time.

## Need Help

If student gives vague answer such as “nothing works,” Codize asks for the first visible symptom:

> “What is the first thing you can point to that is different from what you expected?”

## State writes

- recovery intended behavior;
- observed symptom;
- last-known-working claim;
- student certainty.

---

# 38. Recovery Mode - What Changed?

## Goal

Connect the failure to recent project history without assuming causation.

## If GitHub connected

Codize can say:

> “The issue appeared after this change. These files changed.”

Show a compact change summary.

Do not say the latest change caused the bug unless evidence supports it.

## If GitHub not connected

Ask:

> **“What was the last thing your coding AI changed before this started?”**

If the student does not know:

> “That's okay. What was the last feature you asked it to work on?”

## State writes

- candidate relevant change;
- confidence / uncertainty.

---

# 39. Recovery Evidence Summary

**Surface type:** Automatically maintained card.

## Goal

Make known facts and uncertainty visible.

## Example

```text
WHAT WE KNOW

✓ Adding players worked before
✓ The issue appeared after storage was added
✓ Players disappear after refresh

WHAT WE DON'T KNOW YET

? Are players failing to save?
? Or are they failing to load?
```

## System behavior

Codize builds this from:

- student observations;
- known project history;
- repository evidence;
- previous checks.

Every item should retain provenance internally.

## Rules

Use different visual treatment for:

- student-observed fact;
- repository fact;
- Codize hypothesis;
- unresolved question.

Do not collapse them into one certainty level.

---

# 40. Recovery - Hypothesis / First Check

## Goal

Teach debugging as investigation rather than repeated patching.

## Question

> **“What do you think might be causing it?”**

If that is too advanced for the student, lower the difficulty:

> **“What could we check first to learn more?”**

Need Help available.

## Beginner support

Nudge:

> “We know the problem appears after refresh. What part of the feature deals with refresh?”

Guided clue:

> “There are two parts: saving the players and loading them again. Which one could we check first?”

Teach if necessary.

## State writes

- student hypothesis;
- proposed check;
- support level.

## Do not

- reveal the likely cause before the student has a reasonable chance to think, when debugging is the learning objective;
- force a hypothesis if the student lacks prerequisite knowledge. In that case, teach what can be checked.

---

# 41. Diagnostic Prompt Preview

**Surface type:** Prompt card within Recovery.

## Goal

Generate an investigation prompt rather than a blind fix prompt.

## Example

```text
INVESTIGATION PROMPT

The player form worked before localStorage was added.

Players now disappear after refreshing.

Do not rewrite the feature yet.

Help me determine whether players are failing to save
or failing to load. Inspect the current implementation
first and explain what you find.
```

Actions:

**Edit**

**Copy for Claude**

Optional:

**Why investigate first?**

## Why expansion

> “If the coding agent patches before you know what is failing, it can change more code without solving the real problem. Investigation gives the next change a reason.”

## System behavior

Record diagnostic prompt separately from normal feature prompt.

---

# 42. Recovery Return and Resolution

## Goal

Confirm what the investigation or fix revealed and reconnect to normal building.

## Return question

> **“What did you find?”**

Options may include:

- I found the cause;
- I learned something but it is not fixed;
- I'm still stuck.

## If cause found

Codize asks for the shortest useful description in the student's words.

Then help prepare a bounded correction prompt if needed.

## Final check

Use the original broken behavior.

Example:

```text
Add player
→ refresh
→ player remains
```

## Recovery completion card

```text
FIXED

Problem
Players disappeared after refresh.

Cause
Loading did not run when the page opened.

Check
Add player → refresh → player remains.
```

Primary action:

**Back to building**

## Optional achievement

Example:

🔍 **Before the Patch**

> You checked what was failing before asking AI to rewrite it.

Only show if the evidence actually supports it.

---

# 43. Already-Building Entry

## Goal

Let an existing project enter Codize without repeating new-project onboarding.

## Entry condition

Student chose **I'm already building something**.

## Character copy

> **“What are you building?”**

Student describes project.

Then:

> **“What are you trying to change right now?”**

Optional:

> **“What already works that I should know about?”**

Only ask if Codize does not have repository context.

## GitHub timing

Offer connection earlier than in the new-project flow:

> “If your project is on GitHub, connecting it lets me understand what already exists instead of making you explain everything manually.”

Actions:

**Connect GitHub**

**I'll describe it for now**

## System behavior

Gather minimal context, infer candidate project truth, and clearly separate confirmed user statements from repository-derived facts.

## Next state

Current-Change Confirmation.

## Do not

- force the student to rebuild a complete project roadmap before doing their current task;
- make them classify their app;
- ask five intake questions if GitHub can answer them.

---

# 44. Recovery-First Entry

## Goal

Give immediate value to someone who arrived because AI broke something.

## Entry condition

Student chose **Something broke** before a project exists in Codize.

## Minimal setup

Question 1:

> **“What are you building?”**

Question 2:

> **“What is broken right now?”**

Question 3:

> **“What was the last thing the AI changed before this started?”**

Offer GitHub connection early if useful.

Then enter standard Recovery Mode.

After recovery, Codize asks:

> **“Want me to keep this project here so I can help with the next change too?”**

Primary:

**Keep building with Codize**

Secondary:

**Not now**

---

# 45. Ask About My Project

**Surface type:** Build question mode.

## Goal

Allow project-grounded curiosity without turning Codize into a general-purpose chatbot.

## Entry points

- Build quick action;
- Project Home secondary action;
- code inspection drawer.

## Prompt

> **“What do you want to understand about your project?”**

Examples shown subtly:

- Why do my players stay after refresh?
- Which file controls this button?
- Why did this change affect the other page?
- What does this function do in my app?

## System behavior

Use project memory, repository, learner model, and teaching policy.

If the question is answerable with a direct explanation and there is no learning reason to delay it, answer directly.

If a Socratic prompt will help the student reason from what they already know, ask first.

## Out-of-scope generic question

Codize may answer briefly if harmless, but should maintain product identity:

> “I can help most when the question connects to your project.”

Do not aggressively refuse normal coding questions.

---

# 46. Learning Page

**Conceptual route:** `/app/project/:projectId/learning`

## Goal

Let students optionally explore what they have encountered and what they are becoming more independent at without cluttering Project Home.

## Tone

Curious and motivating, not report-card-like.

## Top-level sections

### Concepts

Example:

```text
EVENT HANDLERS
Recently independent

LOCAL STORAGE
Practiced

AUTHENTICATION
Not encountered
```

### AI-building habits

```text
SCOPING
Recently independent

BOUNDARIES
Practiced

TESTING
Recently independent

DEBUGGING
Guided
```

### Achievements

Examples:

- Caught It Yourself;
- Your Test, Your Idea;
- Before the Patch;
- Connected the Dots;
- Recovered.

## State language

Use:

### New

Encountered.

### Guided

Used with support.

### Practiced

Used more than once.

### Recently independent

Recently demonstrated without help.

Avoid permanent mastery claims.

## Visual direction

Use clear concept/habit cards, compact status labels, achievements, and connections to meaningful cosmetic unlocks. The approved direction does **not** use a decorative learning constellation. Avoid a fake skill tree or map unless later testing demonstrates a real navigational purpose.

## Do not

- show one global score;
- rank students;
- use percentage mastery;
- penalize help;
- make this page necessary to continue building.

---

# 47. Learning Concept Detail

**Surface type:** Page, drawer, or detail panel.

## Goal

Connect a concept to the student's real project history.

## Example

```text
LOCAL STORAGE

Current experience
Practiced

You've used it in:
✓ Volleyball Tracker → Save Players
✓ Homework Tracker → Save Assignments

What you've worked with:
• saving data in the browser
• loading data after refresh

Recent challenge:
You predicted what happens when loading fails.
```

Optional action:

**Try a quick challenge**

This is optional future functionality, not required for V2 MVP.

## Do not

- become a textbook article detached from the project;
- imply concept card completion equals mastery.

---

# 48. Gamification Surface Rules

## Goal

Use playful rewards to reinforce independence and meaningful progress.

## Good reward triggers

- student independently notices an out-of-scope change;
- student proposes and runs a useful check without hints;
- student investigates before asking for a patch;
- student explains a new causal relationship without support;
- student completes a meaningful first version;
- student applies a learned habit in a new context.

## Bad reward triggers

- opening Codize;
- filling every field;
- daily login;
- uploading “evidence”;
- spending more time in the app;
- asking fewer questions simply to avoid losing points.

## Character unlocks

Possible later reward:

- new expression;
- accessory;
- background detail;
- small character animation.

The unlock should represent progress. It is not the learning measurement itself.

## Daily streaks

Not recommended for the initial product because coding is episodic and Codize should not optimize for daily usage.

---

# 49. History Page

**Conceptual route:** `/app/project/:projectId/history`

## Goal

Provide a human-readable record of what was built, what changed, what was checked, and what was learned.

## Example timeline

```text
TODAY

✓ Add player totals
  Checked successfully
  Learned: derived totals

✓ Fixed refresh bug
  Cause: load function wasn't called
  Achievement: Before the Patch

YESTERDAY

✓ Save players
  Learned: localStorage

✓ Add player list
  Unexpected storage.js change inspected
```

## Filters later

Potential:

- All;
- Builds;
- Bugs;
- Learning;
- Git commits.

Do not build complex filtering until needed.

## System behavior

History is generated from structured state, not only chat transcript.

## Do not

- expose raw artifact IDs;
- make students understand internal provenance objects;
- turn History into analytics overload.

---

# 50. History Change Detail

## Goal

Allow the student to understand one past change and use it during debugging or reflection.

## Example

```text
ADD PLAYER TOTALS

You wanted:
Show total kills for each player.

Prompt:
[View prompt]

Changed:
StatsPanel.jsx
PlayerCard.jsx

Check:
Totals updated correctly.

What you learned:
Derived values

Commit:
abc123
```

Optional:

- View diff;
- Ask about this change;
- Use as recovery starting point.

## Do not

- show technical metadata more prominently than the student's intent and result.

---

# 51. First-Version Completion

**Surface type:** Celebration state.

## Goal

Create a meaningful reward, connect project progress to learning progress, and reopen the student's larger ambition.

## Entry condition

All confirmed first-version items are complete enough to call the first version working.

## What the user sees

```text
🎉 YOUR FIRST VERSION IS WORKING

✓ Add players
✓ Record stats
✓ Show totals
✓ Save locally
```

Then two tracks:

```text
YOU BUILT                 YOU LEARNED

Player system             Event handlers
Stat tracking             State
Totals                    Data relationships
Saving                    localStorage
                           Testing
                           Debugging
```

Character:

> “You built the first version. Where do you want to take it next?”

Actions:

**Add a saved idea**

**Improve what I have**

**Start another project**

Saved ambitions reappear:

```text
SAVED FOR LATER

Accounts
Team sharing
AI analysis
```

## Gamification

This is an appropriate moment for a stronger character animation or meaningful unlock.

## Do not

- turn completion into a final exam;
- claim mastery of every concept used;
- hide the student's original bigger goals.

---

# 52. Project Switcher / Multi-Project Surface

**Conceptual route:** `/app/projects`

## Goal

Support multiple projects without making a projects dashboard the first experience for a new user.

## Example

```text
YOUR PROJECTS

● Volleyball Tracker
  Last worked on today

○ Homework Tracker
  Last worked on Aug 2

+ New project
```

## Project switching

Switching stores current state and loads the target project's project truth, build history, learner context, connected repo, and agent preference.

Learner concepts may exist across projects, but project truth must remain project-specific.

---

# 53. Settings

**Conceptual route:** `/settings`

## Sections

### Coding AI

```text
Current agent
Claude Code

Change ›
```

### GitHub

```text
Connected repository
maya/volleyball-tracker

Manage ›
```

### Presentation

```text
Dialogue sounds     ON
Animations          ON
Reduced motion      SYSTEM
```

Character selection and accessories do **not** live in Settings; they live in the dedicated Character destination.

### Learning

Potential future controls for optional explanations or challenge preferences, but do not include a “never make me think” mode.

### Account

Normal account controls.

## Do not

- bury core project actions here;
- make the user configure pedagogy before using the app.

---

# 53A. Character Customization Destination

**Conceptual route:** `/character`

## Goal

Give the student a dedicated secondary destination for switching companions, previewing characters, equipping accessories, and understanding meaningful unlocks without cluttering Project Home or Settings.

## Navigation

`Character` appears above `Settings` at the bottom of the signed-in sidebar. It is secondary to Project / Build / Learning / History.

## Core content

- current character preview;
- available characters;
- locked characters with truthful unlock reason/progress when appropriate;
- accessories grouped by supported slot;
- equipped / unlocked / locked state;
- immediate preview before saving;
- meaningful unlock explanation tied to project/learning evidence.

## Unlock principles

Characters and accessories can unlock from meaningful project milestones, concepts practiced/used independently, testing/debugging/recovery achievements, and other evidence-backed accomplishments. Do not unlock cosmetics merely for login streaks, clicks, or filling required fields.

## Relationship to Settings

Settings owns presentation toggles such as dialogue sound, animation, and reduced motion. Character owns character choice and cosmetics.

---

# 54. Character Behavior Specification

## Functional role

The character is the conversational face of Codize's teaching system.

It should make the product feel like a mentor, not a form wizard.

## Character prominence

### Landing

Large and expressive.

### Build

Medium, near current dialogue.

### Recovery

Medium, with expressions that communicate focus rather than panic.

### Project Home

Small/contextual.

### Learning

Can celebrate or react to progress.

### History

Minimal.

### Character

Large inside customization and preview states; otherwise secondary.

### Settings

None or nearly none.

## Emotional tone

The character may be:

- curious;
- encouraging;
- concise;
- mildly playful;
- confident enough to challenge a bad idea;
- comfortable saying “I don't know yet.”

The character should not be:

- patronizing;
- hyperactive;
- constantly praising trivial actions;
- sarcastic about mistakes;
- overly school-teacher-like;
- overly corporate.

## Example reactions

Student figures something out:

> “Yep. You got it.”

Student says “I don't know”:

> “That's useful. Let's figure out one thing we know for sure.”

Student repeatedly asks AI to fix:

> “Before we change more code, what actually stopped working?”

Student already demonstrates the habit:

> small approval reaction, no extra lecture.

---

# 55. Dialogue Sound Specification

## Goal

Give the character identity without distracting from the work.

## Behavior

- original retro text-blip sound during character dialogue only;
- sound can be toggled on/off globally;
- no copyrighted Undertale audio or direct reproduction;
- do not play sound for user text, buttons, tooltips, code, or every animation;
- remember preference across sessions;
- respect browser and accessibility expectations.

## UI

Visible speaker toggle near character dialogue or global app chrome.

Settings also exposes:

```text
Dialogue sounds: ON / OFF
```

## Reduced motion

Character animation should respect reduced-motion settings independently from sound.

---

# 56. Chat Message / Component Types

The Build experience should use structured message types rather than one generic bubble component.

Required conceptual types:

### `CHARACTER_MESSAGE`

Normal mentor dialogue.

### `QUESTION`

One primary open or constrained question.

### `TEXT_RESPONSE`

Student input.

### `MULTIPLE_CHOICE`

Small number of meaningful choices.

### `DECISION_CARD`

Structured product decision such as First Version.

### `LEARNING_CARD`

Tiny concept explanation.

### `PROMPT_PREVIEW`

Generated coding-agent prompt.

### `EFFORT_SELECTOR`

Quick/Standard/Deep.

### `PROJECT_PLAN_CARD`

Plan proposal or plan summary.

### `CHANGE_SUMMARY`

Prompt intent vs actual repository changes.

### `DIFF_INSPECTION`

Code/diff side surface.

### `CHECK_CARD`

Test/observation interaction.

### `UNCERTAINTY_SUMMARY`

What we know / do not know.

### `ACHIEVEMENT`

Meaningful reward.

### `CONCEPT_CARD`

Concept history/details.

### `HANDOFF_CARD`

Move to external coding agent.

The LLM generates copy inside approved component types. It does not invent new interface primitives arbitrarily.

---

# 57. Build State Machine

Conceptual state machine:

```text
READY
  ↓
CONFIRM_CHANGE
  ↓
INTERVENTION_DECISION
  ├── SKIP
  │     ↓
  └── INTERVENE
        ↓
      TEACH_OR_ASK
        ↓
PREPARE_PROMPT
  ↓
EFFORT_IF_NEEDED
  ↓
HANDOFF
  ↓
WAITING_FOR_RETURN
  ↓
RETURN
  ├── WORKED
  │      ↓
  │    CHECK
  │      ↓
  │    INSPECT_IF_NEEDED
  │      ↓
  │    UNDERSTAND_IF_NEEDED
  │      ↓
  │    COMPLETE
  │
  ├── UNSURE
  │      ↓
  │    INSPECT
  │      ↓
  │    CHECK_OR_RECOVER
  │
  └── BROKEN
         ↓
       RECOVERY
         ↓
       INVESTIGATE
         ↓
       DIAGNOSTIC_HANDOFF
         ↓
       RETURN
         ↓
       CHECK
         ↓
       RESOLVE
```

## State-machine rule

The LLM cannot jump from one state to another simply because it thinks another action would be helpful.

The orchestrator controls legal transitions.

---

# 58. Core Teaching Decision Matrix

A future rules engine can use a matrix like this.

| Situation | Default Codize behavior |
|---|---|
| First meaningful prompt | Teach “done” |
| Student already defines observable outcome | Skip “done” question |
| Existing working feature can be affected | Introduce/ask boundary |
| Student already supplies a boundary | Skip boundary lesson |
| First simple success | Codize supplies a check |
| Student has practiced testing | Ask student for the check |
| Student already tests independently | Stay quiet |
| Diff touches unexpected area | Ask student judgment / inspect |
| Student is new to concept | Tiny explanation + one question |
| Student is already comfortable with concept | Skip explanation |
| Bug appears | Recovery mode before fix prompt |
| High-risk system appears | Add relevant slowdown |
| Student asks for help | Increase support without punishment |
| Student is repeatedly independent | Reduce prompts |

---

# 59. Project Memory Model - UX Implications

The user should not see a raw memory database, but the UX depends on three structured layers.

## 59.1 Project truth

Examples:

```text
Project: Volleyball Tracker
Current V1: Local single-user stat tracker
Not yet: Accounts, cloud sync, AI analysis
Known working: Player creation, player list
Current work: Record stats
```

## 59.2 Build history

```text
Change #1: Player form - checked
Change #2: Player list - checked
Change #3: Persistence - unresolved refresh issue
```

## 59.3 Learner model

```text
Task scoping: usually independent
Boundaries: practiced
Testing: still benefits from prompts
Debugging: new
localStorage: guided
Event handlers: recently independent
```

## UX rule

Codize should use memory to remove repeated questions, not merely to produce more personalized text.

Good:

> “You've been defining your changes clearly, so I'll skip that part.”

Bad:

> “I remember you like volleyball!”

when that memory does not materially improve the current task.

---

# 60. Truth and Uncertainty UI Rules

Codize must distinguish information sources internally and reflect uncertainty in language.

Potential source categories:

- student said;
- repository shows;
- coding agent claimed;
- student observed;
- Codize inferred;
- unresolved.

## Example

Bad:

> “The storage change caused the bug.”

when only temporal order is known.

Better:

> “The problem appeared after the storage change. We have not confirmed the cause yet.”

## UI language

Use:

- “I noticed...”
- “The repository shows...”
- “You said...”
- “It looks like...”
- “We don't know yet...”

Avoid false certification.

---

# 61. High-Risk Change UX

## Goal

Add appropriate friction when misunderstanding has higher consequences.

Examples:

- authentication;
- authorization;
- per-user data access;
- secrets;
- database migrations;
- destructive data actions;
- deployment configuration;
- major refactors;
- payment-related systems if ever relevant;
- unfamiliar architecture.

## Behavior

Codize may introduce more than one check when necessary.

Example for authentication:

1. Clarify what the user should be allowed to do.
2. Clarify what a different user should not be allowed to do.
3. Generate prompt with explicit ownership boundary.
4. Ask student to test both allowed and disallowed access where appropriate.

## Tone

Explain why the extra step exists.

> “I'm slowing down here because this change decides who can access whose data.”

## Do not

- bury the student in a generic security checklist;
- claim the app is secure after one test;
- create a fake “Security passed” badge.

---

# 62. Loading States

## General rule

Never show a blank conversational area while Codize is thinking or fetching project context.

## Character-thinking state

Short:

> “Looking at your latest change...”

Use subtle animation.

## GitHub fetch

> “Checking what changed in your project...”

## Long-running analysis

If more than a few seconds, show progress categories rather than fake percentages.

Example:

```text
✓ Loaded latest commit
● Comparing changed files
○ Preparing the next question
```

## Do not

- show fake 73% progress;
- animate the character endlessly with no status;
- block unrelated navigation if analysis is not required.

---

# 63. Error States

## Principle

Errors should preserve student work and provide a next action.

### AI generation failure

> “I couldn't build the next prompt just now. Your answers are saved.”

Actions:

**Try again**

**Edit my answers**

### GitHub fetch failure

> “I couldn't load the latest project changes. You can retry or keep going without GitHub for now.”

### Lost external-agent return context

> “I still have the prompt you were working on. Did the coding AI finish it?”

Options:

- Yes;
- Not yet;
- Start over from this change.

### Unexpected server error

Use plain language and preserve the active change.

## Do not

- discard student answers;
- reset the project plan;
- expose raw backend stack traces to students;
- force a complete restart after recoverable failure.

---

# 64. Empty States

## Project Home with no project

Redirect to first-time entry or project creation.

## Learning with no concepts yet

> **“Your learning map will grow as your project does.”**

> “Build your first change and I'll start connecting what you use to what you're learning.”

CTA:

**Start building**

## History with no completed changes

> “Your project history will show up here after your first change.”

## Build Plan empty

> “Let's decide the first working piece.”

---

# 65. Responsive Behavior

## Desktop

- left navigation shell;
- Build conversation centered or slightly left-weighted;
- code/diff inspection in right drawer;
- character near dialogue, not consuming excessive width.

## Tablet

- collapsible navigation;
- drawer may overlay rather than split.

## Mobile

- bottom navigation;
- one column;
- character smaller;
- structured cards full width;
- diff inspection as full-screen subview;
- sticky primary action only when it does not obscure content;
- avoid horizontal scroll except code where absolutely necessary.

## Progressive-disclosure rule

Mobile should not solve density by shrinking text. It should reveal less at once.

---

# 66. Accessibility

## Required principles

- keyboard-accessible controls;
- visible focus states;
- semantic headings;
- proper labels for form fields;
- color is never the only indicator of state;
- dialogue sound optional;
- reduced-motion support;
- readable contrast;
- character animation never required to understand content;
- screen-reader-friendly status updates for dynamic chat states;
- code/diff views remain navigable;
- success/failure labels use text and icons, not color alone.

## Character

Character is decorative/supportive unless the dialogue itself is text. Never require reading an expression to understand the next action.

## Sound

No information may exist only in sound.

---

# 67. Forbidden UX Patterns

The following patterns should be treated as design regressions unless explicitly reconsidered.

## 67.1 Multi-dashboard redundancy

Do not show:

- Active Project;
- Current Project;
- Start Here;
- Recommended Starting Point;
- What To Do Next;
- Current Assignment;

all describing the same thing.

## 67.2 Giant all-at-once Build page

Do not simultaneously show:

- assignment confirmation;
- lesson;
- three questions;
- prompt builder;
- effort selector;
- GitHub connection;
- testing card;
- learning progress.

## 67.3 Generic chatbot drift

The LLM should not decide to create arbitrary quizzes, plans, or debugging flows outside the orchestrated state.

## 67.4 Mandatory explanation after every change

Understanding interactions are contextual.

## 67.5 Mandatory full workflow for trivial changes

A color change should not require a Defense-style process.

## 67.6 Fake mastery

No:

> “JavaScript mastery 91%.”

## 67.7 Daily streak dependence

Do not punish students for not coding every day.

## 67.8 Gamifying compliance

Do not reward box completion for its own sake.

## 67.9 AI does the learning target

If the goal is for the student to propose a test, Codize does not provide the test first.

## 67.10 AI silently edits code

Codize should not become an invisible coding agent inside the mentoring flow.

## 67.11 Hidden uncertainty

Do not turn inference into fact.

## 67.12 Jargon-first UX

Do not require the student to understand internal educational or software-engineering terminology before taking action.

---

# 68. Figma Component Inventory

The barebones Figma should create reusable components for at least the following.

## Global

- desktop side navigation;
- mobile bottom navigation;
- project switcher;
- page header;
- connection indicator;
- agent indicator;
- sound toggle.

## Character

- large placeholder;
- medium placeholder;
- small placeholder;
- speaking state;
- thinking state;
- success reaction;
- focused/recovery state.

Use placeholders until final character design exists.

## Conversation

- Codize message;
- student message;
- open text question;
- multiple choice;
- text input composer;
- Need Help link;
- Why? link;
- hint expansion.

## Structured cards

- First Version card;
- Build Plan card;
- Current Change card;
- Prompt Preview;
- Effort Selector;
- Agent Handoff;
- GitHub introduction;
- Check card;
- Change Summary;
- Recovery Evidence Summary;
- Concept card;
- Achievement card;
- Completion card.

## Inspection

- diff drawer;
- file list;
- beginner summary;
- raw diff view.

## Learning

- concept tile;
- habit tile;
- state badge;
- achievement tile;
- concept detail.

## History

- timeline entry;
- bug/recovery entry;
- change detail.

## Empty/error/loading

- empty state;
- error state;
- reconnect state;
- character thinking state;
- repository loading state.

---

# 69. Figma Frame Inventory

The initial barebones Figma should include at minimum these frames or prototype states.

## Public

1. Landing desktop.
2. Landing mobile.
3. Signup/login.

## First-time onboarding

4. What brings you here?
5. New idea prompt.
6. Idea clarification.
7. First Version proposal.
8. First Version edit.
9. Guided resistance.
10. Build Plan proposal.
11. Project Home empty-first-build state.

## First build

12. Current Change confirmation.
13. First “done” lesson.
14. Vague-answer Socratic follow-up.
15. Need Help level 1.
16. Need Help level 2/teach.
17. Coding-agent selection.
18. Prompt Preview.
19. Why prompt is structured this way.
20. Effort introduction.
21. Agent Handoff.
22. Return - How did it go?
23. Guided check.
24. Tiny understanding interaction.
25. Change complete.
26. Project Home after first change.

## GitHub

27. GitHub introduction.
28. GitHub familiarity question.
29. GitHub connection/setup.
30. Connected confirmation.

## Later adaptive build

31. Current change with student already supplying boundary.
32. Prompt Preview with skipped lesson.
33. Student-originated effort selection.
34. Student-originated check.

## Inspection

35. Change Summary.
36. Diff drawer desktop.
37. Diff subview mobile.
38. Student unsure about unexpected change.

## Recovery

39. Recovery entry.
40. Symptom question.
41. What we know / don't know.
42. Hypothesis/check question.
43. Need Help in recovery.
44. Diagnostic Prompt.
45. Recovery return.
46. Recovery fixed summary.

## Secondary

47. Learning page.
48. Concept detail.
49. History page.
50. History change detail.
51. Build Plan page.
52. Project switcher.
53. Settings.
54. First-Version completion celebration.

## System states

55. Loading repository changes.
56. GitHub error.
57. AI generation error with saved work.
58. Empty Learning page.
59. Empty History page.

This is intentionally more states than final routes because the value of the Figma prototype is showing transitions and progressive disclosure, not just page count.

---

# 70. Prototype Connections to Build in Figma

The first clickable prototype should prove these paths.

## Prototype A - New beginner first session

```text
Landing
→ Start Building Free
→ Entry choice
→ New idea
→ First Version
→ Plan
→ Project Home
→ Current Change
→ Define done
→ Prompt
→ Effort
→ Handoff
→ Return worked
→ Check
→ Understanding
→ Complete
→ Home
```

## Prototype B - Student resists simplification

```text
First Version
→ Change this
→ insists on full app
→ Guided Resistance
→ Break into pieces OR Build it all anyway
```

## Prototype C - Need Help

```text
Learning question
→ Need Help
→ Nudge
→ Another hint
→ Teach
→ return to answer
```

## Prototype D - GitHub connection

```text
Post-first-change
→ GitHub introduction
→ What's GitHub?
→ beginner explanation
→ connect
→ connected confirmation
```

## Prototype E - Unexpected change

```text
Return
→ Change Summary
→ I'm not sure
→ Diff drawer
→ student judgment
→ continue
```

## Prototype F - Recovery

```text
Something broke
→ symptom
→ recent change
→ What we know
→ student check
→ Diagnostic Prompt
→ Return
→ Fixed
→ Project Home
```

## Prototype G - Fading guidance

Show a comparison between:

- first change with several guided interactions;
- later change where student has already supplied boundaries, effort, and test behavior so Codize skips those interventions.

This is important because a static prototype could accidentally make V2 look as repetitive as V1.

---

# 71. Copy Style Rules

Codize copy should sound like a smart, approachable mentor.

## Use

- short sentences;
- plain English;
- project-specific language;
- one question at a time;
- calm confidence;
- occasional playful character voice;
- concrete examples.

## Avoid

- “Let's pause.”
- “Let's take a breath.”
- heavy praise after every action;
- academic jargon without reason;
- “Incorrect” for open reasoning;
- long lectures;
- corporate phrases such as “workflow artifact”; 
- language that makes AI use sound shameful.

## Good examples

> “What should still work after this change?”

> “You asked for filtering, but `storage.js` changed too. Were you expecting that?”

> “We know the bug appeared after storage was added. We don't know yet whether saving or loading is failing.”

> “You've been doing this part on your own, so I'll skip it.”

## Bad examples

> “Complete the verification artifact before progressing.”

> “Your response failed the understanding gate.”

> “You have achieved 92% mastery.”

---

# 72. Analytics / Event Model for Validation

The UI should be designed so important behavior can later be measured without invasive tracking.

Useful events include:

- started project;
- accepted/edited first version;
- overrode guided resistance;
- generated first prompt;
- used Need Help and hint level;
- edited generated prompt;
- selected effort independently;
- returned from agent;
- student-originated check;
- unexpected change noticed by student before Codize;
- entered recovery;
- formed hypothesis before diagnostic prompt;
- completed recovery;
- demonstrated habit without prompt;
- connected GitHub;
- skipped optional explanation;
- opened Learning;
- returned for another meaningful change.

## Privacy/product principle

Collect behavior needed to improve Codize and evaluate learning, not every possible interaction simply because it can be logged.

---

# 73. MVP Cut Line

The exact UX describes the full intended V2 interaction model. The first implementation does not need every later enhancement.

## Core V2 MVP surfaces

- landing page;
- auth;
- first-time entry;
- new idea capture;
- First Version shaping;
- lightweight Build Plan;
- Project Home;
- Build workspace;
- current-change confirmation;
- one Socratic habit intervention;
- Need Help ladder;
- Prompt Preview;
- agent selection first when agent is unknown;
- student-first effort selection with one retry/reveal branch;
- Agent Handoff;
- Return;
- simple Check;
- tiny Understanding interaction;
- Something Broke recovery;
- basic structured project memory;
- basic learner evidence;
- simple Learning page;
- simple History page;
- basic Character destination with starter character/customization shell.

## Early but potentially second slice

- GitHub connection;
- automatic diff comparison;
- diff inspection drawer;
- richer gamification/accessory unlock catalog;
- concept detail pages;
- advanced adaptive fading;
- multiple projects;
- optional micro-challenges.

The exact cut should be decided after the V1→V2 technical mapping and migration dependency review. Figma is already the current visual reference.

---

# 74. Figma / Implementation Handoff Criteria

The approved Figma is the current visual reference. Before implementation begins, a reviewer should be able to answer all of the following from the Figma plus this behavior spec without relying on old V1 screens:

1. What is Codize?
2. What does a new user do first?
3. How does an idea become a smaller first version?
4. Can the student override Codize?
5. What does Project Home prioritize?
6. What does the Build workspace feel like?
7. Where does the character appear?
8. What is one example of Socratic teaching?
9. How does Need Help work?
10. How is the coding-agent prompt shown?
11. Where does effort-level teaching happen?
12. How does the student leave for their coding agent and return?
13. What happens when the student says it worked?
14. What happens when AI changed something unexpected?
15. How does Recovery differ from blind reprompting?
16. Where does GitHub enter and why?
17. Where can the student see what they learned?
18. How does the experience become less guided later?
19. What happens when the first version is complete?
20. Does every major screen have one obvious primary action?

If a future Figma edit changes one of these behaviors, update this document or explicitly record the exception before implementation.

---

# 75. Canonical End-to-End Flow

```text
PUBLIC LANDING PAGE
        ↓
SIGN UP
        ↓
WHAT BRINGS YOU HERE?
   ↙          ↓          ↘
NEW IDEA   EXISTING    SOMETHING BROKE
   ↓        PROJECT          ↓
IDEA         ↓           RECOVERY
   ↓     MINIMAL CONTEXT      │
FIRST VERSION                 │
   ↓                          │
BUILD PLAN                    │
   └─────────────┬────────────┘
                 ↓
            PROJECT HOME
                 ↓
      AGENT KNOWN FOR PROJECT?
          ↙ yes       no ↘
           │        CHOOSE AGENT
           └──────────┬───────
                      ↓
                CURRENT CHANGE
                      ↓
           LEARNING ENGINE DECIDES
        ↙         ↓         ↘
      SKIP    ONE HABIT   SLOW DOWN
        \         |         /
                 ↓
          PROMPT PREPARATION
                 ↓
          EFFORT IF NEEDED
                 ↓
           AGENT HANDOFF
                 ↓
       EXTERNAL CODING AGENT
                 ↓
              RETURN
       ↙          ↓          ↘
    WORKED      UNSURE      BROKE
       ↓          ↓          ↓
     CHECK      INSPECT    RECOVERY
        \          |        /
         \         |       /
             UNDERSTAND
                 ↓
          COMPLETE CHANGE
                 ↓
         UPDATE PROJECT STATE
         UPDATE LEARNER STATE
                 ↓
            PROJECT HOME
                 ↓
             NEXT CHANGE
                 ↓
          LESS HELP OVER TIME
                 ↓
       FIRST VERSION COMPLETE
                 ↓
      EXPAND / IMPROVE / NEW
```

---

# 76. Final UX Definition

Codize V2 should feel simple even though its internal system is sophisticated.

To the student, the experience should feel like:

> “Tell Codize what I want to build, work on one understandable change, think through the one thing that matters, take a good prompt to my coding AI, come back, check what actually happened, get help if something broke, and keep going.”

Underneath that experience, Codize maintains:

- structured project truth;
- build history;
- learner evidence;
- adaptive support;
- teaching constraints;
- external-agent context;
- repository context where connected;
- uncertainty and provenance;
- state-machine-controlled progression.

The student should not have to operate those systems directly.

The ultimate UX success condition is not that the student becomes faster at completing Codize flows.

It is:

> **The student gradually starts making bounded prompts, protecting working code, choosing appropriate effort, inspecting changes, testing results, debugging from evidence, and understanding important project relationships before Codize asks them to.**

When that happens, Codize should visibly become quieter.

The character is not becoming more powerful.

**The student is.**
