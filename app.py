import base64
import datetime
from datetime import datetime
import io
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from PIL import Image
import streamlit as st

st.set_page_config(
    page_title="Multi-Org Secure Directory", page_icon="🏢", layout="wide"
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


# --- IMAGE PROCESSING & ENCODING (BYPASSES DRIVE STORAGE QUOTA) ---
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

      # Keep under Google Sheets single cell character limit (50,000 chars)
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


# --- 2. MASTER USER CREDENTIALS & ROLE MAPPING ---
MASTER_USERS = {
    "manager_apollo": {
        "password": "securepassword123",
        "org_name": "Apollo Hospital",
        "role": "manager",
    },
    "emp_apollo1": {
        "password": "password123",
        "org_name": "Apollo Hospital",
        "role": "member",
    },
    "principal_xavier": {
        "password": "xavierpassword",
        "org_name": "St. Xavier College",
        "role": "manager",
    },
    "student_xavier1": {
        "password": "password123",
        "org_name": "St. Xavier College",
        "role": "member",
    },
    "manager_rotary": {
        "password": "rotarypassword",
        "org_name": "Rotary Club of Calcutta",
        "role": "manager",
    },
    "member_rotary1": {
        "password": "password123",
        "org_name": "Rotary Club of Calcutta",
        "role": "member",
    },
    "manager_tech": {
        "password": "techpassword",
        "org_name": "TechCorp India Pvt Ltd",
        "role": "manager",
    },
    "member_tech1": {
        "password": "password123",
        "org_name": "TechCorp India Pvt Ltd",
        "role": "member",
    },
    "manager_metro": {
        "password": "metropassword",
        "org_name": "Metro General Hospital",
        "role": "manager",
    },
    "member_metro1": {
        "password": "password123",
        "org_name": "Metro General Hospital",
        "role": "member",
    },
}

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


# --- 4. DATA LOADERS FROM GOOGLE SHEETS ---
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


# --- 5. AUTHENTICATION / LOGIN VIEW ---
if not st.session_state["authenticated"]:
  st.title("🔐 Secure Multi-Organization Portal Login")
  st.markdown("Please log in using your assigned organizational credentials.")

  with st.form("login_persistent_form"):
    username_input = st.text_input("Username")
    password_input = st.text_input("Password", type="password")
    submit_button = st.form_submit_button("Login")

    if submit_button:
      clean_user = username_input.strip()
      user_data = MASTER_USERS.get(clean_user)

      if user_data and user_data["password"] == password_input:
        st.session_state["authenticated"] = True
        st.session_state["username"] = clean_user
        st.session_state["role"] = user_data["role"]
        st.session_state["org_name"] = user_data["org_name"]

        st.query_params["user"] = clean_user
        st.query_params["role"] = user_data["role"]
        st.query_params["org"] = user_data["org_name"]

        st.rerun()
      else:
        st.error(
            "Invalid username or password. Please check your credentials."
        )

# --- 6. AUTHENTICATED USER INTERFACE ---
else:
  df_master = load_master_data()
  user_org = st.session_state["org_name"]
  current_role = st.session_state["role"]
  current_user = st.session_state["username"]

  if not df_master.empty and "Organization" in df_master.columns:
    df_org = df_master[df_master["Organization"].str.strip() == user_org].copy()
  else:
    df_org = pd.DataFrame()

  st.sidebar.title(f"🏢 {user_org}")
  st.sidebar.markdown(f"**Logged in as:** `{current_user}`")
  st.sidebar.markdown(f"**Role:** `{current_role.capitalize()}`")

  if st.sidebar.button("Log Out"):
    st.session_state["authenticated"] = False
    st.session_state["username"] = ""
    st.session_state["role"] = ""
    st.session_state["org_name"] = ""
    st.query_params.clear()
    st.rerun()

  tabs = ["Directory", "📢 Notice Board", "💬 Community Feed"]
  if current_role == "manager":
    tabs.append("Manager Admin Portal")

  current_tab = st.sidebar.radio("Navigation", tabs)

  # --- DIRECTORY TAB (READ-ONLY) ---
  if current_tab == "Directory":
    st.title(f"📇 {user_org} - Member Directory & SOS")

    search_query = st.sidebar.text_input("Search Directory (Name or Notes)")
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

        with st.expander(f"👤 {name}  |  🩸 Blood Group: {blood}"):
          col1, col2 = st.columns(2)

          with col1:
            st.subheader("📞 Communication Details")
            raw_address = str(row.get("Address", "None"))
            if raw_address and raw_address != "None":
              maps_url = (
                  f"https://www.google.com/maps/search/?api=1&query={raw_address.replace(' ', '+')}"
              )
              st.markdown(
                  f"**Address:** [{raw_address}]({maps_url}) (Click to view on"
                  " Map)"
              )
            else:
              st.markdown("**Address:** None")

            phone = str(row.get("Phone Number", ""))
            st.markdown(f"**Phone:** [{phone}](tel:{phone})")

            wa_digits = "".join(
                filter(str.isdigit, str(row.get("WhatsApp Chat", "")))
            )
            wa_chat_url = f"https://wa.me/{wa_digits}" if wa_digits else "#"
            st.markdown(f"**WhatsApp Chat:** [Open Chat]({wa_chat_url})")

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
  elif current_tab == "📢 Notice Board":
    st.title(f"📢 Official Notices — {user_org}")
    st.markdown(
        "View official announcements and updates issued by your organization's"
        " management."
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
              st.image(img_bytes, caption="Notice Attachment", width=500)

          st.markdown("---")

  # --- COMMUNITY POSTS FEED TAB ---
  elif current_tab == "💬 Community Feed":
    st.title(f"💬 Community Discussion Feed — {user_org}")
    st.markdown(
        "Share updates, messages, or notes with other members of your"
        " organization."
    )

    df_posts = load_posts_data()
    org_posts = (
        df_posts[df_posts["Organization"].str.strip() == user_org]
        if not df_posts.empty
        else pd.DataFrame()
    )

    with st.form("new_post_form", clear_on_submit=True):
      st.markdown(f"**Posting as:** `{current_user}` ({user_org})")
      user_message = st.text_area("Write a message or update...")
      post_image = st.file_uploader(
          "Attach Image (Optional)",
          type=["png", "jpg", "jpeg"],
          key="post_img_upload",
      )
      submit_post = st.form_submit_button("Post to Group Feed")

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
            st.success("Post published to your group feed!")
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
      for _, row in org_posts.iloc[::-1].iterrows():
        author = row.get("Author Username", "Member")
        timestamp = row.get("Timestamp", "")
        message = row.get("Message", "")
        img_data = str(row.get("Image File ID", "")).strip()

        with st.chat_message("user"):
          st.markdown(f"**{author}**  *({timestamp})*")
          if message:
            st.write(message)
          if img_data and img_data != "None" and img_data != "":
            img_bytes = decode_base64_image(img_data)
            if img_bytes:
              st.image(img_bytes, width=400)

  # --- MANAGER ADMIN PORTAL TAB ---
  elif current_tab == "Manager Admin Portal" and current_role == "manager":
    st.title("🛠️ Manager Administrative Portal")
    st.markdown(
        "Add, update, or remove member records. Changes save **permanently**"
        f" to your Google Drive spreadsheet for **{user_org}**."
    )

    edited_org_df = st.data_editor(
        df_org, num_rows="dynamic", use_container_width=True
    )

    if st.button("Save Changes to Google Drive"):
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
            "Changes successfully saved and synced permanently to your Google"
            " Drive spreadsheet!"
        )
      except Exception as e:
        st.error(f"Failed to save changes to Google Sheets: {e}")
