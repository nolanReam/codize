# Codize V2 Product Thesis

## Status

**Document purpose:** Canonical product thesis for Codize V2.

**Product stage:** Canonical V2 direction after UX/Figma definition; pre-implementation and pre-migration.

**Primary audience:** Founder, designers, engineers, future contributors, pilot instructors, and anyone evaluating whether a proposed feature belongs in Codize.

**Authority and synchronization:**

1. This Product Thesis is the highest-level V2 product authority.
2. The `Codize V2 Exact UX Specification` controls interaction behavior and state transitions.
3. The `Codize V2 Character System Blueprint` controls the character/customization subsystem only.
4. The `Codize V2 Technical Architecture and State Model` controls V2 implementation architecture, state, persistence boundaries, concurrency, security, and compatibility under the product/UX authorities.
5. The `Codize V2 Schema and Persistence Design` is subordinate to that architecture and fixes the physical MVP design for later implementation.
6. Future accepted Learning / Teaching Policy documents will control exact evidence qualification, fading, reintroduction, and high-risk teaching rules without overriding this thesis.
7. The approved Figma file controls visual composition, styling, component appearance, and responsive layout only: https://www.figma.com/design/QBGSdTLG7iQ2xEFzU7v0Li/Codize-V2-Product-Design
8. The V2 Journey and Screen/Surface Map were design-process documents and are not implementation authority once the Exact UX Specification exists.

If a later design decision changes behavior, synchronize the behavioral documents intentionally rather than allowing Figma or old V1 documentation to silently redefine the product.

**Core design rule:**

> **One project. One current change. One useful habit at a time.**

**North-star promise:**

> **Build something real with AI. Learn how it works as you go.**

**North-star outcome:**

> A beginner should be able to say:  
> **“I built this with AI, but I actually know what the important pieces do. I know how to make the AI work on one thing at a time, I check what it changed, and when something breaks I do not just keep telling it to fix it.”**

---

# 1. Executive Summary

Codize is a beginner-first learning environment for high school students who want to build real software with coding AI without becoming dependent on it.

The central problem is not simply that AI sometimes writes bad code. AI will continue improving. The deeper and more durable problem is that **AI can make a beginner’s project grow much faster than the beginner’s ability to understand, supervise, debug, and make decisions about that project**.

Traditional programming education often delays meaningful creation:

```text
learn syntax
→ learn loops
→ learn functions
→ complete exercises
→ eventually build something interesting
```

Pure vibe coding does the opposite:

```text
have an idea
→ ask AI to build everything
→ app appears
→ hope it works
```

Codize is intended to occupy the middle:

```text
have an idea
→ start building immediately with AI
→ learn the next useful concept or habit when it becomes relevant
→ check what AI actually did
→ understand enough to stay in control
→ keep building
```

The student’s project becomes more capable while the student becomes more capable.

Codize should not become another coding agent. Students continue using the coding AI they already prefer, such as Codex, Claude, Cursor, ChatGPT, Replit, or another coding tool. Codize acts as the learning and supervisory layer around those tools.

The V2 experience should feel conversational and character-driven, but it must **not** be a generic chatbot. The chat is the interface. Underneath it is a structured system that knows the project, tracks what the student is learning, constrains how Codize teaches, connects to the student’s code history, and decides when to help, when to ask, when to explain, and when to stay quiet.

The long-term goal is not maximum Codize usage. The goal is **appropriate independence**. As students become better at scoping tasks, prompting, testing, inspecting, debugging, and explaining, Codize should gradually reduce its support.

---

# 2. The Core Problem

## 2.1 The durable problem

Codize should not be built around the assumption that AI-generated code is always poor.

The more durable problem is:

> **AI lets a beginner increase the complexity of software much faster than they can increase their understanding of it.**

A beginner can now ask:

> “Make me a social study app with accounts, friend requests, AI study plans, a database, profiles, and notifications.”

A coding agent may produce a large amount of apparently functional software.

The result can look like this:

```text
What they can PRODUCE
████████████████████

What they can UNDERSTAND
████
```

That gap is dangerous because once the project breaks, changes architecture, or requires judgment, the student may no longer be able to supervise the work.

Codize tries to keep project capability and student understanding closer together:

```text
Project capability
██████████

Student understanding
████████
```

The two do not need to be identical. AI should let students accomplish things beyond their current ability. That is part of the opportunity.

The goal is to avoid:

> “My AI built 25 files and I do not even know which one handles login.”

---

## 2.2 The vibe-coding failure loop

A common beginner failure pattern is:

```text
I have an app idea
        ↓
AI makes coding feel accessible
        ↓
I ask for a huge result in normal English
        ↓
My request leaves out important details
        ↓
AI makes assumptions for me
        ↓
A lot of code appears
        ↓
I do not know what parts matter
        ↓
Something does not work
        ↓
"Fix it"
        ↓
AI changes more things
        ↓
"Still does not work. Fix it."
        ↓
My project becomes more complicated
while my understanding barely grows
```

Codize exists to interrupt this loop without destroying the excitement that made the student want to build in the first place.

---

## 2.3 What Codize is not arguing

Codize is **not** anti-AI.

Codize is **not** arguing that students should write every line manually.

Codize is **not** trying to recreate programming education from before coding agents existed.

Codize is **not** trying to slow students down for its own sake.

The thesis is:

> Students should receive the speed and leverage of coding AI while continuing to form the mental models, habits, and judgment needed to understand and own what they create.

---

# 3. Target User

## 3.1 Primary user

The center of V2 is:

> **A 13 to 18-year-old with little to moderate programming experience who has something they genuinely want to build and wants to use AI to help build it.**

Possible backgrounds include:

- only having used Scratch;
- knowing basic Python;
- taking or having taken APCSA;
- knowing basic HTML and CSS;
- having experimented with JavaScript;
- having never completed an entire app;
- already having tried ChatGPT, Claude, Cursor, Replit, or another coding AI;
- being technically curious but intimidated by traditional programming learning paths.

The student’s thought is not:

> “I want to improve my metacognitive software-engineering practices.”

It is:

> **“Wait, I can actually build my idea now?”**

Codize must protect that excitement.

---

## 3.2 Secondary users

Codize should also support:

### Student already building something

They have an existing project and want help making the next change without losing control.

### Student stuck in a patch loop

AI changed something, the project broke, and they are repeatedly asking the coding agent to fix it.

### More experienced student with weak AI workflow

They can code, but still make giant prompts, skip inspection, and trust generated changes too quickly.

These users should enter the same underlying system without being forced through beginner onboarding.

---

# 4. Product Positioning

## 4.1 What Codize is

> **Codize is an AI coding mentor for beginners who want to build real projects with tools like Codex, Claude, and Cursor without getting lost in AI-generated code. Codize connects what the student wants to build, what their coding agent actually changes, and what the student understands. Through a conversational character, it guides them one change at a time, teaches programming and AI-coding habits exactly when they become relevant, helps them recover when something breaks, and gradually removes support as they become more independent.**

---

## 4.2 The internal distinction

> **Chat is the interface.**

> **The evolving project + learner model + connected repository + constrained teaching engine are the product.**

If Codize becomes only a friendly Socratic chatbot, there is not enough reason for it to exist as a separate product.

---

## 4.3 Core promise

> **Build something real with AI. Learn how it works as you go.**

Alternative supporting lines:

> **Build with AI without getting lost in your own code.**

> **Your app gets better. You get better too.**

> **AI can build faster than you can learn. Codize helps you keep up.**

---

# 5. The Product Philosophy

## 5.1 One project

The student builds something they actually care about.

Codize should not force a student with a volleyball tracker idea to complete a coin-flipper curriculum before earning permission to build the volleyball tracker.

The student’s idea provides motivation.

---

## 5.2 One current change

The project can be large, but the student should reason about one understandable change at a time.

Example:

```text
PROJECT
Volleyball Tracker

CURRENT CHANGE
Add a form for recording a player's kills.
```

Codize should keep the current change as the primary unit of work.

---

## 5.3 One useful habit at a time

Codize should usually introduce only one unfamiliar learning behavior or concept when it becomes relevant.

Examples:

