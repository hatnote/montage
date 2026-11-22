export function getWrappedNextIndex(currentIndex, total) {
  if (!total) {
    return 0
  }
  return (currentIndex + 1) % total
}

export function removeVotedFromQueue(items, currentIndex) {
  const queue = Array.isArray(items) ? items.slice() : []
  if (!queue.length) {
    return {
      queue,
      currentIndex: 0,
      current: null,
      next: null
    }
  }

  queue.splice(currentIndex, 1)

  if (!queue.length) {
    return {
      queue,
      currentIndex: 0,
      current: null,
      next: null
    }
  }

  const normalizedIndex = currentIndex >= queue.length ? 0 : currentIndex
  return {
    queue,
    currentIndex: normalizedIndex,
    current: queue[normalizedIndex],
    next: queue[getWrappedNextIndex(normalizedIndex, queue.length)]
  }
}
