import time
import yaml
from yaml.loader import SafeLoader
from database import *
import streamlit_authenticator as st_auth

st.set_page_config(page_title="Stopwatch with Login & DB", page_icon="⏱️", layout="centered")

init_db()

# --- SESSION STATE ---
if "authentication_status" not in st.session_state:
    st.session_state.authentication_status = None
if "authenticator" not in st.session_state:
    st.session_state.authenticator = None
if "config" not in st.session_state:
    st.session_state.config = None
if "username" not in st.session_state:
    st.session_state.username = ""
if "start_time" not in st.session_state:
    st.session_state.start_time = None
if "elapsed_time" not in st.session_state:
    st.session_state.elapsed_time = 0.0
if "running" not in st.session_state:
    st.session_state.running = False

# --- load config ---
if not st.session_state.config:
    with open("config.yaml") as f:
        st.session_state.config = yaml.load(f, Loader=SafeLoader)

# --- authenticator ---
if not st.session_state.authentication_status:
    st.session_state.authenticator = st_auth.Authenticate(
        st.session_state.config["credentials"],
        st.session_state.config["cookie"]["name"],
        st.session_state.config["cookie"]["key"],
        st.session_state.config["cookie"]["expiry_days"],
    )

    # --- login UI (main area) ---
    st.session_state.authenticator.login("main")

if st.session_state.get("authentication_status") is False:
    st.error("Invalid username or password")
    st.session_state.elapsed_time = 0.0
    st.session_state.running = False
elif st.session_state.get("authentication_status") is None:
    st.warning("Please enter your username and password")
elif st.session_state.get("authentication_status"):
    # --- logged-in content ---
    st.sidebar.success(f"Signed in as {st.session_state.username}")
    st.session_state.authenticator.logout(button_name="Log out", location="sidebar")

    st.title(f"⏱️ Stopwatch — {st.session_state.name}")
    all_users = st.session_state.config["credentials"]["usernames"]
    is_admin = all_users[st.session_state.username]["admin"]
    if is_admin:
        with st.expander("Update Teams",expanded=False):
            df = pd.DataFrame({
                "username": list(all_users),
                "team": [all_users[u]["team"] for u in all_users]
            })

            # Keep editable state
            if "df" not in st.session_state:
                st.session_state.df = df

            edited_df = st.data_editor(
                df,
                num_rows="fixed",
                use_container_width=True,
                column_config={
                    "username": st.column_config.TextColumn(label="username", help="Unique user id", required=True, disabled=True),
                    "team": st.column_config.SelectboxColumn(label="team", options=["White", "Blue", "Coach"], required=True),
                }
            )
            if st.button("Update Teams"):
                usernames_to_update = edited_df["username"].tolist()
                teams_to_update = edited_df["team"].tolist()
                for u, t in zip(usernames_to_update, teams_to_update):
                    st.session_state.config["credentials"]["usernames"][u]["team"] = t
                with open("config.yaml", "w") as f:
                    yaml.dump(st.session_state.config, f)


    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("▶️ Start"):
            if not st.session_state.running:
                st.session_state.start_time = time.time() - st.session_state.elapsed_time
                st.session_state.running = True

    with col2:
        if st.button("⏸️ Stop"):
            if st.session_state.running:
                st.session_state.elapsed_time = time.time() - st.session_state.start_time
                st.session_state.running = False

    with col3:
        if st.button("🔁 Reset"):
            st.session_state.start_time = None
            st.session_state.elapsed_time = 0.0
            st.session_state.running = False

    if st.session_state.running:
        st.session_state.elapsed_time = time.time() - st.session_state.start_time

    st.metric("Elapsed Time (s)", f"{st.session_state.elapsed_time:.2f}")

    if st.button("💾 Save Time"):
        if st.session_state.elapsed_time > 0:
            save_time(
                username=st.session_state.username,
                team=st.session_state.config["credentials"]["usernames"][st.session_state.username]["team"],
                elapsed_seconds=float(st.session_state.elapsed_time),
            )
            st.success("Saved time successfully!")
            st.rerun()
        else:
            st.warning("You need to start the stopwatch first.")

    st.divider()
    st.subheader("📜 Saved Times")

    df = load_times()
    if df.empty:
        st.info("No times saved yet.")
    else:
        df["elapsed_seconds"] = df["elapsed_seconds"].round(2)
        st.dataframe(df, width="content", hide_index=True)
        if is_admin:
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download CSV", data=csv, file_name="my_times.csv", mime="text/csv")

            with st.expander("🗑️ Delete a saved run"):
                run_index = st.number_input(label="Enter Run Index to Delete", min_value=1, step=1)
                del_username = st.selectbox(label="Username to delete", options=st.session_state.config["credentials"]["usernames"])
                if st.button("Delete"):
                    delete_time(del_username, int(run_index))
                    st.success(f"Deleted run #{int(run_index)}.")
                    st.rerun()

    if st.session_state.running:
        time.sleep(0.1)
        st.rerun()

