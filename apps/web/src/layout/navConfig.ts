import { UserPersona, UserRole } from '../api/authApi'

export type NavItem = {
  id: string
  label: string
  to: string
  /** When false, route shows a planned-feature placeholder. */
  ready: boolean
  group?: string
}

const USER_NAV: NavItem[] = [
  { id: 'dashboard', label: 'Dashboard', to: '/dashboard', ready: true, group: 'Workspace' },
  { id: 'ask', label: 'AI Sahayak', to: '/ask', ready: true, group: 'Workspace' },
  { id: 'products', label: 'My Products', to: '/products', ready: true, group: 'Workspace' },
  { id: 'classify', label: 'Classification', to: '/classify', ready: true, group: 'Workspace' },
  { id: 'ip-strategy', label: 'IP Strategy', to: '/ip-strategy', ready: true, group: 'Intelligence' },
  { id: 'prior-art', label: 'Prior Art', to: '/prior-art', ready: true, group: 'Intelligence' },
  { id: 'regulatory', label: 'Regulatory', to: '/regulatory', ready: false, group: 'Intelligence' },
  { id: 'tk-abs', label: 'TK & ABS', to: '/tk-abs', ready: true, group: 'Intelligence' },
  { id: 'documents', label: 'Documents', to: '/documents', ready: true, group: 'Records' },
  { id: 'assessments', label: 'Assessments', to: '/assessments', ready: false, group: 'Records' },
  { id: 'my-cases', label: 'My Cases', to: '/cases', ready: true, group: 'Records' },
  { id: 'expert', label: 'Expert Assistance', to: '/expert-assistance', ready: false, group: 'Records' },
  { id: 'reports', label: 'Reports', to: '/reports', ready: false, group: 'Records' },
]

const RESEARCHER_NAV: NavItem[] = [
  { id: 'dashboard', label: 'Dashboard', to: '/dashboard', ready: true, group: 'Workspace' },
  { id: 'ask', label: 'Research Sahayak', to: '/ask', ready: true, group: 'Workspace' },
  { id: 'products', label: 'Research Projects', to: '/products', ready: true, group: 'Workspace' },
  { id: 'prior-art', label: 'Prior Art', to: '/prior-art', ready: true, group: 'Intelligence' },
  { id: 'tk-abs', label: 'TK Explorer', to: '/tk-abs', ready: true, group: 'Intelligence' },
  { id: 'ip-strategy', label: 'IP Opportunities', to: '/ip-strategy', ready: true, group: 'Intelligence' },
  { id: 'documents', label: 'Documents', to: '/documents', ready: true, group: 'Records' },
  { id: 'assessments', label: 'Saved Research', to: '/assessments', ready: false, group: 'Records' },
  { id: 'my-cases', label: 'My Cases', to: '/cases', ready: true, group: 'Records' },
  { id: 'reports', label: 'Reports', to: '/reports', ready: false, group: 'Records' },
  { id: 'expert', label: 'Expert Assistance', to: '/expert-assistance', ready: false, group: 'Records' },
]

const CULTIVATOR_NAV: NavItem[] = [
  { id: 'dashboard', label: 'Dashboard', to: '/dashboard', ready: true, group: 'Workspace' },
  { id: 'ask', label: 'AI Sahayak', to: '/ask', ready: true, group: 'Workspace' },
  { id: 'products', label: 'Biological Resource', to: '/products', ready: true, group: 'Workspace' },
  { id: 'tk-abs', label: 'TK & ABS', to: '/tk-abs', ready: true, group: 'Intelligence' },
  { id: 'documents', label: 'Documents', to: '/documents', ready: true, group: 'Records' },
  { id: 'my-cases', label: 'Cases', to: '/cases', ready: true, group: 'Records' },
]

