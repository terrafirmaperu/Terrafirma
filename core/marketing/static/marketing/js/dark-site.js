document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('[data-dark-toggle-password]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var wrap = btn.closest('.dark-password-wrap');
      if (!wrap) return;
      var input = wrap.querySelector('input[type="password"], input[type="text"]');
      if (!input) return;
      var eye = btn.querySelector('i');
      if (input.type === 'password') {
        input.type = 'text';
        if (eye) {
          eye.classList.remove('fa-eye');
          eye.classList.add('fa-eye-slash');
        }
      } else {
        input.type = 'password';
        if (eye) {
          eye.classList.remove('fa-eye-slash');
          eye.classList.add('fa-eye');
        }
      }
    });
  });
});
