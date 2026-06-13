import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
    plugins: [tailwindcss(), sveltekit()],
    resolve: {
        conditions: ['browser']
    },
    test: {
        globals: true,
        environment: 'jsdom',
        setupFiles: ['./vitest-setup.js'],
        deps: {
            inline: ['@testing-library/svelte', 'svelte']
        }
    }
});