import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection 

# ==========================================
# --- PAGE CONFIGURATION ---
# ==========================================
st.set_page_config(page_title="Lab Asset Dashboard", layout="wide")


# ==========================================
# --- SECURE GSHEETS CONNECTION LAYER ---
# ==========================================

# 1. Safely extract raw connection configurations out of the immutable TOML wrapper
raw_config = dict(st.secrets["connections"]["gsheets"])

# 2. Force evaluate escaped character literals into structural newlines for RSA verification
if "private_key" in raw_config:
    raw_config["private_key"] = raw_config["private_key"].replace("\\n", "\n")

# 3. Instantiate the connection class directly, avoiding fragile factory wrapper routing
conn = GSheetsConnection(connection_name="gsheets", secrets=raw_config)

# Define master spreadsheet URL explicitly
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1vN4IFkM2xlzA0G8oLV6yWo_sD9unOq_j8dYUP0wQMxg/"


@st.cache_data(ttl=60)
def load_live_data():
    # Pass the SPREADSHEET_URL parameter directly into the connection instance
    df_inv = conn.read(spreadsheet=SPREADSHEET_URL, worksheet="Sheet1")
    df_tok = conn.read(spreadsheet=SPREADSHEET_URL, worksheet="AccessTokens")
    return df_inv, df_tok

with st.spinner("Authenticating live connection..."):
    df_inventory, df_tokens = load_live_data()

# Clean up dataframes
df_inventory.fillna("Unknown", inplace=True)
df_tokens.fillna("Unknown", inplace=True)
df_inventory.columns = df_inventory.columns.str.strip().str.lower()
df_tokens.columns = df_tokens.columns.str.strip().str.lower()


# ==========================================
# --- URL TOKEN VALIDATION LAYER ---
# ==========================================
url_params = st.query_params

if "token" not in url_params:
    st.error("🔒 Access Denied: A valid authorization token is required.")
    st.stop()

user_token = str(url_params["token"]).strip()
matching_row = df_tokens[df_tokens["secure_token"].astype(str).str.strip() == user_token]

if matching_row.empty:
    st.error("❌ Invalid or Expired Authorization Token.")
    st.stop()

authorized_room = matching_row.iloc[0]["location_tag"]


# ==========================================
# --- APP UI & READ/EDIT CONTAINER ---
# ==========================================
st.title("🧪 SC Live Lab Asset Management Dashboard")
st.caption(f"Secure session active for Room: **{authorized_room}**")
st.markdown("---")

# Isolate items for this room only
filtered_df = df_inventory[df_inventory["room_tag"] == authorized_room]

# Metrics
col1, col2 = st.columns(2)
with col1:
    st.metric(label="Total Tracked Assets", value=len(filtered_df))
with col2:
    st.metric(label="Distinct Manufacturers", value=filtered_df["manufacturer"].nunique())

st.markdown("---")
st.subheader(f"📋 Asset Inventory List — Room {authorized_room}")
st.caption("💡 Double-click any cell to edit details directly. Click 'Save Table Changes' below to update the live spreadsheet.")

# Render the interactive spreadsheet editor widget
edited_df = st.data_editor(
    filtered_df, 
    use_container_width=True,
    disabled=["room_tag", "timestamp"], 
    key="inventory_editor"
)

# Save Button for Cell Changes
if st.button("💾 Save Table Changes"):
    with st.spinner("Syncing your updates to the live master matrix..."):
        # Pull absolute latest copy from Google Sheets to ensure no cross-room data drops
        df_latest_master, _ = load_live_data()
        df_latest_master.fillna("Unknown", inplace=True)
        df_latest_master.columns = df_latest_master.columns.str.strip().str.lower()
        
        # Pull out rows belonging to OTHER rooms to preserve them
        other_rooms_df = df_latest_master[df_latest_master["room_tag"] != authorized_room]
        
        # Merge untouched room rows with your newly modified room rows
        final_updated_master = pd.concat([other_rooms_df, edited_df], ignore_index=True)
        
        # Force column formatting alignment before push
        final_updated_master = final_updated_master[df_inventory.columns]
        
        # Overwrite the spreadsheet cleanly via secure API execution
        conn.update(spreadsheet=SPREADSHEET_URL, worksheet="Sheet1", data=final_updated_master)
        
        st.success("Table changes successfully synchronized!")
        st.cache_data.clear() # Erase data view cache
        st.rerun()            # Hard reload application UI


# ==========================================
# --- SECURE WRITE-BACK DATA LAYER ---
# ==========================================
st.markdown("---")
with st.expander("➕ Add New Asset to this Room"):
    with st.form("new_asset_form", clear_on_submit=True):
        st.write("Logged assets are automatically tagged to your current authorized space.")
        
        # User
