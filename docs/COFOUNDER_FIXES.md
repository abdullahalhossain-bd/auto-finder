# Co-founder fixes (post devil’s advocate)

## Shipped

1. **Free path value** — Free users can draft messages via **template** (always). LLM personalization remains paid (`ai_auto_message`). No more “leads with zero product writing path.”
2. **Honest scoring** — UI/API labels: opportunity / strong fit / rules-based — not “AI Hot Lead” theater.
3. **Leads N+1** — `GET /leads` without `campaign_id` lists org-wide leads; Dashboard + Leads page use `listAllLeads`.
4. **Referral abuse** — max 25 signup redemptions per code per UTC day.
5. **Analytics** — basic free; conversion/advanced still upsell, not a blank wall.
6. **Onboarding** — deliverability framed as hard requirement before send.
7. **Auto-reply** — labeled experimental; production path = Approvals + Inbox.

## Still the real work (not code theater)

- Measure phone-valid % and reply rate on one city vertical.
- Domain warm-up playbook + ESP production keys.
- Freeze new surface area until 10 paying orgs.
