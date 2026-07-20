(function(){
  var root=document.documentElement;
  // language
  function setLang(l){
    root.lang=l;
    document.querySelectorAll('.langtog button').forEach(function(b){b.classList.toggle('active',b.dataset.lang===l);});
    try{localStorage.setItem('asia_lang',l);}catch(e){}
  }
  document.querySelectorAll('.langtog button').forEach(function(b){
    b.addEventListener('click',function(){setLang(b.dataset.lang);});
  });
  var url=new URLSearchParams(location.search).get('lang');
  var saved=null; try{saved=localStorage.getItem('asia_lang');}catch(e){}
  setLang(url||saved||'vi');
  // theme
  var tb=document.getElementById('themeBtn');
  function setTheme(t){root.setAttribute('data-theme',t);try{localStorage.setItem('asia_theme',t);}catch(e){}}
  var st=null; try{st=localStorage.getItem('asia_theme');}catch(e){}
  if(st) setTheme(st);
  tb.addEventListener('click',function(){
    var cur=root.getAttribute('data-theme');
    if(!cur){cur=matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light';}
    setTheme(cur==='dark'?'light':'dark');
  });
  // scroll reveal
  if('IntersectionObserver' in window){
    var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target);}});},{threshold:.12});
    document.querySelectorAll('[data-rev]').forEach(function(el){io.observe(el);});
  } else {
    document.querySelectorAll('[data-rev]').forEach(function(el){el.classList.add('in');});
  }
})();
