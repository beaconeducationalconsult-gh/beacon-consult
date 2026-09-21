import { defineConfig } from 'vitest/config'

/*
 * The emulator config. Deliberately separate from vitest.config.js: these tests
 * need running Firestore and Storage emulators (JVM programs), so they cannot be
 * part of `make check` — `yarn test` only ever collects `src/**`. Run them with:
 *
 *   yarn test:rules
 *
 * which starts both emulators, runs this config, and shuts them down again.
 * CI runs the same command (the `rules` job in .github/workflows/ci.yml).
 */
export default defineConfig({
  test: {
    environment: 'node',
    include: ['tests/rules/**/*.test.js'],
    // One emulator holds one database per project, so two files in parallel
    // would interleave their writes.
    fileParallelism: false,
    // Every assertion is a round trip through the emulator; a cold first
    // request (and the rules upload) is slower than a unit test.
    testTimeout: 20_000,
    hookTimeout: 60_000,
  },
})
