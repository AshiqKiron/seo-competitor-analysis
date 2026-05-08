import streamlit as st
from openai import OpenAI
import json
import os
from dotenv import load_dotenv
from prompts import CHAIN_TEMPLATES

load_dotenv()

# Initialize client
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

def clean_json(text: str) -> str:
    """Strip markdown/code blocks that sometimes wrap JSON"""
    return text.replace("```json", "").replace("```", "").strip()

def safe_json_parse(text: str, max_retries: int = 2) -> dict:
    """Parse JSON with fallback retry logic"""
    cleaned = clean_json(text)
    for attempt in range(max_retries + 1):
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            if attempt < max_retries:
                # In production: call LLM again with "Fix the JSON to match schema"
                cleaned = clean_json(cleaned)  # double clean
            else:
                raise ValueError("JSON parsing failed. Check model output format.")

def run_chain(features: str) -> dict:
    # STEP 1: Extract
    st.session_state["step1_output"] = "🔄 Step 1: Extracting features & keywords..."
    p1 = CHAIN_TEMPLATES["extract_features"]
    r1 = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": p1["system"]},
            {"role": "user", "content": p1["user"].format(features=features)}
        ],
        temperature=p1["temperature"],
        response_format=p1["response_format"]
    )
    step1 = safe_json_parse(r1.choices[0].message.content)
    
    # 🔍 Safely extract & format as clean strings
    features_list = step1.get("features", [])
    keywords_list = step1.get("keywords", [])
    features_str = "\n".join([f"- {f}" for f in features_list]) if features_list else features
    keywords_str = ", ".join(keywords_list) if keywords_list else ""

    # STEP 2: Marketing Copy
    st.session_state["step2_output"] = "🔄 Step 2: Generating marketing copy..."
    p2 = CHAIN_TEMPLATES["marketing_copy"]
    r2 = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": p2["system"]},
            {"role": "user", "content": p2["user"].format(features=features_str)}
        ],
        temperature=p2["temperature"],
        response_format=p2["response_format"]
    )
    step2 = r2.choices[0].message.content.strip()

    # STEP 3: FAQs + Pros/Cons
    st.session_state["step3_output"] = "🔄 Step 3: Building FAQs & pros/cons..."
    p3 = CHAIN_TEMPLATES["faqs_and_pros_cons"]
    r3 = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": p3["system"]},
            {"role": "user", "content": p3["user"].format(description=step2)}
        ],
        temperature=p3["temperature"],
        response_format=p3["response_format"]
    )
    step3 = safe_json_parse(r3.choices[0].message.content)

    st.session_state["step3_output"] = "✅ Done!"
    
    return {
        "features": features_list,
        "seo_keywords": keywords_list if keywords_list else features_list[:5],
        "description": step2,
        "faqs": step3.get("faqs", []),
        "pros": step3.get("pros", []),
        "cons": step3.get("cons", [])
    }

# Streamlit UI
st.set_page_config(page_title="WP Plugin Copy Generator", layout="wide")
st.title("🤖 AI Plugin Description & SEO Generator")

features = st.text_area("Paste raw plugin features / changelog / readme:", height=150, placeholder="e.g., 1-click migration, GDPR compliant, supports WooCommerce, lazy loading, custom shortcode builder...")

col1, col2 = st.columns([1, 3])
with col1:
    generate = st.button("🚀 Generate Copy", type="primary", disabled=not features)

if generate:
    with st.spinner("Chaining prompts..."):
        result = run_chain(features)

    # Display results
    st.subheader("📝 Marketing Description")
    st.write(result["description"])

    st.subheader("🔑 SEO Keywords")
    st.write(", ".join(result["seo_keywords"]))

        # 🔹 SAFE DISPLAY SECTION (Replace everything from st.subheader("❓ FAQs") downward)
    st.subheader("❓ FAQs")
    for faq in result["faqs"]:
        # Gracefully handle any key variation the LLM might return
        q = faq.get("q") or faq.get("question") or faq.get("Q") or list(faq.keys())[0]
        a = faq.get("a") or faq.get("answer") or faq.get("A") or list(faq.values())[1]
        st.markdown(f"**Q:** {q}\n**A:** {a}")

    st.subheader("✅ Pros & ❌ Cons")
    c1, c2 = st.columns(2)

    # 🔹 Robust formatter that handles strings OR dicts
    def format_bullets(items):
        lines = []
        for item in items:
            if isinstance(item, dict):
                # Gracefully extract the main point regardless of key names
                text = item.get("point") or item.get("0") or " ".join(str(v) for v in item.values())
                lines.append(f"• {text}")
            else:
                lines.append(f"• {item}")
        return "\n".join(lines) or "• None listed"

    c1.markdown(format_bullets(result.get("pros", [])))
    c2.markdown(format_bullets(result.get("cons", [])))

    # 🔍 Debug toggle (uncomment to see raw LLM structure)
    # st.expander("🔍 Debug: Raw JSON Output").json(result)

    # Download
    json_output = json.dumps(result, indent=2)
    st.download_button("💾 Download JSON", json_output, "plugin_copy.json", "application/json")