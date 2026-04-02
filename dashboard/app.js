/* 
MaatiGyan Dashboard Logic
*/

document.addEventListener('DOMContentLoaded', () => {
    // ─── Configuration & State ──────────────────────────────────────────────
    const API_BASE = window.location.origin; // Dynamically detect host
    let map, marker;
    let stats = { queries: 0, savings: 0 };
    
    // ─── Initialize Map ─────────────────────────────────────────────────────
    function initMap() {
        // Center of Bangladesh
        map = L.map('map', {
            center: [23.8103, 90.4125],
            zoom: 7,
            zoomControl: false
        });

        // Add Dark Mode Tiles
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
            subdomains: 'abcd',
            maxZoom: 20
        }).addTo(map);

        // Add Zoom Control to Bottom Right
        L.control.zoom({ position: 'bottomright' }).addTo(map);

        // Handle Map Clicks
        map.on('click', (e) => {
            const { lat, lng } = e.latlng;
            placeMarker(lat, lng);
            triggerAnalysis(lat, lng);
        });

        // Default Marker in Bogura
        placeMarker(24.8481, 89.3730);
    }

    function placeMarker(lat, lng) {
        if (marker) map.removeLayer(marker);
        marker = L.marker([lat, lng]).addTo(map);
        map.panTo([lat, lng]);
    }

    // ─── Analysis Logic ─────────────────────────────────────────────────────
    async function triggerAnalysis(lat, lng) {
        addFeedItem('Satellite Fetching...', 'Querying Sentinel-2 COPERNICUS imagery...', 'pending');
        
        try {
            const response = await fetch(`${API_BASE}/api/analyze?lat=${lat}&lon=${lng}`, {
                method: 'POST'
            });
            if (!response.ok) throw new Error('API Error');
            
            const data = await response.json();
            handleAnalysisResult(data);
        } catch (err) {
            console.error(err);
            addFeedItem('Analysis Failed', `Error: ${err.message}`, 'error');
        }
    }

    function handleAnalysisResult(data) {
        // Update Stats
        stats.queries++;
        if (data.prediction.savings_estimate.saving_bdt) {
            stats.savings += data.prediction.savings_estimate.saving_bdt;
        }
        updateDashboardStats();

        // Add to Feed
        addFeedItem(
            `Analysis Complete: ${data.district}`,
            data.report.summary,
            'success',
            data.report.text
        );

        // Show Modal
        showReportModal(data.report.text);
    }

    // ─── UI Interactions ─────────────────────────────────────────────────────
    function addFeedItem(title, details, status, fullReportText = null) {
        const feed = document.getElementById('activity-feed');
        const item = document.createElement('div');
        item.className = 'feed-item';
        
        const timestamp = new Date().toLocaleTimeString();
        
        item.innerHTML = `
            <div class="feed-item-header">
                <span class="feed-title">${title}</span>
                <span class="feed-time">${timestamp}</span>
            </div>
            <div class="feed-details">${details}</div>
            <div class="feed-tags">
                <span class="tag tag-${status}">${status.toUpperCase()}</span>
                ${fullReportText ? '<button class="tag btn-view" style="cursor:pointer; border:none; background:rgba(255,255,255,0.1); color:white;">VIEW REPORT</button>' : ''}
            </div>
        `;

        if (fullReportText) {
            item.querySelector('.btn-view').onclick = () => showReportModal(fullReportText);
        }

        feed.prepend(item);
        
        // Remove placeholder if exists
        const placeholder = feed.querySelector('.feed-placeholder');
        if (placeholder) placeholder.remove();

        // Limit feed to 10 items
        if (feed.children.length > 10) {
            feed.lastElementChild.remove();
        }
    }

    function updateDashboardStats() {
        document.getElementById('stats-queries').textContent = stats.queries;
        document.getElementById('stats-savings').textContent = `৳${stats.savings.toLocaleString()}`;
    }

    // Modal Controls
    const modal = document.getElementById('report-modal');
    const closeBtn = document.getElementById('close-report');
    
    function showReportModal(text) {
        const body = document.getElementById('report-details');
        body.innerHTML = `<div class="report-card">${text}</div>`;
        modal.classList.remove('hidden');
    }

    closeBtn.onclick = () => modal.classList.add('hidden');
    window.onclick = (e) => { if (e.target == modal) modal.classList.add('hidden'); };

    // ─── Event Listeners ────────────────────────────────────────────────────
    
    // Simulate Button
    document.getElementById('btn-simulate').addEventListener('click', () => {
        // Random point in Bangladesh
        const lat = 22.5 + Math.random() * 3.5;
        const lng = 88.5 + Math.random() * 3.5;
        placeMarker(lat, lng);
        triggerAnalysis(lat, lng);
    });

    // Start everything
    initMap();
    addFeedItem('System Online', 'Monitoring WhatsApp webhook and satellite streams.', 'success');
});
