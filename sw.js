// Frozen Soldat service worker.
// Its whole job: keep a copy of the game so it still loads with no internet.

const CACHE = 'frozen-soldat';

// Take over immediately instead of waiting for every old tab to close.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));

self.addEventListener('fetch', (event) => {
    if (event.request.method !== 'GET') return;

    // NETWORK FIRST -- this ordering matters more than it looks.
    //
    // Try the internet, and quietly save whatever comes back. Only fall back
    // to the saved copy if the network fails.
    //
    // The opposite (cache first) is faster, and it is the classic way to
    // wreck a game you update often: players get served the old saved copy
    // forever and have no idea why your fixes never show up. This way, online
    // players always get your latest push, and offline players get the last
    // version they successfully loaded.
    event.respondWith(
        fetch(event.request)
            .then((response) => {
                const copy = response.clone();
                caches.open(CACHE).then((cache) => cache.put(event.request, copy));
                return response;
            })
            .catch(() => caches.match(event.request))
    );
});