- first project idea: simplify version one;
- first AI prompt: define what “done” means;
- first existing feature: protect what already works;
- first multi-file surprise: inspect what changed;
- first finished feature: test reality yourself;
- first bug: investigate before reprompting;
- first new programming concept: understand one causal relationship;
- first high-risk change: think about ownership, failure, or edge cases.

This is a preference, not an absolute law.

For high-risk work, necessary safety checks may require more than one intervention.

A better rule is:

> **Introduce at most one unfamiliar learning concept at a time when possible, while still applying previously learned habits and necessary safety checks.**

---

# 6. Student Agency

Codize should guide without controlling the student’s project.

## 6.1 Codize should sequence ambition, not kill it

If a beginner wants:

> “An AI-powered social network where friends can upload notes, message each other, and get personalized tutoring.”

Codize should not respond:

> “Build a calculator first.”

Instead:

```text
YOUR IDEA

NOW
Create and organize your own notes locally.

NEXT
Add AI study help.

LATER
Accounts and sharing.

EVENTUALLY
Messaging and richer collaboration.
```

The ambitious idea remains visible.

Codize changes the order, not the destination.

---

## 6.2 Guided resistance

If the student insists on building everything at once, Codize should not simply refuse.

Codize should first help them see the tradeoff.

Student:

> Build all of it at once.

Codize:

> “You could ask your coding AI for the whole thing. Before we do that, look at what this request touches.”

```text
UI
Players
Stats
Storage
Accounts
Authentication
Database
Sharing
Charts
AI analysis
```

Codize:

> “If all of those change together and something breaks, which part would you check first?”

If the student does not know, Codize can use that as the teaching moment:

> “That is why I recommend getting one working piece first. You are still building the same app. We are just making the changes easier to understand.”

If they still insist, most ordinary projects should allow an override.

Codize can say:

> “Okay. I would not recommend this as the easiest way to stay in control. Let’s at least define what version one must accomplish so you have something concrete to check afterward.”

The student remains the owner of the project.

---

# 7. The Leadership Transition: Codize Leads, Then Fades

Codize should not guide forever.

The relationship should evolve:

```text
BEGINNER

Codize → student

        ↓

Codize ↔ student

        ↓

student → Codize

EXPERIENCED
```

At first, Codize may say:

> “I think the next understandable step is adding players.”

Later:

> “What do you think should come next?”

The student:

> “Save the players.”

Codize:

> “Makes sense. That introduces persistent storage. Let’s do it.”

Later still, the student simply says:

> “I’m adding filters next.”

Codize only intervenes if there is a reason.

This transition should happen per competency and concept, not as one global level.

A student may be independent with UI tasks but still need guidance with authentication or debugging.

---

# 8. Public Landing Page

The landing page should explain Codize before signup in a few seconds.

It should not look like a school dashboard.

## 8.1 Hero

### Headline

# **Build something real with AI. Learn how it works as you go.**

Supporting copy:

> Codize helps you turn your idea into manageable changes, work with coding agents like Codex, Claude, and Cursor, and actually understand what you’re building instead of blindly accepting AI-generated code.

Primary CTA:

**Start Building Free**

Secondary CTA:

**See How Codize Works**

---

## 8.2 Defining visual: project growth + understanding growth

The central landing-page visual should show the gap Codize is solving.

Concept:

```text
WITHOUT CODIZE

YOUR PROJECT
Idea → UI → Database → Auth → AI → Deployment
████████████████████████████████████

YOUR UNDERSTANDING
Idea → ???
██████

              "Wait... what does any of this do?"


WITH CODIZE

YOUR PROJECT
Idea → UI → Storage → Features → Auth → ...
████████████████████████████████

YOU
Idea → Events → State → Storage → Data → ...
██████████████████████████████

          Build more.
          Understand more.
```

The final design should not imply fake percentages or mastery scores.

A stronger visual may be two animated tracks.

### What you’re building

```text
💡 Idea
  ↓
🖥️ First screen
  ↓
💾 Save data
  ↓
⚙️ Features
  ↓
🌐 Bigger systems
```

### What you’re learning

```text
🎯 Give AI a clear goal
  ↓
🧠 Understand events
  ↓
🔍 Check what changed
  ↓
🧪 Test it yourself
  ↓
🛠️ Debug instead of blindly reprompting
```

The Codize character can visually move between the tracks, helping them stay aligned.

---

## 8.3 Character in the hero

Example:

```text
[Codize character]

"AI can build faster than you can learn.
 I'll help you keep up."
```

The line can type in with an original retro dialogue sound.

The sound must be optional.

---

## 8.4 Problem section

### Headline

## **AI makes coding easier. Losing control of your project is easier too.**

Visual:

```text
"Build my whole app"
        ↓
AI generates a ton of code
        ↓
Something breaks
        ↓
"Fix it"
        ↓
AI changes more code
        ↓
"Fix it again"
        ↓
😵 "I don't even know how my own app works."
```

Supporting statement:

> **Codize teaches you a better way without making you learn everything before you start building.**

Important positioning:

> AI coding is not the problem. Blindly handing over the thinking is.

---

## 8.5 The better path

### Headline

## **Your idea stays yours. Codize helps you build it one piece at a time.**

```text
        YOUR IDEA
            ↓
      PICK ONE CHANGE
            ↓
      LEARN ONE THING
            ↓
     BUILD WITH YOUR AI
            ↓
      CHECK WHAT HAPPENED
            ↓
        KEEP BUILDING
```

Supporting copy:

> Codize introduces planning, prompting, testing, debugging, GitHub, and programming concepts when they actually become useful in your project.

---

## 8.6 Interactive conversation demo

Example:

**Codize**

> What do you want to build?

**Student**

> A volleyball stat tracker for my team.

**Codize**

> Cool. Let’s start with one working piece. What should someone be able to do first?

**Student**

> Add players.

**Codize**

> Perfect. Let’s make that first AI prompt specific.

Then visually:

```text
Codize
  ↓
creates deliberate prompt
  ↓
Codex / Claude / Cursor
  ↓
project changes
  ↓
Codize helps you check + understand it
```

This section should make clear that Codize is not the coding agent.

---

## 8.7 Works with the AI you already use

### Headline

## **Keep your coding AI. Use it better.**

Copy:

> Codize does not replace your coding agent. It helps you learn how to direct and supervise it.

Potential tools shown:

```text
Codex
Claude
Cursor
ChatGPT
Replit
Other coding agents
```

Future supporting copy:

> Connect your GitHub project and Codize can help you understand what actually changed.

---

## 8.8 Why Codize instead of another chatbot?

### Headline

## **Not another chatbot telling you what to do.**

### Knows your project

> Codize remembers your project’s goals, working features, recent changes, current version boundaries, and what you’re building next.

### Learns how you learn

> It gives more support when something is new and gets out of the way when you’re ready to handle it yourself.

### Connects thinking to real code

> Your intentions, coding-agent prompts, GitHub changes, tests, and understanding stay connected instead of disappearing across separate AI chats.

---

## 8.9 Learn through your project

Show concepts appearing because the project creates a reason for them.

Example:

```text
Student wants saved assignments
        ↓
Codize introduces localStorage
        ↓
Student uses it
        ↓
Student predicts what happens after refresh
```

The lesson is embedded in the build.

---

## 8.10 Get unstuck

Show the recovery path:

```text
Something broke
      ↓
What worked before?
      ↓
What changed?
      ↓
What do we know for sure?
      ↓
What could we check first?
      ↓
Build a diagnostic prompt
```

---

## 8.11 Progress visual

Near the end, reinforce the core thesis:

```text
YOUR BUILD

✓ Player form
✓ Player list
→ Save players

YOUR LEARNING

✓ Events
✓ DOM updates
→ Browser storage
```

Then:

> **Your app gets better. You get better too.**

---

## 8.12 Final CTA

# **Build with AI without getting lost in your own code.**

**Start Building Free**

---

## 8.13 Landing-page hierarchy

1. Hero
2. Project-growth / understanding-growth visual
3. The problem
4. The better path
5. Interactive Codize conversation
6. Works with your coding AI
7. Why Codize instead of another chatbot
8. Learn through your own project
9. Get unstuck
10. Project + learning progression
11. Final CTA

