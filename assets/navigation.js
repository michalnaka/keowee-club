// Progressive enhancement: all destinations remain visible without JavaScript.
(function(){
  var nav=document.querySelector('.nav'),button=nav&&nav.querySelector('.nav-toggle');
  if(!button)return;
  var mobile=window.matchMedia('(max-width:1023px)');
  function close(restoreFocus){
    nav.classList.remove('nav-open');
    button.setAttribute('aria-expanded','false');
    if(restoreFocus)button.focus();
  }
  nav.classList.add('nav-ready');
  button.addEventListener('click',function(){
    var open=button.getAttribute('aria-expanded')!=='true';
    nav.classList.toggle('nav-open',open);
    button.setAttribute('aria-expanded',String(open));
  });
  document.addEventListener('keydown',function(event){
    if(event.key==='Escape'&&nav.classList.contains('nav-open')){
      event.preventDefault();close(true);
    }
  });
  document.addEventListener('click',function(event){
    if(!nav.contains(event.target))close(false);
    else if(event.target.closest('.nav-menu a'))close(mobile.matches);
  });
  nav.addEventListener('focusout',function(event){
    if(event.relatedTarget&&!nav.contains(event.relatedTarget))close(false);
  });
  mobile.addEventListener('change',function(){
    var focused=document.activeElement;
    close(mobile.matches&&!!focused.closest('.nav-menu'));
    if(!mobile.matches&&focused===button)nav.querySelector('.wordmark').focus();
  });
})();
