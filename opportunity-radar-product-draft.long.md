# Opportunity Radar — Product Draft

**An AI opportunity-discovery and targeting engine for technical professionals and independent consultants.**

> Don't wait for work to be posted. Find evidence that someone needs your skills.

---

## 1. Problem and positioning

Job boards and freelance marketplaces only show demand *after* it has been written up and posted. By then it is public, crowded, and often already half-filled. Most consulting demand never gets posted at all: a company hits a problem, someone in the founder's network gets a call, and the work is gone.

Opportunity Radar inverts this. Instead of matching keywords against listings, it continuously collects public evidence that a company is developing a need, scores how well that need fits the user, explains the reasoning, identifies the likely buyer, and recommends a next action.

**The question is not** "Where are the jobs?"
**The question is** "Which companies are about to need someone like me, but haven't asked yet?"

### Who it is for

| Persona | Wants | Today uses |
|---|---|---|
| Senior engineer / architect | High-value roles that fit seniority, stack, remote and salary | LinkedIn, job boards, recruiters |
| Independent consultant / small shop | Clients with a real, fundable technology problem | Upwork, referrals, cold outreach |
| Both (common) | One place to see every kind of opportunity, ranked | Several tools, none proactive |
| Remote worker in a lower-cost market | Real, paying remote work at $5–$20/hour: support, QA, data entry, junior dev, ops | Upwork, Telegram and WhatsApp groups, Facebook groups, word of mouth |
| AI practitioner (ML engineer, LLM engineer, data scientist, AI trainer / annotator) | AI roles and contracts worldwide, including the Chinese AI market, which is large and almost invisible from Western boards | LinkedIn, company pages, Chinese boards if they can read them |

The examples in this document use a Java / Python / backend / ETL profile because that is the first user. Nothing in the design is specific to that stack, and nothing is specific to senior or high-value work.

### Global by default

The product covers every country and every rate band, not the US and not only senior roles. Concretely:

- **Any country, any direction.** A user in Lagos, Cairo, Karachi or Nairobi sees remote work from anywhere in the world, and local work in their own market. A user in London sees the same engine applied to London.
- **Remote is a first-class filter, not a tag.** "Remote" is resolved to *remote from where*: worldwide, specific time zones, specific countries, or region-locked (an "EU remote" role is not remote for someone in Ghana). A role that is remote but requires a US work permit is scored as not available.
- **Real $10/hour jobs count.** A genuine $10/hour QA or support contract from a vetted client is a good opportunity for the right user and must rank highly for them. The scoring model (section 7) matches rate to the user's own floor, not to a global notion of "high value".
- **Sources follow the user.** Each market has its own boards, Telegram and WhatsApp channels, Facebook groups, local marketplaces and classified sites. Source coverage is configured per region, and the US-centric boards are one region among many.
- **AI is a vertical that cuts across every region.** AI roles are the fastest-growing demand category and the one with the most unusual sources. Section 6.4 covers the AI track. Sections 17 to 19 cover three markets with different shapes: China (a boom market Western tools do not index), Japan (a shrinking workforce), and Southern Europe (a large SME base that digitised late and is now being paid to catch up).

---

## 2. Three modes

| Mode | Finds | Primary sources | Role in the product |
|---|---|---|---|
| **Career Hunter** | Full-time roles matching skills, seniority, location, remote preference, salary, at any level and any rate | Global and regional job boards, company career pages, remote-only boards | Table stakes. Keeps the user coming back daily and produces outcome data. |
| **Contract Hunter** | Freelance, contract and hourly engagements from $5/hour upward | Global marketplaces, regional marketplaces, Telegram / WhatsApp / Facebook job groups, the open web | Table stakes, same reasons. Hourly work is where most of the world's remote demand lives. |
| **Client Hunter** | Companies likely to need IT work that have published no job or project | News, funding, hiring patterns, tech-stack detection, open web | **The differentiator.** Nothing else does this for an individual. |

The three modes share one pipeline, one scoring model, and one output format. They differ only in signal sources and scoring weights.

---

## 3. How it works

```text
COLLECT SIGNALS ──> BUILD COMPANY DNA ──> DETECT NEEDS ──> SCORE + EXPLAIN
                                                                │
   LEARN FROM OUTCOMES <── USER ACTS <── DELIVER RADAR <── OPPORTUNITY PACKET
```

Each stage is covered below. The user's side of the graph is the capability model (section 4); the company's side is Company DNA (section 5). Needs (section 6) are the edges between them, and scoring (section 7) ranks the edges.

