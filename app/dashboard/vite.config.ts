import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  base: '/dashboard/',
  build: {
    outDir: resolve(__dirname, '../../static/dist'),
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/api': 'http://localhost:5100',
      '/assets': 'http://localhost:5100',
    },
  },
})
