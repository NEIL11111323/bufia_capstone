/**
 * BUFIA Dashboard Interactive Elements
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize mini charts (sparklines)
    initCharts();
    
    // Initialize form handling
    initForms();
    
    // Initialize rental actions
    initRentalActions();
    
    // Initialize bulk actions
    initBulkActions();
    
    // Initialize keyboard navigation
    initKeyboardNavigation();
});

/**
 * Initialize Charts 
 */
function initCharts() {
    const usersSparklineEl = document.getElementById('usersSparkline');
    const machinesSparklineEl = document.getElementById('machinesSparkline');
    
    // Only initialize if elements exist
    if (usersSparklineEl) {
        new Chart(usersSparklineEl, {
            type: 'line',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                datasets: [{
                    data: usersSparklineEl.dataset.values ? 
                        JSON.parse(usersSparklineEl.dataset.values) : 
                        [10, 12, 11, 14, 16, 17],
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: { display: false },
                    y: { display: false }
                },
                elements: {
                    point: { radius: 0 }
                }
            }
        });
    }
    
    if (machinesSparklineEl) {
        new Chart(machinesSparklineEl, {
            type: 'line',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                datasets: [{
                    data: machinesSparklineEl.dataset.values ? 
                        JSON.parse(machinesSparklineEl.dataset.values) : 
                        [5, 7, 8, 8, 10, 12],
                    borderColor: '#f59e0b',
                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: { display: false },
                    y: { display: false }
                }
            }
        });
    }
    
    // Initialize progress rings
    document.querySelectorAll('.progress-ring-value').forEach(ring => {
        if (ring.dataset.percentage) {
            const radius = ring.getAttribute('r');
            const circumference = 2 * Math.PI * radius;
            const percentage = parseFloat(ring.dataset.percentage);
            const dashOffset = circumference * (1 - percentage / 100);
            
            ring.style.strokeDasharray = circumference;
            ring.style.strokeDashoffset = dashOffset;
        }
    });
}

/**
 * Initialize Forms
 */
function initForms() {
    // Rental creation form handling
    const createRentalForm = document.getElementById('createRentalForm');
    const submitRentalBtn = document.getElementById('submitRental');
    
    if (submitRentalBtn && createRentalForm) {
        submitRentalBtn.addEventListener('click', function() {
            if (!createRentalForm.checkValidity()) {
                createRentalForm.reportValidity();
                return;
            }
            
            // Show loading state
            this.disabled = true;
            this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Creating...';
            
            // Submit the form
            createRentalForm.submit();
        });
    }
    
    // Support form submission
    const supportForm = document.getElementById('supportForm');
    const submitSupportBtn = document.getElementById('submitSupport');
    
    if (submitSupportBtn && supportForm) {
        submitSupportBtn.addEventListener('click', function() {
            if (!supportForm.checkValidity()) {
                supportForm.reportValidity();
                return;
            }
            
            // Show loading state
            this.disabled = true;
            this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Sending...';
            
            // In a real app, you'd submit the form data via AJAX here
            setTimeout(() => {
                // Hide the modal
                bootstrap.Modal.getInstance(document.getElementById('supportModal')).hide();
                
                // Reset the form
                supportForm.reset();
                
                // Reset button state
                this.disabled = false;
                this.innerHTML = '<i class="fas fa-paper-plane me-2"></i>Send Message';
                
                // Show success message
                window.showSuccessModal({
                    title: 'Message Sent',
                    message: 'Your support request has been sent successfully. Our team will get back to you soon.',
                    redirectUrl: null,
                    redirectText: 'OK'
                });
            }, 1500);
        });
    }
}

/**
 * Initialize Rental Actions
 */
function initRentalActions() {
    // Handle rental approval
    document.querySelectorAll('.btn-approve-rental').forEach(button => {
        button.addEventListener('click', function() {
            const rentalId = this.getAttribute('data-rental-id');
            const title = this.getAttribute('data-title');
            const message = this.getAttribute('data-message');
            const details = this.getAttribute('data-details');
            
            window.showModal({
                title: title,
                message: message,
                details: details,
                confirmText: 'Approve',
                confirmIcon: 'fa-check',
                confirmClass: 'btn-success',
                type: 'confirm',
                actionType: 'custom',
                customId: 'approve-rental-' + rentalId
            });
            
            document.addEventListener('modal:confirm', function modalConfirmHandler(event) {
                if (event.detail.id === 'approve-rental-' + rentalId) {
                    document.removeEventListener('modal:confirm', modalConfirmHandler);
                    
                    // In a real app, you'd make an AJAX call to approve the rental
                    // For demo, show a success toast after a delay
                    setTimeout(() => {
                        window.showToast({
                            title: 'Rental Approved',
                            message: 'The rental request has been successfully approved.',
                            type: 'success'
                        });
                        
                        // Optional: reload the page to show updated status
                        // window.location.reload();
                    }, 1000);
                }
            });
        });
    });
    
    // Handle rental rejection
    document.querySelectorAll('.btn-reject-rental').forEach(button => {
        button.addEventListener('click', function() {
            const rentalId = this.getAttribute('data-rental-id');
            const title = this.getAttribute('data-title');
            const message = this.getAttribute('data-message');
            const details = this.getAttribute('data-details');
            
            window.showModal({
                title: title,
                message: message,
                details: details,
                confirmText: 'Reject',
                confirmIcon: 'fa-times',
                confirmClass: 'btn-danger',
                type: 'warning',
                actionType: 'custom',
                customId: 'reject-rental-' + rentalId
            });
            
            document.addEventListener('modal:confirm', function modalConfirmHandler(event) {
                if (event.detail.id === 'reject-rental-' + rentalId) {
                    document.removeEventListener('modal:confirm', modalConfirmHandler);
                    
                    // In a real app, you'd make an AJAX call to reject the rental
                    // For demo, show a success toast after a delay
                    setTimeout(() => {
                        window.showToast({
                            title: 'Rental Rejected',
                            message: 'The rental request has been rejected.',
                            type: 'warning'
                        });
                        
                        // Optional: reload the page to show updated status
                        // window.location.reload();
                    }, 1000);
                }
            });
        });
    });
    
    // Handle delete actions
    document.querySelectorAll('.btn-delete').forEach(button => {
        button.addEventListener('click', function() {
            const target = this.getAttribute('data-target');
            const title = this.getAttribute('data-title');
            const message = this.getAttribute('data-message');
            
            window.showModal({
                title: title,
                message: message,
                confirmText: 'Delete',
                confirmIcon: 'fa-trash',
                confirmClass: 'btn-danger',
                type: 'danger',
                actionType: 'redirect',
                redirectUrl: target
            });
        });
    });
}

