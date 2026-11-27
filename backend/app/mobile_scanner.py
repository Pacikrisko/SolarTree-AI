"""Standalone, phone-only QR scanner page. Camera permission requires HTTPS."""
from fastapi.responses import HTMLResponse

PHONE_HTML = r'''<!doctype html>
<html lang="@@lang@@"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="referrer" content="no-referrer"><title>@@title@@</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#101917;color:#ecf5ed;font-family:system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:480px;padding:42px 22px 34px;margin:auto;min-height:100dvh;display:flex;flex-direction:column;gap:20px}
.brand{font-size:14px;font-weight:800;letter-spacing:.3px;color:#b5ed8e}.brand b{color:#fff}.sub{color:#93a79a;font-size:13px;line-height:1.6}h1{font-size:26px;line-height:1.2;letter-spacing:-1px;margin:3px 0 6px}h2{font-size:17px}
.camera{background:linear-gradient(140deg,#1f3832,#0e1515);border:1px solid #3d5c4b;border-radius:24px;min-height:330px;display:flex;align-items:center;justify-content:center;position:relative;overflow:hidden}
.camera:before{content:'';position:absolute;inset:12% 13%;border:2px solid #baf294;border-radius:20px;z-index:2;pointer-events:none;box-shadow:0 0 26px #3dff8951}
video{position:absolute;width:100%;height:100%;object-fit:cover;inset:0}#fallback{font-size:80px;color:#7caa96}
button,.file{border:0;border-radius:13px;padding:15px;display:block;width:100%;font:inherit;font-weight:750;text-align:center;cursor:pointer;background:#c1f797;color:#193020}
.file{background:#263b32;color:#d9efdc;border:1px solid #56735a}
input[type=file]{display:none}#state{min-height:44px;padding:12px 14px;background:#1a2924;border:1px solid #3c5549;border-radius:12px;color:#d9e8dc;font-size:13px;line-height:1.6}
.tip{color:#859b8d;font-size:12px;text-align:center;line-height:1.5}#canvas{display:none}
</style></head><body><main><div class="brand"><a href="/#/overview" style="color:inherit;text-decoration:none"><img src="/solix.svg" width="24" height="24" alt="" style="vertical-align:middle"> <b>Solix</b></a> <a style="float:right;color:inherit" href="?lang=@@next@@" lang="@@next@@">@@switch@@</a></div><div><h1>@@heading@@</h1><p class="sub">@@description@@</p></div>
<div class="camera"><video id="camera" autoplay playsinline muted></video><div id="fallback">⌗</div></div>
<div id="state" role="status">@@ready@@</div>
<button id="start">@@open@@</button>
<label class="file">@@photo@@<input type="file" id="photo" accept="image/*"></label><canvas id="canvas"></canvas>
<p class="tip">@@tip@@</p></main>
<script src="/api/scanner/jsqr-1.4.0.js"></script>
<script>
const session=location.pathname.split('/').pop();
const video=document.getElementById('camera'), state=document.getElementById('state'), start=document.getElementById('start'), fallback=document.getElementById('fallback'), canvas=document.getElementById('canvas');
const ctx=canvas.getContext('2d',{willReadFrequently:true});let stream=null,active=false,working=false;
function status(s){state.textContent=s}
function stop(){active=false;if(stream){stream.getTracks().forEach(x=>x.stop());stream=null}video.srcObject=null}
function decode(){if(!video.videoWidth||!video.videoHeight)return null;canvas.width=video.videoWidth;canvas.height=video.videoHeight;ctx.drawImage(video,0,0);return decodeCanvas()}
function decodeCanvas(){if(typeof jsQR==='function'){let data=ctx.getImageData(0,0,canvas.width,canvas.height);const c=jsQR(data.data,data.width,data.height,{inversionAttempts:'attemptBoth'});return c&&c.data}return null}
async function submit(raw){if(working||!raw)return;working=true;status('@@checking@@');try{
const res=await fetch('/api/scan/'+encodeURIComponent(session),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({payload:raw})});
const json=await res.json();if(!res.ok)throw new Error(json.detail||'@@error@@');
stop();status('✓ '+json.name+'@@finished@@');start.style.display='none';document.querySelector('.file').style.display='none';
}catch(e){status(e.message||'@@failed@@');working=false;setTimeout(()=>{if(active)status('@@retry@@')},2500)}}
async function scan(){if(!active||working)return;
try {
  const found=decode();
  if(found){await submit(found);if(!active)return}
}catch(e){status('@@unreadable@@')}
setTimeout(scan,180)}
start.onclick=async()=>{try{
if(!navigator.mediaDevices?.getUserMedia){status('@@https@@');return}
start.disabled=true;stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'}},audio:false});video.srcObject=stream;await video.play();fallback.style.display='none';active=true;start.textContent='@@on@@';status('@@aim@@');scan()
}catch(e){stop();start.disabled=false;status('@@denied@@') }};
document.getElementById('photo').onchange=async(e)=>{const f=e.target.files[0];if(!f)return;
const url=URL.createObjectURL(f);
try{
  const image=new Image();image.src=url;await image.decode();
  const scale=Math.min(1,1600/Math.max(image.naturalWidth,image.naturalHeight));
  canvas.width=Math.max(1,Math.round(image.naturalWidth*scale));
  canvas.height=Math.max(1,Math.round(image.naturalHeight*scale));
  ctx.drawImage(image,0,0,canvas.width,canvas.height);
  const raw=decodeCanvas();if(!raw){status('@@missing@@');return}await submit(raw)
}catch(e){status('@@unreadable@@')}
finally{URL.revokeObjectURL(url);e.target.value=''}
};
window.addEventListener('pagehide',stop);
</script></body></html>'''

