/*!
 * M-AIDA mini music player — shared floating theme-song player.
 * Self-contained (no external deps). Loops the playlist and auto-advances to
 * the next track. Lyrics are the author's (Do Thuy Huong).
 * Include on a page with: <script src="assets/mini-music.js" defer></script>
 */
(function () {
  if (window.__maidaMiniMusic) return;      // guard against double-injection
  window.__maidaMiniMusic = true;

  var TRACKS = [
    { t: 'The Heartbeat of M-AIDA', s: 'Que les preuves décident', f: 'assets/maida_song_official.mp3' },
    { t: "Je m'appelle Hương", s: 'mon histoire', f: 'assets/maida_song_mon_histoire.mp3' }
  ];

  var css = '' +
    '.mm-player{position:fixed;right:16px;bottom:16px;z-index:2147483000;display:flex;align-items:center;gap:.5rem;' +
      'max-width:min(78vw,320px);padding:.4rem .55rem;border-radius:999px;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;' +
      'background:rgba(36,20,25,.92);color:#eef2f7;border:1px solid rgba(125,155,185,.35);box-shadow:0 10px 30px -10px rgba(0,0,0,.6);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px)}' +
    '.mm-player button{border:0;background:transparent;color:inherit;cursor:pointer;display:grid;place-items:center;padding:0}' +
    '.mm-player .mm-thumb{width:30px;height:30px;border-radius:8px;object-fit:cover;object-position:top center;flex:none;border:1px solid rgba(125,155,185,.35);background:#241419}' +
    '.mm-player .mm-pp{width:34px;height:34px;border-radius:50%;background:#8a4a58;color:#fff;flex:none}' +
    '.mm-player .mm-pp:hover{background:#a86675}' +
    '.mm-player .mm-txt{min-width:0;line-height:1.15;overflow:hidden}' +
    '.mm-player .mm-txt b{font-size:.78rem;font-weight:600;display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
    '.mm-player .mm-txt small{font-size:.62rem;color:#9fb0c4;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block}' +
    '.mm-player .mm-next{color:#9fb0c4;flex:none;width:26px;height:30px}' +
    '.mm-player .mm-next:hover{color:#eef2f7}' +
    '.mm-player .mm-wave{display:flex;align-items:flex-end;gap:2px;height:16px;flex:none}' +
    '.mm-player .mm-wave i{width:3px;height:4px;background:#C9A24B;border-radius:1px}' +
    '.mm-player.playing .mm-wave i{animation:mmwv .8s ease-in-out infinite alternate}' +
    '.mm-player.playing .mm-wave i:nth-child(2){animation-delay:.15s}.mm-player.playing .mm-wave i:nth-child(3){animation-delay:.3s}.mm-player.playing .mm-wave i:nth-child(4){animation-delay:.22s}' +
    '@keyframes mmwv{from{height:4px}to{height:15px}}' +
    '@media (prefers-reduced-motion:reduce){.mm-player.playing .mm-wave i{animation:none}}' +
    '@media(max-width:520px){.mm-player .mm-txt small{display:none}}';

  function build() {
    var style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);

    var el = document.createElement('div');
    el.className = 'mm-player';
    el.setAttribute('role', 'group');
    el.setAttribute('aria-label', 'M-AIDA theme music. Lyrics by Do Thuy Huong.');
    el.innerHTML =
      '<img class="mm-thumb" src="assets/img/huong/song_aodai.png" alt="">' +
      '<button class="mm-pp" aria-label="Play / pause"><svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg></button>' +
      '<span class="mm-wave" aria-hidden="true"><i></i><i></i><i></i><i></i></span>' +
      '<span class="mm-txt"><b></b><small></small></span>' +
      '<button class="mm-next" aria-label="Next track"><svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M16 6h2v12h-2zM6 18l8.5-6L6 6z"/></svg></button>';
    document.body.appendChild(el);

    var audio = document.createElement('audio');
    audio.preload = 'none';
    document.body.appendChild(audio);

    var ppBtn = el.querySelector('.mm-pp');
    var ppIcon = ppBtn.querySelector('svg');
    var nextBtn = el.querySelector('.mm-next');
    var tB = el.querySelector('.mm-txt b');
    var tS = el.querySelector('.mm-txt small');
    var ICON_PLAY = '<path d="M8 5v14l11-7z"/>';
    var ICON_PAUSE = '<path d="M6 5h4v14H6zm8 0h4v14h-4z"/>';
    var cur = 0;

    function paint() { tB.textContent = TRACKS[cur].t; tS.textContent = TRACKS[cur].s; }
    function load(i, play) {
      cur = (i + TRACKS.length) % TRACKS.length;
      audio.src = TRACKS[cur].f;
      paint();
      if (play) audio.play().catch(function () {});
    }
    function toggle() {
      if (!audio.src) { load(0, true); return; }
      if (audio.paused) audio.play().catch(function () {}); else audio.pause();
    }

    ppBtn.addEventListener('click', toggle);
    nextBtn.addEventListener('click', function () { load(cur + 1, true); });
    audio.addEventListener('play', function () { el.classList.add('playing'); ppIcon.innerHTML = ICON_PAUSE; });
    audio.addEventListener('pause', function () { el.classList.remove('playing'); ppIcon.innerHTML = ICON_PLAY; });
    audio.addEventListener('ended', function () { load(cur + 1, true); });   // auto-advance + loop the playlist

    paint();
  }

  if (document.body) build();
  else document.addEventListener('DOMContentLoaded', build);
})();