---

# 9. Interface Model

## 9.1 Character-guided chat

Codize should feel like a conversation with a knowledgeable coding mentor.

The chat is the primary workspace.

The surrounding UI provides structure and context.

Example:

```text
┌───────────────────────────────────────────────┐
│ Volleyball Tracker                           │
│                                               │
│ Idea → First Version → ● Add Players → ...    │
├───────────────────────────────────────────────┤
│                                               │
│            [Codize character]                 │
│                                               │
│  "What do you want someone to be able        │
│   to do with your app first?"                │
│                                               │
│  ┌─────────────────────────────────────────┐  │
│  │ Type your answer...                     │  │
│  └─────────────────────────────────────────┘  │
│                                               │
│  [Need help?]                                │
└───────────────────────────────────────────────┘
```

---

## 9.2 What the chat is not

Not:

```text
generic AI chat
↓
student can ask anything
↓
AI improvises the entire learning experience
```

Instead:

```text
Codize learning system decides:
- where the student is;
- what decision matters now;
- what Codize knows;
- what the student should think about;
- what Codize may reveal;
- what support level is appropriate;
- whether the student should be asked, nudged, taught, or left alone.

                    ↓

The character communicates that conversationally.
```

The conversation is the interface, not the architecture.

---

# 10. Character and Personality

The Codize character should be an original identity.

Possible elements:

- expressive character art;
- small animations;
- different expressions;
- original retro text-blip speaking SFX;
- dialogue sound toggle;
- reduced-animation mode;
- a dedicated Character destination for switching companions and equipping unlocked accessories;
- visual growth or unlocks connected to meaningful progress.

Character customization is a secondary signed-in destination, placed above Settings in navigation. It is where the student switches characters and equips unlocked accessories.

Settings should contain presentation controls rather than character selection:

```text
Dialogue sounds: ON / OFF
Character animations: ON / REDUCED
Reduced motion: SYSTEM / ON / OFF
```

The sound should be inspired by retro dialogue systems generally, not copied from Undertale or another copyrighted game.

Example responses:

Student succeeds:

> “Yep. You got it.”

Student says “fix it” repeatedly:

> “Hold up. Before we change anything else, what actually stopped working?”

Student says:

> “I have no idea.”

Codize:

> “That’s useful. Let’s figure out one thing we know for sure.”

The character should make Codize feel personal and alive without turning it into a mascot that distracts from the work.

---

# 11. Codize Teaching Policy

“Be Socratic” is not enough.

Codize needs explicit teaching rules.

## Rule 1: Ask before telling when the student can reasonably reason

Bad:

> “You should exclude authentication from this prompt.”

Better:

> “Your login already works. Does adding a profile picture actually require changing login?”

Student:

> “Probably not.”

Codize:

> “Right. So what could you tell your coding AI to leave alone?”

---

## Rule 2: Never trap the student

Socratic teaching becomes frustrating when the student genuinely lacks the prerequisite knowledge.

Bad:

> “Think harder.”

Better support ladder:

```text
Need help?
↓
small clue
↓
another attempt
↓
more concrete clue
↓
another attempt
↓
direct explanation when necessary
```

Suggested levels:

### Nudge

> “Think about something that is already working.”

### Guided clue

> “Your player form already works. Does the stat-total feature need to change it?”

### Teach

> “Probably not. A useful boundary would be to tell the AI to leave the player form unchanged. This helps prevent unrelated rewrites.”

No penalty for needing help.

---

## Rule 3: Student thinking comes before AI suggestions when that thinking is the learning objective

If teaching testing:

> “What would you try to see if it works?”

comes before:

> “Here are some possible tests.”

If testing is not the learning objective and the student already demonstrates the habit, Codize should not unnecessarily force the question.

---

## Rule 4: Do not Socratically quiz obvious information

If the student already wrote:

> “Do not change login.”

Codize should not ask:

> “What should AI avoid changing?”

Recognize demonstrated thinking and move on.

---

## Rule 5: Uncertainty is information, not failure

Student:

> “I do not know why this file changed.”

Codize:

> “Okay. Let’s inspect it.”

Never:

> “Incorrect.”

---

## Rule 6: Teach with the student’s actual project

Not:

> “What is persistence?”

Instead:

> “Your assignments survive a refresh now. Where are they being kept?”

---

## Rule 7: Reduce friction before reducing thought

Codize should automate clerical work, not the cognitive work being taught.

Good automation:

- fetch the diff;
- summarize files touched;
- remember project state;
- populate known context.

Bad automation:

- decide whether a change was appropriate without the student;
- choose every test before the student thinks;
- write the student’s explanation;
- silently certify correctness.

---

## Rule 8: Explain only when there is a reason

An explanation is warranted when:

- a genuinely new concept appears;
- an important causal relationship matters;
- the student shows confusion;
- a consequential or risky change occurs;
- there is a useful transfer opportunity.

Typical explanation target:

> One interaction under roughly 60 seconds.

If they understand, move on.

If they need help, scaffold.

If they already know it, skip.

---

## Rule 9: Curiosity should always have a path

Optional “Why?” affordances should exist throughout the product.

Examples:

> Why are we making the first version smaller?

> Why should AI leave working code alone?

> Why are we testing it ourselves?

The default flow stays short, but curious students can go deeper.

---

# 12. Entry Paths

The first signed-in experience should not begin with a large intake form.

It should offer three understandable entry modes.

## 12.1 Start with an idea

> **I have an idea I want to build**

Primary beginner path.

---

## 12.2 Already building

> **I’m already building something**

Fast entry for existing projects.

---

## 12.3 Something broke

> **Something broke**

Recovery entry.

These all use the same underlying project and learner system.

---

# 13. Primary Path: Start With an Idea

## 13.1 Idea capture

Student:

> “I want to make a volleyball app where I can track stats for players on my team.”

Codize:

> “Cool. Let’s turn that into a first version you can actually understand while you build it.”

Then one useful product question:

> **What do you most want someone to be able to do first?**

Possible suggestions:

```text
Add players
Record stats
See player totals
I'm not sure
```

The beginner is asked about the product, not architecture.

---

## 13.2 Build a simple V1

If the student asks for:

- players;
- teams;
- accounts;
- stat tracking;
- leaderboards;
- charts;
- AI advice;
- sharing;

Codize should separate:

### Build now

```text
Add players
Record kills, assists, blocks, and errors
View totals
Save stats on this device
```

### Save for later

```text
Accounts
Team sharing
Online database
AI analysis
```

Short explanation:

> “We’re starting with a version that runs on your device so you can understand the core app before adding accounts and online data.”

Actions:

**Looks good**

**Change the first version**

The student can edit priorities.

---

# 14. Project Planning

Codize should propose structure, but the student owns priorities.

For beginners:

> “Here are the first 3 to 5 pieces I recommend and why.”

The student can:

- accept;
- reorder;
- remove;
- add;
- insist on another direction.

Later, Codize should stop proposing first and ask:

> “What do you think should come next?”

The goal is to help with technical sequencing beginners cannot yet know without taking away product decisions they can make.

---

# 15. Project Home

The signed-in Project Home should be radically simpler than V1.

Example:

```text
VOLLEYBALL TRACKER

You've built:
Players + stat entry + local saving

────────────────────────────

UP NEXT

Show each player's total kills.

[Continue building]

────────────────────────────

Something broken?
[Get unstuck]

────────────────────────────

Build plan >
Recent changes >
```

The page should not repeat the same concept with multiple labels.

Avoid:

- Active Project;
- Current Project;
- Recommended Starting Point;
- Start Here;
- Current Assignment;
- What To Do Next.

There should be one clear hierarchy.

The public landing page explains the thesis. Project Home simply answers:

> **What am I building next?**

---

# 16. Build Plan

A roadmap can exist, but it should remain secondary.

Example internal plan:

```text
1. Basic app structure
2. Add players
3. Record stats
4. Calculate totals
5. Save locally
6. Polish
```

The student sees mainly:

> **Up next: Add the player form**

A subtle link can expose:

> See build plan

The plan gives orientation without forcing the student to cognitively manage the entire project.

---

# 17. Current-Change Experience

The main build flow should reveal one thing at a time.

