CHAIN_TEMPLATES = {
    "extract_features": {
        "system": "You are a technical analyst. Extract core features and SEO keywords objectively. Output ONLY valid JSON.",
        "user": "Extract 5 core features and 5 SEO keywords from this plugin description: {features}",
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "schema_hint": '{"features": ["string"], "keywords": ["string"]}'
    },
    "marketing_copy": {
        "system": "You are a WordPress plugin copywriter. Write concise, benefit-driven marketing copy. Keep it under 150 words. Focus on user outcomes, not technical specs.",
        "user": "Write a compelling description based on these features: {features}",
        "temperature": 0.7,
        "response_format": None,
        "schema_hint": None
    },
    "faqs_and_pros_cons": {
        "system": "You are a product marketer. Generate realistic FAQs and balanced pros/cons. Output ONLY valid JSON matching the schema.",
        "user": "Based on this description, generate 3 FAQs and pros/cons: {description}",
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
        "schema_hint": '{"faqs": [{"q": "string", "a": "string"}], "pros": ["string"], "cons": ["string"]}'
    }
}