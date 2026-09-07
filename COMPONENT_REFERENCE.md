# 🎨 WellView Modern UI/UX - Quick Reference & Tips

## 📋 Quick Class Reference

### Buttons
```html
<!-- Primary Action (Blue → Purple Gradient) -->
<button class="btn btn-main">Action</button>

<!-- Secondary Action (Border-based) -->
<button class="btn btn-secondary">Cancel</button>

<!-- Success Action (Green gradient) -->
<button class="btn btn-success">Confirm</button>

<!-- Danger Action (Red gradient) -->  
<button class="btn btn-danger">Delete</button>

<!-- Ghost Button (Transparent, for navigation) -->
<button class="btn btn-ghost">Navigate</button>

<!-- Large Button -->
<button class="btn btn-main btn-lg">Big Action</button>

<!-- With Icon -->
<button class="btn btn-main">
    <i class="bi bi-check-circle me-2"></i>Submit
</button>
```

### Cards
```html
<!-- Modern Glassmorphic Card -->
<div class="card">
    <div class="card-header">
        <h5>Card Title</h5>
    </div>
    <div class="card-body">
        <!-- Content here -->
    </div>
    <div class="card-footer">
        <!-- Footer content -->
    </div>
</div>

<!-- Dashboard Card -->
<div class="dashboard-card">
    <div class="dashboard-card-value">42</div>
    <div class="dashboard-card-label">Active Users</div>
</div>
```

### Forms
```html
<!-- Form Group -->
<div class="form-group">
    <label class="form-label">
        <i class="bi bi-envelope me-2"></i>Email Address
    </label>
    <input type="email" class="form-control" placeholder="Enter email">
</div>

<!-- Upload Area -->
<div class="upload-area">
    <i class="bi bi-cloud-upload upload-icon"></i>
    <p class="upload-text">Drag files here</p>
    <input type="file" class="upload-input">
    <button type="button" class="btn btn-primary">Browse</button>
</div>
```

### Alerts & Status
```html
<!-- Success Alert -->
<div class="alert alert-success" role="alert">
    <i class="bi bi-check-circle me-2"></i>Success message
</div>

<!-- Warning Alert -->
<div class="alert alert-warning" role="alert">
    <i class="bi bi-exclamation-triangle me-2"></i>Warning message
</div>

<!-- Danger Alert -->
<div class="alert alert-danger" role="alert">
    <i class="bi bi-x-circle me-2"></i>Error message
</div>

<!-- Info Alert -->
<div class="alert alert-info" role="alert">
    <i class="bi bi-info-circle me-2"></i>Info message
</div>

<!-- Status Badges -->
<span class="badge badge-success">Active</span>
<span class="badge badge-warning">Pending</span>
<span class="badge badge-danger">Failed</span>
<span class="badge badge-primary">New</span>
```

### Typography
```html
<!-- Main Heading (Auto Gradient) -->
<h1>Your Title Here</h1>

<!-- Section Heading -->
<h2 class="section-title">Section Title</h2>
<p class="section-subtitle">Optional subtitle text</p>

<!-- Large Heading -->
<h3>Large Heading</h3>

<!-- Muted Text -->
<p class="text-muted">Disabled or secondary text</p>

<!-- Primary Colored Text -->
<p class="text-primary">Important text</p>
```

### Spacing Utilities
```html
<!-- Margins -->
<div class="mb-lg">// margin-bottom: 32px</div>
<div class="mb-md">// margin-bottom: 24px</div>
<div class="mb-sm">// margin-bottom: 16px</div>
<div class="mt-lg">// margin-top: 32px</div>

<!-- Padding -->
<div class="p-lg">// padding: 32px</div>
<div class="p-md">// padding: 24px</div>
<div class="p-sm">// padding: 16px</div>
```

### Gap (Flexbox)
```html
<!-- Gap Utilities -->
<div class="gap-lg">24px gap</div>
<div class="gap-md">16px gap</div>
<div class="gap-sm">8px gap</div>
```

