<script lang="ts">
	import type { Item } from '$lib/stores/items';
	import { markItemHandled } from '$lib/stores/items';

	export let item: Item;
	export let color: string;
	export let compact: boolean = false;

	const categoryIcons: Record<string, string> = {
		Meeting: '📅',
		School: '🏫',
		Reminder: '💡',
		Task: '✓',
		Activity: '🏃'
	};

	function handleClick() {
		markItemHandled(item.id, !item.handled);
	}

	const weekdayNames = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

	function formatTime(time: string | null): string {
		if (!time) return '';
		const [hours, minutes] = time.split(':');
		const h = parseInt(hours);
		const ampm = h >= 12 ? 'PM' : 'AM';
		const h12 = h % 12 || 12;
		return `${h12}:${minutes} ${ampm}`;
	}

	function formatRecurrence(recurrence: string | null, recurrenceDay: number | null): string {
		if (!recurrence) return '';
		if (recurrence === 'weekly' && recurrenceDay !== null) {
			return `(Every ${weekdayNames[recurrenceDay]})`;
		}
		if (recurrence === 'monthly' && recurrenceDay !== null) {
			const suffix = recurrenceDay === 1 || recurrenceDay === 21 || recurrenceDay === 31 ? 'st'
				: recurrenceDay === 2 || recurrenceDay === 22 ? 'nd'
				: recurrenceDay === 3 || recurrenceDay === 23 ? 'rd' : 'th';
			return `(Monthly on ${recurrenceDay}${suffix})`;
		}
		return `(${recurrence})`;
	}

	$: icon = categoryIcons[item.category] || '📌';
	$: timeDisplay = formatTime(item.time);
	$: recurrenceLabel = formatRecurrence(item.recurrence, item.recurrence_day);
</script>

<button
	class="item-card"
	class:handled={item.handled}
	class:compact
	style="--accent-color: {color}"
	on:click={handleClick}
>
	<div class="icon">{icon}</div>
	<div class="content">
		<div class="title">
			<span class="member">{item.family_member}</span>
			<span class="separator">–</span>
			<span class="text">{item.title}</span>
		</div>
		<div class="meta">
			<span class="category">{item.category}</span>
			{#if timeDisplay}
				<span class="time">{timeDisplay}</span>
			{/if}
			{#if recurrenceLabel}
				<span class="recurrence">{recurrenceLabel}</span>
			{/if}
		</div>
	</div>
	{#if item.handled}
		<div class="check">✓</div>
	{/if}
</button>

<style>
	.item-card {
		display: flex;
		align-items: center;
		gap: 1rem;
		padding: 1rem 1.25rem;
		background: #1a1a2e;
		border: none;
		border-left: 4px solid var(--accent-color);
		border-radius: 8px;
		cursor: pointer;
		transition: all 0.2s ease;
		width: 100%;
		text-align: left;
		color: #fff;
		font-family: inherit;
	}

	.item-card:hover {
		background: #252542;
		transform: translateX(4px);
	}

	.item-card.handled {
		opacity: 0.5;
		background: #12121f;
	}

	.item-card.handled .title .text {
		text-decoration: line-through;
	}

	.item-card.compact {
		padding: 0.6rem 1rem;
		gap: 0.75rem;
	}

	.item-card.compact .icon {
		font-size: 1.25rem;
	}

	.item-card.compact .title {
		font-size: 0.95rem;
	}

	.item-card.compact .meta {
		font-size: 0.75rem;
	}

	.icon {
		font-size: 1.5rem;
		flex-shrink: 0;
	}

	.content {
		flex: 1;
		min-width: 0;
	}

	.title {
		font-size: 1.1rem;
		font-weight: 500;
		display: flex;
		flex-wrap: wrap;
		gap: 0.4rem;
	}

	.member {
		color: var(--accent-color);
		font-weight: 600;
	}

	.separator {
		color: #666;
	}

	.text {
		color: #fff;
	}

	.meta {
		display: flex;
		gap: 0.75rem;
		margin-top: 0.3rem;
		font-size: 0.85rem;
		color: #888;
	}

	.category {
		background: #2a2a4a;
		padding: 0.1rem 0.5rem;
		border-radius: 4px;
	}

	.time {
		color: #aaa;
	}

	.recurrence {
		color: #666;
		font-style: italic;
	}

	.check {
		font-size: 1.5rem;
		color: #4CAF50;
		flex-shrink: 0;
	}
</style>