---

## 4. User capability model

Skills are not tags. Each user has a capability graph with **confidence** and **relationships**, seeded from a CV or profile and refined by outcomes.

```text
Java (0.95)
 ├── Spring Boot (0.9)
 ├── PostgreSQL (0.85)
 ├── Kafka (0.7)
 ├── Microservices (0.9)
 └── Backend architecture (0.9)

ETL (0.85)
 ├── Python (0.9)
 ├── SQL (0.9)
 ├── Data pipelines (0.8)
 └── Migration (0.75)
```

Alongside skills the model holds seniority, years of experience, domains worked in, preferences (location, remote, rate, engagement length), and past outcomes. Confidence rises when a skill features in a won engagement or accepted role and decays when it is never used.

---

## 5. Company DNA

A persistent, evolving profile per company. It is built from publicly observable signals and is the substrate every other feature reads from.

```text
Company                 ABC Logistics
Industry                B2B logistics
Employees               75, growing fast
Funding                 Series A, 4 months ago
Technology              WordPress, WooCommerce, Cloudflare, dated frontend
Engineering maturity    Low (no engineering leadership visible)
Likely IT spend         Low-to-medium, rising
Hiring                  Operations staff, 1 generalist developer
Current triggers        New warehouse, geographic expansion
Potential problems      Manual order processing, no customer portal, no data integration
Likely buyer            Founder / COO
Historical opportunities (none yet)
```

**Technology archaeology** is the sub-process that fills the technology rows: detect the stack from the public website, job postings, DNS and hosting, open-source activity, and vacancies that name technologies. Stack age and gaps are themselves signals (an old frontend plus rapid growth suggests a rebuild is coming).

Every row keeps its source and the date it was observed, so the profile can show what changed and when.

---

## 6. Signals and need detection

A signal is a dated, sourced observation about a company. The system turns signals into **needs** by asking one question of every signal:

> **What IT work could this create?**

### 6.1 Direct signals (someone wrote down the need)

Phrases found on the open web, forums, social posts, and company pages:

- "looking for a developer", "need help with…"
- "migrate our…", "automate…", "integrate…"
- "legacy application", "custom CRM", "database problems"

### 6.2 Trigger events (something changed)

```text
Funding ──> Hiring ──> Product expansion ──> Infrastructure pressure ──> Engineering work
```

Other triggers: acquisition or merger, new CTO or engineering leader, new product or market, new enterprise customer, rapid headcount growth, cloud migration, ERP change, legacy modernization, major website rebuild, outsourcing indicators.

**Structural shortage** is a trigger class of its own. Some markets cannot staff their technology work domestically because the working-age population is shrinking: Japan most sharply, then South Korea, Germany, Italy and Taiwan. There, the signal is not one company's event but the whole market's: government digitisation subsidies, relaxed skilled-worker visas, companies opening English-language hiring for the first time, and offshore development contracts. Section 18 covers Japan as the sharpest case. Southern Europe (section 19) is the related case: not a shortage of people but a shortage of *skills*, with EU recovery money paying SMEs to close the gap.

### 6.3 Hiring-pattern inference (the shape of hiring tells a story)

A company simultaneously hiring a Senior Java Engineer, a Data Engineer, and a DevOps Engineer is probably not making three replacement hires. The inference is a backend or platform expansion, and the derived need is **Java/backend modernization or platform engineering** that a consultant could deliver before, or instead of, those hires landing.

This turns job listings from things to apply for into business-intelligence signals about the company behind them.

### 6.4 The AI track

AI demand has its own signals, and most of them are invisible to a keyword matcher looking for "machine learning engineer".

- **Role signals.** LLM engineer, prompt engineer, AI product engineer, MLOps, evaluation engineer, RLHF / data annotation, AI trainer, model red-teamer. The titles change every quarter, so matching is on the described work, not the title.
- **Adoption signals.** A non-AI company announcing an "AI strategy", hiring its first ML engineer, posting about copilots or chatbots, or listing OpenAI / Anthropic / open-weight model names in a vacancy. Each is a Client Hunter need: integration, evaluation, data pipelines, fine-tuning, guardrails.
- **Lab and vendor signals.** Model labs and their data vendors hire remote annotators, domain experts and evaluators at scale, often at hourly rates from $10 to $60 depending on domain. These are the most accessible global AI jobs and the ones most likely to be hidden inside vendor portals rather than job boards.
- **Compute and funding signals.** GPU procurement, a cloud credits announcement, or a round led by an AI-focused investor predicts hiring 2 to 4 months out.