### Grid System
```html
<!-- Responsive Dashboard Grid -->
<div class="dashboard-grid">
    <div class="dashboard-card">Card 1</div>
    <div class="dashboard-card">Card 2</div>
    <div class="dashboard-card">Card 3</div>
</div>

<!-- Bootstrap Grid (4 columns → 1 column on mobile) -->
<div class="row g-3">
    <div class="col-md-6">Half width on desktop</div>
    <div class="col-md-6">Half width on desktop</div>
</div>
```

---

## 🎬 Using Animations

### Fade In Animation
```html
<div class="fade-in">Content fades in</div>
```

### Slide Up Animation
```html
<div class="slide-up">Content slides up</div>
```

### Pulse Animation (Loading)
```html
<div class="pulse">Loading...</div>
```

### Spinner Animation
```html
<div class="spinner"></div>
```

---

## 🎨 Colors & Gradients

### Primary Color
```css
color: var(--primary);        /* #0066ff */
background: var(--primary);
```

### Gradient Text (like H1)
```css
background: linear-gradient(135deg, var(--primary) 0%, var(--accent-alt) 100%);
-webkit-background-clip: text;
-webkit-text-fill-color: transparent;
background-clip: text;
```

### Gradient Button
```css
background: linear-gradient(135deg, var(--primary) 0%, var(--accent-alt) 100%);
color: white;
```

### Glassmorphic Background
```css
background: rgba(255, 255, 255, 0.85);
backdrop-filter: blur(20px);
border: 1px solid rgba(255, 255, 255, 0.4);
```

---

## 💡 Best Practices

### 1. **Color Usage**
```
✓ Use var(--primary) for main actions
✓ Use var(--accent-alt) for secondary emphasis
✓ Use status colors for alerts (success, danger, warning, info)
✓ Avoid pure black text - use var(--text-1)
```

### 2. **Spacing**
```
✓ Use gap utilities instead of margins for flex layouts
✓ Use padding utilities for internal spacing
✓ Keep 24px gap between major sections
✓ Use 16px gap between components
```

### 3. **Icons**
```
✓ Always pair icons with text labels
✓ Use Bootstrap Icons (bi- prefix)
✓ Add me-2 (margin-end) after icons in buttons/labels
✓ Use size: 1.5rem for decorated icons
```

### 4. **Interactive Elements**
```
✓ Always add hover state feedback
✓ Use 250ms transition for smooth feel
✓ Provide visual feedback on :focus
✓ Use cursor: pointer for clickable items
```

### 5. **Accessibility**
```
✓ Include alt text for images
✓ Use ARIA labels for icon-only buttons
✓ Ensure color contrast ratio ≥ 4.5:1
✓ Support keyboard navigation
✓ Test with screen readers
```

### 6. **Forms**
```
✓ Always use <label> with form inputs
✓ Provide clear placeholder text
✓ Validate inputs before submission
✓ Show error messages clearly
✓ Use required attribute for mandatory fields
```

### 7. **Mobile Optimization**
```
✓ Use d-none d-md-inline for desktop-only content
✓ Stack buttons vertically on mobile (d-grid)
✓ Test on real devices
✓ Ensure touch targets ≥ 44px
✓ Use responsive font sizes
```

---

## 🔧 Custom CSS

### Add Custom Color
```css
:root {
    --my-color: #12345f;
}

.my-button {
    background: var(--my-color);
}
```

### Create Custom Button Style
```css
.btn-custom {
    background: linear-gradient(135deg, #ff6b35 0%, #00d4ff 100%);
    color: white;
    border-radius: 12px;
    padding: 10px 22px;
    font-weight: 600;
    box-shadow: 0 4px 12px rgba(255, 107, 53, 0.2);
    transition: all var(--transition-base);
}

.btn-custom:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(255, 107, 53, 0.3);
}
```

