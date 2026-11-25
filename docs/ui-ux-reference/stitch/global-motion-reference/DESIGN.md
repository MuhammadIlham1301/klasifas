---
name: Academic Hybrid Command
colors:
  surface: '#f8f9ff'
  surface-dim: '#ccdbf3'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dbe7ff'
  surface-container-highest: '#d0e0ff'
  on-surface: '#0f172a'
  on-surface-variant: '#475569'
  inverse-surface: '#233144'
  inverse-on-surface: '#eaf1ff'
  outline: '#cbd5e1'
  outline-variant: '#e2e8f0'
  surface-tint: '#3755c3'
  primary: '#00288e'
  on-primary: '#ffffff'
  primary-container: '#dbeafe'
  on-primary-container: '#1e3a8a'
  inverse-primary: '#b8c4ff'
  secondary: '#565e74'
  on-secondary: '#ffffff'
  secondary-container: '#1e293b'
  on-secondary-container: '#cbd5e1'
  tertiary: '#003757'
  on-tertiary: '#ffffff'
  tertiary-container: '#e0f2fe'
  on-tertiary-container: '#0369a1'
  error: '#b91c1c'
  on-error: '#ffffff'
  error-container: '#fee2e2'
  on-error-container: '#7f1d1d'
  primary-fixed: '#dde1ff'
  primary-fixed-dim: '#b8c4ff'
  on-primary-fixed: '#001453'
  on-primary-fixed-variant: '#173bab'
  secondary-fixed: '#dae2fd'
  secondary-fixed-dim: '#bec6e0'
  on-secondary-fixed: '#131b2e'
  on-secondary-fixed-variant: '#3f465c'
  tertiary-fixed: '#cce5ff'
  tertiary-fixed-dim: '#93ccff'
  on-tertiary-fixed: '#001d31'
  on-tertiary-fixed-variant: '#004b73'
  background: '#f8f9ff'
  on-background: '#0d1c2e'
  surface-variant: '#d5e3fc'
typography:
  display-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
  display-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 36px
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 26px
  headline-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  title-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 22px
  body-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 21px
  body-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  label-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 17px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 15px
    letterSpacing: 0.03em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-mobile: 0.75rem
  margin: 1.5rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
---

---
name: Academic Hybrid Command
theme:
  color_mode: LIGHT
  font: PLUS_JAKARTA_SANS
  roundness: ROUND_EIGHT
  custom_color: '#1e40af'
colors:
  surface: '#f8f9ff'
  surface-dim: '#ccdbf3'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dbe7ff'
  surface-container-highest: '#d0e0ff'
  on-surface: '#0f172a'
  on-surface-variant: '#475569'
  outline: '#cbd5e1'
  outline-variant: '#e2e8f0'
  primary: '#1e40af'
  primary-container: '#dbeafe'
  on-primary: '#ffffff'
  on-primary-container: '#1e3a8a'
  secondary: '#0f172a'
  secondary-container: '#1e293b'
  on-secondary: '#ffffff'
  on-secondary-container: '#cbd5e1'
  tertiary: '#0284c7'
  tertiary-container: '#e0f2fe'
  on-tertiary: '#ffffff'
  on-tertiary-container: '#0369a1'
  error: '#b91c1c'
  error-container: '#fee2e2'
  on-error: '#ffffff'
  on-error-container: '#7f1d1d'
typography:
  font-family: 'Plus Jakarta Sans', sans-serif
  display:
    size: 2rem
    weight: 700
    line-height: 1.25
  heading:
    size: 1.25rem
    weight: 600
    line-height: 1.3
  body:
    size: 0.875rem
    weight: 400
    line-height: 1.5
  label:
    size: 0.75rem
    weight: 600
    line-height: 1.4
layout:
  desktop_sidebar_width: 250px
  desktop_sidebar_collapsed_width: 72px
  max_content_width: 1440px
brandlock:
  institution_logo: official UHAMKA logo only (single institutional logo, logo-uhamka.png)
  app_name: KlasiFas
  app_subtitle: FTII UHAMKA
motion_and_interaction:
  timing_tokens:
    fast: 100ms - 150ms (micro-interactions, button hover/active, focus rings, status badges)
    normal: 200ms - 250ms (dropdowns, accordions, modal scale-in, tab switches)
    moderate: 300ms - 350ms (desktop sidebar 250px <-> 72px, mobile drawer 300ms, toasts)
    deliberate: 400ms - 600ms (KPI count-up reveals, chart entrance, staggered lists)
  easing_curves:
    ease-standard: cubic-bezier(0.2, 0.0, 0, 1.0)
    ease-decelerate: cubic-bezier(0.0, 0.0, 0.2, 1.0)
    ease-accelerate: cubic-bezier(0.4, 0.0, 1.0, 1.0)
    ease-sharp: cubic-bezier(0.4, 0.0, 0.6, 1.0)
  accessibility_prefers_reduced_motion:
    policy: All non-essential animations, transforms, and spatial transitions are disabled when prefers-reduced-motion is active.
    fallback: Instant opacity fade (80ms) replaces spatial movement (transform: none !important). Layout transitions collapse instantly.
  mobile_interaction_pattern:
    policy: No globally mandated bottom-pinned action sheet. Actions are defined contextually per role and workflow.
    roles:
      pimpinan: Contextual modal / analytics filter drawer.
      admin_sarpras: Inline queue actions, quick triage disposition modal.
      teknisi: Field-ready action bar / camera upload panel.
      pelapor: Progressive stepper form submit action.
  ticket_workflow_statuses:
    statuses:
      - Baru
      - Terverifikasi
      - Diproses
      - Selesai
    note: Technician assignment and physical repairs are workflow actions within statuses, not additional status states.
---
# KlasiFas FTII UHAMKA - Master Design System & Motion Specification
Academic Hybrid Command System for Gedung FTII UHAMKA (Floors 1-4).
