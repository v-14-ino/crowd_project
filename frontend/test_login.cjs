const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  page.on('request', request => {
    if (request.url().includes('/api/auth/login')) {
      console.log('>> REQUEST:', request.method(), request.url());
      console.log('>> POST DATA:', request.postData());
    }
  });

  page.on('response', async response => {
    if (response.url().includes('/api/auth/login')) {
      console.log('<< RESPONSE:', response.status(), response.url());
      try {
        console.log('<< BODY:', await response.text());
      } catch (e) {
        console.log('<< NO BODY OR ERROR');
      }
    }
  });

  await page.goto('http://localhost:5173/login');
  await page.fill('input[type="email"]', 'officer@municipal.gov');
  await page.fill('input[type="password"]', 'Officer@123');
  await page.click('button[type="submit"]');

  await page.waitForTimeout(2000);
  await browser.close();
})();
