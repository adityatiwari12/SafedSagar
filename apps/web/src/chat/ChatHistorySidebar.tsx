import { MouseEvent, useEffect, useState } from 'react'
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
  onDeleted,
  refreshKey,
}: {
  activeConversationId: string | null
  onSelect: (conversationId: string) => void
  onNewChat: () => void
  // Called after a conversation is deleted, only when it was the active
  // one - lets the parent reset session state instead of pointing at a
  // conversation that no longer exists.
  onDeleted?: (conversationId: string) => void
  // Bump this after a turn completes so a brand-new conversation (or a
  // retitled one) shows up without a manual refresh.
  refreshKey: number
}) {
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

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

  async function handleDelete(e: MouseEvent, conversationId: string) {
    e.stopPropagation()
    if (!window.confirm('Delete this conversation? This cannot be undone.')) return
    setDeletingId(conversationId)
    try {
      await conversationsApi.remove(conversationId)
      setConversations((prev) => prev.filter((c) => c.conversationId !== conversationId))
      if (conversationId === activeConversationId) onDeleted?.(conversationId)
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : 'Could not delete that conversation.')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="gov-panel flex h-full min-h-0 flex-col">
      <div className="shrink-0 border-b border-surface-border bg-surface-muted px-4 py-2 text-xs font-semibold uppercase tracking-wide text-ink-faint">
        Chat history
      </div>
      <div className="shrink-0 p-3">
        <button type="button" className="gov-btn-primary w-full !py-1.5 text-sm" onClick={onNewChat}>
          + New chat
        </button>
      </div>
      <div
        className="scroll-thin min-h-0 flex-1 space-y-0.5 overflow-y-auto px-3 pb-3"
        aria-label="Past conversations"
      >
        {loadError && <p className="px-1 text-xs text-red-700">{loadError}</p>}
        {!loadError && conversations.length === 0 && (
          <p className="px-1 text-xs text-ink-faint">No past conversations yet.</p>
        )}
        {conversations.map((c) => (
          <div
            key={c.conversationId}
            className={`group flex items-start rounded-lg ${
              c.conversationId === activeConversationId ? 'bg-saffron/12' : 'hover:bg-surface-muted'
            }`}
          >
            <button
              type="button"
              onClick={() => onSelect(c.conversationId)}
              aria-current={c.conversationId === activeConversationId ? 'true' : undefined}
              className={`min-w-0 flex-1 px-2.5 py-2 text-left text-sm ${
                c.conversationId === activeConversationId ? 'text-navy' : 'text-ink'
              }`}
            >
              <p className="truncate font-medium leading-tight">{c.title}</p>
              <p className="text-xs text-ink-faint">{relativeDate(c.updated_at)}</p>
            </button>
            <button
              type="button"
              onClick={(e) => void handleDelete(e, c.conversationId)}
              disabled={deletingId === c.conversationId}
              aria-label={`Delete conversation: ${c.title}`}
              title="Delete conversation"
              className="mr-1 mt-2 shrink-0 rounded-md px-1.5 py-0.5 text-xs text-ink-faint opacity-0 hover:bg-red-100 hover:text-red-700 focus:opacity-100 group-hover:opacity-100 disabled:opacity-50"
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
