const endpoints = [
    {
        method: "GET",
        path: "/api/health",
        status: "Operational",
        description: "Health check verification for the API",
        response: "API status with timestamp and version information",
        exampleResponse: {
            status: "healthy",
            timestamp: "2025-08-09T12:00:00.000Z",
            service: "odyssai-core",
            version: "1.0.0"
        }
    },
    {
        method: "POST",
        path: "/api/create-world",
        status: "Operational",
        description: "Create a new narrative world",
        response: "World creation confirmation with synopsis, world_id and world_name",
        exampleBody: {
            world_name: "Terra Novia",
            world_genre: "Fantasy-science fiction hybrid with Edo-era aesthetics, magic guild culture, and advanced alien technology",
            story_directives: "A high-energy blend of slapstick comedy, heartfelt camaraderie, and over-the-top battles. The world is filled with eccentric characters, absurd situations, and frequent meta-humor, balanced by emotional story arcs about friendship, loyalty, and protecting one's home. Magic guild rivalries, alien politics, and ancient mysteries intertwine in unpredictable adventures."
        },
        exampleResponse: {
            success: true,
            synopsis: "Terra Novia is a whimsical land where wizards in kimonos practice their magic through duels that often end in laughter. Ancient alien technology mingles with enchanted scrolls, creating a landscape full of surprises. Eccentric guilds and quirky characters roam the land, competing for glory while solving ancient mysteries. The fabled Library of Kelezoa, built from the remains of a crashed alien ship, holds the secrets to the Universe's humor. In this peculiar library, spells of joy and enchanted scrolls offer the power to pause time for a moment of delight, while its corridors whisper of laughter that could save or doom the world.",
            world_id: "ac8918e7-ccd8-4cae-9b39-753f2994c46c",
            world_name: "terra novia"
        }
    }
];

const formatJson = (obj) => {
    return JSON.stringify(obj, null, 2);
}

const createEndpointList = (endpoints) => {
    let endpointsHtml = "";
    for (const e of endpoints) {
        endpointsHtml += `
        <div class="endpoint">
            <div class="endpoint-header">
                <span class="method ${e.method.toLowerCase()}">${e.method.toUpperCase()}</span>
                <span class="endpoint-path">${e.path}</span>
                <span class="status-badge">${e.status}</span>
            </div>
            <div class="endpoint-body">
                <div class="endpoint-description"><strong>Description:</strong> ${e.description}</div>
                <div class="endpoint-description"><strong>Response:</strong> ${e.response}</div>
                ${e.exampleBody ? `
                <div class="endpoint-description"><strong>Example Request Body:</strong></div>
                <div class="response-example">${formatJson(e.exampleBody)}</div>
                ` : ""}
                <div class="endpoint-description"><strong>Example Response:</strong></div>
                <div class="response-example">${formatJson(e.exampleResponse)}</div>
                ${e.method === 'GET' ? `<a href="${e.path}" class="try-button" target="_blank">🔗 Test</a>` : ""}
            </div>
        </div>
        `
    }
    return endpointsHtml;
}

document.addEventListener("DOMContentLoaded", () => {
    const apiSection = document.querySelector(".api-section");
    apiSection.innerHTML = createEndpointList(endpoints);
});