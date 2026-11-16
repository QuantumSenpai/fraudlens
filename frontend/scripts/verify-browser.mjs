/* Synthetic boundary tests. Starts an isolated fixture API and the existing Next app. */
import { chromium, expect } from '@playwright/test';
import { createServer } from 'node:http';
import { spawn } from 'node:child_process';
import { randomBytes } from 'node:crypto';
import { mkdir, writeFile } from 'node:fs/promises';
import assert from 'node:assert/strict';
async function recordInteractions(browser, origin, results) {
  await mkdir('screenshots/recordings',{recursive:true});
  for(const mobile of [false,true]) {
    const context=await browser.newContext({viewport:{width:mobile?390:1440,height:mobile?844:960},hasTouch:mobile,isMobile:mobile,recordVideo:{dir:'screenshots/recordings',size:{width:mobile?390:1440,height:mobile?844:960}}});
    const p=await context.newPage();
    await p.addInitScript(()=>{window.__motionSamples={frames:[],longTasks:[],shifts:[]};let last=0;const sample=time=>{if(last)window.__motionSamples.frames.push(time-last);last=time;requestAnimationFrame(sample)};requestAnimationFrame(sample);new PerformanceObserver(list=>list.getEntries().forEach(e=>window.__motionSamples.longTasks.push(e.duration))).observe({type:'longtask',buffered:true});new PerformanceObserver(list=>list.getEntries().forEach(e=>{if(!e.hadRecentInput)window.__motionSamples.shifts.push(e.value)})).observe({type:'layout-shift',buffered:true});});
    await p.goto(origin);await p.waitForTimeout(800);
    if(mobile)await p.getByRole('button',{name:'Explore',exact:true}).tap();else await p.getByRole('button',{name:'Explore',exact:true}).hover();
    await p.waitForTimeout(650);
    if(!mobile)for(const title of ['Product flow','Merchant demo','Reviewer dashboard','Data use']) {await p.getByRole('navigation',{name:'Explore destinations'}).getByRole('link',{name:new RegExp(title)}).hover();await p.waitForTimeout(450);}
    await p.screenshot({path:`screenshots/menu-${mobile?'390':'1440'}.png`});
    if(mobile)await p.getByRole('button',{name:'Close navigation'}).tap();else await p.mouse.move(30,850);
    await p.waitForTimeout(800);
    if(mobile)await p.locator('.decision-stage').scrollIntoViewIfNeeded();
    for(const name of ['REVIEW','BLOCK','ALLOW']){await p.getByRole('button',{name,exact:true}).click();await p.waitForTimeout(750);}
    await p.mouse.wheel(0,mobile?650:600);await p.waitForTimeout(1000);
    const metrics=await p.evaluate(()=>({...window.__motionSamples,cls:window.__motionSamples.shifts.reduce((sum,n)=>sum+n,0)}));
    await writeFile(`screenshots/motion-${mobile?'mobile':'desktop'}.json`,JSON.stringify(metrics,null,2));
    const video=p.video();await context.close();await video.saveAs(`screenshots/recordings/${mobile?'mobile-menu':'desktop-walkthrough'}.webm`);await video.delete();
  }
  results.push('Recorded desktop and mobile interaction walkthroughs');
}
const origin = 'http://127.0.0.1:3024';
const checkId = '00000000-0000-4000-8000-000000000001';
let decision = 'ALLOW', approved = false, capture = false, delay = 0, failing = false;
const calls = [], results = [], errors = [], expectedNetworkErrors = [];
let intentionallyOffline = false;
const stats = {total_checks:0,decision_split:{ALLOW:0,REVIEW:0,BLOCK:0},flagged_count:0,flagged_rate_percent:0,top_triggered_rules:[],average_latency_ms:null,p95_scoring_latency_ms:null,last_24h_hourly_counts:[]};
const review = {id:checkId,user_id:'fixture-user',device_id:'fixture-device',amount:95000,currency:'INR',payment_method:'upi',final_score:40,reasons:[{rule:'STRUCTURING',detail:'Illustrative nearby payments',weight:35}],created_at:'2026-11-16T00:00:00Z',review:null};
const reviews=[review,{...review,id:'00000000-0000-4000-8000-000000000002',user_id:'fixture-user-2'}];
const fixture = createServer(async (req,res) => {
  calls.push({url:req.url,method:req.method,key:req.headers['idempotency-key']});
  assert.equal(req.headers[req.url.includes('/admin/') ? 'authorization' : 'x-api-key'],req.url.includes('/admin/') ? 'Bearer fixture-admin' : 'fixture-merchant');
  if(req.url==='/v1/admin/feed'){res.writeHead(200,{'Content-Type':'text/event-stream'});res.write(': fixture connected\n\n');const timer=setInterval(()=>res.write(': heartbeat\n\n'),1000);req.on('close',()=>clearInterval(timer));return;}
  let body=''; for await(const chunk of req) body+=chunk;
  if(delay) await new Promise(r=>setTimeout(r,delay));
  const json=(value,status=200)=>{res.writeHead(status,{'Content-Type':'application/json'});res.end(JSON.stringify(value));};
  if(failing) return json({error:{message:'Fixture temporarily unavailable'}},503);
  if(req.url==='/v1/signals') return json({device_id:'fixture-device',trust_score:50});
  if(req.url==='/v1/checks') return json({check_id:checkId,decision,final_score:30,ml_score:20,rule_score:40,reasons:decision==='ALLOW'?[]:review.reasons,model_version:'fixture-only',ml_factors:[],latency_ms:18});
  if(req.url==='/v1/payments/order') return decision==='BLOCK'||decision==='REVIEW'&&!approved ? json({error:{message:'Review approval is pending'}},409) : json({order_id:'order_fixture',amount:25000,currency:'INR',key_id:'rzp_test_fixture'});
  if(req.url==='/v1/payments/verify') return json({order_id:'order_fixture',payment_id:'pay_fixture',status:capture?'captured':'authorized'});
  if(req.url==='/v1/admin/stats') return json(stats);
  if(req.url==='/v1/admin/evaluation') return json({labels_total:0});
  if(req.method==='POST'&&req.url.startsWith('/v1/admin/reviews/')){const item=reviews.find(item=>req.url.endsWith(item.id));if(!item)return json({},404);if(item.review)return json({error:{message:'Review already resolved'}},409);const resolution=JSON.parse(body);approved=resolution.outcome==='approve';item.review={...resolution,created_at:'2026-11-16T01:00:00Z'};return json({resolved:true});}
  if(req.url.startsWith('/v1/admin/reviews')) {const filter=new URL(req.url,'http://fixture').searchParams.get('status');return json(reviews.filter(item=>filter==='pending'?!item.review:filter==='reviewed'?!!item.review:true));}
  json({error:{message:'Fixture route missing'}},404);
});
await new Promise(r=>fixture.listen(3034,'127.0.0.1',r));
const app = spawn(process.execPath,['node_modules/next/dist/bin/next','dev','--hostname','127.0.0.1','--port','3024'],{env:{...process.env,FRAUDLENS_API_URL:'http://127.0.0.1:3034',FRAUDLENS_API_KEY:'fixture-merchant',FRAUDLENS_ADMIN_TOKEN:'fixture-admin',DEMO_PASSWORD:'fixture-password',ADMIN_PASSWORD:'fixture-password',SESSION_SECRET:randomBytes(32).toString('hex'),SITE_URL:origin},stdio:['ignore','pipe','pipe']});
let appLog=''; app.stdout.on('data',v=>appLog+=v);app.stderr.on('data',v=>appLog+=v);
let browser, page;
try {
  for(let i=0;i<90;i++){try{if((await fetch(origin)).ok)break;}catch{}await new Promise(r=>setTimeout(r,500));if(i===89)throw Error(appLog);}
  browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_EXECUTABLE?{executablePath:process.env.CHROMIUM_EXECUTABLE}:{})});
  const context=await browser.newContext();
  page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(intentionallyOffline && m.text().includes('ERR_INTERNET_DISCONNECTED')) expectedNetworkErrors.push(m.text()); else if(m.type()==='warning'||m.type()==='error'&&!m.text().includes('status of'))errors.push(m.text());});
  const check=(name,value)=>{assert(value,name);results.push(name); if(!name.startsWith("Layout")&&!name.startsWith("Footer"))console.log(name);};
  const shot=async name=>{await page.evaluate(()=>window.scrollTo({top:0,behavior:"instant"}));await page.waitForTimeout(100);await page.screenshot({path:`screenshots/${name}.png`,fullPage:true});};
  await mkdir('screenshots',{recursive:true});
  for(const width of [1440,1024,768,390,320]){
    await page.setViewportSize({width,height:960});
    for(const path of ['/','/how-it-works','/privacy','/access','/access?role=admin']){
      await page.goto(origin+path); await page.locator('h1').waitFor();
      await page.waitForTimeout(750);
      check(`Layout ${path} at ${width}`,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
      check(`Footer ${path} at ${width}`,await page.getByText('Made by QuantumSenpai').count()===1);
      await shot(`${path==='/'?'landing':path==='/how-it-works'?'how':path==='/privacy'?'privacy':path.includes('admin')?'reviewer-access':'access'}-${width}`);
    }
  }
  // Mobile uses a modal panel and touch semantics, independently of desktop hover.
  await page.setViewportSize({width:390,height:844});await page.goto(origin);
  await page.getByRole('button',{name:'Explore',exact:true}).click();
  await expect(page.getByRole('dialog')).toHaveCSS('opacity','1');
  check('Menu contains keyboard focus',await page.getByRole('dialog').evaluate(n=>n.contains(document.activeElement)));
  for(let i=0;i<7;i++)await page.keyboard.press('Tab');
  check('Mobile menu traps keyboard focus',await page.getByRole('dialog').evaluate(n=>n.contains(document.activeElement)));
  await page.keyboard.press('Escape');await page.getByRole('dialog').waitFor({state:'detached'});await expect(page.getByRole('button',{name:'Explore',exact:true})).toBeFocused();check('Escape restores trigger focus',true);
  await page.getByRole('button',{name:'Explore',exact:true}).click();await page.getByRole('navigation',{name:'Explore destinations'}).getByRole('link',{name:/Data use/}).click();await page.waitForURL('**/privacy');await page.getByRole('dialog').waitFor({state:'detached'});check('Menu route closes panel',true);
  await page.setViewportSize({width:1440,height:960});await page.goto(origin);
  for(const name of ['ALLOW','BLOCK','REVIEW']){await page.getByRole('button',{name,exact:true}).click();check(`Illustrative ${name}`,await page.getByRole('button',{name,exact:true}).getAttribute('aria-pressed')==='true');}
  const trigger=page.getByRole('button',{name:'Explore',exact:true});
  await trigger.hover();await expect(page.getByRole('dialog')).toHaveCSS('opacity','1');
  const nav=page.getByRole('navigation',{name:'Explore destinations'});
  await nav.getByRole('link',{name:/Product flow/}).hover();await page.waitForTimeout(400);
  check('Pointer bridge keeps menu open',await trigger.getAttribute('aria-expanded')==='true');
  for(let i=0;i<3;i++)for(const name of ['Product flow','Merchant demo','Reviewer dashboard','Data use'])await nav.getByRole('link',{name:new RegExp(name)}).hover();
  await page.waitForTimeout(400);await page.screenshot({path:'screenshots/navigation-desktop.png'});
  check('One moving orange menu highlight',await page.locator('.explore-highlight').count()===1);
  const selectedRow=await nav.getByRole('link',{name:/Data use/}).boundingBox();const selectedFill=await page.locator('.explore-highlight').boundingBox();check('Highlight settles on active row',Math.abs(selectedRow.y-selectedFill.y)<2&&Math.abs(selectedRow.height-selectedFill.height)<2);check('Clipped contrast text aligns with each navigation row',await nav.evaluate(n=>Array.from(n.querySelectorAll(':scope > a strong')).every((title,index)=>{const duplicate=n.querySelectorAll('.explore-ink strong')[index];return Math.abs(title.getBoundingClientRect().top-duplicate.getBoundingClientRect().top)<.1})));
  await page.mouse.move(20,800);await page.getByRole('dialog').waitFor({state:'detached'});check('Hover leave reverses reveal',true);
  await trigger.focus();await page.keyboard.press('Enter');await expect(page.getByRole('dialog')).toHaveCSS('opacity','1');await expect(nav.getByRole('link',{name:/Product flow/})).toBeFocused();
  await page.keyboard.press('Tab');await expect(nav.getByRole('link',{name:/Merchant demo/})).toBeFocused();await expect(page.locator('.explore-highlight')).toHaveCSS('opacity','1');check('Keyboard navigation moves highlight',true);
  await page.keyboard.press('Escape');await page.getByRole('dialog').waitFor({state:'detached'});await expect(trigger).toBeFocused();
  await page.keyboard.press('Space');await expect(page.getByRole('dialog')).toHaveCSS('opacity','1');check('Space opens navigation',true);
  await page.getByRole('button',{name:'Close navigation'}).click();await page.getByRole('dialog').waitFor({state:'detached'});
  // Interrupt a closing timeline by reopening from the keyboard.
  await trigger.focus();await page.keyboard.press('Enter');await page.waitForTimeout(100);await page.keyboard.press('Escape');await trigger.focus();await page.keyboard.press('Enter');await expect(page.getByRole('dialog')).toHaveCSS('opacity','1');check('Rapid reverse and reopen stays usable',true);
  await page.setViewportSize({width:1024,height:768});await page.getByRole('dialog').waitFor({state:'detached'});check('Resize closes navigation',true);
  await page.setViewportSize({width:1440,height:960});
  await page.goto(origin+'/demo');await page.waitForURL('**/access');check('Protected demo redirects',true);
  await page.getByLabel('Password').fill('wrong-password');await page.getByRole('button',{name:'Continue',exact:true}).click();await page.getByRole('alert').waitFor();await expect(page.getByRole('button',{name:'Continue',exact:true})).toBeEnabled();check('Invalid password shown',true);
  await page.goto(origin+'/access?role=admin');await page.getByLabel('Password').fill('fixture-password');await page.getByRole('button',{name:'Continue',exact:true}).click();await page.waitForURL('**/admin');await page.getByText('No hourly activity yet').waitFor();await expect(page.getByRole('button',{name:'Refresh data',exact:true})).toBeEnabled();
  check('Dashboard empty state',true);await page.getByRole('button',{name:'Refresh data',exact:true}).click();await expect(page.getByRole('button',{name:'Refresh data',exact:true})).toBeEnabled();await page.getByRole('button',{name:'Reconnect feed'}).click();await page.getByText('Connected',{exact:true}).waitFor();check('Dashboard refresh and feed reconnect',true);await shot('dashboard-1440');
  for(const width of [1024,768,390,320]){await page.setViewportSize({width,height:960});check(`Dashboard layout ${width}`,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await shot(`dashboard-${width}`);}
  await page.getByRole('button',{name:'Evaluation',exact:true}).click();await page.getByText('Not enough labelled cases').waitFor();check('Evaluation empty state',true);
  await page.getByRole('button',{name:'Reviews',exact:true}).click();await page.getByRole('button',{name:'Approve',exact:true}).first().waitFor();
  for(const outcome of ['Approve','Reject']){await page.getByRole('button',{name:outcome,exact:true}).first().click();await page.getByRole('dialog').waitFor();await page.keyboard.press('Escape');check(`${outcome} dialog Escape`,await page.getByRole('dialog').count()===0);}
  await page.getByRole('button',{name:'Approve',exact:true}).first().click();await page.getByLabel('Reviewer name').fill('fixture-reviewer');await page.getByLabel('Note').fill('Synthetic browser test');await page.getByRole('button',{name:'Confirm approve'}).click();await page.getByText('Review approved and feedback label saved.').waitFor();check('Reviewer approval submitted',approved);await page.getByRole('button',{name:'Reject',exact:true}).click();await page.getByLabel('Reviewer name').fill('fixture-reviewer');await page.getByRole('button',{name:'Confirm reject'}).click();await page.getByText('Review rejected and feedback label saved.').waitFor();check('Reviewer rejection submitted',!approved);
  for(const filter of ['Reviewed','All','Pending']){await page.getByRole('button',{name:filter,exact:true}).click();await page.waitForTimeout(100);if(filter==='Reviewed')await shot('reviews-390');}

  check('Review pagination boundaries',await page.getByRole('button',{name:'Previous'}).isDisabled()&&await page.getByRole('button',{name:'Next',exact:true}).isDisabled());
  await page.goto(origin+'/demo');await page.getByText('Waiting for a check').waitFor();await shot('merchant-390');
  await page.setViewportSize({width:1440,height:960});await shot('merchant-1440');await context.grantPermissions(['geolocation']);await context.setGeolocation({latitude:0,longitude:0});await page.getByRole('button',{name:'Add optional location'}).click();await page.getByText('Approximate location added: 0.000, 0.000').waitFor();await page.getByRole('button',{name:'Update location'}).click();await expect(page.getByRole('button',{name:'Update location'})).toBeEnabled();await page.getByRole('button',{name:'Remove location'}).click();check('Synthetic optional location can be added, updated, and removed',await page.getByText(/Approximate location added/).count()===0);
  const submit=async()=>{await page.getByLabel('Merchant user ID').fill('fixture-user');await page.getByLabel('Amount in INR').fill('250');await page.getByRole('button',{name:'Run fraud check'}).click();};
  for(const method of ['card','netbanking','wallet','upi'])await page.getByLabel('Payment method').selectOption(method);
  await page.route('https://checkout.razorpay.com/**',route=>route.fulfill({contentType:'application/javascript',body:`window.Razorpay=class {constructor(options){this.options=options} on(){} open(){this.options.handler({razorpay_order_id:'order_fixture',razorpay_payment_id:'pay_fixture',razorpay_signature:'${'a'.repeat(64)}'})}}` }));
  for(const value of ['BLOCK','REVIEW','ALLOW']){
    decision=value;approved=false;delay=500;await submit();await page.getByText('Registering signals and checking the payment…').waitFor();check(`Slow request ${value} loading`,true);
    await page.getByRole('heading',{name:value==='ALLOW'?'Clear to continue':value==='REVIEW'?'Needs a reviewer':'Payment stopped'}).waitFor();delay=0;
    if(value==='BLOCK'){check('BLOCK prevents Checkout',await page.getByRole('button',{name:/Checkout|continue/i}).count()===0);continue;}
    if(value==='REVIEW'){await page.getByRole('button',{name:'Check approval and continue'}).click();await page.getByText('Review approval is pending').waitFor();approved=true;}
    await page.getByRole('button',{name:value==='REVIEW'?'Check approval and continue':'Continue to test Checkout'}).click();await page.getByText(/Do not mark paid until captured/).waitFor();check(`${value} authorized is not paid`,true);
    capture=true;await page.getByRole('button',{name:'Refresh capture status'}).click();await page.getByText(/Paid in test mode/).waitFor();check(`${value} captured is paid`,true);capture=false;
  }
  failing=true;await submit();await page.getByText('Fixture temporarily unavailable').waitFor();check('API error surfaced',true);failing=false;await submit();await page.getByText('Clear to continue').waitFor();check('Retry recovers',true);
  intentionallyOffline=true;await context.setOffline(true);await submit();await page.getByText(/Cannot reach FraudLens/).waitFor();check('Offline error surfaced',true);await context.setOffline(false);intentionallyOffline=false;
  await context.clearCookies();await submit();await page.getByRole('link',{name:'Sign in again'}).waitFor();check('Expired session offers sign-in',true);await page.goto(origin+'/access');await page.getByLabel('Password').fill('fixture-password');await page.getByRole('button',{name:'Continue',exact:true}).click();await page.waitForURL('**/demo');await page.getByRole('button',{name:'Sign out',exact:true}).click();await page.waitForURL(origin+'/');check('Sign out clears the session and returns home',true);
  await page.goto(origin);await page.emulateMedia({reducedMotion:'reduce'});await page.reload();await page.getByRole('button',{name:'BLOCK',exact:true}).click();check('Reduced motion preserves decisions',await page.getByRole('heading',{name:'Stop before Checkout.',exact:true}).isVisible());await page.getByRole('button',{name:'Explore',exact:true}).focus();await page.keyboard.press('Enter');await expect(page.getByRole('dialog')).toHaveCSS('opacity','1');await page.keyboard.press('Escape');await page.getByRole('dialog').waitFor({state:'detached'});check('Reduced motion preserves menu semantics',true);
  const touch=await browser.newContext({viewport:{width:390,height:844},hasTouch:true,isMobile:true});const touchPage=await touch.newPage();await touchPage.goto(origin);await touchPage.getByRole('button',{name:'Explore',exact:true}).tap();await expect(touchPage.getByRole('dialog')).toHaveCSS('opacity','1');await touchPage.getByRole('navigation',{name:'Explore destinations'}).getByRole('link',{name:/Data use/}).tap();await touchPage.waitForURL('**/privacy');await touchPage.getByRole('dialog').waitFor({state:'detached'});check('Touch navigation closes after selection',true);await touch.close();
  await page.goto(origin+'/not-a-page');await page.getByRole('link',{name:'Back home'}).click();await page.waitForURL(origin+'/');check('404 recovery',true);
  for(const [name,destination] of [['Product flow','/how-it-works'],['Merchant demo','/access'],['Reviewer dashboard','/access?role=admin'],['Data use','/privacy']]){await page.goto(origin);await page.getByRole('button',{name:'Explore',exact:true}).focus();await page.keyboard.press('Enter');await page.getByRole('navigation',{name:'Explore destinations'}).getByRole('link',{name:new RegExp(name)}).click();await page.waitForURL(origin+destination);check(`Navigation destination ${name}`,true);}
  await recordInteractions(browser, origin, results);
  check('No browser runtime warnings or errors',errors.length===0);
  check('Proxy forwards idempotency keys',calls.filter(c=>c.url==='/v1/checks'||c.url==='/v1/payments/order').every(c=>c.key));
  await writeFile('screenshots/browser-results.json',JSON.stringify({mode:'Synthetic fixture API. No real Supabase or Razorpay calls.',checks:results,errors,expectedNetworkErrors},null,2));
  console.log(`${results.length} browser checks passed. Synthetic fixture API only.`);
} catch(error){await page?.screenshot({path:"screenshots/browser-failure.png"}).catch(()=>{});console.error(error);console.error(errors);console.error(await page?.locator("body").innerText());console.error(appLog.slice(-2500));process.exitCode=1;}
finally {await browser?.close();app.kill('SIGTERM');fixture.closeAllConnections();fixture.close();}
