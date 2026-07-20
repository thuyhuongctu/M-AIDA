/*!
 * M-AIDA mini guide — a shared floating Huong AI guide button + intro bubble.
 * Self-contained (no external deps). Text guide only for now; a synced voice
 * track will be added later. Bilingual VI/EN, follows the page's html[lang].
 * Include with: <script src="assets/mini-guide.js" defer></script>
 */
(function () {
  if (window.__maidaMiniGuide) return;
  window.__maidaMiniGuide = true;

  var LINES = {
    hi:   { vi: 'Xin chào! Mình là Hương, hướng dẫn viên AI của M-AIDA.', en: "Hi! I'm Huong, the M-AIDA AI guide." },
    body: { vi: 'M-AIDA là công cụ trích xuất bằng chứng có kiểm chứng con người cho phân tích tổng hợp về quốc tế hóa và hiệu quả doanh nghiệp. Ghé thăm các trang bên dưới nhé.',
            en: 'M-AIDA is a human-verified evidence-extraction tool for the meta-analysis of internationalization and firm performance. Explore the pages below.' },
    voice:{ vi: '🎧 Giọng dẫn: sắp có.', en: '🎧 Voice guide: coming soon.' },
    open: { vi: 'Hương AI dẫn đường', en: 'Huong AI guide' },
    close:{ vi: 'Đóng', en: 'Close' }
  };
  var NAV = [
    { href: 'index.html',       vi: 'M-AIDA',            en: 'M-AIDA' },
    { href: 'songs.html',       vi: 'Bài hát',           en: 'Songs' },
    { href: 'data_melody.html', vi: 'Dữ liệu & Giai điệu', en: 'Data & Melody' },
    { href: 'huong.html',       vi: 'Trang cá nhân',     en: 'Personal page' },
    { href: 'library.html',     vi: 'Thư viện',          en: 'Library' }
  ];

  function isEN() { return (document.documentElement.getAttribute('lang') || 'vi').toLowerCase().indexOf('en') === 0; }
  function L(k) { return LINES[k][isEN() ? 'en' : 'vi']; }

  var css = '' +
    '.mg-fab{position:fixed;left:16px;bottom:16px;z-index:2147483000;width:60px;height:60px;border-radius:50%;padding:0;border:2px solid rgba(212,175,55,.7);' +
      'background:#0a192f;cursor:pointer;overflow:hidden;box-shadow:0 12px 30px -10px rgba(0,0,0,.6)}' +
    '.mg-fab img{width:100%;height:130%;object-fit:cover;object-position:top center;display:block;pointer-events:none}' +
    '.mg-fab::after{content:"";position:absolute;right:2px;bottom:2px;width:12px;height:12px;border-radius:50%;background:#5fbd8e;border:2px solid #0a192f}' +
    '.mg-pop{position:fixed;left:16px;bottom:86px;z-index:2147483000;width:min(84vw,320px);padding:1rem 1.05rem 1.1rem;border-radius:16px;' +
      'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;background:rgba(10,25,47,.94);color:#eef2f7;' +
      'border:1px solid rgba(125,155,185,.35);box-shadow:0 18px 44px -16px rgba(0,0,0,.7);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);display:none}' +
    '.mg-pop.show{display:block}' +
    '.mg-pop h4{margin:0 0 .4rem;font-size:.95rem;color:#fff}' +
    '.mg-pop p{margin:0 0 .6rem;font-size:.8rem;line-height:1.5;color:#c7d2df}' +
    '.mg-pop .mg-voice{font-size:.72rem;color:#e3c06a;margin:0 0 .7rem}' +
    '.mg-pop .mg-nav{display:flex;flex-wrap:wrap;gap:.35rem}' +
    '.mg-pop .mg-nav a{font-size:.72rem;color:#8fcfef;text-decoration:none;border:1px solid rgba(125,155,185,.3);border-radius:999px;padding:.2rem .55rem}' +
    '.mg-pop .mg-nav a:hover{border-color:#3a8bad;color:#eef2f7}' +
    '.mg-pop .mg-x{position:absolute;top:.5rem;right:.6rem;border:0;background:transparent;color:#9fb0c4;font-size:1.1rem;cursor:pointer;line-height:1}';

  function build() {
    var style = document.createElement('style'); style.textContent = css; document.head.appendChild(style);

    var fab = document.createElement('button');
    fab.className = 'mg-fab'; fab.type = 'button';
    fab.setAttribute('aria-label', L('open'));
    fab.innerHTML = '<img src="assets/img/huong/welcome.png" alt="">';
    document.body.appendChild(fab);

    var pop = document.createElement('div');
    pop.className = 'mg-pop'; pop.setAttribute('role', 'dialog'); pop.setAttribute('aria-label', L('open'));
    document.body.appendChild(pop);

    function render() {
      fab.setAttribute('aria-label', L('open'));
      var nav = NAV.map(function (n) {
        return '<a href="' + n.href + '">' + (isEN() ? n.en : n.vi) + '</a>';
      }).join('');
      pop.innerHTML =
        '<button class="mg-x" aria-label="' + L('close') + '">&times;</button>' +
        '<h4>' + L('hi') + '</h4>' +
        '<p>' + L('body') + '</p>' +
        '<p class="mg-voice">' + L('voice') + '</p>' +
        '<div class="mg-nav">' + nav + '</div>';
      pop.querySelector('.mg-x').addEventListener('click', function () { pop.classList.remove('show'); });
    }
    fab.addEventListener('click', function () {
      if (pop.classList.contains('show')) { pop.classList.remove('show'); return; }
      render(); pop.classList.add('show');
    });
  }

  if (document.body) build();
  else document.addEventListener('DOMContentLoaded', build);
})();
