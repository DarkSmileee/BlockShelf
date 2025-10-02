/**
 * BlockShelf Form Validation Library
 *
 * Provides comprehensive client-side validation with accessibility support.
 * Features:
 * - Real-time field validation
 * - ARIA live regions for screen readers
 * - Custom validation rules
 * - Visual and auditory feedback
 * - Keyboard navigation support
 */

(function(window) {
    'use strict';

    /**
     * Main validation class
     */
    class FormValidator {
        constructor(formElement, options = {}) {
            if (!formElement) {
                throw new Error('Form element is required');
            }

            this.form = formElement;
            this.options = {
                validateOnBlur: true,
                validateOnInput: false,
                showErrorsInline: true,
                scrollToFirstError: true,
                focusFirstError: true,
                ariaLiveRegion: true,
                ...options
            };

            this.fields = new Map();
            this.errors = new Map();
            this.isValid = true;

            this.init();
        }

        /**
         * Initialize the validator
         */
        init() {
            // Create ARIA live region for screen reader announcements
            if (this.options.ariaLiveRegion) {
                this.createAriaLiveRegion();
            }

            // Find all validatable fields
            this.discoverFields();

            // Bind event listeners
            this.bindEvents();

            // Mark form as having validation
            this.form.setAttribute('novalidate', '');
            this.form.setAttribute('data-validator-initialized', 'true');
        }

        /**
         * Create ARIA live region for announcements
         */
        createAriaLiveRegion() {
            if (document.getElementById('validation-announcer')) return;

            const announcer = document.createElement('div');
            announcer.id = 'validation-announcer';
            announcer.className = 'sr-only';
            announcer.setAttribute('role', 'status');
            announcer.setAttribute('aria-live', 'polite');
            announcer.setAttribute('aria-atomic', 'true');
            document.body.appendChild(announcer);
            this.announcer = announcer;
        }

        /**
         * Announce message to screen readers
         */
        announce(message) {
            if (!this.announcer) return;

            this.announcer.textContent = '';
            setTimeout(() => {
                this.announcer.textContent = message;
            }, 100);
        }

        /**
         * Discover fields in the form that need validation
         */
        discoverFields() {
            const inputs = this.form.querySelectorAll('input, select, textarea');

            inputs.forEach(input => {
                const fieldName = input.name || input.id;
                if (!fieldName) return;

                const field = {
                    element: input,
                    name: fieldName,
                    rules: this.extractRules(input),
                    errorElement: null
                };

                this.fields.set(fieldName, field);

                // Ensure field has proper ARIA attributes
                this.enhanceFieldAccessibility(input);
            });
        }

        /**
         * Enhance field with accessibility attributes
         */
        enhanceFieldAccessibility(input) {
            const label = this.form.querySelector(`label[for="${input.id}"]`);

            // Add aria-label if no visible label
            if (!label && !input.getAttribute('aria-label')) {
                const placeholder = input.getAttribute('placeholder');
                if (placeholder) {
                    input.setAttribute('aria-label', placeholder);
                }
            }

            // Add aria-required for required fields
            if (input.required || input.hasAttribute('data-required')) {
                input.setAttribute('aria-required', 'true');
            }

            // Add aria-describedby for help text
            const helpText = input.parentElement.querySelector('.form-text');
            if (helpText && !helpText.id) {
                helpText.id = `${input.id}_help`;
                input.setAttribute('aria-describedby', helpText.id);
            }
        }

        /**
         * Extract validation rules from input element
         */
        extractRules(input) {
            const rules = [];

            // Required
            if (input.required || input.hasAttribute('data-required')) {
                rules.push({ type: 'required', message: 'This field is required' });
            }

            // Min/Max for numbers
            if (input.type === 'number') {
                const min = input.getAttribute('min');
                const max = input.getAttribute('max');

                if (min !== null) {
                    rules.push({
                        type: 'min',
                        value: parseFloat(min),
                        message: `Minimum value is ${min}`
                    });
                }

                if (max !== null) {
                    rules.push({
                        type: 'max',
                        value: parseFloat(max),
                        message: `Maximum value is ${max}`
                    });
                }
            }

            // Min/Max length for text
            const minLength = input.getAttribute('minlength');
            const maxLength = input.getAttribute('maxlength');

            if (minLength) {
                rules.push({
                    type: 'minlength',
                    value: parseInt(minLength),
                    message: `Minimum length is ${minLength} characters`
                });
            }

            if (maxLength) {
                rules.push({
                    type: 'maxlength',
                    value: parseInt(maxLength),
                    message: `Maximum length is ${maxLength} characters`
                });
            }

            // Pattern
            const pattern = input.getAttribute('pattern');
            if (pattern) {
                rules.push({
                    type: 'pattern',
                    value: new RegExp(pattern),
                    message: 'Invalid format'
                });
            }

            // Email
            if (input.type === 'email') {
                rules.push({
                    type: 'email',
                    message: 'Please enter a valid email address'
                });
            }

            // URL
            if (input.type === 'url') {
                rules.push({
                    type: 'url',
                    message: 'Please enter a valid URL'
                });
            }

            // Custom validation rules from data attributes
            const customRule = input.getAttribute('data-validate');
            if (customRule && this.customValidators[customRule]) {
                rules.push({
                    type: 'custom',
                    validator: this.customValidators[customRule],
                    message: input.getAttribute('data-validate-message') || 'Invalid value'
                });
            }

            return rules;
        }

        /**
         * Custom validators
         */
        customValidators = {
            positiveInteger: (value) => {
                const num = parseInt(value, 10);
                return !isNaN(num) && num >= 0 && num.toString() === value.trim();
            },
            quantity: (value) => {
                const num = parseInt(value, 10);
                return !isNaN(num) && num >= 0;
            },
            partId: (value) => {
                return /^[0-9A-Za-z]+$/.test(value.trim());
            }
        };

        /**
         * Bind event listeners
         */
        bindEvents() {
            // Form submit
            this.form.addEventListener('submit', (e) => this.handleSubmit(e));

            // Field events
            this.fields.forEach((field, name) => {
                if (this.options.validateOnBlur) {
                    field.element.addEventListener('blur', () => this.validateField(name));
                }

                if (this.options.validateOnInput) {
                    field.element.addEventListener('input', () => this.validateField(name));
                }

                // Clear error on focus
                field.element.addEventListener('focus', () => this.clearFieldError(name));
            });
        }

        /**
         * Handle form submit
         */
        handleSubmit(e) {
            e.preventDefault();

            const isValid = this.validateAll();

            if (isValid) {
                this.announce('Form is valid. Submitting...');
                this.form.submit();
            } else {
                this.announce(`Form has ${this.errors.size} error(s). Please correct them.`);

                if (this.options.focusFirstError) {
                    this.focusFirstError();
                }

                if (this.options.scrollToFirstError) {
                    this.scrollToFirstError();
                }
            }
        }

        /**
         * Validate all fields
         */
        validateAll() {
            this.errors.clear();
            let isValid = true;

            this.fields.forEach((field, name) => {
                if (!this.validateField(name)) {
                    isValid = false;
                }
            });

            this.isValid = isValid;
            return isValid;
        }

        /**
         * Validate a single field
         */
        validateField(fieldName) {
            const field = this.fields.get(fieldName);
            if (!field) return true;

            const value = field.element.value;
            const errors = [];

            // Run all validation rules
            for (const rule of field.rules) {
                const error = this.validateRule(value, rule, field.element);
                if (error) {
                    errors.push(error);
                    break; // Show only first error
                }
            }

            if (errors.length > 0) {
                this.setFieldError(fieldName, errors[0]);
                return false;
            } else {
                this.clearFieldError(fieldName);
                return true;
            }
        }

        /**
         * Validate a single rule
         */
        validateRule(value, rule, element) {
            switch (rule.type) {
                case 'required':
                    if (!value || value.trim() === '') {
                        return rule.message;
                    }
                    break;

                case 'min':
                    if (value !== '' && parseFloat(value) < rule.value) {
                        return rule.message;
                    }
                    break;

                case 'max':
                    if (value !== '' && parseFloat(value) > rule.value) {
                        return rule.message;
                    }
                    break;

                case 'minlength':
                    if (value.length > 0 && value.length < rule.value) {
                        return rule.message;
                    }
                    break;

                case 'maxlength':
                    if (value.length > rule.value) {
                        return rule.message;
                    }
                    break;

                case 'pattern':
                    if (value && !rule.value.test(value)) {
                        return rule.message;
                    }
                    break;

                case 'email':
                    if (value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
                        return rule.message;
                    }
                    break;

                case 'url':
                    try {
                        if (value) new URL(value);
                    } catch {
                        return rule.message;
                    }
                    break;

                case 'custom':
                    if (value && !rule.validator(value, element)) {
                        return rule.message;
                    }
                    break;
            }

            return null;
        }

        /**
         * Set error for a field
         */
        setFieldError(fieldName, message) {
            const field = this.fields.get(fieldName);
            if (!field) return;

            this.errors.set(fieldName, message);

            // Add error class
            field.element.classList.add('is-invalid');
            field.element.setAttribute('aria-invalid', 'true');

            // Create or update error element
            if (this.options.showErrorsInline) {
                let errorEl = field.element.parentElement.querySelector('.invalid-feedback');

                if (!errorEl) {
                    errorEl = document.createElement('div');
                    errorEl.className = 'invalid-feedback';
                    errorEl.id = `${field.element.id}_error`;
                    field.element.parentElement.appendChild(errorEl);
                    field.element.setAttribute('aria-describedby', errorEl.id);
                }

                errorEl.textContent = message;
                errorEl.style.display = 'block';
                field.errorElement = errorEl;
            }
        }

        /**
         * Clear error for a field
         */
        clearFieldError(fieldName) {
            const field = this.fields.get(fieldName);
            if (!field) return;

            this.errors.delete(fieldName);

            // Remove error class
            field.element.classList.remove('is-invalid');
            field.element.setAttribute('aria-invalid', 'false');

            // Hide error element
            if (field.errorElement) {
                field.errorElement.style.display = 'none';
            }
        }

        /**
         * Focus first field with error
         */
        focusFirstError() {
            const firstError = Array.from(this.errors.keys())[0];
            if (firstError) {
                const field = this.fields.get(firstError);
                if (field) {
                    field.element.focus();
                }
            }
        }

        /**
         * Scroll to first field with error
         */
        scrollToFirstError() {
            const firstError = Array.from(this.errors.keys())[0];
            if (firstError) {
                const field = this.fields.get(firstError);
                if (field) {
                    field.element.scrollIntoView({
                        behavior: 'smooth',
                        block: 'center'
                    });
                }
            }
        }

        /**
         * Add custom validator
         */
        addValidator(name, validatorFn) {
            this.customValidators[name] = validatorFn;
        }
    }

    // Export to global scope
    window.FormValidator = FormValidator;

    // Auto-initialize forms with data-validate attribute
    document.addEventListener('DOMContentLoaded', () => {
        const forms = document.querySelectorAll('form[data-validate="true"]');
        forms.forEach(form => {
            new FormValidator(form);
        });
    });

})(window);
