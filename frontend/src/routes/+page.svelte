<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import Header from '$lib/components/Header.svelte';
	import ItemCard from '$lib/components/ItemCard.svelte';
	import {
		connectWebSocket,
		disconnectWebSocket,
		activeItems,
		handledItems,
		familyMembers
	} from '$lib/stores/items';

	let showHandled = false;

	onMount(() => {
		connectWebSocket();
	});

	onDestroy(() => {
		disconnectWebSocket();
	});

	function getColor(member: string): string {
		return $familyMembers[member] || '#888888';
	}

	// Determine if we need compact mode based on item count
	$: totalActive = $activeItems.length;
	$: compact = totalActive > 8;
</script>

<svelte:head>
	<title>Big Board</title>
</svelte:head>

<div class="dashboard">
	<Header />

	<main>
		{#if $activeItems.length === 0 && $handledItems.length === 0}
			<div class="empty-state">
				<div class="empty-icon">📋</div>
				<div class="empty-text">Nothing on the board</div>
				<div class="empty-hint">Add items via the MCP server</div>
			</div>
		{:else}
			<div class="items-grid" class:compact>
				{#each $activeItems as item (item.id)}
					<ItemCard {item} color={getColor(item.family_member)} {compact} />
				{/each}
			</div>

			{#if $handledItems.length > 0}
				<button
					class="handled-toggle"
					on:click={() => (showHandled = !showHandled)}
				>
					{showHandled ? '▼' : '▶'} Handled ({$handledItems.length})
				</button>

				{#if showHandled}
					<div class="handled-items">
						{#each $handledItems as item (item.id)}
							<ItemCard {item} color={getColor(item.family_member)} compact={true} />
						{/each}
					</div>
				{/if}
			{/if}
		{/if}
	</main>
</div>

<style>
	:global(*) {
		box-sizing: border-box;
		margin: 0;
		padding: 0;
	}

	:global(body) {
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen,
			Ubuntu, Cantarell, sans-serif;
		background: #0f0f1a;
		color: #fff;
		min-height: 100vh;
	}

	.dashboard {
		display: flex;
		flex-direction: column;
		min-height: 100vh;
	}

	main {
		flex: 1;
		padding: 1.5rem;
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.items-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
		gap: 1rem;
		align-content: start;
	}

	.items-grid.compact {
		grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
		gap: 0.75rem;
	}

	.empty-state {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 1rem;
		color: #555;
	}

	.empty-icon {
		font-size: 4rem;
		opacity: 0.5;
	}

	.empty-text {
		font-size: 1.5rem;
		font-weight: 500;
	}

	.empty-hint {
		font-size: 1rem;
		color: #444;
	}

	.handled-toggle {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.75rem 1rem;
		background: transparent;
		border: 1px solid #333;
		border-radius: 8px;
		color: #666;
		font-size: 0.9rem;
		cursor: pointer;
		transition: all 0.2s;
		width: fit-content;
	}

	.handled-toggle:hover {
		background: #1a1a2e;
		color: #888;
	}

	.handled-items {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
		gap: 0.5rem;
		opacity: 0.7;
	}
</style>
