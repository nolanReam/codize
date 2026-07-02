## Codize — Master Product Specification 

- Version 1.2 | Pre Roadmap Reference Document 

## - Built from: full product debate, behavioral research review, three panel teardown, Gemini - cross validation 

- — v1.1: Three post consensus corrections reconnection modal mechanic, gate rubric Condition 3 + MVP caveat, pre-build artifact requirement 

## — - v1.2: Security architecture added three non negotiable constraints across all archetypes, - OWASP A01/A02/A03 encoded in templates, mandatory pre deployment checklist phase 

How to use this document: This is the definitive blueprint. Before making any feature decision, building any component, or writing any system prompt, check it against this spec. If ' ' — a decision isn t addressed here, that s a gap not permission to improvise. 

## — Section 1 Core Mission & Positioning 

## The Problem Being Solved 

The rise ofAI coding tools has produced a generation of CS students who can ship but cannot explain. They use Cursor, Copilot, or Claude to generate code, accept what comes out, and move on. The result is a portfolio full of projects they cannot defend in an interview, a skill set that collapses under technical questioning, and a dependency on AI that grows rather than shrinks over time because they never built the understanding to direct it deliberately. 

This is not a laziness problem. It is a workflow problem. No one ever showed them where AI belongs in a professional development process and where it doesn't. Codize fixes that. 

## The precise distinction Codize enforces: 

|Vibe Coding|Codize-Structured Building|
|---|---|
|Describe endresult,accept output|Plan architecturefrst, then generate|
|AI decides thestructure|Human decides structure,AIfllsit|
|No understandingofwhat wasgenerated|Explain everydecision beforeprogressing|
|AI as replacement|AI asaccelerantfor understoodwork|
|Portfolio youcan'tdefend|Portfolio youbuiltand canwalkthrough|



## Target Audience — Be Specific 

– Primary user (MVP): CS students, 1 3 years of experience, who have used AI coding tools and feel a low-grade anxiety that they don't actually understand what they're shipping. They are not beginners. They know what a loop, function, and API call are. They cannot confidently explain the architecture of their own projects. 

They open Codize when: They are starting a new personal project and want to do it right this time. They have an internship or interview coming up. They feel behind peers who seem to — actually understand things. Not when they have an assignment due in two hours that person will not use Codize. 