### 6.5 Rules for need detection

- A need must cite at least one concrete signal. No signal, no need. The model never invents a problem a company "probably has".
- Each need carries the signals that support it, so the packet (section 8) can show evidence rather than assertions.
- Signals expire. A funding round from three years ago is context, not a trigger.

---

## 7. Scoring and explanation

Every opportunity gets a 0–100 score from weighted dimensions. Weights differ by mode; the dimensions do not.

| Dimension | Measures |
|---|---|
| Technical match | Overlap between the need and the capability graph, weighted by confidence |
| Seniority match | Required level vs the user's level, in both directions |
| Domain match | Industry and problem-type familiarity |
| Location / remote eligibility | Not just "remote" but remote *from where*: time zone overlap, work-permit and country restrictions, region locks. Hard filter where the user says so |
| Rate match | Fit against the user's own floor and target, in the user's currency, with cost-of-living context. $10/hour is a strong match for a user whose floor is $8 and a non-match for one whose floor is $60. Over-qualified is also flagged, since employers skip those applicants |
| Recency | How fresh the strongest signal is |
| Competition | How crowded the opportunity is likely to be (see below) |
| Client quality and payment risk | Funding, growth, stability, verified payment history on marketplaces, scam indicators (see section 13). Matters most at the low-rate end, where fraud is common |
| Evidence strength | How many independent signals support the need, and how direct they are |

Example:

```text
Technical match     94
Seniority match     98
Location match     100
Competition         LOW
Evidence strength   HIGH (5 signals, 2 direct)
Overall             93 / 100
```

**Competition** is estimated, not measured. Inputs: niche stack, seniority bar, posting age, remote or not, whether the role appears to have been open a long time, and for client opportunities whether the need has reached a marketplace at all. The most valuable client opportunities are the ones that have **not yet entered a competitive marketplace**.

**Every score must come with a reason.** A score the user cannot interrogate is a score the user will not trust, and distrust kills a recommendation product faster than a wrong recommendation does.

---

## 8. The Opportunity Packet

The packet is the core user experience. Every opportunity above a threshold is presented as a compact research brief that answers, in order: what is the opportunity, why do we believe it, what would you sell, to whom, why you, and what next.

```text
ABC Logistics

Opportunity:        Backend modernization
Confidence:         89 / 100

Evidence:
  - Hiring 3 backend engineers            (careers page, 12 days ago)
  - Customer portal on a 2016-era stack   (site scan, 3 days ago)
  - Series A announced                    (press, 4 months ago)
  - Headcount +40% in 12 months           (LinkedIn, inferred)
  - Java named in a vacancy               (job post, 12 days ago)

What you can sell:  Backend/API modernization + data integration
Possible project:   3–8 week engagement
Potential value:    $10k–$30k

Likely buyer:       CTO (named where publicly listed)

Why you:            Java + backend architecture + ETL, 2 prior logistics engagements

Recommended action: Contact the CTO. Lead with the portal, not the hiring.
```

### 8.1 "What can I sell them?"

The packet does not stop at naming a company. It maps the detected problem to a concrete service, a plausible engagement shape, and a value range, and the rationale must be built from the evidence lines above it. "This company could use a modern backend" is not a rationale. "They are hiring three backend engineers against a 2016 portal" is.

### 8.2 Buyer detection

Problems map to roles; roles map to people only where that person is publicly listed in that role.

```text
Backend modernization   -> CTO / VP Engineering
Data integration        -> CTO / Head of Data
Internal automation     -> COO / Head of Operations
Website modernization   -> Founder / Marketing lead
Legacy Java system      -> CTO / Engineering Director
No engineering leader   -> Founder / COO (and that absence is itself a signal)
```

---

## 9. Delivery

### 9.1 The Radar

The product is proactive. The user does not search; the system delivers a daily or weekly radar.

```text
OPPORTUNITY RADAR  ·  week of 6 Oct

🔥 4 Immediate opportunities
  1. Australian SaaS      Java modernization       Match 96   Remote worldwide, recent funding
  2. UAE logistics        Data integration         Match 91   No public project, CTO identified
  3. Kenyan fintech       Python/ETL contract      Match 88   Posted 2 days ago, EAT time zone
  4. German agency        QA tester, $12/hour      Match 85   Remote, verified payer, 20 hrs/week
  5. Shenzhen AI startup  LLM eval engineer        Match 84   Remote (APAC hours), English OK, Series B via IT桔子
  6. Osaka manufacturer   Legacy Java → cloud      Match 83   English-OK, visa sponsored, DX subsidy approved
  7. Valencia distributor  ERP + warehouse integr.  Match 81   Kit Digital funded, no IT staff, Spanish needed

🧠 Emerging
  4 companies showing early demand signals (watch, don't act yet)

💰 Consulting
  2 companies with probable technology pain and no posted project

📉 Dropped since last week
  1 opportunity filled, 2 signals expired
```

