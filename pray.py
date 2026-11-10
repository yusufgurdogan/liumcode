"""The 'pray for cheaper GPUs' button. Counter lives at api.liumcode.com (api/ in this repo)."""

API = "https://api.liumcode.com/pray"
GOAL = 10_000_000

CSS = """
.pray{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:24px 20px;margin:24px 0;text-align:center}
.pray[hidden]{display:none}
.pray h2{margin:0 0 6px}
.pray .legend{color:var(--muted);margin:0 auto 18px;max-width:560px}
.pray-count{font:800 clamp(34px,8vw,56px)/1.1 system-ui,sans-serif;font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.pray-of{color:var(--muted);font-size:14px;margin:4px 0 12px}
.pray-bar{height:10px;background:var(--panel2);border:1px solid var(--line);border-radius:99px;overflow:hidden;max-width:520px;margin:0 auto}
.pray-bar i{display:block;height:100%;width:0;min-width:4px;background:var(--accent);border-radius:99px;transition:width .4s}
.pray-btn{position:relative;margin:22px auto 8px;display:inline-flex;align-items:center;gap:10px;border:0;border-radius:99px;
padding:16px 30px;font:700 19px system-ui,sans-serif;background:var(--accent);color:#fff;cursor:pointer;
box-shadow:0 6px 24px rgba(124,92,255,.35);transition:transform .08s}
.pray-btn:hover{filter:brightness(1.08)}
.pray-btn:active{transform:scale(.96)}
.pray-btn:focus-visible{outline:3px solid var(--accent2);outline-offset:3px}
.pray-btn .e{font-size:24px}
.pray-mine{font-size:14px;color:var(--muted);min-height:20px}
.pray-share{display:inline-block;margin-top:10px;font-size:14px}
.pray-float{position:absolute;left:50%;top:0;pointer-events:none;font-size:22px;animation:prayup .9s ease-out forwards}
@keyframes prayup{from{opacity:1;transform:translate(-50%,0)}to{opacity:0;transform:translate(calc(-50% + var(--dx)),-70px)}}
@media (prefers-reduced-motion:reduce){.pray-float{display:none}.pray-bar i{transition:none}}
"""


def section(heading_tag="h2", page_link=True):
    more = '<a class="pray-share" href="/pray">Why pray? →</a> · ' if page_link else ""
    return f"""<section class="pray" id="pray" hidden aria-labelledby="pray-h">
<{heading_tag} id="pray-h">GPU prices are too high. Pray with us 🙏</{heading_tag}>
<p class="legend">Legend says that when this counter reaches <b>{GOAL:,}</b> prayers, GPU prices will finally come down.</p>
<div class="pray-count" aria-live="polite">0</div>
<div class="pray-of">prayers sent, <span class="pray-pct">0%</span> of the way there</div>
<div class="pray-bar" role="progressbar" aria-label="Progress to {GOAL:,} prayers" aria-valuemin="0" aria-valuemax="{GOAL}"><i></i></div>
<button class="pray-btn" type="button"><span class="e" aria-hidden="true">🙏</span> Send a prayer</button>
<div class="pray-mine" aria-live="polite"></div>
<div>{more}<a class="pray-share pray-x" href="#" target="_blank" rel="noopener">Share on X</a></div>
</section>"""


JS = """
<script>
(function(){var box=document.getElementById('pray');if(!box||!window.fetch)return;
var API=%(api)s,GOAL=%(goal)d,server=0,pending=0,inflight=false,timer=null,mine=0,warned=false;
var $=function(s){return box.querySelector(s)},cnt=$('.pray-count'),pct=$('.pray-pct'),bar=$('.pray-bar'),btn=$('.pray-btn'),me=$('.pray-mine'),x=$('.pray-x');
try{mine=+localStorage.getItem('prayers')||0}catch(e){}
function fmt(n){return n.toLocaleString('en-US')}
function render(){var n=server+pending,p=n/GOAL*100;cnt.textContent=fmt(n);
pct.textContent=(p<0.01?p.toFixed(4):p<1?p.toFixed(3):p.toFixed(1))+'%%';bar.firstElementChild.style.width=Math.min(p,100)+'%%';
bar.setAttribute('aria-valuenow',n);
if(mine)me.textContent='You have sent '+fmt(mine)+' prayer'+(mine===1?'':'s')+'. The GPUs thank you.';
x.href='https://x.com/intent/post?text='+encodeURIComponent('GPU prices are too high, so I prayed 🙏 '+fmt(n)+' prayers so far. Legend says at '+fmt(GOAL)+' they come down.')+'&url='+encodeURIComponent('https://liumcode.com/pray')}
function get(){if(pending||inflight)return;fetch(API,{cache:'no-store'}).then(function(r){return r.json()}).then(function(d){
if(typeof d.count==='number'){server=d.count;box.hidden=false;render()}}).catch(function(){})}
function flush(){timer=null;if(inflight||!pending)return;var n=Math.min(pending,50);inflight=true;
fetch(API,{method:'POST',headers:{'Content-Type':'text/plain'},body:JSON.stringify({n:n})}).then(function(r){return r.json()})
.then(function(d){pending-=n;if(typeof d.count==='number')server=d.count;
if(d.accepted<n&&!warned){warned=true;me.textContent='Easy there. The heavens need a moment to catch up.'}})
.catch(function(){pending-=n}).then(function(){inflight=false;render();if(pending)timer=setTimeout(flush,1000)})}
btn.addEventListener('click',function(){pending++;mine++;try{localStorage.setItem('prayers',mine)}catch(e){}
render();var f=document.createElement('span');f.className='pray-float';f.textContent='🙏';f.setAttribute('aria-hidden','true');
f.style.setProperty('--dx',(Math.random()*80-40)+'px');btn.appendChild(f);setTimeout(function(){f.remove()},900);
if(!timer&&!inflight)timer=setTimeout(flush,700)});
get();setInterval(function(){if(document.visibilityState==='visible')get()},15000);
})();
</script>
""" % {"api": '"' + API + '"', "goal": GOAL}
