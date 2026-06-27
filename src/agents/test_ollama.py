from src.tools.cricket_data import PLAYER_STATS
import ollama
import json

# ---------------------------
# 1. USER QUERY
# ---------------------------
query = "Analyze Virat Kohli's recent performance"

# ---------------------------
# 2. COORDINATOR AGENT
# ---------------------------
def coordinator(query):
    prompt = f"""
You are a cricket AI coordinator.

Your job:
1. Understand the user query
2. Break it into small tasks
3. Return ONLY valid JSON like this:

{{
  "tasks": [
    "batting analysis",
    "form evaluation"
  ]
}}

User Query:
{query}
"""

    response = ollama.chat(
        model="qwen2.5:7b",
        messages=[{"role": "user", "content": prompt}]
    )

    return response["message"]["content"]

# ---------------------------
# 3. WORKER AGENTS
# ---------------------------
def stats_agent(task):
    data = PLAYER_STATS["virat kohli"]["recent_matches"]

    runs = [m["runs"] for m in data]

    avg = sum(runs) / len(runs)

    best = max(runs)
    worst = min(runs)

    odi = [m["runs"] for m in data if m["format"] == "ODI"]
    t20 = [m["runs"] for m in data if m["format"] == "T20"]
    test = [m["runs"] for m in data if m["format"] == "Test"]

    return {
        "runs": runs,
        "average": round(avg, 2),
        "best": best,
        "worst": worst,
        "odi_avg": round(sum(odi)/len(odi), 2) if odi else None,
        "t20_avg": round(sum(t20)/len(t20), 2) if t20 else None,
        "test_avg": round(sum(test)/len(test), 2) if test else None,
    }


def context_agent(task):
    return "Context analysis not required for this demo."

# ---------------------------
# 4. RUN COORDINATOR
# ---------------------------
plan_text = coordinator(query)

print("\n--- COORDINATOR OUTPUT ---\n")
print(plan_text)

# ---------------------------
# 5. PARSE JSON SAFELY
# ---------------------------
try:
    plan = json.loads(plan_text)
except:
    print("\nJSON parsing failed. Using fallback.\n")
    plan = {"tasks": ["batting analysis"]}

# ---------------------------
# 6. AGENT ROUTING (REAL COORDINATION)
# ---------------------------
results = []

for task in plan["tasks"]:
    task_lower = task.lower()

    if "pitch" in task_lower or "condition" in task_lower:
        results.append(context_agent(task))
    else:
        results.append(stats_agent(task))

print("\n--- AGENT OUTPUTS ---\n")
for r in results:
    print(r)

# ---------------------------
# 7. FORM ANALYSIS (FEATURE ENGINEERING)
# ---------------------------
runs = stats_agent("analyze")["runs"]

last_3_avg = sum(runs[-3:]) / 3
first_2_avg = sum(runs[:2]) / 2

if last_3_avg > first_2_avg:
    form = "Improving form"
else:
    form = "Declining form"

avg = stats_agent("analyze")["average"]

if avg > 50:
    rating = "Excellent form"
elif avg > 30:
    rating = "Good form"
else:
    rating = "Poor form"

# ---------------------------
# 8. FINAL LLM REPORT
# ---------------------------
summary_prompt = f"""
You are a senior cricket analyst.

Use the structured data below:

Stats:
{stats_agent("analyze")}

Form Trend:
{form}

Performance Rating:
{rating}

Agent Outputs:
{results}

Rules:
- Do not invent numbers
- Keep under 150 words
- Make it professional and concise
"""

final = ollama.chat(
    model="qwen2.5:7b",
    messages=[{"role": "user", "content": summary_prompt}]
)

print("\n--- FINAL REPORT ---\n")
print(final["message"]["content"])