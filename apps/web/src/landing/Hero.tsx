import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { animate } from 'animejs'

type Demo = {
  q: string
  product: string
  domain: string
  jurisdiction: string
  guidance: string
  sources: { title: string; section: string }[]
  confidence: number
}

const DEMOS: Demo[] = [
  {
    q: 'Can I patent a classical Ayurvedic formulation?',
    product: 'Classical formulation',
    domain: 'Patentability',
    jurisdiction: 'India',
    guidance:
      'Classical compositions often face limits under traditional-knowledge exclusions. Inventive step beyond known classical use must be demonstrated before filing.',
    sources: [
      { title: 'Patents Act, 1970', section: 'Section 3(p)' },
      { title: 'TK awareness', section: 'CSIR-TKDL pointer' },
    ],
    confidence: 82,
  },
  {
    q: 'What IP protection fits a herbal brand?',
    product: 'Herbal brand / mark',
    domain: 'Trademark',
    jurisdiction: 'India',
    guidance:
      'Names and logos are typically protected as trademarks. Distinctiveness and class selection matter more than patent routes for pure branding.',
    sources: [
      { title: 'Trade Marks Act, 1999', section: 'Distinctiveness' },
      { title: 'IPO practice', section: 'Class selection' },
    ],
    confidence: 78,
  },
  {
    q: 'Does my product trigger biodiversity / ABS duties?',
    product: 'Biological resource use',
    domain: 'ABS',
    jurisdiction: 'India',
    guidance:
      'Commercial use of Indian biological resources generally engages NBA approval pathways. Map access and benefit-sharing early.',
    sources: [
      { title: 'Biological Diversity Act', section: 'ABS pathway' },
      { title: 'NBA guidance', section: 'Commercial use' },
    ],
    confidence: 74,
  },
]

function DocThumb({ label }: { label: string }) {
  return (
    <div className="flex h-12 w-9 flex-col justify-between border border-surface-border bg-ivory p-1" aria-hidden="true">
      <div className="h-1 w-full bg-forest/25" />
      <div className="space-y-0.5">
        <div className="h-0.5 w-full bg-forest/15" />
        <div className="h-0.5 w-3/4 bg-forest/15" />
      </div>
      <span className="text-[6px] font-bold uppercase text-forest/60">{label}</span>
    </div>
  )
}

