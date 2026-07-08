---
name: Premium Wealth Portal
colors:
  surface: '#f7faf8'
  surface-dim: '#d7dbd9'
  surface-bright: '#f7faf8'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f1f4f3'
  surface-container: '#ebefed'
  surface-container-high: '#e5e9e7'
  surface-container-highest: '#e0e3e1'
  on-surface: '#181c1c'
  on-surface-variant: '#3e4947'
  inverse-surface: '#2d3130'
  inverse-on-surface: '#eef1f0'
  outline: '#6e7977'
  outline-variant: '#bdc9c6'
  surface-tint: '#006a63'
  primary: '#005c55'
  on-primary: '#ffffff'
  primary-container: '#0f766e'
  on-primary-container: '#a3faef'
  inverse-primary: '#80d5cb'
  secondary: '#466460'
  on-secondary: '#ffffff'
  secondary-container: '#c5e6e1'
  on-secondary-container: '#4a6864'
  tertiary: '#7f4025'
  on-tertiary: '#ffffff'
  tertiary-container: '#9c573a'
  on-tertiary-container: '#ffe5db'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#9cf2e8'
  primary-fixed-dim: '#80d5cb'
  on-primary-fixed: '#00201d'
  on-primary-fixed-variant: '#00504a'
  secondary-fixed: '#c8e9e4'
  secondary-fixed-dim: '#accdc8'
  on-secondary-fixed: '#00201d'
  on-secondary-fixed-variant: '#2e4c48'
  tertiary-fixed: '#ffdbce'
  tertiary-fixed-dim: '#ffb598'
  on-tertiary-fixed: '#370e00'
  on-tertiary-fixed-variant: '#72361b'
  background: '#f7faf8'
  on-background: '#181c1c'
  surface-variant: '#e0e3e1'
typography:
  h1:
    fontFamily: Manrope
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.02em
  h1-mobile:
    fontFamily: Manrope
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 34px
    letterSpacing: -0.02em
  h2:
    fontFamily: Manrope
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  h3:
    fontFamily: Manrope
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  number-display:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  label-caps:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  sidebar_width: 240px
  container_max_width: 1280px
  gutter: 24px
  margin_mobile: 16px
  margin_desktop: 32px
  stack_sm: 8px
  stack_md: 16px
  stack_lg: 24px
---

## Brand & Style
The design system is engineered for a premium fintech experience, evoking the calm, methodical atmosphere of a modern private banking portal. The brand personality is rooted in reliability and sophisticated simplicity, prioritizing clarity over decoration. 

The aesthetic is **Corporate Modern with a Minimalist touch**, utilizing generous whitespace and a "quiet" UI approach. Every element is designed to reduce cognitive load, allowing users to focus on long-term wealth management rather than market noise. The interface feels spacious, secure, and exclusive, catering to serious investors who value precision and discretion.

## Colors
The palette is dominated by a neutral, cool-toned foundation to maintain a high-end feel. 

- **Foundation:** A light grey-blue background (`#F5F7FA`) provides a soft canvas for pure white cards, creating a subtle layering effect without heavy shadows.
- **Accent:** The deep teal (`#0F766E`) serves as the anchor, used for primary actions, navigation indicators, and branding elements. It suggests stability and growth.
- **Functional:** Success and Error colors are standard but slightly desaturated to fit the "quiet" aesthetic.
- **Charts:** The chart palette uses distinct, high-contrast hues designed to remain legible on white surfaces, supporting complex multi-asset visualisations.

## Typography
This design system uses a dual-font strategy. **Manrope** is used for headlines to provide a modern, geometric, yet authoritative character. **Inter** is used for all body text and data points due to its exceptional legibility.

**Data Precision:** For all financial figures, Inter must be implemented with `tabular-nums` (tnum) enabled to ensure vertical alignment in tables and lists. Currency should follow the Indian format (e.g., ₹2,40,87,460), and larger values should be abbreviated to Lakh (L) or Crore (Cr) in dashboard views to maintain clean layouts.

## Layout & Spacing
The layout follows a **Fixed-Fluid hybrid grid**. 
- **Sidebar:** A fixed 240px white sidebar on the left contains the primary teal navigation.
- **Main Content:** A fluid area that centers content within a 1280px container.
- **Grid:** A 12-column system for desktop, 8-column for tablet, and 4-column for mobile.
- **Rhythm:** An 8px base grid drives all padding and margins. Vertical rhythm is strictly enforced with 16px, 24px, and 32px increments to maintain the "spacious" feel requested.
- **Member Switcher:** A prominent teal pill-style switcher (e.g., [All | PK | CK]) is located at the top level of the content or sidebar to allow quick context switching between family or entity portfolios.

## Elevation & Depth
Depth is created through **Tonal Layering** rather than intense shadows. 
- **Level 0 (Background):** `#F5F7FA` - The lowest surface.
- **Level 1 (Cards/Sidebar):** `#FFFFFF` - Primary containers with a very soft, subtle shadow (`0 1px 3px rgba(16,24,40,0.06)`) and a hairline border (`#E6E9F0`).
- **Interaction:** Hover states on cards should slightly deepen the shadow or add a subtle 1px border shift to primary teal, but the elevation should never feel "floating" far from the surface. 
- **Modals:** Use a heavy backdrop blur (12px) with a semi-transparent dark overlay to maintain the "private banking" focus during transactional tasks.

## Shapes
The shape language is refined and approachable.
- **Cards & Containers:** 12px corner radius (rounded-lg) to create a soft, premium container feel.
- **Buttons & Inputs:** 8px corner radius (base) for a more professional, precise appearance compared to the larger containers.
- **Navigation Pills:** Full-round (pill) shapes are used for the member switcher and status indicators (e.g., active/inactive chips).

## Components
- **Buttons:** Primary buttons use the Teal accent with white text. Ghost buttons use Teal text with no background. All buttons have 8px rounding and use Inter Medium for text.
- **Member Switcher:** A horizontal segmented control with a Teal background for the active state and light Teal (`#E6F4F1`) for the inactive track.
- **Input Fields:** 8px rounding, `#E6E9F0` border, and 16px horizontal padding. On focus, the border transitions to Teal with a 2px soft glow.
- **Cards:** White background, 12px rounding, subtle hairline border. Used for asset allocation, portfolio totals, and market news.
- **Data Tables:** Borderless rows with `#E6E9F0` horizontal dividers. Use "Body Small" for headers (all caps) and "Number Display" settings for financial values to ensure perfect alignment of decimals and currency symbols.
- **Portfolio Progress:** Use thin (4px) progress bars with the chart palette to indicate asset distribution within a card.