## Screen A

> **You’re about to add player totals.**

**Continue**

## Screen B

> **One thing to think about**
>
> Your existing stat-entry system works. What should AI leave alone?

Student answers.

**Continue**

## Screen C

> **Your AI prompt**

Prompt preview.

**Copy & Build**

## Screen D

When they return:

> **How did it go?**

Progressive disclosure is a core V2 principle.

Do not place assignment, lesson, multiple questions, checklist, prompt fields, and workflow controls on one page.

---

# 18. First AI-Assisted Change

The first change should teach one simple habit:

> **Make “done” specific.**

Student wants:

> “Make the player form.”

Codize asks:

> **Before we ask AI, what should you actually be able to do when this is finished?**

Student:

> “Type a player’s name and jersey number and click Add.”

Codize:

> “That’s much clearer than just saying ‘make a player form.’ You’re giving AI a result you can actually check afterward.”

Done.

This should feel like a brief coaching moment, not a lesson module.

---

# 19. Prompt Construction

Codize should transform the student’s decisions into a clean coding-agent prompt.

Example:

```text
I'm building a volleyball stat tracker.

Right now, add a simple player form.

The user should be able to:
- enter a player's name;
- enter a jersey number;
- click Add.

When this change is finished, I should be able to enter both values
and submit the form.

For now, do not build player statistics, accounts, or online storage.
```

Actions:

**Copy for coding AI**

**Edit**

**Why is this prompt structured this way?**

The student owns the final prompt.

Codize should help with phrasing because the learning target is deliberate decision-making, not writing elegant agent prompts from scratch.

Over time, prompt-construction support can fade.

---

# 20. Optional Prompt Explanation

Expand:

### Project context

Helps the agent understand what already exists.

### Current task

Keeps the prompt focused on one change.

### Done looks like

Provides something observable to check afterward.

### Leave alone

Protects working parts of the project.

This explanation is optional so experienced or impatient students are not forced into a lesson.

---

# 21. Coding Agent Choice

If the active project does not yet have a coding-agent preference, **this is the first question in the Build experience before Codize teaches the current change**:

> **What coding AI are you using?**

Potential choices:

- Codex;
- Claude Code;
- Cursor;
- ChatGPT;
- Replit;
- Other.

Codize should remember the choice and adapt later handoff, effort/model guidance, and tool-specific explanations.

Before a choice is made, the Build header must not pretend an agent is already selected. Once an agent is known, Codize should skip this question on later changes unless the student chooses to change tools.

---

# 22. Teaching Effort / Reasoning Level

Codize should teach a tool-independent concept before mapping it to agent-specific controls.

Question:

# **How much thinking does this task need?**

### Quick

Small, obvious, low-risk change.

### Standard

Normal feature work involving several connected pieces.

### Deep

Architecture, confusing debugging, authentication, major refactor, unfamiliar systems, or high-consequence changes.

Then Codize maps this underlying idea to the student’s chosen coding agent when useful.

The student learns:

> “How much reasoning does this task warrant?”

not:

> “Always choose XHIGH.”

---

## 22.1 Effort teaching starts with a student choice

On the first meaningful exposure, Codize should briefly define **Quick / Standard / Deep**, then ask the student to choose before revealing the answer:

> **What effort level do you think this prompt needs?**

The student selects one and submits.

### If the answer is reasonable

Codize confirms it and explains the reasoning in one short message. It then gives the current agent-specific model/reasoning recommendation **when Codize has a maintained, current mapping for that tool**.

### If the answer is not reasonable

Codize does not immediately reveal the answer. It explains what feature of the task makes the choice questionable and gives one Socratic hint. The student gets **one retry**.

If the retry is still not reasonable, Codize reveals the recommended category and explains why.

### Agent-specific recommendation

The transferable concept is always task effort. Tool/model names are only the mapping layer. Codize must not invent current model names or settings from model memory; those recommendations must come from maintained agent metadata.

### Fading

Later, the interaction can shrink to:

> “What effort level do you think this needs?”

Eventually Codize stops asking when the student consistently makes reasonable choices independently, unless a novel or high-risk task warrants reintroducing the intervention.

Pattern:

```text
explain categories briefly
↓
student chooses
↓
feedback / one Socratic retry if needed
↓
agent-specific mapping
↓
less support over time
```

---

# 23. External Coding Agent

Codize should not become the primary code-writing agent in V2.

The student takes the prompt to the tool they already use.

Example:

```text
Codize
↓
structured prompt
↓
Codex / Claude / Cursor / Replit
↓
agent changes the project
↓
Codize helps the student understand and supervise
```

This preserves the key separation:

> Coding agent writes.

> Codize observes, teaches, and helps the student reason.

---

# 24. Returning From the Coding Agent

The return flow must be much simpler than V1.

Avoid a visible sequence like:

```text
Bring Back What Changed
→ Change Map
→ Review
→ Verification
→ Evidence
```

Instead:

# **How did it go?**

Options:

**It worked**

**Something’s wrong**

**I’m not sure**

If the project is not yet connected, Codize may ask for minimal information.

Long term, project integration should reduce this manual work.

---

# 25. First Check

If the student says:

> It worked.

Codize should not simply declare success.

For a beginner:

> “Let’s actually try it once before moving on.”

Example:

> “Add a player named Alex with jersey #7. What happens?”

Later, after the student has practiced testing:

> “What would you try to see whether it works?”

Possible result choices:

```text
It worked
It partly worked
It didn't work
I'm not sure
```

The habit being learned is:

> **AI saying it finished is not the same as observing that the feature works.**

---

# 26. Tiny Understanding Moments

Not every change needs a quiz.

When a meaningful new concept appears, Codize can provide one short explanation.

Example:

## One thing worth knowing

> When you click **Add**, JavaScript runs a function connected to that button. That is called an event handler.

Then one project-grounded question:

> **In your app, what action causes the player-adding code to run?**

Student:

> Clicking Add.

Codize:

> “Yep. Keep building.”

No score is required.

No long lesson.

---

# 27. Progressive Habit Introduction

## 27.1 Protect what already works

Once the student has a working player form:

> “You already have something working now. Before AI adds the player list, what’s one thing you do not want it to mess up?”

Student:

> “The player form.”

The resulting prompt includes:

> Keep the existing player form working as it does now.

The student learns boundaries when boundaries become relevant.

---

## 27.2 Inspect what changed

When AI modifies more areas than expected:

> “You asked AI to work on the player list. It also changed your existing form code.”

Actions:

**Look at why**

**I expected that**

**I’m not sure**

If unsure, Codize helps inspect.

The lesson is:

> **AI output is a proposal, not truth.**

---

## 27.3 Test reality yourself

When a feature is supposedly done, Codize asks for a real check.

The level of support depends on prior evidence.

---

## 27.4 Investigate before reprompting

When a bug appears, Codize switches into recovery.

---

## 27.5 Understand one causal relationship

When a new technical concept becomes relevant, Codize teaches enough for the student to reason about that project.

---

# 28. Just-in-Time Programming Education

Codize should teach more actual programming than V1, but only when useful.

Concepts may include:

- functions;
- state;
- events;
- APIs;
- databases;
- authentication;
- client/server separation;
- persistence;
- async work;
- validation;
- error handling;
- data ownership;
- rendering;
- routing;
- dependencies;
- version control.

Example:

> **Your AI just created an API route.**
>
> “This code runs on the server rather than directly in the browser. Here’s why that matters in your project.”

Then a project-specific question.

Codize should not become “Codecademy with an AI project attached.”

---

# 29. Syntax Is Secondary

Codize should not focus on memorizing details that coding AI can reliably assist with.

Avoid heavy emphasis on questions like:

> What character ends a JavaScript statement?

Prioritize mental models:

- Where does this data come from?
- What causes this function to run?
- What is stored on my device versus online?
- What happens if this request fails?
- Which code decides who gets access?
- Why did changing X affect Y?
- What assumption is this feature making?
- What should remain true after this change?

The human’s job increasingly centers on causal understanding and judgment.

---

# 30. Storage Example

Suppose the student is ready to keep players after refresh.

Codize:

# New idea: browser storage

