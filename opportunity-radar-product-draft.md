# Opportunity Radar — Product Draft

**An AI opportunity-discovery and targeting engine for an individual consultant selling their own services, worldwide, in English, priced in rupees.**

> Don't wait for work to be posted. Find evidence that someone needs your skills.

---

## 1. Positioning

Boards and marketplaces show demand only after it is posted, when it is crowded. Most consulting demand is never posted at all. Opportunity Radar collects public evidence that a company is developing a need, scores the fit, explains why, names the likely buyer, and recommends the next action.

**Not** "where are the jobs?" **but** "which companies are about to need someone like me, and haven't asked yet?"

**The user is an individual consultant.** One person selling their own skills: contracts, hourly work, project engagements, and, when a full-time role is the better deal, a job. The product never positions the user as an agency or a team, and never sells leads to intermediaries. Everything is scored as "can I, personally, win and deliver this?"

| User type | Wants |
|---|---|
| Senior engineer / architect consulting independently | Funded clients with a real technology problem; a full-time role only if it beats consulting |
| Early-career or lower-cost-market consultant | Real, paying remote work from ₹400–₹1,700/h ($5–$20/h): support, QA, data, junior dev |
| AI practitioner (ML/LLM engineer, evaluator, annotator) | AI contracts anywhere, including markets Western boards do not index |

**Three fixed decisions.**

- **English only.** The product, the packets, and the opportunities are in English. Only opportunities that can be won and delivered in English are indexed; local-language roles are out of scope, not translated. This removes multilingual extraction entirely and limits China, Japan and Southern Europe to their English-reachable segments (section 11).
- **Indian rupee is the base currency.** Every rate, salary, budget and value range is stored in its original currency and shown in ₹ first, with the original beside it, at a daily reference rate (RBI reference rate or an equivalent feed). The user's floor and target are set in ₹/hour. Conversions are display-only; the original figure stays as evidence.
- **Global by default.** Any country, any direction, any rate. "Remote" is resolved to *remote from where* (time zone, work permit, region lock). A verified ₹850/h ($10/h) job ranks highly for a user whose floor is ₹700/h. Sources are configured per region; US boards are one region among many.

Examples use a Java / Python / ETL profile because that is the first user; nothing is specific to that stack or to senior work. Dollar figures below are shown with their ₹ equivalent at roughly ₹85/$.

---

## 2. Three modes, one pipeline

| Mode | Finds | Sources | Role |
|---|---|---|---|
| **Career Hunter** | English-language full-time roles, any level, any rate | Global + regional boards, career pages | Secondary; daily use, outcome data, and a benchmark for what consulting must beat |
| **Contract Hunter** | Freelance and hourly work from ₹400/h ($5/h) up | Global + regional marketplaces, Telegram/WhatsApp/Facebook groups, open web | Table stakes; where most of the world's remote demand lives |
| **Client Hunter** | Companies likely to need IT work with nothing posted | News, funding, hiring patterns, tech-stack detection | **The differentiator** |

```text
COLLECT SIGNALS -> COMPANY DNA -> DETECT NEEDS -> SCORE + EXPLAIN -> PACKET -> RADAR -> USER ACTS -> LEARN
```

---

## 3. Data model

**User capability graph.** Skills with confidence and relationships, seeded from a CV, refined by outcomes. Plus seniority, domains, languages, and preferences (location, remote, rate floor, engagement length).

```text
Java (0.95) ── Spring Boot (0.9), PostgreSQL (0.85), Kafka (0.7), Microservices (0.9)
ETL  (0.85) ── Python (0.9), SQL (0.9), Data pipelines (0.8), Migration (0.75)
```

**Company DNA.** A persistent, dated, sourced profile per company: industry, headcount and growth, funding, technology (detected from site, DNS, job posts, GitHub, model releases), engineering maturity, likely IT spend, hiring, current triggers, potential problems, likely buyer, history. Every row keeps its source and observation date.

---

## 4. Signals and need detection

A signal is a dated, sourced observation. Every signal is asked one question: **what IT work could this create?**

