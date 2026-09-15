import { useEffect, useState } from 'react'
import { conversationsApi, ConversationSummary } from '../api/conversationsApi'
import { ApiError } from '../api/http'

function relativeDate(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime()
  const diffMin = Math.round(diffMs / 60000)
  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHr = Math.round(diffMin / 60)
  if (diffHr < 24) return `${diffHr}h ago`
  const diffDay = Math.round(diffHr / 24)
  if (diffDay < 7) return `${diffDay}d ago`
  return new Date(iso).toLocaleDateString()
}

export function ChatHistorySidebar({
  activeConversationId,
  onSelect,
  onNewChat,
  refreshKey,
}: {
  activeConversationId: string | null
  onSelect: (conversationId: string) => void
  onNewChat: () => void
  // Bump this after a turn completes so a brand-new conversation (or a
  // retitled one) shows up without a manual refresh.
  refreshKey: number
}) {
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    conversationsApi
      .list()
      .then((list) => {
        if (!cancelled) setConversations(list)
      })
      .catch((err) => {
        if (!cancelled) setLoadError(err instanceof ApiError ? err.message : 'Could not load chat history.')
      })
    return () => {
      cancelled = true
    }
  }, [refreshKey])

  return (
    <div className="gov-panel flex max-h-[22rem] flex-col lg:max-h-none">
      <div className="border-b border-surface-border bg-surface-muted px-4 py-2 text-xs font-semibold uppercase tracking-wide text-ink-faint">
        Chat history
      </div>
      <div className="p-3">
        <button type="button" className="gov-btn-primary w-full !py-1.5 text-sm" onClick={onNewChat}>
          + New chat
        </button>
      </div>
      <div className="flex-1 space-y-1 overflow-y-auto px-3 pb-3" aria-label="Past conversations">
        {loadError && <p className="px-1 text-xs text-red-700">{loadError}</p>}
        {!loadError && conversations.length === 0 && (
          <p className="px-1 text-xs text-ink-faint">No past conversations yet.</p>
        )}
        {conversations.map((c) => (
          <button
            key={c.conversationId}
            type="button"
            onClick={() => onSelect(c.conversationId)}
            aria-current={c.conversationId === activeConversationId ? 'true' : undefined}
            className={`block w-full rounded-sm px-2 py-2 text-left text-sm ${
              c.conversationId === activeConversationId
                ? 'bg-saffron/15 text-navy'
                : 'text-ink hover:bg-surface-muted'
            }`}
          >
            <p className="truncate font-medium">{c.title}</p>
            <p className="text-xs text-ink-faint">{relativeDate(c.updated_at)}</p>
          </button>
        ))}
      </div>
    </div>
  )
}
