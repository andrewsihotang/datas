import streamlit as st
import pandas as pd
import gspread
import json
from google.oauth2.service_account import Credentials
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import plotly.graph_objects as go
import plotly.express as px

# --- CSS for layout and header/logo tweaks, no tall vertical spacing ---
st.markdown(
    """
<style>
[data-testid="stAppViewContainer"] > .main {
    max-width: 100vw;
    padding-left: 20px;
    padding-right: 20px;
}
.block-container {
    max-width: 100vw;
    padding-top: 2rem;
    padding-bottom: 2rem;
    padding-left: 20px;
    padding-right: 20px;
}
.stDataFrameContainer, .css-1q8dd3e.e1fqkh3o4 {
    max-width: 100vw !important;
}
[data-testid="stSidebar"] {
    display: none;
}
/* aggrid small font for mobile */
@media (max-width: 700px) {
    .ag-root-wrapper, .ag-theme-streamlit input { font-size:11px !important; }
    .ag-header-cell-label, .ag-cell { font-size:10px !important; }
}
/* LOGO HEADER ROW FOR LANDING PAGE */
.landing-header {
    width: 100%;
    display: flex;
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
    margin-top: 12px;
    margin-bottom: 16px;
}
.landing-header .header-group {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 10px;
}
.landing-header .header-logo {
    height: 46px;
}
.landing-header .header-text {
    font-size: 1rem;
    font-weight: 500;
    line-height: 1.1;
}
/* Move up the landing content */
.landing-centered-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-start;
    margin-top: 0px;
    margin-bottom: 0px;
    padding-top: 10px;
    padding-bottom: 10px;
    min-height: unset !important;
    height: auto !important;
}
.landing-centered-content h1, .landing-centered-content h2 {
    text-align: center;
    margin-bottom: 6px;
    margin-top: 0px;
}
.landing-centered-content button {
    margin-top: 18px;
    width: 120px;
}
</style>
""",
    unsafe_allow_html=True,
)

DISDIK_LOGO_URL = "https://raw.githubusercontent.com/andrewsihotang/datas/main/disdik_jakarta.png"
P4_LOGO_URL = "https://raw.githubusercontent.com/andrewsihotang/datas/main/p4.png"

if "page" not in st.session_state:
    st.session_state.page = "landing"


