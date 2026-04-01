import forms from '@tailwindcss/forms'
import typography from '@tailwindcss/typography'

/**
 * Design Token System
 * -------------------
 * Semantic color names reference CSS custom properties defined in index.css.
 * This means every token automatically adapts to dark mode — no `dark:` variant needed.
 *
 * Usage:
 *   bg-background    → page background
 *   bg-surface       → card / panel background
 *   bg-surface-raised→ elevated surface (dropdowns, popovers)
 *   bg-inset         → subtle indented areas (table headers, code blocks)
 *   bg-muted         → hover states, tags
 *
 *   text-foreground  → primary body text
 *   text-muted       → secondary / supporting text
 *   text-subtle      → placeholder, timestamps, tertiary
 *
 *   border-border    → default border
 *   border-strong    → stronger border for emphasis
 *
 *   bg-accent        → indigo-500 primary action
 *   text-accent      → indigo-500 text links
 *   bg-accent-subtle → light indigo tint for hover/selected states
 *
 *   bg-success-subtle / text-success
 *   bg-warning-subtle / text-warning
 *   bg-error-subtle  / text-error
 */

export default {
  darkMode: 'class',
  content: [
    './index.html',
    './src/**/*.{js,jsx,ts,tsx}',
  ],
  theme: {
    container: { center: true, padding: '1rem' },
    extend: {
      colors: {
        // ── Semantic surface tokens ───────────────────────────────────────
        background:      'hsl(var(--background))',
        foreground:      'hsl(var(--foreground))',

        surface: {
          DEFAULT:  'hsl(var(--surface))',
          raised:   'hsl(var(--surface-raised))',
        },
        inset:           'hsl(var(--inset))',
        muted: {
          DEFAULT:  'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        subtle:          'hsl(var(--subtle))',

        // ── Border tokens ─────────────────────────────────────────────────
        border: {
          DEFAULT: 'hsl(var(--border))',
          strong:  'hsl(var(--border-strong))',
        },

        // ── Accent (primary action) ───────────────────────────────────────
        accent: {
          DEFAULT:  'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
          subtle:   'hsl(var(--accent-subtle))',
          hover:    'hsl(var(--accent-hover))',
        },

        // ── Status tokens ─────────────────────────────────────────────────
        success: {
          DEFAULT: 'hsl(var(--success))',
          subtle:  'hsl(var(--success-subtle))',
        },
        warning: {
          DEFAULT: 'hsl(var(--warning))',
          subtle:  'hsl(var(--warning-subtle))',
        },
        error: {
          DEFAULT: 'hsl(var(--error))',
          subtle:  'hsl(var(--error-subtle))',
        },

        // ── Keep legacy zinc/indigo for existing components ───────────────
        primary: {
          DEFAULT: '#0f172a',
          light:   '#1e293b',
          dark:    '#020617',
        },
      },

      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui'],
      },

      borderRadius: {
        DEFAULT: '2px',
        sm:      '2px',
        md:      '4px',
        lg:      '6px',
        xl:      '8px',
        '2xl':   '12px',
        full:    '9999px',
      },

      fontSize: {
        '2xs': ['0.65rem', { lineHeight: '1rem' }],
      },
    },
  },
  plugins: [forms, typography],
}
