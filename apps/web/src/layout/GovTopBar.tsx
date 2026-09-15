/** Top utility bar matching typical Government of India portals. */
export function GovTopBar() {
  return (
    <div className="bg-navy text-white">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-1.5 text-xs sm:text-sm">
        <p className="font-medium">
          <span lang="hi">भारत सरकार</span>
          <span className="mx-2 text-white/40" aria-hidden="true">
            |
          </span>
          Government of India
        </p>
        <p className="text-white/85">
          <span lang="hi">आयुष मंत्रालय</span>
          <span className="mx-2 text-white/40" aria-hidden="true">
            |
          </span>
          Ministry of Ayush
        </p>
      </div>
    </div>
  )
}