export function ProductInterface({ demo, onPick }: { demo: Demo; onPick: (i: number) => void }) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current) return
    const nodes = ref.current.querySelectorAll('[data-reveal]')
    nodes.forEach((node, i) => {
      animate(node, {
        opacity: [0, 1],
        translateY: [10, 0],
        delay: i * 55,
        duration: 380,
        ease: 'outQuad',
      })
    })
  }, [demo])

  return (
    <div ref={ref} className="overflow-hidden border border-white/25 bg-white shadow-lift">
      <div className="flex items-center justify-between bg-forest px-5 py-3.5 text-white">
        <div>
          <p className="text-base font-extrabold tracking-tight">IP-SAKTI Sahayak</p>
          <p className="text-xs text-white/70">Source-cited guidance</p>
        </div>
        <span className="bg-saffron px-2.5 py-1 text-[10px] font-extrabold uppercase tracking-wide">
          Live product
        </span>
      </div>

      <div className="space-y-4 p-5">
        <div data-reveal>
          <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-ink-faint">Question</p>
          <p className="mt-1.5 border-l-4 border-saffron bg-ivory px-3 py-2.5 text-[15px] font-medium leading-snug text-ink">
            “{demo.q}”
          </p>
        </div>

        <div data-reveal className="grid grid-cols-3 gap-3 border-y border-surface-border py-3">
          {[
            ['Classification', demo.product],
            ['IP domain', demo.domain],
            ['Jurisdiction', demo.jurisdiction],
          ].map(([k, v]) => (
            <div key={k}>
              <p className="text-[10px] font-bold uppercase tracking-wide text-ink-faint">{k}</p>
              <p className="mt-1 text-sm font-bold text-forest">{v}</p>
            </div>
          ))}
        </div>

        <div data-reveal>
          <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-saffron-deep">Guidance</p>
          <p className="mt-2 text-[15px] leading-relaxed text-ink-muted">{demo.guidance}</p>
        </div>

        <div data-reveal className="grid gap-2 sm:grid-cols-2">
          {demo.sources.map((s, i) => (
            <div key={s.title} className="flex gap-2 border border-surface-border bg-ivory/80 p-2.5">
              <DocThumb label={i === 0 ? 'Act' : 'TK'} />
              <div>
                <p className="text-[10px] font-extrabold text-saffron">Evidence {i + 1}</p>
                <p className="text-xs font-bold text-ink">{s.title}</p>
                <p className="text-[11px] text-ink-muted">{s.section}</p>
              </div>
            </div>
          ))}
        </div>

        <div data-reveal className="flex flex-wrap items-center justify-between gap-3 border-t border-surface-border pt-3">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wide text-ink-faint">Confidence</p>
            <div className="mt-1 flex items-center gap-2">
              <div className="h-2 w-32 overflow-hidden bg-surface-border">
                <div className="h-full bg-forest-mid" style={{ width: `${demo.confidence}%` }} />
              </div>
              <span className="text-base font-extrabold text-forest">{demo.confidence}%</span>
            </div>
          </div>
          <Link to="/ask" className="text-sm font-extrabold text-saffron-deep underline-offset-2 hover:underline">
            View evidence
          </Link>
        </div>

        <div className="flex flex-wrap gap-2 pt-1">
          {DEMOS.map((d, i) => (
            <button
              key={d.q}
              type="button"
              onClick={() => onPick(i)}
              className={`rounded-sm border px-2.5 py-1 text-left text-[11px] font-semibold ${
                d.q === demo.q
                  ? 'border-forest bg-forest text-white'
                  : 'border-surface-border bg-white text-ink hover:border-forest'
              }`}
            >
              Scenario {i + 1}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

export function Hero() {
  const [i, setI] = useState(0)
  const demo = DEMOS[i]

  return (
    <section className="relative overflow-hidden bg-ivory" aria-labelledby="hero-heading">
      <div className="mx-auto grid max-w-portal lg:grid-cols-12 lg:gap-0">
        {/* Compositional media column */}
        <div className="relative min-h-[280px] lg:col-span-5 lg:min-h-[720px]">
          <img
            src="/media-herbs-2.jpg"
            alt="Ayurvedic herbs and botanical materials"
            className="absolute inset-0 h-full w-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-forest/90 via-forest/35 to-transparent lg:bg-gradient-to-r lg:from-transparent lg:via-forest/20 lg:to-forest/55" />
          <div className="absolute bottom-0 left-0 right-0 p-6 text-white lg:hidden">
            <p className="text-xs font-bold tracking-[0.18em] text-gold-soft">
              MINISTRY OF AYUSH · DIGITAL KNOWLEDGE ASSISTANCE
            </p>
          </div>
        </div>

        {/* Copy + product */}
        <div className="relative bg-forest lg:col-span-7">
          <div className="grid gap-10 px-4 py-12 sm:px-8 lg:grid-cols-[0.95fr_1.05fr] lg:items-center lg:gap-8 lg:px-10 lg:py-14">
            <div className="text-white">
              <p className="hidden text-[11px] font-bold tracking-[0.18em] text-gold-soft lg:block">
                MINISTRY OF AYUSH · DIGITAL KNOWLEDGE ASSISTANCE
              </p>
              <h1 id="hero-heading" className="mt-3">
                <span className="block text-hero font-extrabold tracking-tight">IP-SAKTI</span>
                <span className="mt-1 block text-3xl font-semibold tracking-wide text-gold-soft sm:text-4xl">
                  Sahayak
                </span>
              </h1>
              <p className="mt-6 text-2xl font-semibold leading-snug sm:text-[1.75rem]">
                Navigate intellectual property
                <br />
                and regulation for Ayurveda.
              </p>
              <p className="mt-4 max-w-md text-base leading-relaxed text-white/80 sm:text-lg">
                A multilingual, source-cited AI assistant for practitioners, researchers, AYUSH
                enterprises and innovators.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Link to="/ask" className="gov-btn-primary !px-6 !py-3.5 text-base">
                  Ask IP-SAKTI
                </Link>
                <a href="#knowledge" className="gov-btn-outline-light !px-6 !py-3.5 text-base">
                  Explore Knowledge Centre
                </a>
              </div>
              <ul className="mt-8 flex flex-wrap gap-x-5 gap-y-2 text-[11px] font-extrabold uppercase tracking-[0.14em] text-white/70">
                <li>Source-cited</li>
                <li>Jurisdiction-aware</li>
                <li>Multilingual</li>
              </ul>
            </div>

            <div className="lg:-mr-2">
              <ProductInterface demo={demo} onPick={setI} />
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
