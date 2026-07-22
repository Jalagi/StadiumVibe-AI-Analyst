import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import google.generativeai as genai
import os
import re
import time
import traceback
from PIL import Image


st.set_page_config(
    page_title="StadiumVibe Elite | Smart Stadium & Tournament Operations AI",
    page_icon="🏟️",
    layout="wide",
    initial_sidebar_state="expanded"
)


st.markdown("""
<style>
    /* Import modern Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Plus+Jakarta+Sans:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    h1, h2, h3, .gradient-header {
        font-family: 'Outfit', sans-serif;
    }

    /* Main Title Styling */
    .title-container {
        padding: 1.5rem 0rem 1rem 0rem;
        text-align: center;
    }
    
    .gradient-title {
        background: linear-gradient(135deg, #3B82F6 0%, #8B5CF6 50%, #EC4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 3.2rem;
        margin-bottom: 0.5rem;
        letter-spacing: -0.05em;
    }
    
    .subtitle {
        color: #94A3B8;
        font-size: 1.2rem;
        font-weight: 400;
    }

    /* Glassmorphic Metrics Card */
    .metric-card {
        background: rgba(30, 41, 59, 0.45);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(139, 92, 246, 0.4);
    }
    
    .metric-val {
        font-size: 2.2rem;
        font-weight: 700;
        color: #F8FAFC;
        margin-bottom: 0.25rem;
        font-family: 'Outfit', sans-serif;
    }
    
    .metric-label {
        font-size: 0.85rem;
        font-weight: 600;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Warning/Status box styling */
    .status-box {
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid rgba(16, 185, 129, 0.2);
        color: #A7F3D0;
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 1.5rem;
    }

    .warning-box {
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.2);
        color: #FCA5A5;
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 1.5rem;
    }
    
    .pulse-dot {
        height: 10px;
        width: 10px;
        background-color: #EF4444;
        border-radius: 50%;
        display: inline-block;
        box-shadow: 0 0 0 0 rgba(239, 68, 68, 1);
        animation: pulse 1.5s infinite;
        margin-right: 8px;
    }

    @keyframes pulse {
        0% {
            transform: scale(0.95);
            box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
        }
        70% {
            transform: scale(1);
            box-shadow: 0 0 0 6px rgba(239, 68, 68, 0);
        }
        100% {
            transform: scale(0.95);
            box-shadow: 0 0 0 0 rgba(239, 68, 68, 0);
        }
    }
    
    /* Highlight Challenge context */
    .challenge-tag {
        display: inline-block;
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, rgba(236, 72, 153, 0.2) 100%);
        border: 1px solid rgba(99, 102, 241, 0.4);
        color: #E2E8F0;
        padding: 0.25rem 0.75rem;
        border-radius: 50px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# --- INITIALIZE SESSION STATE ---
if 'sim_data' not in st.session_state:
    st.session_state.sim_data = None
if 'is_simulating' not in st.session_state:
    st.session_state.is_simulating = False
if 'sim_logs_count' not in st.session_state:
    st.session_state.sim_logs_count = 0

# --- UTILITY: STADIUM SAMPLE DATA GENERATORS ---
def get_stadium_crowd_data():
    np.random.seed(42)
    times = pd.date_range(start="2026-07-12 12:00:00", periods=60, freq="10min")
    gates = ['Gate A (Main)', 'Gate B (East)', 'Gate C (North)', 'Gate D (VIP)']
    
    data = []
    for t in times:
        for gate in gates:
            hour_diff = abs((t.hour + t.minute/60) - 16.0)
            base_flow = max(20, 200 - int(hour_diff * 60))
            flow = max(0, int(np.random.normal(base_flow, 20)))
            wait_time = max(1, int(flow * 0.12 + np.random.normal(3, 1)))
            queue_len = max(0, int(flow * 0.75 + np.random.normal(4, 2)))
            
            data.append({
                'Timestamp': t,
                'Gate_Name': gate,
                'Fan_Flow_Rate_Per_Min': flow,
                'Wait_Time_Minutes': wait_time,
                'Queue_Length': queue_len,
                'Staff_Count': np.random.choice([8, 10, 12, 15])
            })
            
    return pd.DataFrame(data)

def get_concessions_sales():
    np.random.seed(42)
    stands = ['North Deck Eats', 'East Field Bar', 'South Gate Pretzels', 'VIP Lounge Grill']
    items = {
        'Hot Dog': (6.50, 'Food'),
        'Nachos': (7.00, 'Food'),
        'Soft Drink': (4.50, 'Beverage'),
        'Beer': (9.00, 'Beverage'),
        'Souvenir Cup': (12.00, 'Merchandise'),
        'Team Scarf': (25.00, 'Merchandise')
    }
    
    data = []
    times = pd.date_range(start="2026-07-12 13:00:00", periods=100, freq="5min")
    for t in times:
        stand = np.random.choice(stands)
        item = np.random.choice(list(items.keys()))
        price, cat = items[item]
        qty = np.random.randint(1, 15)
        revenue = qty * price
        
        data.append({
            'Timestamp': t,
            'Concession_Stand': stand,
            'Item_Name': item,
            'Category': cat,
            'Price': price,
            'Quantity_Sold': qty,
            'Revenue': round(revenue, 2)
        })
    return pd.DataFrame(data)

def get_security_alerts():
    np.random.seed(42)
    sections = ['Upper Tier A', 'Lower Pitch East', 'Gate B Entry', 'VIP Box 102', 'Concourse South']
    types = ['Crowd Congestion', 'Lost Item', 'Suspicious Activity', 'Medical Assistance', 'Facility Repair']
    statuses = ['Resolved', 'In Progress', 'Dispatched', 'Pending']
    priorities = ['Low', 'Medium', 'High', 'Critical']
    
    data = []
    times = pd.date_range(start="2026-07-12 12:30:00", periods=40, freq="15min")
    for i, t in enumerate(times):
        data.append({
            'Alert_ID': f"ALRT-{1000+i}",
            'Timestamp': t,
            'Location_Section': np.random.choice(sections),
            'Incident_Type': np.random.choice(types),
            'Priority': np.random.choice(priorities, p=[0.4, 0.3, 0.2, 0.1]),
            'Response_Time_Min': np.random.randint(2, 25),
            'Status': np.random.choice(statuses, p=[0.6, 0.2, 0.1, 0.1])
        })
    return pd.DataFrame(data)

# --- SIDEBAR CONFIGURATION ---
st.sidebar.markdown("<h2 style='font-family: Outfit; font-weight: 800; color: #F8FAFC;'>🏟️ StadiumVibe Elite</h2>", unsafe_allow_html=True)

# API Key handling
api_key_env = os.environ.get("GEMINI_API_KEY", "")
api_key_input = st.sidebar.text_input(
    "Enter Gemini API Key", 
    value=api_key_env, 
    type="password", 
    help="Input your Gemini API key from Google AI Studio. Overrides system environment key."
)
api_key = api_key_input

if api_key:
    if api_key == api_key_env:
        st.sidebar.markdown(
            '<div class="status-box">✓ Gemini API Key loaded from system environment.</div>',
            unsafe_allow_html=True
        )
    else:
        st.sidebar.markdown(
            '<div class="status-box">✓ Custom Gemini API Key active.</div>',
            unsafe_allow_html=True
        )


# File Uploader
uploaded_file = st.sidebar.file_uploader("Upload tournament dataset (CSV/Excel)", type=["csv", "xlsx"])

st.sidebar.markdown("<p style='font-size: 0.85rem; font-weight:600; color: #94A3B8; margin-top: 1rem;'>GENERATE SAMPLE DATA:</p>", unsafe_allow_html=True)
# Buttons to generate stadium specific sample datasets
use_crowd = st.sidebar.button("🏟️ Stadium Gate Crowd Flow")
use_sales = st.sidebar.button("🍔 Concessions & Merch Sales")
use_security = st.sidebar.button("🚨 Security & Ops Incidents")

# --- INITIALIZE GEMINI CLIENT ---
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
else:
    model = None

# --- LOAD DATA ---
df = None
data_source = None
dataset_type = ""

# Prioritize simulation state data if active
if st.session_state.is_simulating and st.session_state.sim_data is not None:
    df = st.session_state.sim_data
    data_source = "Live Simulated Match Day Feed"
    dataset_type = "Crowd"
elif uploaded_file is not None:
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        data_source = uploaded_file.name
        dataset_type = "Uploaded File"
        st.session_state.is_simulating = False
    except Exception as e:
        st.error(f"Error loading file: {e}")
elif use_crowd:
    df = get_stadium_crowd_data()
    data_source = "Stadium Gate Crowd Flow (IoT Sensors)"
    dataset_type = "Crowd"
    st.session_state.is_simulating = False
elif use_sales:
    df = get_concessions_sales()
    data_source = "Concessions & Merchandise Sales Performance"
    dataset_type = "Sales"
    st.session_state.is_simulating = False
elif use_security:
    df = get_security_alerts()
    data_source = "Stadium Incident Logs & Security Alerts"
    dataset_type = "Security"
    st.session_state.is_simulating = False

# --- MAIN APP LAYOUT ---
if df is None:
    st.markdown(
        """
        <div class="title-container">
            <div class="challenge-tag">Challenge 4 Showcase: Smart Stadiums & Tournament Operations</div>
            <div class="gradient-title">StadiumVibe Elite</div>
            <div class="subtitle">Generative AI-Powered Stadium Operations & CCTV Visual Analyst</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(
            """
            <div class="metric-card" style="height: 280px;">
                <div style="font-size: 2.5rem; margin-bottom: 1rem;">📊</div>
                <div class="metric-label" style="font-size: 1.1rem; color: #F8FAFC; margin-bottom: 0.5rem;">Interactive Operations Feed</div>
                <p style="color: #94A3B8; font-size: 0.95rem;">Track fan flow rates, entry wait times, and queue lengths across major gates. Execute complex data visualization in seconds via plain text.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
    with col2:
        st.markdown(
            """
            <div class="metric-card" style="height: 280px;">
                <div style="font-size: 2.5rem; margin-bottom: 1rem;">📸</div>
                <div class="metric-label" style="font-size: 1.1rem; color: #F8FAFC; margin-bottom: 0.5rem;">CCTV Visual AI Analyst</div>
                <p style="color: #94A3B8; font-size: 0.95rem;">Upload real-time images or screenshots from stadium cams. Gemini analyzes crowd crowd density, debris, or security risks instantly.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
    with col3:
        st.markdown(
            """
            <div class="metric-card" style="height: 280px;">
                <div style="font-size: 2.5rem; margin-bottom: 1rem;">🚨</div>
                <div class="metric-label" style="font-size: 1.1rem; color: #F8FAFC; margin-bottom: 0.5rem;">Operations Command Room</div>
                <p style="color: #94A3B8; font-size: 0.95rem;">Real-time critical warning board with automatically generated statistical updates, live data simulation, and self-healing AI logic.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.info("👈 Choose a tournament sample dataset in the sidebar, or upload your own CSV/Excel operations file to get started!")
    
    if not api_key:
        st.markdown(
            '<div class="warning-box">⚠️ <b>API Key Missing:</b> Please configure your <code>GEMINI_API_KEY</code> environment variable or enter it in the sidebar setup to unlock all AI capabilities.</div>',
            unsafe_allow_html=True
        )

else:
    # App Header
    st.markdown(
        f"""
        <div class="title-container" style="padding-top: 0.5rem; padding-bottom: 0.5rem;">
            <div class="challenge-tag">Smart Stadium Operations Control Room</div>
            <div class="gradient-title" style="font-size: 2.5rem; margin-bottom: 0rem;">StadiumVibe Elite Console</div>
            <div class="subtitle">Operational Target: <b>{data_source}</b></div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Real-Time Simulation Panel
    sim_col1, sim_col2 = st.columns([3, 1])
    with sim_col1:
        if st.session_state.is_simulating:
            st.markdown(
                '<div style="display:flex; align-items:center; margin-bottom:1rem;"><span class="pulse-dot"></span><b style="color: #F8FAFC;">LIVE SIMULATION RUNNING: Appending live match-day telemetry feed...</b></div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown("<div style='margin-bottom:1rem; color:#94A3B8;'>Telemetry Mode: Static Feed (Switch to Live Simulation on the right)</div>", unsafe_allow_html=True)
            
    with sim_col2:
        if not st.session_state.is_simulating:
            if st.button("▶ Run Live Match Simulation", use_container_width=True):
                st.session_state.is_simulating = True
                st.session_state.sim_data = get_stadium_crowd_data()
                st.session_state.sim_logs_count = len(st.session_state.sim_data)
                st.rerun()
        else:
            if st.button("⏹ Stop Live Simulation", use_container_width=True):
                st.session_state.is_simulating = False
                st.rerun()

    # Dynamic Streaming loop
    if st.session_state.is_simulating:
        # Append a new batch of simulated rows to the session state
        np.random.seed(int(time.time()))
        new_time = st.session_state.sim_data['Timestamp'].max() + pd.Timedelta(minutes=10)
        gates = ['Gate A (Main)', 'Gate B (East)', 'Gate C (North)', 'Gate D (VIP)']
        new_rows = []
        for gate in gates:
            flow = max(0, int(np.random.normal(150, 30)))
            wait = max(1, int(flow * 0.15 + np.random.normal(5, 2)))
            queue = max(0, int(flow * 0.8 + np.random.normal(6, 3)))
            new_rows.append({
                'Timestamp': new_time,
                'Gate_Name': gate,
                'Fan_Flow_Rate_Per_Min': flow,
                'Wait_Time_Minutes': wait,
                'Queue_Length': queue,
                'Staff_Count': np.random.choice([8, 10, 12, 15])
            })
        st.session_state.sim_data = pd.concat([st.session_state.sim_data, pd.DataFrame(new_rows)], ignore_index=True)
        df = st.session_state.sim_data
        time.sleep(1) # Live updates every second

    # Grid Metrics Dashboard Row
    num_rows, num_cols = df.shape
    num_numeric = len(df.select_dtypes(include=[np.number]).columns)
    missing_cells = df.isnull().sum().sum()
    total_cells = df.size
    missing_percentage = (missing_cells / total_cells * 100) if total_cells > 0 else 0
    
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    with m_col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val">{num_rows:,}</div>
            <div class="metric-label">Data Points</div>
        </div>
        """, unsafe_allow_html=True)
    with m_col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val">{num_cols}</div>
            <div class="metric-label">Operational Dimensions</div>
        </div>
        """, unsafe_allow_html=True)
    with m_col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val">{num_numeric}</div>
            <div class="metric-label">Numeric Metrics</div>
        </div>
        """, unsafe_allow_html=True)
    with m_col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val">{missing_percentage:.1f}%</div>
            <div class="metric-label">Incomplete Records</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Workspace tabs
    tab_preview, tab_insights, tab_chat, tab_alerts, tab_cctv = st.tabs([
        "📋 Operations Feed", 
        "✨ AI Operations Briefing", 
        "💬 Operations Command Chat",
        "🚨 Incident Alert Room",
        "📸 CCTV Visual Analyst"
    ])
    
    # TAB 1: OPERATIONS FEED
    with tab_preview:
        col_preview, col_types = st.columns([3, 1])
        with col_preview:
            st.markdown("<h4 style='font-family: Outfit; color: #F8FAFC;'>Real-Time Data Feed</h4>", unsafe_allow_html=True)
            st.dataframe(df.tail(20), use_container_width=True)
            
        with col_types:
            st.markdown("<h4 style='font-family: Outfit; color: #F8FAFC;'>Metrics Schema</h4>", unsafe_allow_html=True)
            dtypes_df = pd.DataFrame(df.dtypes, columns=["Type"]).astype(str)
            st.dataframe(dtypes_df, use_container_width=True)
            
        st.markdown("<h4 style='font-family: Outfit; color: #F8FAFC;'>Operational Summary Statistics</h4>", unsafe_allow_html=True)
        st.dataframe(df.describe(include='all').fillna('-'), use_container_width=True)
        
    # TAB 2: AI OPERATIONS BRIEFING
    with tab_insights:
        st.markdown("<h4 style='font-family: Outfit; color: #F8FAFC;'>AI-Generated Operations Report</h4>", unsafe_allow_html=True)
        
        if not model:
            st.warning("Please configure your Gemini API Key in the sidebar to generate operational briefings.")
        else:
            @st.cache_data(show_spinner=False)
            def generate_ops_briefing(columns_info, head_json, row_count, col_count, source_name):
                prompt = f"""
                You are a Senior Tournament Operations Director for a FIFA World Cup stadium.
                You are analyzing stadium operations data named "{source_name}" containing {row_count} rows and {col_count} columns.
                The schema of the data is:
                {columns_info}
                
                Here is a preview of the latest records:
                {head_json}
                
                Please write a comprehensive, professional Smart Stadium briefing:
                1. **Operational Focus:** What specific stadium management domain (crowd control, concessions, safety) does this dataset represent and why is it critical for tournament logistics?
                2. **AI Analysis & Alerts:** Highlight 3 key insights, patterns, or potential operational risks (e.g. queue delays, revenue drops, high response times) visible in this dataset structure.
                3. **Recommended Operations Queries:** Suggest 3 analytical questions that the onsite operations team should ask (which can be typed into the chat interface) to investigate further.
                
                Format your response using bold headings, concise bullet points, and high-impact stadium operational terminology.
                """
                try:
                    response = model.generate_content(prompt)
                    return response.text
                except Exception as ex:
                    return f"Error communicating with Gemini: {ex}"
            
            with st.spinner("Gemini is analyzing tournament metrics..."):
                columns_info = str(df.dtypes.to_dict())
                head_json = df.head(3).to_json(orient='records')
                insights = generate_ops_briefing(columns_info, head_json, num_rows, num_cols, data_source)
                st.markdown(insights)
                
    # TAB 3: OPERATIONS COMMAND CHAT
    with tab_chat:
        st.markdown("<h4 style='font-family: Outfit; color: #F8FAFC;'>Ask the Stadium Operations Command Agent</h4>", unsafe_allow_html=True)
        
        if not model:
            st.warning("Please configure your Gemini API Key in the sidebar to chat with the data.")
        else:
            st.markdown("<p style='font-size: 0.9rem; color: #94A3B8;'>Quick Queries:</p>", unsafe_allow_html=True)
            
            # Suggest queries dynamically based on the dataset type
            if dataset_type == "Crowd":
                default_queries = [
                    "Plot average Fan Flow Rate over time for each Gate Name to find peak entry times.",
                    "Show queue length vs wait time as a scatter plot colored by Gate Name.",
                    "Determine which Gate has the highest average wait time and suggest staffing adjustments."
                ]
            elif dataset_type == "Sales":
                default_queries = [
                    "Plot cumulative Concessions Revenue over time grouped by Item Category.",
                    "Compare total quantity sold for each Item Name using a bar chart.",
                    "Identify the highest-revenue concession stand and show its top selling items."
                ]
            elif dataset_type == "Security":
                default_queries = [
                    "Plot the count of incident types by Priority level using a bar chart.",
                    "Show average Incident Response Time over time for different Location Sections.",
                    "Analyze which Locations have unresolved incidents and list them."
                ]
            else:
                default_queries = [
                    "Generate a correlation heatmap of numerical columns.",
                    "Plot numerical columns against time if timestamps exist, or show their distributions.",
                    "What are the main outliers in this dataset? Show them in a chart."
                ]
            
            btn_col1, btn_col2, btn_col3 = st.columns(3)
            with btn_col1:
                if st.button(default_queries[0], key="q1", use_container_width=True):
                    st.session_state.chat_input = default_queries[0]
            with btn_col2:
                if st.button(default_queries[1], key="q2", use_container_width=True):
                    st.session_state.chat_input = default_queries[1]
            with btn_col3:
                if st.button(default_queries[2], key="q3", use_container_width=True):
                    st.session_state.chat_input = default_queries[2]
            
            # Chat input text box
            user_query = st.chat_input("Ask StadiumVibe to visualize or analyze...")
            
            # Use query from click or manual input
            active_query = user_query
            if 'chat_input' in st.session_state and st.session_state.chat_input:
                active_query = st.session_state.chat_input
                st.session_state.chat_input = None # reset
                
            if active_query:
                st.info(f"Analyzing: **{active_query}**")
                
                with st.spinner("Operations Agent is calculating & plotting..."):
                    prompt = f"""
                    You are StadiumVibe, a Tournament Operations AI Analyst. You are given a pandas DataFrame named `df` containing Smart Stadium data:
                    Schema: {df.dtypes.to_dict()}
                    First 3 rows: {df.head(3).to_dict()}
                    
                    The Operations Director wants to execute this analysis: "{active_query}"
                    
                    Your instructions:
                    1. Write Python code using pandas and plotly.express (or plotly.graph_objects) to build the requested visualization.
                       - Define a variable named `fig` which holds the Plotly Figure object.
                       - DO NOT use st.write, st.plotly_chart, fig.show() or plt.show() inside the code block. Just create the `fig` object.
                       - Use a modern dark theme and vibrant colors (e.g. blue, purple, magenta, emerald) for the chart.
                    2. Write a concise, bulleted operational summary explaining what this chart reveals to the command team.
                    
                    Your output must match this exact format. Do not add any text before or after the code block:
                    
                    ```python
                    # Write only python code here.
                    # It must define a figure object named `fig`
                    ```
                    ---EXPLANATION---
                    Write a concise operational explanation of what this chart reveals and recommendations for stadium management.
                    """
                    
                    try:
                        response = model.generate_content(prompt)
                        result = response.text
                        
                        # Parse the code and the explanation
                        code_pattern = r"```python(.*?)```"
                        code_match = re.search(code_pattern, result, re.DOTALL)
                        
                        explanation = ""
                        if "---EXPLANATION---" in result:
                            explanation = result.split("---EXPLANATION---")[1].strip()
                        else:
                            explanation = re.sub(code_pattern, "", result, flags=re.DOTALL).strip()
                            
                        if code_match:
                            extracted_code = code_match.group(1).strip()
                            
                            local_vars = {
                                'df': df,
                                'pd': pd,
                                'np': np,
                                'px': px,
                                'go': go
                            }
                            
                            try:
                                # Execute the python code generated by the LLM
                                exec(extracted_code, globals(), local_vars)
                                
                                if 'fig' in local_vars:
                                    st.plotly_chart(local_vars['fig'], use_container_width=True)
                                else:
                                    st.error("The code ran successfully but did not define a variable named `fig`.")
                                    
                                with st.expander("🛠️ View generated Python/Plotly code"):
                                    st.code(extracted_code, language='python')
                                    
                                if explanation:
                                    st.markdown("<h5 style='font-family: Outfit; color: #F8FAFC;'>Operational Decision Support:</h5>", unsafe_allow_html=True)
                                    st.markdown(explanation)
                                    
                            except Exception as exec_err:
                                st.warning("⚠️ Initial code failed. Activating AI Self-Healing mechanism...")
                                
                                # AI Self-Healing Attempt
                                healing_prompt = f"""
                                The code you generated previously failed with the following traceback:
                                {traceback.format_exc()}
                                
                                Original instruction: "{active_query}"
                                Original generated code:
                                {extracted_code}
                                
                                Please fix the code so it works perfectly. Remember:
                                1. It MUST define a plotly figure named `fig`.
                                2. DO NOT write `st.write` or `st.plotly_chart` in the code.
                                
                                Return the corrected python code block only.
                                """
                                try:
                                    healed_response = model.generate_content(healing_prompt)
                                    healed_code_match = re.search(code_pattern, healed_response.text, re.DOTALL)
                                    if healed_code_match:
                                        healed_code = healed_code_match.group(1).strip()
                                        
                                        # Retry execution
                                        exec(healed_code, globals(), local_vars)
                                        if 'fig' in local_vars:
                                            st.plotly_chart(local_vars['fig'], use_container_width=True)
                                            st.success("✓ Code self-healed successfully!")
                                            with st.expander("🛠️ View healed Python code"):
                                                st.code(healed_code, language='python')
                                        else:
                                            st.error("Self-healing failed: Code ran but 'fig' variable not found.")
                                    else:
                                        st.error("Self-healing failed: Corrected code block could not be parsed.")
                                except Exception as heal_fail:
                                    st.error(f"AI Self-Healing crashed: {heal_fail}")
                        else:
                            st.error("Gemini failed to output a code block. Please try again.")
                            st.write(result)
                            
                    except Exception as gen_err:
                        st.error(f"Error calling Gemini API: {gen_err}")

    # TAB 4: INCIDENT ALERT ROOM
    with tab_alerts:
        st.markdown("<h4 style='font-family: Outfit; color: #F8FAFC;'>Active Operational Alerts Board</h4>", unsafe_allow_html=True)
        
        # Scrape data to find critical thresholds
        active_warnings = []
        
        # Check Gate Wait times
        if 'Wait_Time_Minutes' in df.columns:
            gate_overload = df[df['Wait_Time_Minutes'] > 20]
            for idx, row in gate_overload.tail(3).iterrows():
                active_warnings.append({
                    'Level': 'Critical' if row['Wait_Time_Minutes'] > 30 else 'High',
                    'Message': f"Gate wait time at {row['Gate_Name']} is at {row['Wait_Time_Minutes']} minutes (Flow rate: {row['Fan_Flow_Rate_Per_Min']}/min)",
                    'Type': 'Crowd'
                })
                
        # Check Security incident urgency
        if 'Priority' in df.columns:
            critical_incidents = df[df['Priority'].isin(['High', 'Critical'])]
            for idx, row in critical_incidents.tail(3).iterrows():
                active_warnings.append({
                    'Level': row['Priority'],
                    'Message': f"Active Incident logged in {row['Location_Section']}: {row['Incident_Type']} (Status: {row['Status']})",
                    'Type': 'Security'
                })
                
        if not active_warnings:
            st.success("✓ All systems clear. No critical alarms or wait times detected across the tournament zones.")
        else:
            for alert in active_warnings:
                badge_style = "background-color: #EF4444; color: white;" if alert['Level'] in ['Critical', 'High'] else "background-color: #F59E0B; color: black;"
                st.markdown(
                    f"""
                    <div style="border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 1rem; margin-bottom: 0.75rem; background: rgba(30, 41, 59, 0.3);">
                        <span style="padding: 0.2rem 0.5rem; border-radius: 6px; font-size: 0.8rem; font-weight:700; {badge_style}">{alert['Level'].upper()}</span>
                        <span style="color: #F8FAFC; margin-left: 10px; font-size: 0.95rem;">{alert['Message']}</span>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
            
            # Use Gemini to give a mitigation advice
            if model:
                st.markdown("<br><h5 style='font-family: Outfit; color: #F8FAFC;'>AI Commander Recommendation:</h5>", unsafe_allow_html=True)
                @st.cache_data(show_spinner=False)
                def get_ops_mitigation(alerts_summary):
                    prompt = f"""
                    You are the Incident Commander for a FIFA Stadium. We have the following active alarms logged in our operations center:
                    {alerts_summary}
                    
                    Please write a 2-3 sentence mitigation strategy outlining resource redeployment (e.g. staff movement, police dispatch, gate redirection) to resolve these issues. Keep it extremely brief and actionable.
                    """
                    try:
                        return model.generate_content(prompt).text
                    except Exception as e:
                        return f"Failed to get AI recommendation: {e}"
                
                alerts_summary = "\n".join([a['Message'] for a in active_warnings])
                mitigation_text = get_ops_mitigation(alerts_summary)
                st.info(mitigation_text)

    # TAB 5: CCTV VISUAL ANALYST
    with tab_cctv:
        st.markdown("<h4 style='font-family: Outfit; color: #F8FAFC;'>CCTV Vision AI Incident Reporter</h4>", unsafe_allow_html=True)
        st.markdown("<p style='color: #94A3B8; font-size:0.9rem;'>Upload camera footage screenshots (crowd build-up, debris on the pitch, structural issues) and let the AI analyze threat levels.</p>", unsafe_allow_html=True)
        
        cctv_file = st.file_uploader("Upload CCTV Screenshot", type=["jpg", "jpeg", "png"])
        
        if cctv_file is not None:
            col_img, col_report = st.columns([1, 1])
            with col_img:
                image = Image.open(cctv_file)
                st.image(image, caption="CCTV Uploaded Feed", use_container_width=True)
                
            with col_report:
                st.markdown("<h5 style='font-family: Outfit; color: #F8FAFC;'>AI Visual Analysis Ticket</h5>", unsafe_allow_html=True)
                if not model:
                    st.warning("Please configure your Gemini API Key in the sidebar.")
                else:
                    with st.spinner("AI Vision is inspecting the image..."):
                        vision_prompt = """
                        You are a Smart Stadium Vision AI Security agent. You are looking at a CCTV feed screenshot.
                        Analyze this image and output an Incident Ticket containing:
                        1. **Incident Title:** (Brief description of what is seen in the image)
                        2. **Estimated Risk Level:** (Low, Medium, High, Critical with reason)
                        3. **Crowd Estimate:** (Approximate count or density description: sparse, moderate, heavy, gridlocked)
                        4. **Suggested Immediate Action:** (What should the security team or onsite stewards do right now to handle this situation?)
                        
                        Keep the ticket concise, formal, and structured.
                        """
                        try:
                            # Send image and prompt to Gemini
                            response = model.generate_content([vision_prompt, image])
                            st.markdown(response.text)
                            st.success("✓ CCTV Incident Report Logged in Database.")
                        except Exception as vision_err:
                            st.error(f"Vision API error: {vision_err}")
