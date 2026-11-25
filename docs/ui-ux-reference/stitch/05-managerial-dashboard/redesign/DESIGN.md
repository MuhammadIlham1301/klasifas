---
name: Academic Hybrid Command
colors:
  surface: '#f8f9ff'
  surface-dim: '#ccdbf3'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e6eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d5e3fc'
  on-surface: '#0d1c2e'
  on-surface-variant: '#444653'
  inverse-surface: '#233144'
  inverse-on-surface: '#eaf1ff'
  outline: '#757684'
  outline-variant: '#c4c5d5'
  surface-tint: '#3755c3'
  primary: '#00288e'
  on-primary: '#ffffff'
  primary-container: '#1e40af'
  on-primary-container: '#a8b8ff'
  inverse-primary: '#b8c4ff'
  secondary: '#904d00'
  on-secondary: '#ffffff'
  secondary-container: '#fe932c'
  on-secondary-container: '#663500'
  tertiary: '#28354a'
  on-tertiary: '#ffffff'
  tertiary-container: '#3f4c61'
  on-tertiary-container: '#afbcd6'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dde1ff'
  primary-fixed-dim: '#b8c4ff'
  on-primary-fixed: '#001453'
  on-primary-fixed-variant: '#173bab'
  secondary-fixed: '#ffdcc3'
  secondary-fixed-dim: '#ffb77d'
  on-secondary-fixed: '#2f1500'
  on-secondary-fixed-variant: '#6e3900'
  tertiary-fixed: '#d6e3fe'
  tertiary-fixed-dim: '#bac7e1'
  on-tertiary-fixed: '#0e1c2f'
  on-tertiary-fixed-variant: '#3a475c'
  background: '#f8f9ff'
  on-background: '#0d1c2e'
  surface-variant: '#d5e3fc'
typography:
  display-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 48px
    letterSpacing: -0.02em
  display-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.005em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 26px
    letterSpacing: 0em
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
    letterSpacing: 0em
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0.005em
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.05em
  metric-num:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.03em
  headline-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.01em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1.25rem
  gutter-lg: 1.5rem
  margin: 1.5rem
  margin-lg: 2rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
---

## Brand & Style

The design system establishes a high-performance, authoritative, and contemporary academic command environment tailored for FTII UHAMKA (Fakultas Teknologi Industri dan Informatika). It bridges institutional heritage with cutting-edge engineering precision.

### Personality & Tone
- **Institutional Authority:** Grounded in collegiate trust, intellectual rigor, and institutional transparency.
- **Engineering Precision:** Technical clarity, dense yet legible information architecture, high-fidelity metric displays, and zero unnecessary decorative clutter.
- **Responsive & Action-Oriented:** The UI instills confidence among students, faculty, and facility managers through instant status legibility and proactive workflow cues.

### Aesthetic Movement: Modern Hybrid Canvas
The interface uses a deliberate hybrid architectural model:
1. **The Navigation Shell (Dark Chrome):** A deep academic navy (`#0B192C`) structural frame housing navigation, system indicators, and brand crests. It offers a focused, quiet anchor that reduces peripheral distraction.
2. **The Workspace Canvas (Crisp Light Surface):** An ultra-clean, high-legibility workspace composed of crisp slate-tinted surfaces (`#F8FAFC` through `#FFFFFF`), precision 1px borders, razor-sharp tabular data, and subtle low-diffusion elevations.
3. **Institutional Accents:** Direct alignment with UHAMKA heraldic iconography—deep royal cobalt blue and luminous solar amber/gold—used selectively to guide interaction focus and signal critical status transitions.

## Colors

The color architecture is built around functional hierarchy, institutional recognition, and standardized complaint processing states.

### Core Foundation
- **Primary (UHAMKA Royal Blue - `#1E40AF`):** Primary interactive elements, active navigation highlights, verified states, and primary CTAs. Hover variant: `#1D4ED8`. Active variant: `#1E3A8A`.
- **Secondary (Solar Amber / Gold - `#D97706`):** Urgent operational notices, spotlight cards, pending alert accents, and active review indicators. Derived from the central sunburst in the official seals.
- **Tertiary / Shell Slate (`#0B192C`):** Applied exclusively to the left-hand navigation console, top utility bar accents, and executive metric containers.
- **Neutral Ground (`#475569`):** Controlled grayscale supporting text hierarchy, fine sub-pixel borders (`#E2E8F0`), and page backdrops (`#F8FAFC`).