### Create Custom Card
```css
.my-card {
    background: rgba(255, 255, 255, 0.85);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.4);
    border-radius: 18px;
    padding: 24px;
    transition: all var(--transition-base);
}

.my-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.1);
}
```

---

## 📱 Responsive Breakpoints

```css
/* Large screens (desktop) */
@media (min-width: 1200px) { ... }

/* Tablets */
@media (max-width: 768px) { ... }

/* Large phones */
@media (max-width: 576px) { ... }

/* Small phones */
@media (max-width: 480px) { ... }
```

### Bootstrap Classes for Responsive
```html
<!-- Show on desktop, hide on mobile -->
<div class="d-none d-md-inline">Desktop only</div>

<!-- Show on mobile, hide on desktop -->
<div class="d-md-none">Mobile only</div>

<!-- Responsive grid -->
<div class="row g-3">
    <div class="col-12 col-md-6 col-lg-4">Dynamic width</div>
</div>
```

---

## 🎯 Common Patterns

### Navigation Item
```html
<a href="#" class="btn btn-ghost d-none d-md-inline-block">
    <i class="bi bi-home me-1"></i>Home
</a>
```

### Hero Section
```html
<div class="page-shell">
    <div class="page-card">
        <h1>Welcome to WellView</h1>
        <p class="section-subtitle">Premium health report analysis</p>
        <button class="btn btn-main">Get Started</button>
    </div>
</div>
```

### Feature Card
```html
<div class="col-md-6">
    <div class="dashboard-card">
        <i class="bi bi-heart-fill text-danger" style="font-size: 2rem;"></i>
        <div class="dashboard-card-value mt-3">42</div>
        <div class="dashboard-card-label">Heart Rate Data</div>
    </div>
</div>
```

### Data Table
```html
<table class="table">
    <thead>
        <tr>
            <th>Column 1</th>
            <th>Column 2</th>
            <th>Status</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>Data 1</td>
            <td>Data 2</td>
            <td><span class="badge badge-success">Active</span></td>
        </tr>
    </tbody>
</table>
```

---

## 🚀 Performance Tips

1. **Use CSS variables** for consistent theming
2. **Minimize repaints** - use transform instead of top/left
3. **Hardware acceleration** - use will-change sparingly
4. **Optimize images** - use modern formats (WebP)
5. **Lazy load** - defer non-critical resources
6. **Minify CSS** - reduce file size for production

---

## 🧪 Testing Checklist

- [ ] Test on Chrome, Firefox, Safari, Edge
- [ ] Test on mobile devices (iOS & Android)
- [ ] Check color contrast ratios (WCAG AA)
- [ ] Test keyboard navigation
- [ ] Run through screen reader
- [ ] Check page load performance
- [ ] Test with different zoom levels
- [ ] Verify animations smooth (60fps)
- [ ] Test form validation
- [ ] Check responsive design breakpoints

---

## 📚 Resources

- **Bootstrap Icons**: https://icons.getbootstrap.com/
- **Google Fonts - Poppins**: https://fonts.google.com/specimen/Poppins
- **CSS Gradients**: https://cssgradient.io/
- **Color Picker**: https://htmlcolorcodes.com/
- **Cubic Bezier Easing**: https://cubic-bezier.com/

---

## ❓ Troubleshooting

### Buttons not showing gradient
- Ensure `.btn-main` class is applied
- Check that CSS is loaded correctly
- Verify no conflicting CSS overrides

### Cards not blurry (glassmorphism)
- Check `backdrop-filter: blur(20px);` is supported
- Fallback: add semi-transparent white background
- Older browsers may not support blur effect

### Animations not smooth
- Verify browser supports 60fps rendering
- Check for JavaScript blocking main thread
- Use Chrome DevTools Performance tab

### Colors not matching
- Use CSS variables: `var(--primary)` instead of hex
- Check for color space differences
- Test on different displays

---

**Last Updated**: February 26, 2026  
**Version**: Modern UI/UX v1.0  
**Ready for Production** ✅
