# Implementation Plan

- [-] 1. Create unified navbar CSS file with base structure

  - Create `static/css/unified-navbar.css` file
  - Define CSS custom properties (variables) for colors, spacing, typography, and transitions
  - Set up base navbar container styles with gradient background and positioning
  - Implement responsive breakpoint variables
  - _Requirements: 6.1, 6.5, 10.1_

- [ ] 1.1 Write property test for CSS variable definitions
  - **Property 22: CSS variable usage**
  - **Validates: Requirements 6.5**

- [ ] 2. Implement brand section styling
  - Style `.navbar-brand` container with flexbox layout
  - Style `.navbar-logo` with responsive height (40px-65px) and aspect ratio preservation
  - Style `.brand-text` with appropriate typography and text-shadow
  - Add hover effects with smooth transitions
  - _Requirements: 1.5, 10.2_

- [ ] 2.1 Write property test for logo consistency
  - **Property 2: Logo consistency**
  - **Validates: Requirements 1.5, 10.2**

- [ ] 3. Style primary navigation links
  - Style `.primary-nav` container with flexbox and appropriate spacing
  - Style `.nav-link` elements with padding, border-radius, and typography
  - Implement hover states with background overlay (rgba(255,255,255,0.15))
  - Implement active states with background overlay (rgba(255,255,255,0.2))
  - Add icon styling with proper alignment
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.3, 3.4, 10.3_

- [ ] 3.1 Write property test for border radius compliance
  - **Property 4: Border radius range compliance**
  - **Validates: Requirements 2.3**

- [ ] 3.2 Write property test for transition duration
  - **Property 5: Transition duration compliance**
  - **Validates: Requirements 2.5**

- [ ] 3.3 Write property test for typography weights
  - **Property 6: Typography weight compliance**
  - **Validates: Requirements 2.4, 3.1**

- [ ] 3.4 Write property test for hover state opacity
  - **Property 9: Hover state background opacity**
  - **Validates: Requirements 3.3**

- [ ] 3.5 Write property test for active state opacity
  - **Property 8: Active state background opacity**
  - **Validates: Requirements 3.1**

- [ ] 3.6 Write property test for navigation spacing
  - **Property 11: Navigation spacing consistency**
  - **Validates: Requirements 3.4**

- [ ] 3.7 Write property test for text color compliance
  - **Property 35: Text color compliance**
  - **Validates: Requirements 10.3**

- [ ] 4. Implement dropdown menu styling
  - Style `.dropdown-menu` with border-radius, box-shadow, and positioning
  - Add fade-in animation with 0.3s duration
  - Style `.dropdown-item` with padding, icon alignment, and hover effects
  - Implement hover translation effect (3px-5px translateX)
  - Style dropdown toggle arrow with rotation on open state
  - Add margin-top spacing (0.5rem) below parent
  - _Requirements: 2.3, 3.2, 3.5, 7.1, 7.2, 7.3, 7.4_

- [ ] 4.1 Write property test for dropdown animation duration
  - **Property 23: Dropdown animation duration**
  - **Validates: Requirements 7.1**

- [ ] 4.2 Write property test for dropdown margin positioning
  - **Property 24: Dropdown margin positioning**
  - **Validates: Requirements 7.2**

- [ ] 4.3 Write property test for dropdown item hover translation
  - **Property 25: Dropdown item hover translation**
  - **Validates: Requirements 7.3**

- [ ] 4.4 Write property test for dropdown arrow rotation
  - **Property 26: Dropdown arrow rotation**
  - **Validates: Requirements 7.4**

- [ ] 4.5 Write property test for dropdown item padding
  - **Property 12: Dropdown item padding minimum**
  - **Validates: Requirements 3.5**

- [ ] 4.6 Write property test for dropdown open state highlighting
  - **Property 10: Dropdown open state highlighting**
  - **Validates: Requirements 3.2**

