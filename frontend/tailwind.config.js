module.exports = {
  content: [
    "../**/templates/**/*.html",
    "../home/templates/**/*.html",
    "../mvp_smart_accounting/templates/**/*.html",
    "../mvp_qflow_core/templates/**/*.html",
    "./**/forms.py",
  ],
  safelist: [
    'peer',
    'sr-only',
    'peer-checked:border-emerald-500',
    'peer-checked:bg-emerald-50/30',
    'focus:ring-emerald-500',
    'focus:border-emerald-700',
    'focus:ring-emerald-500/20',
    // Agrega aquí cualquier clase dinámica que uses en el widget
  ],
  theme: {
    extend: {
      fontFamily: {
        // Cuerpo, botones, navegación y etiquetas
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica",
          "Arial",
          "Noto Sans",
          "sans-serif",
        ],
        // Encabezados principales
        display: [
          "Inter Tight",
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "sans-serif",
        ],
      },
      fontSize: {
        // Large headings
        h1: ["3rem",   { lineHeight: "1.1",  letterSpacing: "-0.02em" }], // 48px
        h2: ["2.25rem",{ lineHeight: "1.15", letterSpacing: "-0.02em" }], // 36px
        h3: ["1.75rem",{ lineHeight: "1.2",  letterSpacing: "-0.015em" }], // 28px
        h4: ["1.375rem",{ lineHeight: "1.3", letterSpacing: "-0.01em" }], // 22px
        h5: ["1.125rem",{ lineHeight: "1.4", letterSpacing: "-0.005em" }], // 18px
        h6: ["1rem",   { lineHeight: "1.5",  letterSpacing: "0em" }], // 16px
        // Supporting text sizes
        lead: ["1.125rem", { lineHeight: "1.7" }], // 18px
        body: ["1rem", { lineHeight: "1.65" }],    // 16px
        small: ["0.875rem", { lineHeight: "1.6" }], // 14px
      },      
      keyframes: {
        "fade-in-blur": {
          "0%": {
            opacity: "0",
            transform: "translateY(-8px)",
            filter: "blur(10px)",
          },
          "100%": {
            opacity: "1",
            transform: "translateY(0)",
            filter: "blur(0px)",
          },
        },
      },
      animation: {
        "fade-in-blur": "fade-in-blur 600ms ease-out both",
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
};