They are not: Complete beginners (too much curriculum design required, out of scope for MVP). Senior engineers (they don't have this problem). Students who genuinely don't care about understanding (no product fixes motivation from zero). 

## Baking Yeager's Self-Transcendent Framing Into the Intake Screen 

The Yeager (2014) study found that students given a self-transcendent purpose framing — "learn " — this to solve real problems and help others showed significantly higher persistence and deeper processing than students given self-oriented framing — "learn this to get a job." This is not a tagline. It is a structural decision about the first question Codize asks. 

## The intake screen does NOT ask: 

"What do you want to build?" 

## The intake screen DOES ask: 

"What problem do you want to solve, and who does solving it help?" 

- This is a two part question, not two questions. It cannot be skipped. It forces the student to articulate purpose before scope. Codize uses the answer to this question in two ways: it personalizes every phase explanation to reference the real-world impact of what they're 

building, and it surfaces this purpose back to the student when they are stuck or disengaged mid-project ("Remember — you're building this because [their answer]. Let's work through this together."). 

## The full intake sequence (conversational, not a form): 

- " " — 

- 1. What problem do you want to solve, and who does solving it help? purpose framing, mandatory, sets Yeager motivation 

2. "Describe what the app does in plain language, like you're explaining it to a friend." — scope definition 

- " " — 

- 3. What languages or frameworks are you most comfortable with? stack calibration 

4. "On a scale of honest to honest: how well do you understand the code AI generates for you right now?" (options: "I can usually explain it" / "Sometimes, depends" / "Honestly, not really") — self-assessment, used to calibrate gate difficulty 

- " ' " — 

- 5. What s your rough deadline for having something working? timeline for pacing 

- After these five questions Codize has: purpose, scope, stack preference, self assessed understanding level, and timeline. That is sufficient to generate a roadmap. No form, no dashboard, no homepage — go straight from signup to question 1. 

## — Section 2 MVP Architecture 

## The Three Archetype System 

The MVP supports exactly three project archetypes. No more. The reason is curriculum reliability. Dynamically generated curriculum — where the LLM invents what to teach from scratch — will hallucinate, drift, and give instructions that don't match the student's actual stack. Hardcoded JSON templates eliminate this failure mode entirely. The LLM's job is to personalize the language, not invent the structure. 

- Archetype 1: AI Powered App A web application where the core feature calls an LLM API. - Examples: AI chatbot, document summarizer, code explainer, AI tutor clone, prompt based content generator. 

- Archetype 2: RESTAPI Backend A server side application exposing data through HTTP endpoints. Examples: task manager API, user authentication system, data pipeline, portfolio backend, sports stats tracker. 

- Archetype 3: Full Stack Web App A complete application with frontend, backend, and database. Examples: social bookmarking app, expense tracker, recipe manager, simple SaaS dashboard. 

## How Archetype Matching Works 

After intake, Codize classifies the student's project into one of the three archetypes using a simple LLM classification call. The prompt is explicit: "Given this project description, which of the following three archetypes best describes it: [Archetype 1], [Archetype 2], [Archetype 3]? Return only the archetype number." Classification is one call, result is deterministic (temperature=0), and it maps to the hardcoded template. 

If the project genuinely doesn't fit any archetype, Codize says so honestly during intake: "Your project as described is a bit broader than what we currently support well. Here's the closest archetype — want to adjust your scope or proceed knowing the curriculum may not be a perfect fit?" This is better than silently giving bad curriculum. 

## The Hardcoded JSON Template Structure 

Each archetype is a JSON file defining the phase structure, required concepts per phase, AI- appropriate tasks, and human required tasks. The LLM reads this template and personalizes variable placeholders with the student's specific project context. It does not add phases, remove phases, or invent new concepts. 

## — - Example Archetype 1 (AI Powered App), Phase 3 template: 

json 

{ "phase": 3, "phase_title": "LLM Integration", "core_concept": "How LLM APIs work — message structure, context windows, tokens, a "ai_appropriate_tasks": [ "Generate boilerplate API client class", "Generate error handling for rate limits and timeouts" ], "human_required_tasks": [ "Write the system prompt for [PROJECT_PURPOSE]", "Design the conversation state management logic", "Determine what context to include per call and why" ], "explanation_gate_targets": [ "Why the system prompt is structured the way it is for [PROJECT_PURPOSE]", "What happens to conversation history between calls", "How token cost is calculated and why it matters for [PROJECT_SCALE]" ], "gate_depth": "medium", "unlock_condition": "3-turn gate passed with no unresolved follow-ups", " " " - — functional_unlock : Advanced: pre built streaming response handler skip manual }   

## What the LLM personalizes (the variables in brackets): 

- [PROJECT_PURPOSE] → filled from intake answer 1 and 2 

- [PROJECT_SCALE] → filled from intake answer 5 (deadline/scope) 

- All explanations, examples, and encouragements are written in the context of their specific project 

## What the LLM never touches: 

Phase order 

- - 

- Which tasks are AI appropriate vs human required 

- The gate targets 

- The unlock conditions 

- The functional unlock rewards 

" - This is a hard constraint enforced in the system prompt: You are personalizing a pre defined - curriculum template. You may change wording and add project specific examples. You may not add phases, remove phases, change which tasks are marked AI-appropriate, or alter gate targets." 

Codize selects the specific tech stack for the student's project during roadmap generation. The selection follows this priority order: use the student's stated preferred language wherever possible, use industry-standard tools for the archetype when the student's preference doesn't fit, flag any language gap explicitly and apply the 20% rule. 

The 20% rule: If the project requires a language the student doesn't know well but only needs a — " ' small portion of it, Codize says this explicitly You ll need some JavaScript for the frontend. You only need about 15% of the language for what we're building. I'll teach you exactly those parts, mapped to [their known language] equivalents. The rest the AI can generate and you'll review." If the gap is larger than ~30%, Codize flags it at intake and asks if they want to adjust scope or extend their timeline. 

## — - Security Architecture Constraints Non Negotiable Across All Archetypes 

Security is not a module at the end. It is a set of architectural constraints encoded into every archetype template from Phase 1. The reason is practical: security issues are architectural decisions. A student who builds their entire app making direct LLM API calls from the frontend and then gets told in the final module that all their keys are exposed has to rebuild significant parts of their app. Codize teaches the correct architecture from the start. Security is a byproduct - of building correctly, not an add on. 

## Why "just a project" is not an excuse to skip this: 

Students push to public GitHub repos. They share links. They leave apps running. A portfolio project with exposed API keys signals to any hiring engineer who reads the code that the developer doesn't understand how secrets work. That is a career consequence, not just a security risk. Codize's mission is to teach students to build like professionals. Professional-grade security practices are part of that mission regardless of whether the student intends to ship to real users. 

## - The three non negotiable constraints encoded in every archetype template: 

Constraint 1 — All secrets live server-side. Always. No API keys, tokens, passwords, or secrets of any kind in frontend code. This applies even if they are stored in .env files — build processes bundle .env variables into JavaScript. Anyone can extract them from the browser. The enforced architecture is: frontend calls the student's backend, backend calls the external API with the real — key. This is also the correct architecture for every other reason rate limiting, error handling, — logging so Codize teaches it as the right way to build, not as a security restriction. 

The archetype template marks any task involving external API calls as human-required with an explicit note: "This call must happen in your backend. If you are writing this in frontend code you are doing it wrong." 

Constraint 2 — RLS enabled on every Supabase table before any other database code is — written. The Supabase anon key is public by design it is included in frontend code and visible 

to anyone. Row Level Security is what prevents that public key from being used to read or write data it shouldn't access. RLS disabled means any table is wide open to anyone who finds the URL and knows basic SQL. 

- The database phase template makes RLS the first human required task, before schema design, before writing queries, before anything else: "Enable RLS on this table and write an ownership policy before continuing. Do not proceed until this is done." The gate for the database phase cannot be passed without the student explaining what their RLS policy actually enforces and " " — " why user is logged in is not sufficient ownership must be verified, meaning user is logged in AND this row belongs to this user." 

Constraint 3 — Auth enforced at the API layer, not the UI layer. Hiding a button or redirecting a page does not protect a route. Anyone can call an API endpoint directly without touching the UI. - Authentication must be verified server side on every protected endpoint. The archetype templates mark auth middleware as human-required on every route that touches user data, with the explicit note: "Hiding this in the UI does not protect it. This check must happen here, in the backend, on every request." 

## The three OWASP issues encoded in the templates (A01, A02, A03): 

These are the three OWASP Top 10 items most likely to appear in the three archetypes. They are taught in context during the relevant phase, not as a separate OWASP module. 

OWASP A01 (Broken Access Control) → covered in the auth and database phases via Constraint 2 and Constraint 3 above. The gate question for these phases explicitly asks the student to explain what would happen if the ownership check were removed. 

OWASP A02 (Cryptographic Failures / Secrets Exposure) → covered in the first phase that involves any external API call via Constraint 1. The gate question asks the student to explain why a .env file in frontend code does not protect a secret. 

OWASP A03 (Injection) → covered in any phase involving user input that reaches a database or gets rendered in the UI. The template marks input validation as human-required and the phase explanation covers parameterized queries vs string concatenation and XSS on rendered content. The gate asks the student to demonstrate they know what breaks if validation is removed. 

Full OWASP audit, rate limiting, DDoS protection, and penetration testing are explicitly out of scope for MVP-level projects and are listed in the Section 5 out-of-scope list. Students who indicate during intake that they intend to ship to real users with real data receive a note at the end of their roadmap flagging these as next steps with links to relevant resources. 

## - — Pre Deployment Security Checklist Mandatory Final Phase 

- Every archetype template ends with a pre deployment checklist phase. This is not a learning — phase it is a verification phase. The concepts were taught during the relevant phases earlier. This phase confirms the implementation is actually correct before the student ships. 

- The checklist is gate checked. The student cannot mark their project complete without passing — it. The gate for this phase does not ask conceptual questions it asks the student to verify each item against their actual running app and explain what they found. 

## — The checklist every item is mandatory for every archetype: 

- Search entire codebase for api_key , secret , sk_live , token , password . Confirm none appear in any frontend file or any file committed to the public repo. 

- Open browser DevTools Network tab. Make requests in the app. Confirm no secrets appear in any request or response payload. 

- Confirm all external API calls with secrets are made from backend functions, not frontend code. 

- Open Supabase Authentication → Policies. Confirm RLS is enabled on every table. Confirm every policy checks ownership, not just login status. 

- Attempt to access a protected route directly via URL or curl without being logged in. Confirm it returns 401, not data. 

- Attempt to access another user's data by manipulating a resource ID in a request. Confirm it returns 403 or 404, not the other user's data. 

- Confirm every user input that reaches the database uses parameterized queries, not string concatenation. 

- Confirm every user input that gets rendered in the UI is sanitized or escaped before rendering. 

- Run the app URL with /api , /admin , /dashboard , and other common paths appended. 

- Document what responds and confirm nothing sensitive is exposed unintentionally. 

- " Gate question for the pre deployment checklist phase: Walk me through one item on this checklist. Tell me what you checked, what you found, and what you did or confirmed as a result." Turn 2 and Turn 3 probe deeper on whatever they chose. A student who says "I checked and everything is fine" without being able to describe what they actually looked at fails immediately. 

## — Section 3 The Interrogation Gate 

## What It Is 

The gate is a mandatory, multi-turn conversational interrogation that must be passed before the next phase unlocks. It is not a quiz. It is not a text box. It is not optional. The student demonstrates understanding through a live conversation about specific decisions in their actual work, not about concepts in the abstract. 

The gate cannot be skipped. The student can choose the format of the gate (explained below) but cannot bypass it entirely. This preserves the autonomy finding from the basic psychological 

needs research (Vansteenkiste et al.) without creating a skip button. 

## — Gate Format Choice Autonomy Over How, Not Whether 

Before each gate, Codize presents two options: 

— - " Option A Architecture Explanation (3 turn conversation) Walk me through what you just ' - " built. I ll ask follow up questions based on your answers. 

— " ' Option B Bug Hunt I ve identified something in your approach that could cause a problem under certain conditions. Find it and explain why it matters." 

Both options unlock the next phase upon passing. Neither can be skipped. The choice is genuine — - students who prefer explaining will choose A, students who prefer problem solving will choose B. This is meaningful autonomy, not theater. 

For the MVP, Option A is the primary path. Option B requires Codize to reliably identify genuine issues in student work, which is a harder technical problem. Option B can be included in MVP as an occasionally offered variant but should not be the default. 

## - — The 3 Turn Gate Exact Mechanics 

## Turn 1 — Anchor statement + open question about a specific decision 

- Before the interrogation question is asked, Codize requires the student to provide a self reported implementation anchor. The prompt is: 

" — Before we start in one sentence, describe the specific structure you built for this phase. Name at least one variable, function, or database field." 

This anchor serves two purposes: it forces the student to ground themselves in their actual code before the conversation begins, and it gives the evaluator LLM a specific implementation detail to check Turn 3 answers against. This is the MVP's substitute for code submission. It is not verifiable against actual code — that requires code submission, which is a v2 feature — but it raises the bar substantially against students who answer in pure generalities. 

- MVP caveat on implementation specificity: In the MVP, the anchor statement is self reported and unverified. A student could fabricate a variable name. The Condition 3 rubric check (described below) creates meaningful friction against this because fabricated details tend to be generic or inconsistent across turns. Full verification of implementation specificity requires code — submission logged as a v2 improvement priority. 

After the anchor is given, Codize asks the Turn 1 question. The question references their specific project, not a generic concept. 

Bad (generic): "Explain how authentication works." 

Good (specific): "You chose to store user sessions in [database] rather than using JWTs. Walk me through that decision and what it means for your app." 

The question is generated from the phase's explanation_gate_targets in the template, 

personalized to their implementation. Temperature is set low (0.3) to keep questions focused and consistent. 

## — - Turn 2 Targeted follow up on the weakest part of their answer 

Codize evaluates the Turn 1 response against three criteria: accuracy (is it correct?), specificity (does it reference their actual implementation or generic knowledge?), and completeness (did they address the core of what was asked?). The Turn 2 question drills into whichever criterion scored lowest. 

If Turn 1 was accurate but generic: "You've described how this works generally. Tell me — " specifically how it works in your project what happens when [specific scenario in their app]? 

" — If Turn 1 was specific but incomplete: Good you covered [X]. Now explain what happens in the edge case where [Y]." 

" ' — If Turn 1 was inaccurate: That s not quite right. Let me give you a hint [targeted hint, not the answer]. Try again." 

## — Turn 3 Application to a hypothetical 

The student must apply their understanding to a slightly different scenario than what they built. - This is the anti cheat mechanism. The hypothetical is generated fresh based on their Turn 1 and - ' Turn 2 answers, making it impossible to pre generate via ChatGPT because the hypothetical s specific form wasn't known until this moment. 

Format: "Given what you've built, what would break or need to change if [specific variation]?" 

Example: "You built this so users authenticate once and stay logged in. What would need to change if you wanted sessions to expire after 30 minutes of inactivity?" 

This question requires understanding of their specific implementation, not the concept generally. A student who copy-pasted their Turn 1 answer from ChatGPT cannot answer Turn 3 without starting a new ChatGPT conversation about their specific code in a specific hypothetical — at which point the effort exceeds the effort of just understanding it. 

## - — Anti Cheat Properties Why This Works 

- The copy paste attack (student pastes gate question into ChatGPT) fails progressively across turns: 

— Turn 1 can be cheated the question is knowable in advance, roughly. 

— Turn 2 cannot be predicted it depends entirely on how the student answered Turn 1. 

— ' Turn 3 cannot be predicted it depends on Turn 1 and Turn 2 combined, and it s a hypothetical about their specific code. 

- By Turn 3, the student would need to share: their full code, their Turn 1 answer, the Turn 2 follow up, their Turn 2 answer, and then ask for a hypothetical response — and then type that response back into Codize. The total effort of this process is approximately equal to the effort of actually understanding the material. This is the structural defense. It is not foolproof. It is sufficient. 

## — - Gate Evaluation The Three Condition Rubric 

The gate evaluates Turn 3 via a second LLM call at temperature=0. The rubric is binary: PASS or - FAIL, with a one sentence reason. No partial credit. No middle ground. 

## — The three conditions all three must be satisfied for a PASS: 

— Condition 1 Structural Identification: Did the student identify the exact component, data structure, or architectural point in their code that would need to change? Generic descriptions of how a concept works do not satisfy this. They must name what specifically changes in their implementation. 

— Condition 2 System Ripple Effect: Did the student correctly state the immediate consequence of that change on the rest of their app? Not what the concept does in general — what breaks, shifts, or must be updated in their specific project as a result of the modification described in the hypothetical. 

— Condition 3 Implementation Specificity: Does the response reference at least one specific — element from their Turn 1 anchor statement or prior turns a variable name, a function they named, a schema field, a specific design decision? A response that is technically correct about the concept but contains no specific reference to their actual implementation is an automatic FAIL under this condition. 

- — - The auto fail rule: Any response that reads as a textbook definition correct, well written, and completely detached from their specific project — fails automatically regardless of whether Conditions 1 and 2 are technically satisfied. The evaluator prompt explicitly checks for this pattern. 

Evaluator prompt instruction: "If the response could have been written by a student who has never seen this specific codebase — if it contains no reference to the student's specific variables, functions, schema, or architectural decisions as established in the anchor statement and prior turns — return FAIL regardless of technical correctness." 

If the student fails Turn 3, Codize does not let them retry immediately. It says: "Your answer shows you understand the concept but not yet how it works in your specific code. Go back and re-read [specific part of their implementation]. Come back when you can tell me what [specific " - line or function] actually does in context. This prevents grinding. There is a 30 minute cooldown before re-attempting the same gate. 

