#!/usr/bin/env python3
import os, json, requests, feedparser
from datetime import datetime
from groq import Groq

# Load config
CONFIG = json.load(open("config.json"))
CLIENT = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))

def fetch_items(comp):
    """Fetch latest items from RSS feed with error handling"""
    try:
        feed = feedparser.parse(comp["url"])
        if not feed.entries:
            print(f"⚠️ No entries found for {comp['name']}")
            return []
        
        items = []
        for e in feed.entries[:CONFIG.get("max_items_per_feed", 5)]:
            items.append({
                "title": getattr(e, "title", "No title")[:150],
                "link": getattr(e, "link", ""),
                "published": getattr(e, "published", getattr(e, "updated", "")),
                "summary": getattr(e, "summary", getattr(e, "description", ""))[:200]
            })
        return items
    except Exception as ex:
        print(f"⚠️ Failed to fetch {comp['name']}: {ex}")
        return []

def diff_changes(new_items, old_items):
    """Return items that are new (not in last week's links)"""
    old_links = {i["link"] for i in old_items}
    return [i for i in new_items if i["link"] not in old_links]

def analyze_with_llm(comp_name, changes):
    """Use Groq LLM to analyze changes and return structured JSON"""
    if not changes:
        return []
    
    prompt = f"""You are a product manager analyzing competitor updates.
Analyze these new items from {comp_name}. Return ONLY a valid JSON array (no markdown, no extra text):
[{{
  "change": "Short, specific title of the change",
  "summary": "One sentence explaining what changed",
  "impact": "low|medium|high",
  "action": "One actionable insight for our product team"
}}]

Items to analyze:
{json.dumps(changes, indent=2)}

Rules:
- If content is just a routine post with no strategic change, set impact="low"
- Always cite the link in your reasoning (but output only JSON)
- If you cannot parse the content, return empty array []
"""
    
    try:
        res = CLIENT.chat.completions.create(
            model=CONFIG["llm_model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=600
        )
        raw = res.choices[0].message.content.strip()
        # Clean any markdown wrappers
        for wrapper in ["```json", "```", "`"]:
            raw = raw.replace(wrapper, "")
        raw = raw.strip()
        
        # Try to extract JSON if LLM added extra text
        if "[" in raw and "]" in raw:
            start = raw.find("[")
            end = raw.rfind("]") + 1
            raw = raw[start:end]
        
        result = json.loads(raw)
        return result if isinstance(result, list) else []
    except Exception as e:
        print(f"⚠️ LLM analysis failed for {comp_name}: {e}")
        # Fallback: return raw changes with low impact
        return [{
            "change": c.get("title", "Update"),
            "summary": c.get("summary", "New content detected")[:100],
            "impact": "low",
            "action": f"Review: {c.get('link')}"
        } for c in changes[:2]]

def format_report(analysis_results, date_str):
    """Format final markdown report"""
    lines = [f"# 📊 SEO Competitor Intelligence — Week of {date_str}\n"]
    
    if not analysis_results:
        lines.append("✅ No significant changes detected this week.\n")
        return "\n".join(lines)
    
    for comp_name, insights in analysis_results.items():
        if not insights:
            lines.append(f"### ✅ {comp_name}: No new strategic updates\n")
            continue
        lines.append(f"### 🆕 {comp_name}\n")
        for i, item in enumerate(insights, 1):
            lines.append(f"{i}. **{item.get('change', 'Update')}**")
            lines.append(f"   - 📝 {item.get('summary')}")
            lines.append(f"   - 🎯 Impact: **{item.get('impact', 'N/A').upper()}**")
            lines.append(f"   - 💡 Action: {item.get('action')}")
            lines.append("")
    
    lines.append("---\n*Report generated automatically. Review before sharing.*")
    return "\n".join(lines)

def main():
    if not os.environ.get("GROQ_API_KEY"):
        print("❌ ERROR: GROQ_API_KEY environment variable not set")
        return
    
    # Load last week's state
    last_week = {}
    if os.path.exists("state/last_week.json"):
        try:
            last_week = json.load(open("state/last_week.json"))
        except: pass
    
    os.makedirs("state", exist_ok=True)
    os.makedirs("reports", exist_ok=True)
    
    new_state, analysis_results = {}, {}
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    print(f"🔍 Starting analysis for week of {date_str}...")
    
    for comp in CONFIG["competitors"]:
        print(f"  → Fetching {comp['name']}...")
        items = fetch_items(comp)
        new_state[comp["name"]] = items
        
        old_items = last_week.get(comp["name"], [])
        changes = diff_changes(items, old_items)
        
        if changes:
            print(f"    ✨ Found {len(changes)} new item(s), analyzing...")
            insights = analyze_with_llm(comp["name"], changes)
            analysis_results[comp["name"]] = insights
        else:
            print(f"    ✓ No new items")
            analysis_results[comp["name"]] = []
    
    # Save state for next run
    with open("state/last_week.json", "w") as f:
        json.dump(new_state, f, indent=2)
    
    # Generate & save report
    report_md = format_report(analysis_results, date_str)
    report_path = f"reports/week-{date_str}.md"
    with open(report_path, "w") as f:
        f.write(report_md)
    
    # Also update latest.md for easy viewing
    with open("reports/latest.md", "w") as f:
        f.write(report_md)
    
    print(f"\n✅ Done! Report saved to {report_path}")
    print("\n" + "="*60 + "\n")
    print(report_md)

if __name__ == "__main__":
    main()