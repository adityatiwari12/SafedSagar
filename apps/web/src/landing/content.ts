export const NAV_LINKS = [
  { href: '/', label: 'Home' },
  { href: '#about', label: 'About' },
  { href: '#services', label: 'Services' },
  { href: '#ip-ayurveda', label: 'IP & Ayurveda' },
  { href: '#knowledge', label: 'Knowledge Centre' },
  { href: '#resources', label: 'Resources' },
  { href: '#faq', label: 'FAQ' },
  { href: '#contact', label: 'Contact' },
] as const

export const USER_GROUPS = [
  {
    title: 'AYUSH Practitioners',
    blurb: 'Clarify IP and regulatory questions when formulating or advising on Ayurvedic products.',
  },
  {
    title: 'Researchers',
    blurb: 'Map traditional knowledge, prior art and biodiversity considerations to published sources.',
  },
  {
    title: 'AYUSH Startups & MSMEs',
    blurb: 'Identify suitable protection paths for brands, formulations and go-to-market compliance.',
  },
  {
    title: 'Cultivators',
    blurb: 'Understand ABS and biological resource obligations tied to cultivation and access.',
  },
  {
    title: 'Manufacturers',
    blurb: 'Navigate AYUSH, FSSAI and IP requirements across product categories.',
  },
  {
    title: 'Exporters',
    blurb: 'Separate India domestic rules from international IP and ABS frameworks before export.',
  },
] as const

export const SERVICES = [
  'Patents',
  'Trademarks',
  'Geographical Indications',
  'Copyright',
  'Designs',
  'Trade Secrets',
  'Traditional Knowledge',
  'Biodiversity & ABS',
  'Ayurveda Regulatory Guidance',
  'International IP & Regulatory Guidance',
  'Prior-Art Assistance',
] as const

export const HOW_IT_WORKS = [
  {
    step: 'Ask',
    detail: 'Describe an invention, formulation or regulatory question.',
  },
  {
    step: 'Classify',
    detail: 'Identify product category, IP type and jurisdiction.',
  },
  {
    step: 'Retrieve',
    detail: 'Retrieve relevant authoritative sources from the corpus.',
  },
  {
    step: 'Verify',
    detail: 'Validate evidence and citations against retrieved text.',
  },
  {
    step: 'Guide',
    detail: 'Receive structured guidance with sources, confidence and limits.',
  },
] as const

export const SOURCES = [
  { authority: 'IP India', type: 'Statutes & rules', focus: 'Patents, trademarks, GI, designs' },
  { authority: 'Ministry of Ayush', type: 'Standards & guidance', focus: 'AYUSH product pathways' },
  { authority: 'National Biodiversity Authority', type: 'Statute & ABS', focus: 'Biological Diversity Act / ABS' },
  { authority: 'FSSAI', type: 'Regulations', focus: 'Ayurveda Aahara food rules' },
  { authority: 'WIPO', type: 'Treaties', focus: 'PCT, Paris, Budapest, GRATK' },
  { authority: 'WTO / TRIPS', type: 'Treaty', focus: 'Trade-related IP standards' },
  { authority: 'CBD Secretariat', type: 'Treaty', focus: 'Convention on Biological Diversity' },
  { authority: 'Nagoya Protocol', type: 'Treaty', focus: 'Access and benefit-sharing' },
  { authority: 'Official registries', type: 'Public records', focus: 'IPO / registry lookups (rate-limited)' },
] as const

export const SAMPLE_QUESTIONS = [
  'Can I patent a classical Ayurvedic formulation?',
  'What IP protection is suitable for my herbal brand?',
  'Does my product involve biodiversity or ABS requirements?',
  'What should I consider before exporting an Ayurvedic product?',
] as const

export const LANGUAGES = ['English', 'हिन्दी'] as const

export const KNOWLEDGE_CARDS = [
  { title: 'Acts & Rules', blurb: 'Indian IP and biodiversity statutes used in retrieval.' },
  { title: 'Regulations & Notifications', blurb: 'AYUSH and FSSAI regulatory instruments in the corpus.' },
  { title: 'International Frameworks', blurb: 'TRIPS, PCT, CBD, Nagoya and related texts.' },
  { title: 'Traditional Knowledge', blurb: 'TK awareness pointers — TKDL is not retrieved live.' },
  { title: 'Prior Art', blurb: 'Guidance on searching known uses before filing.' },
  { title: 'Official Registries', blurb: 'Pointers to public IPO and related registry interfaces.' },
] as const

/** Demo notifications — clearly marked; not official gazette entries. */
export const LATEST_UPDATES = [
  {
    date: '2026-09-15',
    category: 'Corpus',
    title: 'Wave A sources loaded for patents, ABS, Ayurveda Aahara and key treaties',
  },
  {
    date: '2026-09-15',
    category: 'Product',
    title: 'Citizen portal and Ask IP-SAKTI journey available for demonstration',
  },
  {
    date: '2026-05-24',
    category: 'Treaty note',
    title: 'WIPO GRATK Treaty presented as signed, not yet in force',
  },
] as const

export const INDIA_TOPICS = [
  'Patents',
  'Geographical Indications',
  'Trademarks',
  'AYUSH regulations',
  'Biodiversity / ABS',
  'FSSAI',
  'Traditional Knowledge',
] as const

export const INTERNATIONAL_TOPICS = [
  'WIPO frameworks',
  'TRIPS',
  'PCT',
  'CBD',
  'Nagoya Protocol',
  'Country-specific requirements',
] as const
