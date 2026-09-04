const API_BASE = '/api/v1'

function getToken(): string | null {
  return localStorage.getItem('access_token')
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken()

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  })

  const data = await res.json().catch(() => ({}))

  if (!res.ok) {
    const msg =
      data?.error?.message ||
      data?.detail?.error?.message ||
      data?.detail ||
      'Request failed'

    throw new Error(String(msg))
  }

  return data as T
}

export type GeneratedMessage = {
  id?: string
  lead_id?: string
  content?: string
  subject?: string
  ai_rationale?: string
  generation_provider?: string
  status?: string
  job_id?: string
}

export const api = {
  // ============================================================
  // AUTH
  // ============================================================

  login: (email: string, password: string) =>
    request<{ access_token: string; refresh_token?: string }>(
      '/auth/login',
      {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }
    ),

  register: (
    email: string,
    password: string,
    organization_name: string,
    tos_accepted: boolean = true
  ) =>
    request<{ access_token: string }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        email,
        password,
        organization_name,
        tos_accepted,
      }),
    }),

  forgotPassword: (email: string) =>
    request<{ ok: boolean; message: string }>(
      '/auth/forgot-password',
      {
        method: 'POST',
        body: JSON.stringify({ email }),
      }
    ),

  resetPassword: (token: string, new_password: string) =>
    request<{ ok: boolean }>('/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify({
        token,
        new_password,
      }),
    }),

  // ============================================================
  // CAMPAIGNS
  // ============================================================

  listCampaigns: () =>
    request<{
      items: import('../types').Campaign[]
      total: number
    }>('/campaigns'),

  createCampaign: (
    input:
      | string
      | {
          natural_language_input: string
          structured_params?: Record<string, unknown>
        }
  ) => {
    const body =
      typeof input === 'string'
        ? { natural_language_input: input }
        : input
    return request<import('../types').Campaign>('/campaigns', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  },

  getCampaign: (id: string) =>
    request<import('../types').Campaign>(
      `/campaigns/${id}`
    ),

  startCampaign: (id: string) =>
    request<{
      total_found: number
      qualified: number
    }>(`/campaigns/${id}/start`, {
      method: 'POST',
    }),

  listCampaignLeads: (
    campaignId: string,
    stage?: string
  ) => {
    const params = new URLSearchParams()

    if (stage) {
      params.set('stage', stage)
    }

    const q = params.toString()

    return request<{
      items: import('../types').Lead[]
      total: number
    }>(
      `/campaigns/${campaignId}/leads${q ? `?${q}` : ''}`
    )
  },

  // ============================================================
  // LEADS
  // ============================================================

  listLeads: (
    campaignId: string,
    stage?: string
  ) => {
    const params = new URLSearchParams({
      campaign_id: campaignId,
    })

    if (stage) {
      params.set('stage', stage)
    }

    return request<{
      items: import('../types').Lead[]
      total: number
    }>(`/leads?${params}`)
  },

  getLead: (id: string) =>
    request<import('../types').Lead>(
      `/leads/${id}`
    ),

  updateLead: (
    id: string,
    data: {
      stage?: string
      notes?: string
    }
  ) =>
    request<import('../types').Lead>(
      `/leads/${id}`,
      {
        method: 'PATCH',
        body: JSON.stringify(data),
      }
    ),

  setLeadStage: (
    id: string,
    stage: string,
    notes?: string
  ) =>
    request<import('../types').Lead>(
      `/leads/${id}/stage`,
      {
        method: 'POST',
        body: JSON.stringify({
          stage,
          notes,
        }),
      }
    ),

  disqualifyLead: (
    id: string,
    reason?: string
  ) =>
    request<import('../types').Lead>(
      `/leads/${id}/disqualify`,
      {
        method: 'POST',
        body: JSON.stringify({
          reason,
        }),
      }
    ),

  doNotContact: (
    id: string,
    reason?: string
  ) =>
    request<import('../types').Lead>(
      `/leads/${id}/do-not-contact`,
      {
        method: 'POST',
        body: JSON.stringify({
          reason,
        }),
      }
    ),

  // ============================================================
  // MESSAGES
  // ============================================================

  createMessage: (
    lead_id: string,
    content: string
  ) =>
    request<import('../types').Message>(
      '/messages',
      {
        method: 'POST',
        body: JSON.stringify({
          lead_id,
          content,
        }),
      }
    ),

  generateMessage: (
    lead_id: string,
    opts?: {
      service_offered?: string
      async_mode?: boolean
    }
  ) =>
    request<GeneratedMessage>(
      `/leads/${lead_id}/messages`,
      {
        method: 'POST',
        body: JSON.stringify({
          service_offered:
            opts?.service_offered,
          async_mode:
            opts?.async_mode ?? false,
        }),
      }
    ),

  listPendingMessages: () =>
    request<import('../types').Message[]>(
      '/messages/pending'
    ),

  approveMessage: (id: string) =>
    request<import('../types').Message>(
      `/messages/${id}/approve`,
      {
        method: 'POST',
      }
    ),

  rejectMessage: (id: string) =>
    request<import('../types').Message>(
      `/messages/${id}/reject`,
      {
        method: 'POST',
      }
    ),

  markReplied: (id: string) =>
    request<any>(
      `/messages/${id}/mark-replied`,
      {
        method: 'POST',
      }
    ),

  // ============================================================
  // FOLLOW-UPS
  // ============================================================

  scheduleFollowup: (
    messageId: string,
    delay_days = 3
  ) =>
    request<any>(
      `/messages/${messageId}/followup`,
      {
        method: 'POST',
        body: JSON.stringify({
          delay_days,
        }),
      }
    ),

  getFollowup: (messageId: string) =>
    request<any>(
      `/messages/${messageId}/followup`
    ),

  cancelFollowup: (followupId: string) =>
    request<any>(
      `/followups/${followupId}`,
      {
        method: 'DELETE',
      }
    ),

  // ============================================================
  // INBOX
  // ============================================================

  listReplies: () =>
    request<any[]>('/inbox/replies'),

  // ============================================================
  // SUPPRESSION
  // ============================================================

  listSuppression: () =>
    request<import('../types').SuppressionEntry[]>(
      '/suppression'
    ),

  addSuppression: (
    contact_value: string,
    reason?: string
  ) =>
    request<import('../types').SuppressionEntry>(
      '/suppression',
      {
        method: 'POST',
        body: JSON.stringify({
          contact_value,
          reason,
        }),
      }
    ),

  // ============================================================
  // BILLING
  // ============================================================

  getSubscription: () =>
    request<{
      plan_id: string
      status: string
      trial_end?: string
      current_period_end?: string
      caps: Record<string, number>
    }>('/billing/subscription'),

  subscribe: (
    plan: 'starter' | 'pro',
    urls?: {
      success_url?: string
      cancel_url?: string
    }
  ) =>
    request<{
      checkout_url: string
      session_id: string
      plan: string
    }>('/billing/subscribe', {
      method: 'POST',
      body: JSON.stringify({
        plan,
        ...urls,
      }),
    }),

  // ============================================================
  // ORGANIZATION
  // ============================================================

  getMe: () =>
    request<{
      id: string
      name: string
      plan: string
    }>('/organizations/me'),

  getUsage: () =>
    request<any>('/usage'),

  exportOrg: async () => {
    const token =
      localStorage.getItem('access_token')

    const res = await fetch(
      '/api/v1/organizations/me/export',
      {
        headers: token
          ? {
              Authorization: `Bearer ${token}`,
            }
          : {},
      }
    )

    if (!res.ok) {
      throw new Error('Export failed')
    }

    const blob = await res.blob()

    const url =
      URL.createObjectURL(blob)

    const a =
      document.createElement('a')

    a.href = url
    a.download = 'org-export.json'

    document.body.appendChild(a)
    a.click()
    a.remove()

    URL.revokeObjectURL(url)
  },

  // ============================================================
  // INVITES
  // ============================================================

  createInvite: (
    email: string,
    role = 'member'
  ) =>
    request<any>(
      '/organizations/me/invites',
      {
        method: 'POST',
        body: JSON.stringify({
          email,
          role,
        }),
      }
    ),

  listInvites: () =>
    request<any[]>(
      '/organizations/me/invites'
    ),

  revokeInvite: (id: string) =>
    request<any>(
      `/organizations/me/invites/${id}`,
      {
        method: 'DELETE',
      }
    ),

  acceptInvite: (
    token: string,
    password?: string
  ) =>
    request<any>(
      '/invites/accept',
      {
        method: 'POST',
        body: JSON.stringify({
          token,
          password,
        }),
      }
    ),

  // ============================================================
  // SENDING IDENTITY
  // ============================================================

  getSendingIdentity: () =>
    request<any>(
      '/settings/sending-identity'
    ),

  upsertSendingIdentity: (
    body: Record<string, unknown>
  ) =>
    request<any>(
      '/settings/sending-identity',
      {
        method: 'POST',
        body: JSON.stringify(body),
      }
    ),

  verifySendingIdentity: (
    spf = true,
    dkim = true
  ) =>
    request<any>(
      '/settings/sending-identity/verify',
      {
        method: 'POST',
        body: JSON.stringify({
          spf_verified: spf,
          dkim_verified: dkim,
        }),
      }
    ),

  // ============================================================
  // API CREDENTIALS
  // ============================================================

  listApiCredentials: () =>
    request<
      Array<{
        id: string
        provider: string
        last4?: string
        label?: string
      }>
    >('/settings/api-credentials'),

  createApiCredential: (
    provider: string,
    value: string,
    label?: string
  ) =>
    request<any>(
      '/settings/api-credentials',
      {
        method: 'POST',
        body: JSON.stringify({
          provider,
          value,
          label,
        }),
      }
    ),

  deleteApiCredential: (id: string) =>
    request<any>(
      `/settings/api-credentials/${id}`,
      {
        method: 'DELETE',
      }
    ),

  // ============================================================
  // PLATFORM ADMIN
  // ============================================================

  adminMe: () =>
    request<{
      is_platform_admin: boolean
      email?: string | null
      admin_configured?: boolean
    }>('/admin/me'),

  adminOverview: () =>
    request<{
      organizations: number
      organizations_active: number
      organizations_deleted: number
      users: number
      campaigns: number
      leads: number
      messages_sent: number
      plans: Record<string, number>
    }>('/admin/overview'),

  adminListOrgs: (opts?: {
    q?: string
    plan?: string
    include_deleted?: boolean
    limit?: number
    offset?: number
  }) => {
    const params = new URLSearchParams()
    if (opts?.q) params.set('q', opts.q)
    if (opts?.plan) params.set('plan', opts.plan)
    if (opts?.include_deleted) params.set('include_deleted', String(opts.include_deleted))
    if (opts?.limit) params.set('limit', String(opts.limit))
    if (opts?.offset) params.set('offset', String(opts.offset))
    const q = params.toString()
    return request<{ items: any[]; total: number }>(
      `/admin/organizations${q ? `?${q}` : ''}`
    )
  },

  adminGetOrg: (id: string) =>
    request<any>(`/admin/organizations/${id}`),

  adminPatchOrg: (
    id: string,
    data: { plan?: string; name?: string; soft_delete?: boolean }
  ) =>
    request<any>(`/admin/organizations/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  adminListUsers: (opts?: { q?: string; limit?: number; offset?: number }) => {
    const params = new URLSearchParams()
    if (opts?.q) params.set('q', opts.q)
    if (opts?.limit) params.set('limit', String(opts.limit))
    if (opts?.offset) params.set('offset', String(opts.offset))
    const q = params.toString()
    return request<{ items: any[]; total: number }>(
      `/admin/users${q ? `?${q}` : ''}`
    )
  },

  adminAuditLogs: (opts?: {
    organization_id?: string
    action?: string
    limit?: number
    offset?: number
  }) => {
    const params = new URLSearchParams()
    if (opts?.organization_id) params.set('organization_id', opts.organization_id)
    if (opts?.action) params.set('action', opts.action)
    if (opts?.limit) params.set('limit', String(opts.limit))
    if (opts?.offset) params.set('offset', String(opts.offset))
    const q = params.toString()
    return request<{ items: any[]; total: number }>(
      `/admin/audit-logs${q ? `?${q}` : ''}`
    )
  },

  // ============================================================
  // REFERRALS
  // ============================================================

  getReferralMe: () =>
    request<{
      code: string
      share_url: string
      signup_count: number
      successful_paid_referrals: number
      bonus_leads: number
      rewards: {
        signup_inviter_leads: number
        signup_invitee_leads: number
        paid_inviter_leads: number
      }
      history: Array<{
        status: string
        inviter_reward_leads: number
        invitee_reward_leads: number
        paid_reward_granted: boolean
        created_at?: string | null
      }>
    }>('/referrals/me'),

  ensureReferralCode: () =>
    request<{ code: string }>('/referrals/code', {
      method: 'POST',
    }),

  // ============================================================
  // LEAD QUALITY / PROOF METRICS
  // ============================================================

  leadQualityMetrics: () =>
    request<{
      organization_id: string
      as_of: string
      totals: {
        leads: number
        with_phone: number
        with_website: number
        strong_fit_score_ge_65: number
        contacted: number
        replied_or_later: number
        messages_sent: number
      }
      rates: {
        phone_coverage_pct: number
        website_present_pct: number
        strong_fit_pct: number
        contacted_pct: number
        reply_pct_of_leads: number
        reply_pct_of_contacted: number
      }
      method: { scoring: string; not: string; note: string }
    }>('/leads/quality-metrics'),

  exportLeadsCsv: async (opts?: { campaign_id?: string; stage?: string }) => {
    const token = localStorage.getItem('access_token')
    const params = new URLSearchParams()
    if (opts?.campaign_id) params.set('campaign_id', opts.campaign_id)
    if (opts?.stage) params.set('stage', opts.stage)
    const q = params.toString()
    const res = await fetch(`/api/v1/leads/export.csv${q ? `?${q}` : ''}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) {
      throw new Error('Export failed')
    }
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'leads-export.csv'
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  },
}