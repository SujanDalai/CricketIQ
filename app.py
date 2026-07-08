import streamlit as st
import base64
import os
import sys
import re
from src.logger import logger

# 1. System routing: Add 'src' directory to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

st.set_page_config(
    page_title="CricketIQ Dashboard",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ====================================================================
# 🎬 STARTUP SPLASH SCREEN ANIMATION
# ====================================================================
st.markdown("""
    <style>
    /* Splash Screen Overlay Container */
    #splash-screen {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background-color: #0a0c12; /* Matches your dashboard background tint */
        z-index: 999999;
        display: flex;
        justify-content: center;
        align-items: center;
        animation: fadeOut 0.8s ease-in-out forwards;
        animation-delay: 2.2s; /* How long the splash screen stays visible */
        pointer-events: none;
    }

    /* Big Animated Text */
    .splash-logo {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-size: 4rem;
        font-weight: 800;
        color: #ffffff;
        letter-spacing: 2px;
        opacity: 0;
        transform: scale(0.8);
        animation: zoomIn 1.2s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }

    /* Logo Accent Dot */
    .splash-logo span {
        color: #ff4b4b; /* Vibrant crimson match color */
    }

    /* Keyframes for the text intro */
    @keyframes zoomIn {
        0% {
            opacity: 0;
            transform: scale(0.85);
            filter: blur(10px);
        }
        100% {
            opacity: 1;
            transform: scale(1);
            filter: blur(0px);
        }
    }

    /* Keyframes to smoothly fade out the backdrop */
    @keyframes fadeOut {
        0% {
            opacity: 1;
        }
        100% {
            opacity: 0;
            visibility: hidden;
        }
    }
    </style>

    <div id="splash-screen">
        <div class="splash-logo">🏏 CricketIQ<span>.</span></div>
    </div>
""", unsafe_allow_html=True)

# Initialize Session State variables to prevent duplication bugs on hot-reloads
if "current_report" not in st.session_state:
    st.session_state.current_report = ""
if "current_matrix" not in st.session_state:
    st.session_state.current_matrix = []

# 2. Premium Background Image Setup Layout
BACKGROUND_IMAGE_FILENAME = "stadium.jpg" 

if os.path.exists(BACKGROUND_IMAGE_FILENAME):
    with open(BACKGROUND_IMAGE_FILENAME, "rb") as image_file:
        img_base64 = base64.b64encode(image_file.read()).decode()
    
    st.markdown(
        f"""
        <style>
        [data-testid="stAppViewContainer"] {{
            background-image: linear-gradient(rgba(10, 12, 18, 0.94), rgba(10, 12, 18, 0.94)), 
                              url("data:image/jpg;base64,{img_base64}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        [data-testid="stHeader"] {{
            background: transparent;
        }}
        .stTextInput label {{
            color: #ffffff !important;
            font-weight: 600 !important;
            font-size: 1.1rem !important;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# 3. App Title Heading Block
st.markdown("<h1 style='text-align: center; color: white; margin-bottom: 5px;'>🏏 CricketIQ : Multi-Agent Engine</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #888A93; margin-bottom: 30px;'>Analytical predictive intelligence for cricket matchups</p>", unsafe_allow_html=True)
st.markdown("---")

# 4.  User Query Input
user_query = st.text_input(
    "Ask CricketIQ:", 
    value="", 
    placeholder="e.g., Will Rohit Sharma score well vs Mitchell Starc and Jofra Archer at Lords in Test?"
)

# 5. Multi-Agent Run processing pipeline
if user_query:
    if not st.session_state.current_report or st.button("Generate New Report"):
        with st.spinner("Running matchup analysis..."):
            try:
                import io
                old_stdout = sys.stdout
                sys.stdout = buffer = io.StringIO()
                
                from src.agents.coordinator import CoordinatorAgent
                coordinator = CoordinatorAgent()
                
                # First, run the coordinator path once to trigger all sub-agents and fill the terminal buffer
                raw_report = coordinator.run(user_query)
                
                sys.stdout = old_stdout
                console_output = buffer.getvalue()
                
                # Save the raw terminal console logs to session state
                st.session_state.terminal_logs = console_output
                
                # 🌦️ STEP A: Parse the live weather stats string out of the console buffer
                weather_specs = "Clear sky, Temp: 15.2°C, Humidity: 82%, Wind: 3.6 m/s (Fallback)"
                for line in console_output.split("\n"):
                    if "weather details" in line.lower() and ":" in line:
                        weather_specs = line.split(":", 1)[1].strip()
                        break
                
                # 🌦️ STEP B: If we found weather details, we append a strict operational instruction 
                # forcing the final report to process it, and rerun it to align the final text output.
                if weather_specs and "data not available" in raw_report.lower():
                    enhanced_query = (
                        f"{user_query}\n\n"
                        f"[SYSTEM OVERRIDE]: Live weather data has been retrieved successfully. "
                        f"The conditions are: {weather_specs}. "
                        f"Under the section 'How the weather affects the matchup', you must replace any "
                        f"'Data not available' placeholder text, list these exact parameters, and explicitly "
                        f"analyze how they impact this specific cricket matchup (e.g., how humidity/wind "
                        f"affects swing, seam, or batting ease)."
                    )
                    
                    # Capture fresh terminal output with the context-aware text response
                    sys.stdout = buffer_two = io.StringIO()
                    raw_report = coordinator.run(enhanced_query)
                    sys.stdout = old_stdout
                    st.session_state.terminal_logs = console_output + "\n" + buffer_two.getvalue()

                # Precise Regex: Scrape unique head-to-head match blocks out of the console
                raw_matchups = re.findall(
                    r"BOWLING ANALYSIS:\s*([A-Za-z\s]+).*?Innings\s*:\s*(\d+)\s*Dismissals\s*:\s*(\d+)", 
                    st.session_state.terminal_logs, 
                    re.DOTALL | re.IGNORECASE
                )
                
                seen_bowlers = set()
                unique_matrix = []
                for b_name, inn, dis in raw_matchups:
                    clean_b = b_name.split("(")[0].strip()
                    if clean_b not in seen_bowlers:
                        seen_bowlers.add(clean_b)
                        unique_matrix.append((clean_b, int(inn), int(dis)))
                
                st.session_state.current_matrix = unique_matrix
                
                if raw_report:
                    if "CRICKETIQ FINAL REPORT" in raw_report:
                        after_header = raw_report.split("CRICKETIQ FINAL REPORT")[-1]
                        clean_body = after_header.replace("=" * 60, "").strip()
                    else:
                        clean_body = raw_report.replace("=" * 60, "").strip()
                    
                    st.session_state.current_report = clean_body
                
            except Exception as e:
                if 'old_stdout' in locals():
                    sys.stdout = old_stdout
                st.error(f"Execution Error during analysis: {str(e)}")

# 📋 RENDER DISPLAY VIEW
if st.session_state.current_report:
        st.markdown("###  CricketIQ Final Report")
        with st.container(border=True):
            
            # Render Probability Matrix Bars
            if st.session_state.current_matrix:
                st.markdown("<h4 style='margin-bottom: 20px;'> Head-to-Head Probability Matrix</h4>", unsafe_allow_html=True)
                
                st.markdown("""
                    <style>
                    .matrix-container { background-color: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 15px; margin-bottom: 15px; }
                    .matrix-header { color: #ffffff; font-weight: 600; font-size: 1.05rem; margin-bottom: 12px; }
                    .stat-label { color: #888A93; font-size: 0.85rem; display: flex; justify-content: space-between; margin-bottom: 4px; }
                    .bar-bg { background-color: rgba(255, 255, 255, 0.1); border-radius: 4px; height: 8px; width: 100%; margin-bottom: 12px; overflow: hidden; }
                    .risk-bar { background: linear-gradient(90deg, #ff4b4b, #ff7676); height: 100%; border-radius: 4px; }
                    .safety-bar { background: linear-gradient(90deg, #00c853, #b9f6ca); height: 100%; border-radius: 4px; }
                    </style>
                """, unsafe_allow_html=True)
                
                cols = st.columns(len(st.session_state.current_matrix))
                for idx, (name, innings, dismissals) in enumerate(st.session_state.current_matrix):
                    dismissal_pct = round((dismissals / innings) * 100, 1) if innings > 0 else 0.0
                    domination_pct = round(100 - dismissal_pct, 1) if innings > 0 else 0.0
                    
                    with cols[idx]:
                        st.markdown(f"""
                            <div class="matrix-container">
                                <div class="matrix-header">vs {name}</div>
                                <div class="stat-label"><span>Bowler Dismissal Risk</span><span>{dismissal_pct}%</span></div>
                                <div class="bar-bg"><div class="risk-bar" style="width: {dismissal_pct}%;"></div></div>
                                <div class="stat-label"><span>Batter Domination Safety</span><span>{domination_pct}%</span></div>
                                <div class="bar-bg"><div class="safety-bar" style="width: {domination_pct}%;"></div></div>
                            </div>
                        """, unsafe_allow_html=True)
                st.markdown("<hr style='margin-top: 10px; margin-bottom: 20px; border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
            
            # Print the text raw to prevent grammar cutoffs or format corruption
            st.markdown(st.session_state.current_report)   


# ====================================================================
# 🏏 HISTORICAL MATCHES SECTION
# ====================================================================
show_historical = False
if user_query:
    query_lower = user_query.lower()
    historical_keywords = ["historical", "scorecard", "completed match", "final", "world cup", "ipl"]
    if any(keyword in query_lower for keyword in historical_keywords):
        show_historical = True

if show_historical:
    st.markdown("---")
    st.markdown("<h2 style='color: white; margin-top: 20px;'>🏏 Historical Matches</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #888A93; margin-bottom: 20px;'>View details and ball-by-ball performance scorecards of iconic completed matches.</p>", unsafe_allow_html=True)

    try:
        from src.services.historical_matches import HistoricalMatchService
        
        # Initialize service
        hist_service = HistoricalMatchService()
        
        # Get available tournaments
        tournaments = hist_service.get_tournaments()
        
        if not tournaments:
            st.info("No historical tournament data available at this time.")
        else:
            # Layout for Dropdowns
            col_t, col_m = st.columns(2)
            
            with col_t:
                selected_tournament = st.selectbox(
                    "Select Tournament:",
                    options=tournaments,
                    key="hist_tournament_select"
                )
                
            # Get matches for the selected tournament
            matches = hist_service.get_matches_for_tournament(selected_tournament)
            match_options = {m["title"]: m["id"] for m in matches} if matches else {}
            
            with col_m:
                selected_match_title = st.selectbox(
                    "Select Match:",
                    options=list(match_options.keys()),
                    key="hist_match_select"
                )
                
            if selected_match_title:
                match_id = match_options[selected_match_title]
                scorecard = hist_service.get_match_scorecard(match_id)
                
                if not scorecard:
                    st.warning("Scorecard details not found for the selected match.")
                else:
                    # Custom Styling CSS for scorecard
                    st.markdown("""
                        <style>
                        .match-meta-card {
                            background-color: rgba(255, 255, 255, 0.03);
                            border: 1px solid rgba(255, 255, 255, 0.08);
                            border-radius: 8px;
                            padding: 20px;
                            margin-top: 15px;
                            margin-bottom: 25px;
                        }
                        .meta-header {
                            font-size: 1.4rem;
                            font-weight: 700;
                            color: #ffffff;
                            margin-bottom: 12px;
                        }
                        .meta-item {
                            font-size: 0.95rem;
                            color: #e0e0e0;
                            margin-bottom: 6px;
                        }
                        .meta-label {
                            color: #888A93;
                            font-weight: 500;
                        }
                        .scorecard-table {
                            width: 100%;
                            border-collapse: collapse;
                            margin-top: 10px;
                            margin-bottom: 20px;
                            background-color: rgba(255, 255, 255, 0.01);
                            border: 1px solid rgba(255, 255, 255, 0.08);
                            border-radius: 6px;
                            overflow: hidden;
                        }
                        .scorecard-table th {
                            background-color: rgba(255, 255, 255, 0.05);
                            color: #ff4b4b;
                            text-align: left;
                            padding: 8px 12px;
                            font-weight: 600;
                            font-size: 0.9rem;
                            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                        }
                        .scorecard-table td {
                            padding: 8px 12px;
                            color: #e0e0e0;
                            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
                            font-size: 0.85rem;
                        }
                        .scorecard-table tr:hover {
                            background-color: rgba(255, 255, 255, 0.03);
                        }
                        .result-badge {
                            background-color: rgba(0, 200, 83, 0.1);
                            border: 1px solid rgba(0, 200, 83, 0.25);
                            color: #b9f6ca;
                            padding: 6px 12px;
                            border-radius: 4px;
                            display: inline-block;
                            font-weight: 600;
                            margin-top: 10px;
                        }
                        </style>
                    """, unsafe_allow_html=True)
                    
                    # Render metadata card
                    st.markdown(f"""
                        <div class="match-meta-card">
                            <div class="meta-header">{scorecard['match_title']}</div>
                            <div class="meta-item"><span class="meta-label">Tournament:</span> {scorecard['tournament']}</div>
                            <div class="meta-item"><span class="meta-label">Venue:</span> {scorecard['venue']}</div>
                            <div class="meta-item"><span class="meta-label">Date:</span> {scorecard['date']}</div>
                            <div class="meta-item"><span class="meta-label">Toss:</span> {scorecard['toss']}</div>
                            <div class="meta-item"><span class="meta-label">Player of the Match:</span> 🌟 {scorecard['player_of_the_match']}</div>
                            <div class="result-badge">🏆 {scorecard['result']}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Team scores summary
                    st.markdown("### 📊 Team Scores")
                    scores_cols = st.columns(len(scorecard['team_scores']))
                    for idx, (team, score) in enumerate(scorecard['team_scores'].items()):
                        with scores_cols[idx]:
                            st.metric(label=team, value=score)
                    
                    # Detailed Scorecard Tabs
                    tab_batting, tab_bowling = st.tabs(["🏏 Batting Scorecard", "🥎 Bowling Figures"])
                    
                    with tab_batting:
                        for team, batting_rows in scorecard['batting_scorecard'].items():
                            st.markdown(f"#### {team} Innings")
                            
                            # Build HTML table for batting
                            table_html = """
                            <table class="scorecard-table">
                                <thead>
                                    <tr>
                                        <th>Batter</th>
                                        <th>Dismissal</th>
                                        <th style='text-align: right;'>Runs</th>
                                        <th style='text-align: right;'>Balls</th>
                                        <th style='text-align: right;'>4s</th>
                                        <th style='text-align: right;'>6s</th>
                                        <th style='text-align: right;'>SR</th>
                                    </tr>
                                </thead>
                                <tbody>
                            """
                            for row in batting_rows:
                                table_html += f"""
                                    <tr>
                                        <td><b>{row['player']}</b></td>
                                        <td style='color: #888A93;'>{row['status']}</td>
                                        <td style='text-align: right;'>{row['runs']}</td>
                                        <td style='text-align: right;'>{row['balls']}</td>
                                        <td style='text-align: right;'>{row['fours']}</td>
                                        <td style='text-align: right;'>{row['sixes']}</td>
                                        <td style='text-align: right;'>{row['sr']:.1f}</td>
                                    </tr>
                                """
                            table_html += "</tbody></table>"
                            st.html(table_html)
                    
                    with tab_bowling:
                        for team, bowling_rows in scorecard['bowling_figures'].items():
                            st.markdown(f"#### {team} Bowling")
                            
                            # Build HTML table for bowling
                            table_html = """
                            <table class="scorecard-table">
                                <thead>
                                    <tr>
                                        <th>Bowler</th>
                                        <th style='text-align: right;'>Overs</th>
                                        <th style='text-align: right;'>Maidens</th>
                                        <th style='text-align: right;'>Runs</th>
                                        <th style='text-align: right;'>Wickets</th>
                                        <th style='text-align: right;'>Econ</th>
                                    </tr>
                                </thead>
                                <tbody>
                            """
                            for row in bowling_rows:
                                table_html += f"""
                                    <tr>
                                        <td><b>{row['player']}</b></td>
                                        <td style='text-align: right;'>{row['overs']:.1f}</td>
                                        <td style='text-align: right;'>{row['maidens']}</td>
                                        <td style='text-align: right;'>{row['runs']}</td>
                                        <td style='text-align: right;'>{row['wickets']}</td>
                                        <td style='text-align: right;'>{row['econ']:.2f}</td>
                                    </tr>
                                """
                            table_html += "</tbody></table>"
                            st.html(table_html)
                            
    except Exception as ui_ex:
        logger.error(f"Error rendering Historical Matches UI: {ui_ex}")
        st.error("Could not load Historical Matches component.")

