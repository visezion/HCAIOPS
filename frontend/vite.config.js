import { defineConfig } from 'vite';
import { viteStaticCopy } from 'vite-plugin-static-copy';

// Copy unbundled HTML partials so runtime fetches work in the production build
export default defineConfig({
  plugins: [
    viteStaticCopy({
      targets: [
        {
          src: 'src/components/**/*',
          dest: 'src/components',
        },
      ],
    }),
  ],
});
