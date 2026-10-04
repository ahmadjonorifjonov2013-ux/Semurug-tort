document.addEventListener('DOMContentLoaded', function () {

  document.documentElement.classList.add('js');

  /* ------------------------------------------------------------------ */
  /* Bootstrap tooltips                                                  */
  /* ------------------------------------------------------------------ */
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) {
    new bootstrap.Tooltip(el, { delay: { show: 400, hide: 0 } });
  });

  /* ------------------------------------------------------------------ */
  /* Theme toggle (light / dark)                                         */
  /* ------------------------------------------------------------------ */
  var root = document.documentElement;

  function setTheme(theme) {
    root.setAttribute('data-bs-theme', theme);
    try { localStorage.setItem('theme', theme); } catch (e) {}
  }

  function toggleTheme() {
    setTheme(root.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark');
  }

  ['themeToggle', 'themeToggleMobile'].forEach(function (id) {
    var btn = document.getElementById(id);
    if (btn) btn.addEventListener('click', toggleTheme);
  });

  if (!localStorage.getItem('theme')) {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function (e) {
      setTheme(e.matches ? 'dark' : 'light');
    });
  }

  /* ------------------------------------------------------------------ */
  /* Sticky navbar shadow + back-to-top                                  */
  /* ------------------------------------------------------------------ */
  var navbar = document.getElementById('mainNavbar');
  var backToTop = document.getElementById('backToTop');

  function onScroll() {
    if (navbar) navbar.classList.toggle('scrolled', window.scrollY > 8);
    if (backToTop) backToTop.classList.toggle('show', window.scrollY > 600);
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  if (backToTop) {
    backToTop.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  /* ------------------------------------------------------------------ */
  /* Reveal on scroll                                                    */
  /* ------------------------------------------------------------------ */
  var revealEls = document.querySelectorAll('[data-reveal]');
  if ('IntersectionObserver' in window && revealEls.length) {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          var el = entry.target;
          var delay = parseInt(el.dataset.revealDelay || '0', 10);
          setTimeout(function () { el.classList.add('is-visible'); }, delay);
          observer.unobserve(el);
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
    revealEls.forEach(function (el) { observer.observe(el); });
  } else {
    revealEls.forEach(function (el) { el.classList.add('is-visible'); });
  }

  /* ------------------------------------------------------------------ */
  /* Auto-dismiss alerts                                                 */
  /* ------------------------------------------------------------------ */
  document.querySelectorAll('.alert-dismissible').forEach(function (alert) {
    setTimeout(function () {
      bootstrap.Alert.getOrCreateInstance(alert).close();
    }, 7000);
  });

  /* ------------------------------------------------------------------ */
  /* Small UX helpers                                                    */
  /* ------------------------------------------------------------------ */
  document.querySelectorAll('input[type="number"]').forEach(function (input) {
    input.addEventListener('input', function () {
      input.value = input.value.replace(/[^\d]/g, '');
    });
  });

  document.querySelectorAll('input[name="delivery_date"]').forEach(function (input) {
    if (!input.min) input.min = new Date().toISOString().split('T')[0];
  });

  document.querySelectorAll('form[method="post"]:not(.quick-add):not([data-no-loading])').forEach(function (form) {
    form.addEventListener('submit', function () {
      var btn = form.querySelector('button[type="submit"]');
      if (btn && !btn.disabled) {
        btn.disabled = true;
        btn.dataset.original = btn.innerHTML;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Yuborilmoqda...';
        setTimeout(function () {
          btn.disabled = false;
          if (btn.dataset.original) btn.innerHTML = btn.dataset.original;
        }, 12000);
      }
    });
  });

  /* ------------------------------------------------------------------ */
  /* Toast helper (global)                                               */
  /* ------------------------------------------------------------------ */
  window.showToast = function (text, icon) {
    var wrap = document.getElementById('toastWrap');
    if (!wrap) return;
    var note = document.createElement('div');
    note.className = 'toast-note';
    note.innerHTML = '<i class="bi ' + (icon || 'bi-check-circle-fill') +
      ' text-danger fs-5"></i><span class="small">' + text + '</span>';
    wrap.appendChild(note);
    setTimeout(function () {
      note.style.transition = 'opacity .3s, transform .3s';
      note.style.opacity = '0';
      note.style.transform = 'translateY(12px)';
      setTimeout(function () { note.remove(); }, 320);
    }, 3600);
  };
});
