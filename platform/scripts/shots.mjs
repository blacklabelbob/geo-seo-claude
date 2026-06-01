// Logs in as the demo user and screenshots the product. Run after `npm run dev`.
import { chromium } from "playwright";

const BASE = "http://localhost:3000";
const OUT = "/Users/robertacheson/Projects/geo-seo-claude/clients/stg/deliverables";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

// login
await page.goto(`${BASE}/login`);
await page.fill('input[name="email"]', "demo@geo.local");
await page.fill('input[name="password"]', "geodemo123");
await page.click('button:has-text("Sign in")');
await page.waitForURL(`${BASE}/`, { timeout: 15000 });
await page.waitForTimeout(800);
await page.screenshot({ path: `${OUT}/platform-dashboard.png` });
console.log("✓ dashboard.png");

// open Electron site detail
await page.click("text=Electron Srl");
await page.waitForTimeout(1000);
await page.screenshot({ path: `${OUT}/platform-site-detail.png`, fullPage: true });
console.log("✓ site-detail.png");

// pricing
await page.goto(`${BASE}/pricing`);
await page.waitForTimeout(500);
await page.screenshot({ path: `${OUT}/platform-pricing.png` });
console.log("✓ pricing.png");

await browser.close();
