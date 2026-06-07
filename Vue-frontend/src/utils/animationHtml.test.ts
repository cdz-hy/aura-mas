import { describe, expect, it } from 'vitest'
import { escapeJsonForHtml, normalizeAnimationHtml } from './animationHtml'

describe('animationHtml utilities', () => {
  it('escapes script-breaking characters in JSON payloads', () => {
    const escaped = escapeJsonForHtml('</script><img src=x onerror=alert(1)>')
    expect(escaped).toContain('\\u003C/script\\u003E')
    expect(escaped).not.toContain('</script>')
  })

  it('wraps raw animation html in a sandboxed iframe shell', () => {
    const raw = '<!doctype html><html><body><main id="stage"><section class="beat active">动画</section></main></body></html>'
    const wrapped = normalizeAnimationHtml(raw)
    expect(wrapped).toContain('id="animation-html"')
    expect(wrapped).toContain('sandbox="allow-scripts"')
    expect(wrapped).not.toContain('allow-same-origin')
    expect(wrapped).toContain('legacy-control-bar')
  })
})