- [ ] 5. Style user profile section
  - Style `.user-menu-toggle` with flexbox, padding, and border-radius
  - Style `.user-avatar` as circular element (32px-42px diameter)
  - Style `.user-name` with font-weight 600
  - Style `.user-role` with font-size 0.75rem
  - Implement hover effects with background opacity increase (0.2 minimum)
  - Position user menu on far right using margin-left: auto or flex properties
  - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [ ] 5.1 Write property test for user avatar dimensions
  - **Property 28: User avatar dimensions**
  - **Validates: Requirements 8.2**

- [ ] 5.2 Write property test for user profile typography
  - **Property 29: User profile typography**
  - **Validates: Requirements 8.3**

- [ ] 5.3 Write property test for user profile hover opacity
  - **Property 30: User profile hover opacity**
  - **Validates: Requirements 8.4**

- [ ] 6. Implement notification system styling
  - Style `.action-button` for notification icon with circular or rounded design
  - Style notification badge with red background (#ef4444), 8px-10px diameter, circular shape
  - Add pulse animation with 2s duration
  - Style notification dropdown with appropriate width and item layout
  - Style notification items with icon, message, and timestamp layout
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 6.1 Write property test for notification badge color
  - **Property 31: Notification badge color**
  - **Validates: Requirements 9.1**

- [ ] 6.2 Write property test for notification badge dimensions
  - **Property 32: Notification badge dimensions**
  - **Validates: Requirements 9.2**

- [ ] 6.3 Write property test for notification badge animation
  - **Property 33: Notification badge animation**
  - **Validates: Requirements 9.3**

- [ ] 7. Implement mobile responsive styles
  - Add media query for screens below 992px
  - Style hamburger menu toggle button
  - Implement vertical navigation layout for mobile
  - Style mobile dropdown menus with inline expansion (position: static/relative)
  - Ensure touch target sizes are minimum 44px height
  - Add appropriate padding (1rem) for mobile menu
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [ ] 7.1 Write property test for mobile breakpoint behavior
  - **Property 13: Mobile breakpoint behavior**
  - **Validates: Requirements 4.1**

- [ ] 7.2 Write property test for mobile menu layout
  - **Property 14: Mobile menu layout**
  - **Validates: Requirements 4.2**

- [ ] 7.3 Write property test for mobile dropdown positioning
  - **Property 15: Mobile dropdown inline expansion**
  - **Validates: Requirements 4.3**

- [ ] 7.4 Write property test for mobile touch target size
  - **Property 16: Mobile touch target size**
  - **Validates: Requirements 4.4**

- [ ] 8. Implement accessibility features
  - Add focus indicator styles with 2px outline and 2px offset
  - Ensure all interactive elements have visible focus states
  - Add skip-to-content link styling
  - Verify ARIA attributes are properly styled (no visual changes needed, but document)
  - Add styles for reduced motion preference (@media prefers-reduced-motion)
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [ ] 8.1 Write property test for focus indicator presence
  - **Property 17: Focus indicator presence**
  - **Validates: Requirements 5.1**

- [ ] 8.2 Write property test for color contrast compliance
  - **Property 20: Color contrast compliance**
  - **Validates: Requirements 5.5**

- [ ] 9. Add brand identity and polish
  - Verify gradient background uses #019D66 to #017a4f
  - Add box-shadow with appropriate depth (0 2px 10px to 0 2px 20px rgba(0,0,0,0.12))
  - Ensure interactive overlays use rgba(255,255,255,0.1) to rgba(255,255,255,0.3)
  - Add smooth transitions to all interactive elements
  - Polish hover and active states across all components
  - _Requirements: 10.1, 10.4, 10.5_

- [ ] 9.1 Write property test for brand color usage
  - **Property 34: Brand color usage**
  - **Validates: Requirements 10.1**

- [ ] 9.2 Write property test for shadow presence
  - **Property 7: Shadow presence**
  - **Validates: Requirements 2.1, 10.5**

- [ ] 9.3 Write property test for interactive overlay opacity
  - **Property 36: Interactive overlay opacity range**
  - **Validates: Requirements 10.4**




- [ ] 10. Update base template to load unified stylesheet
  - Open `templates/base.html`
  - Add `<link>` tag for `unified-navbar.css` in the `<head>` section
  - Position it after legacy navbar CSS files to ensure proper override
  - Verify no conflicting class names or IDs
  - _Requirements: 6.1, 6.3_

- [ ] 11. Test cross-interface consistency
  - Load multiple admin pages and measure navbar styles
  - Load multiple user pages and measure navbar styles
  - Compare computed styles between admin and user interfaces
  - Verify all key properties match (height, colors, spacing, typography)
  - _Requirements: 1.1, 1.2, 1.4_

- [ ] 11.1 Write property test for cross-interface styling consistency
  - **Property 1: Cross-interface styling consistency**
  - **Validates: Requirements 1.1, 1.2, 1.4**

- [ ] 11.2 Write property test for design pattern consistency
  - **Property 3: Design pattern consistency**
  - **Validates: Requirements 1.4**

- [ ] 12. Test dropdown interactions
  - Test dropdown open/close behavior
  - Verify click-outside closes dropdown
  - Test keyboard navigation (Tab, Enter, Escape)
  - Verify ARIA attributes update correctly
  - Test on multiple browsers
  - _Requirements: 7.5, 5.4_

- [ ] 12.1 Write property test for click-outside dropdown closure
  - **Property 27: Click-outside dropdown closure**
  - **Validates: Requirements 7.5**

- [ ] 12.2 Write property test for ARIA expanded state synchronization
  - **Property 19: ARIA expanded state synchronization**
  - **Validates: Requirements 5.4**

- [ ] 13. Checkpoint - Ensure all tests pass, ask the user if questions arise

- [ ] 14. Perform cross-browser testing
  - Test on Chrome (latest version)
  - Test on Firefox (latest version)
  - Test on Safari (latest version)
  - Test on Edge (latest version)
  - Test on mobile browsers (iOS Safari, Chrome Android)
  - Document any browser-specific issues and add fixes
  - _Requirements: All_

- [ ] 15. Perform responsive testing at standard breakpoints
  - Test at 375px width (mobile)
  - Test at 768px width (tablet)
  - Test at 1024px width (desktop)
  - Test at 1440px width (large desktop)
  - Test at 1920px width (extra large desktop)
  - Verify smooth transitions between breakpoints
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [ ] 16. Deprecate legacy navbar CSS files
  - Identify all legacy navbar CSS files (enhanced-navbar.css, premium-navbar.css, redesigned-navbar.css)
  - Remove or comment out legacy navbar styles
  - Verify unified stylesheet properly overrides any remaining legacy styles
  - Test thoroughly after removal
  - _Requirements: 6.2, 6.4_

- [ ] 16.1 Write property test for stylesheet override effectiveness
  - **Property 21: Stylesheet override effectiveness**
  - **Validates: Requirements 6.4**

- [ ] 17. Final visual regression testing
  - Capture screenshots of navbar on key pages (dashboard, machines, irrigation, admin)
  - Compare screenshots across admin and user interfaces
  - Verify visual consistency
  - Document any intentional differences
  - _Requirements: 1.1, 1.2_

- [ ] 18. Accessibility audit
  - Run automated accessibility checker (axe-core or similar)
  - Perform manual keyboard navigation testing
  - Test with screen reader (NVDA or JAWS)
  - Verify all WCAG 2.1 AA criteria are met
  - Fix any identified issues
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 18.1 Write property test for ARIA attribute presence
  - **Property 18: ARIA attribute presence**
  - **Validates: Requirements 5.2**

- [ ] 19. Performance optimization
  - Minify CSS file for production
  - Verify file size is under 50KB
  - Test page load times with new stylesheet
  - Optimize any expensive CSS selectors if needed
  - _Requirements: All (performance consideration)_

- [ ] 20. Final checkpoint - Ensure all tests pass, ask the user if questions arise

- [ ] 21. Documentation and handoff
  - Document CSS custom properties and their usage
  - Create style guide showing navbar states and variations
  - Document any browser-specific quirks or workarounds
  - Provide migration notes for future developers
  - _Requirements: 6.2_
