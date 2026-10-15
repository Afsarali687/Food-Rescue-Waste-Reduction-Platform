/**
 * Food Rescue & Waste Reduction Platform - Client Scripts
 */

document.addEventListener("DOMContentLoaded", () => {
  // Highlight active navbar link
  const currentPath = window.location.pathname;
  document.querySelectorAll(".navbar-nav .nav-link").forEach((link) => {
    const href = link.getAttribute("href");
    if (href === currentPath || (href !== "/" && currentPath.startsWith(href))) {
      link.classList.add("active");
      link.setAttribute("aria-current", "page");
    }
  });

  // Status Change Confirmation
  document.querySelectorAll('form[action*="/status"]').forEach((form) => {
    form.addEventListener("submit", (event) => {
      const selected = form.querySelector('select[name="status"]');
      if (selected) {
        if (selected.value === "Collected") {
          if (!window.confirm("Confirm that this donation has been successfully collected and delivered?")) {
            event.preventDefault();
            return false;
          }
        } else if (selected.value === "Cancelled") {
          if (!window.confirm("Are you sure you want to cancel this donation request?")) {
            event.preventDefault();
            return false;
          }
        }
      }
    });
  });

  // Request Form Quantity Validation
  const requestForm = document.querySelector("#donation-request-form");
  if (requestForm) {
    const qtyInput = requestForm.querySelector('input[name="quantity_requested"]');
    if (qtyInput) {
      const maxVal = parseInt(qtyInput.getAttribute("max"), 10);
      qtyInput.addEventListener("input", () => {
        const val = parseInt(qtyInput.value, 10);
        if (val > maxVal) {
          qtyInput.setCustomValidity(`Requested quantity cannot exceed ${maxVal}`);
        } else if (val < 1) {
          qtyInput.setCustomValidity("Quantity must be at least 1");
        } else {
          qtyInput.setCustomValidity("");
        }
      });
    }
  }

  // Submit button loading spinner to prevent accidental double-submits
  document.querySelectorAll("form").forEach((form) => {
    // Only apply to forms that don't have preventDefault called
    form.addEventListener("submit", (e) => {
      if (e.defaultPrevented) return;
      const submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn && !submitBtn.dataset.noSpinner) {
        submitBtn.disabled = true;
        const originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = `
          <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
          Processing...
        `;
        // Re-enable if form takes too long or page doesn't unload
        setTimeout(() => {
          submitBtn.disabled = false;
          submitBtn.innerHTML = originalText;
        }, 8000);
      }
    });
  });
});
