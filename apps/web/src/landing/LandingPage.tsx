import { PortalChrome } from './PortalChrome'
import { Hero } from './Hero'
import {
  InnovationArc,
  Personas,
  ServiceGroups,
  HowItWorks,
  FiveLayers,
  SourceGrounded,
  JurisdictionSplit,
  Multilingual,
  AskImmersive,
  KnowledgeCentre,
  LatestUpdates,
  DisclaimerFaq,
} from './sections'

export default function LandingPage() {
  return (
    <PortalChrome>
      <Hero />
      <InnovationArc />
      <Personas />
      <ServiceGroups />
      <HowItWorks />
      <FiveLayers />
      <SourceGrounded />
      <JurisdictionSplit />
      <Multilingual />
      <AskImmersive />
      <KnowledgeCentre />
      <LatestUpdates />
      <DisclaimerFaq />
    </PortalChrome>
  )
}
