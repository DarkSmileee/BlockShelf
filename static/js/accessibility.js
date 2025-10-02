/**
 * BlockShelf Accessibility Enhancement Library
 *
 * Provides comprehensive accessibility features:
 * - Focus management
 * - Keyboard navigation
 * - ARIA attributes
 * - Screen reader announcements
 * - Skip links
 * - Focus trapping for modals
 */

(function(window) {
    'use strict';

    /**
     * Accessibility Manager
     */
    class AccessibilityManager {
        constructor() {
            this.focusableElements = 'a[href], area[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]), iframe, object, embed, [tabindex]:not([tabindex="-1"]), [contenteditable]';
            this.init();
        }

        init() {
            this.enhanceSkipLinks();
            this.enhanceFocusManagement();
            this.enhanceKeyboardNavigation();
            this.enhanceModals();
            this.enhanceTables();
            this.enhanceForms();
            this.addLandmarkLabels();
        }

        /**
         * Enhance skip links for keyboard navigation
         */
        enhanceSkipLinks() {
            // Create skip to main content link if it doesn't exist
            if (!document.getElementById('skip-to-main')) {
                const skipLink = document.createElement('a');
                skipLink.id = 'skip-to-main';
                skipLink.href = '#main-content';
                skipLink.className = 'skip-link sr-only sr-only-focusable';
                skipLink.textContent = 'Skip to main content';
                skipLink.style.cssText = `
                    position: absolute;
                    top: -40px;
                    left: 0;
                    background: #000;
                    color: #fff;
                    padding: 8px;
                    z-index: 100;
                    text-decoration: none;
                `;

                skipLink.addEventListener('focus', function() {
                    this.style.top = '0';
                });

                skipLink.addEventListener('blur', function() {
                    this.style.top = '-40px';
                });

                document.body.insertBefore(skipLink, document.body.firstChild);
            }

            // Ensure main content has id
            const mainContent = document.querySelector('main') || document.querySelector('[role="main"]');
            if (mainContent && !mainContent.id) {
                mainContent.id = 'main-content';
                mainContent.setAttribute('tabindex', '-1');
            }
        }

        /**
         * Enhance focus management
         */
        enhanceFocusManagement() {
            // Add visible focus indicator class
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Tab') {
                    document.body.classList.add('user-is-tabbing');
                }
            });

            document.addEventListener('mousedown', () => {
                document.body.classList.remove('user-is-tabbing');
            });

            // Add focus styles
            if (!document.getElementById('a11y-focus-styles')) {
                const style = document.createElement('style');
                style.id = 'a11y-focus-styles';
                style.textContent = `
                    body.user-is-tabbing *:focus {
                        outline: 3px solid #0b5ed7;
                        outline-offset: 2px;
                    }

                    .sr-only {
                        position: absolute;
                        width: 1px;
                        height: 1px;
                        padding: 0;
                        margin: -1px;
                        overflow: hidden;
                        clip: rect(0, 0, 0, 0);
                        white-space: nowrap;
                        border-width: 0;
                    }

                    .sr-only-focusable:focus {
                        position: static;
                        width: auto;
                        height: auto;
                        overflow: visible;
                        clip: auto;
                        white-space: normal;
                    }
                `;
                document.head.appendChild(style);
            }
        }

        /**
         * Enhance keyboard navigation
         */
        enhanceKeyboardNavigation() {
            // Add keyboard support for custom interactive elements
            document.addEventListener('keydown', (e) => {
                const target = e.target;

                // Handle Enter/Space for role="button" elements
                if (target.getAttribute('role') === 'button' && !target.tagName.match(/button|a/i)) {
                    if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        target.click();
                    }
                }

                // Handle Escape key for dismissible elements
                if (e.key === 'Escape') {
                    const modal = document.querySelector('.modal.show');
                    if (modal) {
                        const closeBtn = modal.querySelector('[data-bs-dismiss="modal"]');
                        if (closeBtn) closeBtn.click();
                    }
                }
            });
        }

        /**
         * Enhance modals with focus trapping
         */
        enhanceModals() {
            const modals = document.querySelectorAll('.modal');

            modals.forEach(modal => {
                modal.setAttribute('role', 'dialog');
                modal.setAttribute('aria-modal', 'true');

                // Add aria-labelledby if modal has title
                const title = modal.querySelector('.modal-title');
                if (title && !title.id) {
                    title.id = `modal-title-${Math.random().toString(36).substr(2, 9)}`;
                    modal.setAttribute('aria-labelledby', title.id);
                }

                // Trap focus within modal
                modal.addEventListener('shown.bs.modal', () => {
                    this.trapFocus(modal);
                });

                modal.addEventListener('hidden.bs.modal', () => {
                    this.releaseFocus();
                });
            });
        }

        /**
         * Trap focus within an element
         */
        trapFocus(element) {
            const focusableContent = element.querySelectorAll(this.focusableElements);
            const firstFocusable = focusableContent[0];
            const lastFocusable = focusableContent[focusableContent.length - 1];

            // Store the element that had focus before modal opened
            this.previousFocus = document.activeElement;

            // Focus first element
            firstFocusable?.focus();

            // Handle tab key
            const handleTab = (e) => {
                if (e.key !== 'Tab') return;

                if (e.shiftKey) {
                    // Shift + Tab
                    if (document.activeElement === firstFocusable) {
                        e.preventDefault();
                        lastFocusable?.focus();
                    }
                } else {
                    // Tab
                    if (document.activeElement === lastFocusable) {
                        e.preventDefault();
                        firstFocusable?.focus();
                    }
                }
            };

            element.addEventListener('keydown', handleTab);
            element._tabHandler = handleTab;
        }

        /**
         * Release focus trap
         */
        releaseFocus() {
            // Restore focus to previously focused element
            if (this.previousFocus) {
                this.previousFocus.focus();
                this.previousFocus = null;
            }
        }

        /**
         * Enhance tables with accessibility attributes
         */
        enhanceTables() {
            const tables = document.querySelectorAll('table:not([role])');

            tables.forEach(table => {
                // Add role if not present
                table.setAttribute('role', 'table');

                // Add aria-label if caption exists
                const caption = table.querySelector('caption');
                if (caption && !table.hasAttribute('aria-label')) {
                    table.setAttribute('aria-label', caption.textContent);
                }

                // Enhance headers
                const headers = table.querySelectorAll('th');
                headers.forEach(th => {
                    if (!th.getAttribute('scope')) {
                        const isInThead = th.closest('thead');
                        th.setAttribute('scope', isInThead ? 'col' : 'row');
                    }
                });
            });
        }

        /**
         * Enhance forms with accessibility features
         */
        enhanceForms() {
            const forms = document.querySelectorAll('form');

            forms.forEach(form => {
                // Ensure all inputs have labels or aria-label
                const inputs = form.querySelectorAll('input, select, textarea');

                inputs.forEach(input => {
                    const id = input.id;
                    if (!id) return;

                    const label = form.querySelector(`label[for="${id}"]`);

                    // Add aria-label if no visible label
                    if (!label && !input.getAttribute('aria-label')) {
                        const placeholder = input.getAttribute('placeholder');
                        if (placeholder) {
                            input.setAttribute('aria-label', placeholder);
                        }
                    }

                    // Associate error messages with inputs
                    const errorMsg = input.parentElement?.querySelector('.invalid-feedback');
                    if (errorMsg) {
                        if (!errorMsg.id) {
                            errorMsg.id = `${id}-error`;
                        }
                        const describedBy = input.getAttribute('aria-describedby') || '';
                        if (!describedBy.includes(errorMsg.id)) {
                            input.setAttribute('aria-describedby',
                                describedBy ? `${describedBy} ${errorMsg.id}` : errorMsg.id
                            );
                        }
                    }

                    // Associate help text with inputs
                    const helpText = input.parentElement?.querySelector('.form-text');
                    if (helpText) {
                        if (!helpText.id) {
                            helpText.id = `${id}-help`;
                        }
                        const describedBy = input.getAttribute('aria-describedby') || '';
                        if (!describedBy.includes(helpText.id)) {
                            input.setAttribute('aria-describedby',
                                describedBy ? `${describedBy} ${helpText.id}` : helpText.id
                            );
                        }
                    }
                });

                // Add submit button aria-label if text is icon only
                const submitBtns = form.querySelectorAll('button[type="submit"]');
                submitBtns.forEach(btn => {
                    if (!btn.textContent.trim() && !btn.getAttribute('aria-label')) {
                        btn.setAttribute('aria-label', 'Submit form');
                    }
                });
            });
        }

        /**
         * Add labels to landmark regions
         */
        addLandmarkLabels() {
            // Navigation
            const navs = document.querySelectorAll('nav');
            navs.forEach((nav, index) => {
                if (!nav.getAttribute('aria-label')) {
                    const label = nav.classList.contains('navbar') ? 'Main navigation' :
                                  `Navigation ${index + 1}`;
                    nav.setAttribute('aria-label', label);
                }
            });

            // Main
            const main = document.querySelector('main');
            if (main && !main.getAttribute('aria-label')) {
                main.setAttribute('aria-label', 'Main content');
            }

            // Aside
            const asides = document.querySelectorAll('aside');
            asides.forEach((aside, index) => {
                if (!aside.getAttribute('aria-label')) {
                    aside.setAttribute('aria-label', `Sidebar ${index + 1}`);
                }
            });

            // Footer
            const footer = document.querySelector('footer');
            if (footer && !footer.getAttribute('aria-label')) {
                footer.setAttribute('aria-label', 'Footer');
            }
        }

        /**
         * Announce message to screen readers
         */
        announce(message, priority = 'polite') {
            let announcer = document.getElementById('global-announcer');

            if (!announcer) {
                announcer = document.createElement('div');
                announcer.id = 'global-announcer';
                announcer.className = 'sr-only';
                announcer.setAttribute('role', 'status');
                announcer.setAttribute('aria-live', priority);
                announcer.setAttribute('aria-atomic', 'true');
                document.body.appendChild(announcer);
            }

            // Clear and set new message
            announcer.textContent = '';
            setTimeout(() => {
                announcer.textContent = message;
            }, 100);
        }
    }

    /**
     * Initialize accessibility manager
     */
    const a11y = new AccessibilityManager();

    // Export to global scope
    window.A11y = a11y;
    window.AccessibilityManager = AccessibilityManager;

})(window);