## Context Management Across Turns 

All three gate turns are held in a dedicated conversation thread separate from the main project 

workspace. The context window for a gate session includes: the phase template targets, the student's Turn 1 and Turn 2 answers verbatim, and a summary of the student's project and stack. — It does not include the full project workspace history this keeps the gate focused and prevents the LLM from drifting into general tutoring mode. 

After the gate is passed, the gate transcript is summarized and stored in the student's learning — profile. This summary is used to calibrate difficulty in future gates students who passed Turn 3 easily get harder hypotheticals next time; students who struggled get more targeted Turn 1 questions. 

## — Section 4 The Functional Reward System 

## The Psychological Foundation 

Schultz's dopamine research establishes that rewards must be unexpected to produce the strongest learning signal. Predictable rewards — you complete phase, you get badge — become normalized within days and lose their motivational effect. The reward system must therefore have two properties: functional value (the reward actually helps) and variable timing (the student cannot predict exactly when or what they'll unlock). 

The incentive research adds a second constraint: incentivize process and effort, never outcome. Rewarding a perfect gate score incentivizes gaming the gate. Rewarding demonstrated engagement over time, consistency, and depth of explanation produces genuine behavior change. 

Codize does not use badges, XP bars, leaderboards, or streaks as primary reward mechanisms. These are shallow signals that correlate weakly with actual learning and are easily gamed. 

