# UI/UX Engineering & Aesthetic Skill
## Purpose
Enforce the exact visual design philosophy, theme, and component structure for the Codize web application interface.

## Core Design Philosophy (The Codize Aesthetic)
- **Theme:** High-contrast, minimalist software-engineering dashboard. 
- **Palette:** Strict Dark Mode baseline. Deep charcoal/near-black backgrounds (`#0d0d12`), cool lavender/violet accents (`#a78bfa`), crisp white/silver text, and distinct functional colors for state changes (e.g., green for passed gates, amber for active checkpoints).
- **Typography:** Technical but readable. Use clean Monospace fonts for code execution blocks and geometric Sans-Serif for primary navigation.
- **Tone:** Look like a premium, highly focused SaaS engineering IDE, not a casual or brightly colored e-learning app.

## Component Architecture Constraints
- **Simplest Implementation Rules:** - Build the simplest robust interface that satisfies the functional specifications.
  - Rely on native HTML5 and modern layout systems (Flexbox and CSS Grid) rather than pulling in massive, unnecessary third-party utility frameworks or component libraries unless explicitly requested.
  - Validate state and UI views rigidly at the boundaries (e.g., API payloads, authentication states), but trust internal framework guarantees.

## Multi-Turn Logic UI Requirements
- **Intake Views:** Ensure conversational state handling is visually clear. The student must see their progress dynamically as they move through the 5 mandatory intake framing questions.
- **The Interrogation Gate View:** Build a dedicated, clean split-screen chat interface for the 3-turn interrogation process. 
  - **Left Side:** Displays the student's current source code/implementation details for context.
  - **Right Side:** The interactive gate terminal where the binary Pass/Fail grading occurs.
- **Reconnection/State Recovery:** The UI must natively accommodate the Spec's requirement for a persistent state reconnection modal to handle unexpected session drops gracefully.