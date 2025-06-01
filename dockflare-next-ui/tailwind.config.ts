// tailwind.config.ts
import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'holo-cyan': '#00E0FF', // Example holographic cyan
        'holo-magenta': '#FF00E0', // Example holographic magenta
        'dark-bg': '#0F172A', // slate-900
        'panel-bg': 'rgba(30, 41, 59, 0.5)', // slate-800 with opacity
      },
      boxShadow: {
        'holo-glow-cyan': '0 0 15px 5px rgba(0, 224, 255, 0.3), 0 0 5px 1px rgba(0, 224, 255, 0.2)',
        'holo-glow-magenta': '0 0 15px 5px rgba(255, 0, 224, 0.3), 0 0 5px 1px rgba(255, 0, 224, 0.2)',
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-conic':
          'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
      },
      
    },
  },
  plugins: [require('daisyui')], 
  daisyui: { 
    themes: ["dark"], 
  },
}
export default config