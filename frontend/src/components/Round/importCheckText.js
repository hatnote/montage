// Texts of the import check (#510). The server sends a reason_code with
// reason_params for each checked row and for source errors; they are shown
// with montage-round-check-reason-<code> / montage-round-check-error-<code>.
// Without a translation (or a code), the server's English text is shown,
// marked as English.

// { text, english }: english is true when the server's text is shown
export const reasonText = (t, te, issue) => {
  const code = issue?.reason_code
  const params = issue?.reason_params || []
  if (code === 'same-name') {
    // params: name, row, name, row, ... of the other files
    const others = []
    for (let i = 0; i + 1 < params.length; i += 2) {
      others.push(params[i] + ' ' + t('montage-round-check-row-ref', [params[i + 1]]))
    }
    return { text: t('montage-round-check-reason-same-name', [others.join(', ')]), english: false }
  }
  const key = 'montage-round-check-reason-' + code
  if (code && te(key)) return { text: t(key, params), english: false }
  return { text: issue?.reason || '', english: true }
}

// { text, english } for a failed request: a translated source error if the
// server sent a known reason_code, else its English detail
export const errorText = (t, te, error) => {
  const data = error?.response?.data
  const key = 'montage-round-check-error-' + data?.reason_code
  if (data?.reason_code && te(key)) {
    return { text: t(key, data.reason_params || []), english: false }
  }
  const english = data?.detail || data?.message || error?.message
  if (english) return { text: english, english: true }
  return { text: t('montage-something-went-wrong'), english: false }
}
