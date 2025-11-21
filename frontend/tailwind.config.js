const flowbitePlugin = require('flowbite/plugin');

module.exports = {
  content: [
    './index.html',
    './src/**/*.{html,js}',
    './node_modules/flowbite/**/*.js',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        display: ['"Space Grotesk"', 'Inter', 'system-ui', 'sans-serif'],
        body: ['"Inter"', 'system-ui', 'sans-serif'],
      },
      colors: {
        midnight: '#0b1224',
        azure: '#38bdf8',
        emeraldPulse: '#34d399',
        danger: '#f43f5e',
        panel: 'rgba(15, 23, 42, 0.75)',
      },
      boxShadow: {
        soft: '0 20px 60px rgba(0, 0, 0, 0.35)',
        glow: '0 10px 30px rgba(56, 189, 248, 0.3)',
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [flowbitePlugin],
};