### Workflow Status Taxonomy
The complaint monitoring lifecycle requires strict, immutable color pairings:
- **Baru (New Intake):** Amber state. Subtle tinted container (`#FEF3C7`), solid border (`#FDE68A`), high-contrast text (`#B45309`). Signals immediate triage need.
- **Terverifikasi (Verified):** Royal Blue state. Tinted container (`#EFF6FF`), solid border (`#BFDBFE`), high-contrast text (`#1D4ED8`). Confirms administrative audit.
- **Diproses (In Progress):** Indigo/Violet state. Tinted container (`#EEF2FF`), solid border (`#C7D2FE`), high-contrast text (`#4338CA`). Denotes technical crew deployment.
- **Selesai (Resolved):** Emerald state. Tinted container (`#ECFDF5`), solid border (`#A7F3D0`), high-contrast text (`#047857`). Confirms ticket closure and verification.

### Application Rules
- Never use saturated fills for status containers; always use 50-level tints with matching 200-level borders and 700/800-level text to maintain visual calm.
- Restrict pure dark navy `#0B192C` to the operational shell to maintain clarity between system controls and document canvas.

## Typography

The typographic hierarchy coordinates expressive modern geometry (`Plus Jakarta Sans`) for structural headings and institutional markers with an engineered neutral workhorse (`Inter`) for dense data grids and tickets.

### Typographic Roles
- **Headings & Metric Numbers:** `Plus Jakarta Sans` provides sharp, authoritative clarity with tightened letterforms (`letter-spacing: -0.02em`) that reflect modern tech platforms.
- **Body & Data Tables:** `Inter` ensures optical balance at small sizes (13px–14px). All numerical metric readouts and ticket IDs must utilize tabular figures (`font-feature-settings: "tnum" 1, "cv05" 1`).
- **Metadata Badges & Micro-Labels:** Set in uppercase, tracked (`letter-spacing: 0.05em`), semi-bold 11px font to provide visual grouping without shouting.

## Layout & Spacing

The system implements a rigid 8pt baseline spacing rhythm paired with a dual-pane hybrid application layout.

### Structural Framework
- **Shell Layout:** Left desktop sidebar fixed at `260px` width. Collapsible to `72px` icon rail on sub-desktop viewpoints.
- **Workspace Grid:** A 12-column responsive fluid grid across the content canvas.
  - **Desktop (>= 1280px):** 12 columns, `1.5rem` (`24px`) gutters, `2rem` (`32px`) canvas margin.
  - **Tablet (768px - 1279px):** 8 columns, `1.25rem` (`20px`) gutters, `1.5rem` (`24px`) canvas margin. Sidebar collapses to drawer or icon mode.
  - **Mobile (< 768px):** 4 columns, `1rem` (`16px`) gutters, `1rem` (`16px`) canvas margin. Bottom pinned action sheet for rapid triage.

### Spatial Densities
- Card inner padding strictly adheres to `space-lg` (`24px`) on desktop and `space-md` (`16px`) on mobile viewports.
- List items and interactive table rows use vertical padding of `space-sm` (`8px`) or `space-md` (`12px` to `16px`) to ensure touch targets never dip below `44px`.

## Elevation & Depth

Visual hierarchy is communicated through subtle layer separation, hairline borders, and targeted ambient lighting rather than heavy drop shadows.

