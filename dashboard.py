import streamlit as st
import pandas as pd
import gspread
import json
from google.oauth2.service_account import Credentials
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

# --- CSS for layout and header/logo tweaks, no tall vertical spacing ---
st.set_page_config(layout="wide") # Set the page to wide mode by default

st.markdown("""
<style>
/* General layout adjustments */
.block-container {
    max-width: 95vw;
    padding-top: 2rem;
    padding-bottom: 2rem;
    padding-left: 20px;
    padding-right: 20px;
}
.stDataFrameContainer, .ag-root-wrapper {
    max-width: 100% !important;
}
[data-testid="stSidebar"] {
    display: none;
}
/* Responsive font sizes for the table */
@media (max-width: 700px) {
    .ag-root-wrapper, .ag-theme-streamlit input { font-size:11px !important; }
    .ag-header-cell-label, .ag-cell { font-size:10px !important; }
}
/* Header styling */
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
/* Centered content for landing page */
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
""", unsafe_allow_html=True)

DISDIK_LOGO_URL = "https://raw.githubusercontent.com/andrewsihotang/datas/main/disdik_jakarta.png"
P4_LOGO_URL = "https://raw.githubusercontent.com/andrewsihotang/datas/main/p4.png"

if "page" not in st.session_state:
    st.session_state.page = "landing"

def show_landing_page():
    st.markdown(
        f'''
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
        ''',
        unsafe_allow_html=True
    )
    st.markdown('<div class="landing-centered-content">', unsafe_allow_html=True)
    st.title("SIPADU")
    st.subheader("Sistem Pangkalan Data Utama")
    st.subheader("P4 Jakarta Utara dan Kepulauan Seribu")
    if st.button("Mulai"):
        st.session_state.page = "main"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

def reset_filters(options_dict):
    for key, default in options_dict.items():
        st.session_state[key] = default