STRINGS = {
  "title": [
    "Solix • Скенер",
    "SolarTree • Scanner"
  ],
  "heading": [
    "Сканирай кода на дървото",
    "Scan the tree code"
  ],
  "description": [
    "Телефонът ще разпознае QR етикета. Устройството автоматично ще се появи в приложението на компютъра.",
    "Scan the QR label with your phone. The device will appear in the application on your computer."
  ],
  "ready": [
    "Готов за сканиране. Разреши достъпа до камерата.",
    "Ready to scan. Allow camera access to continue."
  ],
  "open": [
    "Отвори камерата",
    "Open camera"
  ],
  "photo": [
    "Избери снимка с QR код",
    "Select a QR code photo"
  ],
  "tip": [
    "Временна сесия, свързана само с текущия профил. Не изпращай този линк на други хора.",
    "This temporary session is linked to your account. Keep this link private."
  ],
  "checking": [
    "Проверявам устройството…",
    "Checking the device…"
  ],
  "error": [
    "Грешка при добавянето",
    "Could not add the device"
  ],
  "finished": [
    " е добавено в профила на компютъра. Можеш да затвориш тази страница.",
    " was added to your account. You can close this page."
  ],
  "failed": [
    "Неуспешно сканиране.",
    "Scan failed."
  ],
  "retry": [
    "Опитай отново да насочиш камерата към етикета.",
    "Point the camera at the label again."
  ],
  "https": [
    "За камерата се изисква HTTPS адрес. Отвори публичния защитен линк.",
    "The camera requires HTTPS. Open the secure scanner link."
  ],
  "on": [
    "Камерата е включена",
    "Camera on"
  ],
  "aim": [
    "Насочи камерата към QR етикета на дървото.",
    "Point the camera at the QR label on the tree."
  ],
  "denied": [
    "Не мога да включа камерата. Провери разрешенията на браузъра.",
    "Could not start the camera. Check browser permissions."
  ],
  "missing": [
    "Не открих QR код. Опитай с по-ясна снимка или камерата.",
    "No QR code detected. Try a clearer photo or use the camera."
  ],
  "unreadable": [
    "Не мога да разчета този файл.",
    "Could not read this file."
  ]
}

def scanner_page(language='bg'):
    other='bg' if language=='en' else 'en'
    html=PHONE_HTML.replace('@@lang@@',language).replace('@@next@@',other).replace('@@switch@@','Български' if language=='en' else 'English')
    for key,labels in STRINGS.items():
        html=html.replace('@@'+key+'@@',labels[language=='en'])
    return HTMLResponse(html,headers={'Cache-Control':'no-store','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff'})
