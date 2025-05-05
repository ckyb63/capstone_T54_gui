// Main JavaScript for PPE A.I. Vending Machine Project Site

document.addEventListener('DOMContentLoaded', function() {
    // Mobile menu toggle functionality
    const hamburger = document.querySelector('.hamburger-menu');
    const navOverlay = document.querySelector('.nav-overlay');
    const navLinks = document.querySelectorAll('.nav-links a');
    
    function toggleMobileMenu() {
        document.body.classList.toggle('menu-open');
    }
    
    hamburger.addEventListener('click', toggleMobileMenu);
    navOverlay.addEventListener('click', toggleMobileMenu);
    
    // Close menu when a link is clicked
    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            if (document.body.classList.contains('menu-open')) {
                toggleMobileMenu();
            }
        });
    });
    
    // Add scrolled class to body when page is scrolled
    window.addEventListener('scroll', () => {
        if (window.scrollY > 20) {
            document.body.classList.add('scrolled');
        } else {
            document.body.classList.remove('scrolled');
        }
        
        // Show/hide back to top button
        if (window.scrollY > 300) {
            document.querySelector('.back-to-top').classList.add('visible');
        } else {
            document.querySelector('.back-to-top').classList.remove('visible');
        }
        
        // Update progress bar
        updateProgressBar();
    });
    
    // Smooth scrolling for anchor links with fixed header offset adjustment for mobile
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);
            
            if (targetElement) {
                // Adjust scroll position based on screen size (account for fixed header on mobile)
                const isMobile = window.innerWidth <= 768;
                const offset = isMobile ? 60 : 50;
                
                window.scrollTo({
                    top: targetElement.offsetTop - offset,
                    behavior: 'smooth'
                });
            }
        });
    });
    
    // Active section highlighting in navigation
    const sections = document.querySelectorAll('.content-section');
    const navLinksArray = document.querySelectorAll('nav ul li a');
    
    window.addEventListener('scroll', () => {
        let current = '';
        
        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.clientHeight;
            if (pageYOffset >= (sectionTop - 100)) {
                current = section.getAttribute('id');
            }
        });
        
        navLinksArray.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === `#${current}`) {
                link.classList.add('active');
            }
        });
    });
    
    // Add active class styling to navigation
    const style = document.createElement('style');
    style.textContent = `
        nav ul li a.active {
            color: var(--secondary-color);
            font-weight: 700;
            position: relative;
        }
        
        nav ul li a.active::after {
            content: '';
            position: absolute;
            bottom: -5px;
            left: 0;
            width: 100%;
            height: 2px;
            background-color: var(--secondary-color);
        }
    `;
    document.head.appendChild(style);
    
    // Image lazy loading
    const lazyImages = document.querySelectorAll('img.section-image, img.component-image');
    
    // Add loading="lazy" attribute to images
    lazyImages.forEach(img => {
        img.setAttribute('loading', 'lazy');
    });
    
    // For browsers that support IntersectionObserver
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const image = entry.target;
                    
                    // If the image has a data-src, load that image
                    if (image.dataset.src) {
                        image.src = image.dataset.src;
                        image.removeAttribute('data-src');
                    }
                    
                    image.classList.add('loaded');
                    imageObserver.unobserve(image);
                }
            });
        });
        
        lazyImages.forEach(image => {
            // If we're using data-src
            if (image.src && !image.dataset.src) {
                image.dataset.src = image.src;
                // Set a low-res placeholder or blank
                image.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"%3E%3C/svg%3E';
            }
            
            imageObserver.observe(image);
        });
    } else {
        // Fallback for browsers that don't support IntersectionObserver
        lazyImages.forEach(image => {
            image.classList.add('loaded');
        });
    }
    
    // Add loaded animation to images
    const imageStyle = document.createElement('style');
    imageStyle.textContent = `
        .section-image, .component-image {
            opacity: 0;
            transform: translateY(20px);
            transition: opacity 0.5s ease, transform 0.5s ease;
        }
        
        .section-image.loaded, .component-image.loaded {
            opacity: 1;
            transform: translateY(0);
        }
    `;
    document.head.appendChild(imageStyle);
    
    // Back to top button functionality
    document.querySelector('.back-to-top').addEventListener('click', () => {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });

    // Image click-to-enlarge functionality
    setupImageEnlarge();
    
    function setupImageEnlarge() {
        // Get all images that should be enlargeable, excluding carousel images which are handled separately
        const enlargeableImages = document.querySelectorAll('.section-image, .component-image:not(.carousel-image)');
        
        // Create fullscreen overlay if it doesn't exist
        let fullscreenOverlay = document.querySelector('.fullscreen-overlay');
        if (!fullscreenOverlay) {
            fullscreenOverlay = document.createElement('div');
            fullscreenOverlay.classList.add('fullscreen-overlay');
            
            const fullscreenImage = document.createElement('img');
            fullscreenImage.classList.add('fullscreen-image');
            
            const closeBtn = document.createElement('button');
            closeBtn.classList.add('close-fullscreen');
            closeBtn.innerHTML = '&times;';
            closeBtn.addEventListener('click', closeFullscreen);
            
            fullscreenOverlay.appendChild(fullscreenImage);
            fullscreenOverlay.appendChild(closeBtn);
            document.body.appendChild(fullscreenOverlay);
            
            // Close fullscreen when clicking outside image
            fullscreenOverlay.addEventListener('click', e => {
                if (e.target === fullscreenOverlay) {
                    closeFullscreen();
                }
            });
            
            // Close fullscreen on ESC key
            document.addEventListener('keydown', e => {
                if (e.key === 'Escape' && fullscreenOverlay.classList.contains('active')) {
                    closeFullscreen();
                }
            });
        }
        
        // Add click event to all enlargeable images
        enlargeableImages.forEach(image => {
            image.style.cursor = 'pointer';
            image.addEventListener('click', function() {
                openFullscreen(this.src, false); // Added second parameter to indicate not from carousel
            });
        });
        
        function openFullscreen(imageSrc, isCarousel = false) {
            const fullscreenImage = fullscreenOverlay.querySelector('.fullscreen-image');
            fullscreenImage.src = imageSrc;
            fullscreenOverlay.classList.add('active');
            document.body.style.overflow = 'hidden'; // Prevent scrolling
        }
        
        function closeFullscreen() {
            fullscreenOverlay.classList.remove('active');
            document.body.style.overflow = ''; // Restore scrolling
            
            // Remove any carousel navigation controls if they exist
            const navButtons = fullscreenOverlay.querySelectorAll('.fullscreen-nav-btn');
            navButtons.forEach(btn => btn.remove());
        }
    }

    // Carousel Functionality
    initCarousel();
    
    function initCarousel() {
        const carousels = document.querySelectorAll('.carousel-container');
        
        carousels.forEach(carousel => {
            const track = carousel.querySelector('.carousel-track');
            const slides = Array.from(carousel.querySelectorAll('.carousel-slide'));
            const prevBtn = carousel.querySelector('.prev-btn');
            const nextBtn = carousel.querySelector('.next-btn');
            const dotsContainer = carousel.querySelector('.carousel-dots');
            const fullscreenBtn = carousel.querySelector('.fullscreen-btn');
            
            let currentIndex = 0;
            
            // Create dot indicators
            slides.forEach((_, index) => {
                const dot = document.createElement('div');
                dot.classList.add('carousel-dot');
                if (index === 0) dot.classList.add('active');
                dot.addEventListener('click', () => goToSlide(index));
                dotsContainer.appendChild(dot);
            });
            
            // Button event listeners
            if (prevBtn) {
                prevBtn.addEventListener('click', () => {
                    goToSlide(currentIndex - 1);
                });
            }
            
            if (nextBtn) {
                nextBtn.addEventListener('click', () => {
                    goToSlide(currentIndex + 1);
                });
            }
            
            // Make carousel images clickable
            slides.forEach(slide => {
                const img = slide.querySelector('img');
                if (img) {
                    img.addEventListener('click', () => {
                        openCarouselFullscreen(img.src);
                    });
                }
            });
            
            // Fullscreen functionality
            if (fullscreenBtn) {
                fullscreenBtn.addEventListener('click', () => {
                    // Use the same fullscreen overlay as our image enlarger
                    const imageSrc = slides[currentIndex].querySelector('img').src;
                    openCarouselFullscreen(imageSrc);
                });
            }
            
            // Navigation with swipe for touch devices
            let touchStartX = 0;
            let touchEndX = 0;
            
            track.addEventListener('touchstart', e => {
                touchStartX = e.changedTouches[0].clientX;
            });
            
            track.addEventListener('touchend', e => {
                touchEndX = e.changedTouches[0].clientX;
                handleSwipe();
            });
            
            function handleSwipe() {
                const swipeThreshold = 50;
                if (touchStartX - touchEndX > swipeThreshold) {
                    // Swipe left, go to next
                    goToSlide(currentIndex + 1);
                } else if (touchEndX - touchStartX > swipeThreshold) {
                    // Swipe right, go to previous
                    goToSlide(currentIndex - 1);
                }
            }
            
            // Core carousel functions
            function goToSlide(index) {
                // Handle loop around
                if (index < 0) {
                    index = slides.length - 1;
                } else if (index >= slides.length) {
                    index = 0;
                }
                
                currentIndex = index;
                updateCarousel();
            }
            
            function updateCarousel() {
                // Move the track
                track.style.transform = `translateX(-${currentIndex * 100}%)`;
                
                // Update dots
                const dots = dotsContainer.querySelectorAll('.carousel-dot');
                dots.forEach((dot, index) => {
                    if (index === currentIndex) {
                        dot.classList.add('active');
                    } else {
                        dot.classList.remove('active');
                    }
                });
            }
            
            // Function specific for opening carousel images in fullscreen
            function openCarouselFullscreen(imageSrc) {
                const fullscreenOverlay = document.querySelector('.fullscreen-overlay');
                const fullscreenImage = fullscreenOverlay.querySelector('.fullscreen-image');
                fullscreenImage.src = imageSrc;
                fullscreenOverlay.classList.add('active');
                document.body.style.overflow = 'hidden'; // Prevent scrolling
                
                // Add navigation controls for the carousel images
                addCarouselControls();
            }
            
            // Add carousel-specific navigation controls to the fullscreen view
            function addCarouselControls() {
                const fullscreenOverlay = document.querySelector('.fullscreen-overlay');
                
                // Remove existing carousel controls if any
                const existingControls = fullscreenOverlay.querySelectorAll('.fullscreen-nav-btn');
                existingControls.forEach(control => control.remove());
                
                // Add carousel navigation controls
                const prevFullscreenBtn = document.createElement('button');
                prevFullscreenBtn.classList.add('fullscreen-nav-btn', 'prev-fullscreen-btn');
                prevFullscreenBtn.innerHTML = '&#10094;';
                prevFullscreenBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    goToSlide(currentIndex - 1);
                    updateFullscreenImage();
                });
                
                const nextFullscreenBtn = document.createElement('button');
                nextFullscreenBtn.classList.add('fullscreen-nav-btn', 'next-fullscreen-btn');
                nextFullscreenBtn.innerHTML = '&#10095;';
                nextFullscreenBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    goToSlide(currentIndex + 1);
                    updateFullscreenImage();
                });
                
                fullscreenOverlay.appendChild(prevFullscreenBtn);
                fullscreenOverlay.appendChild(nextFullscreenBtn);
                
                // Add keyboard navigation for fullscreen
                const keyHandler = (e) => {
                    if (!fullscreenOverlay.classList.contains('active')) return;
                    
                    if (e.key === 'ArrowLeft') {
                        goToSlide(currentIndex - 1);
                        updateFullscreenImage();
                    } else if (e.key === 'ArrowRight') {
                        goToSlide(currentIndex + 1);
                        updateFullscreenImage();
                    }
                };
                
                // Remove existing event listener to avoid duplicates
                document.removeEventListener('keydown', keyHandler);
                document.addEventListener('keydown', keyHandler);
                
                // Remove controls when fullscreen is closed
                const removeControls = () => {
                    if (!fullscreenOverlay.classList.contains('active')) {
                        prevFullscreenBtn.remove();
                        nextFullscreenBtn.remove();
                        document.removeEventListener('keydown', keyHandler);
                        fullscreenOverlay.removeEventListener('transitionend', removeControls);
                    }
                };
                
                fullscreenOverlay.addEventListener('transitionend', removeControls);
            }
            
            function updateFullscreenImage() {
                const fullscreenOverlay = document.querySelector('.fullscreen-overlay');
                if (fullscreenOverlay && fullscreenOverlay.classList.contains('active')) {
                    const fullscreenImage = fullscreenOverlay.querySelector('.fullscreen-image');
                    fullscreenImage.src = slides[currentIndex].querySelector('img').src;
                }
            }
        });
    }

    // Progress bar functionality
    function updateProgressBar() {
        const progressBar = document.getElementById('progress-bar');
        if (progressBar) {
            const totalHeight = document.body.scrollHeight - window.innerHeight;
            const progress = (window.pageYOffset / totalHeight) * 100;
            progressBar.style.width = progress + '%';
        }
    }

    // Initial progress bar update
    updateProgressBar();
}); 