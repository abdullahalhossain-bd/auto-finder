export interface User {
  id: string
  email: string
}

export interface Campaign {
  id: string
  organization_id: string
  natural_language_input: string
  structured_params?: Record<string, unknown> | null
  status: string
  total_leads_found: number
  qualified_leads: number
  created_at: string
  updated_at: string
}

export interface Lead {
  id: string
  campaign_id: string
  business_id: string
  opportunity_score?: number | null
  score_breakdown?: Record<string, unknown> | null
  stage: string
  confidence_summary?: Record<string, string> | null
  notes?: string | null
  business_name?: string | null
  business_category?: string | null
  business_address?: string | null
  business_phone?: string | null
  business_website?: string | null
  created_at: string
  updated_at: string
}

export interface Message {
  id: string
  lead_id: string
  contact_id?: string | null
  content: string
  status: string
  subject?: string | null
  approved_by?: string | null
  sent_at?: string | null
  esp_message_id?: string | null
  esp_provider?: string | null
  to_email?: string | null
  last_send_error?: string | null
  ai_rationale?: string | null
  generation_provider?: string | null
  created_at: string
  updated_at?: string
}

export interface SuppressionEntry {
  id: string
  organization_id: string
  contact_value: string
  reason?: string | null
  created_at: string
}