## What Gets Tracked (Process Metrics) 

Codize tracks the following signals per student: 

Gate quality score — the evaluator LLM scores each Turn 3 response on a scale of 0–10 based on - depth and specificity against the three condition rubric. A score of ≥7 across two consecutive — phases triggers the first functional unlock. No deductions for retries only the final Turn 3 quality matters. A complete gate failure (30-minute cooldown triggered) records a score of 0 for that phase. Updated after every gate. 

Return rate — did the student come back the next day, or did they disappear for a week? Tracked per project. 

— Stuck behavior when the student pauses for more than 10 minutes in a phase, do they ask Codize for a hint, ask for the answer, or push through? The first is good. The second is worth noting. The third is worth rewarding. 

— ' Explanation vocabulary growth over time, does the student s language in gate responses become more precise and technical? Tracked via a simple embedding comparison between early and recent gate transcripts. 

None of these metrics are shown to the student as numbers or scores. They are used internally to calibrate difficulty and trigger functional rewards. 

## — Functional Unlocks Exact Examples 

Functional unlocks are capabilities within the Codize workspace that save real time or skip tedious work. They are earned through demonstrated quality, not time. They are described 

functionally, not as "prizes." The student should think "oh that's actually useful" not "oh I got a reward." 

## Examples of functional unlocks: 

