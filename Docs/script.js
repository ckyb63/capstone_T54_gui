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
}); 