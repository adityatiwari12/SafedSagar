/** State Emblem of India — Wikimedia Commons SVG (public domain / GOI work). */
export function StateEmblem({ className = 'h-16 w-auto' }: { className?: string }) {
  return (
    <img
      src="/emblem-of-india.svg"
      alt="State Emblem of India"
      className={className}
      width={72}
      height={96}
      decoding="async"
    />
  )
}