### 9.2 Acting on an opportunity

Mass autonomous application is explicitly **not** the product. The user stays in the loop.

```text
Discover -> Classify -> Score -> Draft tailored application or outreach -> User reviews -> User sends
```

Where a platform prohibits scraping or automation, use its API or human-in-the-loop browser assistance. Outreach drafts are evidence-led and specific; the system should make it hard to send a generic message.

---

## 10. Learning from outcomes

Every action gets an outcome, and outcomes feed back into the capability model and the scoring weights.

| Mode | Outcomes recorded |
|---|---|
| Career | Applied, screened, interviewed, offered, accepted, rejected, user declined |
| Contract / Client | Contacted, replied, call held, proposal sent, won, lost, user declined |

Example of what the system learns for one user:

```text
Accepted / won:   Java + architecture, senior, remote, backend modernization, ETL, internal tools
Rejected / lost:  junior or mid roles, frontend-only, onsite, WordPress, SEO, projects below the user's floor
```

**Cold start.** Before any outcomes exist, scoring runs on explicit preferences and the capability graph alone. The first weeks of radar should ask for cheap feedback ("relevant / not relevant" on each packet) so learning starts before the first real outcome arrives.

---

## 11. The moat

Feature by feature, everything here can be copied. The dataset cannot.

```text
Skills -> Companies -> Signals -> Problems -> Opportunities -> Actions -> Outcomes
```

Over time the system learns **which signals predict real opportunities, for which kind of person, at which kind of company, for which service, at which price**. That mapping only exists if users act through the product and report what happened, which is why the delivery loop (section 9) and the outcome capture (section 10) are not optional features; they are how the moat is built.

---

## 12. What not to build

These are easy to copy, poorly differentiated, and would pull the product toward volume instead of precision:

- Resume builder, cover-letter generator
- LinkedIn scraper, generic Upwork scraper, job aggregator
- One-click mass-apply bot
- Keyword job matcher
- Generic CRM, generic cold-email generator

If a feature request looks like one of these, the answer is to produce a better packet, not a new tool.

---

## 13. Risks and constraints

| Risk | Why it matters | Mitigation |
|---|---|---|
| **Data sourcing and terms of service** | Several of the best signal sources forbid scraping | Prefer official APIs, licensed data, and the open web; keep a per-source allow list; never log in to scrape |
| **Invented needs** | A plausible-sounding packet with no real evidence destroys trust in every other packet | Evidence-only rule (6.4); packet shows sources and dates; needs with one weak signal stay in "Emerging" |
| **Stale signals** | A need that was real six months ago reads as spam today | Signal expiry; "dropped" section in the radar |
| **Personal data** | Naming decision makers touches GDPR and similar regimes | Store role, not person, by default; show a name only when publicly listed in that role; no enrichment from private sources |
| **Outreach quality** | A tool that helps people spam CTOs gets its users blocked | No sending without review; drafts must quote evidence; rate-limit per user |
| **Cold start** | Learning needs outcomes that do not exist on day one | Explicit preferences plus lightweight relevance feedback (section 10) |
| **Scams and non-payment** | Low-rate remote work is full of fake clients, "pay to apply" schemes, and unpaid trials, especially in groups and classifieds | Payment-risk score per client; flag unverified payers, upfront-fee requests, free-work "tests"; prefer escrow-backed marketplaces for first engagements |
| **Uneven source coverage** | Arab, African and South Asian markets are under-served by the big boards; the real listings sit in Telegram, WhatsApp and Facebook groups | Per-region source lists; group ingestion only where terms allow or via user-forwarded messages; measure coverage per region, not globally |
| **Language** | Listings and signals in Arabic, French, Portuguese, Swahili and others | Multilingual extraction from day one; score in the user's language, keep the original text as evidence |
| **Fake "remote"** | Many "remote" listings are country-locked or need a local work permit | Resolve remote-from-where explicitly; treat an unresolved restriction as a question, not as "worldwide" |
| **China access and law** | Chinese boards need a mainland phone number and real-name registration, block foreign IPs, and scraping them breaches PIPL and the platforms' terms | No scraping of logged-in Chinese platforms; use public company pages, WeChat public accounts, funding databases, overseas-hiring channels and user-forwarded posts (section 17) |

