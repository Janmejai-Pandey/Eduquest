/* ════════════════════════════════════════════════════════════
   EduQuest — Main Script
   ════════════════════════════════════════════════════════════ */

(function () {
    'use strict';

    // ════════════════════════════════════════
    // 1. NAVBAR — mobile menu + scroll effect
    // ════════════════════════════════════════
    const mobileToggle = document.getElementById('mobileToggle');
    const navLinks     = document.getElementById('navLinks');
    const navbar       = document.getElementById('navbar');

    if (mobileToggle && navLinks) {
        mobileToggle.addEventListener('click', () => {
            navLinks.classList.toggle('open');
            const spans = mobileToggle.querySelectorAll('span');

            if (navLinks.classList.contains('open')) {
                spans[0].style.transform = 'rotate(45deg) translate(5px, 5px)';
                spans[1].style.opacity   = '0';
                spans[2].style.transform = 'rotate(-45deg) translate(5px, -5px)';
            } else {
                spans[0].style.transform = '';
                spans[1].style.opacity   = '1';
                spans[2].style.transform = '';
            }
        });
    }

    if (navbar) {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 50) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        });
    }


    // ════════════════════════════════════════
    // 2. SCROLL REVEAL ANIMATIONS
    // ════════════════════════════════════════
    const fadeObserver = new IntersectionObserver(
        (entries) => {
            entries.forEach((entry, index) => {
                if (entry.isIntersecting) {
                    setTimeout(() => {
                        entry.target.classList.add('visible');
                    }, index * 100);
                    fadeObserver.unobserve(entry.target);
                }
            });
        },
        {
            threshold:  0.15,
            rootMargin: '0px 0px -50px 0px',
        }
    );

    document.querySelectorAll('.fade-in, .step').forEach((el) => {
        fadeObserver.observe(el);
    });


    // ════════════════════════════════════════
    // 3. ANIMATED COUNTERS
    // ════════════════════════════════════════
    const counterObserver = new IntersectionObserver(
        (entries) => {
            entries.forEach((entry) => {
                if (!entry.isIntersecting) return;

                const el     = entry.target;
                const target = parseInt(el.dataset.target);
                if (!target) return;

                let current   = 0;
                const steps   = 60;
                const inc     = target / steps;
                const stepMs  = 2000 / steps;

                const timer = setInterval(() => {
                    current += inc;
                    if (current >= target) {
                        current = target;
                        clearInterval(timer);
                    }
                    el.textContent = Math.floor(current);
                }, stepMs);

                counterObserver.unobserve(el);
            });
        },
        { threshold: 0.5 }
    );

    document.querySelectorAll('.stat-number[data-target]').forEach((el) => {
        counterObserver.observe(el);
    });


    // ════════════════════════════════════════
    // 4. CHAT TYPING EFFECT
    // ════════════════════════════════════════
    function typeEffect(element, text, speed = 25) {
        element.textContent = '';
        let i = 0;
        const timer = setInterval(() => {
            element.textContent += text[i];
            i++;
            if (i >= text.length) clearInterval(timer);
        }, speed);
    }

    window.addEventListener('load', () => {
        const botMsg = document.querySelector('.chat-msg.bot');
        if (!botMsg) return;

        const aiLabel = botMsg.querySelector('.ai-label');
        const originalText =
            'Based on your slide 12, supervised learning uses labeled training data to predict outcomes, while unsupervised learning finds hidden patterns without labels...';

        setTimeout(() => {
            // Remove existing text (keep ai-label)
            [...botMsg.childNodes].forEach((n) => {
                if (n !== aiLabel) botMsg.removeChild(n);
            });

            const span = document.createElement('span');
            span.className = 'typed-text';
            botMsg.appendChild(span);
            typeEffect(span, originalText, 25);
        }, 1500);
    });


    // ════════════════════════════════════════
    // 5. SMOOTH SCROLL FOR ANCHOR LINKS
    // ════════════════════════════════════════
    document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (href === '#') return;

            const target = document.querySelector(href);
            if (target) {
                e.preventDefault();
                target.scrollIntoView({
                    behavior: 'smooth',
                    block:    'start',
                });

                // Close mobile menu if open
                if (navLinks && navLinks.classList.contains('open')) {
                    navLinks.classList.remove('open');
                    const spans = mobileToggle.querySelectorAll('span');
                    spans[0].style.transform = '';
                    spans[1].style.opacity   = '1';
                    spans[2].style.transform = '';
                }
            }
        });
    });


    // ════════════════════════════════════════
    // 6. READY
    // ════════════════════════════════════════
    console.log('🎓 EduQuest website loaded successfully');

})();