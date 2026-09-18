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
import { LanguageSelectCard } from '../i18n/LanguageSelectCard'

export default function LandingPage() {
  return (
    <PortalChrome>
      <Hero />
      <div className="bg-ivory px-4 py-10 lg:px-8">
        <div className="mx-auto max-w-portal">
          <LanguageSelectCard />
        </div>
      </div>
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
