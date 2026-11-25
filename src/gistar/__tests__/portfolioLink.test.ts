import { expect, it } from 'vitest'
import { validPortfolioLink } from '../views/api/portfolioLink'

it('preserves a valid explicit HTTPS URL from the submission API', () => {
  expect(validPortfolioLink('  https://github.com/learner/portfolio  ')).toBe('https://github.com/learner/portfolio')
  expect(validPortfolioLink('https://example.test/artifact?q=1#section')).toBe('https://example.test/artifact?q=1#section')
})

it.each([
  '', 'http://example.test/my-work', '/my-work', 'https:example.test/work',
  'https:///example.test/work', 'https://', 'https://malformed host.test/work',
  'https://name:secret@example.test/work', 'https://example.test\\work', 'https://example.test/' + 'x'.repeat(500),
])('rejects an invalid portfolio link (%s)', value => {
  expect(validPortfolioLink(value)).toBeNull()
})
