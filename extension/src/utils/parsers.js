import { format } from 'date-fns'

function extractSymbolFromUrl(url) {
  if (!url) return null

  try {
    const urlObj = new URL(url)

    if (urlObj.hostname.includes('finance.yahoo.com')) {
      const match = urlObj.pathname.match(/\/quote\/([^\/?]+)/)
      return match ? decodeURIComponent(match[1]) : null
    }

    if (urlObj.hostname.includes('google.com') && urlObj.pathname.includes('/finance')) {
      const match = urlObj.pathname.match(/\/quote\/([^\/?]+)/)
      if (match) {
        return decodeURIComponent(match[1])
      }
    }
  } catch (e) {
    return null
  }

  return null
}

function formatDate(dateStr) {
  if (!dateStr) return ''

  try {
    const date = new Date(dateStr)
    if (isNaN(date.getTime())) return ''

    return format(date, 'MMM d, yyyy')
  } catch (e) {
    return ''
  }
}

export { extractSymbolFromUrl, formatDate }