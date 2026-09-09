"""Shared fixture data for eval tests."""

# ---------------------------------------------------------------------------
# Meeting transcripts
# ---------------------------------------------------------------------------

STANDUP_TRANSCRIPT = """
Phil:
Good morning everyone. Let's do a quick standup. I finished the Postgres migration yesterday,
all tests are passing. Today I'm working on the Drive module and the learning coach.

Henry:
I reviewed Phil's PR last night, left a few comments on the error handling. Today I'll finish
the authentication refactor and write unit tests for the new token service.

Phil:
Henry, can you also update the deployment docs by Thursday? The client is asking about the
new setup process.

Henry:
Sure, I'll get that done by Thursday EOD.

Phil:
Great. I also want to flag that we need to schedule a demo for the AyaData team next week.
Can everyone check their calendars and let me know by tomorrow if Wednesday works?

Henry:
Wednesday works for me.

Phil:
Perfect. Elton, can you prepare the slides for the demo? Target audience is non-technical
stakeholders, so keep it high-level.
"""

PLANNING_TRANSCRIPT = """
[Alice] Let's finalize the Q3 roadmap. We have three main tracks: infra hardening,
product expansion, and customer success.

[Bob] For infra, we need to complete the database migration by June 1st. That's blocking
everything else.

[Alice] Agreed. Bob, can you own that and give us a status update every Monday?

[Bob] Yes, I'll take that. I'll also need Dave's help on the networking side.

[Alice] Dave, are you available to support Bob on networking?

[Dave] I can carve out 20% of my time for the next three weeks. I'll send Bob a calendar
invite today.

[Alice] Great. For product expansion, we need the API rate limiting feature shipped by
June 15th. Carol, that's yours.

[Carol] Confirmed. I'll have a design doc ready for review by next Friday.

[Alice] And for customer success — we need to onboard Acme Corp by end of June. I'll
handle the kickoff call scheduling this week.
"""

# ---------------------------------------------------------------------------
# Email samples
# ---------------------------------------------------------------------------

URGENT_CLIENT_EMAIL = {
    "subject": "URGENT: Production outage — API returning 500s",
    "from_name": "Elton Mensah",
    "from_address": "elton@client.com",
    "body": (
        "Phil, we're seeing widespread 500 errors from your API since 14:30 UTC. "
        "Our users can't access the dashboard. This is blocking our entire team. "
        "Please advise ASAP — do you need anything from our side?"
    ),
    "expected_category": "action_needed",
    "expected_urgency_min": 8,
}

NEWSLETTER_EMAIL = {
    "subject": "The Weekly AI Digest — Issue #47",
    "from_name": "AI Weekly",
    "from_address": "digest@aiweekly.io",
    "body": (
        "This week in AI: GPT-4o gets a vision upgrade, Anthropic releases Claude 4, "
        "and Google announces Gemini Ultra 2. Read more inside..."
    ),
    "expected_category": "newsletter",
    "expected_urgency_max": 3,
}

MEETING_REQUEST_EMAIL = {
    "subject": "Re: Let's sync on the Q3 roadmap",
    "from_name": "Sarah Chen",
    "from_address": "sarah@partner.com",
    "body": (
        "Hi Phil, happy to connect. I'm free Tuesday 2-4pm or Thursday morning. "
        "Does either work? We can use my Zoom link."
    ),
    "expected_category": "follow_up",
    "expected_needs_reply": True,
}

# ---------------------------------------------------------------------------
# Intent classification test cases
# ---------------------------------------------------------------------------

INTENT_CASES = [
    ("show me my tasks for today", "task.list"),
    ("remind me to send the report to Elton by Friday", "task.create"),
    ("what's in my inbox?", "email.read"),
    ("triage my email", "email.triage"),
    ("draft a reply to Sarah's meeting request", "email.draft"),
    ("summarize yesterday's standup meeting", "meeting.summarize"),
    ("process this meeting transcript", "meeting.transcribe"),
    ("generate my morning brief", "brief.generate"),
    ("change my brief to 8am", "brief.configure"),
    ("help me build a learning roadmap for Rust", "learning.plan"),
    ("what should I study today?", "learning.prompt"),
    ("suggest something I can do this weekend", "life.suggest"),
    ("find my notes from last week", "drive.search"),
    ("what did we decide in the last board meeting?", "memory.recall"),
    ("hello, how are you?", "general.chat"),
]

# ---------------------------------------------------------------------------
# Expected action items from STANDUP_TRANSCRIPT
# ---------------------------------------------------------------------------

STANDUP_EXPECTED_ACTIONS = [
    {
        "keywords": ["deployment", "docs", "documentation"],
        "owner_contains": "henry",
        "due_hint": "thursday",
    },
    {
        "keywords": ["demo", "slides", "presentation"],
        "owner_contains": "elton",
    },
    {
        "keywords": ["demo", "schedule", "calendar", "wednesday"],
        "owner_contains": None,
    },
]
