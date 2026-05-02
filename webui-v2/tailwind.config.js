/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#00D9A6',
          hover: '#00B88C',
          dark: '#009975',
        },
        bg: {
          main: '#0F1117',
          card: '#1A1D26',
          hover: '#242830',
        },
        text: {
          primary: '#E8EAED',
          secondary: '#9AA0A6',
          muted: '#5F6368',
        },
        success: '#34A853',
        error: '#EA4335',
        info: '#4285F4',
        warning: '#FBBC04',
      },
    },
  },
  plugins: [],
  corePlugins: {
    preflight: false, // avoid conflicts with antd
  },
};
