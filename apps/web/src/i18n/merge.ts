import type { Messages } from './types'

/** Deep-merge `patch` onto `base` (objects only; arrays/primitives replaced). */
export function mergeMessages(base: Messages, patch: DeepPartial<Messages>): Messages {
  const out = structuredClone(base)
  mergeInto(out as unknown as Record<string, unknown>, patch as Record<string, unknown>)
  return out
}

type DeepPartial<T> = {
  [K in keyof T]?: T[K] extends object ? DeepPartial<T[K]> : T[K]
}

function mergeInto(target: Record<string, unknown>, patch: Record<string, unknown>) {
  for (const [key, value] of Object.entries(patch)) {
    if (value === undefined) continue
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      const cur = target[key]
      if (cur && typeof cur === 'object' && !Array.isArray(cur)) {
        mergeInto(cur as Record<string, unknown>, value as Record<string, unknown>)
      } else {
        target[key] = structuredClone(value)
      }
    } else {
      target[key] = value
    }
  }
}

export type { DeepPartial }
