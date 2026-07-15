/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js}'],
  // 玄策为深色优先；Tailwind 仅作排版/布局工具，颜色一律用 var(--xc-*)。
  corePlugins: {
    preflight: false, // 避免与 Element Plus / 玄策基线冲突
  },
  theme: {
    extend: {},
  },
  plugins: [],
}