def show_landing_page():
    st.markdown(
        f"""
        <div class="landing-header">
            <div class="header-group">
                <img src="{DISDIK_LOGO_URL}" class="header-logo" alt="Dinas Pendidikan" />
                <div class="header-text">Dinas Pendidikan Provinsi DKI Jakarta</div>
            </div>
            <div class="header-group">
                <img src="{P4_LOGO_URL}" class="header-logo" alt="P4" />
                <div class="header-text">P4 Jakarta Utara dan Kepulauan Seribu</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="landing-centered-content">', unsafe_allow_html=True)
    st.title("SIPADU")
    st.subheader("Sistem Pangkalan Data Utama P4 Jakarta Utara dan Kepulauan Seribu")
    if st.button("Mulai"):
        st.session_state.page = "main"
    st.markdown("</div>", unsafe_allow_html=True)


def reset_filters(options_dict):
    for key, default in options_dict.items():
        st.session_state[key] = default


def load_gsheet_to_df(json_keyfile_str, spreadsheet_id, sheet_name):
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds_dict = json.loads(json_keyfile_str)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    df.columns = df.columns.str.strip()
    return df


def load_data_from_gsheets(json_keyfile_str, spreadsheet_id, sheet_name):
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds_dict = json.loads(json_keyfile_str)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    df.columns = df.columns.str.strip()
    df["TANGGAL"] = pd.to_datetime(df["TANGGAL"])
    if "NPSN" in df.columns:
        df["NPSN"] = df["NPSN"].astype(str)
    if "STASUS_SEKOLAH" in df.columns:
        df.rename(columns={"STASUS_SEKOLAH": "STATUS_SEKOLAH"}, inplace=True)
    if "STATUS_SEKOLAH" not in df.columns:
        df["STATUS_SEKOLAH"] = pd.NA
    return df


def get_target_school_count(sheet_df, jenjang_type):
    kabupaten_filter = ["KAB. ADM. KEP. SERIBU", "KOTA ADM. JAKARTA UTARA"]
    pembina_filter = "KEMENTERIAN PENDIDIKAN DASAR DAN MENENGAH"

    # First check if required columns exist to prevent errors
    for col in ["Status", "Kabupaten", "Pembina", "Nama Sekolah"]:
        if col not in sheet_df.columns:
            return 0

    if jenjang_type == "PAUD":
        filtered_df = sheet_df[
            (sheet_df["Status"] == "Negeri")
            & (sheet_df["Kabupaten"].isin(kabupaten_filter))
            & (sheet_df["Pembina"] == pembina_filter)
        ]
    elif jenjang_type == "DIKMAS":
        if "Bentuk" not in sheet_df.columns:
            return 0
        filtered_df = sheet_df[
            (sheet_df["Status"] == "Negeri")
            & (sheet_df["Kabupaten"].isin(kabupaten_filter))
            & (sheet_df["Pembina"] == pembina_filter)
            & (~sheet_df["Bentuk"].str.contains("KURSUS", case=False, na=False))
        ]
    elif jenjang_type == "DIKDAS":
        filtered_df = sheet_df[
            (sheet_df["Kabupaten"].isin(kabupaten_filter))
            & (sheet_df["Pembina"] == pembina_filter)
        ]
    elif jenjang_type == "DIKMEN":
        filtered_df = sheet_df[
            (sheet_df["Kabupaten"].isin(kabupaten_filter))
            & (sheet_df["Pembina"] == pembina_filter)
        ]
    else:
        filtered_df = sheet_df.iloc[0:0]
    return filtered_df["Nama Sekolah"].nunique() if "Nama Sekolah" in filtered_df.columns else 0


def main_app():
    st.markdown("<br>", unsafe_allow_html=True)
    colbtn1, colbtn2, _ = st.columns([1, 1, 8])
    with colbtn1:
        if st.button("Refresh Data"):
            st.cache_data.clear()
            st.experimental_rerun()
    with colbtn2:
        if st.button("Reset Filter"):
            filter_defaults = {
                "jenjang_filter": [],
                "kecamatan_filter": [],
                "nama_pelatihan_filter": [],
                "pelatihan_filter": [],
                "status_sekolah_filter": [],
                "date_range": [],
            }
            reset_filters(filter_defaults)

    # Load main pelatihan sheets and add the CATEGORY column
    json_keyfile_str = st.secrets["GSHEET_SERVICE_ACCOUNT"]
    spreadsheet_id = "1_YeSK2zgoExnC8n6tlmoJFQDVEWZbncdBLx8S5k-ljc"
    sheet_names = ["Tendik", "Pendidik", "Kejuruan"]

    dfs = []
    for sheet_name in sheet_names:
        df_sheet = load_data_from_gsheets(json_keyfile_str, spreadsheet_id, sheet_name)
        df_sheet["CATEGORY"] = sheet_name
        dfs.append(df_sheet)
    df = pd.concat(dfs, ignore_index=True)

    st.title("Data Peserta Pelatihan Tenaga Kependidikan")

    # Filters area
    col1, col2, col3, col4, col5, col6 = st.columns([1, 1, 1, 1, 1, 1])
    with col1:
        jenjang_filter = st.multiselect(
            "JENJANG",
            df["JENJANG"].dropna().unique(),
            key="jenjang_filter",
            default=st.session_state.get("jenjang_filter", []),
        )
    with col2:
        kecamatan_filter = st.multiselect(
            "KECAMATAN",
            df["KECAMATAN"].dropna().unique(),
            key="kecamatan_filter",
            default=st.session_state.get("kecamatan_filter", []),
        )
    with col3:
        nama_pelatihan_filter = st.multiselect(
            "NAMA PELATIHAN",
            df["NAMA_PELATIHAN"].dropna().unique(),
            key="nama_pelatihan_filter",
            default=st.session_state.get("nama_pelatihan_filter", []),
        )
    with col4:
        pelatihan_filter = st.multiselect(
            "PELATIHAN",
            df["CATEGORY"].unique(),
            key="pelatihan_filter",
            default=st.session_state.get("pelatihan_filter", []),
        )
    with col5:
        status_options = df["STATUS_SEKOLAH"].dropna().unique() if "STATUS_SEKOLAH" in df.columns else []
        status_sekolah_filter = st.multiselect(
            "STATUS SEKOLAH",
            status_options,
            key="status_sekolah_filter",
            default=st.session_state.get("status_sekolah_filter", []),
        )
    with col6:
        date_range = st.date_input(
            "TANGGAL",
            value=st.session_state.get("date_range", []),
            key="date_range",
        )

    conditions = []
    if jenjang_filter:
        conditions.append(df["JENJANG"].isin(jenjang_filter))
    if kecamatan_filter:
        conditions.append(df["KECAMATAN"].isin(kecamatan_filter))
    if nama_pelatihan_filter:
        conditions.append(df["NAMA_PELATIHAN"].isin(nama_pelatihan_filter))
    if pelatihan_filter:
        conditions.append(df["CATEGORY"].isin(pelatihan_filter))
    if status_sekolah_filter:
        conditions.append(df["STATUS_SEKOLAH"].isin(status_sekolah_filter))
    if len(date_range) == 2:
        start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
        conditions.append((df["TANGGAL"] >= start_date) & (df["TANGGAL"] <= end_date))

    if conditions:
        filter_condition = conditions[0]
        for cond in conditions[1:]:
            filter_condition &= cond
    else:
        filter_condition = pd.Series([True] * len(df))

    filtered_df = df[filter_condition]

    if "NO" in filtered_df.columns:
        filtered_df = filtered_df.drop(columns=["NO"])

    filtered_df = filtered_df.reset_index(drop=True)
    filtered_df.index = filtered_df.index + 1
    filtered_df["TANGGAL"] = filtered_df["TANGGAL"].dt.strftime("%Y-%m-%d")

    cols = list(filtered_df.columns)
    if "STATUS_SEKOLAH" in cols and "ASAL_SEKOLAH" in cols:
        cols.remove("STATUS_SEKOLAH")
        asal_idx = cols.index("ASAL_SEKOLAH")
        cols.insert(asal_idx + 1, "STATUS_SEKOLAH")
        display_df = filtered_df[cols]
    else:
        display_df = filtered_df

    st.write(f"Showing {display_df.shape[0]} records")

    view_mode = st.radio("Table view mode:", ["Full Table View", "Compact Table View"], horizontal=True)
    if view_mode == "Compact Table View":
        compact_cols = ["NAMA_PESERTA", "NAMA_PELATIHAN", "TANGGAL"]
        display_df_view = display_df[compact_cols].copy()
    else:
        display_df_view = display_df.copy()

    gb = GridOptionsBuilder.from_dataframe(display_df_view)
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)
    gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc="sum", editable=False)
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    grid_options = gb.build()
    grid_response = AgGrid(
        display_df_view,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        height=500,
        fit_columns_on_grid_load=True,
        reload_data=True,
    )
    selected = grid_response["selected_rows"]
    if selected and len(selected) > 0:
        if isinstance(selected, pd.DataFrame):
            selected_list = selected.to_dict(orient="records")
        else:
            selected_list = selected
        selected_name = selected_list[0].get("NAMA_PESERTA", "")
        st.markdown("### Detail Peserta")
        st.write(f"Semua pelatihan yang diikuti oleh: **{selected_name}**")
        participant_trainings = filtered_df[filtered_df["NAMA_PESERTA"] == selected_name][
            ["NAMA_PELATIHAN", "TANGGAL", "ASAL_SEKOLAH", "NPSN"]
        ].drop_duplicates().reset_index(drop=True)
        participant_trainings.index = participant_trainings.index + 1
        st.dataframe(participant_trainings)
        st.write(f"Jumlah pelatihan: {participant_trainings.shape[0]}")

    st.markdown("*Data cutoff: 08 September 2025*")
    st.markdown("---")

    pelatihan_selected = None
    if pelatihan_filter and len(pelatihan_filter) == 1:
        pelatihan_selected = pelatihan_filter[0]

    title_prefix_map = {
        "Tendik": "Tendik",
        "Pendidik": "Pendidik",
        "Kejuruan": "Kejuruan",
    }
    prefix_name = title_prefix_map.get(pelatihan_selected, "Tenaga Kependidikan")

    targets_by_category = {
        "Tendik": {
            "jenjang": {
                "DIKMAS": 284,
                "PAUD": 2292,
                "SD": 2556,
                "SMP": 1500,
                "SMA": 801,
                "SMK": 636,
            },
            "sekolah": {
                "PAUD": 855,
                "DIKMAS": 149,
                "SD": 424,
                "SMP": 239,
                "SMA": 111,
                "SMK": 76,
            },
        },
        "Pendidik": {
            "jenjang": {
                "DIKMAS": 150,
                "PAUD": 1000,
                "SD": 1200,
                "SMP": 900,
                "SMA": 500,
                "SMK": 450,
            },
            "sekolah": {
                "PAUD": 400,
                "DIKMAS": 80,
                "SD": 350,
                "SMP": 210,
                "SMA": 90,
                "SMK": 65,
            },
        },
        "Kejuruan": {
            "jenjang": {
                "DIKMAS": 100,
                "PAUD": 200,
                "SD": 300,
                "SMP": 400,
                "SMA": 250,
                "SMK": 180,
            },
            "sekolah": {
                "PAUD": 100,
                "DIKMAS": 60,
                "SD": 120,
                "SMP": 80,
                "SMA": 40,
                "SMK": 30,
            },
        },
    }

    default_targets = targets_by_category["Tendik"]

    jenjang_targets = default_targets["jenjang"]
    sekolah_targets = default_targets["sekolah"]
    if pelatihan_selected in targets_by_category:
        jenjang_targets = targets_by_category[pelatihan_selected]["jenjang"]
        sekolah_targets = targets_by_category[pelatihan_selected]["sekolah"]

    # Load school reference sheets with caching
    @st.cache_data
    def load_school_reference_sheets():
        paud_df = load_gsheet_to_df(json_keyfile_str, spreadsheet_id, "PAUD")
        dikmas_df = load_gsheet_to_df(json_keyfile_str, spreadsheet_id, "DIKMAS")
        dikdas_df = load_gsheet_to_df(json_keyfile_str, spreadsheet_id, "DIKDAS")
        dikmen_df = load_gsheet_to_df(json_keyfile_str, spreadsheet_id, "DIKMEN")
        return paud_df, dikmas_df, dikdas_df, dikmen_df

    paud_df, dikmas_df, dikdas_df, dikmen_df = load_school_reference_sheets()

    def get_unique_filtered_school_count(jenjang):
        if jenjang == "PAUD":
            return get_target_school_count(paud_df, "PAUD")
        elif jenjang == "DIKMAS":
            return get_target_school_count(dikmas_df, "DIKMAS")
        elif jenjang in ["SD", "SMP"]:
            return get_target_school_count(dikdas_df, "DIKDAS")
        elif jenjang in ["SMA", "SMK"]:
            return get_target_school_count(dikmen_df, "DIKMEN")
        else:
            return 0

    # Summary by Jenjang - cap percentage at 100%
    summary_rows = []
    for jenjang, target in jenjang_targets.items():
        df_jenjang = filtered_df[
            (filtered_df["JENJANG"] == jenjang)
            & (filtered_df["NPSN"].notna())
            & (filtered_df["NPSN"].astype(str) != "0")
        ]
        unique_count = df_jenjang["NAMA_PESERTA"].nunique()

        denominator = max(target, unique_count)
        percent = (unique_count / denominator * 100) if denominator else 0
        percent = min(percent, 100)

        kurang = max(0, target - unique_count) if unique_count < target else 0
        summary_rows.append(
            {
                "Jenjang": jenjang,
                "Target Jumlah Peserta Pelatihan": f"{target:,} Orang",
                "Jumlah Peserta Pelatihan (unique)": f"{unique_count:,} Orang",
                "Persentase": f"{percent:.2f} %",
                "Kurang": f"{kurang:,} Orang",
            }
        )
    df_summary = pd.DataFrame(summary_rows)
    df_summary.index = df_summary.index + 1
    df_summary = df_summary[
        [
            "Jenjang",
            "Target Jumlah Peserta Pelatihan",
            "Jumlah Peserta Pelatihan (unique)",
            "Persentase",
            "Kurang",
        ]
    ]

    st.write(f"### Rekap Pencapaian Pelatihan {prefix_name} berdasarkan Jenjang")
    st.dataframe(df_summary)

    # Summary by Jumlah Sekolah with correct target from filtered school sheets and cap percentage
    sekolah_rows = []
    for jenjang, target in sekolah_targets.items():
        unique_schools_data = (
            filtered_df[
                (filtered_df["JENJANG"] == jenjang)
                & (filtered_df["ASAL_SEKOLAH"].notna())
                & (filtered_df["ASAL_SEKOLAH"] != "")
            ]["ASAL_SEKOLAH"].nunique()
        )
        unique_schools_ref = get_unique_filtered_school_count(jenjang)
        unique_schools = max(unique_schools_data, unique_schools_ref)

        # Cap percentage calculation
        calc_target = target
        if target < unique_schools:
            calc_target = unique_schools
        percent = (unique_schools / calc_target * 100) if calc_target else 0
        percent = min(percent, 100)

        kurang = max(0, target - unique_schools) if unique_schools < target else 0
        sekolah_rows.append(
            {
                "Jenjang": jenjang,
                "Target Jumlah Sekolah": f"{target:,} Sekolah",
                "Jumlah Sekolah (unique)": f"{unique_schools:,} Sekolah",
                "Persentase": f"{percent:.2f} %",
                "Kurang": f"{kurang:,} Sekolah",
            }
        )
    df_sekolah = pd.DataFrame(sekolah_rows)
    df_sekolah.index = df_sekolah.index + 1
    df_sekolah = df_sekolah[
        [
            "Jenjang",
            "Target Jumlah Sekolah",
            "Jumlah Sekolah (unique)",
            "Persentase",
            "Kurang",
        ]
    ]

    st.write(f"### Rekap Pencapaian Pelatihan {prefix_name} berdasarkan Jumlah Sekolah")
    st.markdown("*Data cutoff: 08 September 2025*")
    st.dataframe(df_sekolah)

    st.write("---")
    st.header("Upload Data Terbaru")
    upload_category = st.selectbox("Pilih kategori pelatihan untuk ditambahkan data", sheet_names)
    uploaded_file = st.file_uploader(
        f"Upload file CSV atau Excel untuk pelatihan '{upload_category}' (format sesuai template)",
        type=["csv", "xlsx"],
    )
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".csv"):
                new_data = pd.read_csv(uploaded_file, sep=";")
            else:
                new_data = pd.read_excel(uploaded_file)
            st.write("Pratinjau data yang diunggah:")
            st.dataframe(new_data)
            expected_columns = df.columns.drop("CATEGORY", errors="ignore").tolist()
            if not all(col in new_data.columns for col in expected_columns):
                st.error(f"File unggahan kehilangan beberapa kolom wajib: {expected_columns}")
            else:
                for col in new_data.select_dtypes(include=["datetime64", "datetimetz"]).columns:
                    new_data[col] = new_data[col].dt.strftime("%Y-%m-%d")
                if st.button("Tambahkan data ke Google Sheet"):
                    try:
                        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
                        creds_dict = json.loads(st.secrets["GSHEET_SERVICE_ACCOUNT"])
                        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
                        client = gspread.authorize(creds)
                        sheet = client.open_by_key(spreadsheet_id).worksheet(upload_category)
                        existing_data = sheet.get_all_values()
                        if len(existing_data) == 0:
                            combined_data = [new_data.columns.values.tolist()] + new_data.values.tolist()
                        else:
                            existing_rows = existing_data[1:]
                            existing_df = pd.DataFrame(existing_rows, columns=existing_data[0])
                            combined_df = pd.concat([existing_df, new_data], ignore_index=True)
                            combined_data = [combined_df.columns.values.tolist()] + combined_df.values.tolist()
                        sheet.clear()
                        sheet.update(combined_data)
                        st.success(f"Data berhasil ditambahkan ke sheet '{upload_category}'!")
                    except Exception as e:
                        st.error(f"Gagal menambahkan data: {e}")
        except Exception as e:
            st.error(f"Gagal membaca file unggahan: {e}")

    st.markdown(
        """
        <hr>
        <div style="text-align: center; margin-top: 20px;">
            <a href="https://www.instagram.com/p4jakut_ks?igsh=c3Mya2dodm5hbHU1" target="_blank" style="margin: 0 20px; display: inline-block; text-decoration: none; color: inherit;">
                <img src="https://raw.githubusercontent.com/andrewsihotang/datas/main/instagrams.png" alt="Instagram" width="32" height="32" />
                <div style="font-size: 0.7rem; margin-top: 4px;">Instagram P4 JUKS</div>
            </a>
            <a href="https://www.tiktok.com/@p4.juks?_t=ZS-8zKsAgWjXJQ&_r=1" target="_blank" style="margin: 0 20px; display: inline-block; text-decoration: none; color: inherit;">
                <img src="https://raw.githubusercontent.com/andrewsihotang/datas/main/tiktok.png" alt="TikTok" width="32" height="32" />
                <div style="font-size: 0.7rem; margin-top: 4px;">TikTok P4 JUKS</div>
            </a>
            <a href="https://youtube.com/@p4jakartautaradankep-seribu?si=BWAVvVyVdYvbj8Xo" target="_blank" style="margin: 0 20px; display: inline-block; text-decoration: none; color: inherit;">
                <img src="https://raw.githubusercontent.com/andrewsihotang/datas/main/youtube.png" alt="YouTube" width="32" height="32" />
                <div style="font-size: 0.7rem; margin-top: 4px;">YouTube P4 JUKS</div>
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )


if st.session_state.page == "landing":
    show_landing_page()
elif st.session_state.page == "main":
    main_app()
else:
    st.session_state.page = "landing"
    show_landing_page()
