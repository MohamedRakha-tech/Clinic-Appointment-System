/**
 * Sanctuary Health – Auth UI
 * - Role switch toggle (login page)
 * - Form validation with inline error states
 */

/* ──────────────────────────────────────────────
   ROLE SWITCH
   Reads [data-role-switch] container and wires
   [data-role-option] buttons to hidden #login-role
─────────────────────────────────────────────── */
(function initRoleSwitch() {
  const container = document.querySelector('[data-role-switch]');
  if (!container) return;

  const hiddenInput = document.getElementById('login-role');
  const buttons     = container.querySelectorAll('[data-role-option]');

  const ACTIVE_CLASSES   = ['bg-gradient-to-b', 'from-primary', 'to-primary-container', 'text-on-primary', 'shadow-sm', 'font-semibold'];
  const INACTIVE_CLASSES = ['text-on-surface-variant', 'hover:text-on-surface', 'font-medium'];

  function setActive(selectedRole) {
    buttons.forEach(btn => {
      const role = btn.dataset.roleOption;
      if (role === selectedRole) {
        btn.classList.remove(...INACTIVE_CLASSES);
        btn.classList.add(...ACTIVE_CLASSES);
      } else {
        btn.classList.remove(...ACTIVE_CLASSES);
        btn.classList.add(...INACTIVE_CLASSES);
      }
    });
    if (hiddenInput) hiddenInput.value = selectedRole;
  }

  // Initialise to whichever button is already "active" via server-rendered classes,
  // or default to the hidden input's current value.
  const initialRole = hiddenInput ? hiddenInput.value || 'patient' : 'patient';
  setActive(initialRole);

  buttons.forEach(btn => {
    btn.addEventListener('click', () => setActive(btn.dataset.roleOption));
  });
})();


/* ──────────────────────────────────────────────
   FORM VALIDATION
   Targets form[data-validate-form].
   Each required field carries:
     data-error-required="<message>"
   Each error display carrier:
     <p data-error-for="<fieldName>" class="... hidden"></p>
─────────────────────────────────────────────── */
(function initFormValidation() {
  const forms = document.querySelectorAll('form[data-validate-form]');

  // Border-class helpers
  const VALID_BORDER   = ['border-outline-variant', 'focus:border-primary'];
  const INVALID_BORDER = ['border-error', 'focus:border-error'];

  function showError(field, message) {
    field.classList.remove(...VALID_BORDER);
    field.classList.add(...INVALID_BORDER);

    const errorEl = field.closest('div, section')?.querySelector('[data-error-for="' + field.name + '"]');
    if (errorEl) {
      errorEl.textContent = message;
      errorEl.classList.remove('hidden');
    }
  }

  function clearError(field) {
    field.classList.remove(...INVALID_BORDER);
    field.classList.add(...VALID_BORDER);

    // We must search a bit wider — error element may be a sibling of the wrapper
    const form    = field.closest('form');
    const errorEl = form?.querySelector('[data-error-for="' + field.name + '"]');
    if (errorEl) {
      errorEl.textContent = '';
      errorEl.classList.add('hidden');
    }
  }

  function validateField(field) {
    const requiredMsg = field.dataset.errorRequired || 'This field is required';

    if (field.type === 'checkbox') {
      if (!field.checked) {
        showError(field, requiredMsg);
        return false;
      }
      clearError(field);
      return true;
    }

    if (!field.value.trim()) {
      showError(field, requiredMsg);
      return false;
    }

    // Email format check
    if (field.type === 'email') {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(field.value.trim())) {
        showError(field, 'Please enter a valid email address');
        return false;
      }
    }

    // Password-confirm check
    if (field.name === 'password2') {
      const pw1 = field.closest('form')?.querySelector('[name="password1"]');
      if (pw1 && field.value !== pw1.value) {
        showError(field, 'Passwords do not match');
        return false;
      }
    }

    clearError(field);
    return true;
  }

  forms.forEach(form => {
    // Live clearing on input so errors disappear as user types
    form.addEventListener('input', e => {
      if (e.target.required) validateField(e.target);
    });
    form.addEventListener('change', e => {
      if (e.target.required) validateField(e.target);
    });

    form.addEventListener('submit', e => {
      const requiredFields = form.querySelectorAll('[required]');
      let valid = true;

      requiredFields.forEach(field => {
        if (!validateField(field)) valid = false;
      });

      if (!valid) {
        e.preventDefault();
        // Scroll to first error
        const firstError = form.querySelector('.border-error');
        if (firstError) firstError.focus();
      }
    });
  });
})();