---

## 14. MVP

The differentiator is Client Hunter, so the MVP should test that and nothing else.

**Phase 1 (validate the packet).** One user profile, Client Hunter only, a hand-curated set of signal sources (funding news, careers pages, tech-stack detection) drawn from several regions, for example Gulf, East Africa, Southern Europe, Chinese AI and Japan, so regional source gaps show up immediately. Weekly radar as an email, packets reviewed by hand before sending. Success is whether the packets are right, not whether the pipeline is automated.

**Phase 2 (add the loop).** Outcome capture, relevance feedback, Career and Contract modes on the same pipeline so daily use produces data. Contract mode launches with hourly work from $5/hour upward and the payment-risk score, because that is the volume market and where trust is won or lost.

**Phase 3 (learn).** Per-user weight tuning from outcomes, competition estimation, multi-user.

---

## 15. Success metrics

| Metric | Definition | Phase 1 target |
|---|---|---|
| Packet precision | Share of delivered packets the user marks "real need" | ≥ 60% |
| Evidence accuracy | Share of evidence lines that check out when the user verifies them | ≥ 95% |
| Reply rate | Replies per outreach sent from a packet | Better than the user's current cold-outreach rate |
| Time to first conversation | Days from first radar to first call booked | ≤ 30 days |
| Won engagements | Engagements traceable to a packet | 1 |
| Regional coverage | Share of a region's known listings (sampled by hand) that the system also found | ≥ 70% in each Phase 1 region |

Career mode adds interview rate per application and offer rate per interview.

---

## 16. Open questions

1. Which signal sources are legally and practically available for Phase 1, and at what cost?
2. How is "potential value" estimated, and does showing a dollar range help or anchor badly?
3. Is the first customer the author (dogfooding) or a small cohort of consultants? That changes Phase 1 scope.
4. Where does the line sit between "identify the likely buyer role" and "name a person"? Section 13 proposes a default; it needs a decision.
5. Pricing: per-seat subscription, or a success-based model that aligns with the outcome data the moat depends on? A user earning $10/hour cannot pay $50/month; pricing must be regional or success-based for that segment.
6. Which Telegram, WhatsApp and Facebook sources can be ingested legitimately, and is user-forwarding (the user shares a group post into the app) a good enough substitute where direct ingestion is not allowed?
7. Which regions first? The draft proposes Gulf, East Africa, Southern Europe, Chinese AI and Japan for Phase 1, but that is too many for one person; the choice should follow where the first users are.
8. For China: is a Chinese-speaking user base a target, or only the segments reachable in English? The former doubles the source work and raises the legal exposure.
9. For Japan: should the product go beyond discovery and connect users to the visa and relocation step, which is where most foreign candidates drop out? That is a different product, but it may be where the money is.
10. Which other structural-shortage markets follow Japan: South Korea, Germany, Taiwan? Each has the same shape and a different language barrier.
11. For Southern Europe: can the product partner with digital agents and accountants as a channel, since they are who the SME buyer actually trusts? That turns Client Hunter into a lead source for intermediaries, which may be a better business than selling to individual consultants.

---

## 17. Market focus: China AI

China is the second-largest AI labour market and the least visible one from outside. None of LinkedIn, Indeed or the Western remote boards index it meaningfully, which is exactly the kind of gap this product exists to close.

### 17.1 What the market looks like

- **Employers.** The large labs and platforms (ByteDance / Doubao, Alibaba / Qwen, Tencent / Hunyuan, Baidu / ERNIE, DeepSeek, Moonshot / Kimi, Zhipu, MiniMax, StepFun, 01.AI), the autonomous-driving and robotics companies, the chip and inference-infrastructure firms, and thousands of application startups building on open-weight models.
- **Roles.** Algorithm engineer (算法工程师) is the umbrella title and covers LLM, CV, speech, recommendation and search. Alongside it: large-model engineer (大模型工程师), data annotation and RLHF labelling (数据标注), AI product manager, inference and CUDA engineers, evaluation and safety.
- **Rates.** Senior algorithm roles pay well by any standard. Annotation and labelling pay $3 to $10 per hour domestically but far more for English, legal, medical and code domains, which is where non-Chinese users fit.
- **Where it is listed.** Boss直聘, 拉勾, 猎聘, 智联招聘, 前程无忧 (51job) for the mainstream; 脉脉 for referrals; 牛客 for new graduates; company WeChat public accounts (公众号) and 知乎 / 掘金 posts for teams that hire directly. Overseas-facing hiring runs through company English career pages, Boss直聘's overseas channel, and dedicated Singapore or Hong Kong entities.

