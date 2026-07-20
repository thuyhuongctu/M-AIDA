/* Access gate for the unpublished dissertation site (asia*.html).
   NOTE: this is client-side deterrence only. On a public static host the
   page source still ships to the browser; it is NOT real access control.
   To change the passcode, edit CODE below. */
(function(){
  var CODE = 'maida2026';                 // <-- change this passcode
  var KEY  = 'maida_thesis_gate';
  try { if (sessionStorage.getItem(KEY) === '1') return; } catch (e) {}
  var de = document.documentElement;
  de.style.visibility = 'hidden';
  function run(){
    var p = window.prompt('Trang luận án chưa công bố — nhập mã truy cập\nUnpublished dissertation site — enter access code:');
    if (p !== null && p.trim() === CODE) {
      try { sessionStorage.setItem(KEY, '1'); } catch (e) {}
      de.style.visibility = '';
    } else {
      window.location.replace('index.html');
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run);
  else run();
})();
