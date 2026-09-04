# Core Database Schema (Stage 1)

## organizations
id, name, plan, created_at

## users
id, email, password_hash, full_name, created_at

## memberships
user_id, organization_id, role

## campaigns
id, organization_id, natural_language_input, structured_params (jsonb), status, created_at

## businesses
id, name, category, address, latitude, longitude, phone, website_url, rating, review_count, source_data (jsonb)

## leads
id, campaign_id, business_id, opportunity_score, stage, confidence_summary (jsonb), created_at

## website_audits
id, business_id, has_ssl, has_viewport, booking_vendor_detected, http_status, raw_findings (jsonb), crawled_at

## contacts
id, business_id, type (email/phone), value, confidence_state, consent_state

## messages
id, lead_id, content, status (draft/approved/sent/rejected), approved_by, sent_at, created_at

## suppression_list
id, organization_id, contact_value, reason, created_at

## followups
id, message_id, scheduled_at, status

## jobs
id, type, status, payload (jsonb), idempotency_key, created_at

## audit_logs
id, actor_id, action, target, metadata (jsonb), created_at