### 17.2 What is realistically reachable from outside China

Honesty here matters more than coverage numbers.

| Opportunity type | Reachable? | Notes |
|---|---|---|
| Onsite algorithm roles in Beijing / Shanghai / Shenzhen / Hangzhou | Only with Chinese fluency and a work permit | Index them for Chinese-speaking users; do not show them to others as "remote" |
| Overseas entities of Chinese AI firms (Singapore, HK, US, EU) | Yes | Same hiring as Western companies, listed on English career pages; good match for senior non-Chinese users |
| Remote English-domain annotation, evaluation, red-teaming | Yes, in volume | Runs through data vendors and lab contractor programmes; hourly, often $10 to $40; the single biggest China-linked opportunity for a global user base |
| Remote contract work for Chinese startups building for overseas markets | Sometimes | Growing; found through founders' posts, Product Hunt-style launches, and overseas-hiring channels; payment via Payoneer or Wise, so payment-risk scoring applies |
| Client Hunter needs at Chinese companies | Partially | Funding and hiring signals are available; tech-stack detection on Chinese web properties is weak; the buyer is usually reached through an introduction, not cold email |

### 17.3 Sources and signals

- **Funding and company data.** IT桔子 and 36氪 for rounds and investors; 企查查 / 天眼查 for registration and headcount; MIIT and CAC announcements for licensed model releases, which are a hiring signal in themselves.
- **Hiring patterns.** A company posting algorithm, data and inference roles together, or opening a Singapore entity, is expanding or going overseas. Both create reachable work.
- **Technology signals.** Open-weight model releases on Hugging Face and ModelScope with a company attribution, GitHub organisations, papers with corporate affiliations. These identify the team and its stack more reliably than website scanning.
- **Language.** All extraction runs in Chinese. Scores and packets are rendered in the user's language with the original Chinese kept as evidence. Title normalisation (算法工程师 → ML engineer; 大模型 → LLM) is maintained as a curated mapping, not left to the model.
- **Access.** No scraping behind login and no mainland phone-number accounts operated by the product. Public pages, public WeChat articles, funding databases and user-forwarded posts only. This limits mainstream-board coverage and the draft accepts that; the reachable segments in 17.2 do not depend on those boards.

### 17.4 Phase 1 for China

Add Chinese AI as a fourth Phase 1 region alongside Gulf, East Africa and Western Europe, limited to the two reachable segments: overseas entities of Chinese AI firms, and remote English-domain annotation and evaluation. Success metric: at least ten verified, applyable opportunities per week in each segment by the end of the phase.

---

## 18. Market focus: Japan

Japan is the clearest case of demand created by demographics rather than growth. The working-age population has been falling since the mid-1990s, METI's own estimate is a shortfall of several hundred thousand IT workers by 2030, and a large share of corporate systems still run on COBOL and on-premise Java that the engineers who built them are retiring from. The government's "2025 digital cliff" warning, the DX subsidy programmes and the easing of engineer visas are all one response: Japan has to import or outsource technical work, and has started doing so.

For this product that means Japan is a market where a non-Japanese engineer is not competing against a deep local bench. The bench is not there.

### 18.1 What the market looks like

- **Demand types.** Legacy modernisation (COBOL, mainframe, old Java and .NET), cloud migration, ERP replacement, factory and logistics automation, bilingual bridge engineers between Japanese firms and offshore teams, and increasingly AI integration. Most of it is in Tokyo, Osaka, Nagoya and Fukuoka; a growing share is remote within Japan or offshore.
- **Employers.** Global-facing tech (Mercari, Rakuten, PayPay, LINE Yahoo, SmartNews, Woven by Toyota, Preferred Networks, Sony) hire in English. Traditional SIers (NTT Data, Fujitsu, NEC, Hitachi) and manufacturers hire mostly in Japanese but outsource heavily. SMEs with DX subsidy approval are the Client Hunter target: funded, under-staffed, and unlikely to have posted anything in English.
- **Language.** The real divider. Roles are "English OK", "Japanese business level (JLPT N2)" or "native". Scoring must treat language as a hard dimension and show the requirement in every packet. A user with N2 sees roughly ten times the market of one without it.
- **Visas.** Engineer / Specialist in Humanities is the standard sponsored route; Highly Skilled Professional gives points-based fast residency; the J-Find and Digital Nomad visas cover short stays. Whether a listing sponsors a visa is a scoring input, and "visa sponsored" is a filter.
- **Rates.** Senior roles pay below the US but comfortably above most of Asia and Europe, with low tax friction for sponsored employees. Low-rate work is rare domestically; the $10 per hour segment here is offshore development subcontracted by Japanese firms to Vietnam, the Philippines and India, which is itself a reachable opportunity for users in those countries.

