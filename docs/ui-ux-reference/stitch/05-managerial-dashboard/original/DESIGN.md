---
name: Academic Civic Trust
colors:
  surface: '#f8f9ff'
  surface-dim: '#d0dbed'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e6eeff'
  surface-container-high: '#dee9fc'
  surface-container-highest: '#d9e3f6'
  on-surface: '#121c2a'
  on-surface-variant: '#43474f'
  inverse-surface: '#27313f'
  inverse-on-surface: '#eaf1ff'
  outline: '#747781'
  outline-variant: '#c4c6d1'
  surface-tint: '#3e5e95'
  primary: '#002048'
  on-primary: '#ffffff'
  primary-container: '#0c356a'
  on-primary-container: '#7f9fdb'
  inverse-primary: '#abc7ff'
  secondary: '#795900'
  on-secondary: '#ffffff'
  secondary-container: '#fec335'
  on-secondary-container: '#6f5100'
  tertiary: '#002339'
  on-tertiary: '#ffffff'
  tertiary-container: '#00395a'
  on-tertiary-container: '#45a6eb'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d7e3ff'
  primary-fixed-dim: '#abc7ff'
  on-primary-fixed: '#001b3f'
  on-primary-fixed-variant: '#23467c'
  secondary-fixed: '#ffdea0'
  secondary-fixed-dim: '#f8bd2f'
  on-secondary-fixed: '#261a00'
  on-secondary-fixed-variant: '#5c4300'
  tertiary-fixed: '#cce5ff'
  tertiary-fixed-dim: '#93ccff'
  on-tertiary-fixed: '#001d31'
  on-tertiary-fixed-variant: '#004b73'
  background: '#f8f9ff'
  on-background: '#121c2a'
  surface-variant: '#d9e3f6'
typography:
  headline-xl:
    fontFamily: Public Sans
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.02em
  headline-xl-mobile:
    fontFamily: Public Sans
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 36px
    letterSpacing: -0.01em
  headline-lg:
    fontFamily: Public Sans
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 36px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Public Sans
    fontSize: 22px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: 0em
  headline-md:
    fontFamily: Public Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.005em
  headline-sm:
    fontFamily: Public Sans
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: 0em
  body-lg:
    fontFamily: Public Sans
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Public Sans
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Public Sans
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
  label-lg:
    fontFamily: Public Sans
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-md:
    fontFamily: Public Sans
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Public Sans
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.03em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-sm: 1rem
  margin: 2rem
  margin-sm: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style

This design system establishes an authoritative, reliable, and accessible digital portal tailored for campus facility incident and service requests. The visual atmosphere balances collegiate gravitas with civic transparency, ensuring students, faculty, and administrative staff feel heard, reassured, and guided through bureaucratic touchpoints.

### Personality & Demeanor
- **Institutional & Trustworthy:** Anchored by deep collegiate navy, evoking institutional heritage and accountability.
- **Approachable & Efficient:** Clear typographic signals and structured workflows eliminate friction when filing urgent infrastructural issues (e.g., broken AV equipment, laboratory hazards, facility repairs).
- **Pragmatic & Accessible:** Strict adherence to high-contrast legibility (WCAG AA/AAA compliance) across daylight and dim campus environments, avoiding trendy visual noise such as heavy blur matrices, neo-brutalist harshness, or unnecessary micro-animations.

### Visual Aesthetic
The interface applies a refined **Corporate / Modern Civic** model. Forms, dashboards, and feeds rely on crisp container boundaries, subtle border definitions, and disciplined whitespace to project operational efficiency.

## Colors

The palette directly reflects academic heritage and civic transparency, centered around deep navy and warm gold accentuation.

### Core Application Roles
- **Primary Navy (`#0C356A`):** The foundational anchor. Reserved for primary calls-to-action, structural navigation headers, major brand landmarks, and focused boundary highlights.
- **Accent Gold (`#FFC436`):** Dedicated to attention-directing status indicators, verified category highlights, progress alerts, and active badge counters. Never used for long-form body text due to contrast thresholds; reserved for decorative trims, badges with high-contrast text, and key priority flags.
- **Tertiary Information (`#0284C7`):** Complementary sky-blue tone applied to interactive link structures, informational alert banners, and neutral system metadata.
- **Surface & Canvas:**
  - Base Background: `#F6F8FA` provides an eye-resting, cool-neutral backdrop that elevates cards without stark glare.
  - Surface Pure: `#FFFFFF` for primary cards, modals, table rows, and form containment surfaces.
  - Surface Subtle: `#F1F4F9` for table headers, inactive card footers, and secondary metadata containers.
