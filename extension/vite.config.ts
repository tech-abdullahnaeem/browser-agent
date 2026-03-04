import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { resolve } from "path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": resolve(__dirname, "src"),
    },
  },
  // Chrome extensions need relative paths (no leading /)
  base: "",
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        "service-worker": resolve(__dirname, "src/background/service-worker.ts"),
        content: resolve(__dirname, "src/content/index.tsx"),
        sidepanel: resolve(__dirname, "src/sidepanel/index.html"),
        popup: resolve(__dirname, "src/popup/index.html"),
      },
      output: {
        entryFileNames: "[name].js",
        chunkFileNames: "chunks/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]",
      },
    },
    // Chrome extensions need inline sourcemaps for content scripts
    sourcemap: process.env.NODE_ENV === "development" ? "inline" : false,
    // Don't minify in dev for easier debugging
    minify: process.env.NODE_ENV === "production",
    // Target modern Chrome
    target: "chrome120",
  },
  // Ensure CSS is extracted for shadow DOM injection
  css: {
    modules: {
      localsConvention: "camelCase",
    },
  },
});