> “Right now your player list only lives while the page is open. `localStorage` lets the browser keep small amounts of information after the page refreshes.”

Visual:

```text
Add player
   ↓
JavaScript
   ↓
localStorage
   ↓
refresh
   ↓
load saved players
```

Question:

> **If saving works but loading does not, what do you think will happen after refreshing?**

This is programming education embedded in the student’s own project.

---

# 31. Recovery Mode

Recovery should always be easily accessible.

Persistent action:

> **Something broke**

Possible quick actions:

```text
[Continue building]
[Something broke]
[Ask about my project]
```

The same character remains present.

The system switches modes:

```text
NORMAL BUILD MODE
        ↕
RECOVERY MODE
```

---

## 31.1 Recovery conversation

Start:

> “Okay. Let’s figure out one thing before changing more code.”

Then one question at a time:

1. What were you trying to do?
2. What happened instead?
3. Was this working before?
4. What changed right before this?
5. What do we know for sure?
6. What could we check first?

Codize may summarize:

```text
✓ Adding players worked before
✓ The problem appeared after storage was added
? We do not yet know whether saving or loading is failing
```

Then ask:

> **What could we check first?**

The student can choose **Need help?**

---

## 31.2 Diagnostic prompt

After narrowing the problem, Codize can construct a diagnostic prompt:

```text
The player form worked before localStorage was added.

Now players disappear after refreshing.

Do not rewrite the feature yet.

Help me determine whether the problem is in saving or loading.
First inspect the relevant code and explain what you think is happening.
```

The recovery habit is:

```text
Observe
→ narrow
→ investigate
→ then change
```

not:

```text
broken
→ fix it
→ broken differently
→ fix it again
```

---

# 32. “Need Help?” System

Every challenging question should provide an accessible support path.

```text
Need help?
     ↓
Hint 1
     ↓
Try again

Still stuck?
     ↓
Hint 2
     ↓
Try again

Still stuck?
     ↓
Let's work through it
```

Support should never feel punitive.

Codize may remember how much help was needed to adapt future scaffolding, but it should not present this as failure.

---

# 33. Increasing Question Difficulty

Questions should become more sophisticated as the student demonstrates understanding.

Progression:

> **Concrete → causal → predictive → transfer**

Example with localStorage:

### Concrete

> What makes your players stay after refreshing?

### Causal

> Which part saves the players and which part loads them?

### Predictive

> What do you think would happen if saving worked but loading did not?

### Transfer

In a new project:

> This project needs preferences to survive refreshes. Where would you consider storing them, and why?

If the student struggles, Codize should reduce difficulty and increase support.

No shame.

No level loss.

---

# 34. Guidance Fading

Scaffolding should fade when the student demonstrates independent behavior.

Example: no-touch boundary.

### First time

> “What’s already working that you do not want AI to mess with?”
>
> *Hint: Think about something from an earlier change.*

### Later

> “What should stay untouched?”

### Later

```text
No-touch boundary
[________________]
```

### Eventually

Codize detects that the student already included a reasonable boundary.

Codize says nothing.

The same applies to:

- task scoping;
- testing;
- debugging;
- effort selection;
- prompt structure;
- inspection;
- concept explanation.

Codize’s success is partly measured by when it can stay quiet.

---

# 35. No Global Beginner / Intermediate / Advanced Label

A student may be strong in one area and weak in another.

Example:

```text
Task scoping:
usually independent

Prompt boundaries:
recently independent

Testing:
still benefits from prompts

Debugging:
new

localStorage:
practiced with guidance

Authentication:
not yet encountered
```

Support should adapt per behavior and concept.

Avoid a simplistic global level like:

> Level 7 Programmer

---

# 36. Structured Memory

Codize needs more than conversation memory.

## Layer 1: Project truth

Example:

```text
Project:
Volleyball Tracker

Current V1:
Local single-user stat tracker

Not yet:
Accounts
Cloud sync
AI analysis

Current stack:
HTML / CSS / JS

Known working:
Player creation
Player list

Current work:
Persist players
```

---

## Layer 2: Build history

```text
Change #1
Player form
✓ checked

Change #2
Player list
✓ checked

Change #3
Persistence
? refresh issue unresolved
```

---

## Layer 3: Learner model

```text
Task scoping:
usually independent

Prompt boundaries:
guided once
independent twice

Testing:
still benefits from prompts

Debugging:
new

localStorage:
used with guidance

event handlers:
explained independently
```

This makes future interactions context-aware.

Example:

> “You’ve been pretty good at defining what a change should accomplish, so I’ll skip that part. This is your first time touching authentication though, so I want to slow down there.”

That is a major differentiation from a generic chatbot.

---

# 37. Project Connection and GitHub

Long term, Codize should reduce manual context switching by connecting to the student’s repository.

The preferred initial architecture is a read-oriented GitHub integration.

Codize should be able to understand, where permissions allow:

- repository files;
- current commit;
- commit history;
- changed files;
- diffs;
- branches later if needed.

The initial design should avoid silent code-writing permissions.

Separation:

> **Coding agent writes.**

> **Codize observes, teaches, and helps the student reason.**

---

## 37.1 Why project connection matters

Without integration:

```text
Codize
→ copy prompt
→ coding agent
→ student manually explains what changed
→ Codize
```

That is high friction.

With project connection:

```text
Codize
→ copy prompt
→ coding agent
→ project changes
→ repository history makes changes visible
→ Codize compares intention with result
```

Automation should remove clerical work.

It should not remove the student’s judgment.

---

# 38. GitHub Learning

GitHub should itself be taught just in time.

At an appropriate moment:

> **Do you use GitHub yet?**

Choices:

**Yes, I’m comfortable with it**

**A little**

**No / What’s GitHub?**

If they say no, use beginner language:

> “GitHub gives your project a history. Think of it like checkpoints in a game. If something goes wrong later, you can see what changed or return to an earlier version.”

Teach concepts when relevant:

```text
commit = saved checkpoint
repository = project + history
```

Later, only when needed:

```text
branch
pull request
merge
```

Do not dump version-control theory on the first screen.

---

# 39. When to Offer GitHub Connection

Do not require it before the student understands its purpose.

Possible first session:

```text
Idea
↓
first version
↓
first prompt
↓
build something
```

Then:

> **Want Codize to keep track of what changes automatically?**

> “Connecting your project lets me compare what you asked for with what actually changed.”

Actions:

**Connect GitHub**

**Not yet**

Now the feature has a reason.

---

# 40. Automatic Inspection Policy

Codize should automatically gather evidence but not automatically make the student’s judgment.

Example:

GitHub tells Codize:

> `storage.js` changed.

Codize should not silently conclude:

> “This change was inappropriate.”

Instead:

> “You asked for filtering. `storage.js` also changed. Were you expecting that?”

Later, when the student is more experienced:

> “Anything surprising in this diff?”

The student inspects first.

Only afterward might Codize surface what they missed.

Rule:

> **Automation removes clerical work, not cognitive work.**

---

# 41. The External-Tool Round Trip

This is one of the biggest product risks.

A manual loop like:

```text
Codize
→ copy prompt
→ agent
→ manually paste five things back
→ Codize
```

is probably too burdensome.

A more viable loop is:

```text
Codize
→ copy prompt
→ agent
→ project changes become automatically visible
→ return to Codize
```

GitHub is the first integration hypothesis.

Later, if necessary, an IDE or browser companion may reduce friction further.

Do not build every integration before proving the core experience.

---

# 42. Gamification Philosophy

Codize should not reject gamification.

It should distinguish between **gamifying learning progress** and **gamifying compliance with Codize**.

Core principle:

> **Gamify discovery, independence, project progress, and genuine accomplishment. Do not gamify compliance with Codize.**

---

## 42.1 Bad gamification

Avoid:

- +10 XP for filling out Prompt Builder;
- +5 XP for uploading evidence;
- +20 XP for completing a Defense;
- daily login streaks;
- losing progress because the student did not code for four days;
- fake mastery percentages;
- rewards for completing every required field;
- incentives that make students optimize for Codize usage.

This trains:

> use Codize a lot

instead of:

> become a better AI-assisted programmer.

---

## 42.2 Better gamification

### Character development

