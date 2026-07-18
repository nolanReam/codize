// Beginner-friendly phase guidance (M13E.1). Deterministic and client-side —
// no LLM call: phase titles come from the three fixed archetype templates, so
// a keyword map covers every real title, with a safe generic fallback for
// personalized wording drift. `meaning` explains the phase in plain language;
// `asks` are starter requests the student can drop into the Prompt Builder.

export interface PhaseGuide {
  meaning: string;
  asks: string[];
}

const GUIDES: { match: RegExp; guide: PhaseGuide }[] = [
  {
    match: /api design|resource model/,
    guide: {
      meaning:
        "Deciding what information your app keeps track of (the data) and what actions it offers (the routes) — on paper, before anyone writes real code. Getting this right stops AI from generating random files that don't fit together.",
      asks: [
        "Help me design the data model for my app — what should it store, and how do the pieces relate?",
        "Suggest database tables and explain what each field means.",
        "List the API routes I need before writing any code.",
        "Ask me questions if my design is missing ownership or permissions.",
        "Do not write code yet — just the plan.",
      ],
    },
  },
  {
    match: /architecture/,
    guide: {
      meaning:
        "Planning what pieces your app has (pages, server, database, outside services) and how they talk to each other — a map you draw before building, so every later step has a place to go.",
      asks: [
        "List the components my app needs and what each one is responsible for.",
        "Walk me through what happens, step by step, when a user does the main action in my app.",
        "Ask me questions about anything unclear or missing in my idea before proposing a design.",
        "Keep it simple — the smallest set of parts that works.",
      ],
    },
  },
  {
    match: /server foundation|backend foundation/,
    guide: {
      meaning:
        "Getting a minimal server running that you can start, stop, and check is alive — the skeleton every later feature hangs on. Small on purpose: prove the base works before adding anything.",
      asks: [
        "Set up a minimal server app with one health-check route, and explain what each file does.",
        "Explain what each starter file and setting is for, in one sentence each.",
        "Show me how to run it locally and how to tell it's working.",
        "Don't add any features yet — just the running skeleton.",
      ],
    },
  },
  {
    match: /schema|database|rls/,
    guide: {
      meaning:
        "Deciding what tables your database has, and — just as important — who is allowed to see each row. Rules like \"users only see their own data\" get set here, at the database, not just in the UI.",
      asks: [
        "Suggest the database tables I need and explain what each field means.",
        "Add an owner column to each table and explain how row-level security keeps users' data separate.",
        "Ask me questions if the schema is missing ownership or permissions.",
        "Show me how to verify that one user cannot read another user's rows.",
      ],
    },
  },
  {
    match: /auth/,
    guide: {
      meaning:
        "Login and identity: proving who the user is, and making the server re-check it on every request. The key idea — hiding a button in the UI is not security; the server must enforce it.",
      asks: [
        "Add signup and login, and walk me through where the session actually lives.",
        "Explain the difference between the page hiding something and the server refusing it.",
        "Make every protected route check the user server-side, and show me the check.",
        "Do not store passwords yourself — use the auth service, and explain why.",
      ],
    },
  },
  {
    match: /crud|validation/,
    guide: {
      meaning:
        "The everyday actions — create, read, update, delete — plus checking every piece of user input so bad or malicious data can't sneak into your database.",
      asks: [
        "Add the create and list endpoints for my main resource, validating every field.",
        "Show me what happens if someone submits an empty value, a huge string, or someone else's id.",
        "Explain how the input validation protects the database.",
        "Only these endpoints — don't touch auth or the schema.",
      ],
    },
  },
  {
    match: /llm integration/,
    guide: {
      meaning:
        "Calling the AI model from your backend — never from the browser, where the API key would be visible to anyone — and handling its answers (and failures) safely.",
      asks: [
        "Add one backend route that calls the model and returns the reply.",
        "Keep the API key server-side only, and show me exactly where it's read from.",
        "What happens if the model call fails or times out? Handle that visibly.",
        "Explain why the browser must never call the model API directly.",
      ],
    },
  },
  {
    match: /integration/,
    guide: {
      meaning:
        "Wiring the pages to your backend so real data flows: forms actually save, lists show what's in the database, and errors show up somewhere a user can see them.",
      asks: [
        "Connect this form to the API route, and handle loading and error states visibly.",
        "Explain, step by step, what happens when I submit the form.",
        "Show me one thing that could fail in this wiring and how I'd notice it.",
        "Don't change the backend — only the page-to-API connection.",
      ],
    },
  },
  {
    match: /frontend|conversation ui/,
    guide: {
      meaning:
        "The pages people actually see and click. The goal is a simple working screen wired to real data — not a design showcase.",
      asks: [
        "Build the page that lists my data from the API, with loading, empty, and error states.",
        "Keep the styling simple and explain the component structure you chose.",
        "Ask me before adding any component library or dependency.",
        "Only this page — don't restructure the rest of the app.",
      ],
    },
  },
  {
    match: /persistence|history/,
    guide: {
      meaning:
        "Saving things so they're still there after a refresh — stored per user, with the ownership checks that keep one user's data invisible to another.",
      asks: [
        "Store this data per user and show me where the ownership check happens.",
        "Explain what happens to the data when the user logs out and back in.",
        "Show me how to verify another user can't see my saved data.",
      ],
    },
  },
  {
    match: /error handling|testing|documentation/,
    guide: {
      meaning:
        "Making failures graceful instead of crashes, and writing tests — proof your app behaves, including when someone feeds it garbage.",
      asks: [
        "Add tests for my main endpoint, including at least one failure case.",
        "Make bad input return a clear error message instead of a crash, and show me the before/after.",
        "List the errors a user could realistically hit, and what they'd see for each.",
      ],
    },
  },
  {
    match: /security checklist|deployment/,
    guide: {
      meaning:
        "A pre-flight check before anyone else can reach your app: no secret keys shipped to the browser, permissions enforced server-side, input checked. This is the phase that keeps your project from being someone else's target practice.",
      asks: [
        "Check my project for any secret key that would end up visible in the browser.",
        "Walk through the security checklist with me one item at a time — explain each before fixing anything.",
        "Show me how to test that a logged-out user (and a different user) is actually blocked.",
      ],
    },
  },
];

const FALLBACK: PhaseGuide = {
  meaning:
    "This phase builds one specific slice of your project. Use the core concept and current work to keep its purpose and scope clear before moving on.",
  asks: [
    "Explain what this phase's first task involves before writing any code.",
    "Help me with the first task of this phase — one small step at a time.",
    "Ask me questions about my project before proposing anything.",
  ],
};

export function phaseGuide(phaseTitle: string): PhaseGuide {
  const lowered = phaseTitle.toLowerCase();
  return GUIDES.find((g) => g.match.test(lowered))?.guide ?? FALLBACK;
}