- **Text & Hierarchy:**
  - Primary Text: `#1F2937` (Slate 800) for headers and core legible text (exceeding WCAG AAA contrast against white).
  - Secondary Text: `#4B5563` (Slate 600) for timestamps, metadata, descriptive helper labels, and placeholder states.
- **Borders & Dividers:**
  - Primary Structural Border: `#E5E7EB` for card perimeters, dividers, and table cell separators.
  - Input Inactive Border: `#D1D5DB` for neutral, accessible form bounding boxes.
- **Status & Feedback Accents:**
  - Success / Resolved: `#059669` (surface fill `#ECFDF5`)
  - In Progress / Review: `#D97706` (surface fill `#FFFBEB`)
  - Urgent / Blocked: `#DC2626` (surface fill `#FEF2F2`)

## Typography

The type scale utilizes **Public Sans**, an institutional, open-source grotesque designed specifically for accessible public administration interfaces, with fallbacks to system staples (`Segoe UI`, `-apple-system`, `sans-serif`).

### Guidelines & Hierarchical Use
- **Headlines:** Use `headline-xl` solely for landing hero titles and public portal statistics summaries. In dashboard layouts, top-level screen containers lead with `headline-lg`.
- **Form Labels & Table Headings:** Use `label-lg` for interactive field indicators to preserve visual distinction over input values. All sub-text and instructional guides must default to `body-sm` in Secondary Text (`#4B5563`).
- **Ticket / Complaint IDs:** Ticket identifiers (e.g., `#FTII-2024-089`) must render in `label-md` with `font-feature-settings: 'tnum'` enabled for tabular alignment across listings.
- **Editorial Balance:** Maintain tight line-height ratios on headlines for high visual impact while granting body typography comfortable breathing room (`line-height: 1.5` to `1.6`) for reading comprehensive report descriptions.

## Layout & Spacing

The layout is built upon a standard 12-column responsive fluid grid, harmonizing directly with standard enterprise and modern institutional front-end frameworks.

### Breakpoints & Container Boundaries
- **Mobile (< 768px):** 4-column layout, canvas margins set to `margin-sm` (`1rem`), and component gutters set to `gutter-sm` (`1rem`). Full-width fluid card stacks.
- **Tablet (768px – 1024px):** 8-column layout, canvas margins set to `margin` (`2rem`), gutters set to `gutter` (`1.5rem`). Two-column forms and split report listings.
- **Desktop (1024px+):** 12-column structure with fixed max-width containers (`1200px` for standard operational portals, `1440px` for dense technician dispatch boards), flanked by auto-centering canvas margins.

### Vertical Spacing & Rhythm
- Inter-field gaps within complaint entry forms strictly observe `space-lg` (`1.5rem`).
- Micro-grouping between input labels, helper text, and bounding inputs uses `space-xs` (`0.25rem`) and `space-sm` (`0.5rem`).
- Module-to-module layout blocks (e.g., hero overview to active queue filter) separate using `space-xl` (`2.5rem`).

## Elevation & Depth

To preserve an authentic institutional tone, the system eschews heavy drop-shadows and frosted glass blurs in favor of **low-contrast perimeter lines accompanied by shallow, restrained ambient resting shadows**.

### Elevation Scale
- **Flat / Ground (`elevation-0`):** Applied to the main application background (`#F6F8FA`) and inset input fields. Border is absent or defined purely by layout boundaries.
- **Card Resting (`elevation-1`):** Applied to operational cards, table containers, and filter rows. Uses a crisp border (`1px solid #E5E7EB`) backed by a delicate ambient shadow:
  `box-shadow: 0 1px 3px 0 rgba(15, 23, 42, 0.05), 0 1px 2px -1px rgba(15, 23, 42, 0.05);`
- **Interactive Hover / Card Focus (`elevation-2`):** Applied to hovered complaint cards, active dropdown menus, and raised status selectors:
  `box-shadow: 0 4px 6px -1px rgba(12, 53, 106, 0.08), 0 2px 4px -2px rgba(12, 53, 106, 0.06);`
  The shadow carries a faint Navy tint (`rgba(12, 53, 106, ...)`) to reinforce the brand identity subtly in space.
