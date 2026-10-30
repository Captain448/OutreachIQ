import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    watch: false,
    pool: 'forks',
    forks: {
      singleFork: true,
    },
    poolTimeout: 180000,
    testTimeout: 60000,
    fileParallelism: false,
    isolate: false,
  },
});
