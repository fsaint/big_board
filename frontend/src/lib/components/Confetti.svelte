<script lang="ts">
	import { onMount } from 'svelte';

	export let particleCount = 100;
	export let duration = 5000;

	let canvas: HTMLCanvasElement;
	let ctx: CanvasRenderingContext2D | null;
	let particles: Particle[] = [];
	let animationId: number;
	let stopSpawning = false;

	interface Particle {
		x: number;
		y: number;
		vx: number;
		vy: number;
		color: string;
		size: number;
		rotation: number;
		rotationSpeed: number;
	}

	const colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#f9ca24', '#6c5ce7', '#a29bfe', '#fd79a8', '#00b894'];

	function createParticle(): Particle {
		return {
			x: Math.random() * canvas.width,
			y: -20,
			vx: (Math.random() - 0.5) * 8,
			vy: Math.random() * 3 + 2,
			color: colors[Math.floor(Math.random() * colors.length)],
			size: Math.random() * 10 + 5,
			rotation: Math.random() * 360,
			rotationSpeed: (Math.random() - 0.5) * 10
		};
	}

	function animate() {
		if (!ctx) return;

		ctx.clearRect(0, 0, canvas.width, canvas.height);

		particles.forEach((p, index) => {
			p.x += p.vx;
			p.y += p.vy;
			p.vy += 0.1; // gravity
			p.vx *= 0.99; // air resistance
			p.rotation += p.rotationSpeed;

			ctx!.save();
			ctx!.translate(p.x, p.y);
			ctx!.rotate((p.rotation * Math.PI) / 180);
			ctx!.fillStyle = p.color;
			ctx!.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 0.6);
			ctx!.restore();

			// Remove particles that fall off screen
			if (p.y > canvas.height + 50) {
				if (stopSpawning) {
					particles.splice(index, 1);
				} else {
					particles[index] = createParticle();
				}
			}
		});

		// Stop animation when all particles are gone
		if (stopSpawning && particles.length === 0) {
			ctx.clearRect(0, 0, canvas.width, canvas.height);
			return;
		}

		animationId = requestAnimationFrame(animate);
	}

	function handleResize() {
		if (canvas) {
			canvas.width = window.innerWidth;
			canvas.height = window.innerHeight;
		}
	}

	onMount(() => {
		ctx = canvas.getContext('2d');
		handleResize();

		// Create initial particles
		for (let i = 0; i < particleCount; i++) {
			const p = createParticle();
			p.y = Math.random() * canvas.height; // Spread initial particles
			particles.push(p);
		}

		animate();

		// Stop spawning new particles after duration
		const stopTimer = setTimeout(() => {
			stopSpawning = true;
		}, duration);

		window.addEventListener('resize', handleResize);

		return () => {
			clearTimeout(stopTimer);
			cancelAnimationFrame(animationId);
			window.removeEventListener('resize', handleResize);
		};
	});
</script>

<canvas bind:this={canvas}></canvas>

<style>
	canvas {
		position: fixed;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
		pointer-events: none;
		z-index: 100;
	}
</style>
