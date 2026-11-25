const assert = require('node:assert/strict')
const {chromium} = require(process.env.BROWSER_MODULE)
const origin = 'http://127.0.0.1:10000'

async function main() {
  const browser = await chromium.launch({executablePath:process.env.CHROME_PATH})
  try {
    const page = await browser.newPage({viewport:{width:1440,height:900}})
    const errors = []
    page.on('pageerror', error => errors.push(error.message))
    page.on('console', msg => { if(msg.type()==='error') errors.push(msg.text()) })
    await page.goto(origin)
    await page.locator('#signin-email').waitFor()
    assert.equal(await page.locator('.signin-form').evaluate(form => form.checkValidity()), false)
    assert.equal(await page.evaluate(()=>performance.getEntriesByType('resource').some(r=>/Charts-/.test(new URL(r.name).pathname))),false)
    await page.locator('.signin-reveal').click()
    assert.equal(await page.locator('#signin-password').getAttribute('type'),'text')
    await page.locator('a[href="#/forgot-password"]').click()
    await page.locator('input[autocomplete=email]').waitFor()
    await page.locator('a[href="#/overview"]').click()
    await page.locator('.signin-switch button').click()
    await page.locator('#signin-name').fill('Browser test')
    await page.locator('#signin-email').fill('browser@example.com')
    await page.locator('#signin-password').fill('Test-password-7249')
    await page.locator('.signin-submit').click()
    await page.locator('.dashboard').waitFor()
    await page.locator('.dashboard button').filter({hasText:/Добави дърво|Add tree/i}).first().click()
    const form = page.locator('.pairing-modal form.modal-form')
    await form.locator('input').nth(0).fill('CI-TREE')
    await form.locator('input').nth(1).fill(process.env.TEST_CLAIM)
    await form.locator('button.full').click()
    await form.locator('.paired-model').waitFor()
    await form.locator('input').nth(2).fill('Browser tree')
    await form.locator('input').nth(3).fill('Sofia')
    await form.locator('button[type=submit]').click()
    await form.waitFor({state:'hidden'})
    const token = await page.evaluate(()=>localStorage.getItem('solartree_token'))
    const response = await page.request.get(origin+'/api/trees',{headers:{Authorization:'Bearer '+token}})
    const [tree] = await response.json()
    assert.equal(tree.name,'Browser tree')
    for(const width of [390,768,1440]){
      await page.setViewportSize({width,height:900})
      for(const section of ['overview','trees','detail','insights','assistant','service','settings','profile']){
        const url = origin+'/#/'+section+'/'+tree.id
        await page.goto(url)
        await page.reload()
        await page.locator('.page-body').first().waitFor()
        await page.waitForLoadState('networkidle')
        assert.equal(new URL(page.url()).hash,new URL(url).hash)
        assert.ok(await page.locator('h1').first().innerText())
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'overflow '+section+' '+width)
      }
    }
    const theme = () => page.locator('html').getAttribute('data-theme')
    const before = await theme()
    await page.locator('.theme-switch:visible').first().click()
    assert.notEqual(await theme(),before)
    const language = await page.locator('html').getAttribute('lang')
    await page.locator('.language-switch:visible').first().click()
    assert.notEqual(await page.locator('html').getAttribute('lang'),language)
    assert.deepEqual(errors,[])
  } finally { await browser.close() }
}
main().catch(error=>{console.error(error);process.exitCode=1})
