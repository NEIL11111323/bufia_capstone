/**
 * Modal Form Handling
 * Functions for handling form submissions with modals
 */

document.addEventListener('DOMContentLoaded', function() {
  // Initialize all form modals
  initializeFormModals();
  
  // Initialize confirmation modals for forms
  initializeFormConfirmation();
});

/**
 * Initialize form modals for all elements with data-form-modal attribute
 */
function initializeFormModals() {
  document.querySelectorAll('[data-form-modal]').forEach(button => {
    button.addEventListener('click', function(e) {
      e.preventDefault();
      
      const formId = this.getAttribute('data-form-id');
      const form = document.getElementById(formId);
      
      if (!form) {
        console.error(`Form with ID ${formId} not found`);
        return;
      }
      
      const title = this.getAttribute('data-title') || 'Form Submission';
      const message = this.getAttribute('data-message') || 'Please confirm your submission';
      const confirmText = this.getAttribute('data-confirm-text') || 'Submit';
      const type = this.getAttribute('data-modal-type') || 'info';
      
      // Show the modal
      window.showModal({
        title: title,
        message: message,
        confirmText: confirmText,
        type: type,
        actionType: 'form-submit',
        customId: formId
      });
      
      // Listen for the modal confirm event
      document.addEventListener('modal:confirm', function modalConfirmHandler(event) {
        if (event.detail.id === formId) {
          // Remove the event listener to prevent multiple submissions
          document.removeEventListener('modal:confirm', modalConfirmHandler);
          
          // Submit the form
          form.submit();
        }
      });
    });
  });
}

/**
 * Initialize confirmation modals for forms with data-confirm attribute
 */
function initializeFormConfirmation() {
  document.querySelectorAll('form[data-confirm]').forEach(form => {
    form.addEventListener('submit', function(e) {
      // Only intercept if not already processed
      if (!this.hasAttribute('data-confirm-processed')) {
        e.preventDefault();
        
        const message = this.getAttribute('data-confirm') || 'Are you sure you want to submit this form?';
        const title = this.getAttribute('data-confirm-title') || 'Confirmation';
        const type = this.getAttribute('data-confirm-type') || 'confirm';
        
        // Show the modal
        window.showModal({
          title: title,
          message: message,
          type: type,
          actionType: 'custom',
          customId: this.id || 'form-' + Math.random().toString(36).substr(2, 9)
        });
        
        // Mark as processed to prevent infinite loops
        this.setAttribute('data-confirm-processed', 'true');
        
        // Store reference to the form
        const formRef = this;
        
        // Listen for the modal confirm event
        document.addEventListener('modal:confirm', function modalConfirmHandler(event) {
          if (event.detail.id === formRef.id || 
              (!formRef.id && event.detail.id.startsWith('form-'))) {
            // Remove the event listener to prevent multiple submissions
            document.removeEventListener('modal:confirm', modalConfirmHandler);
            
            // Submit the form
            formRef.submit();
          }
        });
      }
    });
  });
}

/**
 * Handle form validation with modals
 * @param {HTMLFormElement} form - The form element to validate
 * @returns {boolean} - Whether the form is valid
 */
function validateFormWithModal(form) {
  // Check HTML5 validation
  if (!form.checkValidity()) {
    // Find the first invalid field
    const invalidField = form.querySelector(':invalid');
    
    if (invalidField) {
      // Show error modal
      window.showModal({
        title: 'Validation Error',
        message: invalidField.validationMessage || 'Please check the form for errors',
        type: 'error',
        confirmText: 'OK',
        confirmClass: 'btn-secondary',
        actionType: 'custom'
      });
      
      // Focus the invalid field
      invalidField.focus();
    }
    
    return false;
  }
  
  return true;
}

/**
 * Show confirmation for standard buttons with data-confirm attribute
 */
document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('[data-confirm]').forEach(element => {
    if (element.tagName !== 'FORM') { // Skip forms, they're handled separately
      element.addEventListener('click', function(e) {
        e.preventDefault();
        
        const message = this.getAttribute('data-confirm');
        const title = this.getAttribute('data-confirm-title') || 'Confirmation';
        const href = this.getAttribute('href') || this.getAttribute('data-href');
        
        window.showModal({
          title: title,
          message: message,
          type: 'confirm',
          actionType: href ? 'redirect' : 'custom',
          targetUrl: href,
          customId: this.id || 'button-' + Math.random().toString(36).substr(2, 9)
        });
        
        // For custom actions that aren't redirects
        if (!href && this.hasAttribute('data-action')) {
          const actionName = this.getAttribute('data-action');
          const elementId = this.id || 'button-' + Math.random().toString(36).substr(2, 9);
          
          document.addEventListener('modal:confirm', function modalActionHandler(event) {
            if (event.detail.id === elementId) {
              // Remove the event listener
              document.removeEventListener('modal:confirm', modalActionHandler);
              
              // Trigger custom event that can be caught elsewhere
              const customEvent = new CustomEvent('custom-action', {
                detail: { action: actionName, element: element }
              });
              document.dispatchEvent(customEvent);
            }
          });
        }
      });
    }
  });
}); 