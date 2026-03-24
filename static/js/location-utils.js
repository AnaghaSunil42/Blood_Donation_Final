/**
 * location-utils.js
 * Shared utility for getting current location and searching addresses via Nominatim API.
 */

function getCurrentLocation(latId, lonId, statusId) {
    const status = document.getElementById(statusId);
    
    if (!navigator.geolocation) {
        if (status) status.innerText = "Geolocation is not supported by your browser.";
        return;
    }

    if (status) {
        status.innerText = "Locating...";
        status.className = "mt-2 small text-muted";
    }

    navigator.geolocation.getCurrentPosition(
        async (position) => {
            const lat = position.coords.latitude;
            const lon = position.coords.longitude;
            
            document.getElementById(latId).value = lat.toFixed(8);
            document.getElementById(lonId).value = lon.toFixed(8);
            
            // Reverse Geocoding to get address name
            try {
                const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`);
                const data = await response.json();
                if (data && data.display_name) {
                    if (status) {
                        status.innerHTML = `<strong>Selected Location:</strong> ${data.display_name}`;
                        status.className = "mt-2 small text-success p-2 bg-light rounded border border-success";
                    }
                } else {
                    if (status) {
                        status.innerHTML = `<strong>Selected Location:</strong> Coordinates Set (${lat.toFixed(4)}, ${lon.toFixed(4)})`;
                        status.className = "mt-2 small text-success";
                    }
                }
            } catch (err) {
                if (status) {
                    status.innerHTML = `<strong>Selected Location:</strong> Coordinates Set (${lat.toFixed(4)}, ${lon.toFixed(4)})`;
                    status.className = "mt-2 small text-success";
                }
            }
        },
        (error) => {
            if (status) {
                status.innerText = "Unable to retrieve your location: " + error.message;
                status.className = "mt-2 small text-danger";
            }
        }
    );
}

async function searchLocation(query, latId, lonId, statusId) {
    if (!query) return;
    
    const status = document.getElementById(statusId);
    if (status) {
        status.innerText = "Searching...";
        status.className = "mt-2 small text-muted";
    }

    try {
        const response = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}`);
        const data = await response.json();

        if (data && data.length > 0) {
            const lat = parseFloat(data[0].lat);
            const lon = parseFloat(data[0].lon);
            
            document.getElementById(latId).value = lat.toFixed(8);
            document.getElementById(lonId).value = lon.toFixed(8);
            
            if (status) {
                status.innerHTML = `<strong>Selected Location:</strong> ${data[0].display_name}`;
                status.className = "mt-2 small text-success p-2 bg-light rounded border border-success";
            }
        } else {
            if (status) {
                status.innerText = "No results found for that location.";
                status.className = "mt-2 small text-warning";
            }
        }
    } catch (error) {
        console.error("Geocoding error:", error);
        if (status) {
            status.innerText = "Error connecting to location service.";
            status.className = "mt-2 small text-danger";
        }
    }
}
