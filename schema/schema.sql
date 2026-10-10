-- Opportunity Radar schema. Applied by load_data.py into the configured schema (search_path is set).
-- Ids are nanoid text. Money is stored in its ORIGINAL currency as numeric plus a currency code;
-- INR is computed at display time from fx_rate. Every fact and signal carries a source and a date.

CREATE TABLE IF NOT EXISTS user_profile (
    id              text PRIMARY KEY,
    name            text NOT NULL,
    headline        text NOT NULL DEFAULT '',
    summary         text NOT NULL DEFAULT '',
    seniority       text NOT NULL DEFAULT 'senior',          -- junior | mid | senior | lead
    years_experience numeric(4,1) NOT NULL DEFAULT 0,
    country         text NOT NULL DEFAULT 'IN',
    timezone        text NOT NULL DEFAULT 'Asia/Kolkata',
    rate_floor_inr_hour  numeric(10,2) NOT NULL,
    rate_target_inr_hour numeric(10,2) NOT NULL,
    remote_only     boolean NOT NULL DEFAULT true,
    open_to_fulltime boolean NOT NULL DEFAULT true,
    domains         text[] NOT NULL DEFAULT '{}',
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

-- Capability graph: a skill with confidence, optionally under a parent skill.
CREATE TABLE IF NOT EXISTS skill (
    id          text PRIMARY KEY,
    profile_id  text NOT NULL REFERENCES user_profile(id) ON DELETE CASCADE,
    name        text NOT NULL,
    parent_id   text REFERENCES skill(id) ON DELETE SET NULL,
    confidence  numeric(3,2) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    years       numeric(4,1) NOT NULL DEFAULT 0,
    aliases     text[] NOT NULL DEFAULT '{}',
    UNIQUE (profile_id, name)
);

CREATE TABLE IF NOT EXISTS source (
    key         text PRIMARY KEY,
    kind        text NOT NULL,            -- greenhouse | lever | ashby | remotive | arbeitnow | rss | fx
    region      text NOT NULL DEFAULT 'global',
    label       text NOT NULL,
    config      jsonb NOT NULL DEFAULT '{}'::jsonb,
    enabled     boolean NOT NULL DEFAULT true,
    last_run_at timestamptz,
    last_status text,
    last_count  integer
);

CREATE TABLE IF NOT EXISTS company (
    id          text PRIMARY KEY,
    name        text NOT NULL,
    domain      text,
    website     text,
    country     text,
    region      text,
    industry    text,
    headcount   integer,
    is_ai_native boolean NOT NULL DEFAULT false,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS company_domain_idx ON company (domain) WHERE domain IS NOT NULL;
CREATE INDEX IF NOT EXISTS company_name_idx ON company (lower(name));

-- Company DNA rows: dated, sourced facts.
CREATE TABLE IF NOT EXISTS company_fact (
    id          text PRIMARY KEY,
    company_id  text NOT NULL REFERENCES company(id) ON DELETE CASCADE,
    fact_type   text NOT NULL,            -- technology | headcount | funding | leadership | hiring | trigger | problem | buyer
    key         text NOT NULL,
    value       text NOT NULL,
    source_key  text NOT NULL,
    source_url  text,
    observed_at timestamptz NOT NULL DEFAULT now(),
    expires_at  timestamptz,
    UNIQUE (company_id, fact_type, key, value)
);

CREATE TABLE IF NOT EXISTS job_posting (
    id              text PRIMARY KEY,
    company_id      text NOT NULL REFERENCES company(id) ON DELETE CASCADE,
    source_key      text NOT NULL,            -- ats kind or board key; not a FK, derived/site labels share the column
    external_id     text NOT NULL,
    title           text NOT NULL,
    family          text NOT NULL DEFAULT 'other', -- backend | frontend | data | devops | ml | mobile | qa | security | product | other
    location        text,
    remote_scope    text NOT NULL DEFAULT 'unknown', -- worldwide | region | country | onsite | unknown
    remote_detail   text,
    employment_type text NOT NULL DEFAULT 'unknown', -- fulltime | contract | parttime | unknown
    rate_min        numeric(14,2),
    rate_max        numeric(14,2),
    rate_currency   text,
    rate_period     text,                            -- hour | month | year
    url             text NOT NULL,
    posted_at       timestamptz,
    first_seen_at   timestamptz NOT NULL DEFAULT now(),
    last_seen_at    timestamptz NOT NULL DEFAULT now(),
    closed_at       timestamptz,
    description     text NOT NULL DEFAULT '',
    tech            text[] NOT NULL DEFAULT '{}',
    is_english      boolean NOT NULL DEFAULT true,
    raw             jsonb NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (source_key, external_id)
);
CREATE INDEX IF NOT EXISTS job_posting_company_idx ON job_posting (company_id, closed_at);

-- A signal: one dated, sourced observation about a company.
CREATE TABLE IF NOT EXISTS signal (
    id          text PRIMARY KEY,
    company_id  text NOT NULL REFERENCES company(id) ON DELETE CASCADE,
    class       text NOT NULL,            -- direct | trigger | hiring | ai | shortage | technology
    kind        text NOT NULL,            -- e.g. funding_round, hiring_cluster, first_tech_hire, ai_adoption, old_stack
    title       text NOT NULL,
    detail      text NOT NULL DEFAULT '',
    strength    numeric(3,2) NOT NULL DEFAULT 0.5 CHECK (strength BETWEEN 0 AND 1),
    source_key  text NOT NULL,
    source_url  text,
    observed_at timestamptz NOT NULL DEFAULT now(),
    expires_at  timestamptz NOT NULL,
    dedupe_key  text NOT NULL UNIQUE,
    raw         jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS signal_company_idx ON signal (company_id, expires_at);

-- A need: what IT work the signals suggest. Never exists without at least one signal.
CREATE TABLE IF NOT EXISTS need (
    id          text PRIMARY KEY,
    company_id  text NOT NULL REFERENCES company(id) ON DELETE CASCADE,
    kind        text NOT NULL,            -- backend_modernization | data_platform | platform_expansion | ai_integration | first_tech_hire | portal_rebuild | automation
    summary     text NOT NULL,
    rationale   text NOT NULL,
    status      text NOT NULL DEFAULT 'active',  -- emerging | active | expired
    detected_by text NOT NULL,            -- rule:<name> | llm
    detected_at timestamptz NOT NULL DEFAULT now(),
    expires_at  timestamptz NOT NULL,
    UNIQUE (company_id, kind)
);
CREATE TABLE IF NOT EXISTS need_signal (
    need_id   text NOT NULL REFERENCES need(id) ON DELETE CASCADE,
    signal_id text NOT NULL REFERENCES signal(id) ON DELETE CASCADE,
    PRIMARY KEY (need_id, signal_id)
);

CREATE TABLE IF NOT EXISTS opportunity (
    id              text PRIMARY KEY,
    mode            text NOT NULL,        -- client | contract | career
    company_id      text NOT NULL REFERENCES company(id) ON DELETE CASCADE,
    need_id         text REFERENCES need(id) ON DELETE CASCADE,
    job_posting_id  text REFERENCES job_posting(id) ON DELETE CASCADE,
    title           text NOT NULL,
    score           integer NOT NULL CHECK (score BETWEEN 0 AND 100),
    dimensions      jsonb NOT NULL,       -- {technical: 94, seniority: 98, ...}
    reasons         jsonb NOT NULL,       -- ["...", "..."]
    sell            text NOT NULL DEFAULT '',
    engagement      text NOT NULL DEFAULT '',
    value_min       numeric(14,2),
    value_max       numeric(14,2),
    value_currency  text,
    value_period    text,                 -- hour | project | year
    buyer_role      text NOT NULL DEFAULT '',
    why_you         text NOT NULL DEFAULT '',
    action          text NOT NULL DEFAULT '',
    bucket          text NOT NULL,        -- immediate | emerging | consulting | dropped
    first_seen_at   timestamptz NOT NULL DEFAULT now(),
    last_scored_at  timestamptz NOT NULL DEFAULT now(),
    dropped_at      timestamptz,
    drop_reason     text,
    UNIQUE (mode, company_id, need_id, job_posting_id)
);
CREATE INDEX IF NOT EXISTS opportunity_bucket_idx ON opportunity (bucket, score DESC);

CREATE TABLE IF NOT EXISTS feedback (
    id              text PRIMARY KEY,
    opportunity_id  text NOT NULL REFERENCES opportunity(id) ON DELETE CASCADE,
    verdict         text NOT NULL,        -- relevant | not_relevant
    note            text NOT NULL DEFAULT '',
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS outcome (
    id              text PRIMARY KEY,
    opportunity_id  text NOT NULL REFERENCES opportunity(id) ON DELETE CASCADE,
    stage           text NOT NULL,        -- contacted | replied | call | proposal | won | lost | applied | interview | offer | accepted | rejected | declined
    note            text NOT NULL DEFAULT '',
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS fx_rate (
    currency    text NOT NULL,
    as_of       date NOT NULL,
    rate_inr    numeric(14,6) NOT NULL,   -- 1 unit of currency = rate_inr INR
    fetched_at  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (currency, as_of)
);

CREATE TABLE IF NOT EXISTS radar_run (
    id          text PRIMARY KEY,
    ran_at      timestamptz NOT NULL DEFAULT now(),
    immediate   integer NOT NULL,
    emerging    integer NOT NULL,
    consulting  integer NOT NULL,
    dropped     integer NOT NULL,
    summary     jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS fetch_log (
    id          text PRIMARY KEY,
    source_key  text NOT NULL,
    url         text NOT NULL,
    status      integer,
    ok          boolean NOT NULL,
    detail      text NOT NULL DEFAULT '',
    fetched_at  timestamptz NOT NULL DEFAULT now()
);

-- Country reference: stable facts only (name, workspace region, UTC offset of the main hub, English as a
-- normal working language). Seeded from resources/seed/country.csv. No statistics live here.
CREATE TABLE IF NOT EXISTS country (
    code        text PRIMARY KEY,         -- ISO 3166-1 alpha-2
    name        text NOT NULL,
    region      text NOT NULL,            -- us | uk | eu | gulf | in | jp | apac | latam | africa | other
    utc_offset  numeric(3,1) NOT NULL,    -- standard-time offset of the main business hub
    english_ok  boolean NOT NULL          -- English is an official or the usual working language in tech
);

-- Countries a posting is deliverable in/for, resolved from its free-text location by service/geo.py.
ALTER TABLE job_posting ADD COLUMN IF NOT EXISTS countries text[] NOT NULL DEFAULT '{}';
CREATE INDEX IF NOT EXISTS job_posting_countries_idx ON job_posting USING gin (countries);

-- Region gap: per-country picture of thin local IT supply and small budgets, recomputed each run
-- from open English engineering postings and live signals (service/regions.py).
CREATE TABLE IF NOT EXISTS region_gap (
    country_code text PRIMARY KEY REFERENCES country(code),
    score        integer NOT NULL CHECK (score BETWEEN 0 AND 100),
    thin         boolean NOT NULL,        -- fewer postings than the evidence floor; the score is capped
    dimensions   jsonb NOT NULL,          -- {shortage, low_depth, affordability, offshore_open, senior_demand, timezone}
    metrics      jsonb NOT NULL,          -- the counts and medians the dimensions were read from
    reasons      jsonb NOT NULL,          -- ["...", ...]
    computed_at  timestamptz NOT NULL DEFAULT now()
);
