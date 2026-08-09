import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  esbuild: { jsx: "automatic" },
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  test: {
    environment: "node",
    exclude: ["e2e/**", "node_modules/**", ".next/**"],
    setupFiles: ["./src/test/setup.ts"],
    coverage: { reporter: ["text", "json-summary"] },
  },
});
