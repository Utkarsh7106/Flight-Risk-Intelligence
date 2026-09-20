---
name: Executive HR Intelligence
colors:
  surface: '#f7f9fb'
  surface-dim: '#d8dadc'
  surface-bright: '#f7f9fb'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f6'
  surface-container: '#eceef0'
  surface-container-high: '#e6e8ea'
  surface-container-highest: '#e0e3e5'
  on-surface: '#191c1e'
  on-surface-variant: '#45464d'
  inverse-surface: '#2d3133'
  inverse-on-surface: '#eff1f3'
  outline: '#76777d'
  outline-variant: '#c6c6cd'
  surface-tint: '#565e74'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#131b2e'
  on-primary-container: '#7c839b'
  inverse-primary: '#bec6e0'
  secondary: '#515f74'
  on-secondary: '#ffffff'
  secondary-container: '#d5e3fd'
  on-secondary-container: '#57657b'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#001e2f'
  on-tertiary-container: '#008cc7'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dae2fd'
  primary-fixed-dim: '#bec6e0'
  on-primary-fixed: '#131b2e'
  on-primary-fixed-variant: '#3f465c'
  secondary-fixed: '#d5e3fd'
  secondary-fixed-dim: '#b9c7e0'
  on-secondary-fixed: '#0d1c2f'
  on-secondary-fixed-variant: '#3a485c'
  tertiary-fixed: '#c9e6ff'
  tertiary-fixed-dim: '#89ceff'
  on-tertiary-fixed: '#001e2f'
  on-tertiary-fixed-variant: '#004c6e'
  background: '#f7f9fb'
  on-background: '#191c1e'
  surface-variant: '#e0e3e5'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  mono-data:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  container-max: 1440px
  gutter: 1.5rem
  margin-page: 2rem
  stack-sm: 0.5rem
  stack-md: 1rem
  stack-lg: 2rem
---

## Brand & Style
The design system is engineered for high-stakes decision-making in human resources. It prioritizes clarity, analytical depth, and institutional trust. The visual language follows a **Modern Corporate** style—fusing the systematic rigor of enterprise software with the refined aesthetics of modern SaaS. 

The UI should evoke a sense of professional authority and calm efficiency. By utilizing generous white space and a structured information hierarchy, the system transforms dense workforce metrics into actionable insights. Every element is designed to minimize cognitive load, allowing HR Business Partners to identify trends, risks, and opportunities at a glance.

## Colors
The palette is anchored by **Deep Navy** (#0F172A) for primary navigation and headers to establish authority. **Slate** (#334155) serves as the secondary color for sub-text and icons, maintaining a grounded, professional feel. **Cyan** (#0EA5E9) is used sparingly as an action and highlight color to draw attention to interactive elements and primary call-to-actions.

The background uses a tiered neutral scale (Slate 50 to 100) to define content areas without relying on heavy borders. Semantic colors are critical: **Emerald 600** for low-risk/positive growth, **Amber 500** for medium-risk/caution, and **Red 600** for high-risk/immediate attention. These are calibrated for high legibility against white and light-gray backgrounds.

## Typography
This design system utilizes **Inter** for its exceptional legibility in data-dense environments. The type scale is strictly hierarchical to handle complex dashboards. 

Key decisions:
- **Numerical Data:** Use tabular figures (`tnum`) for all data tables and KPI cards to ensure columns of numbers align vertically.
- **Headlines:** Bold weights are used for metric totals, while medium weights define section headers.
- **Labels:** Small caps or uppercase labels are used for table headers and chart legends to distinguish them from primary data points.
- **Mobile:** Headline sizes scale down by 20% on mobile devices, while body text remains consistent at 16px for readability.

## Layout & Spacing
The layout follows a **Fluid Grid** system within a 1440px maximum container. It uses a standard 12-column grid for dashboard widgets, allowing for flexible configurations (e.g., 3-column KPI rows, 2-column chart layouts).

- **Desktop:** 24px (1.5rem) gutters between cards. Page margins are set to 32px (2rem).
- **Tablet:** 16px gutters; sidebar collapses into a hamburger menu or icon-only rail.
- **Mobile:** Single column stack with 16px margins.
- **Rhythm:** An 8px linear scale governs all padding and margins to ensure visual harmony across diverse component sizes.

## Elevation & Depth
Elevation is expressed through **Tonal Layering** and subtle, functional shadows. 
- **Level 0 (Background):** Slate 50 (#F8FAFC).
- **Level 1 (Cards/Surface):** Pure White (#FFFFFF) with a 1px border in Slate 200. No shadow.
- **Level 2 (Interactive/Hover):** Pure White with a soft, diffused shadow (0px 4px 6px -1px rgba(15, 23, 42, 0.1)).
- **AI Insights:** Highlighted with a subtle inner-glow or a Cyan 50 background to distinguish machine-generated analysis from standard raw data.

Depth is used to denote interactivity rather than decoration. Overlays (modals/drawers) use a 40% opacity Slate 900 backdrop.

## Shapes
The design system employs a **Soft** shape language. Standard components like buttons and input fields use a 4px (0.25rem) radius. Data cards and larger containers use an 8px (0.5rem) radius. 

This subtle rounding balances the professional "seriousness" of the HR environment with a modern, approachable feel. Status badges and tags use a fully rounded (pill) shape to differentiate them from actionable buttons or data containers.

## Components
- **KPI Cards:** Large numeric value (Display LG) with a sparkline trend and a semantic "percent change" indicator.
- **Data Tables:** High-density rows (40px height) with subtle zebra striping. Headers are fixed on scroll. Columns for "Risk" include a colored status dot.
- **Buttons:** Primary buttons are Solid Deep Navy. Secondary are Outlined Slate. Ghost buttons are used for table actions to reduce visual noise.
- **Status Badges:** Use low-saturation background tints with high-saturation text (e.g., Red 50 background with Red 700 text) for a refined look.
- **AI-Insight Callouts:** Featured in a special container with a left-accent border in Cyan and a small "Sparkle" icon to denote algorithmic intelligence.
- **Interactive Charts:** Bar and line charts use a palette of Primary Navy, Secondary Slate, and Tertiary Cyan. Hover states show high-contrast tooltips with white text on a Navy background.