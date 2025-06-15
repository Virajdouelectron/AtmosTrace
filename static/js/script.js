// Globe initialization and configuration
let globe;
let isInitialized = false;

function initGlobe() {
    if (isInitialized) return;
    
    globe = Globe()
        .globeImageUrl('//unpkg.com/three-globe/example/img/earth-blue-marble.jpg')
        .bumpImageUrl('//unpkg.com/three-globe/example/img/earth-topology.png')
        .backgroundImageUrl('//unpkg.com/three-globe/example/img/night-sky.png')
        .width(window.innerWidth)
        .height(window.innerHeight)
        .atmosphereColor('#ffffff')
        .atmosphereAltitude(0.1)
        .autoRotate(true)
        .autoRotateSpeed(0.5)
        (document.getElementById('globeViz'));

    // Handle window resize
    window.addEventListener('resize', () => {
        globe.width(window.innerWidth)
            .height(window.innerHeight);
    });

    isInitialized = true;
}

// Tooltip handling
const tooltip = document.getElementById('tooltip');

function showTooltip(event, meteor) {
    const { clientX, clientY } = event;
    tooltip.style.left = `${clientX + 10}px`;
    tooltip.style.top = `${clientY + 10}px`;
    
    const warningHtml = meteor.magnitude >= 6 ? 
        `<div class="warning-badge mb-2">🚨 HIGH IMPACT</div>` : '';
    
    const mediaButtonHtml = (meteor.media && (meteor.media.images.length > 0 || meteor.media.videos.length > 0)) ?
        `<button class="media-button" onclick="showMediaGallery(${JSON.stringify(meteor)})">
            <i class="fas fa-images"></i>
            View Media
        </button>` : '';
    
    tooltip.innerHTML = `
        <div class="space-y-2">
            ${warningHtml}
            <div class="font-bold">${meteor.type || 'Fireball'}</div>
            <div class="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
                <div>Magnitude:</div>
                <div>${meteor.magnitude}</div>
                <div>Velocity:</div>
                <div>${meteor.velocity_kms} km/s</div>
                <div>Time (UTC):</div>
                <div>${meteor.time_utc}</div>
                <div>Source:</div>
                <div>${meteor.source}</div>
            </div>
            <div class="flex space-x-2">
                <a href="${meteor.mapLink}" 
                   target="_blank" 
                   class="block mt-2 text-center text-blue-400 hover:text-blue-300 bg-blue-900/50 p-1 rounded flex-1">
                    View on Map
                </a>
                ${mediaButtonHtml}
            </div>
        </div>
    `;
    tooltip.classList.remove('hidden');
}

function hideTooltip() {
    tooltip.classList.add('hidden');
}

// Loading spinner
const spinner = document.querySelector('.loading-spinner');

function showSpinner() {
    spinner.classList.add('active');
}

function hideSpinner() {
    spinner.classList.remove('active');
}

// Calculate entry point (15° away from impact)
function calculateEntryPoint(lat, lng) {
    const distance = 15; // degrees
    const bearing = Math.random() * 360; // random direction
    
    const lat1 = lat * Math.PI / 180;
    const lng1 = lng * Math.PI / 180;
    const brng = bearing * Math.PI / 180;
    
    const lat2 = Math.asin(
        Math.sin(lat1) * Math.cos(distance/180*Math.PI) +
        Math.cos(lat1) * Math.sin(distance/180*Math.PI) * Math.cos(brng)
    );
    
    const lng2 = lng1 + Math.atan2(
        Math.sin(brng) * Math.sin(distance/180*Math.PI) * Math.cos(lat1),
        Math.cos(distance/180*Math.PI) - Math.sin(lat1) * Math.sin(lat2)
    );
    
    return {
        lat: lat2 * 180 / Math.PI,
        lng: lng2 * 180 / Math.PI
    };
}

// Initialize date inputs with default values
function initializeDateInputs() {
    const today = new Date();
    const oneMonthAgo = new Date();
    oneMonthAgo.setMonth(today.getMonth() - 1);
    
    document.getElementById('startDate').value = oneMonthAgo.toISOString().split('T')[0];
    document.getElementById('endDate').value = today.toISOString().split('T')[0];
}

// Show/hide custom date range inputs
function toggleCustomDateRange() {
    const customDateRange = document.getElementById('customDateRange');
    const timeRange = document.getElementById('timeRange').value;
    
    if (timeRange === 'custom') {
        customDateRange.classList.remove('hidden');
    } else {
        customDateRange.classList.add('hidden');
    }
}

