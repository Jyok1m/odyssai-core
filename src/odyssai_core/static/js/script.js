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
    },
    {
        method: "POST",
        path: "/api/join-game",
        status: "Operational",
        description: "Join an existing game world",
        response: "Confirmation of character joining the game with character_id, character_name, and world_id",
        exampleBody: {
            "world_name": "Terra Novia",
            "character_name": "jyokaro"
        },
        exampleResponse: {
            "character_id": "56feea05-af36-40da-ae30-b6cf8c807a81",
            "character_name": "jyokaro",
            "success": true,
            "world_id": "ac8918e7-ccd8-4cae-9b39-753f2994c46c",
            "world_name": "terra novia",
            "world_summary": "Terra Novia is a whimsical world where magic and alien technology mix in unexpected ways. Wizards in kimonos duel clumsily, creating chaos and laughter. The land is dotted with enchanting scrolls and ancient tech, forming a unique landscape where eccentric guilds compete for glory. In Ever-Chuckle Marsh, the mysterious Circle of Mirrors reflects worlds that blend reality and humor, a testament to the land's lighthearted yet strange nature.\n\nJyokaro, a witty and loyal hero from the city of Zenthalore, balances swordplay and wizardry. He is part of a guild known for its unusual jobs, from handling alien bounties to recovering magical artifacts. His journey is filled with slapstick battles and heartwarming quests, as he protects friends and uncovers ancient secrets. The world is lively and unpredictable, where laughter can unveil truths or trap the unwary forever."
        }
    },
    {
        method: "GET",
        path: "/api/game-prompt",
        status: "Operational",
        description: "Get game instructions/prompt for the player",
        response: "AI-generated prompt/question for the player based on current game state",
        queryParams: {
            world_id: "ac8918e7-ccd8-4cae-9b39-753f2994c46c",
            character_id: "56feea05-af36-40da-ae30-b6cf8c807a81"
        },
        exampleResponse: {
            "ai_prompt": "As the kaleidoscopic light of dawn filters through the vibrant canopy of the Wandering Woods, Jyokaro finds himself standing at the edge of Whimsyrose, a place where laughter whispers on the breeze and every shadow holds a potential jest. The Clocktower of Nonsense looms nearby, its chaotic hands spinning wildly, a testament to the town's peculiar charm. With the recent whispers of an ancient prophecy echoing in his mind, Jyokaro recalls a rumor about Tinker Tock, the reclusive gnome whose riddles might hold the key to unraveling secrets buried deep within Whimsyrose. Yet, across town, a fellow guild member frantically gestures towards the shimmering path leading to the Llibrary of Kelezoa, claiming that a once-in-a-century phenomenon is about to reveal an artifact that could change Terra Novia forever. Jyokaro stands at a crossroads: should he seek out the enigmatic gnome for answers to the prophecy, or dash towards the library to seize a chance at untold power and knowledge? The fate of whimsical worlds may hinge on his choice. What will Jyokaro do next?",
            "character_id": "56feea05-af36-40da-ae30-b6cf8c807a81",
            "success": true,
            "world_id": "ac8918e7-ccd8-4cae-9b39-753f2994c46c"
        }
    },
    {
        method: "POST",
        path: "/api/register-answer",
        status: "Operational",
        description: "Register player's answer/response to the game prompt",
        response: "Immediate events summary based on player's action",
        exampleBody: {
            "world_id": "ac8918e7-ccd8-4cae-9b39-753f2994c46c",
            "character_id": "56feea05-af36-40da-ae30-b6cf8c807a81",
            "player_answer": "I want to follow the gnome's trail."
        },
        exampleResponse: {
            "character_id": "56feea05-af36-40da-ae30-b6cf8c807a81",
            "immediate_events": "Jyokaro stands at the edge of Whimsyrose, a magical place filled with laughter and mysterious shadows. Nearby, the Clocktower of Nonsense spins its hands wildly. A prophecy about this peculiar town echoes in his mind, along with rumors of a gnome named Tinker Tock, whose riddles might unlock its secrets. Faced with a choice, Jyokaro decides to follow the gnome's trail in hopes of finding answers to the prophecy. The path ahead is uncertain, but Jyokaro feels that understanding the prophecy could be important for the future of Terra Novia.",
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