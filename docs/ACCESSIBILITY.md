# Accessibility Guide for BlockShelf

## Overview

BlockShelf is committed to providing an accessible experience for all users, including those with disabilities. This document outlines our accessibility features, testing procedures, and best practices.

---

## Accessibility Standards Compliance

BlockShelf adheres to:
- **WCAG 2.1 Level AA** (Web Content Accessibility Guidelines)
- **Section 508** standards
- **ARIA 1.2** (Accessible Rich Internet Applications)

---

## Implemented Features

### 1. Keyboard Navigation ✅

**Skip Links:**
- Skip to main content link appears on Tab
- Located at the top of every page
- Allows keyboard users to bypass navigation

**Focus Management:**
- Visible focus indicators on all interactive elements
- Logical tab order throughout the application
- Focus trap in modals to prevent escape
- Focus returns to trigger element when modal closes

**Keyboard Shortcuts:**
- `Tab` - Move to next interactive element
- `Shift + Tab` - Move to previous interactive element
- `Enter/Space` - Activate buttons and links
- `Escape` - Close modals and dismiss alerts

### 2. Screen Reader Support ✅

**ARIA Live Regions:**
- Global announcer for important messages
- Form validation announcements
- Dynamic content updates announced
- Loading states announced

**Semantic HTML:**
- Proper heading hierarchy (h1 → h2 → h3)
- Semantic landmarks (`<main>`, `<nav>`, `<aside>`, `<header>`)
- Lists use `<ul>`, `<ol>`, and `<dl>` appropriately
- Tables have proper headers with `scope` attributes

**ARIA Attributes:**
- `aria-label` on icon-only buttons
- `aria-describedby` for form field help text
- `aria-invalid` on fields with errors
- `aria-required` on required fields
- `aria-live` regions for dynamic updates
- `aria-busy` during async operations

### 3. Form Accessibility ✅

**Labels:**
- All form fields have associated `<label>` elements
- Labels are properly linked via `for` attribute
- Icon-only buttons have `aria-label`

**Validation:**
- Client-side validation with immediate feedback
- Error messages announced to screen readers
- Errors displayed visually and programmatically
- Focus moves to first invalid field on submit

**Help Text:**
- Associated with fields via `aria-describedby`
- Available to screen readers
- Visible to all users

**Required Fields:**
- Marked with `required` attribute
- `aria-required="true"` for assistive technologies
- Visual indicator (if implemented)

### 4. Visual Accessibility ✅

**Color Contrast:**
- Text meets WCAG AA contrast ratio (4.5:1)
- Large text meets 3:1 ratio
- Interactive elements have sufficient contrast

