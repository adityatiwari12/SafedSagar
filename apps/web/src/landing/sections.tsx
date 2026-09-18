import { FormEvent, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useLanguage } from '../i18n/LanguageContext'
import { LANGUAGES } from '../api/languages'

export function InnovationArc() {
  const { t } = useLanguage()
  const steps = [t('about.step1'), t('about.step2'), t('about.step3'), t('about.step4'), t('about.step5')]
  return (
    <section id="about" className="scroll-mt-28 bg-ivory py-20 lg:py-28">
      <div className="mx-auto grid max-w-portal gap-12 px-4 lg:grid-cols-12 lg:gap-10 lg:px-8">
        <div className="lg:col-span-7">
          <h2 className="text-section text-forest">
            {t('about.title1')}
            <br />
            {t('about.title2')}
          </h2>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-ink-muted">{t('about.body')}</p>
          <p className="mt-8 max-w-xl border-l-4 border-saffron bg-white px-5 py-4 text-lg font-semibold leading-snug text-forest">
            {t('about.callout')}
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
  const { t } = useLanguage()
  const personas = [
    { title: t('personas.p1title'), image: '/media-chyawanprash.webp', copy: t('personas.p1copy') },
    { title: t('personas.p2title'), image: '/media-herbs-1.jpg', copy: t('personas.p2copy') },
    { title: t('personas.p3title'), image: '/media-ayurveda-3.jpg', copy: t('personas.p3copy') },
    { title: t('personas.p4title'), image: '/media-herbs-2.jpg', copy: t('personas.p4copy') },
    { title: t('personas.p5title'), image: '/media-herbs-1.jpg', copy: t('personas.p5copy') },
    { title: t('personas.p6title'), image: '/media-ayurveda-3.jpg', copy: t('personas.p6copy') },
  ]

  return (
    <section className="bg-white py-20 lg:py-28">
      <div className="mx-auto max-w-portal px-4 lg:px-8">
        <h2 className="text-section text-forest">{t('personas.title')}</h2>
        <p className="mt-4 max-w-2xl text-lg text-ink-muted">{t('personas.blurb')}</p>
        <div className="mt-14 space-y-12">
          {personas.map((p, i) => {
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
                    {t('personas.askContext')}
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
  const { t } = useLanguage()
  const protect = [
    t('services.patents'),
    t('services.trademarks'),
    t('services.gi'),
    t('services.copyright'),
    t('services.designs'),
    t('services.tradeSecrets'),
  ]
  const comply = [
    t('services.ayurvedaReg'),
    t('services.biodiversity'),
    t('services.abs'),
    t('services.tk'),
    t('services.fssai'),
  ]
  const expand = [
    t('services.intlIp'),
    t('services.pct'),
    t('services.wipo'),
    t('services.trips'),
    t('services.countrySpecific'),
  ]

  return (
    <section id="services" className="scroll-mt-28 bg-ivory py-20 lg:py-28">
      <div className="mx-auto max-w-portal px-4 lg:px-8">
        <h2 className="text-section text-forest">{t('services.title')}</h2>
        <div className="mt-14 grid gap-6 lg:grid-cols-12">
          <div className="relative overflow-hidden bg-forest p-8 text-white lg:col-span-6 lg:min-h-[420px] lg:p-10">
            <img src="/media-herbs-1.jpg" alt="" className="absolute inset-0 h-full w-full object-cover opacity-25" />
            <div className="relative">
              <p className="text-sm font-extrabold tracking-[0.16em] text-gold-soft">{t('services.protect')}</p>
              <h3 className="mt-3 text-4xl font-extrabold sm:text-5xl">{t('services.protectTitle')}</h3>
              <ul className="mt-8 grid gap-3 sm:grid-cols-2">
                {protect.map((item) => (
                  <li key={item}>
                    <Link
                      to="/ask"
                      className="block border border-white/20 bg-white/5 px-4 py-3 text-base font-bold hover:bg-white/15"
                    >
                      {item}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </div>
          <div className="grid gap-6 lg:col-span-6">
            <div className="border border-surface-border bg-white p-7">
              <p className="text-sm font-extrabold tracking-[0.16em] text-saffron-deep">{t('services.comply')}</p>
              <h3 className="mt-2 text-2xl font-extrabold text-forest sm:text-3xl">{t('services.complyTitle')}</h3>
              <ul className="mt-5 flex flex-wrap gap-2">
                {comply.map((item) => (
                  <li key={item}>
                    <Link
                      to="/ask"
                      className="inline-block border border-surface-border bg-ivory px-3 py-2 text-sm font-semibold text-ink hover:border-saffron"
                    >
                      {item}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
            <div className="border border-surface-border bg-navy p-7 text-white">
              <p className="text-sm font-extrabold tracking-[0.16em] text-gold-soft">{t('services.expand')}</p>
              <h3 className="mt-2 text-2xl font-extrabold sm:text-3xl">{t('services.expandTitle')}</h3>
              <ul className="mt-5 flex flex-wrap gap-2">
                {expand.map((item) => (
                  <li key={item}>
                    <Link
                      to="/ask"
                      className="inline-block border border-white/25 bg-white/5 px-3 py-2 text-sm font-semibold hover:bg-white/15"
                    >
                      {item}
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
  const { t } = useLanguage()
  const process = [
    { n: '01', title: t('how.ask'), detail: t('how.askDetail') },
    { n: '02', title: t('how.classify'), detail: t('how.classifyDetail') },
    { n: '03', title: t('how.retrieve'), detail: t('how.retrieveDetail') },
    { n: '04', title: t('how.verify'), detail: t('how.verifyDetail') },
    { n: '05', title: t('how.guide'), detail: t('how.guideDetail') },
  ]
  const pipeline = [
    t('how.pipeUser'),
    t('how.pipeUnderstand'),
    t('how.pipeProduct'),
    t('how.pipeJurisdiction'),
    t('how.pipeRetrieve'),
    t('how.pipeReason'),
    t('how.pipeCite'),
    t('how.pipeAnswer'),
  ]

  return (
    <section className="bg-white py-20 lg:py-28">
      <div className="mx-auto max-w-portal px-4 lg:px-8">
        <h2 className="text-section text-forest">{t('how.title')}</h2>
        <div className="relative mt-14">
          <div className="absolute left-0 right-0 top-7 hidden h-0.5 bg-saffron md:block" aria-hidden="true" />
          <ol className="grid gap-8 md:grid-cols-5">
            {process.map((s) => (
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
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-ink-faint">{t('how.underJourney')}</p>
          <ol className="mt-4 flex min-w-max items-center gap-2 text-sm font-semibold text-forest">
            {pipeline.map((p, i) => (
              <li key={p} className="flex items-center gap-2">
                <span className="whitespace-nowrap bg-white px-3 py-2">{p}</span>
                {i < pipeline.length - 1 && (
                <span className="text-saffron" aria-hidden="true">
                    →
                  </span>
                )}
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
  const { t } = useLanguage()
  const layers = [
    { n: '01', title: t('layers.l1title'), body: t('layers.l1body') },
    { n: '02', title: t('layers.l2title'), body: t('layers.l2body') },
    { n: '03', title: t('layers.l3title'), body: t('layers.l3body') },
    { n: '04', title: t('layers.l4title'), body: t('layers.l4body') },
    { n: '05', title: t('layers.l5title'), body: t('layers.l5body') },
  ]

  return (
    <section className="relative overflow-hidden bg-forest py-20 text-white lg:py-28">
      <img src="/media-herbs-2.jpg" alt="" className="absolute inset-0 h-full w-full object-cover opacity-20" />
      <div className="relative mx-auto max-w-portal px-4 lg:px-8">
        <h2 className="text-section text-white">
          {t('layers.title1')}
          <br />
          {t('layers.title2')}
        </h2>
        <p className="mt-5 max-w-2xl border-l-4 border-saffron bg-black/20 px-5 py-4 text-lg text-white/90">
          {t('layers.sampleQ')}
        </p>
        <div className="mt-12 grid gap-6 lg:grid-cols-12">
          <ol className="space-y-2 lg:col-span-5">
            {layers.map((l, i) => (
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
              {t('layers.layerLabel')} {layers[active].n}
            </p>
            <h3 className="mt-3 text-3xl font-extrabold text-forest">{layers[active].title}</h3>
            <p className="mt-4 text-lg leading-relaxed text-ink-muted">{layers[active].body}</p>
            <Link to="/ask" className="gov-btn-primary mt-8 inline-flex">
              {t('layers.runAsk')}
            </Link>
          </div>
        </div>
      </div>
    </section>
  )
}

export function SourceGrounded() {
  const [id, setId] = useState('1')
  const { t } = useLanguage()
  const claims = [
    {
      id: '1',
      claim: t('sources.c1'),
      source: t('sources.c1source'),
      section: t('sources.c1section'),
      authority: t('sources.c1authority'),
    },
    {
      id: '2',
      claim: t('sources.c2'),
      source: t('sources.c2source'),
      section: t('sources.c2section'),
      authority: t('sources.c2authority'),
    },
    {
      id: '3',
      claim: t('sources.c3'),
      source: t('sources.c3source'),
      section: t('sources.c3section'),
      authority: t('sources.c3authority'),
    },
  ]
  const active = claims.find((c) => c.id === id) ?? claims[0]

  return (
    <section id="sources" className="scroll-mt-28 bg-forest py-20 text-white lg:py-28">
      <div className="mx-auto max-w-portal px-4 lg:px-8">
        <h2 className="text-section text-white">
          {t('sources.title1')}
          <br />
          {t('sources.title2')}
        </h2>
        <div className="mt-14 grid gap-10 lg:grid-cols-12 lg:items-start">
          <div className="space-y-3 lg:col-span-6">
            {claims.map((c) => (
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
              <p className="text-xs font-extrabold tracking-[0.16em] text-saffron-deep">{t('sources.claimSource')}</p>
              <p className="mt-4 text-lg font-semibold leading-snug text-ink">{active.claim}</p>
              <div className="mt-6 border-t border-surface-border pt-5">
                <p className="text-xs font-bold uppercase tracking-wide text-ink-faint">{t('sources.supporting')}</p>
                <p className="mt-2 text-2xl font-extrabold text-forest">{active.source}</p>
                <p className="text-base font-semibold text-ink-muted">{active.section}</p>
                <p className="mt-1 text-sm text-ink-faint">{active.authority}</p>
                <Link to="/ask" className="mt-5 inline-block text-sm font-extrabold text-saffron-deep underline">
                  {t('sources.openAsk')}
                </Link>
              </div>
            </aside>
            <ul className="mt-4 flex flex-wrap gap-2 text-sm font-semibold text-white/80">
              <li className="border border-white/25 px-3 py-1.5">WIPO</li>
              <li className="border border-white/25 px-3 py-1.5">{t('common.ministryAyush')}</li>
              <li className="border border-white/25 px-3 py-1.5">National Biodiversity Authority</li>
            </ul>
          </div>
        </div>
      </div>
    </section>
  )
}

export function JurisdictionSplit() {
  const { t } = useLanguage()
  const india = [
    t('jurisdiction.patents'),
    t('jurisdiction.gi'),
    t('jurisdiction.trademarks'),
    t('jurisdiction.ayush'),
    t('jurisdiction.biodiversityAbs'),
    t('jurisdiction.fssai'),
    t('jurisdiction.tk'),
  ]
  const intl = [
    t('jurisdiction.wipo'),
    t('jurisdiction.trips'),
    t('jurisdiction.pct'),
    t('jurisdiction.cbd'),
    t('jurisdiction.nagoya'),
    t('jurisdiction.foreignIp'),
    t('jurisdiction.marketReg'),
  ]

  return (
    <section id="ip-ayurveda" className="scroll-mt-28 bg-ivory">
      <div className="mx-auto grid max-w-portal lg:grid-cols-[1fr_auto_1fr]">
        <div className="border-b border-surface-border px-6 py-16 lg:border-b-0 lg:border-r lg:px-10 lg:py-24">
          <p className="text-sm font-extrabold tracking-[0.16em] text-saffron-deep">{t('jurisdiction.india')}</p>
          <h2 className="mt-3 text-4xl font-extrabold text-forest sm:text-5xl">{t('jurisdiction.domestic')}</h2>
          <ul className="mt-8 space-y-3 text-lg text-ink-muted">
            {india.map((item) => (
              <li key={item} className="flex items-center gap-3">
                <span className="h-px w-8 bg-saffron" />
                {item}
              </li>
            ))}
          </ul>
        </div>
        <div className="flex items-center justify-center bg-navy px-6 py-12 text-center text-white lg:min-w-[12rem]">
          <div>
            <p className="text-[11px] font-extrabold tracking-[0.18em] text-gold-soft">
              {t('jurisdiction.routingKicker')}
            </p>
            <p className="mt-2 text-3xl font-extrabold leading-none">{t('jurisdiction.routing')}</p>
          </div>
        </div>
        <div className="px-6 py-16 lg:px-10 lg:py-24">
          <p className="text-sm font-extrabold tracking-[0.16em] text-forest-mid">{t('jurisdiction.international')}</p>
          <h2 className="mt-3 text-4xl font-extrabold text-forest sm:text-5xl">{t('jurisdiction.global')}</h2>
          <ul className="mt-8 space-y-3 text-lg text-ink-muted">
            {intl.map((item) => (
              <li key={item} className="flex items-center gap-3">
                <span className="h-px w-8 bg-forest-mid" />
                {item}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  )
}

export function Multilingual() {
  const { t, language, setLanguage } = useLanguage()
  return (
    <section className="bg-white py-20 lg:py-28">
      <div className="mx-auto max-w-portal px-4 lg:px-8">
        <h2 className="text-section text-forest">{t('multilingual.title')}</h2>
        <p className="mt-4 max-w-2xl text-lg text-ink-muted">{t('multilingual.body')}</p>
        <div className="mt-12 flex flex-wrap gap-x-6 gap-y-5">
          {LANGUAGES.map((lang) => (
            <button
              key={lang.code}
              type="button"
              lang={lang.code}
              onClick={() => setLanguage(lang.code)}
              className={`leading-none transition-colors ${
                language === lang.code
                  ? 'text-5xl font-extrabold text-saffron-deep sm:text-6xl'
                  : 'text-3xl font-semibold text-forest/70 hover:text-forest sm:text-4xl'
              }`}
            >
              {lang.nativeName}
            </button>
          ))}
        </div>
        <p className="mt-6 text-sm font-semibold text-forest-mid">{t('langCard.poweredBy')}</p>
      </div>
    </section>
  )
}

export function AskImmersive() {
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const { t } = useLanguage()
  const suggestions = useMemo(() => [t('ask.s1'), t('ask.s2'), t('ask.s3'), t('ask.s4')], [t])

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    navigate('/ask', { state: { seededDraft: q || suggestions[0] } })
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
        <h2 className="text-section text-white">{t('ask.title')}</h2>
        <form onSubmit={onSubmit} className="mt-10">
          <div className="flex flex-col gap-3 border border-white/20 bg-white p-3 sm:flex-row">
            <input
              className="min-h-[56px] flex-1 border-0 bg-transparent px-3 text-base outline-none"
              placeholder={t('ask.placeholder')}
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <button type="submit" className="gov-btn-primary !px-8">
              {t('common.askIpsakti')}
            </button>
          </div>
        </form>
        <ul className="mt-6 grid gap-2 sm:grid-cols-2">
          {suggestions.map((s) => (
            <li key={s}>
              <button
                type="button"
                className="w-full px-1 py-2 text-left text-sm text-white/80 underline-offset-2 hover:text-white hover:underline"
                onClick={() => navigate('/ask', { state: { seededDraft: s } })}
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
  const { t } = useLanguage()
  const docs = [
    {
      title: t('knowledge.d1title'),
      authority: t('knowledge.d1authority'),
      type: t('knowledge.d1type'),
      jurisdiction: t('knowledge.d1jurisdiction'),
      version: t('knowledge.d1version'),
    },
    {
      title: t('knowledge.d2title'),
      authority: t('knowledge.d2authority'),
      type: t('knowledge.d2type'),
      jurisdiction: t('knowledge.d2jurisdiction'),
      version: t('knowledge.d2version'),
    },
    {
      title: t('knowledge.d3title'),
      authority: t('knowledge.d3authority'),
      type: t('knowledge.d3type'),
      jurisdiction: t('knowledge.d3jurisdiction'),
      version: t('knowledge.d3version'),
    },
    {
      title: t('knowledge.d4title'),
      authority: t('knowledge.d4authority'),
      type: t('knowledge.d4type'),
      jurisdiction: t('knowledge.d4jurisdiction'),
      version: t('knowledge.d4version'),
    },
    {
      title: t('knowledge.d5title'),
      authority: t('knowledge.d5authority'),
      type: t('knowledge.d5type'),
      jurisdiction: t('knowledge.d5jurisdiction'),
      version: t('knowledge.d5version'),
    },
    {
      title: t('knowledge.d6title'),
      authority: t('knowledge.d6authority'),
      type: t('knowledge.d6type'),
      jurisdiction: t('knowledge.d6jurisdiction'),
      version: t('knowledge.d6version'),
    },
    {
      title: t('knowledge.d7title'),
      authority: t('knowledge.d7authority'),
      type: t('knowledge.d7type'),
      jurisdiction: t('knowledge.d7jurisdiction'),
      version: t('knowledge.d7version'),
    },
  ]

  return (
    <section id="knowledge" className="scroll-mt-28 bg-ivory py-20 lg:py-28">
      <div className="mx-auto max-w-portal px-4 lg:px-8">
        <h2 className="text-section text-forest">{t('knowledge.title')}</h2>
        <p className="mt-4 max-w-2xl text-lg text-ink-muted">{t('knowledge.blurb')}</p>
        <div className="mt-12 overflow-hidden border border-surface-border bg-white">
          <div className="hidden grid-cols-[1.4fr_1fr_0.8fr_0.8fr_0.7fr] gap-3 bg-forest px-5 py-3 text-[11px] font-extrabold uppercase tracking-wide text-white/80 md:grid">
            <span>{t('knowledge.collection')}</span>
            <span>{t('knowledge.authority')}</span>
            <span>{t('knowledge.type')}</span>
            <span>{t('knowledge.jurisdiction')}</span>
            <span>{t('knowledge.version')}</span>
          </div>
          <ul>
            {docs.map((d) => (
              <li
                key={d.title}
                data-knowledge-row
                className="grid items-center gap-2 border-b border-surface-border px-5 py-5 last:border-0 md:grid-cols-[1.4fr_1fr_0.8fr_0.8fr_0.7fr]"
              >
                <div className="flex items-center gap-3">
                  <div
                    className="hidden h-14 w-10 flex-col justify-between border border-surface-border bg-ivory p-1 sm:flex"
                    aria-hidden="true"
                  >
                    <div className="h-1 bg-forest/20" />
                    <div className="space-y-0.5">
                      <div className="h-0.5 bg-forest/15" />
                      <div className="h-0.5 w-2/3 bg-forest/15" />
                    </div>
                  </div>
                  <div>
                    <p className="font-extrabold text-forest">{d.title}</p>
                    <Link to="/ask" className="text-xs font-bold text-saffron-deep underline">
                      {t('knowledge.viewInAsk')}
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
  const { t } = useLanguage()
  const updates = [
    { date: '2026-09-15', category: t('updates.u1cat'), title: t('updates.u1title'), demo: true },
    { date: '2026-08-20', category: t('updates.u2cat'), title: t('updates.u2title'), demo: true },
    { date: '2026-05-24', category: t('updates.u3cat'), title: t('updates.u3title'), demo: true },
  ]

  return (
    <section className="bg-white py-16 lg:py-20">
      <div className="mx-auto max-w-portal px-4 lg:px-8">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h2 className="text-3xl font-extrabold text-forest sm:text-4xl">{t('updates.title')}</h2>
          <p className="text-xs font-bold uppercase tracking-wide text-ink-faint">{t('updates.demoNote')}</p>
        </div>
        <ol className="mt-10 space-y-0 border-l-2 border-saffron/40">
          {updates.map((u) => (
            <li key={u.title} className="relative py-5 pl-8">
              <span className="absolute -left-[5px] top-7 h-2.5 w-2.5 rounded-full bg-saffron" />
              <p className="text-xs font-extrabold tracking-[0.14em] text-saffron-deep">
                {u.date} · {u.category}
                {u.demo ? ` · ${t('updates.demo')}` : ''}
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
  const { t } = useLanguage()
  return (
    <>
      <section id="disclaimer" className="scroll-mt-28 border-y border-surface-border bg-ivory py-14">
        <div className="mx-auto max-w-portal px-4 lg:px-8">
          <h2 className="text-2xl font-extrabold text-forest">{t('disclaimer.title')}</h2>
          <p className="mt-4 max-w-3xl text-base leading-relaxed text-ink-muted">{t('disclaimer.body')}</p>
        </div>
      </section>
      <section id="faq" className="scroll-mt-28 bg-white py-14">
        <div className="mx-auto grid max-w-portal gap-8 px-4 md:grid-cols-3 lg:px-8">
          <div>
            <h3 className="font-extrabold text-forest">{t('disclaimer.q1')}</h3>
            <p className="mt-2 text-sm text-ink-muted">{t('disclaimer.a1')}</p>
          </div>
          <div>
            <h3 className="font-extrabold text-forest">{t('disclaimer.q2')}</h3>
            <p className="mt-2 text-sm text-ink-muted">{t('disclaimer.a2')}</p>
          </div>
          <div>
            <h3 className="font-extrabold text-forest">{t('disclaimer.q3')}</h3>
            <p className="mt-2 text-sm text-ink-muted">{t('disclaimer.a3')}</p>
          </div>
        </div>
      </section>
    </>
  )
}
