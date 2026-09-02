module.exports = {
  content: [
    "../**/templates/**/*.html",
    "../home/templates/**/*.html",
    "../mvp_smart_accounting/templates/**/*.html",
    "../mvp_qflow_core/templates/**/*.html",
    "../**/forms.py",
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
        // Encabezados
        h1: [
          "3rem",
          {
            lineHeight: "1.1",
            letterSpacing: "-0.02em",
          },
        ],

        h2: [
          "2.25rem",
          {
            lineHeight: "1.15",
            letterSpacing: "-0.02em",
          },
        ],

        h3: [
          "1.75rem",
          {
            lineHeight: "1.2",
            letterSpacing: "-0.015em",
          },
        ],

        h4: [
          "1.375rem",
          {
            lineHeight: "1.3",
            letterSpacing: "-0.01em",
          },
        ],

        h5: [
          "1.125rem",
          {
            lineHeight: "1.4",
            letterSpacing: "-0.005em",
          },
        ],

        h6: [
          "1rem",
          {
            lineHeight: "1.5",
            letterSpacing: "0",
          },
        ],

        // Textos complementarios
        lead: [
          "1.125rem",
          {
            lineHeight: "1.7",
          },
        ],

        body: [
          "1rem",
          {
            lineHeight: "1.65",
          },
        ],

        small: [
          "0.875rem",
          {
            lineHeight: "1.6",
          },
        ],
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
            filter: "blur(0)",
          },
        },

        "icon-float": {
          "0%, 100%": {
            transform: "translate3d(0, 0, 0) rotate(0deg)",
          },

          "50%": {
            transform: "translate3d(0, -8px, 0) rotate(1.5deg)",
          },
        },
      },

      animation: {
        "fade-in-blur": "fade-in-blur 600ms ease-out both",
        "icon-float": "icon-float 5.5s ease-in-out infinite",
      },
    },
  },

  plugins: [
    require("@tailwindcss/typography"),
  ],
};