**Focus Indicators:**
- 3px solid outline on focused elements
- 2px offset for clarity
- High contrast color (#0b5ed7)

**Responsive Design:**
- Scales from 320px to 4K displays
- No horizontal scrolling required
- Text reflows properly
- Pinch-to-zoom enabled

### 5. Motor Accessibility ✅

**Click Targets:**
- Minimum 44x44 CSS pixels (WCAG AAA)
- Adequate spacing between interactive elements
- Large buttons for primary actions

**Time Limits:**
- No time limits on form submission
- No auto-refresh or auto-redirect
- User controls all interactions

---

## Accessibility Features by Component

### Navigation

```html
<nav aria-label="Primary navigation">
  <ul role="list">
    <li><a href="...">Inventory</a></li>
    <li><a href="...">Add Item</a></li>
    <li><a href="...">Settings</a></li>
  </ul>
</nav>
```

**Features:**
- Labeled navigation landmark
- Keyboard accessible
- Current page indicated (aria-current)
- Skip link available

### Forms (Item Form)

```html
<form data-validate="true">
  <label for="id_name">Name</label>
  <input id="id_name"
         type="text"
         required
         aria-required="true"
         aria-describedby="name_help">
  <div id="name_help" class="form-text">Enter part name</div>
  <div id="name_error" class="invalid-feedback"></div>
</form>
```

**Features:**
- All fields have labels
- Required fields marked
- Help text associated
- Errors announced
- Live validation feedback

### Tables (Inventory List)

```html
<table role="table" aria-label="Inventory items">
  <thead>
    <tr>
      <th scope="col">Name</th>
      <th scope="col">Part ID</th>
      <th scope="col">Quantity</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Brick 2x4</td>
      <td>3001</td>
      <td>50</td>
    </tr>
  </tbody>
</table>
```

**Features:**
- Table role explicit
- Column headers with scope
- Caption or aria-label provided
- Sortable columns announced

### Modals

```html
<div class="modal"
     role="dialog"
     aria-modal="true"
     aria-labelledby="modal-title">
  <div class="modal-header">
    <h2 id="modal-title">Confirm Delete</h2>
    <button aria-label="Close dialog">×</button>
  </div>
  <div class="modal-body">...</div>
</div>
```

**Features:**
- Dialog role
- Focus trapped
- Escape key closes
- Title associated
- Close button accessible

### Buttons

```html
<!-- Text button (accessible by default) -->
<button type="submit">Save</button>

<!-- Icon-only button (needs aria-label) -->
<button aria-label="Toggle dark/light theme">🌓</button>

<!-- Loading state -->
<button aria-busy="true" disabled>Loading...</button>
```

---

## JavaScript Libraries

### 1. FormValidator (`static/js/validation.js`)

**Purpose:** Client-side form validation with accessibility

**Features:**
- Real-time validation
- ARIA live announcements
- Focus management on errors
- Custom validation rules
- Keyboard friendly

**Usage:**
```javascript
// Auto-initialize
<form data-validate="true">...</form>

// Manual initialization
const validator = new FormValidator(formElement, {
  validateOnBlur: true,
  validateOnInput: false,
  focusFirstError: true,
  ariaLiveRegion: true
});

// Add custom validator
validator.addValidator('partId', (value) => {
  return /^[0-9A-Za-z]+$/.test(value);
});
```

**Validation Rules:**
- `required` - Field must have value
- `min/max` - Number range
- `minlength/maxlength` - Text length
- `pattern` - Regex matching
- `email` - Valid email format
- `url` - Valid URL format
- `custom` - Custom validator function

### 2. AccessibilityManager (`static/js/accessibility.js`)

**Purpose:** Enhance accessibility features globally

**Features:**
- Skip link creation
- Focus management
- Keyboard navigation
- Modal focus trapping
- ARIA enhancements
- Landmark labeling

**Auto-initialized on page load**

**Usage:**
```javascript
// Announce to screen readers
A11y.announce('Item added successfully');

// Announce urgent message
A11y.announce('Error occurred', 'assertive');
```

---

## Testing Procedures

### Keyboard Navigation Testing

**Steps:**
1. Load any page
2. Press `Tab` key repeatedly
3. Verify focus moves through all interactive elements
4. Verify focus indicator is visible
5. Verify tab order is logical
6. Press `Shift+Tab` to navigate backwards
7. Press `Enter` or `Space` on buttons/links
8. Press `Escape` on modals

**Expected:**
- All interactive elements are keyboard accessible
- Focus indicator is always visible
- Tab order follows visual layout
- Buttons activate on Enter/Space
- Modals close on Escape

### Screen Reader Testing

**Tools:**
- **NVDA** (Windows) - Free
- **JAWS** (Windows) - Commercial
- **VoiceOver** (macOS) - Built-in
- **TalkBack** (Android) - Built-in
- **Orca** (Linux) - Free

**Test Scenarios:**

#### 1. Form Submission (Item Form)
```
Steps:
1. Navigate to Add Item page
2. Tab through form fields
3. Listen to field labels and help text
4. Enter invalid data
5. Submit form
6. Listen to error announcements
7. Tab to first error
8. Correct errors
9. Submit successfully

Expected:
- All labels read correctly
- Help text announced with field
- Errors announced when form submits
- Focus moves to first error
- Success message announced
```

#### 2. Navigation
```
Steps:
1. Load home page
2. Press Tab to skip link
3. Activate skip link
4. Verify focus moves to main content
5. Navigate through menu items
6. Listen to current page indicator

Expected:
- Skip link announces "Skip to main content"
- Main content receives focus
- Current page indicated
- All menu items accessible
```

#### 3. Table Navigation
```
Steps:
1. Navigate to inventory list
2. Tab into table
3. Listen to column headers
4. Navigate through rows
5. Activate sort controls

Expected:
- Table caption/label announced
- Column headers read
- Row data read with context
- Sort controls accessible
```

### Color Contrast Testing

**Tools:**
- **WebAIM Contrast Checker** - https://webaim.org/resources/contrastchecker/
- **Browser DevTools** - Lighthouse accessibility audit
- **axe DevTools** - Browser extension

**Minimum Ratios:**
- Normal text: 4.5:1 (WCAG AA)
- Large text (18pt+): 3:1 (WCAG AA)
- UI components: 3:1 (WCAG AA)

**Test All:**
- Text on background
- Button text on button background
- Link text on background
- Error messages
- Focus indicators
- Disabled states

### Automated Testing

**Tools:**
- **axe** - https://www.deque.com/axe/
- **Lighthouse** - Chrome DevTools
- **WAVE** - https://wave.webaim.org/
- **Pa11y** - Command-line tool

**Run Lighthouse:**
```bash
# Chrome DevTools > Lighthouse > Accessibility
Score target: 95+
```

**Run axe DevTools:**
```bash
# Browser extension: Scan entire page
# Fix all Critical and Serious issues
# Review and fix Moderate issues
```

---

## Common Accessibility Issues & Fixes

### Issue: Form field has no label

**Problem:**
```html
<input type="text" name="quantity">
```

**Fix:**
```html
<label for="quantity">Quantity</label>
<input type="text" id="quantity" name="quantity">
```

### Issue: Button has no accessible name

**Problem:**
```html
<button>🔍</button>
```

**Fix:**
```html
<button aria-label="Search">🔍</button>
```

### Issue: Error not associated with field

**Problem:**
```html
<input type="email" id="email">
<div class="error">Invalid email</div>
```

**Fix:**
```html
<input type="email" id="email" aria-describedby="email-error" aria-invalid="true">
<div id="email-error" class="error">Invalid email</div>
```

### Issue: Focus not visible

**Problem:**
```css
:focus {
  outline: none; /* Never do this! */
}
```

**Fix:**
```css
:focus {
  outline: 3px solid #0b5ed7;
  outline-offset: 2px;
}

/* Or provide alternative focus indicator */
:focus {
  outline: none;
  box-shadow: 0 0 0 3px rgba(11, 94, 215, 0.5);
}
```

### Issue: Modal not trapped

**Problem:**
```html
<!-- Focus can leave modal -->
<div class="modal">
  <button>Close</button>
  <input type="text">
</div>
<!-- User tabs to content behind modal -->
```

**Fix:**
```javascript
// Use AccessibilityManager (automatic)
// Or implement focus trap manually
modal.addEventListener('shown.bs.modal', () => {
  A11y.trapFocus(modal);
});
```

---

## Accessibility Checklist

Use this checklist when adding new features:

### Markup
- [ ] Semantic HTML elements used
- [ ] Headings in logical order (h1 → h2 → h3)
- [ ] Landmarks have labels (`<nav aria-label="...">`)
- [ ] All images have alt text
- [ ] All form fields have labels
- [ ] Tables have headers with scope

### Keyboard
- [ ] All functionality keyboard accessible
- [ ] Focus indicator visible
- [ ] Tab order is logical
- [ ] No keyboard traps (except modals)
- [ ] Skip link provided

### Screen Reader
- [ ] Content reads in logical order
- [ ] Dynamic content announced (aria-live)
- [ ] Form errors announced
- [ ] Buttons have accessible names
- [ ] Links have descriptive text

### Visual
- [ ] Color contrast meets WCAG AA (4.5:1)
- [ ] Text resizes to 200% without loss
- [ ] Content reflows on small screens
- [ ] No information conveyed by color alone

### Forms
- [ ] All fields have visible labels
- [ ] Required fields marked (aria-required)
- [ ] Errors clearly identified
- [ ] Help text associated (aria-describedby)
- [ ] Validation feedback provided

### Testing
- [ ] Tested with keyboard only
- [ ] Tested with screen reader
- [ ] Lighthouse score 95+
- [ ] axe DevTools shows no errors
- [ ] Contrast checked

---

## Resources

### Standards & Guidelines
- [WCAG 2.1](https://www.w3.org/WAI/WCAG21/quickref/)
- [ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [Section 508](https://www.section508.gov/)

### Testing Tools
- [NVDA Screen Reader](https://www.nvaccess.org/)
- [axe DevTools](https://www.deque.com/axe/devtools/)
- [WAVE Browser Extension](https://wave.webaim.org/extension/)
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)

### Learning Resources
- [WebAIM](https://webaim.org/)
- [A11y Project](https://www.a11yproject.com/)
- [MDN Accessibility](https://developer.mozilla.org/en-US/docs/Web/Accessibility)
- [Deque University](https://dequeuniversity.com/)

### Community
- [Web Accessibility Slack](https://web-a11y.slack.com/)
- [A11y Weekly Newsletter](https://a11yweekly.com/)

---

## Contributing

When contributing to BlockShelf:

1. **Follow WCAG 2.1 AA** guidelines
2. **Test with keyboard** before submitting PR
3. **Test with screen reader** if changing forms/navigation
4. **Run Lighthouse audit** (score 95+)
5. **Update this doc** if adding new patterns

---

## Support

If you encounter accessibility barriers:

1. Open an issue on GitHub
2. Tag with `accessibility` label
3. Include details:
   - Assistive technology used
   - Browser and version
   - Steps to reproduce
   - Expected vs actual behavior

We aim to address accessibility issues within 2 business days.

---

**Last Updated:** 2025-01-02
**Maintained By:** BlockShelf Development Team
**Accessibility Level:** WCAG 2.1 Level AA
