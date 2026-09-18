const VERSION="mcu-v6";
const SHELL=["./","index.html","chart.html","posters.js","people.js","manifest.webmanifest","icons/icon-192.png","icons/icon-512.png"];
self.addEventListener("install",e=>{e.waitUntil(caches.open(VERSION).then(c=>c.addAll(SHELL)));self.skipWaiting();});
self.addEventListener("activate",e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==VERSION&&k!=="mcu-img").map(k=>caches.delete(k)))));self.clients.claim();});
self.addEventListener("fetch",e=>{
  const u=new URL(e.request.url);
  if(e.request.method!=="GET")return;
  // ポスター画像: 一度見たら端末に保存して、オフラインでも表示
  if(u.hostname==="image.tmdb.org"){
    e.respondWith(caches.open("mcu-img").then(c=>c.match(e.request).then(hit=>hit||fetch(e.request).then(res=>{c.put(e.request,res.clone());return res;}))));
    return;
  }
  // アプリ本体: ネット優先、つながらなければ保存版
  if(u.origin===location.origin){
    e.respondWith(fetch(e.request).then(res=>{const copy=res.clone();caches.open(VERSION).then(c=>c.put(e.request,copy));return res;}).catch(()=>caches.match(e.request).then(r=>r||caches.match("index.html"))));
  }
});
