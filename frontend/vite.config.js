import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

const backendPort = process.env.BACKEND_PORT || '8000';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		port: 5173,
		proxy: {
			'/ws': {
				target: `ws://localhost:${backendPort}`,
				ws: true
			},
			'/api': {
				target: `http://localhost:${backendPort}`
			}
		}
	}
});
