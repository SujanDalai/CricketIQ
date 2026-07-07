# 🏏 CricketIQ — AI-Powered Cricket Match Analysis using LangGraph

CricketIQ is a **multi-agent AI system** that analyzes cricket players, predicts batter vs bowler matchups, and generates explainable insights using real-world cricket statistics.

Instead of relying on a single LLM prompt, CricketIQ uses **LangGraph** to orchestrate specialized AI agents that collaborate to produce a structured cricket analysis.

---

## ✨ Features

* 🤖 Multi-Agent AI Architecture using LangGraph
* 🏏 Batter vs Bowler matchup prediction
* 📊 Statistical probability model (Python-based)
* 🌦 Venue and weather-aware analysis
* 📈 Recent player form analysis
* ⚡ CricAPI integration with caching
* 🧠 LLM-generated expert explanations
* 📄 Structured JSON output for future frontend integration

---

# Example Query

```text
Virat Kohli vs Jasprit Bumrah at Wankhede Stadium
```

Example Output

```text
PLAYER MATCHUP PREDICTION

Batter: Virat Kohli
Bowler: Jasprit Bumrah
Venue: Wankhede Stadium

Batting Dominance
████████░░ 54%

Dismissal Chance
███████░░░ 46%

Confidence
High

Expert Verdict
Virat Kohli has a slight statistical edge due to his recent form and outstanding career average, while Bumrah remains a major wicket-taking threat.
```

---

# Project Architecture

```
                  User Query
                      │
                      ▼
               Supervisor Agent
                      │
      ┌───────────────┼───────────────┐
      ▼               ▼               ▼
 CricketAgent   BowlerAgent    WeatherAgent
      │               │
      └───────────────┬───────────────┘
                      ▼
              MatchupAgent
                      ▼
         MatchupPredictorAgent
                      ▼
                Aggregator
                      ▼
              Final AI Report
```

Each agent has a dedicated responsibility.

* **Supervisor** → Parses user intent and routes tasks
* **CricketAgent** → Batter analysis
* **BowlerAgent** → Bowler analysis
* **WeatherAgent** → Venue and weather context
* **MatchupAgent** → Combines cricket insights
* **MatchupPredictorAgent** → Computes statistical probabilities
* **Aggregator** → Produces the final report

---

# Tech Stack

* Python
* LangGraph
* LangChain
* Groq API
* CricAPI
* Weather API
* Requests
* AsyncIO

---

# Statistical Prediction Model

Unlike prompt-only cricket assistants, CricketIQ computes probabilities using a deterministic statistical model before passing them to the LLM.

Inputs include:

* Batting Average
* Strike Rate
* Bowling Average
* Economy Rate
* Bowling Strike Rate
* Recent Form
* Venue Effects
* Weather Conditions

The LLM explains the prediction but does **not** invent probabilities.

---

# Repository Structure

```
src/
│
├── agents/
├── graph/
├── tools/
├── models/
├── utils/
├── prompts/
├── main.py
│
cache/
│
data/
│
README.md
```

---

# Installation

Clone the repository

```bash
git clone <repository-url>
cd CricketIQ
```

Create a virtual environment

```bash
python -m venv .venv
```

Activate it

Windows

```bash
.venv\Scripts\activate
```

Linux/macOS

```bash
source .venv/bin/activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

Create a `.env` file

```env
GROQ_API_KEY=your_key
CRIC_API_KEY=your_key
WEATHER_API_KEY=your_key
```

Run

```bash
python -m src.main
```

---

# Sample Queries

```text
Virat Kohli

Jasprit Bumrah

Virat Kohli vs Jasprit Bumrah

David Warner vs Mitchell Starc

Kane Williamson vs Trent Boult at Lord's

Today's live matches

Upcoming matches
```

---

# Future Improvements

* Head-to-head player records
* Expected Runs model
* Expected Wickets model
* Streamlit dashboard
* FastAPI backend
* Player comparison charts
* IPL-specific analytics
* Win probability engine

---

# Why This Project?

Most cricket chatbots rely entirely on LLM reasoning.

CricketIQ combines:

* Real cricket statistics
* Deterministic statistical modeling
* Multi-agent orchestration
* Explainable AI

This results in analyses that are more structured, transparent, and reproducible.

---

# Author

Built by **Sujan** as a portfolio project exploring:

* Multi-Agent AI Systems
* LangGraph
* Sports Analytics
* Explainable AI
* LLM Engineering
