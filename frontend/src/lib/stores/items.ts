import { writable, derived } from 'svelte/store';

export interface Item {
	id: number;
	title: string;
	family_member: string;
	date: string;
	time: string | null;
	category: string;
	recurrence: string | null;
	recurrence_day: number | null;
	handled: boolean;
}

interface DashboardState {
	items: Item[];
	familyMembers: Record<string, string>;
	categories: string[];
	displayDate: string;
	isTomorrow: boolean;
	connected: boolean;
}

const initialState: DashboardState = {
	items: [],
	familyMembers: {},
	categories: [],
	displayDate: new Date().toISOString().split('T')[0],
	isTomorrow: false,
	connected: false
};

export const dashboardState = writable<DashboardState>(initialState);

// Derived stores for convenience
export const items = derived(dashboardState, $state => $state.items);
export const activeItems = derived(dashboardState, $state =>
	$state.items.filter(item => !item.handled)
);
export const handledItems = derived(dashboardState, $state =>
	$state.items.filter(item => item.handled)
);
export const familyMembers = derived(dashboardState, $state => $state.familyMembers);
export const categories = derived(dashboardState, $state => $state.categories);
export const displayDate = derived(dashboardState, $state => $state.displayDate);
export const isTomorrow = derived(dashboardState, $state => $state.isTomorrow);
export const connected = derived(dashboardState, $state => $state.connected);

let ws: WebSocket | null = null;
let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;

export function connectWebSocket() {
	if (ws?.readyState === WebSocket.OPEN) return;

	// Determine WebSocket URL based on current location
	const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
	const wsUrl = `${protocol}//${window.location.host}/ws`;

	ws = new WebSocket(wsUrl);

	ws.onopen = () => {
		console.log('WebSocket connected');
		dashboardState.update(state => ({ ...state, connected: true }));
		if (reconnectTimeout) {
			clearTimeout(reconnectTimeout);
			reconnectTimeout = null;
		}
	};

	ws.onmessage = (event) => {
		const data = JSON.parse(event.data);
		handleMessage(data);
	};

	ws.onclose = () => {
		console.log('WebSocket disconnected');
		dashboardState.update(state => ({ ...state, connected: false }));
		// Reconnect after 2 seconds
		reconnectTimeout = setTimeout(connectWebSocket, 2000);
	};

	ws.onerror = (error) => {
		console.error('WebSocket error:', error);
	};
}

function handleMessage(data: any) {
	if (data.type === 'init' || data.type === 'update') {
		dashboardState.update(state => ({
			...state,
			items: data.items,
			familyMembers: data.family_members,
			categories: data.categories,
			displayDate: data.display_date,
			isTomorrow: data.is_tomorrow
		}));
	}
}

export function markItemHandled(itemId: number, handled: boolean = true) {
	if (ws?.readyState === WebSocket.OPEN) {
		ws.send(JSON.stringify({
			type: 'mark_handled',
			item_id: itemId,
			handled
		}));
	}
}

export function requestRefresh() {
	if (ws?.readyState === WebSocket.OPEN) {
		ws.send(JSON.stringify({ type: 'refresh' }));
	}
}

export function disconnectWebSocket() {
	if (reconnectTimeout) {
		clearTimeout(reconnectTimeout);
		reconnectTimeout = null;
	}
	if (ws) {
		ws.close();
		ws = null;
	}
}
