import { fileURLToPath } from 'node:url'
import { mergeConfig } from 'vite'
import { configDefaults, defineConfig } from 'vitest/config'
import viteConfig from './vite.config'

export default mergeConfig(
  viteConfig,
  defineConfig({
    resolve: {
      // https://github.com/vitest-dev/vitest/issues/1452
      mainFields: ['module']
    },
    test: {
      server: {
        deps: {
          inline: ['echarts', 'vuetify']
        }
      },
      environment: 'jsdom',
      exclude: [...configDefaults.exclude, 'e2e/*'],
      root: fileURLToPath(new URL('./', import.meta.url)),
      coverage: {
        provider: 'v8',
        // text -> terminal summary, html -> browsable report, lcov -> CI tools
        reporter: ['text', 'html', 'lcov'],
        reportsDirectory: './coverage',
        // Count every source file, even ones no test imports, so the percentage
        // reflects the real codebase rather than only what's already covered.
        all: true,
        include: ['src/**/*.{ts,js,vue}'],
        exclude: [
          'src/backend/**', // generated OpenAPI client
          'src/**/*.spec.ts',
          'src/**/__tests__/**',
          'src/main.ts',
          'src/**/*.d.ts'
        ]
      }
    }
  })
)
