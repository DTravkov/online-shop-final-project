import '@testing-library/jest-dom/vitest'
import { afterEach, vi } from 'vitest'

// jsdom не умеет прокручивать страницу, поэтому подменяем scrollTo.
window.scrollTo = vi.fn()

afterEach(() => {
  localStorage.clear()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})