Character expressions, accessories, backgrounds, or small visual evolutions can unlock around meaningful milestones.

The playful reward sits on top of real learning evidence.

---

### Concept collection

Secondary screen:

# Things You’ve Learned

Example:

```text
EVENT HANDLERS

You've used this in:
✓ Add Player
✓ Record Stats

Current experience:
Used independently
```

```text
LOCAL STORAGE

You've used this in:
✓ Save Players

Current experience:
Practiced with guidance
```

Possible visual forms should remain simple and readable. The current approved direction does **not** use a decorative learning constellation. Concepts can use cards, grouped lists, compact progress markers, and character/cosmetic unlock connections without inventing a fake mastery map.

---

### Meaningful achievements

🏆 **Caught It Yourself**

> Noticed an unrelated AI change before Codize pointed it out.

🔍 **Before the Patch**

> Investigated a bug before asking AI to modify code.

🧪 **Your Test, Your Idea**

> Proposed and ran your own useful check.

🧩 **Connected the Dots**

> Explained a new relationship in your project without hints.

🛠️ **Recovered**

> Found the cause of a bug without entering another blind repair loop.

These reward independence.

---

# 43. Learning Screen

The learning history should be secondary, not Home.

Signed-in navigation:

```text
Project
Build
Learning
History

Character
Settings
```

`Character` and `Settings` are secondary destinations. `Something broke` is contextual on Project Home / Build rather than a sidebar destination.

Learning can include:

### Concepts encountered

### Habits practiced

### Things becoming independent

### Concepts likely coming up in the current project

Avoid:

> JavaScript mastery: 83%

Use evidence-oriented language instead.

Possible states:

### NEW

You have encountered it.

### GUIDED

You have used it with help.

### PRACTICED

You have used it more than once.

### RECENTLY INDEPENDENT

You recently demonstrated it without help.

“Recently independent” should not mean permanent mastery.

---

# 44. Project Timeline

A motivating timeline can connect project progress and learning.

```text
YOUR BUILD

✓ Player form
  You learned how button events trigger code.

✓ Player list
  You practiced protecting working features.

✓ Save players
  You learned where browser data is stored.

→ Record statistics
```

The message:

> **I can see both what I built and what I now understand.**

This is more meaningful than arbitrary XP.

---

# 45. Why Not Just Use ChatGPT?

This challenge should guide every product decision.

A generic AI can already:

- explain programming;
- ask Socratic questions;
- help write prompts;
- quiz a student;
- remember some conversation context;
- debug code.

Therefore:

> **“Codize is a Socratic AI tutor with memory” is not enough.**

A student could ask a general AI:

> “I’m building a volleyball app. Don’t let me vibe code. Teach me Socratically. Remember my skill level. Ask me to make bounded changes. Keep track of my repo. Never give tests before I think of one. Fade help as I improve.”

The problem is that the beginner has to design and maintain their own learning system.

They must know what good supervision looks like before they can request it.

Codize should make the good workflow the path of least resistance.

---

# 46. Codize Differentiation

## A. Live project understanding

Codize can know:

- what files exist;
- what changed;
- what commits happened;
- what was working previously;
- what the current V1 excludes.

Generic AI:

> “Here is what you told me.”

Codize:

> “You asked your agent to add player totals. The latest project change also modified `storage.js`, which was outside that request.”

---

## B. Structured project memory

Codize tracks:

```text
intended change
expected result
no-touch boundary
actual diff
student judgment
test
actual result
concepts encountered
support required
known uncertainties
```

across sessions.

---

## C. Learner model

Codize can know:

> “They independently scoped the last four changes. Stop asking.”

and:

> “This is their first database feature. Introduce client/server separation.”

The system decides when not to teach.

---

## D. Constrained teaching engine

Codize can enforce:

```text
Student should predict first.
Do not reveal candidate tests yet.

Student has enough knowledge.
Ask one question.

Student tried twice and still lacks prerequisite knowledge.
Teach directly.

Student already demonstrated this behavior.
Skip the intervention.
```

This is product logic, not just conversational tone.

---

## E. Bridge between coding agent and learner

```text
Student decides
      ↓
Codize constructs deliberate prompt
      ↓
Coding agent executes
      ↓
Project history records result
      ↓
Codize compares prompt ↔ actual changes
      ↓
Student learns from discrepancy
```

Codize becomes the learning layer around the coding agent.

---

## F. Agent-specific guidance

Codize knows whether the student uses Codex, Claude Code, Cursor, Replit, or another tool.

It teaches transferable concepts, then maps them to the specific interface.

Example:

> task complexity

becomes:

> which effort/reasoning setting is appropriate in this agent?

---

## G. The project becomes the curriculum

Generic AI can explain:

> localStorage

Codize knows:

> “You just introduced localStorage into your volleyball tracker, and this is your first persistent-storage feature.”

So it teaches the concept exactly when it matters.

Later, it can check transfer in another feature or project.

---

# 47. Differentiation Test for Every Feature

Use this harsh rule:

> **If a proposed Codize feature could be replaced by opening ChatGPT and asking one question, it is not enough to justify the feature.**

Weak feature:

> Ask AI to explain arrays.

Stronger feature:

> Codize notices the coding agent changed the player representation from an object to an array, knows arrays are new for the student, shows where the change happened in the real project, teaches only the needed concept, and later asks the student to predict how a similar collection will behave.

---

# 48. System Architecture

Conceptual architecture:

```text
                    CODIZE

        ┌─────────────────────────────┐
        │      CHARACTER + CHAT       │
        │                             │
        │ conversational interface    │
        └──────────────┬──────────────┘
                       │
              orchestrated by
                       │
        ┌──────────────▼──────────────┐
        │      LEARNING ENGINE        │
        │                             │
        │ What should be taught?      │
        │ How much help?              │
        │ Ask or tell?                │
        │ Should Codize stay quiet?   │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │       PROJECT MEMORY        │
        │                             │
        │ V1                          │
        │ history                     │
        │ known-working state         │
        │ current change              │
        │ uncertainty                 │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │       LEARNER MODEL         │
        │                             │
        │ concepts                    │
        │ habits                      │
        │ assistance needed           │
        │ recent independence         │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │      PROJECT CONNECTION     │
        │                             │
        │ GitHub                      │
        │ commits                     │
        │ files                       │
        │ diffs                       │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │    EXTERNAL CODING AGENT    │
        │                             │
        │ Codex / Claude / Cursor ... │
        └─────────────────────────────┘
```

---

# 49. Conceptual State Model

A future implementation should likely maintain separate state for:

## Project state

- project identity;
- current version boundaries;
- future features;
- tech stack;
- current change;
- known working behaviors;
- known uncertainties;
- connected repository;
- current commit;
- recent changes.

## Learning state

- concepts encountered;
- concepts practiced;
- support used;
- recent independent demonstrations;
- habits demonstrated;
- habits needing support;
- transfer opportunities.

## Conversation state

- current mode;
- current question;
- available help level;
- what Codize has already revealed;
- whether the student has attempted independently;
- whether the flow can advance.

## Agent state

- chosen coding agent;
- current agent-specific instructions;
- mapping between task complexity and tool settings;
- known user familiarity with that agent.

This separation should prevent “chat history” from becoming the source of truth.

---

# 50. Safety and Truthfulness Rules

Codize should never claim more than it knows.

It should distinguish:

- what the student said;
- what the coding agent claimed;
- what the repository shows;
- what the student observed;
- what Codize inferred;
- what remains uncertain.

Codize should not say:

> “Your app is secure.”

> “This proves the feature is correct.”

> “You mastered authentication.”

Prefer:

> “This test supports the behavior you checked.”

> “The repository shows these files changed.”

> “You recently explained this without help.”

> “We have not checked cross-user access yet.”

---

# 51. High-Risk Changes

Some project changes deserve more friction.

Examples:

- authentication;
- authorization;
- per-user data ownership;
- database migrations;
- secrets;
- payment flows;
- destructive data operations;
- deployment configuration;
- large refactors;
- unfamiliar architecture;
- changes that touch many connected systems.

Codize should slow down more when the consequence of misunderstanding is larger.

However, it should still avoid overwhelming the student with every possible concern.

