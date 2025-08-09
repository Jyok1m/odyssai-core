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
        method: "GET",
        path: "/api/create-world",
        status: "Operational",
        description: "Create a new narrative world",
        response: "Creation confirmation with workflow details",
        exampleResponse: {
            success: true,
            workflow: {
                // Détails du workflow de création
            }
        }
    }
];

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
                <div class="response-example">
                    ${JSON.stringify(e.exampleResponse, null, 2)}
                </div>
                <a href="${e.path}" class="try-button" target="_blank">🔗 Test</a>
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