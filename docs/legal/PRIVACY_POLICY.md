# Privacy Policy

**Last updated:** 2026-08-23  
**Product:** AI Sales Agent (Local Business Opportunity Finder + Safe Outreach Assistant)

## 1. Who we are
This platform helps freelancers and small agencies discover publicly listed local businesses and draft outreach messages. The operator of your deployment is the data controller for account data collected through that deployment.

## 2. Data we collect
- **Account data:** email, password hash (argon2id), organization name, role.
- **Usage data:** campaigns, discovered business records, leads, messages, approval actions, suppression list entries.
- **Technical logs:** request IDs, IP-derived rate-limit keys, error traces — retained for security and reliability.

We do **not** sell personal data. We do not use discovered business contacts for our own marketing.

## 3. Business contact data
Discovered businesses and contact details come from public sources (e.g. OpenStreetMap) and optional third-party APIs you configure (e.g. Google Places with **your** API key). You are responsible for ensuring outreach complies with laws in your target jurisdiction (CAN-SPAM, GDPR/ePrivacy, PECR, etc.).

## 4. How we use data
- Provide the service (discovery, scoring, message drafting, sending via your configured ESP).
- Enforce plan limits, abuse prevention, and deliverability protections.
- Improve reliability and security of the platform.

## 5. Sharing
- **Email service providers** (e.g. Resend) process outbound mail you approve.
- **LLM providers** (platform-hosted Ollama by default; optional Groq with your key) receive only the business facts needed to draft a message — not your password.
- We do not share data with advertisers.

## 6. Retention
- Account and operational data: while your account is active.
- After account deletion request: soft-delete then hard-delete within approximately 30 days, except records we must keep for legal compliance or dispute resolution.
- Inactive discovered contact data may be purged after a period of inactivity to limit storage of stale data.

## 7. Security
Passwords are hashed. API credentials are encrypted at rest when stored. Access is organization-scoped. No system can guarantee absolute security; report issues to the operator of your deployment.

## 8. Your rights
Depending on your location you may have rights to access, correct, export, or delete personal data. Contact the deployment operator. Export and deletion endpoints are provided for organization owners where implemented.

## 9. Children
This service is for business users, not directed at children under 16.

## 10. Changes
We may update this policy. Material changes will be reflected by updating the “Last updated” date and, where appropriate, notifying account holders.
