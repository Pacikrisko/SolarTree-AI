import assert from 'node:assert/strict'
import test from 'node:test'

test('temporary service errors preserve the session and an expired session returns to sign-in', async () => {
  const entries = new Map()
  globalThis.localStorage = {
    getItem: key => entries.get(key) ?? null,
    setItem: (key, value) => entries.set(key, value),
    removeItem: key => entries.delete(key),
  }
  globalThis.window = new EventTarget()
  const { api, hasAuthToken, setAuthToken } = await import('../src/api.ts')
  setAuthToken('test-session')
  let ended = 0
  window.addEventListener('solartree-session-ended', () => ended++)
  globalThis.fetch = async () => new Response('{}', { status: 503 })
  await assert.rejects(api.me())
  assert.equal(hasAuthToken(), true)
  assert.equal(ended, 0)

  let finish
  globalThis.fetch = () => new Promise(resolve => { finish = resolve })
  const pending = api.me()
  setAuthToken('replacement-session')
  finish(new Response('{}', { status: 401 }))
  await assert.rejects(pending)
  assert.equal(hasAuthToken(), true)
  globalThis.fetch = async () => new Response('{}', { status: 401 })
  await assert.rejects(api.me())
  assert.equal(hasAuthToken(), false)
  assert.equal(ended, 1)
})
