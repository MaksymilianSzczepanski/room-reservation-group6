import { defineConfig } from '@playwright/test';
export default defineConfig({ testDir: './tests', use: { baseURL: process.env.FRONTEND_URL || 'http://localhost:8002', viewport: { width: 1280, height: 900 } }, reporter: 'list' });
