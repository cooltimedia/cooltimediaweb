module.exports = {
  content: [
    "../**/templates/**/*.html",
    "../home/templates/**/*.html",
  ],
  theme: {
    extend: {
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
  plugins: [],
};

