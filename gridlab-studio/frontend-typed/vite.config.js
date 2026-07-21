import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
export default defineConfig({
    plugins: [react()],
    base: "/studio/",
    build: {
        outDir: "../frontend-typed-dist",
        emptyOutDir: true,
    },
    server: {
        port: 5173,
        proxy: {
            "/api": "http://127.0.0.1:8000",
        },
    },
    test: {
        environment: "jsdom",
        setupFiles: "./src/test/setup.ts",
        exclude: ["tests/browser/**", "node_modules/**"],
    },
});