"Your explanation of the authentication architecture was thorough enough that we can skip the — ' - basic session setup walkthrough in Phase 4 here s the pre configured session handler. Plug this in and we'll move straight to the logic layer." 

"Based on how you explained your database schema, you clearly understand the data 

relationships. You've unlocked the advanced query builder — this gives you a set of pre-written complex queries for your specific schema that would have taken Phase 5 to work through manually." 

"Your gate score across the last three phases puts you in the top cohort for architectural 

reasoning. You've unlocked the system design review — at the end of your project, Codize will do a full architectural critique of your codebase and give you a written technical review you can reference in interviews." 

These unlocks must meet three criteria to qualify. They save real time or effort (not cosmetic). They are tied to demonstrated quality in the specific area they skip. They are described in functional terms without gamification language. 

## What Triggers a Functional Unlock 

Unlocks are not triggered by completing phases. They are triggered by performance thresholds that the student cannot directly observe or target. Specifically: 

Gate quality score above threshold for two consecutive gates → unlock that skips configuration work in the next phase. 

Return rate showing three consecutive days of engagement → unlock that provides a pre-built component relevant to their current phase. 

Explanation vocabulary growth detected between Phase 2 and Phase 4 → unlock the system design review (described above). 

The student does not know these thresholds. They know unlocks exist — Codize mentions this briefly during onboarding — but not when or why they trigger. This variable ratio schedule is the - Schultz derived mechanism. The brain responds to unexpected rewards more strongly than predictable ones. The student improves their explanations because they care about understanding, and the unlock appears as a consequence, not a target. 

