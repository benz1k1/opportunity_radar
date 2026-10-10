# Opportunity Radar — Product Draft

## Core Idea

An AI **opportunity-discovery and targeting engine** for technical professionals and independent consultants.

Instead of simply finding jobs by keywords, it detects **evidence that someone needs what you can provide**—including opportunities that have not yet been posted as jobs or projects.

> **Don't wait for work to be posted. Find evidence that someone needs your skills.**

---

## Three Modes

### 1. Career Hunter
Find high-value jobs matching the user's skills, seniority, location, remote preference, salary, and experience.

### 2. Contract Hunter
Find freelance/contract opportunities from marketplaces and the wider web.

### 3. Client Hunter
Proactively identify companies likely to need IT work—even when they have not published a project.

**Client Hunter is the main differentiation.**

---

## 1. Opportunity Graph

Build a continuously updated graph connecting:

```text
USER
 ├── skills
 ├── experience
 ├── seniority
 ├── preferences
 └── past outcomes
        ↓
OPPORTUNITY GRAPH
 ├── Jobs
 ├── Companies
 ├── Projects
 ├── People / decision makers
 ├── Technology
 └── Signals
        ↓
RECOMMENDED ACTION
```

Skills are not simple tags. Represent them as a capability model with confidence and relationships.

Example:

```text
Java
 ├── Spring Boot
 ├── PostgreSQL
 ├── Kafka
 ├── Microservices
 └── Backend

ETL
 ├── Python
 ├── SQL
 ├── Data pipelines
 └── Migration
```

---

## 2. Opportunity Scoring

Every opportunity gets a score based on multiple dimensions:

```text
Technical match
Seniority match
Domain match
Location / remote match
Salary / budget match
Recency
Competition
Company quality
Opportunity strength
```

Example:

```text
Technical match     94%
Seniority match     98%
Location match     100%
Competition         LOW
Overall opportunity 93/100
```

The system must explain **why** it scored the opportunity highly.

---

## 3. Need Detection

Go beyond job titles.

Example:

A company is simultaneously hiring:

- Senior Java Engineer
- Data Engineer
- DevOps Engineer

The system infers:

> Possible backend/platform expansion rather than a single replacement hire.

Potential opportunity:

**Java/backend modernization or platform engineering**

This turns job listings into **business-intelligence signals**.

---

## 4. Client Discovery / Pain Detection

Search the open web for signals of technology problems rather than only explicit project listings.

### Direct signals

- "looking for a developer"
- "need help with..."
- "migrate our..."
- "automate..."
- "integrate..."
- "legacy application"
- "custom CRM"
- "database problems"

### Indirect signals

- Recent funding
- Rapid hiring
- New CTO / engineering leadership
- Acquisition / merger
- Geographic expansion
- New product launch
- Old technology stack
- Multiple engineering vacancies
- New ERP implementation
- Manual business workflows
- Technology migration
- Outsourcing indicators

The goal is to identify:

> **Companies with probable IT pain before they become obvious freelance opportunities.**

---

## 5. Technology Archaeology

Build a company technology profile from publicly observable signals.

Example:

```text
ABC Logistics

Technology:
- WordPress
- WooCommerce
- Cloudflare
- Old frontend stack

Business:
- B2B logistics
- 75 employees
- Rapid growth

Signals:
- New warehouse
- Hiring operations staff
- Recent expansion

Potential IT opportunities:
★★★★★ Operations automation
★★★★☆ Customer portal
★★★★☆ Data integration
★★★☆☆ Analytics platform
```

---

## 6. "What Can I Sell Them?"

Do not stop at identifying a company.

Translate signals into possible services.

Example:

```text
Company problem:
Manual order processing

Potential solution:
Backend/API + workflow automation

Possible project:
3–8 week engagement

Potential value:
$8k–$25k
```

Generate a short rationale based on evidence, not generic AI guesses.

---

## 7. Trigger Events

Monitor events that can create future IT demand.

```text
Funding
   ↓
Hiring
   ↓
Product expansion
   ↓
Infrastructure pressure
   ↓
Potential engineering work
```

Other triggers:

- Acquisition
- New CTO
- New product
- New market
- New enterprise customer
- Rapid employee growth
- Cloud migration
- ERP change
- Legacy modernization
- Major website rebuild