| Class | Examples |
|---|---|
| Direct | "looking for a developer", "need help with…", "migrate our…", "legacy application", "custom CRM" |
| Trigger events | Funding → hiring → product expansion → infrastructure pressure. Also: acquisition, new CTO, new market, new enterprise customer, headcount growth, cloud/ERP migration, website rebuild, outsourcing |
| Hiring patterns | Senior Java + Data + DevOps posted together = platform expansion, not replacement hires. A company's *first-ever* technical hire is the strongest single signal |
| AI track | New AI-flavoured titles (LLM, MLOps, eval, RLHF, AI trainer); non-AI firms announcing AI strategies or naming model vendors in vacancies; labs and data vendors hiring remote annotators and evaluators at ₹850–₹5,100/h ($10–$60/h); GPU or AI-investor funding predicts hiring 2–4 months out |
| Structural shortage | Whole markets that cannot staff tech work: shrinking workforce (Japan, Korea, Germany) or low skills base with public money to fix it (Southern Europe). Signals are subsidies, eased visas, first English-language hiring, offshore contracts |

**Rules.** No signal, no need: the model never invents a problem. Each need carries its supporting signals. Signals expire.

---

## 5. Scoring

0–100 from weighted dimensions; weights vary by mode, dimensions do not. **Every score ships with its reasons.**

| Dimension | Measures |
|---|---|
| Technical match | Need vs capability graph, weighted by confidence |
| Seniority match | Both directions; over-qualified is flagged, employers skip those |
| Domain match | Industry and problem-type familiarity |
| Remote eligibility | Remote *from where*: time zone, permit, region lock. Hard filter if the user says so |
| Language | Hard filter: English-deliverable only. Anything requiring another language is dropped before scoring |
| Rate match | Against the user's ₹/h floor and target, converted at the daily reference rate; original currency kept |
| Recency | Age of the strongest signal |
| Competition | Estimated: niche stack, seniority bar, posting age, whether the need has reached a marketplace at all |
| Client quality / payment risk | Funding, stability, verified payment history, scam indicators. Dominant at the low-rate end |
| Evidence strength | Count and directness of independent signals |

---

## 6. The Opportunity Packet

The core UX. Answers in order: what, why we believe it, what to sell, to whom, why you, what next.

```text
ABC Logistics                         Backend modernization      Confidence 89/100
Evidence:  3 backend hires (careers, 12d) · portal on 2016 stack (scan, 3d) · Series A (press, 4mo)
           headcount +40%/12mo (inferred) · Java in vacancy (post, 12d)
Sell:      Backend/API modernization + data integration · 3–8 weeks · ₹8.5L–₹25.5L ($10k–$30k)
Buyer:     CTO (named only if publicly listed in role)
Why you:   Java + architecture + ETL, 2 prior logistics engagements
Action:    Contact CTO. Lead with the portal, not the hiring.
```

Rationale must be built from the evidence lines ("hiring three backend engineers against a 2016 portal"), never generic. Buyer mapping is problem → role → person-only-if-public: modernization → CTO; data → Head of Data; automation → COO; website → Founder/Marketing; no engineering leader → Founder/COO (and that absence is a signal). In relationship-driven markets the action is "get an introduction", not "email the owner". The packet is written to help one consultant pitch, never a team.

---

## 7. Delivery and action

**Radar.** Daily or weekly, pushed, not searched.

```text
🔥 Immediate   Australian SaaS · Java modernization · 96 · remote worldwide, recent funding
               UAE logistics · data integration · 91 · nothing posted, CTO identified
               Kenyan fintech · Python/ETL contract · 88 · posted 2d, EAT hours
               German agency · QA, ₹1,020/h ($12/h) · 85 · verified payer, 20h/wk
               Shenzhen AI startup · LLM eval, ₹3,400/h ($40/h) · 84 · remote APAC, English OK
               Tokyo fintech · backend contract, ¥9,000/h (₹5,100) · 83 · English-OK, remote JST
               Barcelona SaaS · data integration, €60/h (₹5,400) · 81 · English hub, EU remote
🧠 Emerging    4 companies with early signals (watch)
💰 Consulting  2 companies with probable pain, nothing posted
📉 Dropped     1 filled, 2 signals expired
```

