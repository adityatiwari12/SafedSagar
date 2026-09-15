import { FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

const PERSONAS = [
  {
    title: 'Practitioners',
    image: '/media-chyawanprash.webp',
    copy: 'Clarify classical vs proprietary routes, documentation needs and regulatory framing before you advise or formulate.',
  },
  {
    title: 'Researchers',
    image: '/media-herbs-1.jpg',
    copy: 'Map prior-art awareness, traditional-knowledge pointers and jurisdiction before you publish or file.',
  },
  {
    title: 'AYUSH Startups & MSMEs',
    image: '/media-ayurveda-3.jpg',
    copy: 'Identify protection and compliance pathways while product and market choices are still inexpensive to change.',
  },
  {
    title: 'Manufacturers',
    image: '/media-herbs-2.jpg',
    copy: 'Navigate AYUSH, FSSAI and IP requirements across product categories without mixing India and export rules.',
  },
  {
    title: 'Cultivators',
    image: '/media-herbs-1.jpg',
    copy: 'Understand ABS and biological-resource obligations tied to cultivation, access and commercial supply.',
  },
  {
    title: 'Exporters',
    image: '/media-ayurveda-3.jpg',
    copy: 'Separate domestic ABS/IP duties from destination-market frameworks before market entry.',
  },
] as const

const PROTECT = ['Patents', 'Trademarks', 'GI', 'Copyright', 'Designs', 'Trade Secrets']
const COMPLY = ['Ayurveda Regulation', 'Biodiversity', 'ABS', 'Traditional Knowledge', 'FSSAI']
const EXPAND = ['International IP', 'PCT', 'WIPO', 'TRIPS', 'Country-specific requirements']

const PROCESS = [
  { n: '01', title: 'Ask', detail: 'Describe an invention, formulation or regulatory question.' },
  { n: '02', title: 'Classify', detail: 'Identify product category, IP type and jurisdiction.' },
  { n: '03', title: 'Retrieve', detail: 'Hybrid retrieval across statutes, rules, treaties and cases.' },
  { n: '04', title: 'Verify', detail: 'Mechanical citation validation against retrieved chunks.' },
  { n: '05', title: 'Guide', detail: 'Structured answer with confidence, limits and next steps.' },
] as const

const PIPELINE = [
  'User',
  'Question understanding',
  'Product classification',
  'Jurisdiction routing',
  'Hybrid retrieval',
  'Reasoning',
  'Citation validation',
  'Answer',
]

const LAYERS = [
  {
    n: '01',
    title: 'Product classification',
    body: 'Classical / Proprietary / New composition — sets which statute cluster is relevant.',
  },
  {
    n: '02',
    title: 'IP analysis',
    body: 'Patent, GI, trademark or TK pathway — routed without conflating brand and patentability.',
  },
  {
    n: '03',
    title: 'Regulatory analysis',
    body: 'AYUSH, FSSAI or drug framing — kept distinct from filing strategy.',
  },
  {
    n: '04',
    title: 'Biodiversity & ABS',
    body: 'Biological resources and traditional-knowledge signals that may trigger NBA pathways.',
  },
  {
    n: '05',
    title: 'Evidence',
    body: 'Law → section → source → citation — only claims supported by retrieved text survive.',
  },
] as const

const CLAIMS = [
  {
    id: '1',
    claim: 'Classical formulations may face specific patentability limitations.',
    source: 'Patents Act, 1970',
    section: 'Section 3(p)',
    authority: 'Government of India',
  },
  {
    id: '2',
    claim: 'Commercial use of Indian biological resources can require NBA approval.',
    source: 'Biological Diversity Act',
    section: 'ABS pathway',
    authority: 'National Biodiversity Authority',
  },
  {
    id: '3',
    claim: 'Ayurveda Aahara products follow FSSAI food rules — not drug claims by default.',
    source: 'Ayurveda Aahara Regulations, 2022',
    section: 'Food pathway',
    authority: 'FSSAI',
  },
] as const

const SCRIPTS = ['हिन्दी', 'English', 'मराठी', 'ગુજરાતી', 'বাংলা', 'தமிழ்', 'తెలుగు', 'ಕನ್ನಡ', 'മലയാളം', 'ਪੰਜਾਬੀ']

const DOCS = [
  { title: 'Acts & Rules', authority: 'IP India / NBA', type: 'Statute', jurisdiction: 'India', version: 'Corpus Wave A' },
  { title: 'Regulations', authority: 'FSSAI / Ayush', type: 'Regulation', jurisdiction: 'India', version: '2022+' },
  { title: 'Notifications', authority: 'Demo index', type: 'Notice', jurisdiction: 'India', version: 'DEMO' },
  { title: 'International Frameworks', authority: 'WIPO / WTO / CBD', type: 'Treaty', jurisdiction: 'International', version: 'Curated' },
  { title: 'Traditional Knowledge', authority: 'TK awareness', type: 'Pointer', jurisdiction: 'India', version: 'Non-retrieval' },
  { title: 'Prior Art', authority: 'Corpus + registries', type: 'Guidance', jurisdiction: 'Both', version: 'MVP' },
  { title: 'Official Registries', authority: 'IPO interfaces', type: 'Registry', jurisdiction: 'India', version: 'Pointers' },
] as const

const UPDATES = [
  { date: '2026-09-15', category: 'Corpus', title: 'Wave A IP / ABS / treaty sources loaded for demonstration', demo: true },
  { date: '2026-08-20', category: 'Product', title: 'Ask journey with citation validation available', demo: true },
  { date: '2026-05-24', category: 'Treaty note', title: 'GRATK presented as signed, not yet in force', demo: true },
] as const

const SUGGESTIONS = [
  'Can I patent a classical Ayurvedic formulation?',
  'What IP protection fits my herbal brand?',
  'Does my product trigger biodiversity / ABS considerations?',
  'What should I consider before exporting?',
]

export function InnovationArc() {
  const steps = ['Traditional knowledge', 'Formulation', 'Innovation', 'Intellectual property', 'Commercialisation']
  return (
    <section id="about" className="bg-ivory py-20 lg:py-28">
      <div className="mx-auto grid max-w-portal gap-12 px-4 lg:grid-cols-12 lg:gap-10 lg:px-8">
        <div className="lg:col-span-7">
          <h2 className="text-section text-forest">
            From Ayurveda knowledge
            <br />
            to responsible innovation.
          </h2>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-ink-muted">
            Ayurveda sits where living traditional knowledge, biological resources and modern
            products meet. Those intersections create interlocking IP and regulatory duties.
          </p>
          <p className="mt-8 max-w-xl border-l-4 border-saffron bg-white px-5 py-4 text-lg font-semibold leading-snug text-forest">
            IP-SAKTI connects the legal, regulatory and knowledge layers behind Ayurveda innovation.
          </p>
        </div>
        <div className="relative lg:col-span-5">
          <img
            src="/media-chyawanprash.webp"
            alt=""
            className="absolute inset-0 h-full w-full object-cover opacity-20"
          />
          <ol className="relative space-y-0 border border-surface-border bg-white/90 p-6 backdrop-blur-[1px]">
            {steps.map((s, i) => (
              <li key={s} className="flex items-start gap-4 py-3">
                <span className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full bg-saffron" />
                <div>
                  <p className="text-lg font-bold text-forest">{s}</p>
                  {i < steps.length - 1 && (
                    <p className="mt-1 text-saffron" aria-hidden="true">
                      →
                    </p>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  )
}

export function Personas() {
  return (
    <section className="bg-white py-20 lg:py-28">
      <div className="mx-auto max-w-portal px-4 lg:px-8">
        <h2 className="text-section text-forest">Who is IP-SAKTI for?</h2>
        <p className="mt-4 max-w-2xl text-lg text-ink-muted">
          One citizen-facing service covering the people who move Ayurveda from knowledge to market.
        </p>
        <div className="mt-14 space-y-12">
          {PERSONAS.map((p, i) => {
            const reverse = i % 2 === 1
            return (
              <article
                key={p.title}
                className={`grid overflow-hidden border border-surface-border lg:grid-cols-12 ${
                  reverse ? 'lg:[&>div:first-child]:order-2' : ''
                }`}
              >
                <div className="relative min-h-[260px] lg:col-span-5">
                  <img src={p.image} alt="" className="absolute inset-0 h-full w-full object-cover" />
                  <div className="absolute inset-0 bg-forest/45" />
                  <p className="absolute bottom-5 left-5 text-2xl font-extrabold text-white sm:text-3xl">
                    {p.title}
                  </p>
                </div>
                <div className="flex flex-col justify-center bg-ivory px-6 py-10 lg:col-span-7 lg:px-12">
                  <p className="max-w-xl text-lg leading-relaxed text-ink-muted sm:text-xl">{p.copy}</p>
                  <Link to="/ask" className="gov-btn-primary mt-8 w-fit">
                    Ask for this context
                  </Link>
                </div>
              </article>
            )
          })}
        </div>
      </div>
    </section>
  )
}

export function ServiceGroups() {
  return (
    <section id="services" className="bg-ivory py-20 lg:py-28">
      <div className="mx-auto max-w-portal px-4 lg:px-8">
        <h2 className="text-section text-forest">What can IP-SAKTI help navigate?</h2>
        <div className="mt-14 grid gap-6 lg:grid-cols-12">
          <div className="relative overflow-hidden bg-forest p-8 text-white lg:col-span-6 lg:min-h-[420px] lg:p-10">
            <img src="/media-herbs-1.jpg" alt="" className="absolute inset-0 h-full w-full object-cover opacity-25" />
            <div className="relative">
              <p className="text-sm font-extrabold tracking-[0.16em] text-gold-soft">Protect</p>
              <h3 className="mt-3 text-4xl font-extrabold sm:text-5xl">IP that holds</h3>
              <ul className="mt-8 grid gap-3 sm:grid-cols-2">
                {PROTECT.map((t) => (
                  <li key={t}>
                    <Link
                      to="/ask"
                      className="block border border-white/20 bg-white/5 px-4 py-3 text-base font-bold hover:bg-white/15"
                    >
                      {t}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </div>
          <div className="grid gap-6 lg:col-span-6">
            <div className="border border-surface-border bg-white p-7">
              <p className="text-sm font-extrabold tracking-[0.16em] text-saffron-deep">Comply</p>
              <h3 className="mt-2 text-2xl font-extrabold text-forest sm:text-3xl">Regulatory & ABS</h3>
              <ul className="mt-5 flex flex-wrap gap-2">
                {COMPLY.map((t) => (
                  <li key={t}>
                    <Link to="/ask" className="inline-block border border-surface-border bg-ivory px-3 py-2 text-sm font-semibold text-ink hover:border-saffron">
                      {t}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
            <div className="border border-surface-border bg-navy p-7 text-white">
              <p className="text-sm font-extrabold tracking-[0.16em] text-gold-soft">Expand</p>
              <h3 className="mt-2 text-2xl font-extrabold sm:text-3xl">International track</h3>
              <ul className="mt-5 flex flex-wrap gap-2">
                {EXPAND.map((t) => (
                  <li key={t}>
                    <Link to="/ask" className="inline-block border border-white/25 bg-white/5 px-3 py-2 text-sm font-semibold hover:bg-white/15">
                      {t}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

export function HowItWorks() {
  return (
    <section className="bg-white py-20 lg:py-28">
      <div className="mx-auto max-w-portal px-4 lg:px-8">
        <h2 className="text-section text-forest">How the system works</h2>
        <div className="relative mt-14">
          <div className="absolute left-0 right-0 top-7 hidden h-0.5 bg-saffron md:block" aria-hidden="true" />
          <ol className="grid gap-8 md:grid-cols-5">
            {PROCESS.map((s) => (
              <li key={s.n} className="relative">
                <span className="relative z-10 inline-block h-3.5 w-3.5 rounded-full border-2 border-saffron bg-white" />
                <p className="mt-5 text-4xl font-extrabold text-ivory-deep" style={{ WebkitTextStroke: '1.25px #0A3D2E33' }}>
                  {s.n}
                </p>
                <h3 className="mt-2 text-xl font-extrabold text-forest">{s.title}</h3>
                <p className="mt-2 text-[15px] leading-relaxed text-ink-muted">{s.detail}</p>
              </li>
            ))}
          </ol>
        </div>
        <div className="mt-14 overflow-x-auto border border-surface-border bg-ivory p-5">
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-ink-faint">Under the journey</p>
          <ol className="mt-4 flex min-w-max items-center gap-2 text-sm font-semibold text-forest">
            {PIPELINE.map((p, i) => (
              <li key={p} className="flex items-center gap-2">
                <span className="whitespace-nowrap bg-white px-3 py-2">{p}</span>
                {i < PIPELINE.length - 1 && <span className="text-saffron" aria-hidden="true">↓</span>}
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  )
}

export function FiveLayers() {
  const [active, setActive] = useState(0)
  return (
    <section className="relative overflow-hidden bg-forest py-20 text-white lg:py-28">
      <img src="/media-herbs-2.jpg" alt="" className="absolute inset-0 h-full w-full object-cover opacity-20" />
      <div className="relative mx-auto max-w-portal px-4 lg:px-8">
        <h2 className="text-section text-white">
          One question.
          <br />
          Five layers of intelligence.
        </h2>
        <p className="mt-5 max-w-2xl border-l-4 border-saffron bg-black/20 px-5 py-4 text-lg text-white/90">
          “Can I commercialize this Ayurvedic formulation?”
        </p>
        <div className="mt-12 grid gap-6 lg:grid-cols-12">
          <ol className="space-y-2 lg:col-span-5">
            {LAYERS.map((l, i) => (
              <li key={l.n}>
                <button
                  type="button"
                  onClick={() => setActive(i)}
                  className={`w-full border px-4 py-4 text-left transition-colors ${
                    active === i ? 'border-saffron bg-saffron text-white' : 'border-white/20 bg-white/5 hover:bg-white/10'
                  }`}
                >
                  <span className="text-xs font-extrabold tracking-[0.14em] opacity-80">{l.n}</span>
                  <span className="mt-1 block text-lg font-extrabold">{l.title}</span>
                </button>
              </li>
            ))}
          </ol>
          <div className="border border-white/20 bg-white p-8 text-ink lg:col-span-7">
            <p className="text-xs font-extrabold tracking-[0.16em] text-saffron-deep">
              Layer {LAYERS[active].n}
            </p>
            <h3 className="mt-3 text-3xl font-extrabold text-forest">{LAYERS[active].title}</h3>
            <p className="mt-4 text-lg leading-relaxed text-ink-muted">{LAYERS[active].body}</p>
            <Link to="/ask" className="gov-btn-primary mt-8 inline-flex">
              Run this question in Ask
            </Link>
          </div>
        </div>
      </div>
    </section>
  )
}

export function SourceGrounded() {
  const [id, setId] = useState('1')
  const active = CLAIMS.find((c) => c.id === id) ?? CLAIMS[0]

  return (
    <section id="sources" className="bg-forest py-20 text-white lg:py-28">
      <div className="mx-auto max-w-portal px-4 lg:px-8">
        <h2 className="text-section text-white">
          AI that shows you where
          <br />
          the answer comes from.
        </h2>
        <div className="mt-14 grid gap-10 lg:grid-cols-12 lg:items-start">
          <div className="space-y-3 lg:col-span-6">
            {CLAIMS.map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => setId(c.id)}
                className={`flex w-full items-start gap-4 border px-4 py-4 text-left transition-colors ${
                  id === c.id ? 'border-saffron bg-white text-ink' : 'border-white/20 bg-white/5 hover:bg-white/10'
                }`}
              >
                <span
                  className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center text-sm font-extrabold ${
                    id === c.id ? 'bg-saffron text-white' : 'bg-white/15 text-white'
                  }`}
                >
                  {c.id.padStart(2, '0')}
                </span>
                <span className="text-[15px] font-medium leading-snug">{c.claim}</span>
              </button>
            ))}
          </div>

          <div className="relative lg:col-span-6">
            <svg className="pointer-events-none absolute -left-8 top-10 hidden h-24 w-8 lg:block" aria-hidden="true">
              <path className="evidence-line" d="M0 40 H32" />
            </svg>
            <aside className="border border-white/20 bg-white p-7 text-ink shadow-lift">
              <p className="text-xs font-extrabold tracking-[0.16em] text-saffron-deep">Claim → Source</p>
              <p className="mt-4 text-lg font-semibold leading-snug text-ink">{active.claim}</p>
              <div className="mt-6 border-t border-surface-border pt-5">
                <p className="text-xs font-bold uppercase tracking-wide text-ink-faint">Supporting source</p>
                <p className="mt-2 text-2xl font-extrabold text-forest">{active.source}</p>
                <p className="text-base font-semibold text-ink-muted">{active.section}</p>
                <p className="mt-1 text-sm text-ink-faint">{active.authority}</p>
                <Link to="/ask" className="mt-5 inline-block text-sm font-extrabold text-saffron-deep underline">
                  Open in Ask with this focus
                </Link>
              </div>
            </aside>
            <ul className="mt-4 flex flex-wrap gap-2 text-sm font-semibold text-white/80">
              <li className="border border-white/25 px-3 py-1.5">WIPO</li>
              <li className="border border-white/25 px-3 py-1.5">Ministry of Ayush</li>
              <li className="border border-white/25 px-3 py-1.5">National Biodiversity Authority</li>
            </ul>
          </div>
        </div>
      </div>
    </section>
  )
}

export function JurisdictionSplit() {
  return (
    <section id="ip-ayurveda" className="bg-ivory">
      <div className="mx-auto grid max-w-portal lg:grid-cols-[1fr_auto_1fr]">
        <div className="border-b border-surface-border px-6 py-16 lg:border-b-0 lg:border-r lg:px-10 lg:py-24">
          <p className="text-sm font-extrabold tracking-[0.16em] text-saffron-deep">India</p>
          <h2 className="mt-3 text-4xl font-extrabold text-forest sm:text-5xl">Domestic track</h2>
          <ul className="mt-8 space-y-3 text-lg text-ink-muted">
            {['Patents', 'GI', 'Trademarks', 'AYUSH', 'Biodiversity / ABS', 'FSSAI', 'Traditional Knowledge'].map(
              (t) => (
                <li key={t} className="flex items-center gap-3">
                  <span className="h-px w-8 bg-saffron" />
                  {t}
                </li>
              ),
            )}
          </ul>
        </div>
        <div className="flex items-center justify-center bg-navy px-6 py-12 text-center text-white lg:min-w-[12rem]">
          <div>
            <p className="text-[11px] font-extrabold tracking-[0.18em] text-gold-soft">Jurisdiction-aware</p>
            <p className="mt-2 text-3xl font-extrabold leading-none">Routing</p>
          </div>
        </div>
        <div className="px-6 py-16 lg:px-10 lg:py-24">
          <p className="text-sm font-extrabold tracking-[0.16em] text-forest-mid">International</p>
          <h2 className="mt-3 text-4xl font-extrabold text-forest sm:text-5xl">Global track</h2>
          <ul className="mt-8 space-y-3 text-lg text-ink-muted">
            {['WIPO', 'TRIPS', 'PCT', 'CBD', 'Nagoya Protocol', 'Foreign IP offices', 'Market-specific regulation'].map(
              (t) => (
                <li key={t} className="flex items-center gap-3">
                  <span className="h-px w-8 bg-forest-mid" />
                  {t}
                </li>
              ),
            )}
          </ul>
        </div>
      </div>
    </section>
  )
}

export function Multilingual() {
  return (
    <section className="bg-white py-20 lg:py-28">
      <div className="mx-auto max-w-portal px-4 lg:px-8">
        <h2 className="text-section text-forest">Knowledge should not be limited by language.</h2>
        <p className="mt-4 max-w-2xl text-lg text-ink-muted">
          English is available now. Scripts below show the intended multilingual surface for future
          BHASHINI integration — we do not claim live support for all languages yet.
        </p>
        <div className="mt-12 flex flex-wrap gap-x-6 gap-y-5">
          {SCRIPTS.map((s) => (
            <span
              key={s}
              className={`font-hindi leading-none ${
                s === 'English' ? 'text-5xl font-extrabold text-saffron-deep sm:text-6xl' : 'text-3xl font-semibold text-forest/70 sm:text-4xl'
              }`}
              lang={s === 'English' ? 'en' : undefined}
            >
              {s}
            </span>
          ))}
        </div>
      </div>
    </section>
  )
}

export function AskImmersive() {
  const navigate = useNavigate()
  const [q, setQ] = useState('')

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    navigate('/ask', { state: { prefill: q || SUGGESTIONS[0] } })
  }

  return (
    <section
      className="relative overflow-hidden py-20 lg:py-28"
      style={{
        backgroundImage: 'linear-gradient(rgba(10,61,46,0.88), rgba(10,61,46,0.88)), url(/media-ayurveda-3.jpg)',
        backgroundSize: 'cover',
        backgroundPosition: 'center',
      }}
    >
      <div className="mx-auto max-w-portal px-4 lg:px-8">
        <h2 className="text-section text-white">Ask a question.</h2>
        <form onSubmit={onSubmit} className="mt-10">
          <div className="flex flex-col gap-3 border border-white/20 bg-white p-3 sm:flex-row">
            <input
              className="min-h-[56px] flex-1 border-0 bg-transparent px-3 text-base outline-none"
              placeholder="Describe your formulation, invention or regulatory question…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <button type="submit" className="gov-btn-primary !px-8">
              Ask IP-SAKTI
            </button>
          </div>
        </form>
        <ul className="mt-6 grid gap-2 sm:grid-cols-2">
          {SUGGESTIONS.map((s) => (
            <li key={s}>
              <button
                type="button"
                className="w-full px-1 py-2 text-left text-sm text-white/80 underline-offset-2 hover:text-white hover:underline"
                onClick={() => navigate('/ask', { state: { prefill: s } })}
              >
                {s}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}

export function KnowledgeCentre() {
  return (
    <section id="knowledge" className="bg-ivory py-20 lg:py-28">
      <div className="mx-auto max-w-portal px-4 lg:px-8">
        <h2 className="text-section text-forest">Knowledge Centre</h2>
        <p className="mt-4 max-w-2xl text-lg text-ink-muted">
          Document-library view of materials Sahayak can cite from the curated corpus.
        </p>
        <div className="mt-12 overflow-hidden border border-surface-border bg-white">
          <div className="hidden grid-cols-[1.4fr_1fr_0.8fr_0.8fr_0.7fr] gap-3 bg-forest px-5 py-3 text-[11px] font-extrabold uppercase tracking-wide text-white/80 md:grid">
            <span>Collection</span>
            <span>Authority</span>
            <span>Type</span>
            <span>Jurisdiction</span>
            <span>Version</span>
          </div>
          <ul>
            {DOCS.map((d) => (
              <li
                key={d.title}
                className="grid items-center gap-2 border-b border-surface-border px-5 py-5 last:border-0 md:grid-cols-[1.4fr_1fr_0.8fr_0.8fr_0.7fr]"
              >
                <div className="flex items-center gap-3">
                  <div className="hidden h-14 w-10 flex-col justify-between border border-surface-border bg-ivory p-1 sm:flex" aria-hidden="true">
                    <div className="h-1 bg-forest/20" />
                    <div className="space-y-0.5">
                      <div className="h-0.5 bg-forest/15" />
                      <div className="h-0.5 w-2/3 bg-forest/15" />
                    </div>
                  </div>
                  <div>
                    <p className="font-extrabold text-forest">{d.title}</p>
                    <Link to="/ask" className="text-xs font-bold text-saffron-deep underline">
                      View in Ask
                    </Link>
                  </div>
                </div>
                <p className="text-sm text-ink-muted">{d.authority}</p>
                <p className="text-sm text-ink-muted">{d.type}</p>
                <p className="text-sm font-bold text-forest">{d.jurisdiction}</p>
                <p className="text-xs font-semibold text-ink-faint">{d.version}</p>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  )
}

export function LatestUpdates() {
  return (
    <section className="bg-white py-16 lg:py-20">
      <div className="mx-auto max-w-portal px-4 lg:px-8">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h2 className="text-3xl font-extrabold text-forest sm:text-4xl">Latest updates</h2>
          <p className="text-xs font-bold uppercase tracking-wide text-ink-faint">Demo timeline — not gazette notices</p>
        </div>
        <ol className="mt-10 space-y-0 border-l-2 border-saffron/40">
          {UPDATES.map((u) => (
            <li key={u.title} className="relative py-5 pl-8">
              <span className="absolute -left-[5px] top-7 h-2.5 w-2.5 rounded-full bg-saffron" />
              <p className="text-xs font-extrabold tracking-[0.14em] text-saffron-deep">
                {u.date} · {u.category}
                {u.demo ? ' · DEMO' : ''}
              </p>
              <p className="mt-2 text-lg font-semibold text-ink">{u.title}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}

export function DisclaimerFaq() {
  return (
    <>
      <section id="disclaimer" className="border-y border-surface-border bg-ivory py-14">
        <div className="mx-auto max-w-portal px-4 lg:px-8">
          <h2 className="text-2xl font-extrabold text-forest">Disclaimer</h2>
          <p className="mt-4 max-w-3xl text-base leading-relaxed text-ink-muted">
            IP-SAKTI Sahayak provides information and decision-support based on available
            authoritative sources. It does not provide legal advice and does not replace qualified
            legal or regulatory professionals.
          </p>
        </div>
      </section>
      <section id="faq" className="bg-white py-14">
        <div className="mx-auto grid max-w-portal gap-8 px-4 md:grid-cols-3 lg:px-8">
          <div>
            <h3 className="font-extrabold text-forest">Is this legal advice?</h3>
            <p className="mt-2 text-sm text-ink-muted">No — cited information and decision-support only.</p>
          </div>
          <div>
            <h3 className="font-extrabold text-forest">Does it search TKDL?</h3>
            <p className="mt-2 text-sm text-ink-muted">Awareness pointers only; contents are not retrieved.</p>
          </div>
          <div>
            <h3 className="font-extrabold text-forest">Mixed jurisdictions?</h3>
            <p className="mt-2 text-sm text-ink-muted">Never. India and international stay on separate tracks.</p>
          </div>
        </div>
      </section>
    </>
  )
}