const FACILITATOR_NAV: NavItem[] = [
  { id: 'dashboard', label: 'Dashboard', to: '/dashboard', ready: true, group: 'Workspace' },
  { id: 'cases', label: 'Case Queue', to: '/cases', ready: true, group: 'Workspace' },
  { id: 'my-cases', label: 'My Cases', to: '/cases?scope=mine', ready: true, group: 'Workspace' },
  { id: 'assessments', label: 'AI Assessments', to: '/assessments', ready: false, group: 'Intelligence' },
  { id: 'prior-art', label: 'Prior Art', to: '/prior-art', ready: false, group: 'Intelligence' },
  { id: 'documents', label: 'Documents', to: '/documents', ready: false, group: 'Records' },
  { id: 'communication', label: 'Communication', to: '/communication', ready: false, group: 'Records' },
  { id: 'reports', label: 'Reports', to: '/reports', ready: false, group: 'Records' },
  { id: 'sources', label: 'Sources', to: '/sources', ready: false, group: 'Records' },
]

const EXPERT_NAV: NavItem[] = [
  { id: 'dashboard', label: 'Dashboard', to: '/dashboard', ready: true, group: 'Workspace' },
  { id: 'cases', label: 'Assigned Cases', to: '/cases', ready: true, group: 'Workspace' },
  { id: 'compliance', label: 'Compliance Reviews', to: '/cases?view=compliance', ready: true, group: 'Workspace' },
  { id: 'classify', label: 'Product Classification', to: '/classify', ready: false, group: 'Intelligence' },
  { id: 'assessments', label: 'AI Assessments', to: '/assessments', ready: false, group: 'Intelligence' },
  { id: 'documents', label: 'Documents', to: '/documents', ready: false, group: 'Records' },
  { id: 'communication', label: 'Communication', to: '/communication', ready: false, group: 'Records' },
  { id: 'reports', label: 'Reports', to: '/reports', ready: false, group: 'Records' },
  { id: 'sources', label: 'Sources', to: '/sources', ready: false, group: 'Records' },
]

const ADMIN_NAV: NavItem[] = [
  { id: 'dashboard', label: 'Dashboard', to: '/dashboard', ready: true, group: 'Workspace' },
  { id: 'admin', label: 'Users', to: '/admin', ready: true, group: 'Platform' },
  { id: 'organisations', label: 'Organisations', to: '/organisations', ready: false, group: 'Platform' },
  { id: 'products', label: 'Products', to: '/products-admin', ready: false, group: 'Platform' },
  { id: 'cases', label: 'Cases', to: '/cases', ready: true, group: 'Platform' },
  { id: 'knowledge', label: 'Knowledge Base', to: '/knowledge-base', ready: true, group: 'Intelligence' },
  { id: 'ai-quality', label: 'AI Quality', to: '/ai-quality', ready: false, group: 'Intelligence' },
  { id: 'analytics', label: 'Analytics', to: '/analytics', ready: false, group: 'Intelligence' },
  { id: 'languages', label: 'Languages', to: '/languages', ready: false, group: 'Governance' },
  { id: 'jurisdictions', label: 'Jurisdictions', to: '/jurisdictions', ready: false, group: 'Governance' },
  { id: 'audit', label: 'Audit Logs', to: '/audit-logs', ready: true, group: 'Governance' },
  { id: 'security', label: 'Security', to: '/security', ready: false, group: 'Governance' },
]

export function navForRole(role: UserRole, persona?: UserPersona | null): NavItem[] {
  if (role === 'admin') return ADMIN_NAV
  if (role === 'facilitator') return FACILITATOR_NAV
  if (role === 'regulatory_expert') return EXPERT_NAV
  if (role === 'user' && persona === 'practitioner_researcher') return RESEARCHER_NAV
  if (role === 'user' && persona === 'cultivator') return CULTIVATOR_NAV
  return USER_NAV
}

export function groupNav(items: NavItem[]): { group: string; items: NavItem[] }[] {
  const order: string[] = []
  const map = new Map<string, NavItem[]>()
  for (const item of items) {
    const g = item.group ?? 'Workspace'
    if (!map.has(g)) {
      map.set(g, [])
      order.push(g)
    }
    map.get(g)!.push(item)
  }
  return order.map((group) => ({ group, items: map.get(group)! }))
}
