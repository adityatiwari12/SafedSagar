"""RBAC permission catalog and role->permission matrix.

Single source of truth for `app/authz/seed.py` (writes this into the
`roles`/`permissions`/`role_permissions` tables) and for any code that
needs to reference a role/permission name as a string constant instead
of a magic literal. See docs/product/rbac-full-implementation-spec.md
Sections 0 and 4 for the reasoning behind this exact set - this module
should stay a direct, unembellished transcription of that document's
Section 4 table, not diverge from it silently.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Roles (spec Section 0). `guest` is deliberately absent - unauthenticated
# access has no DB row and no role grant; it's handled by simply not
# requiring auth on public routes, not by a "guest" permission set.
# ---------------------------------------------------------------------------


class RoleName:
    USER = "user"
    FACILITATOR = "facilitator"
    LEGAL_EXPERT = "legal_expert"
    REGULATORY_EXPERT = "regulatory_expert"
    INSTITUTIONAL_ADMIN = "institutional_admin"
    MINISTRY_ADMIN = "ministry_admin"
    KB_MANAGER = "kb_manager"


ALL_ROLES = (
    RoleName.USER,
    RoleName.FACILITATOR,
    RoleName.LEGAL_EXPERT,
    RoleName.REGULATORY_EXPERT,
    RoleName.INSTITUTIONAL_ADMIN,
    RoleName.MINISTRY_ADMIN,
    RoleName.KB_MANAGER,
)

# Roles a caller may request at self-registration - never an admin tier,
# mirrors the legacy SELF_REGISTERABLE_ROLES in app.db.models (kept in
# sync manually since the legacy set is enum-typed, this one is not).
# `legal_expert` is deliberately NOT self-registerable, unlike
# facilitator/regulatory_expert: it reviews escalated/high-risk/
# ambiguous/ABS-sensitive/sensitive-TK cases specifically because they
# need a higher bar than routine review, and self-registration here
# currently activates *immediately* (the admin-verification gate is
# disabled for this hackathon build, app/auth/router.py) - granting that
# authority to anyone who checks a box would undercut "expert review is
# required for high-risk cases" rather than serve it. Provisioned only
# (by a ministry_admin, once that endpoint exists - Phase 1 seeds no
# users into it).
SELF_REGISTERABLE_ROLE_NAMES = frozenset({RoleName.USER, RoleName.FACILITATOR, RoleName.REGULATORY_EXPERT})

ROLE_DESCRIPTIONS: dict[str, str] = {
    RoleName.USER: "Practitioner, researcher, AYUSH startup/MSME, or TK holder/cultivator (persona-differentiated, not permission-differentiated).",
    RoleName.FACILITATOR: "Reviews routine, non-escalated IP cases.",
    RoleName.LEGAL_EXPERT: "Reviews only escalated/high-risk/ambiguous/complex-international/ABS-sensitive/sensitive-TK cases.",
    RoleName.REGULATORY_EXPERT: "Reviews regulatory-compliance cases (AYUSH/FSSAI/Drugs & Cosmetics).",
    RoleName.INSTITUTIONAL_ADMIN: "Administers one organization's users/cases - org-scoped, not platform-wide.",
    RoleName.MINISTRY_ADMIN: "Platform-wide governance: users, organizations, roles, configuration, aggregate analytics.",
    RoleName.KB_MANAGER: "Owns the RAG knowledge corpus - sources, ingestion, versioning, metadata.",
}

# ---------------------------------------------------------------------------
# Permissions (spec Section 4).
# ---------------------------------------------------------------------------


class Permission:
    AI_ASK = "ai.ask"
    AI_TRANSLATE = "ai.translate"
    AI_VIEW_SOURCES = "ai.view_sources"
    AI_VIEW_CITATIONS = "ai.view_citations"
    AI_VIEW_REASONING = "ai.view_reasoning"

    CASE_CREATE = "case.create"
    CASE_VIEW_OWN = "case.view_own"
    CASE_VIEW_QUEUE = "case.view_queue"
    CASE_EDIT = "case.edit"
    CASE_ASSIGN = "case.assign"
    CASE_ESCALATE = "case.escalate"
    CASE_CLOSE = "case.close"

    PRODUCT_CREATE = "product.create"
    PRODUCT_VIEW = "product.view"
    PRODUCT_EDIT = "product.edit"
    PRODUCT_DELETE = "product.delete"

    RESEARCH_CREATE = "research.create"
    RESEARCH_SEARCH_PRIOR_ART = "research.search_prior_art"
    RESEARCH_SAVE_EVIDENCE = "research.save_evidence"
    RESEARCH_EXPORT = "research.export"

    TK_CREATE = "tk.create"
    TK_VIEW_OWN = "tk.view_own"
    TK_VIEW_ASSIGNED = "tk.view_assigned"
    TK_VIEW_PUBLIC = "tk.view_public"
    TK_EDIT = "tk.edit"
    TK_SET_VISIBILITY = "tk.set_visibility"

    REVIEW_VIEW = "review.view"
    REVIEW_APPROVE = "review.approve"
    REVIEW_MODIFY = "review.modify"
    REVIEW_REJECT = "review.reject"
    REVIEW_ESCALATE = "review.escalate"

    SOURCE_CREATE = "source.create"
    SOURCE_EDIT = "source.edit"
    SOURCE_VERIFY = "source.verify"
    SOURCE_DEPRECATE = "source.deprecate"
    SOURCE_PUBLISH = "source.publish"

    ORG_CREATE = "org.create"
    ORG_VIEW = "org.view"
    ORG_MANAGE_MEMBERS = "org.manage_members"

    USERS_MANAGE = "users.manage"
    ROLES_MANAGE = "roles.manage"
    PERMISSIONS_MANAGE = "permissions.manage"
    ORGANIZATIONS_MANAGE = "organizations.manage"
    SYSTEM_CONFIGURE = "system.configure"
    AUDIT_VIEW = "audit.view"

    ANALYTICS_PERSONAL = "analytics.personal"
    ANALYTICS_ORGANIZATION = "analytics.organization"
    ANALYTICS_NATIONAL = "analytics.national"

    DOCUMENT_CREATE = "document.create"
    DOCUMENT_VIEW = "document.view"
    DOCUMENT_DELETE = "document.delete"


# (key, resource, action, description) - what gets seeded into `permissions`.
PERMISSION_CATALOG: list[tuple[str, str, str, str]] = [
    (Permission.AI_ASK, "ai", "ask", "Ask the assistant a question."),
    (Permission.AI_TRANSLATE, "ai", "translate", "Use the translation/multilingual layer."),
    (Permission.AI_VIEW_SOURCES, "ai", "view_sources", "View retrieved source chunks behind an answer."),
    (Permission.AI_VIEW_CITATIONS, "ai", "view_citations", "View validated citations on an answer."),
    (Permission.AI_VIEW_REASONING, "ai", "view_reasoning", "View the AI's classification/routing/confidence detail."),
    (Permission.CASE_CREATE, "case", "create", "Create a new case from a question."),
    (Permission.CASE_VIEW_OWN, "case", "view_own", "View one's own cases."),
    (Permission.CASE_VIEW_QUEUE, "case", "view_queue", "View a review queue's cases."),
    (Permission.CASE_EDIT, "case", "edit", "Correct classification/answer on a case."),
    (Permission.CASE_ASSIGN, "case", "assign", "Claim/assign a case."),
    (Permission.CASE_ESCALATE, "case", "escalate", "Escalate a case to a review queue."),
    (Permission.CASE_CLOSE, "case", "close", "Close a case."),
    (Permission.PRODUCT_CREATE, "product", "create", "Create a product/formulation record."),
    (Permission.PRODUCT_VIEW, "product", "view", "View a product/formulation record."),
    (Permission.PRODUCT_EDIT, "product", "edit", "Edit a product/formulation record."),
    (Permission.PRODUCT_DELETE, "product", "delete", "Delete a product/formulation record."),
    (Permission.RESEARCH_CREATE, "research", "create", "Create a research project."),
    (Permission.RESEARCH_SEARCH_PRIOR_ART, "research", "search_prior_art", "Run a prior-art/patent/TK search."),
    (Permission.RESEARCH_SAVE_EVIDENCE, "research", "save_evidence", "Save a source into an evidence workspace."),
    (Permission.RESEARCH_EXPORT, "research", "export", "Export an evidence report."),
    (Permission.TK_CREATE, "tk", "create", "Create a traditional-knowledge record."),
    (Permission.TK_VIEW_OWN, "tk", "view_own", "View one's own TK records."),
    (Permission.TK_VIEW_ASSIGNED, "tk", "view_assigned", "View a TK record one has been explicitly granted access to."),
    (Permission.TK_VIEW_PUBLIC, "tk", "view_public", "View a TK record marked public."),
    (Permission.TK_EDIT, "tk", "edit", "Edit a TK record."),
    (Permission.TK_SET_VISIBILITY, "tk", "set_visibility", "Change a TK record's visibility tier."),
    (Permission.REVIEW_VIEW, "review", "view", "View an expert review."),
    (Permission.REVIEW_APPROVE, "review", "approve", "Approve a case's AI answer as final guidance."),
    (Permission.REVIEW_MODIFY, "review", "modify", "Modify/replace a case's answer."),
    (Permission.REVIEW_REJECT, "review", "reject", "Reject a case's AI answer."),
    (Permission.REVIEW_ESCALATE, "review", "escalate", "Escalate a case to a higher review tier."),
    (Permission.SOURCE_CREATE, "source", "create", "Add a new knowledge-base source."),
    (Permission.SOURCE_EDIT, "source", "edit", "Edit a knowledge-base source's metadata/content."),
    (Permission.SOURCE_VERIFY, "source", "verify", "Mark a source's last-verified date/status."),
    (Permission.SOURCE_DEPRECATE, "source", "deprecate", "Mark a source superseded."),
    (Permission.SOURCE_PUBLISH, "source", "publish", "Publish a source into the live RAG index."),
    (Permission.ORG_CREATE, "org", "create", "Create an organization."),
    (Permission.ORG_VIEW, "org", "view", "View an organization's profile."),
    (Permission.ORG_MANAGE_MEMBERS, "org", "manage_members", "Add/remove an organization's members."),
    (Permission.USERS_MANAGE, "users", "manage", "View/edit/suspend user accounts."),
    (Permission.ROLES_MANAGE, "roles", "manage", "Create/edit/delete roles."),
    (Permission.PERMISSIONS_MANAGE, "permissions", "manage", "Edit role->permission grants."),
    (Permission.ORGANIZATIONS_MANAGE, "organizations", "manage", "Create/edit organizations platform-wide."),
    (Permission.SYSTEM_CONFIGURE, "system", "configure", "Change platform configuration (models, flags, languages)."),
    (Permission.AUDIT_VIEW, "audit", "view", "View audit log entries."),
    (Permission.ANALYTICS_PERSONAL, "analytics", "personal", "View one's own usage analytics."),
    (Permission.ANALYTICS_ORGANIZATION, "analytics", "organization", "View aggregate analytics for one's organization."),
    (Permission.ANALYTICS_NATIONAL, "analytics", "national", "View platform-wide aggregate analytics."),
    (Permission.DOCUMENT_CREATE, "document", "create", "Upload a document."),
    (Permission.DOCUMENT_VIEW, "document", "view", "View/list/download a document's metadata or bytes."),
    (Permission.DOCUMENT_DELETE, "document", "delete", "Soft-delete a document and its stored bytes."),
]

# ---------------------------------------------------------------------------
# Role -> permission grants (spec Section 4 table, corrected per the two
# fixes noted in that section: ai.* is universal; admin tiers never get
# case.view_queue or review.approve/modify/reject).
# ---------------------------------------------------------------------------

_AI_PERMISSIONS = {
    Permission.AI_ASK,
    Permission.AI_TRANSLATE,
    Permission.AI_VIEW_SOURCES,
    Permission.AI_VIEW_CITATIONS,
    Permission.AI_VIEW_REASONING,
}

ROLE_PERMISSIONS: dict[str, set[str]] = {
    RoleName.USER: _AI_PERMISSIONS
    | {
        Permission.CASE_CREATE,
        Permission.CASE_VIEW_OWN,
        Permission.CASE_ESCALATE,
        Permission.PRODUCT_CREATE,
        Permission.PRODUCT_VIEW,
        Permission.PRODUCT_EDIT,
        Permission.PRODUCT_DELETE,
        Permission.RESEARCH_CREATE,
        Permission.RESEARCH_SEARCH_PRIOR_ART,
        Permission.RESEARCH_SAVE_EVIDENCE,
        Permission.RESEARCH_EXPORT,
        Permission.TK_CREATE,
        Permission.TK_VIEW_OWN,
        Permission.TK_EDIT,
        Permission.TK_SET_VISIBILITY,
        # Section 4a: scoped by can_access_resource to orgs the caller is
        # already a member of - never a blanket admin-like grant.
        Permission.ORG_MANAGE_MEMBERS,
        Permission.ANALYTICS_PERSONAL,
        Permission.DOCUMENT_CREATE,
        Permission.DOCUMENT_VIEW,
        Permission.DOCUMENT_DELETE,
    },
    RoleName.FACILITATOR: _AI_PERMISSIONS
    | {
        Permission.CASE_VIEW_QUEUE,
        Permission.CASE_EDIT,
        Permission.CASE_ASSIGN,
        Permission.CASE_ESCALATE,
        Permission.CASE_CLOSE,
        Permission.TK_VIEW_ASSIGNED,
        Permission.REVIEW_VIEW,
        Permission.REVIEW_APPROVE,
        Permission.REVIEW_MODIFY,
        Permission.REVIEW_REJECT,
        Permission.REVIEW_ESCALATE,
    },
    RoleName.LEGAL_EXPERT: _AI_PERMISSIONS
    | {
        Permission.CASE_VIEW_QUEUE,
        Permission.CASE_EDIT,
        Permission.CASE_ASSIGN,
        Permission.CASE_CLOSE,
        Permission.TK_VIEW_ASSIGNED,
        Permission.REVIEW_VIEW,
        Permission.REVIEW_APPROVE,
        Permission.REVIEW_MODIFY,
        Permission.REVIEW_REJECT,
    },
    RoleName.REGULATORY_EXPERT: _AI_PERMISSIONS
    | {
        Permission.CASE_VIEW_QUEUE,
        Permission.CASE_EDIT,
        Permission.CASE_ASSIGN,
        Permission.CASE_ESCALATE,
        Permission.CASE_CLOSE,
        Permission.REVIEW_VIEW,
        Permission.REVIEW_APPROVE,
        Permission.REVIEW_MODIFY,
        Permission.REVIEW_REJECT,
        Permission.REVIEW_ESCALATE,
    },
    RoleName.INSTITUTIONAL_ADMIN: _AI_PERMISSIONS
    | {
        Permission.ORG_VIEW,
        Permission.ORG_MANAGE_MEMBERS,
        Permission.USERS_MANAGE,
        Permission.AUDIT_VIEW,
        Permission.ANALYTICS_ORGANIZATION,
    },
    RoleName.MINISTRY_ADMIN: _AI_PERMISSIONS
    | {
        Permission.ORG_CREATE,
        Permission.ORG_VIEW,
        Permission.ORG_MANAGE_MEMBERS,
        Permission.ORGANIZATIONS_MANAGE,
        Permission.USERS_MANAGE,
        Permission.ROLES_MANAGE,
        Permission.PERMISSIONS_MANAGE,
        Permission.SYSTEM_CONFIGURE,
        Permission.AUDIT_VIEW,
        Permission.ANALYTICS_ORGANIZATION,
        Permission.ANALYTICS_NATIONAL,
    },
    RoleName.KB_MANAGER: _AI_PERMISSIONS
    | {
        Permission.SOURCE_CREATE,
        Permission.SOURCE_EDIT,
        Permission.SOURCE_VERIFY,
        Permission.SOURCE_DEPRECATE,
        Permission.SOURCE_PUBLISH,
        Permission.AUDIT_VIEW,
        Permission.ANALYTICS_NATIONAL,
    },
}

# Invariant asserted by tests/test_authz_matrix.py: no admin-tier role
# (institutional_admin/ministry_admin/kb_manager) may hold review.approve/
# modify/reject - system administration must never double as legal
# decision-making (spec Sections 0 and 8).
ADMIN_TIER_ROLES = (RoleName.INSTITUTIONAL_ADMIN, RoleName.MINISTRY_ADMIN, RoleName.KB_MANAGER)
_FORBIDDEN_FOR_ADMIN_TIERS = {Permission.REVIEW_APPROVE, Permission.REVIEW_MODIFY, Permission.REVIEW_REJECT}
for _role in ADMIN_TIER_ROLES:
    _granted = ROLE_PERMISSIONS[_role]
    _violations = _granted & _FORBIDDEN_FOR_ADMIN_TIERS
    if _violations:
        raise AssertionError(
            f"role {_role!r} must never hold {_violations} - "
            "admin tiers cannot approve/modify/reject legal guidance (spec Section 0)"
        )
