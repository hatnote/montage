export function formatDate(dateString) {
  const options = { year: 'numeric', month: 'short', day: 'numeric' }
  return new Date(dateString).toLocaleDateString('en-US', options)
}

export function getVotingName(voting) {
  const types = {
    yesno: 'montage-round-yesno',
    rating: 'montage-round-rating',
    ranking: 'montage-round-ranking'
  }

  return types[voting]
}

export function getAvatarColor(username) {
  const colors = [
    '#1abc9c',
    '#2ecc71',
    '#3498db',
    '#9b59b6',
    '#34495e',
    '#16a085',
    '#27ae60',
    '#2980b9',
    '#8e44ad',
    '#2c3e50',
    '#f1c40f',
    '#e67e22',
    '#e74c3c',
    '#95a5a6',
    '#f39c12',
    '#d35400',
    '#c0392b',
    '#bdc3c7',
    '#7f8c8d'
  ]

  const sum = stringToColor(username)
  const color = colors[sum % colors.length]
  const rgba = hexToRgba(color, 0.5)

  return rgba
}

function stringToColor(str) {
  let hash = 0
  for (let char of str) {
    hash = char.charCodeAt(0) + ((hash << 5) - hash)
  }
  return Math.abs(hash % 19)
}

function hexToRgba(hex, alpha) {
  const r = parseInt(cutHex(hex).substring(0, 2), 16)
  const g = parseInt(cutHex(hex).substring(2, 4), 16)
  const b = parseInt(cutHex(hex).substring(4, 6), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

function cutHex(h) {
  return h.startsWith('#') ? h.substring(1, 7) : h
}

export function getCommonsImageUrl(image, width = 1280) {
  if (!image) return null

  // Handle different data structures:
  // - image.entry.name (task/vote object with nested entry)
  // - image.name (direct entry object or task with top-level name)
  // - image (string filename)
  const imageName = image.entry?.name || image.name || image
  const encodedName = encodeURIComponent(imageName)

  // Use Special:Redirect which works universally for all file types including TIFF
  // It handles redirects for moved files and performs automatic format conversion
  if (width) {
    return `//commons.wikimedia.org/w/index.php?title=Special:Redirect/file/${encodedName}&width=${width}`
  } else {
    return `//commons.wikimedia.org/w/index.php?title=Special:Redirect/file/${encodedName}`
  }
}

// Badge i18n key for a round's server-computed import_state
// (hatnote/montage#622), or null when there is nothing to show.
export function getImportBadgeKey(importState) {
  if (!importState || !importState.blocks_activation) return null
  if (importState.blocked_reason === 'import_failed') return 'montage-import-badge-failed'
  return 'montage-import-badge-importing'
}

// The server sends naive UTC ISO dates without a zone; new Date() would
// read them as local time. locale: the vue-i18n locale (e.g. 'pt-br').
export function formatUtcDateTime(s, locale) {
  if (!s) return ''
  const date = new Date(s.endsWith('Z') ? s : s + 'Z')
  try {
    return date.toLocaleString(locale || undefined)
  } catch (e) {
    // RangeError: a locale code the browser does not accept
    return date.toLocaleString()
  }
}

// Import warnings are dicts ({'duplicate import': '...'}) or plain strings
export function formatImportWarning(warning) {
  return typeof warning === 'string' ? warning : Object.values(warning || {}).join(' ')
}

// Bounded poll of an import job (hatnote/montage#622): call fetchJob()
// every intervalMs, at most maxMs / intervalMs times. onFinished(job) once
// the job has succeeded or failed; onTimeout() when the attempts run out
// (failed requests count as attempts). Returns a function that stops it.
export function pollImportJob({
  fetchJob,
  onFinished,
  onTimeout,
  intervalMs = 3000,
  maxMs = 60000
}) {
  const maxAttempts = Math.max(1, Math.floor(maxMs / intervalMs))
  let attempts = 0
  let timer = null
  let stopped = false

  const next = () => {
    if (stopped) return
    if (attempts >= maxAttempts) {
      stopped = true
      onTimeout()
    } else {
      timer = setTimeout(tick, intervalMs)
    }
  }

  const tick = () => {
    timer = null
    if (stopped) return
    attempts += 1
    Promise.resolve()
      .then(fetchJob)
      .then((job) => {
        if (stopped) return
        if (job && (job.status === 'succeeded' || job.status === 'failed')) {
          stopped = true
          onFinished(job)
        } else {
          next()
        }
      })
      .catch(next)
  }

  timer = setTimeout(tick, intervalMs)
  return () => {
    stopped = true
    if (timer) clearTimeout(timer)
    timer = null
  }
}
