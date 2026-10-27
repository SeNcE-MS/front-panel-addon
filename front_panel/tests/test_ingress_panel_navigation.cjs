const assert=require('node:assert/strict'),{spawn}=require('node:child_process');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright-core');
(async()=>{
 const base='http://127.0.0.1:18876';
 const srv=spawn('python',['-c',"import server;server.create_server(('127.0.0.1',18876),trusted_peers={'127.0.0.1'},viewer_ip='127.0.0.2').serve_forever()"],{cwd:__dirname+'/..',stdio:'ignore'});
 let browser;
 try{
  browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
  for(const viewport of [{width:390,height:844},{width:1440,height:900}]){
   const context=await browser.newContext({viewport,extraHTTPHeaders:{'X-Ingress-Path':'/api/hassio_ingress/fixture'}});
   for(let i=0;i<100;i++){try{if((await context.request.get(base+'/health')).ok())break}catch{}await new Promise(r=>setTimeout(r,50))}
   // Model an HA app iframe with an Ingress prefix, forwarding only its relative path.
   const host=await context.newPage();
   await context.route('http://ha.fixture.invalid/**',async route=>{
    const url=new URL(route.request().url());
    if(url.pathname==='/shell')return route.fulfill({contentType:'text/html',body:'<iframe style="border:0;width:100%;height:95vh" src="/api/hassio_ingress/fixture/editor"></iframe>'});
    const path=url.pathname.replace('/api/hassio_ingress/fixture','')+url.search;
    const response=await context.request.get(base+path);
    await route.fulfill({response});
   });
   await host.goto('http://ha.fixture.invalid/shell');
   const frame=host.frames().find(f=>f.url().endsWith('/editor'));
   const link=frame.getByRole('link',{name:'표시 화면 열기'});
   await link.waitFor();assert.equal(await link.getAttribute('href'),'./?view=panel');
   await link.click();
   await new Promise(r=>setTimeout(r,250));
   assert.equal(context.pages().length,1,'must not create a new page');
   assert.equal(new URL(frame.url()).pathname,'/api/hassio_ingress/fixture/');
   assert.equal(new URL(frame.url()).search,'?view=panel');
   await frame.locator('#room-tabs').waitFor();
   assert.equal(host.url(),'http://ha.fixture.invalid/shell','HA shell remains open');
   const denied=await context.request.get(base+'/editor',{headers:{'X-Ingress-Path':''}});assert.equal(denied.status(),403);
   const wrong=await context.request.get(base+'/',{headers:{'X-Ingress-Path':''}});assert.equal(wrong.status(),403);
   console.log(JSON.stringify({viewport,sameIframe:true,pages:context.pages().length,panelLoaded:true,directEditor:denied.status(),wrongIp:wrong.status(),physicalControls:0}));
   await context.close();
  }
 }finally{if(browser)await browser.close();srv.kill()}
})().catch(e=>{console.error(e);process.exit(1)});
