import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    // The backend's CORS setting allows http://localhost:5173 only. strictPort makes Vite fail
    // loudly if that port is busy, instead of silently moving to one the backend would block.
    port: 5173,
    strictPort: true,
  },
});
