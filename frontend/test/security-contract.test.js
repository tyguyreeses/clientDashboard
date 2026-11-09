import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const source = (path) => readFile(new URL(path, import.meta.url), 'utf8')

test('frontend login consumes only the one-use server flash endpoint', async () => {
  const login = await source('../src/pages/AdminLoginPage.jsx')

  assert.match(login, /\/api\/auth\/flash/)
  assert.doesNotMatch(login, /URLSearchParams\(window\.location\.search\).*error/)
})

test('frontend uses only the same-origin API proxy', async () => {
  const [utils, viteConfig] = await Promise.all([
    source('../src/utils.js'),
    source('../vite.config.js'),
  ])

  assert.doesNotMatch(utils, /VITE_API_URL|https?:\/\/[^"']+:8000/)
  assert.match(utils, /fetch\(`\$\{API_URL\}\$\{path\}`/)
  assert.doesNotMatch(viteConfig, /127\.0\.0\.1/)
  assert.match(viteConfig, /proxy\s*:\s*\{[\s\S]*["']\/api["']/)
  assert.match(viteConfig, /localhost:8000/)
})
