export const PORTFOLIO_LINK_MAX_LENGTH = 500

export function validPortfolioLink(value: string): string | null {
  const link = value.trim()
  if (!/^https:\/\/[^/]/.test(link) || /[\p{Cc}\s\\]/u.test(link) || link.length > PORTFOLIO_LINK_MAX_LENGTH) {
    return null
  }

  try {
    const parsed = new URL(link)
    return parsed.hostname && !parsed.username && !parsed.password ? link : null
  } catch {
    return null
  }
}