/**
 * Initialize Bulk Actions
 */
function initBulkActions() {
    // Bulk approval functionality
    const selectAllCheckbox = document.getElementById('selectAllRentals');
    const rentalCheckboxes = document.querySelectorAll('.rental-checkbox');
    const approveSelectedBtn = document.getElementById('approveSelectedRentals');
    
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            rentalCheckboxes.forEach(checkbox => {
                checkbox.checked = this.checked;
            });
        });
    }
    
    if (approveSelectedBtn) {
        approveSelectedBtn.addEventListener('click', function() {
            const selectedRentals = Array.from(rentalCheckboxes)
                .filter(checkbox => checkbox.checked)
                .map(checkbox => checkbox.value);
            
            if (selectedRentals.length === 0) {
                window.showModal({
                    title: 'No Rentals Selected',
                    message: 'Please select at least one rental request to approve.',
                    type: 'info',
                    confirmText: 'OK',
                    confirmClass: 'btn-secondary',
                    actionType: 'custom'
                });
                return;
            }
            
            window.showModal({
                title: 'Confirm Bulk Approval',
                message: `Are you sure you want to approve ${selectedRentals.length} rental requests?`,
                confirmText: 'Approve All',
                confirmIcon: 'fa-check',
                confirmClass: 'btn-success',
                type: 'confirm',
                actionType: 'custom',
                customId: 'bulk-approve'
            });
            
            document.addEventListener('modal:confirm', function modalConfirmHandler(event) {
                if (event.detail.id === 'bulk-approve') {
                    document.removeEventListener('modal:confirm', modalConfirmHandler);
                    
                    // In a real app, you'd make an AJAX call to bulk approve rentals
                    // For demo, show a success message after a delay
                    setTimeout(() => {
                        // Hide the modal
                        bootstrap.Modal.getInstance(document.getElementById('bulkApprovalModal')).hide();
                        
                        window.showSuccessModal({
                            title: 'Rentals Approved',
                            message: `${selectedRentals.length} rental requests have been approved successfully.`,
                            redirectUrl: window.location.href,
                            redirectText: 'Refresh Page'
                        });
                    }, 1500);
                }
            });
        });
    }
    
    // Handle backup generation
    document.addEventListener('custom-action', function(event) {
        if (event.detail.action === 'generate_backup') {
            // Show loading modal
            window.showModal({
                title: 'Generating Backup',
                message: 'Please wait while the system backup is being generated...',
                type: 'info',
                confirmText: 'Processing...',
                confirmClass: 'btn-primary disabled',
                cancelText: '',
                cancelIcon: ''
            });
            
            // In a real app, you'd make an AJAX call to generate the backup
            // For demo, show a success message after a delay
            setTimeout(() => {
                window.showSuccessModal({
                    title: 'Backup Generated',
                    message: 'The system backup has been generated successfully and is ready for download.',
                    redirectText: 'Download Backup',
                    redirectUrl: '#'  // This would be a real download URL in a real app
                });
            }, 2500);
        }
    });
}

/**
 * Initialize Keyboard Navigation for Accessibility
 */
function initKeyboardNavigation() {
    // Add keyboard navigation for dropdown menus
    document.querySelectorAll('.action-dropdown-menu').forEach(menu => {
        menu.addEventListener('keydown', function(e) {
            const items = Array.from(this.querySelectorAll('.action-dropdown-item'));
            if (!items.length) return;
            
            const index = items.indexOf(document.activeElement);
            
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                items[(index + 1) % items.length].focus();
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                items[(index - 1 + items.length) % items.length].focus();
            }
        });
    });
    
    // Skip to main content functionality
    const skipLink = document.querySelector('.skip-link');
    if (skipLink) {
        skipLink.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.getElementById(this.getAttribute('href').substring(1));
            if (target) {
                target.setAttribute('tabindex', '-1');
                target.focus();
            }
        });
    }
} 