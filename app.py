import streamlit as st
from logic import predict_log

# Page Configuration
st.set_page_config(page_title="Log-Guard AI", page_icon="🛡️", layout="centered")

# Custom CSS to make the UI pop
st.markdown("""
    <style>
    .main {
        background-color: #f5f7f9;
    }
    .stTextArea textarea {
        font-family: monospace;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Log-Guard: Hybrid Classifier")
st.markdown("""
    Paste your system logs below. This tool uses **Regex** for known patterns 
    and **AI** (Sentence Transformers) for complex anomalies.
""")

# Input Area
user_log = st.text_area("Log Message:", placeholder="e.g., 192.168.1.1 - Database connection failed", height=150)

if st.button("Analyze Log", type="primary"):
    if user_log.strip():
        with st.spinner("Classifying log entry..."):
            # Call our combined logic
            result, method = predict_log(user_log)
            
            st.divider()
            
            # --- COLOR CODED RESULTS ---
            if result == "Security Alert":
                st.error(f"### 🚨 Result: **{result}**")
                st.toast("Security Threat Detected!", icon="🛡️")
            
            elif result == "Critical Error":
                st.error(f"### 🛑 Result: **{result}**")
                st.toast("System Failure Detected!", icon="🔥")
                
            elif result in ["Resource Warning", "Network Issue", "Web Error"]:
                st.warning(f"### ⚠️ Result: **{result}**")
            
            elif result == "Unknown":
                st.info(f"### 🔍 Result: **{result}**")
            
            elif "Error" in result:
                st.error(f"### ❌ {result}")
            
            else:
                # For User Action, System Notification, Web Success
                st.success(f"### ✅ Result: **{result}**")

            # Display the source of the decision
            st.info(f"**Classification Method:** {method}")
            
    else:
        st.warning("Please enter a log message first.")

st.divider()
st.caption("🛡️ Log-Guard Project v1.2 | Hybrid Regex-AI Engine")