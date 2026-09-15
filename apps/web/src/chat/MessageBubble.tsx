import { ReactNode } from 'react'

export function MessageBubble({
  role,
  children,
}: {
  role: 'user' | 'assistant'
  children: ReactNode
}) {
  const isUser = role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[min(100%,42rem)] rounded-sm px-4 py-3 text-sm leading-relaxed shadow-panel ${
          isUser
            ? 'bg-saffron text-white'
            : 'border border-surface-border bg-white text-ink'
        }`}
      >
        <p className={`mb-1 text-xs font-bold uppercase tracking-wide ${isUser ? 'text-white/80' : 'text-ink-faint'}`}>
          {isUser ? 'You' : 'Sahayak'}
        </p>
        {children}
      </div>
    </div>
  )
}