**Acting.** Discover → classify → score → draft tailored outreach → **user reviews** → user sends. No mass auto-apply. Drafts must quote evidence. Compliant APIs or human-in-the-loop where platforms forbid automation.

---

## 8. Learning and moat

Outcomes per action (applied/screened/interviewed/offered/accepted; contacted/replied/call/proposal/won/lost; user declined) feed the capability graph and scoring weights. Cold start: explicit preferences plus "relevant / not relevant" feedback on every packet from week one. With a cohort, pooled outcomes (opt-in, anonymised) tell the system which signal classes are real.

The moat is the dataset `skills → companies → signals → problems → opportunities → actions → outcomes`: which signals predict real work, for which kind of person, company, service and price. Features are copyable; that mapping is not, and it only exists if users act and report through the product.

---

## 9. Not building

Resume builder · cover-letter generator · LinkedIn or Upwork scraper · job aggregator · keyword matcher · mass-apply bot · generic CRM · generic cold-email tool. If a request looks like one of these, the answer is a better packet.

---

## 10. Risks

| Risk | Mitigation |
|---|---|
| Data sourcing and terms of service | Official APIs, licensed data, open web; per-source allow list; never scrape behind login |
| Invented needs | Evidence-only rule; sources and dates on every packet; single weak signals stay in Emerging |
| Stale signals | Expiry; Dropped section |
| Personal data (GDPR, PIPL) | Store role not person; name only if publicly listed in role; no private enrichment |
| Outreach spam | No sending without review; evidence-led drafts; per-user rate limit |
| Scams and non-payment at the low-rate end | Payment-risk score; flag upfront fees, unpaid "tests", unverified payers; escrow marketplaces first |
| Uneven regional coverage | Per-region source lists; measure coverage per region; user-forwarded group posts where ingestion is not allowed |
| Currency drift | Store original currency and date; convert on display at the daily reference rate; never re-score on FX moves alone |
| Payment into India | Flag clients that cannot pay via Wise, Payoneer, PayPal or SWIFT; note FIRC / purpose-code needs on the packet |
| Non-English listings | Dropped at ingestion, not translated; English-deliverable is a hard filter |
| Fake "remote" | Resolve remote-from-where; unresolved restriction is a question, not "worldwide" |
| China access | No logged-in or real-name-account scraping; public pages, WeChat articles, funding DBs, overseas channels only |

---

## 11. Market playbooks

