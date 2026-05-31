import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In production Nginx serves the built SPA and proxies `/api/*` to the API on the
// same origin, so the app only ever uses relative paths. In development the Vite
// dev server stands in for Nginx by proxying `/api` to the local API service.
const LOCAL_API_TARGET = "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: LOCAL_API_TARGET,
        changeOrigin: true,
      },
    },
  },
});
