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
    page_title="TogetheSpace v0.2 — Secure Multi-Org Portal", page_icon="🏢", layout="wide"
)

# --- CUSTOM GOOGLE FONTS & STYLING ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif;
    }
    
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
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


# --- HELPER FOR DOB (SHOWING ONLY DAY & MONTH) ---
def format_dob(dob_str):
  dob_str = str(dob_str).strip()
  if not dob_str or dob_str.lower() == "none":
    return ""
  try:
    # Try parsing common formats like YYYY-MM-DD or DD-MM-YYYY
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%m/%d/%Y"):
      try:
        dt = datetime.strptime(dob_str, fmt)
        return dt.strftime("%B %d")  # e.g. "October 12"
      except ValueError:
        continue
    return dob_str  # Fallback if unparsable
  except Exception:
    return dob_str


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
          ["manager_apollo", default_pw_hash, "Apollo Hospital", "manager"],
          ["principal_xavier", default_pw_hash, "St. Xavier College", "manager"],
          ["manager_rotary", default_pw_hash, "Rotary Club of Calcutta", "manager"],
          ["manager_tech", default_pw_hash, "TechCorp India Pvt Ltd", "manager"],
          ["manager_metro", default_pw_hash, "Metro General Hospital", "manager"],
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
      return pd.DataFrame(
          columns=[
              "Notice ID",
              "Organization",
              "Title",
              "Content",
              "Date Posted",
              "Image File ID",
          ]
      )
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    if not df.empty:
      df.columns = df.columns.str.strip().str.lstrip("\ufeff")
    return df.fillna("")
  except Exception as e:
    return pd.DataFrame(
        columns=[
            "Notice ID",
            "Organization",
            "Title",
            "Content",
            "Date Posted",
            "Image File ID",
        ]
    )


@st.cache_data(ttl=30)
def load_posts_data():
  try:
    client = get_gspread_client()
    try:
      sheet = client.open_by_key(MASTER_SHEET_ID).worksheet("Posts")
    except Exception:
      return pd.DataFrame(
          columns=[
              "Post ID",
              "Organization",
              "Author Username",
              "Message",
              "Timestamp",
              "Image File ID",
          ]
      )
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    if not df.empty:
      df.columns = df.columns.str.strip().str.lstrip("\ufeff")
    return df.fillna("")
  except Exception as e:
    return pd.DataFrame(
        columns=[
            "Post ID",
            "Organization",
            "Author Username",
            "Message",
            "Timestamp",
            "Image File ID",
        ]
    )


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
    if df.empty or "Post ID" not in df.columns or "Username" not in df.columns:
      sheet.clear()
      sheet.append_row(["Post ID", "Username"])
      data = sheet.get_all_records()
      df = pd.DataFrame(data)

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
      data = sheet.get_all_records()
      df = pd.DataFrame(data)

    df.columns = df.columns.str.strip().str.lstrip("\ufeff")
    return df.fillna("")
  except Exception:
    return pd.DataFrame(columns=["Post ID", "Username", "Comment", "Timestamp"])


@st.cache_data(ttl=30)
def load_locality_data():
  try:
    client = get_gspread_client()
    spreadsheet = client.open_by_key(MASTER_SHEET_ID)
    try:
      sheet = spreadsheet.worksheet("LocalityBulletin")
    except Exception:
      sheet = spreadsheet.add_worksheet(title="LocalityBulletin", rows="500", cols="7")
      sheet.append_row([
          "Entry ID",
          "Organization",
          "Author",
          "Window",
          "Category",
          "Title & Details",
          "Image File ID",
      ])

    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    if df.empty or "Entry ID" not in df.columns:
      sheet.clear()
      sheet.append_row([
          "Entry ID",
          "Organization",
          "Author",
          "Window",
          "Category",
          "Title & Details",
          "Image File ID",
      ])
      data = sheet.get_all_records()
      df = pd.DataFrame(data)

    df.columns = df.columns.str.strip().str.lstrip("\ufeff")
    return df.fillna("")
  except Exception:
    return pd.DataFrame(
        columns=[
            "Entry ID",
            "Organization",
            "Author",
            "Window",
            "Category",
            "Title & Details",
            "Image File ID",
        ]
    )


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
      data = sheet.get_all_records()
      df = pd.DataFrame(data)
    else:
      for col in expected_cols:
        if col not in df.columns:
          df[col] = ""

    df.columns = df.columns.str.strip().str.lstrip("\ufeff")
    return df.fillna("")
  except Exception:
    return pd.DataFrame(columns=["Organization", "Sender", "Recipient", "Message", "Timestamp", "Image File ID", "ReadStatus"])


@st.cache_data(ttl=30)
def load_learning_hub_data():
  try:
    client = get_gspread_client()
    spreadsheet = client.open_by_key(MASTER_SHEET_ID)
    try:
      sheet = spreadsheet.worksheet("LearningHub")
    except Exception:
      sheet = spreadsheet.add_worksheet(title="LearningHub", rows="500", cols="6")
      sheet.append_row(["Session ID", "Organization", "Instructor", "Subject", "Description", "ScheduleLink"])

    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    if df.empty or "Session ID" not in df.columns:
      sheet.clear()
      sheet.append_row(["Session ID", "Organization", "Instructor", "Subject", "Description", "ScheduleLink"])
      data = sheet.get_all_records()
      df = pd.DataFrame(data)

    df.columns = df.columns.str.strip().str.lstrip("\ufeff")
    return df.fillna("")
  except Exception:
    return pd.DataFrame(columns=["Session ID", "Organization", "Instructor", "Subject", "Description", "ScheduleLink"])


