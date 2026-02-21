(function () {
  function redirectToLogin() {
    const next = encodeURIComponent(window.location.pathname + window.location.search);
    window.location.replace('/login?next=' + next);
  }

  function enforceAuth() {
    fetch('/auth/status', { credentials: 'same-origin', cache: 'no-store' })
      .then(resp => (resp.ok ? resp.json() : { logged_in: false }))
      .then(data => {
        if (!data || !data.logged_in) redirectToLogin();
      })
      .catch(redirectToLogin);
  }

  function bindLogout(btn) {
    if (!btn || btn.dataset.authBound === '1') return;
    btn.dataset.authBound = '1';
    btn.addEventListener('click', async function () {
      if (btn.disabled) return;
      btn.disabled = true;
      btn.style.opacity = '0.7';
      try {
        await fetch('/auth/logout', { method: 'POST', credentials: 'same-origin' });
      } finally {
        window.location.href = '/login';
      }
    });
  }

  // Toolbar injection removed to prevent duplicate logout buttons
  // function ensureToolbar() { ... }
  // function initToolbar() { ... }

  enforceAuth();
  // initToolbar();
})();
