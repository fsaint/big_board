<script lang="ts">
	import { displayDate, isTomorrow, connected } from '$lib/stores/items';
	import { onMount, onDestroy } from 'svelte';

	let currentTime = new Date();
	let interval: ReturnType<typeof setInterval>;

	onMount(() => {
		interval = setInterval(() => {
			currentTime = new Date();
		}, 1000);
	});

	onDestroy(() => {
		if (interval) clearInterval(interval);
	});

	function formatDate(dateStr: string): string {
		const date = new Date(dateStr + 'T00:00:00');
		return date.toLocaleDateString('en-US', {
			weekday: 'long',
			month: 'long',
			day: 'numeric'
		});
	}

	function formatTime(date: Date): string {
		return date.toLocaleTimeString('en-US', {
			hour: 'numeric',
			minute: '2-digit',
			hour12: true
		});
	}

	$: dateLabel = $isTomorrow ? 'Tomorrow' : 'Today';
	$: formattedDate = formatDate($displayDate);
	$: formattedTime = formatTime(currentTime);
</script>

<header>
	<div class="date-section">
		<span class="label">{dateLabel}:</span>
		<span class="date">{formattedDate}</span>
	</div>
	<div class="time-section">
		<span class="time">{formattedTime}</span>
		<span class="status" class:connected={$connected} class:disconnected={!$connected}>
			{$connected ? '●' : '○'}
		</span>
	</div>
</header>

<style>
	header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1rem 1.5rem;
		background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
		border-bottom: 1px solid #2a2a4a;
	}

	.date-section {
		display: flex;
		align-items: baseline;
		gap: 0.5rem;
	}

	.label {
		font-size: 1rem;
		color: #888;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.date {
		font-size: 1.4rem;
		font-weight: 600;
		color: #fff;
	}

	.time-section {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.time {
		font-size: 1.4rem;
		font-weight: 500;
		color: #fff;
		font-variant-numeric: tabular-nums;
	}

	.status {
		font-size: 0.75rem;
	}

	.status.connected {
		color: #4CAF50;
	}

	.status.disconnected {
		color: #f44336;
		animation: pulse 1s infinite;
	}

	@keyframes pulse {
		0%, 100% { opacity: 1; }
		50% { opacity: 0.3; }
	}
</style>