# --- 3. SESSION STATE & URL QUERY PARAMS PERSISTENCE ---
query_params = st.query_params

if "authenticated" not in st.session_state:
  if (
      "user" in query_params
      and "role" in query_params
      and "org" in query_params
  ):
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
      <div style="text-align: center; padding: 20px;">
          <h1 style="color: #4f46e5; font-weight: 700;">🔐 TogetheSpace v0.2</h1>
          <h3 style="color: #64748b; font-weight: 400;">Secure Multi-Org Portal Login</h3>
      </div>
      """,
      unsafe_allow_html=True,
  )

  with st.form("login_form"):
    username_input = st.text_input("Username")
    password_input = st.text_input("Password", type="password")
    submit_login = st.form_submit_button("🚀 Login to Portal")

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

  st.sidebar.markdown(f"<h3 style='color: #4f46e5;'>🏢 {user_org}</h3>", unsafe_allow_html=True)
  st.sidebar.caption("✨ TogetheSpace v0.2")
  st.sidebar.markdown(f"**Logged in as:** `{current_user}`")
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
                users_sheet = client.open_by_key(MASTER_SHEET_ID).worksheet(
                    "Users"
                )
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

  # Calculate total unread private messages safely
  df_pm_all = load_private_messages_data()
  unread_count = 0
  if not df_pm_all.empty and "Recipient" in df_pm_all.columns and "ReadStatus" in df_pm_all.columns:
    unread_df = df_pm_all[
        (df_pm_all["Organization"].astype(str).str.strip() == user_org) &
        (df_pm_all["Recipient"].astype(str).str.strip() == current_user) &
        (df_pm_all["ReadStatus"].astype(str).str.strip() != "Read")
    ]
    unread_count = len(unread_df)

  pm_button_label = f"🔒 Private Messages ({unread_count})" if unread_count > 0 else "🔒 Private Messages"

  # --- SIDEBAR PUSH BUTTON NAVIGATION ---
  st.sidebar.markdown("### 🧭 Navigation Menu")

  if st.sidebar.button("📇 Member Directory", use_container_width=True):
    st.session_state["nav_page"] = "Directory"
    st.rerun()

  if st.sidebar.button("📢 Official Notice Board", use_container_width=True):
    st.session_state["nav_page"] = "Notice Board"
    st.rerun()

  if st.sidebar.button("💬 Community Feed", use_container_width=True):
    st.session_state["nav_page"] = "Community Feed"
    st.rerun()

  if st.sidebar.button(pm_button_label, use_container_width=True):
    st.session_state["nav_page"] = "Private Messages"
    st.rerun()

  if st.sidebar.button("📚 Teaching & Learning Hub", use_container_width=True):
    st.session_state["nav_page"] = "Learning Hub"
    st.rerun()

  if st.sidebar.button("🌟 Locality Attractions & Events", use_container_width=True):
    st.session_state["nav_page"] = "Locality Attractions"
    st.rerun()

  if current_role == "manager":
    if st.sidebar.button("🛠️ Manager Admin Portal", use_container_width=True):
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

  # --- DIRECTORY TAB (READ-ONLY) ---
  if current_tab == "Directory":
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #4f46e5 0%, #06b6d4 100%); padding: 20px; border-radius: 12px; color: white; margin-bottom: 20px;">
            <h1 style="margin:0; font-weight:700;">📇 {user_org} — Member Directory & SOS</h1>
            <p style="margin:5px 0 0 0; opacity: 0.9;">Secure organizational contacts and emergency medical info</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    search_query = st.sidebar.text_input("🔍 Search Directory (Name or Notes)")
    filtered_df = df_org.copy()

    if search_query and not filtered_df.empty:
      filtered_df = filtered_df[
          filtered_df["Full Name"].str.contains(search_query, case=False, na=False)
          | filtered_df["Notes"].str.contains(
              search_query, case=False, na=False
          )
      ]

    st.markdown(f"Showing **{len(filtered_df)}** records for **{user_org}**")

    if filtered_df.empty:
      st.warning("No entries found matching your search.")
    else:
      for _, row in filtered_df.iterrows():
        name = row.get("Full Name", "Member")
        blood = row.get("Blood Group", "N/A")
        bio_text = str(row.get("Bio", "")).strip()
        org_name = row.get("Organization", user_org)
        member_role = row.get("Role", "Member")
        raw_birthday = row.get("Birthday", "")
        formatted_dob = format_dob(raw_birthday)
        timezone = row.get("Timezone", "")
        notes = row.get("Notes", "")

        with st.expander(f"👤 {name}  |  🏢 {org_name}  |  🩸 Blood Group: {blood}"):
          if bio_text and bio_text != "None":
            st.info(f"**Bio:** {bio_text}")

          meta_cols = st.columns(4)
          with meta_cols[0]:
            st.markdown(f"**Role:** `{str(member_role).capitalize()}`")
          with meta_cols[1]:
            if formatted_dob:
              st.markdown(f"🎂 **Birthday:** {formatted_dob}")
          with meta_cols[2]:
            if timezone and timezone != "None":
              st.markdown(f"🌍 **Timezone:** {timezone}")
          with meta_cols[3]:
            if notes and notes != "None":
              st.markdown(f"📝 **Notes:** {notes}")

          st.markdown("---")
          col1, col2 = st.columns(2)

          with col1:
            st.subheader("📞 Communication Details")
            raw_address = str(row.get("Address", "None"))
            if raw_address and raw_address != "None":
              maps_url = f"https://www.google.com/maps/search/?api=1&query={raw_address.replace(' ', '+')}"
              st.markdown(f"**Address:** [{raw_address}]({maps_url}) (Click to view on Map)")
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
              if wa_chat.startswith("http"):
                wa_chat_url = wa_chat
              else:
                wa_digits = "".join(filter(str.isdigit, wa_chat))
                wa_chat_url = f"https://wa.me/{wa_digits}" if wa_digits else "#"
              st.markdown(f"**WhatsApp Chat:** [Open Chat]({wa_chat_url})")
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

  # --- NOTICE BOARD TAB ---
  elif current_tab == "Notice Board":
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #f59e0b 0%, #ef4444 100%); padding: 20px; border-radius: 12px; color: white; margin-bottom: 20px;">
            <h1 style="margin:0; font-weight:700;">📢 Official Notices — {user_org}</h1>
            <p style="margin:5px 0 0 0; opacity: 0.9;">Important announcements and updates from management</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    df_notices = load_notices_data()
    org_notices = (
        df_notices[df_notices["Organization"].str.strip() == user_org]
        if not df_notices.empty
        else pd.DataFrame()
    )

    if current_role == "manager":
      with st.expander("➕ Publish New Notice (Manager Only)", expanded=False):
        with st.form("notice_form", clear_on_submit=True):
          notice_title = st.text_input("Notice Title")
          notice_content = st.text_area("Notice Details / Content")
          notice_image = st.file_uploader(
              "Attach Image (Optional)", type=["png", "jpg", "jpeg"]
          )
          submit_notice = st.form_submit_button("Publish Notice")

          if submit_notice:
            if notice_title.strip() and notice_content.strip():
              try:
                image_data_str = ""
                if notice_image is not None:
                  image_data_str = process_image_to_base64(notice_image)

                client = get_gspread_client()
                notice_sheet = client.open_by_key(
                    MASTER_SHEET_ID
                ).worksheet("Notices")
                new_id = (
                    str(len(df_notices) + 1)
                    if not df_notices.empty
                    else "1"
                )
                today_date = datetime.now().strftime("%Y-%m-%d %H:%M")

                notice_sheet.append_row([
                    new_id,
                    user_org,
                    notice_title.strip(),
                    notice_content.strip(),
                    today_date,
                    image_data_str,
                ])
                st.cache_data.clear()
                st.success("Notice published successfully!")
                st.rerun()

              except Exception as e:
                st.error(f"Failed to publish notice: {e}")
            else:
              st.warning("Please fill in both title and content.")

    st.markdown("---")
    if org_notices.empty:
      st.info(
          "No official notices have been published for your organization yet."
      )
    else:
      for _, row in org_notices.iloc[::-1].iterrows():
        with st.container():
          st.subheader(f"📌 {row.get('Title', 'Notice')}")
          st.caption(
              f"Posted on: {row.get('Date Posted', 'Recent')} | Issuer:"
              f" Management"
          )
          st.write(row.get("Content", ""))

          img_data = str(row.get("Image File ID", "")).strip()
          if img_data and img_data != "None" and img_data != "":
            img_bytes = decode_base64_image(img_data)
            if img_bytes:
              st.image(img_bytes, caption="Notice Attachment", use_container_width=True)

          st.markdown("---")

  # --- COMMUNITY POSTS FEED TAB ---
  elif current_tab == "Community Feed":
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #10b981 0%, #3b82f6 100%); padding: 20px; border-radius: 12px; color: white; margin-bottom: 20px;">
            <h1 style="margin:0; font-weight:700;">💬 Community Discussion Feed — {user_org}</h1>
            <p style="margin:5px 0 0 0; opacity: 0.9;">Share updates, notes, and photos with your team</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    df_posts = load_posts_data()
    df_likes = load_likes_data()
    df_comments = load_comments_data()

    org_posts = (
        df_posts[df_posts["Organization"].str.strip() == user_org]
        if not df_posts.empty
        else pd.DataFrame()
    )

    with st.form("crisp_post_form", clear_on_submit=True):
      user_message = st.text_area("What's on your mind?", placeholder="Write a message or update...", height=80)
      
      c_col1, c_col2 = st.columns([2, 1])
      with c_col1:
        post_image = st.file_uploader(
            "Attach Image",
            type=["png", "jpg", "jpeg"],
            key="post_img_upload",
        )
      with c_col2:
        st.markdown("<br>", unsafe_allow_html=True)
        submit_post = st.form_submit_button("🚀 Publish Post", use_container_width=True)

      if submit_post:
        if user_message.strip() or post_image is not None:
          try:
            image_data_str = ""
            if post_image is not None:
              image_data_str = process_image_to_base64(post_image)

            client = get_gspread_client()
            posts_sheet = client.open_by_key(MASTER_SHEET_ID).worksheet("Posts")
            new_post_id = str(len(df_posts) + 1) if not df_posts.empty else "1"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            posts_sheet.append_row([
                new_post_id,
                user_org,
                current_user,
                user_message.strip(),
                timestamp,
                image_data_str,
            ])
            st.cache_data.clear()
            st.success("Post published successfully!")
            st.rerun()

          except Exception as e:
            st.error(f"Failed to publish post: {e}")
        else:
          st.warning("Please provide a message or attach an image to post.")

    st.markdown("---")
    st.subheader("Recent Group Activity")

    if org_posts.empty:
      st.info(
          "No community posts yet. Be the first to share an update with your"
          " team!"
      )
    else:
      pastel_colors = ["#f0f8ff", "#fff0f5", "#f0fff0", "#fffaf0", "#f8f0ff"]

      for idx, (_, row) in enumerate(org_posts.iloc[::-1].iterrows()):
        post_id = str(row.get("Post ID", ""))
        author = row.get("Author Username", "Member")
        timestamp = row.get("Timestamp", "")
        message = row.get("Message", "")
        img_data = str(row.get("Image File ID", "")).strip()

        card_bg = pastel_colors[idx % len(pastel_colors)]

        post_likes = (
            df_likes[df_likes["Post ID"].astype(str).str.strip() == post_id]
            if not df_likes.empty and "Post ID" in df_likes.columns
            else pd.DataFrame()
        )
        like_count = len(post_likes)
        user_has_liked = (
            not post_likes[
                post_likes["Username"].astype(str).str.strip() == current_user
            ].empty
            if not post_likes.empty and "Username" in post_likes.columns
            else False
        )

        post_comments = (
            df_comments[df_comments["Post ID"].astype(str).str.strip() == post_id]
            if not df_comments.empty and "Post ID" in df_comments.columns
            else pd.DataFrame()
        )
        comment_count = len(post_comments)

        is_saved = post_id in st.session_state["saved_posts"]

        msg_html = f"<div style='font-size: 15px; color: #0f1419; margin-bottom: 12px; line-height: 1.5; white-space: pre-wrap;'>{message}</div>" if message else ""
        
        img_html = ""
        if img_data and img_data != "None" and img_data != "":
          img_html = f"<div style='margin-top: 12px; margin-bottom: 4px;'><img src='data:image/jpeg;base64,{img_data}' style='width: 100%; border-radius: 8px; object-fit: cover;'/></div>"

        st.markdown(
            f"""
            <div style="background-color: {card_bg}; padding: 22px; border-radius: 12px; border: 1.5px solid #d0d7de; margin-bottom: 16px; box-shadow: 0 2px 6px rgba(0,0,0,0.03);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                    <div style="display: flex; align-items: center;">
                        <div style="background-color: #1da1f2; color: white; border-radius: 50%; width: 42px; height: 42px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 18px; margin-right: 12px;">
                            {author[0].upper()}
                        </div>
                        <div>
                            <div style="font-weight: bold; color: #0f1419; font-size: 16px;">{author} <span style="font-weight: normal; color: #536471; font-size: 13px;">({user_org})</span></div>
                            <div style="color: #536471; font-size: 12px;">🕒 {timestamp}</div>
                        </div>
                    </div>
                </div>
                {msg_html}
                {img_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

        if current_role == "manager" or current_user == author:
          del_col1, del_col2, del_col3, del_col4 = st.columns([1, 1, 1, 1])
          with del_col4:
            if st.button("🗑️ Delete Post", key=f"del_post_{post_id}"):
              try:
                client = get_gspread_client()
                posts_sheet = client.open_by_key(MASTER_SHEET_ID).worksheet("Posts")
                cell = posts_sheet.find(str(post_id))
                if cell:
                  posts_sheet.delete_rows(cell.row)
                  st.cache_data.clear()
                  st.success("Post successfully removed.")
                  st.rerun()
                else:
                  st.error("Post record not found in sheet.")
              except Exception as e:
                st.error(f"Failed to delete post: {e}")

        col_a, col_b, col_c, col_d = st.columns(4)

        with col_a:
          like_label = (
              f"❤️ {like_count} Liked"
              if user_has_liked
              else f"👍 {like_count} Like"
          )
          if st.button(like_label, key=f"like_btn_{post_id}"):
            try:
              client = get_gspread_client()
              spreadsheet = client.open_by_key(MASTER_SHEET_ID)
              try:
                likes_sheet = spreadsheet.worksheet("Likes")
              except Exception:
                likes_sheet = spreadsheet.add_worksheet(
                    title="Likes", rows="500", cols="2"
                )
                likes_sheet.append_row(["Post ID", "Username"])

              if user_has_liked:
                cell = likes_sheet.find(current_user)
                while cell:
                  row_vals = likes_sheet.row_values(cell.row)
                  if (
                      len(row_vals) >= 2
                      and str(row_vals[0]).strip() == str(post_id)
                      and str(row_vals[1]).strip() == current_user
                  ):
                    likes_sheet.delete_rows(cell.row)
                    break
                  cell = likes_sheet.find(current_user, in_column=2)
              else:
                likes_sheet.append_row([str(post_id), current_user])

              st.cache_data.clear()
              st.rerun()
            except Exception as e:
              st.error(f"Error updating like: {e}")

        with col_b:
          show_comments_key = f"show_comm_{post_id}"
          if show_comments_key not in st.session_state:
            st.session_state[show_comments_key] = False

          if st.button(
              f"💬 {comment_count} Comments", key=f"comm_btn_{post_id}"
          ):
            st.session_state[show_comments_key] = not st.session_state[
                show_comments_key
            ]

        with col_c:
          if st.button("🔄 Share", key=f"share_btn_{post_id}"):
            st.toast("🔗 Post link ready to share with team members!")

        with col_d:
          save_label = "🔖 Saved" if is_saved else "🏷️ Save"
          if st.button(save_label, key=f"save_btn_{post_id}"):
            if is_saved:
              st.session_state["saved_posts"].remove(post_id)
              st.toast("Post removed from saved bookmarks.")
            else:
              st.session_state["saved_posts"].append(post_id)
              st.toast("Post saved to bookmarks!")
            st.rerun()

        if st.session_state.get(f"show_comm_{post_id}", False):
          st.markdown(
              "<div style='background-color: #ffffff; padding: 14px;"
              " border-radius: 8px; margin-top: 8px; margin-bottom: 12px; border: 1px solid #d0d7de;'>",
              unsafe_allow_html=True,
          )
          st.markdown("**Comments Section**")

          if not post_comments.empty:
            for _, c_row in post_comments.iterrows():
              c_user = c_row.get("Username", "User")
              c_text = c_row.get("Comment", "")
              c_time = c_row.get("Timestamp", "")
              st.markdown(
                  f"💬 **{c_user}** <span"
                  f" style='font-size:11px;color:gray;'>({c_time})</span>: "
                  f"{c_text}",
                  unsafe_allow_html=True,
              )
          else:
            st.caption("No comments yet. Be the first to reply!")

          with st.form(key=f"comment_form_{post_id}", clear_on_submit=True):
            new_comment_text = st.text_input(
                "Write a comment...", key=f"input_comm_{post_id}"
            )
            submit_comment = st.form_submit_button("Post Comment")

            if submit_comment:
              if new_comment_text.strip():
                try:
                  client = get_gspread_client()
                  spreadsheet = client.open_by_key(MASTER_SHEET_ID)
                  try:
                    com_sheet = spreadsheet.worksheet("Comments")
                  except Exception:
                    com_sheet = spreadsheet.add_worksheet(
                        title="Comments", rows="500", cols="4"
                    )
                    com_sheet.append_row(
                        ["Post ID", "Username", "Comment", "Timestamp"]
                    )

                  comm_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                  com_sheet.append_row([
                      str(post_id),
                      current_user,
                      new_comment_text.strip(),
                      comm_timestamp,
                  ])
                  st.cache_data.clear()
                  st.success("Comment added!")
                  st.rerun()
                except Exception as e:
                  st.error(f"Failed to post comment: {e}")
              else:
                st.warning("Comment cannot be empty.")

          st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<hr style='margin: 24px 0; border: none; border-top: 1px solid #e1e8ed;'>", unsafe_allow_html=True)

  # --- PRIVATE MESSAGES TAB ---
  elif current_tab == "Private Messages":
    col_t1, col_t2 = st.columns([4, 1])
    with col_t1:
      st.markdown(
          f"""
          <div style="background: linear-gradient(135deg, #8b5cf6 0%, #ec4899 100%); padding: 20px; border-radius: 12px; color: white; margin-bottom: 20px;">
              <h1 style="margin:0; font-weight:700;">🔒 Secure Private Messages — {user_org}</h1>
              <p style="margin:5px 0 0 0; opacity: 0.9;">1-on-1 private messaging and photo sharing (Bridge mode)</p>
          </div>
          """,
          unsafe_allow_html=True,
      )
    with col_t2:
      st.markdown("<br>", unsafe_allow_html=True)
      if st.button("🔄 Refresh Chat", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    df_users_all = load_users_data()
    org_members = (
        df_users_all[df_users_all["Organization"].astype(str).str.strip() == user_org]["Username"].astype(str).str.strip().tolist()
        if not df_users_all.empty
        else []
    )
    if current_user in org_members:
      org_members.remove(current_user)

    if not org_members:
      st.info("No other members found in your organization to chat with.")
    else:
      selected_recipient = st.selectbox("Select Team Member to Chat With", org_members)

      if selected_recipient:
        st.markdown(f"### 💬 Conversation with `{selected_recipient}`")
        
        client_client = get_gspread_client()
        spreadsheet = client_client.open_by_key(MASTER_SHEET_ID)
        try:
          pm_sheet = spreadsheet.worksheet("PrivateMessages")
        except Exception:
          pm_sheet = spreadsheet.add_worksheet(title="PrivateMessages", rows="500", cols="7")
          pm_sheet.append_row(["Organization", "Sender", "Recipient", "Message", "Timestamp", "Image File ID", "ReadStatus"])

        all_pm_records = pm_sheet.get_all_records()
        df_pm = pd.DataFrame(all_pm_records)
        if not df_pm.empty:
          df_pm.columns = df_pm.columns.str.strip().str.lstrip("\ufeff")
          for idx, row in df_pm.iterrows():
            if (
                str(row.get("Organization", "")).strip() == user_org and
                str(row.get("Sender", "")).strip() == selected_recipient and
                str(row.get("Recipient", "")).strip() == current_user and
                str(row.get("ReadStatus", "")).strip() != "Read"
            ):
              try:
                pm_sheet.update_cell(idx + 2, 7, "Read")
              except Exception:
                pass

        df_pm_refreshed = load_private_messages_data()
        
        if not df_pm_refreshed.empty and "Sender" in df_pm_refreshed.columns:
          chat_filter = df_pm_refreshed[
              (df_pm_refreshed["Organization"].astype(str).str.strip() == user_org) &
              (
                  ((df_pm_refreshed["Sender"].astype(str).str.strip() == current_user) & (df_pm_refreshed["Recipient"].astype(str).str.strip() == selected_recipient)) |
                  ((df_pm_refreshed["Sender"].astype(str).str.strip() == selected_recipient) & (df_pm_refreshed["Recipient"].astype(str).str.strip() == current_user))
              )
          ]
        else:
          chat_filter = pd.DataFrame()

        chat_container = st.container()
        with chat_container:
          if chat_filter.empty:
            st.info("No messages yet. Start the conversation below!")
          else:
            for _, msg_row in chat_filter.iterrows():
              m_sender = str(msg_row.get("Sender", "")).strip()
              m_text = str(msg_row.get("Message", "")).strip()
              m_time = str(msg_row.get("Timestamp", "")).strip()
              m_img = str(msg_row.get("Image File ID", "")).strip()

              img_tag = ""
              if m_img and m_img != "None" and m_img != "":
                img_tag = f"<div style='margin-top: 6px;'><img src='data:image/jpeg;base64,{m_img}' style='max-width: 100%; border-radius: 6px;'/></div>"

              if m_sender == current_user:
                st.markdown(
                    f"""
                    <div style="background-color: #dcf8c6; padding: 10px 14px; border-radius: 10px; margin-bottom: 8px; margin-left: 20%; text-align: right; border: 1px solid #c5e1a5;">
                        <span style="font-size: 11px; color: #555;">You ({m_time})</span>
                        <div style="color: #000; font-size: 14px; margin-top: 2px; white-space: pre-wrap;">{m_text}</div>
                        {img_tag}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
              else:
                st.markdown(
                    f"""
                    <div style="background-color: #ffffff; padding: 10px 14px; border-radius: 10px; margin-bottom: 8px; margin-right: 20%; border: 1px solid #d0d7de;">
                        <span style="font-size: 11px; color: #555;">{m_sender} ({m_time})</span>
                        <div style="color: #000; font-size: 14px; margin-top: 2px; white-space: pre-wrap;">{m_text}</div>
                        {img_tag}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        with st.form(key="send_pm_form", clear_on_submit=True):
          new_msg = st.text_input("Type a private message...")
          pm_image = st.file_uploader("Attach Image (Optional)", type=["png", "jpg", "jpeg"], key="pm_img_upload")
          submit_pm = st.form_submit_button("Send Private Message")

          if submit_pm:
            if new_msg.strip() or pm_image is not None:
              try:
                img_data_str = ""
                if pm_image is not None:
                  img_data_str = process_image_to_base64(pm_image)

                client = get_gspread_client()
                spreadsheet = client.open_by_key(MASTER_SHEET_ID)
                try:
                  pm_sheet = spreadsheet.worksheet("PrivateMessages")
                except Exception:
                  pm_sheet = spreadsheet.add_worksheet(title="PrivateMessages", rows="500", cols="7")
                  pm_sheet.append_row(["Organization", "Sender", "Recipient", "Message", "Timestamp", "Image File ID", "ReadStatus"])

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                pm_sheet.append_row([user_org, current_user, selected_recipient, new_msg.strip(), timestamp, img_data_str, "Unread"])
                st.cache_data.clear()
                st.rerun()
              except Exception as e:
                st.error(f"Failed to send message: {e}")
            else:
              st.warning("Please type a message or attach an image.")

  # --- TEACHING & LEARNING HUB TAB ---
  elif current_tab == "Learning Hub":
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #0284c7 0%, #6366f1 100%); padding: 20px; border-radius: 12px; color: white; margin-bottom: 20px;">
            <h1 style="margin:0; font-weight:700;">📚 Teaching & Learning Hub — {user_org}</h1>
            <p style="margin:5px 0 0 0; opacity: 0.9;">Explore sessions on painting, cooking, online counseling, academics, and more!</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    df_hub = load_learning_hub_data()
    org_hub = (
        df_hub[df_hub["Organization"].str.strip() == user_org]
        if not df_hub.empty
        else pd.DataFrame()
    )

    with st.expander("➕ Host / Post a New Learning Session", expanded=False):
      with st.form("learning_session_form", clear_on_submit=True):
        subject_name = st.text_input("Subject / Skill (e.g., Oil Painting, Baking, Career Counseling)")
        session_desc = st.text_area("Session Description & Details")
        schedule_link = st.text_input("Meeting / Schedule Link (Zoom, Google Meet, or notes)")
        submit_session = st.form_submit_button("Publish Learning Session")

        if submit_session:
          if subject_name.strip() and session_desc.strip():
            try:
              client = get_gspread_client()
              hub_sheet = client.open_by_key(MASTER_SHEET_ID).worksheet("LearningHub")
              new_session_id = str(len(df_hub) + 1) if not df_hub.empty else "1"

              hub_sheet.append_row([
                  new_session_id,
                  user_org,
                  current_user,
                  subject_name.strip(),
                  session_desc.strip(),
                  schedule_link.strip(),
              ])
              st.cache_data.clear()
              st.success("Learning session published successfully!")
              st.rerun()
            except Exception as e:
              st.error(f"Failed to publish session: {e}")
          else:
            st.warning("Please provide a subject and description.")

    st.markdown("---")
    st.subheader("Available Teaching & Learning Sessions")

    if org_hub.empty:
      st.info("No learning sessions posted yet. Be the first teacher or student to host one!")
    else:
      for _, row in org_hub.iloc[::-1].iterrows():
        session_id = row.get("Session ID", "")
        instructor = row.get("Instructor", "")
        subject = row.get("Subject", "")
        description = row.get("Description", "")
        link = row.get("ScheduleLink", "")

        with st.container():
          st.markdown(
              f"""
              <div style="background-color: #ffffff; padding: 18px; border-radius: 10px; border: 1px solid #cbd5e1; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                  <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                      <span style="background-color: #0284c7; color: white; padding: 3px 10px; border-radius: 4px; font-size: 13px; font-weight: bold;">🎨 / 🍳 {subject}</span>
                      <span style="color: #64748b; font-size: 13px;">Instructor: <b>{instructor}</b></span>
                  </div>
                  <div style="font-size: 15px; color: #1e293b; line-height: 1.5; white-space: pre-wrap; margin-top: 8px;">{description}</div>
              </div>
              """,
              unsafe_allow_html=True,
          )

          if link and link != "None":
            if not link.startswith("http"):
              link = f"https://{link}"
            st.markdown(f"🔗 **Join / Schedule:** [Open Session Link]({link})")

          if current_role == "manager" or current_user == instructor:
            if st.button("🗑️ Delete Session", key=f"del_hub_{session_id}"):
              try:
                client = get_gspread_client()
                hub_sheet = client.open_by_key(MASTER_SHEET_ID).worksheet("LearningHub")
                cell = hub_sheet.find(str(session_id))
                if cell:
                  hub_sheet.delete_rows(cell.row)
                  st.cache_data.clear()
                  st.success("Session deleted successfully.")
                  st.rerun()
              except Exception as e:
                st.error(f"Failed to delete session: {e}")

          st.markdown("---")

  # --- LOCALITY ATTRACTIONS & EVENTS PORTAL ---
  elif current_tab == "Locality Attractions":
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%); padding: 20px; border-radius: 12px; color: white; margin-bottom: 20px;">
            <h1 style="margin:0; font-weight:700;">🌟 Locality Attractions, Business & Events Bulletin</h1>
            <p style="margin:5px 0 0 0; opacity: 0.9;">Indexed community facilities and local updates</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    df_locality = load_locality_data()

    if current_role == "manager":
      with st.expander("➕ Publish Daily Locality Bulletin (Manager Only)", expanded=False):
        with st.form("locality_form", clear_on_submit=True):
          b_window = st.selectbox("Update Window", ["Morning Window", "Afternoon Window"])
          b_category = st.selectbox("Category", ["Attractions", "Business", "Facilities", "Events"])
          b_title_details = st.text_area("Title & Details", placeholder="Enter attraction or event details...")
          b_image = st.file_uploader("Attach Image (Optional)", type=["png", "jpg", "jpeg"])
          submit_bulletin = st.form_submit_button("Publish Bulletin Entry")

          if submit_bulletin:
            if b_title_details.strip():
              try:
                img_str = ""
                if b_image is not None:
                  img_str = process_image_to_base64(b_image)

                client = get_gspread_client()
                loc_sheet = client.open_by_key(MASTER_SHEET_ID).worksheet("LocalityBulletin")
                new_entry_id = str(len(df_locality) + 1) if not df_locality.empty else "1"

                loc_sheet.append_row([
                    new_entry_id,
                    user_org,
                    current_user,
                    b_window,
                    b_category,
                    b_title_details.strip(),
                    img_str,
                ])
                st.cache_data.clear()
                st.success("Bulletin entry published successfully!")
                st.rerun()
              except Exception as e:
                st.error(f"Failed to publish bulletin: {e}")
            else:
              st.warning("Please provide title and details.")

    st.markdown("---")

    cat_filter = st.selectbox("Filter by Category (Index)", ["All Categories", "Attractions", "Business", "Facilities", "Events"])
    
    filtered_loc = df_locality.copy()
    if cat_filter != "All Categories" and not filtered_loc.empty:
      filtered_loc = filtered_loc[filtered_loc["Category"].str.strip() == cat_filter]

    if filtered_loc.empty:
      st.info("No locality updates published yet for this category.")
    else:
      for _, row in filtered_loc.iloc[::-1].iterrows():
        entry_id = row.get("Entry ID", "")
        org = row.get("Organization", "")
        author = row.get("Author", "")
        window = row.get("Window", "")
        category = row.get("Category", "")
        details = row.get("Title & Details", "")
        img_id = str(row.get("Image File ID", "")).strip()

        with st.container():
          st.markdown(
              f"""
              <div style="background-color: #ffffff; padding: 18px; border-radius: 10px; border: 1px solid #d0d7de; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                  <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                      <span style="background-color: #0366d6; color: white; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;">{category}</span>
                      <span style="color: #586069; font-size: 12px;">🕒 {window} | Issuer: {org}</span>
                  </div>
                  <div style="font-size: 15px; color: #24292e; line-height: 1.5; white-space: pre-wrap; margin-top: 8px;">{details}</div>
              </div>
              """,
              unsafe_allow_html=True,
          )

          if img_id and img_id != "None" and img_id != "":
            img_bytes = decode_base64_image(img_id)
            if img_bytes:
              st.image(img_bytes, use_container_width=True)

          if current_role == "manager" or current_user == author:
            if st.button("🗑️ Delete Bulletin", key=f"del_loc_{entry_id}"):
              try:
                client = get_gspread_client()
                loc_sheet = client.open_by_key(MASTER_SHEET_ID).worksheet("LocalityBulletin")
                cell = loc_sheet.find(str(entry_id))
                if cell:
                  loc_sheet.delete_rows(cell.row)
                  st.cache_data.clear()
                  st.success("Bulletin deleted successfully.")
                  st.rerun()
              except Exception as e:
                st.error(f"Failed to delete bulletin: {e}")

          st.markdown("---")

  # --- MANAGER ADMIN PORTAL TAB ---
  elif current_tab == "Manager Admin Portal" and current_role == "manager":
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #ef4444 0%, #f97316 100%); padding: 20px; border-radius: 12px; color: white; margin-bottom: 20px;">
            <h1 style="margin:0; font-weight:700;">🛠️ Manager Administrative Portal — {user_org}</h1>
            <p style="margin:5px 0 0 0; opacity: 0.9;">Staff accounts, offboarding, and directory management</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    admin_sub_tab = st.selectbox(
        "Manager Actions",
        [
            "Manage Directory",
            "Add New Employee Account",
            "Reset Employee Password",
            "Remove Employee Account (Offboarding)",
        ],
    )

    if admin_sub_tab == "Manage Directory":
      edited_org_df = st.data_editor(
          df_org, num_rows="dynamic", use_container_width=True
      )

      if st.button("Save Directory Changes to Google Drive"):
        try:
          client = get_gspread_client()
          sheet = client.open_by_key(MASTER_SHEET_ID).sheet1

          edited_org_df["Organization"] = user_org

          df_others = (
              df_master[df_master["Organization"].str.strip() != user_org]
              if not df_master.empty
              else pd.DataFrame()
          )
          df_final_save = pd.concat([df_others, edited_org_df], ignore_index=True)

          sheet.clear()
          sheet.update(
              [df_final_save.columns.values.tolist()]
              + df_final_save.values.tolist()
          )

          st.cache_data.clear()
          st.success(
              "Directory changes successfully saved and synced permanently!"
          )
        except Exception as e:
          st.error(f"Failed to save changes to Google Sheets: {e}")

    elif admin_sub_tab == "Add New Employee Account":
      st.subheader(f"Create Employee Login for {user_org}")
      st.markdown(
          "Set a custom unique username and initial temporary password for the"
          " employee."
      )

      with st.form("create_employee_form", clear_on_submit=True):
        new_emp_user = st.text_input("Employee Username (e.g., emp_apollo101)")
        new_emp_pass = st.text_input(
            "Initial Temporary Password", type="password"
        )
        submit_new_emp = st.form_submit_button("Create Account")

        if submit_new_emp:
          clean_emp_user = new_emp_user.strip()
          if not clean_emp_user or not new_emp_pass:
            st.warning("Please provide both username and password.")
          else:
            df_users_check = load_users_data()
            existing_usernames = (
                df_users_check["Username"].astype(str).str.strip().tolist()
                if not df_users_check.empty
                else []
            )

            if clean_emp_user in existing_usernames:
              st.error(
                  "This username is already taken. Please choose another one."
              )
            else:
              try:
                client = get_gspread_client()
                users_sheet = client.open_by_key(MASTER_SHEET_ID).worksheet(
                    "Users"
                )
                hashed_pw = hash_password(new_emp_pass)

                users_sheet.append_row(
                    [clean_emp_user, hashed_pw, user_org, "member"]
                )
                st.cache_data.clear()
                st.success(
                    f"Account for '{clean_emp_user}' created successfully under"
                    f" {user_org}!"
                )
              except Exception as e:
                st.error(f"Failed to create user account: {e}")

    elif admin_sub_tab == "Reset Employee Password":
      st.subheader(f"Reset Employee Password — {user_org}")
      st.markdown(
          "If an employee forgets their password, you can assign them a new"
          " temporary password here."
      )

      df_users_all = load_users_data()
      org_users = (
          df_users_all[
              (df_users_all["Organization"].astype(str).str.strip() == user_org)
              & (df_users_all["Role"].astype(str).str.strip() == "member")
          ]
          if not df_users_all.empty
          else pd.DataFrame()
      )

      if org_users.empty:
        st.info("No employee accounts found under your organization.")
      else:
        emp_usernames = org_users["Username"].astype(str).str.strip().tolist()
        with st.form("reset_emp_pass_form", clear_on_submit=True):
          selected_user_to_reset = st.selectbox(
              "Select Employee Username", emp_usernames
          )
          new_temp_pass = st.text_input(
              "New Temporary Password", type="password"
          )
          submit_reset = st.form_submit_button("Reset Password")

          if submit_reset:
            if not new_temp_pass:
              st.warning("Please enter a new password.")
            else:
              try:
                client = get_gspread_client()
                users_sheet = client.open_by_key(MASTER_SHEET_ID).worksheet(
                    "Users"
                )
                cell = users_sheet.find(selected_user_to_reset)
                if cell:
                  new_hash = hash_password(new_temp_pass)
                  users_sheet.update_cell(cell.row, 2, new_hash)
                  st.cache_data.clear()
                  st.success(
                      f"Password for '{selected_user_to_reset}' has been"
                      " successfully reset!"
                  )
                else:
                  st.error("User row not found in the Google Sheet.")
              except Exception as e:
                st.error(f"Failed to reset password: {e}")

    elif admin_sub_tab == "Remove Employee Account (Offboarding)":
      st.subheader(f"Remove Employee Account — {user_org}")
      st.markdown(
          "Select an employee username to immediately revoke their access when"
          " they leave the organization."
      )

      df_users_all = load_users_data()
      org_users = (
          df_users_all[
              (df_users_all["Organization"].astype(str).str.strip() == user_org)
              & (df_users_all["Role"].astype(str).str.strip() == "member")
          ]
          if not df_users_all.empty
          else pd.DataFrame()
      )

      if org_users.empty:
        st.info("No employee accounts found under your organization.")
      else:
        emp_usernames = org_users["Username"].astype(str).str.strip().tolist()
        selected_user_to_delete = st.selectbox(
            "Select Employee Username to Delete", emp_usernames
        )

        if st.button("Revoke & Delete Employee Account"):
          try:
            client = get_gspread_client()
            users_sheet = client.open_by_key(MASTER_SHEET_ID).worksheet(
                "Users"
            )
            cell = users_sheet.find(selected_user_to_delete)
            if cell:
              users_sheet.delete_rows(cell.row)
              st.cache_data.clear()
              st.success(
                  f"Account '{selected_user_to_delete}' has been permanently"
                  " deleted and access revoked."
              )
              st.rerun()
            else:
              st.error("User row not found in the Google Sheet.")
          except Exception as e:
            st.error(f"Failed to delete account: {e}")