- **Overlays & Modals (`elevation-3`):** Applied to ticket submission dialogs, image inspection lightboxes, and sliding navigation drawers:
  `box-shadow: 0 20px 25px -5px rgba(15, 23, 42, 0.12), 0 8px 10px -6px rgba(15, 23, 42, 0.08);`
  Always paired with an accessible dark scrim: `background: rgba(15, 23, 42, 0.45)` with `backdrop-filter: blur(2px)`.

## Shapes

The design uses **Soft (Level 1)** geometry. Formality and precision require structure; rounding is gentle and restrained, steering clear of juvenile or overly casual full-pill shapes except where strictly denoting numeric status chips.

### Geometry Specifications
- **Controls & Form Elements:** Standard buttons, text inputs, textareas, and select menus maintain a crisp corner radius of `0.25rem` (4px).
- **Cards & Data Surfaces:** Report cards, data panels, and modal containers scale to `rounded-lg` (`0.5rem` / 8px).
- **Accent Top Borders:** Key actionable summary cards and portal feature modules leverage an architectural `3px` solid top border in Primary Navy (`#0C356A`) or Accent Gold (`#FFC436`), anchored flush across the top corners.
- **Status Tags & Badges:** Feature a controlled radius of `0.25rem` (4px) for category tags or full circular pill geometry exclusively for compact numeric counter badges.

## Components

### Buttons
- **Primary Action (e.g., "Kirim Laporan"):** Solid Primary Navy (`#0C356A`) background, white text (`#FFFFFF`), `font-weight: 600`, minimum touch height `44px`. Focus state triggers an offset outline ring (`3px solid rgba(12, 53, 106, 0.25)`). Active/press state darkens to `#082245`.
- **Secondary Action:** White background with a `1px solid #D1D5DB` border, `#1F2937` text. Hover transitions to `#F1F4F9` with `#0C356A` border.
- **Accent Utility (e.g., Quick Pin, Priority):** Solid Accent Gold (`#FFC436`) with dark slate text (`#1F2937`) to guarantee WCAG compliance. Never use white text over the accent gold background.

### Form Inputs & Textareas
- **Resting:** `1px solid #D1D5DB`, `#FFFFFF` surface, `#1F2937` typography, `border-radius: 4px`, vertical padding `10px`, horizontal padding `14px`.
- **Focused State:** Explicit border change to `#0C356A` accompanied by an institutional outer focus ring: `box-shadow: 0 0 0 3px rgba(12, 53, 106, 0.15)`.
- **Validation State (Error):** Border `#DC2626` with red focus glow `rgba(220, 38, 38, 0.15)`. Inline error messages render beneath the field in `label-sm` with a contextual warning icon.

### Cards & Ticket Modules
- **Facility Ticket Card:** Pure white background, `1px solid #E5E7EB`, `elevation-1`, `border-radius: 8px`.
- **Status Accent Stripe:** High-priority or emergency reports incorporate a `3px` Accent Gold (`#FFC436`) or Amber status bar along the top edge of the card.
- **Card Header & Meta:** Top row houses the unique ticket ID (`label-md`, `#4B5563`), time elapsed, and categorical badge. The title uses `headline-sm` (`#1F2937`), followed by a constrained 2-line snippet in `body-sm`.

### Status Badges & Chips
- Compact badges display report milestones without visual disruption:
  - *Diajukan (Submitted):* `#F1F4F9` background, `#4B5563` text, `#E5E7EB` border.
  - *Diproses (In Progress):* `#FFFBEB` background, `#B45309` text, `#FDE68A` border.
  - *Selesai (Resolved):* `#ECFDF5` background, `#047857` text, `#A7F3D0` border.
  - *Ditolak / Dibatalkan (Rejected):* `#FEF2F2` background, `#B91C1C` text, `#FECACA` border.

### Checkboxes & Radio Controls
- Square (`checkbox`) and circular (`radio`) controls sized at `18px × 18px`.
- Unchecked: `#FFFFFF` fill with `1.5px solid #D1D5DB`.
- Checked: `#0C356A` fill featuring a crisp white tick or inner pip. Focus ring retains the standard navy translucent halo.

### Media Upload / Evidence Dropzone
- Dedicated component for attaching photographic evidence of damaged facilities.
- Dashed perimeter (`2px dashed #D1D5DB`), `#F6F8FA` resting fill. Transitions to `#F1F4F9` with `#0C356A` border upon file hover/dragover.
- Thumbnail previews include a compact floating delete badge and upload progress bar striped in Primary Navy.