### Elevation Levels
- **Level 0 (App Canvas):** Base tinted background (`#F8FAFC`). Flat surface.
- **Level 1 (Card & Module Layer):** Pure white surface (`#FFFFFF`) with 1px structural outline in `rgba(226, 232, 240, 0.9)` and ambient micro-shadow: `0 1px 3px 0 rgba(15, 23, 42, 0.04), 0 1px 2px -1px rgba(15, 23, 42, 0.03)`.
- **Level 2 (Interactive Floating Elements):** Dropdown menus, popovers, active cards on hover: `0 4px 6px -1px rgba(15, 23, 42, 0.07), 0 2px 4px -2px rgba(15, 23, 42, 0.05)`, border color shifted to `#CBD5E1`.
- **Level 3 (Modals & Overlays):** Deep ambient diffusion `0 20px 25px -5px rgba(11, 25, 44, 0.12), 0 8px 10px -6px rgba(11, 25, 44, 0.08)` layered above an active blurred backdrop (`backdrop-filter: blur(4px)` with background `rgba(11, 25, 44, 0.65)`).
- **Glassmorphic Top Header:** Sticky horizontal canvas header uses `rgba(255, 255, 255, 0.85)` with `backdrop-filter: blur(12px)` and a bottom border in `rgba(226, 232, 240, 0.8)`.

## Shapes

The design system enforces a disciplined geometric standard: **Roundedness Level 2**.

### Radius Calibration
- **Default (0.5rem / 8px):** Standard inputs, filter buttons, regular cards, data badges, and status pills.
- **Large (1rem / 16px):** Modal dialogs, prominent stat KPI containers, and media attachment modules.
- **Extra-Large (1.5rem / 24px):** Slide-out drawer corners and prominent onboarding hero modules.
- **Pill (9999px):** Pure circular iconography wrappers, user avatars, and primary numerical counter indicators.

No sharp (0px) shapes are permitted. Rounded edges balance technical precision with modern, approachable usability.

## Components

### Buttons
- **Primary:** Solid `#1E40AF` fill with pure white label, `8px` corner radius, font weight 600. Inner vertical padding `10px`, horizontal `18px`. Hover: `#1D4ED8` with subtle translate-y micro-shift (`-0.5px`).
- **Secondary:** Surface white `#FFFFFF` with 1px border `#CBD5E1` and text `#1E293B`. Hover: `#F8FAFC` background with border `#94A3B8`.
- **Tertiary / Ghost:** Transparent background with `#475569` text. Hover: `#F1F5F9` background and `#0F172A` text.
- **Accent (Action/Urgent):** Amber `#D97706` background with white text, utilized exclusively for priority escalation or triage trigger.

### Status Badge Pills
Structured with an 8px border-radius, `4px 10px` padding, 11px semi-bold uppercase text, and an inline `6px` status dot indicator:
- **Baru:** Amber pill (`bg-[#FEF3C7] text-[#B45309] border border-[#FDE68A]`). Status dot: `#D97706`.
- **Terverifikasi:** Blue pill (`bg-[#EFF6FF] text-[#1D4ED8] border border-[#BFDBFE]`). Status dot: `#2563EB`.
- **Diproses:** Indigo pill (`bg-[#EEF2FF] text-[#4338CA] border border-[#C7D2FE]`). Status dot: `#6366F1`.
- **Selesai:** Emerald pill (`bg-[#ECFDF5] text-[#047857] border border-[#A7F3D0]`). Status dot: `#10B981`.

### Data Cards & KPI Metrics
- Built with a white surface, `1px solid #E2E8F0`, and `16px` border-radius.
- Contains subtle top-edge color hints (e.g., a 2px blue or amber accent top line on critical KPI cards).
- Metric titles use `Inter` 12px uppercase tracked text (`#64748B`), and metric numbers display in `Plus Jakarta Sans` 28px/700 with tabular figures.
- Includes lightweight inline SVG sparklines with smooth gradient area fills (`#1E40AF` fading to transparent).

### Input Fields & Controls
- Form controls feature an off-white resting state (`#F8FAFC`), shifting to pure `#FFFFFF` on focus with a crisp `2px` ring in `rgba(30, 64, 175, 0.2)` and border `#1E40AF`.
- Placeholder text in `#94A3B8`.
- Checkboxes and radio buttons use `#1E40AF` for selected states with smooth transitions.

### Institutional Header & Crest Integration
- The dark navigation shell (`#0B192C`) integrates the circular UHAMKA and FTII UHAMKA seals inside a dedicated top brandlock:
  - Logos are rendered with high fidelity on a subtle inset dark tile (`#132238`), flanked by crisp white and gold institutional typography: "FTII UHAMKA" in bold Plus Jakarta Sans with "KlasiFas Campus Facility Suite" beneath in 11px slate-400.