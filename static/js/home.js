// Smooth scrolling for navigation links
document.querySelectorAll('.nav-links a').forEach(link => {
    link.addEventListener('click', function(e) {
        const href = this.getAttribute('href');
        
        // Skip smooth scrolling for external links
        if (href.startsWith('/') || href.startsWith('http')) {
            return; // Allow normal navigation
        }

        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            window.scrollTo({
                top: target.offsetTop - 70, // Adjust for sticky header
                behavior: 'smooth',
            });
        }
    });
});

// Smooth scrolling for the "Explore Our Services" button
const exploreButton = document.querySelector('.cta-button');
if (exploreButton) {
    exploreButton.addEventListener('click', function (e) {
        e.preventDefault();
        const servicesSection = document.querySelector('#services');
        if (servicesSection) {
            window.scrollTo({
                top: servicesSection.offsetTop - 70, // Adjust for sticky header
                behavior: 'smooth',
            });
        }
    });
}

// Sticky header effect
window.addEventListener('scroll', () => {
    const navbar = document.querySelector('.navbar');
    if (window.scrollY > 50) {
        navbar.classList.add('scrolled');
    } else {
        navbar.classList.remove('scrolled');
    }
});
