import jurorService from '@/services/jurorService'
import alertService from '@/services/alertService'

const STORAGE_KEY = 'montage_vote_drafts'

function isAuthError(error) {
  const status = error?.response?.status
  return status === 401 || status === 403
}

function loadDrafts() {
  if (typeof localStorage === 'undefined') return []

  try {
    const drafts = JSON.parse(localStorage.getItem(STORAGE_KEY))
    return Array.isArray(drafts) ? drafts : []
  } catch {
    return []
  }
}

function saveDrafts(drafts) {
  if (typeof localStorage === 'undefined') return

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(drafts))
  } catch {
    // Ignore storage write failures and keep the current UI state unchanged.
  }
}

function upsertDraft(roundId, taskId, value) {
  const drafts = loadDrafts()
  const nextDraft = { roundId, taskId, value, timestamp: Date.now() }
  const nextDrafts = drafts.filter((draft) => draft.roundId !== roundId || draft.taskId !== taskId)

  nextDrafts.push(nextDraft)
  saveDrafts(nextDrafts)
}

export function useVoteDraft(roundId) {
  function handleVoteError(error, taskId, value) {
    if (!isAuthError(error)) {
      return false
    }

    upsertDraft(roundId, taskId, value)
    alertService.error(
      {
        message: 'Your session has expired. The vote was kept locally and will be retried after you sign in again.'
      },
      8000
    )

    return true
  }

  async function replayDrafts() {
    const storedDrafts = loadDrafts()
    const roundDrafts = storedDrafts.filter((draft) => draft.roundId === roundId)

    if (!roundDrafts.length) {
      return { appliedCount: 0, failedCount: 0 }
    }

    const failedDrafts = []
    let appliedCount = 0

    for (const draft of roundDrafts) {
      try {
        await jurorService.setRating(draft.roundId, {
          ratings: [{ task_id: draft.taskId, value: draft.value }]
        })
        appliedCount += 1
      } catch {
        failedDrafts.push(draft)
      }
    }

    const otherDrafts = storedDrafts.filter((draft) => draft.roundId !== roundId)
    saveDrafts([...otherDrafts, ...failedDrafts])

    if (failedDrafts.length) {
      alertService.error(
        {
          message: `${failedDrafts.length} locally saved vote(s) could not be submitted and were kept for retry.`
        },
        8000
      )
    } else if (appliedCount) {
      alertService.success(`${appliedCount} locally saved vote(s) submitted.`)
    }

    return { appliedCount, failedCount: failedDrafts.length }
  }

  return { handleVoteError, replayDrafts }
}

export { isAuthError }