| | **China AI** | **Japan** | **Southern Europe** (ES, IT, PT, GR) |
|---|---|---|---|
| Why | Second-largest AI labour market, invisible from Western boards | Shrinking workforce; METI projects a large IT shortfall by 2030; COBOL/old Java estate; "2025 digital cliff" | Lowest EU digital-skills scores; SME-dominated economy on spreadsheets; EU recovery money (PNRR, Kit Digital, PRR) now paying SMEs to digitise |
| Demand | LLM, CV, inference/CUDA, eval, annotation, AI product | Legacy modernisation, cloud, ERP, factory/logistics automation, bridge engineers, AI integration | ERP/accounting migration, e-commerce integration, warehouse automation, CRM, e-invoicing compliance, AI for customer service |
| English-reachable segment (all that is indexed) | Overseas entities (SG/HK/US/EU) of Chinese labs; remote English-domain annotation, evaluation, red-teaming at ₹850–₹3,400/h ($10–$40/h); startup contracts paid via Payoneer/Wise | English-OK roles and contracts at global-facing tech (Mercari, Rakuten, PayPay, LINE Yahoo, Woven, PFN); offshore development subcontracted to India, which is a direct fit for an Indian consultant | English hub roles and contracts (Barcelona, Madrid, Lisbon, Milan); nearshore and offshore work for Northern-EU-owned firms; EU remote where no local language is needed |
| Out of scope (non-English) | Onsite mainland roles; all mainstream Chinese boards | Japanese-language SIer and manufacturer roles | Local-language corporate, integrator and SME work; the Kit Digital / PNRR SME segment, which needs the local language and a local intermediary |
| Sources | English career pages of Chinese labs and their overseas entities; lab and data-vendor contractor portals; Hugging Face / ModelScope / GitHub attributions; IT桔子 and 36氪 only as funding data | Japan Dev, TokyoDev, Daijob, GaijinPot, Wantedly and Green English listings; English career pages; offshore-vendor and bridge-SE postings; METI/IPA reports as market signal | LinkedIn, Indeed, Landing.jobs, Manfred English listings; Malt and EURES; English career pages of hub startups; TED for English-language public tenders |
| Strongest signal | Opening a Singapore entity, or algorithm + data + inference roles posted together | A traditional firm's first English-language or bridge-SE posting, or a new offshore programme | A hub startup's funding round, or a Northern-EU firm opening a Southern-EU engineering site |
| Buyer path | Introduction, rarely cold email | Introduction or the offshore vendor's account lead | Founder or CTO directly; English hubs behave like London or Berlin |
| Phase 1 segment | English-domain annotation/eval + overseas entities; target 10 verified opportunities/week | English-OK contracts + offshore-to-India programmes; target 10/week | Hub startup contracts; target 10/week |

Highest-yield English-first regions for an India-based consultant, before any of the above: US, UK, Gulf (English-OK, overlapping hours), Singapore and Australia. Next: Germany and Netherlands (English engineering hubs), South Korea and Taiwan (shortage, English segments only).

---

## 12. MVP and metrics

**Status (2026-10-09):** Phase 1 implementation started in this repo; see `CLAUDE.md` for commands and `python radar.py run` for the pipeline. The **Region gaps** page (`/region`) ranks countries by thin local IT supply, shallow in-house engineering and budgets near the profile floor, computed from the stored postings and signals, as the evidence-led counterpart to the hand-picked regions in §11.

**Phase 1, validate the packet.** One user, Client Hunter only, hand-curated sources from two or three regions, weekly radar by email, packets checked by hand before sending. Automation is not the success criterion; packet correctness is.
**Phase 2, add the loop.** Outcome capture, relevance feedback, Career and Contract modes (hourly from ₹400/h with payment-risk and pay-into-India checks).
**Phase 3, learn.** Per-user weight tuning, competition estimation, multi-user, pooled signals.

| Metric | Phase 1 target |
|---|---|
| Packet precision (user marks "real need") | ≥ 60% |
| Evidence accuracy (lines that check out) | ≥ 95% |
| Reply rate per outreach | Above the user's current cold rate |
| Time to first conversation | ≤ 30 days |
| Won engagements traceable to a packet | 1 |
| Regional coverage (hand-sampled listings found) | ≥ 70% per Phase 1 region |

---

## 13. Open questions

1. Which signal sources are legally and practically available per region, at what cost?
2. How is "potential value" estimated, and does showing a ₹ range help or anchor badly?
3. First customer: the author, or a small cohort of Indian consultants? Which regions follow from that?
4. Buyer naming: role-only by default is proposed; needs a decision.
5. Pricing for the product itself: subscription cannot work for a ₹850/h user; tiered by the user's ₹ floor, or success-based?
6. Group sources (Telegram, WhatsApp, Facebook): what can be ingested, and is user-forwarding enough?
7. Japan: extend into visa and relocation for the English-OK roles, where most foreign candidates drop out?
8. Warm-path routing and proof artefacts (an evidence-based teardown the buyer wants to read) are the two features most likely to lift reply rate; build before or after Phase 1?
9. Does Career Hunter stay in at all, or is a full-time role just a Contract Hunter result with a long duration and a different rate shape?

**Decided:** English only. ₹ base currency with originals shown. The user is an individual consultant; no agency positioning, no selling leads to intermediaries, no local-language segments.
