/**
 * MaatiGyan — Farmer Web App Logic
 * Handles GPS location, form submission, and report display.
 */

const API_BASE_URL = window.location.origin; // Dynamically detect host
const steps = {
    location: document.getElementById('step-location'),
    info: document.getElementById('step-info'),
    loading: document.getElementById('step-loading'),
    report: document.getElementById('step-report')
};

let userCoords = { lat: null, lon: null };

// --- Navigation ---
function showStep(stepName) {
    Object.values(steps).forEach(s => s.classList.remove('active'));
    steps[stepName].classList.add('active');
}

// --- Step 1: Geolocation ---
document.getElementById('btn-get-location').addEventListener('click', () => {
    const statusDisplay = document.getElementById('location-display');
    
    if (!navigator.geolocation) {
        statusDisplay.innerText = "Error: Geolocation not supported.";
        return;
    }

    statusDisplay.innerText = "লোকেশন খোঁজা হচ্ছে...";
    
    navigator.geolocation.getCurrentPosition(
        (position) => {
            userCoords.lat = position.coords.latitude;
            userCoords.lon = position.coords.longitude;
            statusDisplay.innerText = `✅ লোকেশন পাওয়া গেছে: ${userCoords.lat.toFixed(4)}, ${userCoords.lon.toFixed(4)}`;
            
            // Auto-advance after a small delay
            setTimeout(() => showStep('info'), 1000);
        },
        (error) => {
            console.error("GPS Error:", error);
            statusDisplay.innerText = "❌ লোকেশন পাওয়া যায়নি। অনুগ্রহ করে পারমিশন দিন।";
            alert("আপনার জমির সঠিক রিপোর্ট পেতে লোকেশন পারমিশন প্রয়োজন।");
        },
        { enableHighAccuracy: true, timeout: 10000 }
    );
});

// --- Step 2: Form Submission ---
document.getElementById('btn-analyze').addEventListener('click', async () => {
    const farmerName = document.getElementById('farmer-name').value;
    const landArea = parseFloat(document.getElementById('land-area').value);
    const cropType = document.getElementById('crop-type').value;

    if (!farmerName || !landArea) {
        alert("অনুগ্রহ করে আপনার নাম এবং জমির পরিমাণ লিখুন।");
        return;
    }

    if (!userCoords.lat) {
        alert("লোকেশন পাওয়া যায়নি। আবার চেষ্টা করুন।");
        showStep('location');
        return;
    }

    showStep('loading');

    try {
        const response = await fetch(`${API_BASE_URL}/api/farmer-analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                lat: userCoords.lat,
                lon: userCoords.lon,
                farmer_name: farmerName,
                land_area: landArea,
                crop: cropType,
                language: 'bn'
            })
        });

        if (!response.ok) throw new Error("Analysis failed");

        const result = await response.json();
        displayReport(result.report.text);
        showStep('report');

    } catch (err) {
        console.error("API Error:", err);
        alert("দুঃখিত, রিপোর্ট তৈরি করা সম্ভব হয়নি। আবার চেষ্টা করুন।");
        showStep('info');
    }
});

// --- Step 4: Display Results ---
function displayReport(markdownText) {
    const reportBox = document.getElementById('report-content');
    // Simple markdown-ish to HTML conversion for the result box
    let html = markdownText
        .replace(/\*(.*?)\*/g, '<strong>$1</strong>')
        .replace(/_(.*?)_/g, '<em>$1</em>')
        .replace(/━━━━━━━━━━━━━━━━━━━━━━/g, '<hr>');
    
    reportBox.innerHTML = html;
}
