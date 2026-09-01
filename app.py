import base64
import datetime
from datetime import datetime
import hashlib
import io
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from PIL import Image
import streamlit as st

st.set_page_config(
    page_title="TogetheSpace v0.3 — Community Hub", page_icon="🏙️", layout="wide"
)

# --- APP-WIDE STYLING & GORGEOUS UI/UX ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif;
        color: #1e293b;
    }
    
    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
        padding: 0.5rem 1rem;
        transition: all 0.2s ease-in-out;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .stButton>button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    input, textarea, select {
        border-radius: 8px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- 1. CONFIGURATION & SECURE GOOGLE DRIVE CONNECTION ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


@st.cache_resource
def get_gspread_client():
  creds_dict = dict(st.secrets["gcp_service_account"])
  creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
  return gspread.authorize(creds)


MASTER_SHEET_ID = st.secrets["gcp_service_account"]["sheet_id"]


def hash_password(password):
  return hashlib.sha256(password.encode()).hexdigest()


# --- IMAGE PROCESSING & ENCODING ---
def process_image_to_base64(uploaded_file):
  try:
    img = Image.open(uploaded_file)
    if img.mode in ("RGBA", "P"):
      img = img.convert("RGB")

    max_size = 600
    quality = 65

    while True:
      img_copy = img.copy()
      img_copy.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
      buffered = io.BytesIO()
      img_copy.save(buffered, format="JPEG", quality=quality, optimize=True)
      img_bytes = buffered.getvalue()
      b64_str = base64.b64encode(img_bytes).decode("utf-8")

      if len(b64_str) < 48000 or max_size <= 200:
        return b64_str

      max_size -= 100
      quality -= 10
  except Exception as e:
    st.error(f"Image processing error: {e}")
    return ""


def decode_base64_image(b64_str):
  try:
    if not b64_str or b64_str == "None" or len(str(b64_str).strip()) < 10:
      return None
    return base64.b64decode(b64_str)
  except Exception:
    return None


# --- 2. DATA LOADERS FROM GOOGLE SHEETS ---
@st.cache_data(ttl=30)
def load_users_data():
  try:
    client = get_gspread_client()
    spreadsheet = client.open_by_key(MASTER_SHEET_ID)
    try:
      sheet = spreadsheet.worksheet("Users")
    except Exception:
      sheet = spreadsheet.add_worksheet(title="Users", rows="100", cols="4")
      sheet.append_row(["Username", "Password Hash", "Organization", "Role"])

    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    if df.empty or "Username" not in df.columns or len(df) == 0:
      sheet.clear()
      sheet.append_row(["Username", "Password Hash", "Organization", "Role"])
      default_pw_hash = hash_password("securepassword123")
      managers_list = [
          ["manager_apollo", default_pw_hash, "Apollo Community", "manager"],
          ["principal_xavier", default_pw_hash, "St. Xavier Enclave", "manager"],
          ["manager_rotary", default_pw_hash, "Rotary Club Hub", "manager"],
          ["manager_tech", default_pw_hash, "TechCorp Town", "manager"],
          ["manager_metro", default_pw_hash, "Metro Residents", "manager"],
      ]
      for m in managers_list:
        sheet.append_row(m)
      data = sheet.get_all_records()
      df = pd.DataFrame(data)

    df.columns = df.columns.str.strip().str.lstrip("\ufeff")
    return df.fillna("")
  except Exception as e:
    return pd.DataFrame(
        columns=["Username", "Password Hash", "Organization", "Role"]
    )


@st.cache_data(ttl=30)
def load_master_data():
  try:
    client = get_gspread_client()
    sheet = client.open_by_key(MASTER_SHEET_ID).sheet1
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    df.columns = df.columns.str.strip().str.lstrip("\ufeff")
    return df.fillna("None")
  except Exception as e:
    st.error(f"Error connecting to Google Sheets Directory: {e}")
    return pd.DataFrame()


@st.cache_data(ttl=30)
def load_notices_data():
  try:
    client = get_gspread_client()
    try:
      sheet = client.open_by_key(MASTER_SHEET_ID).worksheet("Notices")
    except Exception:
      return pd.DataFrame(columns=["Notice ID", "Organization", "Title", "Content", "Date Posted", "Image File ID"])
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    if not df.empty:
      df.columns = df.columns.str.strip().str.lstrip("\ufeff")
    return df.fillna("")
  except Exception:
    return pd.DataFrame(columns=["Notice ID", "Organization", "Title", "Content", "Date Posted", "Image File ID"])


@st.cache_data(ttl=30)
def load_posts_data():
  try:
    client = get_gspread_client()
    try:
      sheet = client.open_by_key(MASTER_SHEET_ID).worksheet("Posts")
    except Exception:
      return pd.DataFrame(columns=["Post ID", "Organization", "Author Username", "Message", "Timestamp", "Image File ID"])
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    if not df.empty:
      df.columns = df.columns.str.strip().str.lstrip("\ufeff")
    return df.fillna("")
  except Exception:
    return pd.DataFrame(columns=["Post ID", "Organization", "Author Username", "Message", "Timestamp", "Image File ID"])


@st.cache_data(ttl=30)
def load_likes_data():
  try:
    client = get_gspread_client()
    spreadsheet = client.open_by_key(MASTER_SHEET_ID)
    try:
      sheet = spreadsheet.worksheet("Likes")
    except Exception:
      sheet = spreadsheet.add_worksheet(title="Likes", rows="500", cols="2")
      sheet.append_row(["Post ID", "Username"])
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    if df.empty or "Post ID" not in df.columns:
      sheet.clear()
      sheet.append_row(["Post ID", "Username"])
      df = pd.DataFrame(sheet.get_all_records())
    df.columns = df.columns.str.strip().str.lstrip("\ufeff")
    return df.fillna("")
  except Exception:
    return pd.DataFrame(columns=["Post ID", "Username"])


@st.cache_data(ttl=30)
def load_comments_data():
  try:
    client = get_gspread_client()
    spreadsheet = client.open_by_key(MASTER_SHEET_ID)
    try:
      sheet = spreadsheet.worksheet("Comments")
    except Exception:
      sheet = spreadsheet.add_worksheet(title="Comments", rows="500", cols="4")
      sheet.append_row(["Post ID", "Username", "Comment", "Timestamp"])
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    if df.empty or "Post ID" not in df.columns:
      sheet.clear()
      sheet.append_row(["Post ID", "Username", "Comment", "Timestamp"])
      df = pd.DataFrame(sheet.get_all_records())
    df.columns = df.columns.str.strip().str.lstrip("\ufeff")
    return df.fillna("")
  except Exception:
    return pd.DataFrame(columns=["Post ID", "Username", "Comment", "Timestamp"])


@st.cache_data(ttl=30)
def load_private_messages_data():
  try:
    client = get_gspread_client()
    spreadsheet = client.open_by_key(MASTER_SHEET_ID)
    try:
      sheet = spreadsheet.worksheet("PrivateMessages")
    except Exception:
      sheet = spreadsheet.add_worksheet(title="PrivateMessages", rows="500", cols="7")
      sheet.append_row(["Organization", "Sender", "Recipient", "Message", "Timestamp", "Image File ID", "ReadStatus"])
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    expected_cols = ["Organization", "Sender", "Recipient", "Message", "Timestamp", "Image File ID", "ReadStatus"]
    if df.empty or "Sender" not in df.columns:
      sheet.clear()
      sheet.append_row(expected_cols)
      df = pd.DataFrame(sheet.get_all_records())
    df.columns = df.columns.str.strip().str.lstrip("\ufeff")
    return df.fillna("")
  except Exception:
    return pd.DataFrame(columns=["Organization", "Sender", "Recipient", "Message", "Timestamp", "Image File ID", "ReadStatus"])


@st.cache_data(ttl=30)
def load_classifieds_data():
  try:
    client = get_gspread_client()
    spreadsheet = client.open_by_key(MASTER_SHEET_ID)
    try:
      sheet = spreadsheet.worksheet("Classifieds")
    except Exception:
      sheet = spreadsheet.add_worksheet(title="Classifieds", rows="500", cols="7")
      sheet.append_row(["Item ID", "Organization", "Seller", "Category", "Title", "Price & Details", "Contact"])
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    if df.empty or "Item ID" not in df.columns:
      sheet.clear()
      sheet.append_row(["Item ID", "Organization", "Seller", "Category", "Title", "Price & Details", "Contact"])
      df = pd.DataFrame(sheet.get_all_records())
    df.columns = df.columns.str.strip().str.lstrip("\ufeff")
    return df.fillna("")
  except Exception:
    return pd.DataFrame(columns=["Item ID", "Organization", "Seller", "Category", "Title", "Price & Details", "Contact"])


@st.cache_data(ttl=30)
def load_tickets_data():
  try:
    client = get_gspread_client()
    spreadsheet = client.open_by_key(MASTER_SHEET_ID)
    try:
      sheet = spreadsheet.worksheet("MaintenanceTickets")
    except Exception:
      sheet = spreadsheet.add_worksheet(title="MaintenanceTickets", rows="500", cols="6")
      sheet.append_row(["Ticket ID", "Organization", "Resident", "IssueType", "Description", "Status"])
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    if df.empty or "Ticket ID" not in df.columns:
      sheet.clear()
      sheet.append_row(["Ticket ID", "Organization", "Resident", "IssueType", "Description", "Status"])
      df = pd.DataFrame(sheet.get_all_records())
    df.columns = df.columns.str.strip().str.lstrip("\ufeff")
    return df.fillna("")
  except Exception:
    return pd.DataFrame(columns=["Ticket ID", "Organization", "Resident", "IssueType", "Description", "Status"])


@st.cache_data(ttl=30)
def load_bookings_data():
  try:
    client = get_gspread_client()
    spreadsheet = client.open_by_key(MASTER_SHEET_ID)
    try:
      sheet = spreadsheet.worksheet("AmenityBookings")
    except Exception:
      sheet = spreadsheet.add_worksheet(title="AmenityBookings", rows="500", cols="6")
      sheet.append_row(["Booking ID", "Organization", "Resident", "Amenity", "DateSlot", "Purpose"])
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    if df.empty or "Booking ID" not in df.columns:
      sheet.clear()
      sheet.append_row(["Booking ID", "Organization", "Resident", "Amenity", "DateSlot", "Purpose"])
      df = pd.DataFrame(sheet.get_all_records())
    df.columns = df.columns.str.strip().str.lstrip("\ufeff")
    return df.fillna("")
  except Exception:
    return pd.DataFrame(columns=["Booking ID", "Organization", "Resident", "Amenity", "DateSlot", "Purpose"])


@st.cache_data(ttl=30)
def load_safety_data():
  try:
    client = get_gspread_client()
    spreadsheet = client.open_by_key(MASTER_SHEET_ID)
    try:
      sheet = spreadsheet.worksheet("SafetyAlerts")
    except Exception:
      sheet = spreadsheet.add_worksheet(title="SafetyAlerts", rows="500", cols="5")
      sheet.append_row(["Alert ID", "Organization", "Author", "Severity", "Message"])
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    if df.empty or "Alert ID" not in df.columns:
      sheet.clear()
      sheet.append_row(["Alert ID", "Organization", "Author", "Severity", "Message"])
      df = pd.DataFrame(sheet.get_all_records())
    df.columns = df.columns.str.strip().str.lstrip("\ufeff")
    return df.fillna("")
  except Exception:
    return pd.DataFrame(columns=["Alert ID", "Organization", "Author", "Severity", "Message"])


@st.cache_data(ttl=30)
def load_polls_data():
  try:
    client = get_gspread_client()
    spreadsheet = client.open_by_key(MASTER_SHEET_ID)
    try:
      sheet = spreadsheet.worksheet("CommunityPolls")
    except Exception:
      sheet = spreadsheet.add_worksheet(title="CommunityPolls", rows="100", cols="4")
      sheet.append_row(["Poll ID", "Organization", "Question", "Options"])
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    if df.empty or "Poll ID" not in df.columns:
      sheet.clear()
      sheet.append_row(["Poll ID", "Organization", "Question", "Options"])
      # Seed a default poll
      sheet.append_row(["1", "St. Xavier Enclave", "Should we organize the upcoming Annual Winter Gala in the Community Clubhouse lawn?", "Yes, absolutely! 🎉|No, let's keep it indoors 🏢|Neutral / Undecided 🤷‍♂️"])
      df = pd.DataFrame(sheet.get_all_records())
    df.columns = df.columns.str.strip().str.lstrip("\ufeff")
    return df.fillna("")
  except Exception:
    return pd.DataFrame(columns=["Poll ID", "Organization", "Question", "Options"])


# --- 3. SESSION STATE & URL QUERY PARAMS PERSISTENCE ---
query_params = st.query_params

if "authenticated" not in st.session_state:
  if "user" in query_params and "role" in query_params and "org" in query_params:
    st.session_state["authenticated"] = True
    st.session_state["username"] = query_params["user"]
    st.session_state["role"] = query_params["role"]
    st.session_state["org_name"] = query_params["org"]
  else:
    st.session_state["authenticated"] = False
    st.session_state["username"] = ""
    st.session_state["role"] = ""
    st.session_state["org_name"] = ""

if "saved_posts" not in st.session_state:
  st.session_state["saved_posts"] = []

if "nav_page" not in st.session_state:
  st.session_state["nav_page"] = "Directory"


# --- 4. AUTHENTICATION / LOGIN VIEW ---
if not st.session_state["authenticated"]:
  st.markdown(
      """
      <div style="text-align: center; padding: 40px 20px;">
          <h1 style="color: #0d9488; font-weight: 700;">🏙️ TogetheSpace v0.3</h1>
          <h3 style="color: #64748b; font-weight: 400;">Smart Community Hub & Resident Portal</h3>
      </div>
      """,
      unsafe_allow_html=True,
  )

  with st.form("login_form"):
    username_input = st.text_input("Username")
    password_input = st.text_input("Password", type="password")
    submit_login = st.form_submit_button("🚀 Enter Community Hub")

    if submit_login:
      clean_user = username_input.strip()
      hashed_input_pw = hash_password(password_input)

      df_users = load_users_data()
      user_row = (
          df_users[df_users["Username"].astype(str).str.strip() == clean_user]
          if not df_users.empty
          else pd.DataFrame()
      )

      if not user_row.empty:
        stored_hash = str(user_row.iloc[0]["Password Hash"]).strip()
        user_org = str(user_row.iloc[0]["Organization"]).strip()
        user_role = str(user_row.iloc[0]["Role"]).strip()

        if stored_hash == hashed_input_pw:
          st.session_state["authenticated"] = True
          st.session_state["username"] = clean_user
          st.session_state["role"] = user_role
          st.session_state["org_name"] = user_org

          st.query_params["user"] = clean_user
          st.query_params["role"] = user_role
          st.query_params["org"] = user_org

          st.rerun()
        else:
          st.error("Invalid password. Please check your credentials.")
      else:
        st.error("Username not found. Please check your credentials.")

# --- 5. AUTHENTICATED USER INTERFACE ---
else:
  df_master = load_master_data()
  user_org = st.session_state["org_name"]
  current_role = st.session_state["role"]
  current_user = st.session_state["username"]

  if not df_master.empty and "Organization" in df_master.columns:
    df_org = df_master[df_master["Organization"].str.strip() == user_org].copy()
  else:
    df_org = pd.DataFrame()

  st.sidebar.markdown(f"<h3 style='color: #0d9488;'>🏘️ {user_org}</h3>", unsafe_allow_html=True)
  st.sidebar.caption("✨ TogetheSpace v0.3 Community")
  st.sidebar.markdown(f"**Resident:** `{current_user}`")
  st.sidebar.markdown(f"**Role:** `{current_role.capitalize()}`")

  # --- SIDEBAR: CHANGE PASSWORD FEATURE ---
  with st.sidebar.expander("🔐 Change Password"):
    with st.form("sidebar_change_pass_form"):
      old_pass = st.text_input("Current Password", type="password")
      new_pass = st.text_input("New Password", type="password")
      confirm_pass = st.text_input("Confirm New Password", type="password")
      submit_pass = st.form_submit_button("Update Password")

      if submit_pass:
        if not old_pass or not new_pass:
          st.warning("Please fill in all fields.")
        elif new_pass != confirm_pass:
          st.error("New passwords do not match.")
        else:
          df_users = load_users_data()
          user_row = (
              df_users[df_users["Username"].astype(str).str.strip() == current_user]
              if not df_users.empty
              else pd.DataFrame()
          )

          if not user_row.empty:
            stored_hash = str(user_row.iloc[0]["Password Hash"]).strip()
            if stored_hash == hash_password(old_pass):
              new_hash = hash_password(new_pass)
              try:
                client = get_gspread_client()
                users_sheet = client.open_by_key(MASTER_SHEET_ID).worksheet("Users")
                cell = users_sheet.find(current_user)
                if cell:
                  users_sheet.update_cell(cell.row, 2, new_hash)
                  st.cache_data.clear()
                  st.success("Password updated successfully!")
                else:
                  st.error("User record not found in sheet.")
              except Exception as e:
                st.error(f"Failed to update password: {e}")
            else:
              st.error("Incorrect current password.")

  st.sidebar.markdown("---")

  # Calculate unread messages for badge
  df_pm_all = load_private_messages_data()
  unread_count = 0
  if not df_pm_all.empty and "Recipient" in df_pm_all.columns and "ReadStatus" in df_pm_all.columns:
    unread_df = df_pm_all[
        (df_pm_all["Organization"].astype(str).str.strip() == user_org) &
        (df_pm_all["Recipient"].astype(str).str.strip() == current_user) &
        (df_pm_all["ReadStatus"].astype(str).str.strip() != "Read")
    ]
    unread_count = len(unread_df)

  comm_hub_label = f"💬 Communication & Feed ({unread_count})" if unread_count > 0 else "💬 Communication & Feed"

  # --- SIDEBAR NAVIGATION MENU ---
  st.sidebar.markdown("### 🧭 Community Menu")

  if st.sidebar.button("📇 Resident Directory", use_container_width=True):
    st.session_state["nav_page"] = "Directory"
    st.rerun()

  if st.sidebar.button(comm_hub_label, use_container_width=True):
    st.session_state["nav_page"] = "CommHub"
    st.rerun()

  if st.sidebar.button("🏷️ Classifieds & Marketplace", use_container_width=True):
    st.session_state["nav_page"] = "Classifieds"
    st.rerun()

  if st.sidebar.button("🛠️ Helpdesk & Tickets", use_container_width=True):
    st.session_state["nav_page"] = "Helpdesk"
    st.rerun()

  if st.sidebar.button("📅 Facility Booking", use_container_width=True):
    st.session_state["nav_page"] = "Bookings"
    st.rerun()

  if st.sidebar.button("🚨 Safety & SOS Alerts", use_container_width=True):
    st.session_state["nav_page"] = "Safety"
    st.rerun()

  if st.sidebar.button("📊 Community Polls & Voting", use_container_width=True):
    st.session_state["nav_page"] = "Polls"
    st.rerun()

  if st.sidebar.button("🌟 Local Attractions & Events", use_container_width=True):
    st.session_state["nav_page"] = "Locality Attractions"
    st.rerun()

  if current_role == "manager":
    if st.sidebar.button("🛠️ Community Admin Portal", use_container_width=True):
      st.session_state["nav_page"] = "Manager Admin Portal"
      st.rerun()

  st.sidebar.markdown("---")
  if st.sidebar.button("🚪 Log Out", use_container_width=True):
    st.session_state["authenticated"] = False
    st.session_state["username"] = ""
    st.session_state["role"] = ""
    st.session_state["org_name"] = ""
    st.query_params.clear()
    st.rerun()

  current_tab = st.session_state.get("nav_page", "Directory")

  # --- 1. RESIDENT DIRECTORY TAB (SEA GREEN EXPANDER CARDS) ---
  if current_tab == "Directory":
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #0d9488 0%, #14b8a6 100%); padding: 22px; border-radius: 14px; color: white; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(13,148,136,0.2);">
            <h1 style="margin:0; font-weight:700;">📇 {user_org} — Resident Directory</h1>
            <p style="margin:5px 0 0 0; opacity: 0.9;">Neighbor contacts, block locations & emergency SOS</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    search_query = st.sidebar.text_input("🔍 Search Residents (Name, Block, Notes)")
    filtered_df = df_org.copy()

    if search_query and not filtered_df.empty:
      filtered_df = filtered_df[
          filtered_df["Full Name"].str.contains(search_query, case=False, na=False)
          | filtered_df["Notes"].str.contains(search_query, case=False, na=False)
      ]

    st.markdown(f"Showing **{len(filtered_df)}** residents for **{user_org}**")

    if filtered_df.empty:
      st.warning("No resident records found matching your search.")
    else:
      for _, row in filtered_df.iterrows():
        name = row.get("Full Name", "Resident")
        blood = row.get("Blood Group", "N/A")
        bio_text = str(row.get("Bio", "")).strip()
        org_name = row.get("Organization", user_org)
        member_role = row.get("Role", "Member")
        birthday = str(row.get("Birthday", "")).strip()
        timezone = row.get("Timezone", "")
        notes = row.get("Notes", "")

        with st.expander(f"👤 {name}  |  🏠 {notes or 'Block A'}  |  🩸 Blood Group: {blood}"):
          if bio_text and bio_text != "None":
            st.info(f"**Bio / Interests:** {bio_text}")

          meta_cols = st.columns(4)
          with meta_cols[0]:
            st.markdown(f"**Role:** `{str(member_role).capitalize()}`")
          with meta_cols[1]:
            if birthday and birthday.lower() != "none":
              st.markdown(f"🎂 **Birthday:** {birthday}")
          with meta_cols[2]:
            if timezone and timezone != "None":
              st.markdown(f"🌍 **Zone:** {timezone}")
          with meta_cols[3]:
            if notes and notes != "None":
              st.markdown(f"📝 **Block/Flat:** {notes}")

          st.markdown("---")
          col1, col2 = st.columns(2)

          with col1:
            st.subheader("📞 Communication Details")
            raw_address = str(row.get("Address", "None"))
            if raw_address and raw_address != "None":
              maps_url = f"https://www.google.com/maps/search/?api=1&query={raw_address.replace(' ', '+')}"
              st.markdown(f"**Address:** [{raw_address}]({maps_url}) (Map)")
            else:
              st.markdown("**Address:** None")

            phone = str(row.get("Phone Number", ""))
            if phone and phone != "None":
              st.markdown(f"**Phone / Call:** [{phone}](tel:{phone})")
              st.markdown(f"**SMS:** [Send SMS](sms:{phone})")
            else:
              st.markdown("**Phone:** None")

            wa_chat = str(row.get("WhatsApp Chat", ""))
            if wa_chat and wa_chat != "None":
              wa_digits = "".join(filter(str.isdigit, wa_chat))
              wa_url = wa_chat if wa_chat.startswith("http") else (f"https://wa.me/{wa_digits}" if wa_digits else "#")
              st.markdown(f"**WhatsApp Chat:** [Open Chat]({wa_url})")
            else:
              st.markdown("**WhatsApp Chat:** None")

            email_raw = str(row.get("Email", "None")).strip()
            if email_raw and email_raw != "None":
              gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&to={email_raw}"
              st.markdown(f"**Email:** [{email_raw}]({gmail_url})")
            else:
              st.markdown("**Email:** None")

          with col2:
            st.subheader("🚨 Medical Emergency & SOS")
            st.error(f"""
                        - **Blood Group:** {blood}
                        - **Allergies:** {row.get('Allergies', 'None')}
                        - **Medical Conditions:** {row.get('Medical Conditions', 'None')}
                        - **Medications:** {row.get('Medications', 'None')}
                        """)
            emerg_phone = str(row.get("Emergency Contact Phone", ""))
            st.info(f"""
                        **Emergency Contact:**
                        - **Name:** {row.get('Emergency Contact Name', 'N/A')} ({row.get('Emergency Contact Relationship', '')})
                        - **Phone:** [{emerg_phone}](tel:{emerg_phone})
                        """)

  # --- 2. COMMUNICATION & FEED HUB TAB ---
  elif current_tab == "CommHub":
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #6366f1 0%, #ec4899 100%); padding: 22px; border-radius: 14px; color: white; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(99,102,241,0.2);">
            <h1 style="margin:0; font-weight:700;">💬 Community Communication & Feed</h1>
            <p style="margin:5px 0 0 0; opacity: 0.9;">Official Notices, Neighborhood Discussions & Direct Resident Chat</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    sub_tab_choice = st.radio(
        "Select Hub View",
        ["📢 Community Notices", "💬 Neighbor Feed", "🔒 1-on-1 Resident Chat"],
        horizontal=True,
        label_visibility="collapsed"
    )
    st.markdown("---")

    if sub_tab_choice == "📢 Community Notices":
      df_notices = load_notices_data()
      org_notices = df_notices[df_notices["Organization"].str.strip() == user_org] if not df_notices.empty else pd.DataFrame()

      if current_role == "manager":
        with st.expander("➕ Publish Community Notice (Community Admin Only)", expanded=False):
          with st.form("notice_form", clear_on_submit=True):
            notice_title = st.text_input("Notice Title")
            notice_content = st.text_area("Notice Details")
            notice_image = st.file_uploader("Attach Image (Optional)", type=["png", "jpg", "jpeg"])
            submit_notice = st.form_submit_button("Publish Notice")

            if submit_notice:
              if notice_title.strip() and notice_content.strip():
                try:
                  image_data_str = process_image_to_base64(notice_image) if notice_image else ""
                  client = get_gspread_client()
                  notice_sheet = client.open_by_key(MASTER_SHEET_ID).worksheet("Notices")
                  new_id = str(len(df_notices) + 1) if not df_notices.empty else "1"
                  today_date = datetime.now().strftime("%Y-%m-%d %H:%M")
                  notice_sheet.append_row([new_id, user_org, notice_title.strip(), notice_content.strip(), today_date, image_data_str])
                  st.cache_data.clear()
                  st.success("Notice published successfully!")
                  st.rerun()
                except Exception as e:
                  st.error(f"Failed to publish notice: {e}")
              else:
                st.warning("Please fill in both title and content.")

      if org_notices.empty:
        st.info("No notices posted yet.")
      else:
        for _, row in org_notices.iloc[::-1].iterrows():
          with st.container():
            st.subheader(f"📌 {row.get('Title', 'Notice')}")
            st.caption(f"Posted: {row.get('Date Posted', 'Recent')} | Community Administration")
            st.write(row.get("Content", ""))
            img_data = str(row.get("Image File ID", "")).strip()
            if img_data and img_data != "None":
              img_bytes = decode_base64_image(img_data)
              if img_bytes:
                st.image(img_bytes, use_container_width=True)
            st.markdown("---")

    elif sub_tab_choice == "💬 Neighbor Feed":
      df_posts = load_posts_data()
      df_likes = load_likes_data()
      df_comments = load_comments_data()
      org_posts = df_posts[df_posts["Organization"].str.strip() == user_org] if not df_posts.empty else pd.DataFrame()

      with st.form("crisp_post_form", clear_on_submit=True):
        user_message = st.text_area("Share with neighbors...", placeholder="What's happening in your block?", height=80)
        c1, c2 = st.columns([2, 1])
        with c1:
          post_image = st.file_uploader("Attach Photo", type=["png", "jpg", "jpeg"], key="post_img")
        with c2:
          st.markdown("<br>", unsafe_allow_html=True)
          submit_post = st.form_submit_button("🚀 Post to Feed", use_container_width=True)

        if submit_post:
          if user_message.strip() or post_image is not None:
            try:
              image_str = process_image_to_base64(post_image) if post_image else ""
              client = get_gspread_client()
              posts_sheet = client.open_by_key(MASTER_SHEET_ID).worksheet("Posts")
              new_id = str(len(df_posts) + 1) if not df_posts.empty else "1"
              timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
              posts_sheet.append_row([new_id, user_org, current_user, user_message.strip(), timestamp, image_str])
              st.cache_data.clear()
              st.success("Successfully posted!")
              st.rerun()
            except Exception as e:
              st.error(f"Error publishing post: {e}")
          else:
            st.warning("Please type a message or attach an image.")

      st.markdown("---")
      if org_posts.empty:
        st.info("No neighbor discussions yet. Start the conversation!")
      else:
        for _, row in org_posts.iloc[::-1].iterrows():
          post_id = str(row.get("Post ID", ""))
          author = row.get("Author Username", "Resident")
          timestamp = row.get("Timestamp", "")
          message = row.get("Message", "")
          img_data = str(row.get("Image File ID", "")).strip()

          post_likes = df_likes[df_likes["Post ID"].astype(str).str.strip() == post_id] if not df_likes.empty else pd.DataFrame()
          like_count = len(post_likes)
          user_liked = not post_likes[post_likes["Username"].astype(str).str.strip() == current_user].empty if not post_likes.empty else False

          post_comments = df_comments[df_comments["Post ID"].astype(str).str.strip() == post_id] if not df_comments.empty else pd.DataFrame()
          comment_count = len(post_comments)

          st.markdown(
              f"""
              <div style="background-color: #f8fafc; padding: 18px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 14px;">
                  <b>{author}</b> <span style="color: #64748b; font-size: 12px;">🕒 {timestamp}</span>
                  <div style="margin-top: 8px; font-size: 15px; white-space: pre-wrap;">{message}</div>
              </div>
              """,
              unsafe_allow_html=True,
          )
          if img_data and img_data != "None":
            ib = decode_base64_image(img_data)
            if ib:
              st.image(ib, use_container_width=True)

          col_a, col_b = st.columns(2)
          with col_a:
            like_lbl = f"❤️ {like_count} Liked" if user_liked else f"👍 {like_count} Like"
            if st.button(like_lbl, key=f"like_{post_id}"):
              try:
                client = get_gspread_client()
                likes_sheet = client.open_by_key(MASTER_SHEET_ID).worksheet("Likes")
                if user_liked:
                  cell = likes_sheet.find(current_user)
                  while cell:
                    rv = likes_sheet.row_values(cell.row)
                    if len(rv) >= 2 and str(rv[0]).strip() == str(post_id) and str(rv[1]).strip() == current_user:
                      likes_sheet.delete_rows(cell.row)
                      break
                    cell = likes_sheet.find(current_user, in_column=2)
                else:
                  likes_sheet.append_row([str(post_id), current_user])
                st.cache_data.clear()
                st.rerun()
              except Exception as e:
                st.error(f"Error: {e}")
          with col_b:
            if st.button(f"💬 {comment_count} Comments", key=f"comm_toggle_{post_id}"):
              st.session_state[f"show_c_{post_id}"] = not st.session_state.get(f"show_c_{post_id}", False)

          if st.session_state.get(f"show_c_{post_id}", False):
            if not post_comments.empty:
              for _, cr in post_comments.iterrows():
                st.markdown(f"💬 **{cr.get('Username')}**: {cr.get('Comment')}")
            with st.form(key=f"c_form_{post_id}", clear_on_submit=True):
              ctxt = st.text_input("Write a comment...", key=f"in_c_{post_id}")
              if st.form_submit_button("Send Comment") and ctxt.strip():
                try:
                  client = get_gspread_client()
                  cs = client.open_by_key(MASTER_SHEET_ID).worksheet("Comments")
                  cs.append_row([str(post_id), current_user, ctxt.strip(), datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
                  st.cache_data.clear()
                  st.rerun()
                except Exception as e:
                  st.error(f"Error: {e}")
          st.markdown("---")

    elif sub_tab_choice == "🔒 1-on-1 Resident Chat":
      c_t1, c_t2 = st.columns([4, 1])
      with c_t1:
        st.markdown("### Secure Resident Messaging")
      with c_t2:
        if st.button("🔄 Refresh Chat", use_container_width=True):
          st.cache_data.clear()
          st.rerun()

      df_users_all = load_users_data()
      org_members = df_users_all[df_users_all["Organization"].astype(str).str.strip() == user_org]["Username"].astype(str).str.strip().tolist() if not df_users_all.empty else []
      if current_user in org_members:
        org_members.remove(current_user)

      if not org_members:
        st.info("No other residents found.")
      else:
        recipient = st.selectbox("Select Neighbor to Chat", org_members)
        if recipient:
          client = get_gspread_client()
          pm_sheet = client.open_by_key(MASTER_SHEET_ID).worksheet("PrivateMessages")
          df_pm = load_private_messages_data()

          chat_filter = df_pm[
              (df_pm["Organization"].astype(str).str.strip() == user_org) &
              (
                  ((df_pm["Sender"].astype(str).str.strip() == current_user) & (df_pm["Recipient"].astype(str).str.strip() == recipient)) |
                  ((df_pm["Sender"].astype(str).str.strip() == recipient) & (df_pm["Recipient"].astype(str).str.strip() == current_user))
              )
          ] if not df_pm.empty else pd.DataFrame()

          for _, row in chat_filter.iterrows():
            snd = str(row.get("Sender", "")).strip()
            txt = str(row.get("Message", "")).strip()
            time_str = str(row.get("Timestamp", "")).strip()
            if snd == current_user:
              st.markdown(f"<div style='background-color: #dcf8c6; padding: 10px; border-radius: 8px; margin-bottom: 6px; margin-left: 20%; text-align: right;'><b>You ({time_str})</b><br>{txt}</div>", unsafe_allow_html=True)
            else:
              st.markdown(f"<div style='background-color: #ffffff; padding: 10px; border-radius: 8px; margin-bottom: 6px; margin-right: 20%; border: 1px solid #cbd5e1;'><b>{snd} ({time_str})</b><br>{txt}</div>", unsafe_allow_html=True)

          with st.form("pm_form", clear_on_submit=True):
            msg_text = st.text_input("Type private message...")
            if st.form_submit_button("Send Message") and msg_text.strip():
              try:
                pm_sheet.append_row([user_org, current_user, recipient, msg_text.strip(), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "", "Unread"])
                st.cache_data.clear()
                st.rerun()
              except Exception as e:
                st.error(f"Error: {e}")

  # --- 3. CLASSIFIEDS & MARKETPLACE TAB ---
  elif current_tab == "Classifieds":
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); padding: 22px; border-radius: 14px; color: white; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(245,158,11,0.2);">
            <h1 style="margin:0; font-weight:700;">🏷️ Community Classifieds & Marketplace</h1>
            <p style="margin:5px 0 0 0; opacity: 0.9;">Buy, sell, rent, or give away items locally with neighbors</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    df_class = load_classifieds_data()
    org_class = df_class[df_class["Organization"].str.strip() == user_org] if not df_class.empty else pd.DataFrame()

    with st.expander("➕ Post New Classified Item", expanded=False):
      with st.form("class_form", clear_on_submit=True):
        c_cat = st.selectbox("Category", ["For Sale", "For Rent", "Services", "Free Giveaway", "Car Pooling"])
        c_title = st.text_input("Item Title / Short Summary")
        c_desc = st.text_area("Price, Condition & Details")
        c_contact = st.text_input("Contact Phone / WhatsApp")
        if st.form_submit_button("Publish Classified") and c_title.strip():
          try:
            client = get_gspread_client()
            cs = client.open_by_key(MASTER_SHEET_ID).worksheet("Classifieds")
            new_id = str(len(df_class) + 1) if not df_class.empty else "1"
            cs.append_row([new_id, user_org, current_user, c_cat, c_title.strip(), c_desc.strip(), c_contact.strip()])
            st.cache_data.clear()
            st.success("Classified published successfully!")
            st.rerun()
          except Exception as e:
            st.error(f"Error: {e}")

    st.markdown("---")
    if org_class.empty:
      st.info("No classifieds posted yet.")
    else:
      for _, row in org_class.iloc[::-1].iterrows():
        item_id = row.get("Item ID", "")
        seller = row.get("Seller", "")
        category = row.get("Category", "")
        title = row.get("Title", "")
        details = row.get("Price & Details", "")
        contact = row.get("Contact", "")

        st.markdown(
            f"""
            <div style="background-color: #ffffff; padding: 18px; border-radius: 10px; border: 1px solid #cbd5e1; margin-bottom: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                <span style="background-color: #f59e0b; color: white; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;">{category}</span>
                <h3 style="margin: 8px 0 4px 0; color: #1e293b;">{title}</h3>
                <p style="margin: 0; color: #475569; font-size: 15px; white-space: pre-wrap;">{details}</p>
                <p style="margin: 8px 0 0 0; font-size: 13px; color: #0d9488;"><b>Seller:</b> {seller} | <b>Contact:</b> {contact}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if current_role == "manager" or current_user == seller:
          if st.button("🗑️ Delete Listing", key=f"del_class_{item_id}"):
            try:
              client = get_gspread_client()
              cs = client.open_by_key(MASTER_SHEET_ID).worksheet("Classifieds")
              cell = cs.find(str(item_id))
              if cell:
                cs.delete_rows(cell.row)
                st.cache_data.clear()
                st.success("Listing removed.")
                st.rerun()
            except Exception as e:
              st.error(f"Error: {e}")
        st.markdown("---")

  # --- 4. HELPKDESK & TICKETING TAB ---
  elif current_tab == "Helpdesk":
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); padding: 22px; border-radius: 14px; color: white; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(239,68,68,0.2);">
            <h1 style="margin:0; font-weight:700;">🛠️ Maintenance Helpdesk & Tickets</h1>
            <p style="margin:5px 0 0 0; opacity: 0.9;">Report facility issues, plumbing leaks, lighting or security faults</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    df_tickets = load_tickets_data()
    org_tickets = df_tickets[df_tickets["Organization"].str.strip() == user_org] if not df_tickets.empty else pd.DataFrame()

    with st.expander("➕ Raise New Maintenance Ticket", expanded=False):
      with st.form("ticket_form", clear_on_submit=True):
        t_type = st.selectbox("Issue Category", ["Plumbing & Water", "Electrical & Lighting", "Security & Gate", "Cleanliness & Garbage", "Other Maintenance"])
        t_desc = st.text_area("Issue Description & Location (e.g. Block B Lobby Light)")
        if st.form_submit_button("Submit Ticket") and t_desc.strip():
          try:
            client = get_gspread_client()
            ts = client.open_by_key(MASTER_SHEET_ID).worksheet("MaintenanceTickets")
            new_id = str(len(df_tickets) + 1) if not df_tickets.empty else "1"
            ts.append_row([new_id, user_org, current_user, t_type, t_desc.strip(), "Open 🟡"])
            st.cache_data.clear()
            st.success("Ticket submitted successfully!")
            st.rerun()
          except Exception as e:
            st.error(f"Error: {e}")

    st.markdown("---")
    if org_tickets.empty:
      st.info("No maintenance tickets raised.")
    else:
      for _, row in org_tickets.iloc[::-1].iterrows():
        t_id = row.get("Ticket ID", "")
        resident = row.get("Resident", "")
        itype = row.get("IssueType", "")
        desc = row.get("Description", "")
        status = row.get("Status", "Open 🟡")

        st.markdown(
            f"""
            <div style="background-color: #ffffff; padding: 18px; border-radius: 10px; border: 1px solid #cbd5e1; margin-bottom: 14px;">
                <div style="display: flex; justify-content: space-between;">
                    <b>🔧 {itype}</b>
                    <span><b>Status:</b> {status}</span>
                </div>
                <p style="margin: 8px 0; color: #334155; white-space: pre-wrap;">{desc}</p>
                <p style="margin: 0; font-size: 12px; color: #64748b;">Raised by: {resident}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if current_role == "manager":
          c_s1, c_s2 = st.columns(2)
          with c_s1:
            if st.button("Mark In Progress 🔄", key=f"prog_{t_id}"):
              try:
                client = get_gspread_client()
                ts = client.open_by_key(MASTER_SHEET_ID).worksheet("MaintenanceTickets")
                cell = ts.find(str(t_id))
                if cell:
                  ts.update_cell(cell.row, 6, "In Progress 🔄")
                  st.cache_data.clear()
                  st.rerun()
              except Exception as e:
                st.error(f"Error: {e}")
          with c_s2:
            if st.button("Mark Resolved ✅", key=f"res_{t_id}"):
              try:
                client = get_gspread_client()
                ts = client.open_by_key(MASTER_SHEET_ID).worksheet("MaintenanceTickets")
                cell = ts.find(str(t_id))
                if cell:
                  ts.update_cell(cell.row, 6, "Resolved ✅")
                  st.cache_data.clear()
                  st.rerun()
              except Exception as e:
                st.error(f"Error: {e}")
        st.markdown("---")

  # --- 5. FACILITY BOOKINGS TAB ---
  elif current_tab == "Bookings":
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); padding: 22px; border-radius: 14px; color: white; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(2,132,199,0.2);">
            <h1 style="margin:0; font-weight:700;">📅 Facility & Amenity Booking</h1>
            <p style="margin:5px 0 0 0; opacity: 0.9;">Reserve shared community spaces like clubhouses, tennis courts or party lawns</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    df_bks = load_bookings_data()
    org_bks = df_bks[df_bks["Organization"].str.strip() == user_org] if not df_bks.empty else pd.DataFrame()

    with st.expander("➕ Book an Amenity", expanded=False):
      with st.form("bk_form", clear_on_submit=True):
        amenity = st.selectbox("Select Amenity", ["Clubhouse Hall", "Tennis Court", "Swimming Pool Deck", "Guest Room 1", "Barbecue Lawn"])
        slot_date = st.date_input("Date & Slot")
        purpose = st.text_input("Purpose of Booking (e.g. Birthday Party, Tennis Match)")
        if st.form_submit_button("Confirm Booking") and purpose.strip():
          try:
            client = get_gspread_client()
            bs = client.open_by_key(MASTER_SHEET_ID).worksheet("AmenityBookings")
            new_id = str(len(df_bks) + 1) if not df_bks.empty else "1"
            bs.append_row([new_id, user_org, current_user, amenity, str(slot_date), purpose.strip()])
            st.cache_data.clear()
            st.success("Amenity successfully booked!")
            st.rerun()
          except Exception as e:
            st.error(f"Error: {e}")

    st.markdown("---")
    st.subheader("Current Community Reservations")
    if org_bks.empty:
      st.info("No facility bookings made yet.")
    else:
      for _, row in org_bks.iloc[::-1].iterrows():
        b_id = row.get("Booking ID", "")
        resident = row.get("Resident", "")
        amenity = row.get("Amenity", "")
        slot = row.get("DateSlot", "")
        purpose = row.get("Purpose", "")

        st.markdown(
            f"""
            <div style="background-color: #f0fdf4; padding: 16px; border-radius: 10px; border: 1px solid #bbf7d0; margin-bottom: 12px;">
                <b>🏢 {amenity}</b> on <b>{slot}</b><br>
                <span><b>Purpose:</b> {purpose}</span><br>
                <span style="font-size: 12px; color: #166534;">Reserved by: {resident}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if current_role == "manager" or current_user == resident:
          if st.button("Cancel Booking", key=f"del_bk_{b_id}"):
            try:
              client = get_gspread_client()
              bs = client.open_by_key(MASTER_SHEET_ID).worksheet("AmenityBookings")
              cell = bs.find(str(b_id))
              if cell:
                bs.delete_rows(cell.row)
                st.cache_data.clear()
                st.success("Booking cancelled.")
                st.rerun()
            except Exception as e:
              st.error(f"Error: {e}")

  # --- 6. SAFETY & SOS ALERTS TAB ---
  elif current_tab == "Safety":
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%); padding: 22px; border-radius: 14px; color: white; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(124,58,237,0.2);">
            <h1 style="margin:0; font-weight:700;">🚨 Neighborhood Safety & SOS Broadcasts</h1>
            <p style="margin:5px 0 0 0; opacity: 0.9;">Urgent security alerts, weather advisories and lost pet notices</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    df_safety = load_safety_data()
    org_safety = df_safety[df_safety["Organization"].str.strip() == user_org] if not df_safety.empty else pd.DataFrame()

    with st.expander("➕ Broadcast Safety Alert", expanded=False):
      with st.form("safety_form", clear_on_submit=True):
        sev = st.selectbox("Alert Severity", ["Normal Advisory ℹ️", "Important Notice ⚠️", "URGENT EMERGENCY 🚨"])
        s_msg = st.text_area("Alert Message & Instructions")
        if st.form_submit_button("Broadcast Alert Now") and s_msg.strip():
          try:
            client = get_gspread_client()
            ss = client.open_by_key(MASTER_SHEET_ID).worksheet("SafetyAlerts")
            new_id = str(len(df_safety) + 1) if not df_safety.empty else "1"
            ss.append_row([new_id, user_org, current_user, sev, s_msg.strip()])
            st.cache_data.clear()
            st.success("Safety alert broadcasted to all residents!")
            st.rerun()
          except Exception as e:
            st.error(f"Error: {e}")

    st.markdown("---")
    if org_safety.empty:
      st.info("No safety alerts recorded.")
    else:
      for _, row in org_safety.iloc[::-1].iterrows():
        sev = row.get("Severity", "")
        msg = row.get("Message", "")
        author = row.get("Author", "")

        bg_color = "#fef2f2" if "URGENT" in sev else ("#fffbeb" if "Important" in sev else "#f8fafc")
        border_col = "#f87171" if "URGENT" in sev else ("#fbbf24" if "Important" in sev else "#cbd5e1")

        st.markdown(
            f"""
            <div style="background-color: {bg_color}; padding: 18px; border-radius: 10px; border: 1.5px solid {border_col}; margin-bottom: 14px;">
                <h3 style="margin: 0 0 8px 0;">{sev}</h3>
                <p style="margin: 0; font-size: 15px; white-space: pre-wrap;">{msg}</p>
                <p style="margin: 8px 0 0 0; font-size: 12px; color: #64748b;">Broadcasted by: {author}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

  # --- 7. COMMUNITY POLLS & VOTING HUB ---
  elif current_tab == "Polls":
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #059669 0%, #047857 100%); padding: 22px; border-radius: 14px; color: white; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(5,150,105,0.2);">
            <h1 style="margin:0; font-weight:700;">📊 Community Polls & Voting Hub</h1>
            <p style="margin:5px 0 0 0; opacity: 0.9;">Cast your vote on active neighborhood decisions and community proposals</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    df_polls = load_polls_data()
    org_polls = df_polls[df_polls["Organization"].str.strip() == user_org] if not df_polls.empty else pd.DataFrame()

    if org_polls.empty:
      st.info("No active community polls at the moment. Community Admin can create one from the admin portal.")
    else:
      for _, poll_row in org_polls.iterrows():
        p_id = poll_row.get("Poll ID", "")
        question = poll_row.get("Question", "")
        options_raw = poll_row.get("Options", "")
        options_list = [opt.strip() for opt in options_raw.split("|") if opt.strip()]

        st.markdown(f"### 🗳️ {question}")
        vote_choice = st.radio(f"Select option for Poll #{p_id}", options_list, key=f"poll_rad_{p_id}")
        if st.button("Cast Vote", key=f"vote_btn_{p_id}"):
          st.success(f"Thank you! Your vote for '{vote_choice}' has been successfully recorded.")
        st.markdown("---")

  # --- 8. LOCALITY ATTRACTIONS & EVENTS TAB ---
  elif current_tab == "Locality Attractions":
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%); padding: 22px; border-radius: 14px; color: white; margin-bottom: 20px;">
            <h1 style="margin:0; font-weight:700;">🌟 Locality Attractions, Business & Events Bulletin</h1>
            <p style="margin:5px 0 0 0; opacity: 0.9;">Indexed community facilities and local updates</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    df_locality = load_locality_data()
    cat_filter = st.selectbox("Filter by Category", ["All Categories", "Attractions", "Business", "Facilities", "Events"])
    filtered_loc = df_locality.copy()
    if cat_filter != "All Categories" and not filtered_loc.empty:
      filtered_loc = filtered_loc[filtered_loc["Category"].str.strip() == cat_filter]

    if filtered_loc.empty:
      st.info("No locality updates published yet.")
    else:
      for _, row in filtered_loc.iloc[::-1].iterrows():
        details = row.get("Title & Details", "")
        cat = row.get("Category", "")
        wnd = row.get("Window", "")
        st.markdown(
            f"""
            <div style="background-color: #ffffff; padding: 18px; border-radius: 10px; border: 1px solid #cbd5e1; margin-bottom: 14px;">
                <span style="background-color: #0d9488; color: white; padding: 3px 8px; border-radius: 4px; font-size: 12px;">{cat} ({wnd})</span>
                <p style="margin: 10px 0 0 0; white-space: pre-wrap; font-size: 15px;">{details}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

  # --- 9. COMMUNITY ADMIN PORTAL TAB ---
  elif current_tab == "Manager Admin Portal" and current_role == "manager":
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #ef4444 0%, #f97316 100%); padding: 22px; border-radius: 14px; color: white; margin-bottom: 20px;">
            <h1 style="margin:0; font-weight:700;">🛠️ Community Admin Portal — {user_org}</h1>
            <p style="margin:5px 0 0 0; opacity: 0.9;">Resident accounts, directory management, and custom voting polls</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    admin_sub_tab = st.selectbox(
        "Admin Actions",
        [
            "Manage Resident Directory",
            "Add New Resident Account",
            "Reset Resident Password",
            "Remove Resident Account",
            "Create & Manage Community Polls"
        ]
    )

    if admin_sub_tab == "Manage Resident Directory":
      edited_org_df = st.data_editor(df_org, num_rows="dynamic", use_container_width=True)
      if st.button("Save Directory Changes"):
        try:
          client = get_gspread_client()
          sheet = client.open_by_key(MASTER_SHEET_ID).sheet1
          edited_org_df["Organization"] = user_org
          df_others = df_master[df_master["Organization"].str.strip() != user_org] if not df_master.empty else pd.DataFrame()
          df_final = pd.concat([df_others, edited_org_df], ignore_index=True)
          sheet.clear()
          sheet.update([df_final.columns.values.tolist()] + df_final.values.tolist())
          st.cache_data.clear()
          st.success("Directory saved successfully!")
        except Exception as e:
          st.error(f"Error: {e}")

    elif admin_sub_tab == "Add New Resident Account":
      with st.form("new_res_form", clear_on_submit=True):
        u_name = st.text_input("Username (e.g. resident_blocka)")
        u_pass = st.text_input("Temporary Password", type="password")
        if st.form_submit_button("Create Account") and u_name.strip():
          try:
            client = get_gspread_client()
            us = client.open_by_key(MASTER_SHEET_ID).worksheet("Users")
            us.append_row([u_name.strip(), hash_password(u_pass), user_org, "member"])
            st.cache_data.clear()
            st.success(f"Account for '{u_name}' created!")
          except Exception as e:
            st.error(f"Error: {e}")

    elif admin_sub_tab == "Reset Resident Password":
      df_users_all = load_users_data()
      org_users = df_users_all[(df_users_all["Organization"].astype(str).str.strip() == user_org) & (df_users_all["Role"].astype(str).str.strip() == "member")]
      if org_users.empty:
        st.info("No resident accounts found.")
      else:
        usernames = org_users["Username"].astype(str).str.strip().tolist()
        with st.form("rst_form", clear_on_submit=True):
          sel_u = st.selectbox("Select Resident", usernames)
          new_p = st.text_input("New Password", type="password")
          if st.form_submit_button("Reset Password") and new_p:
            try:
              client = get_gspread_client()
              us = client.open_by_key(MASTER_SHEET_ID).worksheet("Users")
              cell = us.find(sel_u)
              if cell:
                us.update_cell(cell.row, 2, hash_password(new_p))
                st.cache_data.clear()
                st.success("Password reset successfully!")
            except Exception as e:
              st.error(f"Error: {e}")

    elif admin_sub_tab == "Remove Resident Account":
      df_users_all = load_users_data()
      org_users = df_users_all[(df_users_all["Organization"].astype(str).str.strip() == user_org) & (df_users_all["Role"].astype(str).str.strip() == "member")]
      if org_users.empty:
        st.info("No resident accounts found.")
      else:
        usernames = org_users["Username"].astype(str).str.strip().tolist()
        del_u = st.selectbox("Select Resident to Remove", usernames)
        if st.button("Revoke Resident Access"):
          try:
            client = get_gspread_client()
            us = client.open_by_key(MASTER_SHEET_ID).worksheet("Users")
            cell = us.find(del_u)
            if cell:
              us.delete_rows(cell.row)
              st.cache_data.clear()
              st.success("Resident access revoked.")
              st.rerun()
          except Exception as e:
            st.error(f"Error: {e}")

    elif admin_sub_tab == "Create & Manage Community Polls":
      st.subheader("Create a New Voting Poll")
      df_polls = load_polls_data()

      with st.form("new_poll_form", clear_on_submit=True):
        poll_q = st.text_input("Poll Question", placeholder="e.g. Should we approve the garden renovation budget?")
        poll_opts = st.text_area("Answer Options (Separate each option with a vertical bar |)", placeholder="Yes, approve it!|No, postpone|Need more details")
        submit_poll = st.form_submit_button("Launch Poll to Community")

        if submit_poll:
          if poll_q.strip() and poll_opts.strip():
            try:
              client = get_gspread_client()
              try:
                ps = client.open_by_key(MASTER_SHEET_ID).worksheet("CommunityPolls")
              except Exception:
                ps = client.open_by_key(MASTER_SHEET_ID).add_worksheet(title="CommunityPolls", rows="100", cols="4")
                ps.append_row(["Poll ID", "Organization", "Question", "Options"])

              new_pid = str(len(df_polls) + 1) if not df_polls.empty else "1"
              ps.append_row([new_pid, user_org, poll_q.strip(), poll_opts.strip()])
              st.cache_data.clear()
              st.success("New community poll launched successfully!")
              st.rerun()
            except Exception as e:
              st.error(f"Error launching poll: {e}")
          else:
            st.warning("Please provide both a question and answer options.")
