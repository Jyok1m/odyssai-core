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
        path: "/api/synopsis",
        status: "Operational",
        description: "Get a synopsis of an existing world",
        response: "World synopsis based on world context, lore, and characters",
        queryParams: {
            world_id: "ac8918e7-ccd8-4cae-9b39-753f2994c46c"
        },
        exampleResponse: {
            success: true,
            synopsis: "In the world of terra novia, clumsy wizards dressed in kimonos duel with magic, often causing chaos and laughter. Ancient alien technology stands alongside enchanted scrolls, creating a land full of surprises. Eccentric guilds and colorful characters wander the landscape, engaging in comedic battles and heartwarming quests. Friendships are formed as guilds compete for glory, while unraveling ancient mysteries. In the misty valleys, the Llibrary of Kelezoa stands, built from the walls of a crashed alien ship. Here, sentient amphibious librarians keep enchanted scrolls that hold the secrets to the Universe's humor, offering spells that summon laughter and potions that taste like sunshine. The library's quiet corners whisper of laughter that could save or doom the world.",
            world_id: "ac8918e7-ccd8-4cae-9b39-753f2994c46c"
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
    },
    {
        method: "POST",
        path: "/api/create-character",
        status: "Operational",
        description: "Create a new narrative character",
        response: "Character creation confirmation with character_id, character_name, character_description and world_id",
        exampleBody: {
            "world_id": "ac8918e7-ccd8-4cae-9b39-753f2994c46c",
            "character_name": "jyokaro",
            "character_gender": "male",
            "character_description": "a quick-witted swordsman with a knack for trouble, combining samurai discipline with a wizard’s magical prowess. he’s part of a rambunctious guild that takes odd jobs ranging from alien bounties to magical artifact retrieval. his sarcastic humor hides a deep loyalty to his friends."
        },
        exampleResponse: {
            "character_description": "Jyokaro is a male character in Terra Novia, a world of whimsical chaos where magic and alien technology coexist. Born in the bustling city of Zenthalore, Jyokaro grew up amidst the laughter of clumsy wizards and the hum of ancient alien artifacts. As a child, he was often caught in the middle of magical duels, sparking his fascination with both swordplay and wizardry. As he matured, Jyokaro honed his skills, blending the discipline of a samurai with the unpredictable prowess of a wizard. His quick wit and knack for finding trouble led him to join a rambunctious guild known for its odd jobs, from hunting alien bounties to retrieving magical artifacts. Despite his sarcastic humor, which often masks his true feelings, Jyokaro is deeply loyal to his friends, always ready to wield his sword or cast a spell to protect them. His role in the story is that of a cunning hero, navigating the comedic and perilous world of Terra Novia with a sharp mind and a sharper blade.",
            "character_id": "5b808977-d546-45ee-866a-7243cae1e2c3",
            "character_name": "jyokaro",
            "success": true,
            "world_id": "ac8918e7-ccd8-4cae-9b39-753f2994c46c"
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
                ${e.queryParams ? `
                <div class="endpoint-description"><strong>Query Parameters:</strong></div>
                <div class="response-example">${formatJson(e.queryParams)}</div>
                ` : ""}
                ${e.exampleBody ? `
                <div class="endpoint-description"><strong>Example Request Body:</strong></div>
                <div class="response-example">${formatJson(e.exampleBody)}</div>
                ` : ""}
                <div class="endpoint-description"><strong>Example Response:</strong></div>
                <div class="response-example">${formatJson(e.exampleResponse)}</div>
                ${e.method === 'GET' ? `<a href="${e.path}${e.queryParams ? '?' + Object.keys(e.queryParams).map(key => key + '=' + e.queryParams[key]).join('&') : ''}" class="try-button" target="_blank">🔗 Test</a>` : ""}
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