def main_app():
    st.markdown("<br>", unsafe_allow_html=True)
    colbtn1, colbtn2, _ = st.columns([1, 1, 8])
    with colbtn1:
        if st.button("Refresh Data"):
            st.cache_data.clear()
            st.rerun()
    with colbtn2:
        if st.button("Reset Filter"):
            filter_defaults = {
                "jenjang_filter": [], "kecamatan_filter": [], "nama_pelatihan_filter": [],
                "pelatihan_filter": [], "status_sekolah_filter": [], "date_range": [],
                "summary_status_filter": [], "summary_kabupaten_filter": []
            }
            reset_filters(filter_defaults)
            st.rerun()

    @st.cache_data
    def load_data_from_gsheets(json_keyfile_str, spreadsheet_id, sheet_name):
        scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        creds_dict = json.loads(json_keyfile_str)
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        return df

    @st.cache_data
    def load_school_data(json_keyfile_str, spreadsheet_id):
        df_sekolah = load_data_from_gsheets(json_keyfile_str, spreadsheet_id, 'data_sekolah')
        df_sekolah.columns = [col.strip().upper() for col in df_sekolah.columns]
        df_sekolah['TIPE'].replace('', pd.NA, inplace=True)
        df_sekolah.dropna(subset=['TIPE'], inplace=True)
        return df_sekolah

    # --- Load Data ---
    json_keyfile_str = st.secrets["GSHEET_SERVICE_ACCOUNT"]
    spreadsheet_id = '1_YeSK2zgoExnC8n6tlmoJFQDVEWZbncdBLx8S5k-ljc'
    sheet_names = ['Tendik', 'Pendidik', 'Kejuruan']
    dfs = [load_data_from_gsheets(json_keyfile_str, spreadsheet_id, name) for name in sheet_names]
    df = pd.concat(dfs, ignore_index=True)
    df_sekolah_sumber = load_school_data(json_keyfile_str, spreadsheet_id)

    # --- Data Cleaning ---
    df.columns = [col.strip().upper() for col in df.columns]
    if 'STASUS_SEKOLAH' in df.columns:
        df.rename(columns={'STASUS_SEKOLAH': 'STATUS_SEKOLAH'}, inplace=True)
    df = df.loc[:, ~df.columns.duplicated(keep='first')]
    df['TANGGAL'] = pd.to_datetime(df['TANGGAL'], errors='coerce')
    if 'NPSN' in df.columns:
        df['NPSN'] = df['NPSN'].astype(str)
    if 'STATUS_SEKOLAH' not in df.columns:
        df['STATUS_SEKOLAH'] = pd.NA

    pelatihan_choice = st.session_state.get("pelatihan_filter", [None])[0] if len(st.session_state.get("pelatihan_filter", [])) == 1 else None
    title_map = {'Tendik': 'Data Peserta Pelatihan Tenaga Kependidikan', 'Pendidik': 'Data Peserta Pelatihan Pendidik', 'Kejuruan': 'Data Peserta Pelatihan Kejuruan'}
    main_title = title_map.get(pelatihan_choice, 'Data Peserta Pelatihan Tenaga Kependidikan')
    st.title(main_title)

    # --- Filters ---
    with st.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            jenjang_filter = st.multiselect('JENJANG', df['JENJANG'].dropna().unique(), key="jenjang_filter")
            kecamatan_filter = st.multiselect('KECAMATAN', df['KECAMATAN'].dropna().unique(), key="kecamatan_filter")
        with col2:
            nama_pelatihan_filter = st.multiselect('NAMA PELATIHAN', df['NAMA_PELATIHAN'].dropna().unique(), key="nama_pelatihan_filter")
            pelatihan_filter = st.multiselect('PELATIHAN', df['PELATIHAN'].dropna().unique(), key="pelatihan_filter")
        with col3:
            status_sekolah_filter = st.multiselect('STATUS SEKOLAH', df['STATUS_SEKOLAH'].dropna().unique(), key="status_sekolah_filter")
            date_range = st.date_input('TANGGAL', value=[], key="date_range")
            
    conditions = []
    if jenjang_filter: conditions.append(df['JENJANG'].isin(jenjang_filter))
    if kecamatan_filter: conditions.append(df['KECAMATAN'].isin(kecamatan_filter))
    if nama_pelatihan_filter: conditions.append(df['NAMA_PELATIHAN'].isin(nama_pelatihan_filter))
    if pelatihan_filter: conditions.append(df['PELATIHAN'].isin(pelatihan_filter))
    if status_sekolah_filter: conditions.append(df['STATUS_SEKOLAH'].isin(status_sekolah_filter))
    if len(date_range) == 2:
        start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
        conditions.append((df['TANGGAL'] >= start_date) & (df['TANGGAL'] <= end_date))
    filtered_df = df[pd.concat(conditions, axis=1).all(axis=1)] if conditions else df.copy()

    # --- NEW: Search Functionality ---
    st.markdown("---")
    search_col1, search_col2 = st.columns(2)
    with search_col1:
        search_name = st.text_input("Cari Nama Peserta", key="search_name_input", placeholder="Ketik nama untuk mencari...")
    with search_col2:
        search_school = st.text_input("Cari Asal Sekolah", key="search_school_input", placeholder="Ketik nama sekolah untuk mencari...")

    # Apply search filters on top of the main filters
    search_results_df = filtered_df.copy()
    if search_name:
        search_results_df = search_results_df[search_results_df['NAMA_PESERTA'].str.contains(search_name, case=False, na=False)]
    if search_school:
        search_results_df = search_results_df[search_results_df['ASAL_SEKOLAH'].str.contains(search_school, case=False, na=False)]

    # --- DISPLAY SECTION (CARD VIEW / TABLE VIEW) ---
    st.write(f'Showing {len(search_results_df)} records')
    view_mode = st.radio("Display mode:", ['Card View', 'Table View'], horizontal=True, label_visibility="collapsed")

    # Initialize session state for pagination if it doesn't exist
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1

    # Reset page to 1 if filters or search terms change the number of records
    if 'last_record_count' not in st.session_state:
        st.session_state.last_record_count = len(search_results_df)
    if st.session_state.last_record_count != len(search_results_df):
        st.session_state.current_page = 1
        st.session_state.last_record_count = len(search_results_df)

    # --- CARD VIEW IMPLEMENTATION with Custom Pagination ---
    if view_mode == 'Card View':
        page_size = 8
        total_pages = (len(search_results_df) // page_size) + (1 if len(search_results_df) % page_size > 0 else 0)
        total_pages = max(1, total_pages) # Ensure at least 1 page

        # Ensure current page is valid
        st.session_state.current_page = min(st.session_state.current_page, total_pages)

        start_index = (st.session_state.current_page - 1) * page_size
        end_index = start_index + page_size
        paginated_df = search_results_df.iloc[start_index:end_index]

        # Display the cards in a grid
        num_columns = 4
        cols = st.columns(num_columns)
        for index, row in paginated_df.reset_index().iterrows():
            col_index = index % num_columns
            with cols[col_index]:
                with st.container(border=True):
                    st.markdown(f"**{row.get('NAMA_PESERTA', 'N/A')}**")
                    school_name = str(row.get('ASAL_SEKOLAH', 'N/A'))
                    training_name = str(row.get('NAMA_PELATIHAN', 'N/A'))
                    st.markdown(f"<small><b>Sekolah:</b> {school_name[:25] + '...' if len(school_name) > 25 else school_name}</small>", unsafe_allow_html=True)
                    st.markdown(f"<small><b>Pelatihan:</b> {training_name[:25] + '...' if len(training_name) > 25 else training_name}</small>", unsafe_allow_html=True)
                    tanggal_str = pd.to_datetime(row.get('TANGGAL')).strftime('%d %b %Y') if pd.notna(row.get('TANGGAL')) else 'N/A'
                    st.markdown(f"<small><b>Tanggal:</b> {tanggal_str}</small>", unsafe_allow_html=True)
                    st.write("")
                    if st.button("Lihat Detail", key=f"detail_{row['index']}", use_container_width=True):
                        st.session_state.selected_participant_details = row.to_dict()
                        st.rerun()
        
        st.markdown("---")
        
        # --- NEW: Custom Pagination Logic ---
        if total_pages > 1:
            prev_col, page_info_col, next_col = st.columns([1, 8, 1])
            with prev_col:
                if st.button("⬅️ Prev", use_container_width=True, disabled=(st.session_state.current_page <= 1)):
                    st.session_state.current_page -= 1
                    st.rerun()
            with page_info_col:
                st.markdown(f"<div style='text-align: center; margin-top: 5px;'>Page {st.session_state.current_page} of {total_pages}</div>", unsafe_allow_html=True)
            with next_col:
                if st.button("Next ➡️", use_container_width=True, disabled=(st.session_state.current_page >= total_pages)):
                    st.session_state.current_page += 1
                    st.rerun()

    # --- TABLE VIEW IMPLEMENTATION (Now uses search results) ---
    elif view_mode == 'Table View':
        display_df = search_results_df.copy() # Use the search results here
        if "NO" in display_df.columns: display_df = display_df.drop(columns=["NO"])
        display_df = display_df.reset_index(drop=True)
        display_df.insert(0, "NO", range(1, len(display_df) + 1))
        display_df['TANGGAL'] = display_df['TANGGAL'].dt.strftime('%Y-%m-%d')
        if 'CATEGORY' in display_df.columns: display_df = display_df.drop(columns=['CATEGORY'])
        
        gb = GridOptionsBuilder.from_dataframe(display_df)
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)
        gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc="sum", editable=False)
        gb.configure_selection(selection_mode="single", use_checkbox=False)
        grid_options = gb.build()
        
        grid_response = AgGrid(
            display_df, gridOptions=grid_options, update_mode=GridUpdateMode.SELECTION_CHANGED,
            height=500, fit_columns_on_grid_load=True, reload_data=True, use_legacy_py_rendering=True
        )
        
        selected = grid_response['selected_rows']
        if selected is not None and not selected.empty:
            st.session_state.selected_participant_details = selected.iloc[0].to_dict()

    # --- DETAIL VIEW LOGIC (Used by both Card and Table views) ---
    if 'selected_participant_details' in st.session_state and st.session_state.selected_participant_details:
        with st.container(border=True):
            selected_row = st.session_state.selected_participant_details
            selected_name = selected_row.get('NAMA_PESERTA', 'N/A')
            selected_school = selected_row.get('ASAL_SEKOLAH', 'N/A')

            st.markdown("### Detail Peserta")
            st.write(f"Semua pelatihan yang diikuti oleh: **{selected_name}** dari **{selected_school}**")

            participant_trainings = df[
                (df['NAMA_PESERTA'] == selected_name) &
                (df['ASAL_SEKOLAH'] == selected_school)
            ][['NAMA_PELATIHAN', 'TANGGAL', 'ASAL_SEKOLAH', 'NPSN']].drop_duplicates().reset_index(drop=True)
            
            participant_trainings['TANGGAL'] = pd.to_datetime(participant_trainings['TANGGAL']).dt.strftime('%Y-%m-%d')
            participant_trainings.index += 1
            st.dataframe(participant_trainings, use_container_width=True)
            st.write(f"Jumlah pelatihan: {len(participant_trainings)}")
            
            if st.button("Tutup Detail"):
                del st.session_state.selected_participant_details
                st.rerun()

    # --- DYNAMIC SUMMARY SECTION (Unchanged) ---
    st.markdown('---')
    st.subheader("Filter untuk Rekap Pencapaian")
    summary_col1, summary_col2 = st.columns(2)
    with summary_col1:
        summary_status_filter = st.multiselect(
            'Filter Status Sekolah (Negeri/Swasta)',
            options=df_sekolah_sumber['STATUS'].dropna().unique(),
            key="summary_status_filter"
        )
    with summary_col2:
        summary_kabupaten_filter = st.multiselect(
            'Filter Kabupaten/Kota',
            options=df_sekolah_sumber['KABUPATEN'].dropna().unique(),
            key="summary_kabupaten_filter"
        )

    filtered_school_data = df_sekolah_sumber.copy()
    if summary_status_filter:
        filtered_school_data = filtered_school_data[filtered_school_data['STATUS'].isin(summary_status_filter)]
    if summary_kabupaten_filter:
        filtered_school_data = filtered_school_data[filtered_school_data['KABUPATEN'].isin(summary_kabupaten_filter)]

    def get_dynamic_targets(filtered_df_sekolah):
        df_sekolah = filtered_df_sekolah[filtered_df_sekolah['TIPE'] != 'SLB'].copy()
        df_sekolah['KEPALA_SEKOLAH'] = pd.to_numeric(df_sekolah['KEPALA_SEKOLAH'], errors='coerce').fillna(0).astype(int)
        df_sekolah['TENAGA_KEPENDIDIKAN'] = pd.to_numeric(df_sekolah['TENAGA_KEPENDIDIKAN'], errors='coerce').fillna(0).astype(int)
        df_sekolah['TARGET_PESERTA'] = df_sekolah['KEPALA_SEKOLAH'] + df_sekolah['TENAGA_KEPENDIDIKAN']
        jenjang_targets = df_sekolah.groupby('TIPE')['TARGET_PESERTA'].sum().to_dict()
        sekolah_targets = df_sekolah.groupby('TIPE').size().to_dict()
        return jenjang_targets, sekolah_targets

    jenjang_targets, sekolah_targets = get_dynamic_targets(filtered_school_data)
    npsn_to_show = filtered_school_data['NPSN'].astype(str).unique()
    
    summary_df = filtered_df.copy()
    if summary_status_filter or summary_kabupaten_filter:
        summary_df = summary_df[summary_df['NPSN'].astype(str).isin(npsn_to_show)]

    prefix = pelatihan_choice if pelatihan_choice else "Keseluruhan"
    all_jenjang = sorted([j for j in df_sekolah_sumber['TIPE'].unique() if j != 'SLB'])

    summary_rows = []
    for jenjang in all_jenjang:
        target = jenjang_targets.get(jenjang, 0)
        df_jenjang = summary_df[summary_df['JENJANG'] == jenjang]
        unique_count = df_jenjang.drop_duplicates(subset=['NAMA_PESERTA', 'ASAL_SEKOLAH']).shape[0]
        percent = (unique_count / target * 100) if target > 0 else 0
        kurang = max(0, target - unique_count)
        summary_rows.append({
            'Jenjang': jenjang, 'Target Jumlah Peserta Pelatihan': f"{target:,} Orang",
            'Jumlah Peserta Pelatihan (unique)': f"{unique_count:,} Orang",
            'Persentase': f"{percent:.2f} %", 'Kurang': f"{kurang:,} Orang"
        })
    df_summary_jenjang = pd.DataFrame(summary_rows).set_index('Jenjang').reindex(all_jenjang).reset_index()
    df_summary_jenjang.index += 1
    st.write(f'### Rekap Pencapaian Pelatihan {prefix} berdasarkan Jenjang')
    st.dataframe(df_summary_jenjang, use_container_width=True)
        
    sekolah_rows = []
    for jenjang in all_jenjang:
        target = sekolah_targets.get(jenjang, 0)
        df_sekolah = summary_df[summary_df['JENJANG'] == jenjang]
        unique_sekolah_count = df_sekolah['ASAL_SEKOLAH'].nunique()
        percent = (unique_sekolah_count / target * 100) if target > 0 else 0
        kurang = max(0, target - unique_sekolah_count)
        sekolah_rows.append({
            'Jenjang': jenjang, 'Target Jumlah Sekolah': f"{target:,} Sekolah",
            'Jumlah Sekolah (unique)': f"{unique_sekolah_count:,} Sekolah",
            'Persentase': f"{percent:.2f} %", 'Kurang': f"{kurang:,} Sekolah"
        })
    df_summary_sekolah = pd.DataFrame(sekolah_rows).set_index('Jenjang').reindex(all_jenjang).reset_index()
    df_summary_sekolah.index += 1
    st.write(f'### Rekap Pencapaian Pelatihan {prefix} berdasarkan Jumlah Sekolah')
    st.dataframe(df_summary_sekolah, use_container_width=True)
    
    st.markdown(f'*Data cutoff: {pd.Timestamp.now(tz="Asia/Jakarta").strftime("%d %B %Y")}*')
    
    st.write("---")
    st.header("Upload Data Terbaru")
    upload_category = st.selectbox("Pilih kategori pelatihan untuk ditambahkan data", sheet_names)
    uploaded_file = st.file_uploader(f"Upload file CSV atau Excel untuk pelatihan '{upload_category}' (format sesuai template)", type=['csv', 'xlsx'])
    
    if uploaded_file is not None:
        try:
            new_data = pd.read_csv(uploaded_file, sep=';') if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            st.write("Pratinjau data yang diunggah:")
            st.dataframe(new_data)
            expected_cols_base = load_data_from_gsheets(json_keyfile_str, spreadsheet_id, upload_category).columns
            if any(c not in new_data.columns for c in expected_cols_base):
                st.error(f"File unggahan kehilangan beberapa kolom wajib. Kolom yang hilang: {', '.join(set(expected_cols_base) - set(new_data.columns))}")
            else:
                new_data = new_data.astype(str)
                if st.button("Tambahkan data ke Google Sheet"):
                    try:
                        scopes = ['https://www.googleapis.com/auth/spreadsheets']
                        creds_dict = json.loads(st.secrets["GSHEET_SERVICE_ACCOUNT"])
                        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
                        client = gspread.authorize(creds)
                        sheet = client.open_by_key(spreadsheet_id).worksheet(upload_category)
                        sheet.append_rows(new_data[expected_cols_base].values.tolist(), value_input_option='USER_ENTERED')
                        st.success(f"Data berhasil ditambahkan ke sheet '{upload_category}'!")
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"Gagal menambahkan data: {e}")
        except Exception as e:
            st.error(f"Gagal membaca file unggahan: {e}")

    st.markdown(
        """
        <hr>
        <div style="text-align: center; margin-top: 20px;">
            <a href="https://www.instagram.com/p4jakut_ks?igsh=c3Mya2dodm5hbHU1" target="blank" style="margin: 0 20px; display: inline-block; text-decoration: none; color: inherit;">
                <img src="https://raw.githubusercontent.com/andrewsihotang/datas/main/instagrams.png" alt="Instagram" width="32" height="32" />
                <div style="font-size: 0.7rem; margin-top: 4px;">Instagram P4 JUKS</div>
            </a>
            <a href="https://www.tiktok.com/@p4.juks?_t=ZS-8zKsAgWjXJQ&_r=1" target="blank" style="margin: 0 20px; display: inline-block; text-decoration: none; color: inherit;">
                <img src="https://raw.githubusercontent.com/andrewsihotang/datas/main/tiktok.png" alt="TikTok" width="32" height="32" />
                <div style="font-size: 0.7rem; margin-top: 4px;">TikTok P4 JUKS</div>
            </a>
            <a href="https://youtube.com/@p4jakartautaradankep-seribu?si=BWAVvVyVdYvbj8Xo" target="blank" style="margin: 0 20px; display: inline-block; text-decoration: none; color: inherit;">
                <img src="https://raw.githubusercontent.com/andrewsihotang/datas/main/youtube.png" alt="YouTube" width="32" height="32" />
                <div style="font-size: 0.7rem; margin-top: 4px;">YouTube P4 JUKS</div>
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Main flow control
if st.session_state.page == "landing":
    show_landing_page()
elif st.session_state.page == "main":
    main_app()
else:
    st.session_state.page = "landing"
    show_landing_page()