## The Yeager Reconnection Trigger 

When process metrics detect disengagement — the student hasn't returned for 3+ days, or has been stuck on the same phase for more than a week — Codize surfaces a reconnection prompt on next login that references their intake purpose answer directly. 

Implementation: On login, the frontend checks the last_login timestamp in Supabase. If the delta is >72 hours, a modal renders before the workspace is accessible. The modal shows: 

- Their exact intake purpose statement in large text 

- One sentence on what completing their current phase means for that purpose 

- A single button: "Let's keep building" 

— The modal is dismissed only by clicking that button not by a timer, not by clicking outside, not by pressing Escape. The act of clicking forces one moment of intentional acknowledgment. This - - is the mechanism. A 5 second auto dismiss would allow users to look away immediately and not read it, defeating the purpose entirely. 

- - ' Why click to dismiss and not a timer: Schultz s research shows the dopamine signal transfers — to the predictor of the reward, not the reward itself. A timer becomes a waiting game the - student looks away and waits it out. A required click creates a micro commitment that primes engagement before the workspace loads. The 5 seconds of forced waiting Gemini suggested creates friction without attention. A required button click creates attention without friction. 

This is not a generic "come back!" notification. It is a personalized reference to their stated reason ' - for building. Yeager s research shows this framing is significantly more effective at re engagement than self-oriented prompts like "you're almost done" or "don't break your streak." 

## — Section 5 Scope Constraints for October 26 

## - Strict In Scope (Must work on October 26) 

