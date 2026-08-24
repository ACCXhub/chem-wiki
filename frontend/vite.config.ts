import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react()],
  define: {
    // Ketcher's browser-targeted Node util shim reads this expression unguarded.
    'process.env.NODE_DEBUG': 'undefined',
    // Draft.js/fbjs uses Browserify's `global` alias for standard browser globals.
    global: 'globalThis',
  },
  server: {
    proxy: {
      '/v1': 'http://localhost:8000',
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
  },
})
