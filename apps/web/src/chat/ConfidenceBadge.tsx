import { ChatTurnResponse } from '../api/chatApi'
import { ConfidenceBadge as UiConfidenceBadge } from '../ui/primitives'

export function ConfidenceBadge({
  band,
  confidence,
}: {
  band: ChatTurnResponse['confidence_band']
  confidence: number
}) {
  return <UiConfidenceBadge band={band} confidence={confidence} />
}