These are non-negotiable. If any of these don't work, the product doesn't exist yet. 

Auth and user state Email/password signup and login via Supabase Auth. User profile stores intake answers, stack preferences, active project, phase progress, gate history summary, and - session log. Survives page refresh and cross device login. 

Intake flow All five conversational intake questions, sequential, mandatory. Codize classifies project into one of three archetypes. Codize applies the 20% rule and flags language gaps. Codize acknowledges if the project doesn't fit an archetype cleanly. 

Roadmap generation for all three archetypes Full phase list with phase titles, concept 

- - summary, AI vs human task split, and timeline estimate. Rendered in the workspace. Clickable per phase. 

Phase workspace Each phase shows: the concept explanation personalized to their project, the task list with AI/human labels, and resources. Student can mark tasks complete. Progress is saved. 

- The 3 turn interrogation gate Option A (architecture explanation) working for all three archetypes. Turn 1 pulls from template gate targets. Turn 2 dynamically follows up on the weakest part of their response. Turn 3 presents a fresh hypothetical. Pass/fail evaluation via - second LLM call. 30 minute cooldown on failed attempts. Gate transcript stored and summarized in profile. 

- Functional unlocks (at least two working examples) Two concrete unlocks implemented end 

- - - to end: one that skips a configuration step in Phase 3 4 range, one that provides a pre built component. Triggered by gate quality score threshold across two consecutive gates. 

Yeager reconnection Stored intake purpose answer. If student has not returned in 72 hours, reconnection prompt surfaces on next login referencing their purpose answer. 

Basic working UI Three screens: intake conversation, roadmap view with phase navigation, phase workspace with gate. Rough is fine. Must be functional on desktop browser. No mobile requirement. 

Deployed and accessible Frontend on Vercel, backend on Railway. Both environments have environment variables set correctly. App loads without errors for a new user going through the full flow. 

## - - Explicitly Out of Scope for October 26 

These are v2 features. Do not start building any of them before the five in-scope items are working completely. 

— Advanced security hardening rate limiting, DDoS protection, penetration testing, full OWASP Top 10 audit, CSP headers, and security scanning tools are out of scope for MVP. The - - - three non negotiable constraints (secrets server side, RLS, server side auth) and the three OWASP items (A01, A02, A03) are in scope and baked into the templates. Everything beyond that is flagged as next steps for students who intend to ship to real users with real data, not taught as part of the core curriculum. 

— Code submission UI or embedded editor the MVP does not require the student to submit code to Codize. The gate interrogates their understanding verbally. Code submission is a v2 

feature that substantially improves gate quality but is significant additional scope. 

— Option B gate (bug hunt) needs reliable issue identification in student code, which requires code submission. Out of scope until code submission exists. 

Mobile responsiveness — desktop only for MVP. 

— Polished CSS or design system rough and functional is the standard. No design polish until the core loop is working. 

— More than three archetypes do not add a fourth archetype before October. The temptation will come. Resist it. 

— ' Adaptive learning profile storing and using the student s explanation vocabulary growth over time. The data should be logged for future use, but the adaptive calibration system is v2. 

Payment or monetization — not in scope until there are users who want to pay. 

Social features — no leaderboards, no cohort views, no sharing. 

— Browser extension or VS Code integration v2, requires a separate technical foundation. 

- — RAG based dynamic curriculum the MVP uses hardcoded JSON templates. RAG for curriculum generation is explicitly ruled out for MVP based on hallucination and context drift risk. 

— Instructor or institutional features no class management, no assignment integration, no LMS compatibility. 

## — Resolved Decisions No Longer Open 

These were flagged as unresolved in v1.0. All five are now locked. Do not re-open them. 

Gate pass/fail rubric: Three conditions — Structural Identification, System Ripple Effect, - Implementation Specificity. All three must pass. Auto fail on generic textbook responses regardless of technical correctness. Evaluator LLM at temperature=0 returns PASS/FAIL + onesentence reason + 0–10 quality score. 

Archetype tiebreaker: Hierarchical priority. If LLM API is a core feature → Archetype 1, no exceptions. If no AI but has frontend/database → Archetype 3. Otherwise → Archetype 2. 

Default stack for Archetype 1: Python + FastAPI + Vanilla HTML/JS. Fixed default. LLM does not decide this ad hoc. 

