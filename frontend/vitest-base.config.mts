import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    pool: 'threads',
    poolOptions: {
      threads: {
        singleThread: true,
      },
      forks: {
        singleFork: true,
      },
    },
    fileParallelism: false,
    testTimeout: 60000,
    hookTimeout: 30000,
    teardownTimeout: 30000,
  },
});
