"""
Automated Sentiment Simulation Runner — Engram (Second Brain SaaS)

Runs the full pipeline without touching the UI:
  1. Preview seed → get markdown + simulation_requirement
  2. Upload markdown → generate ontology (async task)
  3. Build knowledge graph (async task)
  4. Create campaign
  5. Prepare campaign (agent + config generation)
  6. Start simulation (3 scenarios: baseline, competitive, crisis)

Usage:
  cd /Users/prathamesh/Documents/MiroFish/backend
  python scripts/run_engram_simulation.py

Requirements:
  - Backend running on http://localhost:5001
  - pip install requests
"""

import time
import json
import sys
import requests

BASE_URL = "http://localhost:5001"

# ── Seed Template ──────────────────────────────────────────────────────────────

SEED = {
    "product_name": "Engram",
    "product_category": "AI Knowledge Management SaaS",
    "tagline": "Drop anything in. Your second brain builds itself.",
    "target_market": (
        "Knowledge workers, indie researchers, software engineers, writers, and graduate students aged 22-42 "
        "who consume 10+ articles/papers/videos per week but struggle to retain, connect, and retrieve what they learn. "
        "Primarily English-speaking, US/Canada/UK/Australia markets. Tech-forward early adopters who already use "
        "tools like Notion, Obsidian, Readwise, or Roam Research — and feel the friction."
    ),

    "product_story": (
        "Engram was built out of personal frustration. The founder — a solo software engineer — spent 3 years "
        "building elaborate Obsidian vaults, Notion databases, and bookmark systems, only to realize they "
        "could never find what they saved when they needed it. The insight: the problem isn't capture, it's "
        "synthesis and retrieval. Engram replaces the friction-heavy manual PKM workflow with a fully automated "
        "pipeline: drop anything in, AI handles the rest. Built on GPT-4o-mini + Zep memory graphs. "
        "Currently in public beta with 1,200 waitlist signups, 340 active beta users, and 4.7/5 average rating "
        "from 80+ beta feedback responses. NPS score: 62. Average session length: 14 minutes. D7 retention: 38%."
    ),

    "core_features": [
        {
            "name": "Zero-Friction Universal Capture",
            "description": (
                "Drop a URL, paste text, upload a PDF or EPUB, or forward an email — "
                "Engram's ingestion pipeline automatically fetches content (bypassing soft paywalls via Reader Mode), "
                "extracts the full text, runs GPT-4o-mini summarization with 5 key takeaways, assigns topic tags, "
                "and stores everything in under 8 seconds. Browser extension (Chrome/Firefox/Arc) for one-click capture. "
                "Mobile share-sheet support for iOS and Android. No manual tagging ever required."
            )
        },
        {
            "name": "Semantic Search with Concept Expansion",
            "description": (
                "Full-text vector search across every entry in your vault. Search by concept, not keywords — "
                "query 'distributed systems trade-offs' and surface notes about CAP theorem, consensus algorithms, "
                "and that blog post about Dynamo you saved in 2022. Sub-200ms latency on vaults up to 10,000 entries. "
                "Powered by text-embedding-3-small with hybrid BM25 re-ranking. Results include relevance score "
                "and the exact passage that matched."
            )
        },
        {
            "name": "RAG-Powered Knowledge Chat",
            "description": (
                "Ask your knowledge base anything in plain English. 'What did I learn about React Server Components?' "
                "gets you a synthesized 3-paragraph answer with numbered citations linking back to source entries. "
                "The chat is grounded exclusively in YOUR saved content — no hallucinations from general training data. "
                "Supports multi-turn conversation with context retention. Answers include confidence scores. "
                "Pro users get 200 queries/month; Power users unlimited."
            )
        },
        {
            "name": "Auto-Linking Knowledge Graph",
            "description": (
                "After ingestion, Engram's entity extraction pipeline identifies concepts, people, tools, and events "
                "mentioned in your content and automatically creates bidirectional links to other entries mentioning "
                "the same entities. The result is a living, self-organizing knowledge graph that surfaces connections "
                "you didn't know existed. Visual graph explorer (force-directed, zoomable) included. "
                "Based on Zep's graph memory technology. No manual linking ever required — zero [[wiki-link]] typing."
            )
        },
        {
            "name": "Weekly Intelligence Digest",
            "description": (
                "Every Sunday, Engram sends a personalized email digest summarizing: (1) what you learned this week "
                "grouped by theme cluster, (2) 3 surprising connections between this week's entries and older knowledge, "
                "(3) spaced-repetition prompts for entries you haven't revisited in 30+ days, "
                "and (4) a 'knowledge gap' suggestion based on your reading patterns. "
                "Users in beta report this as their #1 favorite feature — 78% open rate."
            )
        },
        {
            "name": "Highlights & Annotation Sync",
            "description": (
                "Native Kindle highlight import (upload My Clippings.txt), Readwise integration (two-way sync), "
                "and in-app web highlighter. Highlights are treated as first-class entries in the knowledge graph. "
                "Inline annotation support: add your own commentary to any highlighted passage. "
                "All highlights become searchable and linkable within 60 seconds of import."
            )
        },
        {
            "name": "Export & Portability",
            "description": (
                "Full data portability guaranteed. Export entire vault as: (1) Obsidian-compatible markdown vault "
                "with [[wikilinks]] preserved, (2) JSON data dump, (3) PDF report per topic cluster. "
                "No lock-in. If you cancel, your data leaves with you in a format you can read forever. "
                "Power tier includes public API (REST + webhooks) for custom automation and Zapier integration."
            )
        }
    ],

    "pricing_tiers": [
        {
            "name": "Free",
            "price": "$0/mo",
            "description": (
                "Up to 100 entries lifetime. 30 semantic searches/month. 15 AI chat queries/month. "
                "URL capture and PDF upload (max 5MB). Basic knowledge graph (up to 50 nodes). "
                "No credit card required. Designed to let users build genuine dependency before hitting the wall. "
                "Estimated conversion window: 3-6 weeks of regular use."
            )
        },
        {
            "name": "Pro",
            "price": "$14/mo ($11/mo annually)",
            "description": (
                "Unlimited entries and storage. Unlimited semantic search. 500 AI chat queries/month. "
                "Full knowledge graph (unlimited nodes). Weekly Intelligence Digest. Browser extension. "
                "PDF/EPUB upload up to 50MB. Kindle highlight import. Readwise sync. "
                "Priority ingestion queue (< 5 second processing). "
                "Annual plan: $132/yr (saves $36). Most popular tier. "
                "Comparable to Mem AI's $14.99/mo or Readwise's $7.99/mo — but Engram does both."
            )
        },
        {
            "name": "Power",
            "price": "$28/mo ($22/mo annually)",
            "description": (
                "Everything in Pro. Unlimited AI chat queries. Public API access (10,000 req/month). "
                "Webhooks for real-time knowledge graph events. Bulk import (CSV, JSON, Roam export, Logseq export). "
                "Team sharing (up to 3 shared vaults in beta). Priority support with < 4 hour response SLA. "
                "Annual plan: $264/yr. Targets power users, indie researchers, and small teams."
            )
        }
    ],
    "trial_policy": "Freemium (no credit card required). Annual plans have 30-day money-back guarantee.",
    "billing_cycle": "Monthly or annual. Annual saves ~22%. Stripe billing. Cancel anytime.",

    "competitors": [
        {
            "name": "Obsidian (+ AI plugins like Copilot or Smart Connections)",
            "strength": (
                "Massive community (1M+ users), local-first privacy with files on your disk, "
                "beautiful bidirectional linking, plugin ecosystem with 1,000+ plugins, one-time purchase ($50 for Sync + Publish). "
                "Extremely customizable. Beloved by power PKM users."
            ),
            "gap": (
                "Manual everything: you must manually tag, link, and organize every note. "
                "No automatic ingestion pipeline — saving a URL requires copy-paste. "
                "AI plugins are bolt-ons requiring separate API keys and configuration. "
                "Steep learning curve; most users never use 20% of features. "
                "Sync is $8/mo extra. Mobile experience is subpar. "
                "Not a second brain — it's a text editor that requires YOU to be the brain."
            )
        },
        {
            "name": "Mem AI",
            "strength": (
                "Clean, minimal UX. Automatic organization using AI. Semantic search. "
                "Chat with your notes. $14.99/mo. Has funding and VC backing."
            ),
            "gap": (
                "No URL ingestion pipeline — you paste text manually. No PDF upload. "
                "No visual knowledge graph. No browser extension for one-click capture. "
                "No Kindle/Readwise integration. Chat quality reportedly inconsistent. "
                "Users complain about missing mobile app features and slow development pace. "
                "Has pivoted product direction multiple times, causing user trust issues."
            )
        },
        {
            "name": "Notion AI",
            "strength": (
                "All-in-one workspace with databases, docs, projects. Huge brand trust (30M+ users). "
                "Strong collaboration features. AI writing assistant ($8-10/mo add-on). "
                "Integrations with every tool imaginable."
            ),
            "gap": (
                "No semantic search across notes — keyword search only. No knowledge graph. "
                "No automatic ingestion or connection-building. AI is a writing assistant, not a second brain. "
                "Heavily enterprise-focused; individual knowledge management is secondary. "
                "Database-heavy UX overwhelms note-taking users. Expensive for power users ($16-20/mo per person). "
                "Your knowledge is locked in Notion's proprietary format."
            )
        },
        {
            "name": "Readwise Reader",
            "strength": (
                "Excellent read-later app with highlights, annotations, and Kindle sync. "
                "$7.99/mo. Strong community. RSS reader built in. Spaced repetition for highlights."
            ),
            "gap": (
                "Read-later tool, not a knowledge base — you can't 'ask' your highlights questions. "
                "No AI synthesis or chat. No knowledge graph. No PDF workspace. "
                "Highlights are siloed from your other notes. "
                "Engram can import all Readwise content and add the AI layer on top."
            )
        },
        {
            "name": "Roam Research",
            "strength": (
                "Pioneered daily notes + bidirectional linking. Beloved by academics and writers. "
                "Powerful query language. $15/mo or $165/yr."
            ),
            "gap": (
                "Cult product with steep learning curve — most users quit within 2 weeks. "
                "No AI features natively. No automatic ingestion. "
                "Dated UX that hasn't meaningfully improved in 3 years. "
                "No mobile app worth using. Developer communication is notoriously poor. "
                "Niche audience; not expanding."
            )
        }
    ],

    "target_persona": {
        "age_range": "22-42",
        "income_level": "Middle to upper-middle income ($60K-$150K/yr). Comfortable paying $10-30/mo for tools.",
        "pain_points": (
            "Reads 15+ articles/papers per week across Pocket, RSS feeds, and Twitter/X saved posts. "
            "Forgets 85% of what they read within 72 hours (Ebbinghaus forgetting curve). "
            "Has 3,000+ Notion pages they never revisit. Has a 600+ article Pocket backlog they feel guilty about. "
            "Spent 2+ hours setting up an Obsidian vault that they abandoned after 3 weeks. "
            "Has asked ChatGPT to help them recall something from an article they 'saved somewhere.' "
            "Feels like they're learning constantly but retaining nothing. "
            "Would describe themselves as 'information hoarders' with a retrieval problem."
        ),
        "buying_triggers": (
            "Hits the 100-entry free tier limit after 3-4 weeks of genuine use. "
            "Successfully retrieves an insight from 6 months ago using Engram's semantic search — "
            "the 'aha moment' that proves the value. "
            "Receives a Weekly Digest that surfaces a connection they find genuinely surprising. "
            "Tool must demonstrably save 2+ hours/week on knowledge retrieval and synthesis. "
            "Social proof: sees a trusted peer posting about Engram on Twitter or Product Hunt."
        ),
        "psychographics": [
            "lifelong learner with a growth mindset",
            "productivity and PKM enthusiast (follows Tiago Forte, Ali Abdaal, etc.)",
            "tech-savvy but frustrated with tool complexity",
            "knowledge worker who values deep work and focus",
            "indie hacker or builder with side projects",
            "graduate student or academic researcher",
            "software engineer who reads widely about distributed systems, ML, product",
            "writer or content creator who needs to cite sources and synthesize ideas",
            "information-overwhelmed professional who reads on commutes and lunch breaks"
        ],
        "segments": {
            "segment_a_power_pkm": "Heavy Obsidian/Roam users burned by complexity. Want automation without losing depth. 25% of addressable market.",
            "segment_b_passive_hoarders": "Pocket/Instapaper users with 500+ unread items. Don't have a PKM system at all. 40% of TAM.",
            "segment_c_ai_curious": "ChatGPT power users who want AI to work on THEIR data, not generic training data. 20% of TAM.",
            "segment_d_researchers": "Grad students and academics who need to synthesize literature. 15% of TAM."
        }
    },

    "launch_channel": "product_hunt",
    "launch_channel_notes": (
        "Primary launch: Product Hunt on a Tuesday at 12:01 AM PST (historically highest traffic day). "
        "Goal: #1 Product of the Day. Strategy: 200+ beta users pre-committed to upvote on launch day. "
        "Launch post written by the founder in first-person, showing real screenshots and the personal story. "
        "Secondary channels (same week): Hacker News Show HN post, Reddit r/productivity + r/PKMS + r/ObsidianMD. "
        "Twitter/X build-in-public thread (founder has 4,200 followers). "
        "Email blast to 1,200 waitlist subscribers with 15% off annual plan for first 72 hours. "
        "Influencer outreach: 5 PKM YouTubers (Tiago Forte's team, Ali Abdaal's team, Nick Milo) sent early access. "
        "Expected: 500-800 Product Hunt upvotes, 200-400 new signups from launch day, "
        "5-15 media mentions in productivity newsletters (Superorganizers, Ness Labs, etc.)."
    ),

    "known_risks": [
        (
            "LLM API cost scaling: At 1,000 Pro users averaging 500 chat queries/month = 500,000 queries. "
            "At $0.0002/query with gpt-4o-mini, that's $100/month. Manageable. "
            "But if usage skews toward Power users with unlimited chat, costs could balloon 10x. "
            "Mitigation: Rate limiting, caching frequent queries, downgrading to cheaper models for short responses."
        ),
        (
            "Paywall bypass breakage: The content extraction pipeline uses a combination of Reader Mode, "
            "Jina AI's reader API, and custom scrapers. Major paywalled sites (NYT, WSJ, Medium) "
            "actively update anti-scraping measures. A major paywall update could break ingestion for "
            "20-40% of URLs users try to save. Mitigation: Manual paste fallback, Readwise import for highlights."
        ),
        (
            "AI hallucination in knowledge chat: The RAG pipeline grounds responses in user content, "
            "but GPT-4o-mini may still blend training knowledge with retrieved content. "
            "If a user cites Engram's answer in a research paper and it's wrong, "
            "trust collapses instantly for the researcher segment. "
            "Mitigation: Confidence scores on all answers, strict citation enforcement, 'I don't know' threshold."
        ),
        (
            "Data privacy and cloud storage concerns: Users are storing personal research notes, "
            "private annotations, journal entries, and sensitive professional documents. "
            "A data breach, subpoena, or investor-forced data policy change would be catastrophic. "
            "Privacy-cautious PKM users (especially Obsidian converts) are deeply skeptical of cloud storage. "
            "Mitigation: E2E encryption at rest (AES-256), zero-knowledge architecture in roadmap for Q2, "
            "explicit no-data-training policy, SOC 2 Type II on roadmap."
        ),
        (
            "Obsidian adds native AI auto-linking: Obsidian has 1M+ users and a thriving plugin ecosystem. "
            "If they ship a native Smart Connections feature with auto-ingestion, "
            "Engram's core differentiation collapses for the power PKM segment (25% of TAM). "
            "Mitigation: Focus on the 'no setup required' positioning vs. Obsidian's inherent complexity; "
            "move toward the passive hoarder segment (40% of TAM) where Obsidian will never play."
        ),
        (
            "Freemium conversion rate may be lower than expected: "
            "If the 100-entry free tier is too generous, users may stay free indefinitely. "
            "Beta data shows 12% conversion rate at 100 entries, but target is 18%. "
            "Mitigation: Add soft-paywalling earlier (graph visualization, weekly digest) to drive conversion; "
            "add social proof nudges ('1,200 users upgraded this month') in the UI."
        ),
        (
            "Single-developer bus factor: The entire product — backend (Python/Flask), "
            "frontend (Vue.js), AI pipeline, and infrastructure (Railway + Supabase) — "
            "is maintained by one person. A health issue, burnout, or distraction from a full-time job "
            "could stall development for weeks. "
            "Mitigation: Comprehensive documentation, automated CI/CD, infrastructure-as-code, "
            "considering bringing on a co-founder or part-time contractor by month 4."
        ),
        (
            "OpenAI API dependency and pricing risk: All AI features depend on OpenAI's API. "
            "A 2x price increase (which happened with GPT-4) would double COGS. "
            "An OpenAI outage would make Engram's core features unavailable. "
            "Mitigation: Designing the LLM abstraction layer to support fallback to Claude or Gemini; "
            "considering open-source models (Llama 3.1) for summarization to reduce cost."
        ),
        (
            "Market education burden: Most potential users don't know what 'PKM' or 'second brain' means. "
            "The 'aha moment' requires actual use — it's hard to convey in a 30-second demo. "
            "Conversion from Product Hunt visitors (who browse, not commit) may be low. "
            "Mitigation: 5-entry demo vault pre-populated with content, interactive tour, "
            "founder-led onboarding calls for first 100 Pro users."
        )
    ],

    "beta_traction": {
        "waitlist_signups": 1200,
        "active_beta_users": 340,
        "average_rating": "4.7/5 (80+ responses)",
        "nps_score": 62,
        "d7_retention": "38%",
        "avg_session_length_minutes": 14,
        "top_loved_features": ["Weekly Digest (78% open rate)", "Semantic search", "Knowledge graph visualization"],
        "top_complaints": ["Paywall bypass only works 60% of the time", "Mobile capture UX needs work", "Want offline mode"],
        "notable_quote": "'I found a connection between two notes I saved 8 months apart. I would never have found that manually.' — Beta user, software engineer, Seattle"
    },

    "total_agents": 150,
    "max_rounds": 20,
    "competitive_event_type": "feature_match",
    "crisis_event_type": "security_breach",
    "enable_twitter": True,
    "enable_reddit": True,
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def log(msg):
    print(f"  {msg}", flush=True)

def step(n, title):
    print(f"\n[Step {n}] {title}", flush=True)

def check(res, label):
    """Assert response is successful, print error and exit if not."""
    if not res.get("success"):
        error = res.get("error") or res.get("errors") or "unknown error"
        print(f"\n✗ FAILED at: {label}")
        print(f"  Error: {error}")
        sys.exit(1)

def poll_task(task_id, label, timeout_s=600, interval_s=4):
    """Poll /api/graph/task/<task_id> until completed or failed."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        res = requests.get(f"{BASE_URL}/api/graph/task/{task_id}").json()
        task = res.get("data") or {}
        status = task.get("status", "")
        pct = task.get("progress", 0)
        msg = task.get("message") or status or ""
        log(f"{label}: {pct}% — {msg}")
        if status == "completed":
            return task
        if status == "failed":
            print(f"\n✗ Task failed: {msg}")
            sys.exit(1)
        time.sleep(interval_s)
    print(f"\n✗ Task timed out after {timeout_s}s")
    sys.exit(1)

# ── Main flow ──────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Engram — Product Sentiment Simulation")
    print("=" * 60)

    # ── Step 1: Validate seed ──────────────────────────────────────
    step(1, "Validating seed template")
    res = requests.post(f"{BASE_URL}/api/sentiment/seed/validate", json=SEED).json()
    check(res, "seed/validate")
    if not res.get("valid"):
        print(f"  ✗ Seed invalid: {res.get('errors')}")
        sys.exit(1)
    log("✓ Seed template is valid")

    # ── Step 2: Preview → get markdown + simulation_requirement ───
    step(2, "Generating markdown from seed")
    res = requests.post(f"{BASE_URL}/api/sentiment/seed/preview", json=SEED).json()
    check(res, "seed/preview")
    markdown_text = res["markdown"]
    sim_req = res["simulation_requirement"]
    log(f"✓ Markdown: {len(markdown_text)} chars")
    log(f"✓ Simulation requirement: {len(sim_req)} chars")

    # ── Step 3: Upload markdown → generate ontology (synchronous) ─
    step(3, "Uploading product brief → generating ontology")
    file_bytes = markdown_text.encode("utf-8")
    files = {
        "files": (f"{SEED['product_name']}_brief.md", file_bytes, "text/markdown"),
    }
    data = {
        "simulation_requirement": sim_req,
        "project_name": SEED["product_name"],
    }
    res = requests.post(
        f"{BASE_URL}/api/graph/ontology/generate", files=files, data=data, timeout=300
    ).json()
    check(res, "graph/ontology/generate")
    project_id = res["data"]["project_id"]
    entity_count = len(res["data"].get("ontology", {}).get("entity_types", []))
    log(f"✓ project_id: {project_id}")
    log(f"✓ Ontology complete — {entity_count} entity types extracted")

    # ── Step 4: Build knowledge graph (async) ─────────────────────
    step(4, "Building knowledge graph in Zep")
    res = requests.post(f"{BASE_URL}/api/graph/build", json={"project_id": project_id}).json()
    check(res, "graph/build")
    build_task_id = res["data"]["task_id"]
    log(f"  Waiting for graph build task {build_task_id}...")
    task_result = poll_task(build_task_id, "Graph build")
    graph_id = task_result.get("result", {}).get("graph_id", "")
    log(f"✓ Graph ready — graph_id: {graph_id}")

    # ── Step 5: Create campaign ────────────────────────────────────
    step(5, "Creating sentiment campaign")
    payload = {
        "project_id": project_id,
        "graph_id": graph_id,
        "seed_data": SEED,
        "competitive_event_type": SEED["competitive_event_type"],
        "crisis_event_type": SEED["crisis_event_type"],
        "total_agents": SEED["total_agents"],
        "enable_twitter": SEED["enable_twitter"],
        "enable_reddit": SEED["enable_reddit"],
    }
    res = requests.post(f"{BASE_URL}/api/sentiment/campaign/create", json=payload).json()
    check(res, "campaign/create")
    campaign_id = res["campaign"]["campaign_id"]
    log(f"✓ campaign_id: {campaign_id}")

    # ── Step 6: Prepare campaign (agent + config generation) ───────
    step(6, "Preparing scenarios — generating 450 agents + 3 LLM configs")
    log("  (This takes a few minutes — generating profiles and simulation configs)")
    log("  [Full run: 150 agents × 20 rounds × 3 scenarios ≈ $4.50–6.50]")
    res = requests.post(
        f"{BASE_URL}/api/sentiment/campaign/{campaign_id}/prepare",
        timeout=600,
    ).json()
    check(res, "campaign/prepare")
    log(f"✓ Preparation complete — {len(res.get('progress', []))} steps done")

    # ── Step 7: Start simulation ───────────────────────────────────
    step(7, "Starting simulation — 3 sequential scenarios × 20 rounds each")
    res = requests.post(
        f"{BASE_URL}/api/sentiment/campaign/{campaign_id}/start",
        json={"platform": "parallel", "max_rounds": SEED["max_rounds"]},
    ).json()
    check(res, "campaign/start")
    log("✓ Simulation started!")

    # ── Done ───────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  SIMULATION RUNNING")
    print("=" * 60)
    print(f"\n  Campaign ID : {campaign_id}")
    print(f"  Agents      : {SEED['total_agents']}")
    print(f"  Rounds      : {SEED['max_rounds']} per scenario")
    print(f"  Scenarios   : A (baseline) · B (feature_match) · C (security_breach)")
    print(f"\n  Track progress in the UI:")
    print(f"  → http://localhost:5173/sentiment")
    print(f"\n  Or poll status via API:")
    print(f"  → GET {BASE_URL}/api/sentiment/campaign/{campaign_id}")
    print(f"\n  When done, get results:")
    print(f"  → GET {BASE_URL}/api/sentiment/campaign/{campaign_id}/sentiment")
    print(f"  → GET {BASE_URL}/api/sentiment/campaign/{campaign_id}/compare")
    print()

    # Save campaign ID to file for easy reference
    with open("/tmp/engram_campaign_id.txt", "w") as f:
        f.write(campaign_id)
    print(f"  (Campaign ID saved to /tmp/engram_campaign_id.txt)")


if __name__ == "__main__":
    main()
