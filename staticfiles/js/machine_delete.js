// Machine delete functionality
document.addEventListener('DOMContentLoaded', function() {
    // Find all machine delete buttons
    const deleteButtons = document.querySelectorAll('.btn-delete');
    
    // Add click event handler to each delete button
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Find the parent form
            const form = this.closest('form.delete-form');
            
            // Confirm deletion
            if (confirm('Are you sure you want to delete this machine? This action cannot be undone.')) {
                // Submit the form directly - no need to create a new one
                form.submit();
            }
        });
    });
}); 