The extra friction should be relevant and explained.

---

# 52. Complexity and Ambition Policy

Rule:

> **Do not kill ambition. Sequence it.**

Codize can show:

```text
NOW
Local homework tracker

NEXT
Saved data

LATER
Accounts + cloud sync

EVENTUALLY
Shared classrooms
```

If the student insists on an advanced feature, Codize can use guided resistance, explain what becomes harder to inspect, and then usually allow them to proceed with greater scaffolding.

Codize should not create an arbitrary “you are not ready” gate unless there is a genuine safety or technical reason.

---

# 53. What Codize AI May Do

Codize AI may:

- understand the student’s idea;
- help simplify the first version;
- propose a build sequence;
- explain why a sequence is recommended;
- turn student decisions into a clean coding prompt;
- parse pasted coding-agent output;
- inspect repository diffs;
- notice possible out-of-scope changes;
- identify new concepts;
- generate project-specific explanations;
- generate project-specific questions;
- suggest debugging checks after the student has had a chance to think;
- maintain and summarize project context;
- adapt support level;
- translate task complexity into tool-specific guidance.

---

# 54. What Codize AI Should Avoid

Codize AI should avoid:

- automatically deciding every project priority;
- writing the entire student answer when the answer is the learning objective;
- giving the test before the student thinks when testing is the target skill;
- certifying correctness without evidence;
- claiming security;
- automatically patching the code during the learning flow;
- inventing project state;
- silently turning inference into fact;
- locking the student into Codize;
- manufacturing fake mastery metrics;
- forcing lessons the student has already demonstrated;
- adding educational friction to trivial changes.

Rule:

> **Codize AI can organize information around a decision. The student should still own consequential decisions.**

---

# 55. Full Beginner User Flow Example

## Step 1: Landing

Headline:

> **Build something real with AI. Learn how it works as you go.**

Student clicks:

> **Start Building Free**

---

## Step 2: Entry choice

Student chooses:

> **I have an idea I want to build**

---

## Step 3: Idea

Codize:

> “What do you want to build?”

Student:

> “A homework tracker.”

---

## Step 4: First version

Codize:

> “Let’s make the first version simple enough to understand while you build it.”

Suggested first version:

- add assignments;
- mark them done;
- filter them;
- keep them after refresh.

Saved for later:

- accounts;
- cloud sync;
- shared classrooms.

Student edits or accepts.

---

## Step 5: Build plan

Codize proposes:

```text
1. Basic assignment form
2. Show assignments in a list
3. Mark assignments done
4. Filter assignments
5. Save assignments locally
```

Student can view the plan, but the interface emphasizes only the current step.

---

## Step 6: Current change

> **First: create the basic assignment form.**

**Start**

---

## Step 7: One useful habit

Codize:

> “A good AI prompt says what ‘done’ looks like.”

Question:

> “When this part is finished, what should you be able to do?”

Student:

> “Type an assignment and due date and press Add.”

---

## Step 8: Prompt

Codize constructs a prompt.

Student can edit it.

Optional:

> **Why is this prompt structured this way?**

---

## Step 9: Agent + effort

Codize knows the student uses Codex.

First time, Codize may recommend:

> Standard

and briefly explain why.

Later, the student chooses.

---

## Step 10: Build externally

Student copies prompt to the coding agent.

Coding agent edits the project.

---

## Step 11: Return

Codize:

> **How did it go?**

Student:

> It worked.

---

## Step 12: Check

Codize:

> “Let’s actually try it once.”

> “Add ‘Math worksheet’ due Friday. What happened?”

Student:

> “It appeared.”

---

## Step 13: Tiny concept moment

Codize:

> “One thing worth knowing: when you press Add, JavaScript runs code connected to that click. That’s an event handler.”

Question:

> “What action causes your assignment code to run?”

Student:

> “Clicking Add.”

Codize:

> “Yep.”

---

## Step 14: Home

```text
✓ Basic assignment form

UP NEXT
Keep assignments in a list

[Continue building]

Something broke?
[Get unstuck]
```

The first session produced:

- real progress;
- one AI-use habit;
- one programming concept;
- a clear next step;
- no giant curriculum module.

---

# 56. Example Later-Project Flow

Student has:

- player form;
- player list;
- local saving.

Next change:

> Add stat totals.

Codize may skip “define done” because the student has shown that skill repeatedly.

Instead, because existing functionality matters:

> “Your stat-entry system already works. What should AI leave alone?”

Student answers.

Codize generates the prompt.

After the agent works, the repository shows `storage.js` changed unexpectedly.

Codize asks:

> “You asked for totals. `storage.js` changed too. Were you expecting that?”

The student inspects.

This is how learner state changes the experience.

---

# 57. Example Recovery Flow

Student:

> “Something broke.”

Codize:

> “What were you trying to do when it stopped working?”

Student:

> “Add localStorage.”

Codize:

> “What happened instead?”

Student:

> “Players disappear after refresh.”

Codize:

> “Was adding players working before storage?”

Student:

> “Yes.”

Codize:

> “So we know the form worked before, and the problem appeared after storage. We do not know yet whether saving or loading is failing. What could we check first?”

Student:

> “Maybe whether it saved anything?”

Codize:

> “Good. Let’s check that before changing code.”

Then Codize can help construct a diagnostic agent prompt.

---

# 58. Learning Progression

The internal system may use a progression like:

| Project situation | Habit or concept introduced |
|---|---|
| First project idea | Simplify version one |
| First AI prompt | Define a specific result |
| Existing working feature | Protect what works |
| Multiple changed areas | Inspect what AI changed |
| Feature supposedly done | Test reality yourself |
| First bug | Investigate before reprompting |
| New concept introduced | Understand one causal relationship |
| More consequential feature | Think about edge cases |
| Accounts / data / security | Think about ownership and failure |
| Student improves | Reduce scaffolding |

The student should not see this as a rigid curriculum.

The project creates the reason for the lesson.

---

# 59. Anti-Overwhelm Design Principles

1. Show one primary action at a time.
2. Keep secondary information collapsible.
3. Do not repeat the same status in multiple cards.
4. Do not show a full roadmap unless the student asks.
5. Avoid jargon unless teaching the term is useful.
6. Keep explanations short by default.
7. Offer “Why?” instead of forcing explanation.
8. Offer “Need help?” instead of forcing failure.
9. Hide internal ontology.
10. Do not make the student operate provenance, verification, evidence, or learning-state terminology directly unless the concept itself is useful.
11. Let the character carry continuity.
12. Keep the current change visually dominant.
13. Keep recovery accessible but not intrusive.
14. Preserve ambition while sequencing complexity.

---

# 60. V1 Concepts That Survive Under V2

The V1 work should not be discarded automatically.

Useful concepts that may survive internally:

- project memory;
- current assignment;
- Prompt Builder;
- bounded prompts;
- bring-back concept;
- change comparison;
- verification;
- evidence distinction;
- provenance;
- recovery;
- stale state;
- project history;
- task ownership;
- assignment-scoped drafts;
- lifecycle awareness.

But these should not necessarily remain separate student-facing screens.

V2 should reuse the strongest internal ideas while simplifying the visible experience.

---

# 61. Concepts Likely Hidden or Removed From Student-Facing V2

Potentially hide, merge, or remove:

- seven visible phases;
- formal archetype classification;
- phase navigation;
- separate Change Map screen;
- separate Review screen;
- separate Evidence screen;
- routine Project Defense;
- Defense Reports;
- visible lifecycle staleness;
- large workflow diagrams;
- detailed project intake;
- repeated status cards;
- giant competency dashboards;
- mandatory full workflow for trivial changes.

These can remain internal only if they still serve a real purpose.

---

# 62. Features Not to Build Yet

Freeze until the core V2 experience is proven:

- teacher dashboard;
- district administration;
- parent portal;
- payment system;
- daily streaks;
- leaderboards;
- social feed;
- formal mastery score;
- mobile app;
- huge project-template library;
- broad standards alignment;
- automatic security certification;
- dozens of AI platform integrations;
- complex marketplace features;
- advanced institutional analytics;
- elaborate assessment reports;
- mandatory micro-course library;
- broad social gamification.

Prioritize the bones before the shiny features.

