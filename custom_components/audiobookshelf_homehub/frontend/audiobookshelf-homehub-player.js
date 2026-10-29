/* Audiobookshelf Home Hub player card - development preview */
class AudiobookshelfHomeHubPlayer extends HTMLElement {
  setConfig(config) {
    if (!config.entry_id || !/^[A-Za-z0-9_-]+$/.test(config.entry_id)) throw Error('entry_id required');
    this.config = config;
    this.base = `/api/audiobookshelf_homehub/${config.entry_id}`;
    if (!this.shadowRoot) this.attachShadow({mode:'open'});
    this.shadowRoot.innerHTML = `<style>
      :host{display:block;color:var(--primary-text-color)}.panel{padding:20px;background:var(--ha-card-background,var(--card-background-color));border-radius:22px;text-align:center;box-sizing:border-box}img{width:min(72%,240px);aspect-ratio:1;object-fit:cover;border-radius:12px}h3{margin:12px 0 3px}p{margin:0 0 16px;color:var(--secondary-text-color)}input[type=range]{width:100%;accent-color:var(--primary-color)}.times{display:flex;justify-content:space-between;font-size:12px;color:var(--secondary-text-color)}.buttons{display:flex;align-items:center;justify-content:center;gap:16px;margin:18px 0}button,select{border:0;border-radius:12px;background:var(--primary-color);color:var(--text-primary-color,#fff);padding:12px;cursor:pointer;font-size:16px}.play{font-size:25px;min-width:70px}button:disabled{opacity:.4}#status{font-size:12px;color:var(--secondary-text-color);min-height:18px}
    </style><ha-card><div class="panel"><img id="cover" alt="Book cover"><h3 id="title">Loading…</h3><p id="author"></p><input id="seek" type="range" min="0" max="1" step="0.1" value="0" aria-label="Seek"><div class="times"><span id="elapsed">0:00</span><span id="total">0:00</span></div><div class="buttons"><button id="back" aria-label="Back 15 seconds">↶ 15</button><button class="play" id="play" aria-label="Play or pause">▶</button><button id="forward" aria-label="Forward 30 seconds">30 ↷</button></div><select id="speed" aria-label="Playback speed"><option value="0.75">0.75×</option><option value="1">1×</option><option selected value="1.2">1.2×</option><option value="1.5">1.5×</option><option value="1.75">1.75×</option><option value="2">2×</option></select><div id="status">Ready</div><audio id="audio" preload="metadata"></audio></div></ha-card>`;
    this.$ = id=>this.shadowRoot.getElementById(id);
    this.audio=this.$('audio'); this.session=null; this.book=null; this.tracks=[]; this.index=0; this.listened=0; this.lastTick=0; this.lastSync=0; this.loading=false;
    this.$('play').onclick=()=>this.toggle().catch(e=>this.status(e.message));
    this.$('back').onclick=()=>this.seek(this.position()-15).catch(e=>this.status(e.message));
    this.$('forward').onclick=()=>this.seek(this.position()+30).catch(e=>this.status(e.message));
    this.$('seek').onchange=e=>this.seek(Number(e.target.value)).catch(e=>this.status(e.message));
    this.$('speed').onchange=()=>this.audio.playbackRate=Number(this.$('speed').value);
    this.audio.onplay=()=>this.$('play').textContent='Ⅱ';
    this.audio.onpause=()=>this.$('play').textContent='▶';
    this.audio.onended=()=>{if(this.index+1<this.tracks.length){this.loadTrack(this.index+1,this.tracks[this.index+1].startOffset).then(()=>this.audio.play()).catch(e=>this.status(e.message));}else{this.sync(true).catch(()=>{});this.status('Finished');}};
    this.loadCurrent().catch(e=>this.status(e.message));
  }
  set hass(value){this._hass=value;}
  status(value){this.$('status').textContent=value;}
  async api(action,method='GET',body){
    if(!this._hass)throw Error('Home Assistant not connected');
    const response=await this._hass.auth.fetchWithAuth(`${this.base}/${action}`,{method,headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});
    if(!response.ok)throw Error(`Home Assistant request failed (${response.status})`);
    return response.json();
  }
  async loadCurrent(){
    this.book=await this.api('current');
    if(!this.book.available){this.$('title').textContent='No audiobook in progress';this.status('Add or start a book in Audiobookshelf');return;}
    this.$('title').textContent=this.book.title||'Audiobook';this.$('author').textContent=this.book.author||'';
    if(this.book.cover_url)this.$('cover').src=this.book.cover_url;
    this.draw();this.status('Ready to play at 1.2×');
  }
  position(){return this.session?(Number(this.tracks[this.index]?.startOffset)||0)+this.audio.currentTime:Number(this.book?.position)||0;}
  draw(){if(!this.book)return;const fmt=s=>{s=Math.max(0,Math.floor(s||0));return `${Math.floor(s/3600)?Math.floor(s/3600)+':':''}${Math.floor(s%3600/60)}:${String(s%60).padStart(2,'0')}`};const pos=this.position();this.$('seek').max=this.book.duration||1;this.$('seek').value=Math.min(pos,this.book.duration||1);this.$('elapsed').textContent=fmt(pos);this.$('total').textContent=fmt(this.book.duration);}
  async loadTrack(i,at){
    this.index=i;const track=this.tracks[i];
    // Re-sign each track URL immediately before use, so long books can change tracks.
    const signed=await this.api('refresh','POST',{handle:track.handle});
    this.audio.src=signed.url;this.audio.load();
    await new Promise((resolve,reject)=>{if(this.audio.readyState>=1)return resolve();this.audio.addEventListener('loadedmetadata',resolve,{once:true});this.audio.addEventListener('error',()=>reject(Error('Audio unavailable')),{once:true})});
    this.audio.currentTime=Math.max(0,at-(Number(track.startOffset)||0));this.audio.playbackRate=Number(this.$('speed').value);this.draw();
  }
  async toggle(){
    if(!this.book?.available)return;
    if(!this.audio.paused){this.audio.pause();await this.sync();this.status('Paused');return;}
    if(this.session){await this.audio.play();this.status('Playing');return;}
    if(this.loading)return;this.loading=true;
    try{this.status('Opening audiobook…');const data=await this.api('start','POST',{book_id:this.book.book_id});this.session=data.session;this.tracks=data.tracks.map(t=>({...t,handle:t.url.split('/').pop().split('?')[0]}));
      if(!this.tracks.length)throw Error('No audio tracks');let at=Number(this.book.position)||0;let i=this.tracks.findIndex(t=>at>=t.startOffset&&at<t.startOffset+t.duration);if(i<0)i=0;
      await this.loadTrack(i,at);await this.audio.play();this.status('Playing');
    }finally{this.loading=false;}
  }
  async seek(at){if(!this.book)return;at=Math.max(0,Math.min(this.book.duration||0,at));if(!this.session){this.book.position=at;this.draw();return;}const i=this.tracks.findIndex(t=>at>=t.startOffset&&at<t.startOffset+t.duration);const target=i<0?this.tracks.length-1:i;if(target!==this.index){const playing=!this.audio.paused;await this.loadTrack(target,at);if(playing)await this.audio.play();}else this.audio.currentTime=Math.max(0,at-this.tracks[this.index].startOffset);this.draw();await this.sync();}
  async sync(close=false){if(!this.session)return;const body={session:this.session,position:this.position(),timeListened:this.listened,duration:this.book.duration};this.listened=0;await this.api(close?'close':'sync','POST',body);if(close)this.session=null;}
  connectedCallback(){this.timer=setInterval(()=>{if(!this.audio||!this.book)return;const now=Date.now();if(!this.audio.paused&&this.session){if(this.lastTick)this.listened+=(now-this.lastTick)/1000;this.lastTick=now;this.draw();if(now-this.lastSync>20000){this.lastSync=now;this.sync().catch(e=>this.status(e.message));}}else this.lastTick=0;},1000);this.onHidden=()=>{if(document.hidden)this.sync().catch(()=>{});};document.addEventListener('visibilitychange',this.onHidden);}
  disconnectedCallback(){clearInterval(this.timer);document.removeEventListener('visibilitychange',this.onHidden);if(this.audio)this.audio.pause();this.sync(true).catch(e=>console.warn('Audiobookshelf session close failed',e));}
  getCardSize(){return 5;}
}
customElements.define('audiobookshelf-homehub-player',AudiobookshelfHomeHubPlayer);
window.customCards=window.customCards||[];window.customCards.push({type:'audiobookshelf-homehub-player',name:'Audiobookshelf Home Hub Player',description:'Browser audiobook player using the Home Assistant audio proxy'});
