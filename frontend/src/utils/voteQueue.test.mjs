import test from 'node:test'
import assert from 'node:assert/strict'

import { getWrappedNextIndex, removeVotedFromQueue } from './voteQueue.js'

test('wrapped next index loops to start', () => {
  assert.equal(getWrappedNextIndex(0, 3), 1)
  assert.equal(getWrappedNextIndex(1, 3), 2)
  assert.equal(getWrappedNextIndex(2, 3), 0)
  assert.equal(getWrappedNextIndex(0, 0), 0)
})

test('remove voted item advances to next remaining item', () => {
  const items = [{ id: 'A' }, { id: 'B' }, { id: 'C' }]
  const result = removeVotedFromQueue(items, 0)

  assert.deepEqual(result.queue.map((i) => i.id), ['B', 'C'])
  assert.equal(result.current.id, 'B')
  assert.equal(result.next.id, 'C')
  assert.equal(result.currentIndex, 0)
})

test('remove voted last item wraps current to first', () => {
  const items = [{ id: 'A' }, { id: 'B' }, { id: 'C' }]
  const result = removeVotedFromQueue(items, 2)

  assert.deepEqual(result.queue.map((i) => i.id), ['A', 'B'])
  assert.equal(result.current.id, 'A')
  assert.equal(result.next.id, 'B')
  assert.equal(result.currentIndex, 0)
})

test('single-item queue becomes empty after vote', () => {
  const items = [{ id: 'A' }]
  const result = removeVotedFromQueue(items, 0)

  assert.deepEqual(result.queue, [])
  assert.equal(result.current, null)
  assert.equal(result.next, null)
  assert.equal(result.currentIndex, 0)
})