– Gate quality score threshold: Evaluator LLM scores Turn 3 quality 0 10. Score ≥7 across two consecutive phases triggers first functional unlock. No retry deductions. Full gate failure = score of 0 for that phase. 

- Reconnection prompt infrastructure: In app modal only. No email. Triggered on login if last_login delta >72 hours. Dismissed by clicking "Let's keep building" — not by timer, not by clicking outside. See Section 4 for full implementation spec. 

## - Pre Build Artifacts Required 

These must exist before any backend development begins. Do not write a database schema, system prompt, or API route until both are complete. 

## — Artifact 1 Three Archetype JSON Templates 

The roadmap generation, phase workspace, gate targets, and functional unlock definitions all pull from these templates. They are the ground truth the entire system runs on. Writing them is a – 2 3 day exercise that forces every curriculum decision to be made concretely rather than deferred to the LLM. 

- Each template must define for every phase: phase title, core concept, AI appropriate tasks, - – human required tasks, explanation gate targets (3 5 specific questions), gate depth (light/medium/heavy), unlock condition, and functional unlock reward. 

All three archetypes must be written before any backend work. A partial template set means partial system behavior, which makes debugging impossible. 

## — Artifact 2 Six System Prompts (Draft 1) 

— The six prompts defined in the System Prompt Architecture section must be written in full not as descriptions but as actual prompts — and tested manually in a plain LLM interface before any backend code is written. Test each one against adversarial inputs: a student trying to skip the anchor statement, a student giving a textbook Turn 3 answer, a student whose project doesn't cleanly fit the archetype. Find the holes before they're in production code. 

## System Prompt Architecture — Non-Negotiable Constraints 

The system prompts are the product. These constraints apply to every LLM call in Codize. 

— ' Roadmap generation prompt must include: the full archetype JSON template, the student s intake answers verbatim, explicit instruction that phase structure cannot be altered, explicit instruction to personalize language and examples to the student's project but not invent new phases or concepts. 

— ' Phase explanation prompt must include: the specific phase template, the student s project description and purpose, their stated stack, instruction to reference their specific project in every example. 

Gate Turn 2 prompt — must include: Turn 1 question, Turn 1 student response verbatim, the three evaluation criteria (accuracy, specificity, completeness), instruction to identify the weakest criterion and probe it directly. 

Gate Turn 3 prompt — must include: Turn 1 and Turn 2 exchange, instruction to generate a hypothetical that requires applying their specific implementation to a changed condition, explicit instruction that the hypothetical must not be answerable from general knowledge alone. 

— Gate evaluation prompt must include: all three turns verbatim including the Turn 1 anchor - statement, the full three condition rubric (Structural Identification, System Ripple Effect, - Implementation Specificity) in plain language, the auto fail instruction for generic textbook responses, temperature 0, instruction to return PASS or FAIL with a one-sentence reason and a – score of 0 10 for the Turn 3 response quality. 

## What Codize Is Not 

State this clearly to avoid scope creep. 

Codize is not a tutorial platform. It does not teach concepts from scratch to beginners. 

Codize is not a code generator. It does not write code for students. 

Codize is not a plagiarism detector. It does not try to catch cheaters. It makes genuine understanding the most efficient path. 

Codize is not a chat tool. It is a structured project workspace with a conversational interface. 

Codize is not Duolingo for coding. Shallow gamification is explicitly avoided based on the incentive research reviewed. 

This document represents the consensus output of a full product debate incorporating: threepanel critique (Stanford admissions, Silicon Valley staff engineer, cynical PM), Gemini crossvalidation on two drafts, behavioral research review (Schultz 2016, Yeager 2014, Vansteenkiste et al., incentive crowding-out literature), and direct product design iteration across 40+ exchanges. v1.1 incorporated three post-consensus corrections: reconnection modal changed from 5-second timer to click-to-dismiss; gate rubric expanded with Condition 3 (Implementation Specificity) - plus Turn 1 anchor statement and MVP caveat; Pre Build Artifacts Required section added. v1.2 - added Security Architecture Constraints section to Section 2: three non negotiable constraints across all archetypes (secrets server-side, RLS on all tables, server-side auth enforcement), - OWASP A01/A02/A03 encoded directly into relevant phase templates, mandatory pre 

deployment security checklist as final phase of every archetype, and advanced security topics added to out-of-scope list. Any feature or decision not addressed here should be pressure-tested against the core mission before being added to scope. 

