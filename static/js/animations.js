/**
 * PhishGuard Scrolling Animations & Interactions
 * IntersectionObserver reveals, number counter easing, scroll progress bar, nav transitions.
 */

document.addEventListener('DOMContentLoaded', () => {
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // 1. Scroll Progress Bar
    const progressBar = document.getElementById('scroll-progress');
    if (progressBar) {
        window.addEventListener('scroll', () => {
            const scrollTop = window.scrollY || document.documentElement.scrollTop;
            const docHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
            const progress = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
            progressBar.style.width = `${progress}%`;
        }, { passive: true });
    }

    // 2. Navigation Transition on Scroll
    const nav = document.querySelector('.landing-nav');
    if (nav) {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 20) {
                nav.classList.add('scrolled');
            } else {
                nav.classList.remove('scrolled');
            }
        }, { passive: true });
    }

    // 3. Intersection Observer for Scroll Reveals
    const revealElements = document.querySelectorAll('.reveal-on-scroll');
    if (revealElements.length > 0) {
        if (prefersReducedMotion || !('IntersectionObserver' in window)) {
            revealElements.forEach(el => el.classList.add('is-revealed'));
        } else {
            const revealObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('is-revealed');
                        observer.unobserve(entry.target);
                    }
                });
            }, {
                threshold: 0.15,
                rootMargin: '0px 0px -40px 0px'
            });

            revealElements.forEach(el => revealObserver.observe(el));
        }
    }

    // 4. Smooth Number Counting Animations
    const counterElements = document.querySelectorAll('[data-counter]');
    if (counterElements.length > 0) {
        function animateCounter(el) {
            const targetVal = parseFloat(el.getAttribute('data-counter')) || 0;
            const decimals = parseInt(el.getAttribute('data-decimals') || '0', 10);
            const prefix = el.getAttribute('data-prefix') || '';
            const suffix = el.getAttribute('data-suffix') || '';
            const duration = 1400; // ms
            const startTime = performance.now();

            function easeOutQuart(x) {
                return 1 - Math.pow(1 - x, 4);
            }

            function update(currentTime) {
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);
                const currentVal = easeOutQuart(progress) * targetVal;

                el.textContent = `${prefix}${currentVal.toFixed(decimals)}${suffix}`;

                if (progress < 1) {
                    requestAnimationFrame(update);
                } else {
                    el.textContent = `${prefix}${targetVal.toFixed(decimals)}${suffix}`;
                }
            }

            requestAnimationFrame(update);
        }

        if (prefersReducedMotion || !('IntersectionObserver' in window)) {
            counterElements.forEach(el => {
                const targetVal = parseFloat(el.getAttribute('data-counter')) || 0;
                const decimals = parseInt(el.getAttribute('data-decimals') || '0', 10);
                const prefix = el.getAttribute('data-prefix') || '';
                const suffix = el.getAttribute('data-suffix') || '';
                el.textContent = `${prefix}${targetVal.toFixed(decimals)}${suffix}`;
            });
        } else {
            const counterObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        animateCounter(entry.target);
                        observer.unobserve(entry.target);
                    }
                });
            }, { threshold: 0.2 });

            counterElements.forEach(el => counterObserver.observe(el));
        }
    }
});
