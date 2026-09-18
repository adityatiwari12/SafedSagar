import { ReactNode } from 'react'

export function MessageBubble({
  role,
  children,
}: {
  role: 'user' | 'assistant'
  children: ReactNode
}) {
  const isUser = role === 'user'

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[min(85%,42rem)] rounded-2xl rounded-br-md bg-saffron px-4 py-2.5 text-sm leading-relaxed text-white shadow-panel">
          {children}
        </div>
      </div>
    )
  }

  return (
    <div className="flex justify-start gap-3">
      <div
        aria-hidden="true"
        className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-forest text-[0.7rem] font-bold text-white"
      >
        S
      </div>
      <div className="min-w-0 max-w-[min(100%,44rem)] flex-1 text-sm leading-relaxed text-ink">
        <p className="mb-1 text-xs font-bold uppercase tracking-wide text-ink-faint">Sahayak</p>
        {children}
      </div>
    </div>
  )
}