### 18.2 What is reachable from outside Japan

| Opportunity type | Reachable? | Notes |
|---|---|---|
| English-OK roles at global-facing Japanese tech | Yes | Listed on English career pages and the foreign-engineer boards; visa sponsored; the natural entry point |
| Japanese-language roles at SIers and manufacturers | With N2 or better | Large volume; index for Japanese-capable users only |
| Offshore development contracts from Japanese firms | Yes, for teams in Vietnam, Philippines, India | Found via bridge-SE postings and offshore-vendor hiring; stable, long engagements |
| Remote contract for Japanese startups | Sometimes | Growing post-2020; time-zone overlap matters; payment usually clean |
| Client Hunter needs at Japanese SMEs | Partially | DX subsidy lists and local news are strong signals; the buyer expects an introduction or a local partner, so the recommended action is often "find the partner", not "email the CEO" |

### 18.3 Sources and signals

- **Foreign-engineer boards.** Japan Dev, TokyoDev, Daijob, GaijinPot Jobs, and the English pages of Wantedly and Green. These are small, well-curated, and already tag language level and visa sponsorship, which makes them the best-quality source in any region.
- **Domestic boards.** Doda, Indeed Japan, BizReach, Green, Wantedly, Paiza for engineers; LinkedIn is used but shallow. Mostly Japanese-language; index for Japanese-capable users.
- **Public signals.** METI and IPA publications on the digital shortage, DX subsidy (IT導入補助金) approval lists, DX認定 certified companies, prefectural digitisation grants, EDINET filings mentioning system renewal, and local press on factory automation. A DX-certified SME with no engineering hires is a textbook Client Hunter need.
- **Hiring patterns.** A traditional company posting its first English-language engineering role, or a bridge-SE role, is opening to foreign engineers. Flag the first such posting per company as a trigger.
- **Language handling.** All extraction runs in Japanese; language requirement, visa sponsorship and remote scope are extracted as structured fields, not inferred. Title normalisation (SE, PG, PL, PM, インフラエンジニア) is a curated mapping.
- **Access.** Japanese boards are generally indexable without login and have no equivalent of China's real-name barrier. Respect robots.txt and rate limits; prefer the boards' feeds and employer pages.

### 18.4 Phase 1 for Japan

Add Japan as a Phase 1 region restricted to English-OK sponsored roles and offshore development contracts, the two segments where coverage is cheap and the match for a global user base is strongest. Measure the language-filter accuracy separately: a packet that sends a non-Japanese speaker to an N2 role is a precision failure, not a near miss.

---

## 19. Market focus: Southern Europe (Italy, Spain, Portugal, Greece)

Southern Europe is the third pattern. There is no shortage of working-age people, but the EU's own Digital Economy and Society Index puts Italy near the bottom of the Union on basic digital skills and ICT specialists per capita, with Spain, Portugal and Greece only somewhat better. The economy is dominated by small and family-owned firms that run on spreadsheets, on-premise accounting packages, paper and WhatsApp. Then, from 2021, EU recovery money arrived: Italy's PNRR earmarked tens of billions for digitisation, Spain's Kit Digital pays SMEs directly for websites, e-commerce, ERP and process automation, and Portugal and Greece run equivalent schemes. The result is a large population of funded, under-skilled buyers who have never written a job post and would not know what to put in one.

For a consultant, that is the Client Hunter thesis in its purest form. For an employee, it is a market where mid-level skills that are commodity in London or Berlin are scarce locally.

### 19.1 What the market looks like