// Fetch and update meteor data
async function fetchMeteors() {
    showSpinner();
    try {
        const timeRange = document.getElementById('timeRange').value;
        let url = '/api/meteors?time_range=' + timeRange;
        
        if (timeRange === 'custom') {
            const startDate = document.getElementById('startDate').value;
            const endDate = document.getElementById('endDate').value;
            url += `&start_date=${startDate}&end_date=${endDate}`;
        }
        
        const response = await fetch(url);
        const meteors = await response.json();
        
        // Clear existing points and arcs
        globe.pointsData([]).arcsData([]);
        
        // Add new points and arcs
        const points = meteors.map(meteor => {
            const entryPoint = calculateEntryPoint(meteor.lat, meteor.lng);
            return {
                ...meteor,
                entryLat: entryPoint.lat,
                entryLng: entryPoint.lng,
                color: getMeteorColor(meteor),
                radius: getMeteorRadius(meteor),
                label: getMeteorLabel(meteor)
            };
        });

        const arcs = points.map(meteor => ({
            startLat: meteor.entryLat,
            startLng: meteor.entryLng,
            endLat: meteor.lat,
            endLng: meteor.lng,
            color: meteor.color
        }));

        globe.pointsData(points)
            .arcsData(arcs)
            .pointAltitude(0.1)
            .pointColor('color')
            .pointRadius('radius')
            .pointLabel('label')
            .arcColor('color')
            .arcAltitude(0.3)
            .arcStroke(0.5)
            .arcDashLength(0.4)
            .arcDashGap(0.2)
            .arcDashAnimateTime(2000);

        // Add hover effects
        globe.onPointHover(showTooltip)
            .onPointUnhover(hideTooltip);
    } catch (error) {
        console.error('Error fetching meteor data:', error);
    } finally {
        hideSpinner();
    }
}

// Helper functions for meteor visualization
function getMeteorColor(meteor) {
    if (meteor.magnitude >= 6) return '#ff0000';
    if (meteor.magnitude >= 5) return '#ff4444';
    return '#ffa500';
}

function getMeteorRadius(meteor) {
    if (meteor.magnitude >= 6) return 0.5;
    if (meteor.magnitude >= 5) return 0.4;
    return 0.3;
}

function getMeteorLabel(meteor) {
    if (meteor.magnitude >= 6) return '🚨';
    return '☄️';
}

// Media Gallery Functions
function showMediaGallery(meteor) {
    const modal = document.getElementById('mediaModal');
    const imageGallery = document.querySelector('.image-gallery');
    const videoGallery = document.querySelector('.video-gallery');
    
    // Clear existing content
    imageGallery.innerHTML = '';
    videoGallery.innerHTML = '';
    
    // Add images
    if (meteor.media && meteor.media.images && meteor.media.images.length > 0) {
        meteor.media.images.forEach(image => {
            const imageCard = document.createElement('div');
            imageCard.className = 'image-card';
            imageCard.innerHTML = `
                <img src="${image.url}" alt="${image.title}">
                <div class="image-info">
                    <div class="image-title">${image.title}</div>
                    <div class="image-description">${image.description}</div>
                    <div class="image-source">Source: ${image.source}</div>
                </div>
            `;
            imageGallery.appendChild(imageCard);
        });
    } else {
        imageGallery.innerHTML = '<div class="text-center text-gray-500">No images available</div>';
    }
    
    // Add videos
    if (meteor.media && meteor.media.videos && meteor.media.videos.length > 0) {
        meteor.media.videos.forEach(video => {
            const videoCard = document.createElement('div');
            videoCard.className = 'video-card';
            videoCard.innerHTML = `
                <div class="video-thumbnail">
                    <img src="${video.thumbnail}" alt="${video.title}">
                    <div class="play-button" onclick="window.open('${video.url}', '_blank')">
                        <svg viewBox="0 0 24 24" width="24" height="24" fill="white">
                            <path d="M8 5v14l11-7z"/>
                        </svg>
                    </div>
                </div>
                <div class="video-info">
                    <div class="video-title">${video.title}</div>
                    <div class="video-source">Source: ${video.source}</div>
                </div>
            `;
            videoGallery.appendChild(videoCard);
        });
    } else {
        videoGallery.innerHTML = '<div class="text-center text-gray-500">No videos available</div>';
    }
    
    // Show modal
    modal.classList.remove('hidden');
}

function hideMediaGallery() {
    const modal = document.getElementById('mediaModal');
    modal.classList.add('hidden');
}

// Tab switching
function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.toggle('active', button.dataset.tab === tabName);
    });
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `${tabName}Tab`);
    });
}

// Initialize and start updates
document.addEventListener('DOMContentLoaded', () => {
    initGlobe();
    initializeDateInputs();
    fetchMeteors();
    
    // Add event listeners
    document.getElementById('timeRange').addEventListener('change', () => {
        toggleCustomDateRange();
        fetchMeteors();
    });
    
    document.getElementById('applyCustomRange').addEventListener('click', fetchMeteors);
    
    // Media gallery event listeners
    document.querySelector('.close-modal').addEventListener('click', hideMediaGallery);
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', () => switchTab(button.dataset.tab));
    });
    
    // Close modal when clicking outside
    document.getElementById('mediaModal').addEventListener('click', (e) => {
        if (e.target === e.currentTarget) {
            hideMediaGallery();
        }
    });
    
    // Only set interval for realtime updates if realtime is selected
    let updateInterval = setInterval(() => {
        if (document.getElementById('timeRange').value === 'realtime') {
            fetchMeteors();
        }
    }, 60000); // Update every minute
    
    // Update interval when time range changes
    document.getElementById('timeRange').addEventListener('change', () => {
        clearInterval(updateInterval);
        if (document.getElementById('timeRange').value === 'realtime') {
            updateInterval = setInterval(fetchMeteors, 60000);
        }
    });
}); 