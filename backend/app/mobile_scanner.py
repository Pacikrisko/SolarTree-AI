"""Standalone, phone-only QR scanner page. Camera permission requires HTTPS."""
from fastapi.responses import HTMLResponse

PHONE_HTML = r'''<!doctype html>
<html lang="bg"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="referrer" content="no-referrer"><title>SolarTree • Скенер</title>
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
</style></head><body><main><div class="brand">✳ <b>SolarTree</b> AI</div><div><h1>Сканирай кода на дървото</h1><p class="sub">Телефонът ще разпознае QR етикета. Устройството автоматично ще се появи в приложението на компютъра.</p></div>
<div class="camera"><video id="camera" autoplay playsinline muted></video><div id="fallback">⌗</div></div>
<div id="state" role="status">Готов за сканиране. Разреши достъпа до камерата.</div>
<button id="start">Отвори камерата</button>
<label class="file">Избери снимка с QR код<input type="file" id="photo" accept="image/*"></label><canvas id="canvas"></canvas>
<p class="tip">Временна сесия, свързана само с текущия профил. Не изпращай този линк на други хора.</p></main>
<script src="https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.js" defer></script>
<script>
const session=location.pathname.split('/').pop();
const video=document.getElementById('camera'), state=document.getElementById('state'), start=document.getElementById('start'), fallback=document.getElementById('fallback'), canvas=document.getElementById('canvas');
const ctx=canvas.getContext('2d',{willReadFrequently:true});let stream=null,active=false,working=false,detector=null;
function status(s){state.textContent=s}
function stop(){active=false;if(stream){stream.getTracks().forEach(x=>x.stop());stream=null}video.srcObject=null}
function decode(){if(!video.videoWidth||!video.videoHeight)return null;canvas.width=video.videoWidth;canvas.height=video.videoHeight;ctx.drawImage(video,0,0);return decodeCanvas()}
function decodeCanvas(){if(typeof jsQR==='function'){let data=ctx.getImageData(0,0,canvas.width,canvas.height);const c=jsQR(data.data,data.width,data.height,{inversionAttempts:'attemptBoth'});return c&&c.data}return null}
async function submit(raw){if(working||!raw)return;working=true;status('Проверявам устройството…');try{
const res=await fetch('/api/scan/'+encodeURIComponent(session),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({payload:raw})});
const json=await res.json();if(!res.ok)throw new Error(json.detail||'Грешка при добавянето');
stop();status('✓ '+json.name+' е добавено в профила на компютъра. Можеш да затвориш тази страница.');start.style.display='none';document.querySelector('.file').style.display='none';
}catch(e){status(e.message||'Неуспешно сканиране.');working=false;setTimeout(()=>{if(active)status('Опитай отново да насочиш камерата към етикета.')},2500)}}
async function scan(){if(!active||working)return;
try{if(!window.jsQR && 'BarcodeDetector' in window){detector ??= new BarcodeDetector({formats:['qr_code']});const items=await detector.detect(video);if(items.length){await submit(items[0].rawValue);return}}
else {const found=decode();if(found){await submit(found);return}}}catch(e){}
setTimeout(scan,180)}
start.onclick=async()=>{try{
if(!navigator.mediaDevices?.getUserMedia){status('За камерата се изисква HTTPS адрес. Отвори публичния защитен линк.');return}
stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'}},audio:false});video.srcObject=stream;await video.play();fallback.style.display='none';active=true;start.textContent='Камерата е включена';status('Насочи камерата към QR етикета на дървото.');scan()
}catch(e){status('Не мога да включа камерата. Провери разрешенията на браузъра.') }};
document.getElementById('photo').onchange=async(e)=>{const f=e.target.files[0];if(!f)return;try{const bmp=await createImageBitmap(f);canvas.width=bmp.width;canvas.height=bmp.height;ctx.drawImage(bmp,0,0);const raw=decodeCanvas();bmp.close();if(!raw){status('Не открих QR код. Опитай с по-ясна снимка или камерата.');return}await submit(raw)}catch(e){status('Не мога да разчета този файл.') }};
</script></body></html>'''

def scanner_page():
    return HTMLResponse(PHONE_HTML,headers={'Cache-Control':'no-store','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff'})