- **Demand types.** ERP and accounting migration, e-commerce and marketplace integration, warehouse and logistics automation, CRM for sales-led SMEs, data consolidation across spreadsheets, cloud migration from on-premise servers, GDPR and e-invoicing compliance (Italy's SDI, Spain's Verifactu), and increasingly AI integration for customer service and document handling.
- **Buyers.** Owner-managers of 10 to 200 person firms in manufacturing, agri-food, fashion, tourism, construction and distribution. They buy through a local accountant, a trade association or a "digital agent", not through a job board.
- **Employers for salaried roles.** Startup hubs in Barcelona, Madrid, Lisbon, Milan and Valencia hire in English; the banks, telcos and large industrials hire in the local language; the rest outsource to local system integrators, who are chronically short of senior people.
- **Language.** Spanish, Italian, Portuguese or Greek is required for the SME segment and most corporate roles. English is enough in the startup hubs and for nearshore work. Score language as a hard dimension, as in Japan.
- **Rates.** Lower than Northern Europe, which cuts both ways: a Spanish or Italian engineer is attractive to German and Dutch firms as nearshore talent, and a consultant from Eastern Europe, North Africa or South Asia can price competitively against local integrators. A $10 to $25 per hour band is realistic here for support, QA and junior development work from outside the EU.
- **Visas and tax.** EU and EEA citizens need nothing. Non-EU candidates use the EU Blue Card (eased in 2023), national skilled-worker permits, or the digital nomad visas that Spain, Portugal, Italy and Greece all now offer. Spain's Beckham regime, Italy's inbound-worker tax relief and Portugal's successor to NHR materially raise net pay for relocators, and a packet should say so.

### 19.2 What is reachable from where

| Opportunity type | Reachable by | Notes |
|---|---|---|
| English-speaking roles in the startup hubs | Anyone with EU work rights or sponsorship | Listed on LinkedIn, Indeed and the local boards; standard Western hiring |
| Local-language corporate and integrator roles | Local-language speakers | Large volume; EU citizens from elsewhere with the language are in demand |
| Remote contract for SMEs and integrators | EU-based or EU-time-zone freelancers with the language | Found via Malt, local freelance platforms and subcontracting by integrators |
| Nearshore work from Northern Europe | Spanish, Italian, Portuguese engineers | German, Dutch and Nordic firms hire here for cost; reverse direction of the usual flow |
| Offshore support, QA and junior dev at $10 to $25 per hour | Users in Eastern Europe, North Africa, South Asia, Latin America | Latin America has a language advantage for Spain; Francophone and Arabic-speaking North Africa for Southern Europe generally |
| Client Hunter needs at funded SMEs | Consultants with the language and a local partner | The buyer expects a referral; the recommended action is usually to reach the accountant, trade association or digital agent, not the owner directly |

### 19.3 Sources and signals

- **Boards and platforms.** Spain: InfoJobs, Tecnoempleo, Manfred, LinkedIn, Indeed. Italy: LinkedIn, Indeed, Monster, InfoJobs.it, Subito Lavoro. Portugal: Net-Empregos, ITJobs.pt, Landing.jobs. Greece: Kariera, Skywalker. EU-wide: EURES, Malt and Freelancermap for freelance, and the EU tender portal TED for public work.
- **Public-money signals.** These are the distinctive asset of this region. Spain publishes the list of approved Kit Digital "agentes digitalizadores" and the firms that received vouchers; Italy's PNRR tenders and awards are on OpenPNRR and the regional portals; Industria 4.0 / Transizione 5.0 tax-credit uptake, Portugal's PRR awards and Greece's Digital Transformation programme are all public. A firm that received a digitisation grant and has no IT hires is a Client Hunter need with the budget already attached.
- **Company data.** Spain's Registro Mercantil and Italy's Registro Imprese for size and sector; Chamber of Commerce directories; trade-association member lists for the sectors above. Tech-stack detection works better here than in China because the firms' public web presence is Western-hosted.
- **Hiring patterns.** A family firm posting its first "responsabile IT" or "técnico informático" role, or an integrator posting several roles at once, is a trigger. The first-ever technical hire at a company is the single strongest signal in this region.
- **Language handling.** Extraction in all four languages; packets in the user's language with the original kept as evidence. Local title normalisation (técnico, responsabile IT, analista programador) is a curated mapping.
- **Access.** Boards and public registries are indexable within terms; prefer feeds and public pages. No special legal barrier beyond GDPR, which section 13 already covers.

### 19.4 Phase 1 for Southern Europe

Start with one country, not four: Spain, because Kit Digital publishes the cleanest list of funded SMEs and the language also opens Latin America as a user base. Index the English-speaking hub roles and the Kit Digital recipients, and test the Client Hunter packet against the latter. Success metric: of twenty funded SMEs with no IT hires, how many respond to an evidence-led approach routed through their digital agent or accountant. That number decides whether the referral-routing feature in section 8 is worth building first.
