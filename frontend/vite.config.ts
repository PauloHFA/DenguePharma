/// <reference types="vitest" />
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, "..", "DENGUEPHARMA_");
  return {
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": env.DENGUEPHARMA_API_TARGET || "http://localhost:8080" },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
  },
  };
});

