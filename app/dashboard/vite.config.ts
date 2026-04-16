import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  base: '/dashboard/',
  build: {
    outDir: resolve(__dirname, '../static/dist'),
    emptyOutDir: true,
    rollupOptions: {
      // /assets/* are served directly by FastAPI — not bundled by Vite
      onwarn(warning, defaultHandler) {
        if (warning.code === 'UNRESOLVED_IMPORT') return
        defaultHandler(warning)
      },
    },
  },
  server: {
    proxy: {
      '/api': 'http://localhost:5100',
      '/assets': 'http://localhost:5100',
    },
  },
  // preview (used by `vite preview` and Playwright tests) — /assets is served
  // by FastAPI at runtime, no proxy needed here
  preview: {
    proxy: {
      '/api': 'http://localhost:5100',
    },
  },
})
