document.addEventListener('DOMContentLoaded', function() {
    // Carousel thumbnail navigation
    initCarouselNavigation();
    
    // Image zoom functionality
    initImageZoom();
    
    // Print functionality
    initPrintFunctionality();
    
    // Share functionality
    initShareFunctionality();
    
    // Initialize availability calendar
    initAvailabilityCalendar();
});

function initCarouselNavigation() {
    const thumbnails = document.querySelectorAll('.thumbnail');
    thumbnails.forEach(thumbnail => {
        thumbnail.addEventListener('click', function() {
            const slideIndex = this.getAttribute('data-bs-slide-to');
            const carousel = new bootstrap.Carousel(document.getElementById('machineCarousel'));
            carousel.to(Number(slideIndex));
            
            // Update active class
            thumbnails.forEach(thumb => thumb.classList.remove('active'));
            this.classList.add('active');
        });
    });
    
    // Update thumbnails on carousel slide
    const carouselElement = document.getElementById('machineCarousel');
    if (carouselElement) {
        carouselElement.addEventListener('slid.bs.carousel', function(event) {
            const slideIndex = event.to;
            thumbnails.forEach(thumb => {
                if (thumb.getAttribute('data-bs-slide-to') == slideIndex) {
                    thumb.classList.add('active');
                } else {
                    thumb.classList.remove('active');
                }
            });
        });
    }
}

function initImageZoom() {
    const zoomContainer = document.getElementById('imageZoom');
    const zoomedImage = document.getElementById('zoomedImage');
    const zoomClose = document.querySelector('.zoom-close');
    const carouselImages = document.querySelectorAll('.carousel-image');
    
    carouselImages.forEach(image => {
        image.addEventListener('click', function() {
            zoomedImage.src = this.getAttribute('data-zoom');
            zoomContainer.style.display = 'flex';
            document.body.style.overflow = 'hidden';
        });
    });
    
    zoomClose.addEventListener('click', closeZoom);
    zoomContainer.addEventListener('click', function(e) {
        if (e.target === zoomContainer) {
            closeZoom();
        }
    });
    
    function closeZoom() {
        zoomContainer.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}

function initPrintFunctionality() {
    const printButton = document.querySelector('.print-button');
    if (printButton) {
        printButton.addEventListener('click', function() {
            window.print();
        });
    }
}

function initShareFunctionality() {
    const shareButton = document.querySelector('.share-button');
    if (shareButton && navigator.share) {
        shareButton.addEventListener('click', function() {
            navigator.share({
                title: document.title,
                text: 'Check out this machine: ' + document.title,
                url: window.location.href
            })
            .catch(error => console.log('Error sharing:', error));
        });
    } else if (shareButton) {
        shareButton.style.display = 'none';
    }
}

function initAvailabilityCalendar() {
    const calendarEl = document.getElementById('availability-calendar');
    if (calendarEl && typeof FullCalendar !== 'undefined') {
        // Get calendar events from data attribute
        const calendarData = document.getElementById('calendar-data');
        let events = [];
        
        if (calendarData && calendarData.getAttribute('data-events')) {
            try {
                events = JSON.parse(calendarData.getAttribute('data-events'));
            } catch (e) {
                console.error('Error parsing calendar events:', e);
            }
        }
        
        const calendar = new FullCalendar.Calendar(calendarEl, {
            initialView: 'dayGridMonth',
            headerToolbar: {
                left: 'prev,next today',
                center: 'title',
                right: ''
            },
            height: 'auto',
            events: events
        });
        calendar.render();
    }
} 