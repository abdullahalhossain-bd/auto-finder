# DEMO MODE

`DEMO_MODE=true` (default in `.env` for buyer demos)

## Guarantees
- No Google Maps / Places / Search API calls
- No Facebook API
- No Stripe / payment gateway
- No remote AI — deterministic templates
- No real ESP email delivery

## Architecture
UI → Service layer → Mock adapters → fixtures (`app/demo/fixtures.py`)

## Buyer login
Open `/demo`:
- demo.user — free plan
- demo.pro — pro plan
- demo.admin — platform admin

Always show Demo Mode / Demo Data labels in UI.