Translate every trigger into:

> **What IT work could this create?**

---

## 8. Company DNA

Maintain a persistent company profile:

```text
Company
Industry
Employees
Growth
Funding
Technology
Engineering maturity
Likely IT spend
Hiring
Current triggers
Potential problems
Likely buyer
Historical opportunities
```

The profile evolves over time.

---

## 9. Buyer Detection

Map problems to likely decision makers.

```text
Backend modernization → CTO / VP Engineering
Data integration      → CTO / Data leader
Internal automation   → COO / Operations
Website modernization → Founder / Marketing
Legacy Java system    → CTO / Engineering Director
```

The system should identify the likely buyer role and, where publicly appropriate, the relevant decision maker.

---

## 10. Opportunity Packet

Every important opportunity should be presented as a compact research packet.

```text
ABC Logistics

Opportunity: Backend modernization
Confidence: 89/100

Evidence:
- Hiring 3 backend engineers
- Old customer portal
- Recent funding
- Rapid employee growth
- Java mentioned in vacancy

What you can sell:
Backend/API modernization + data integration

Likely buyer:
CTO

Why you:
Java + Python + backend + architecture + ETL

Potential value:
$10k–$30k

Recommended action:
Contact CTO
```

This is the core user experience.

---

## 11. Competition Intelligence

Estimate how crowded an opportunity is.

Example:

```text
Opportunity: 91/100
Competition: LOW

Reasons:
- Niche Java stack
- Seniority requirement
- Recently posted
- Remote
- Company appears to have difficulty filling role
```

For client opportunities:

> Detect opportunities that have **not yet entered competitive marketplaces**.

---

## 12. Learning From Outcomes

The system learns from actual results.

### Job outcomes

```text
Accepted:
- Java + architecture
- Senior roles
- Remote
- 10–15+ years

Rejected:
- Junior/mid-level
- Frontend-only
- Onsite
- Low salary
```

### Client outcomes

```text
Won:
- Backend modernization
- ETL
- Internal tools
- Architecture consulting

Lost:
- WordPress
- SEO
- Low-value projects
```

Future recommendations adapt automatically.

---

## 13. Opportunity Radar

The product should proactively deliver a daily/weekly radar rather than requiring constant searching.

Example:

```text
OPPORTUNITY RADAR

🔥 3 Immediate Opportunities

1. Australian SaaS — Java modernization
   Match: 96
   Remote
   Recent funding

2. UK logistics company — data integration
   Match: 91
   No public project
   CTO identified

3. US fintech — Python/ETL contract
   Match: 88
   Recently posted

🧠 Emerging Opportunities
4 companies showing early demand signals

💰 Consulting Opportunities
2 companies with probable technology pain
```

---

## 14. Application Workflow

Avoid making mass autonomous application the product.

Preferred flow:

```text
Discover
   ↓
Classify
   ↓
Score
   ↓
Generate tailored application
   ↓
User reviews
   ↓
User applies / authorized API workflow
```

Where platforms prohibit scraping or automation, use compliant APIs or human-in-the-loop browser assistance.

---

## 15. What NOT to Build

Avoid becoming another:

- Resume builder
- Cover-letter generator
- LinkedIn scraper
- 1-click mass apply bot
- Generic Upwork scraper
- Job aggregator
- Keyword job matcher
- Generic CRM
- Generic cold-email generator

These are easy to copy and poorly differentiated.

---

## 16. The Moat

The valuable dataset becomes:

```text
Skills
   ↓
Companies
   ↓
Signals
   ↓
Problems
   ↓
Opportunities
   ↓
Recommended actions
   ↓
Outcomes
```

Over time the system learns:

**Which signals predict real opportunities for which person, company, technology, service, and price range.**

That outcome data becomes the moat.

---

## Product Positioning

> **An AI opportunity-hunting engine for technical professionals and independent consultants.**
>
> It doesn't wait for work to be posted. It continuously looks for evidence that someone needs what you can do, scores the opportunity, explains why, identifies the likely buyer, and tells you what to do next.

### Core differentiator

**The question isn't:**

> "Where are the jobs?"

**The question is:**

> **"Which companies are about to need a Java/Python/backend/data engineer, but haven't asked for one yet?"**
