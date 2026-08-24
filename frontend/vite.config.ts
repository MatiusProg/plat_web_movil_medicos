import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'

// El puerto 5173 es el que ya está en CORS_ALLOWED_ORIGINS del backend
// (config/settings.py). Cambiarlo obliga a tocar el .env de los seis.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    // `import.meta.dirname` y no `__dirname`: Vite 8 lee esta configuración de
    // forma nativa y ahí `__dirname` no existe.
    alias: { '@': path.resolve(import.meta.dirname, './src') },
  },
  server: {
    port: 5173,
  },
})
