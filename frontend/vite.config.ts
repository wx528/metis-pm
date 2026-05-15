import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { readFileSync } from 'fs'
import { resolve } from 'path'

function getVersion() {
  if (process.env.APP_VERSION) return process.env.APP_VERSION
  try {
    return readFileSync(resolve(__dirname, '../VERSION'), 'utf-8').trim()
  } catch {
    return '0.0.0'
  }
}

const version = getVersion()

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  define: {
    __APP_VERSION__: JSON.stringify(version),
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    chunkSizeWarningLimit: 1500,
  },
})
