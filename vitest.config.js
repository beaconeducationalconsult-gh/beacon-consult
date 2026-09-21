import { defineConfig } from 'vitest/config'

/*
 * Tests are plain modules under src/ that need no DOM: pure helpers
 * (src/lib, buildTree) and contract checks over the committed curriculum
 * bundle in public/curriculum. Kept separate from vite.config.js so the app
 * build never loads the test runner config.
 */
export default defineConfig({
  test: {
    environment: 'node',
    include: ['src/**/*.test.js'],
  },
})
