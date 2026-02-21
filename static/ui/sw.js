const CACHE_NAME = 'broadcast-v1';

// Install event - skip waiting to activate immediately
self.addEventListener('install', (event) => {
    self.skipWaiting();
});

// Activate event - claim clients immediately
self.addEventListener('activate', (event) => {
    event.waitUntil(self.clients.claim());
});

// Fetch event - Network only (since this is a realtime controller)
// We don't want to cache the API calls or the main page logic too aggressively
// in case of updates.
self.addEventListener('fetch', (event) => {
    if (event.request.method !== 'GET') {
        return;
    }
    
    event.respondWith(
        fetch(event.request)
            .catch(() => {
                // simple fallback if offline
                return new Response("請檢查網路連線 (Network Error)", {
                    status: 503,
                    statusText: "Service Unavailable"
                });
            })
    );
});