---

# 63. Possible V2 MVP

A thin V2 should probably include only:

1. Public landing page with the growth/understanding thesis.
2. Character-guided chat interface.
3. Three entry paths.
4. Simple project idea capture.
5. Simple V1 scoping.
6. Lightweight build plan.
7. One current change.
8. One just-in-time learning intervention.
9. Structured prompt generation.
10. Agent selection as the first Build question when the agent is unknown.
11. Student-first task-effort guidance with agent-specific mapping.
12. Simple return state: worked / broken / unsure.
13. One check flow.
14. One tiny concept explanation where relevant.
15. “Something broke” recovery flow.
16. Basic project memory.
17. Basic learner state.
18. Optional “Why?”
19. Optional “Need help?”
20. Simple Learning screen.
21. Basic Character destination with Codybara, switching/customization shell, and unlock-ready data model.
22. Basic meaningful achievements/accessory unlocks only if they do not distract.
23. GitHub connection as an early but not necessarily day-one V2 capability.

The MVP should be judged by whether the experience feels useful and understandable, not by feature count.

---

# 64. Product Validation Philosophy

The project should not return to broad building just because the thesis sounds coherent.

The next implementation should be thin enough to put in front of a few real beginners.

Early testing can be qualitative.

Ask a student:

> “You have an app idea. Try using this to build it.”

Then observe:

- where they hesitate;
- what they skip;
- what excites them;
- whether Codize interrupts at sensible moments;
- whether “Need help?” works;
- whether the character feels useful or annoying;
- whether the prompt feels better than what they would have written;
- whether they understand why Codize asked something;
- whether they return after using their coding agent;
- whether GitHub connection reduces friction;
- what they do when something breaks;
- whether the student starts applying habits without prompts.

Do not overbuild analytics before the flow survives basic use.

---

# 65. Success Metrics

Codize should not optimize only for retention.

A student needing Codize less can be success if they have internalized the habits.

Useful categories:

## Adoption

Will a beginner start?

## Engagement

Will they complete a meaningful build loop?

## Return

Will they return when another meaningful change or bug occurs?

## Behavior change

Do they scope tasks, set boundaries, inspect changes, test, and debug differently?

## Transfer

Do they use those habits when Codize does not explicitly prompt them?

## Appropriate independence

Does support fade because the student increasingly supplies the reasoning themselves?

## Friction

How much time and annoyance does Codize add relative to the value?

---

# 66. Failure Modes

Codize is in danger if:

- students experience it as homework;
- every change requires ceremony;
- students rush through answers;
- students repeatedly choose “just tell me”;
- students use Codize only because an instructor requires it;
- students become better at answering Codize but not better without it;
- the character becomes distracting;
- gamification rewards usage rather than independence;
- students manually re-enter information that Git already knows;
- Codize asks questions they already answered;
- Codize becomes another source of dependence;
- external coding tools offer a sufficiently good native learning mode;
- project connection becomes too difficult for beginners;
- Codize’s adaptive logic feels arbitrary;
- the user cannot tell why Codize interrupted them;
- Codize blocks ambition rather than sequencing it.

---

# 67. Open Tradeoffs

## Here is a tradeoff you might want to question or change: how much project planning should Codize do?

Current decision:

> **Codize proposes structure; student owns priorities.**

Risk of too much Codize planning:

- student outsources project thinking;
- plan feels imposed;
- product becomes curriculum.

Risk of too little:

- beginner repeatedly chooses changes far beyond current understanding;
- project complexity outruns learning.

---

## Here is a tradeoff you might want to question or change: how much should Codize inspect automatically?

Current decision:

> **Automatically gather evidence, but do not automatically make the student’s judgment.**

Too much automation:

- student never learns inspection.

Too little:

- external-tool round trip becomes annoying.

---

## Here is a tradeoff you might want to question or change: how much explanation is enough?

Current decision:

> **Explain only when a new concept, confusion, consequence, or transfer opportunity makes it useful. Keep it brief by default.**

Too much:

- feels like school.

Too little:

- student’s project outpaces understanding.

---

## Here is a tradeoff you might want to question or change: is the external-tool round trip acceptable?

Current decision:

> **Only if Codize automates most of the context handoff.**

GitHub is the first integration hypothesis.

If the round trip still feels bad, future IDE or browser integration may become necessary.

---

## Here is a tradeoff you might want to question or change: how aggressively should Codize steer away from advanced features?

Current decision:

> **Do not kill ambition. Sequence it. Use guided resistance, then preserve student agency.**

---

## Here is a tradeoff you might want to question or change: should students see learning history?

Current decision:

> **Yes, but on a secondary Learning screen, not on Home.**

---

# 68. Product Principles Checklist

A proposed V2 feature should pass most of these questions:

1. Does it help a beginner build something they actually care about?
2. Does it reduce the gap between project capability and student understanding?
3. Is it relevant to the current change?
4. Is the student doing the important thinking?
5. Is Codize automating clerical work rather than cognitive work?
6. Can the feature become less intrusive as the student improves?
7. Does it avoid fake certainty?
8. Does it preserve student agency?
9. Does it avoid unnecessary jargon?
10. Does it keep the current experience simple?
11. Could this feature be replaced by one generic ChatGPT question?
12. Does it use project state, learner state, repository state, or constrained teaching in a way a generic chat would not?
13. Is it rewarding independence rather than compliance?
14. Is there a clear reason to show this now?
15. Could Codize stay quiet instead?
16. Does it make the student more capable outside Codize over time?

If the answer to #11 is “yes” and there is no stronger reason in #12, the feature probably does not justify its existence.

---

# 69. Long-Term Vision

If the thesis is correct, Codize can eventually become a persistent learning layer around AI-assisted software development.

A mature version could know:

- what the student intends;
- what they delegate;
- what the coding agent changes;
- what surprises them;
- what they inspect;
- what they test;
- what they misunderstand;
- which concepts they can explain;
- how much help they need;
- where they have become independent;
- when support should return.

The deeper product question is:

> **How should an intelligent system expand a human’s capability without replacing the reasoning the human needs to stay in control?**

Coding is the concrete environment where Codize explores that question.

---

# 70. The North-Star Experience

At the beginning:

```text
Codize tells me how to make a bounded prompt.
```

Later:

```text
I automatically make bounded prompts.
```

At the beginning:

```text
Codize reminds me to test.
```

Later:

```text
I test before it asks.
```

At the beginning:

```text
Codize helps me diagnose bugs.
```

Later:

```text
I naturally inspect the error before asking AI to patch.
```

At the beginning:

```text
Codize teaches me how my app works.
```

Later:

```text
I can reason through much of it myself.
```

The character should literally become less intrusive as this happens.

The character is not becoming more powerful.

**The student is.**

---

# 71. Whiteboard Model

```text
                    MY IDEA
                       ↓
               SIMPLE FIRST VERSION
                       ↓
                 CURRENT CHANGE
                       ↓
             WHAT DO I NEED HERE?
                       ↓
          ┌─────────────────────────┐
          │ one relevant new habit  │
          │ or concept, if needed   │
          └────────────┬────────────┘
                       ↓
                BUILD WITH AI
                       ↓
                  WHAT HAPPENED?
                  ↙             ↘
              WORKED           BROKE
                ↓                ↓
             CHECK            RECOVER
                ↓                ↓
            UNDERSTAND ←─────────┘
                ↓
             NEXT CHANGE
                ↓
         less help over time
```

---

# 72. Final Definition

> **Codize is a project-based, beginner-first AI coding mentor for high school students. Students bring the projects they actually want to build and continue using coding agents like Codex, Claude, Cursor, ChatGPT, or Replit. Codize helps keep project complexity from outrunning student understanding by guiding one current change at a time, introducing programming concepts and AI-coding habits exactly when they become relevant, connecting the student’s intention to the code that actually changed, helping them test and recover without blind reprompting, and gradually reducing support as they become more independent. The conversational character is the interface, while the real product is the structured learning engine, project memory, learner model, repository connection, and constrained teaching system underneath it.**

The defining principle remains:

# **One project. One current change. One useful habit at a time.**

And the public promise remains:

# **Build something real with AI. Learn how it works as you go.**
