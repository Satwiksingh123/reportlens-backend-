import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    // Bind every interface, not just the default. Node 17+ resolves "localhost" to IPv6
    // ::1 first, so Vite's default binding left http://127.0.0.1:5173 refusing connections
    // outright - browsers and tools that reach for IPv4 saw "site can't be reached" even
    // though the server was running. This also lets you open the app from a phone on the
    // same network, which matters here: photographing a report is the main mobile use case.
    host: true,
  },
})
