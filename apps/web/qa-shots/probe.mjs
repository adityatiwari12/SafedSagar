import { chromium } from 'playwright'
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
await page.goto('http://127.0.0.1:5173/', { waitUntil: 'networkidle' })
const info = await page.evaluate(() => {
  const h1 = document.querySelector('#hero-heading')
  const forest = document.querySelector('section[aria-labelledby="hero-heading"] .bg-forest')
  const cs = (el) => (el ? getComputedStyle(el) : null)
  return {
    h1Color: cs(h1)?.color,
    h1Size: cs(h1)?.fontSize,
    forestBg: cs(forest)?.backgroundColor,
    forestClass: forest?.className?.slice?.(0, 80),
  }
})
console.log(JSON.stringify(info, null, 2))
await browser.close()
