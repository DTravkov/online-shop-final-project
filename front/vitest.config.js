import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// Отдельный конфиг для тестов, чтобы не менять vite.config.js команды.
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/__tests__/setup.js'],
    include: ['src/__tests__/**/*.test.{js,jsx}'],
  },
})
