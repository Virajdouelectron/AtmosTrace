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
            </div>
            <a href="https://maps.google.com?q=${meteor.lat},${meteor.lng}" 
               target="_blank" 
               class="block mt-2 text-center text-blue-400 hover:text-blue-300 bg-blue-900/50 p-1 rounded">
                View on Map
            </a>
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

// Fetch and update meteor data
async function fetchMeteors() {
    showSpinner();
    try {
        const response = await fetch('/api/meteors');
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
                color: meteor.magnitude >= 6 ? '#ff0000' : 
                       meteor.magnitude >= 5 ? '#ff4444' : '#ffa500',
                radius: meteor.magnitude >= 6 ? 0.5 : 0.3,
                label: meteor.magnitude >= 6 ? '🚨' : '☄️'
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

// Initialize and start updates
document.addEventListener('DOMContentLoaded', () => {
    initGlobe();
    fetchMeteors();
    setInterval(fetchMeteors, 60000); // Update every minute
}); 