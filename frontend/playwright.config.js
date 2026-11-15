import { defineConfig } from '@playwright/test';
export default defineConfig({ testDir: './tests', workers: 1, use: { baseURL: process.env.FRONTEND_URL || 'http://localhost:8002', viewport: { width: 1280, height: 900 }, launchOptions: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH } : {} }, reporter: 'list' });
