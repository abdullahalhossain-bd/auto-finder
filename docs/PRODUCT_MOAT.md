# Why this is hard to clone as a weekend project

This is not DRM. It is product depth that takes real engineering to reproduce well.

1. **Multi-tenant isolation** — org-scoped data, memberships, soft-delete, audit logs.
2. **Discovery + deterministic scoring** — OSM/Places, website audits, rule-based opportunity scores (LLM never invents the score).
3. **Safe outreach** — human approval, suppression, SPF/DKIM identity, ESP webhooks, bounce auto-pause.
4. **Quota + billing** — plan caps, referral bonus credits, Stripe portal/webhooks, trial expiry gates on send.
5. **Referral growth loop** — shareable codes, signup + paid conversion rewards enforced server-side.
6. **Ops** — platform admin, Celery jobs, rate limits, structured logging.

A static UI or scraper demo is easy. A trustworthy B2B outreach SaaS with billing, trust, and isolation is not.
