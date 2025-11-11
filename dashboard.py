import streamlit as st
import pandas as pd
import gspread
import json
import io  # Diperlukan untuk download Excel
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

# Inisialisasi Session State di Awal
if "page" not in st.session_state:
    st.session_state.page = "landing"
if "current_page" not in st.session_state:
    st.session_state.current_page = 1
# State untuk download
if "download_ready" not in st.session_state:
    st.session_state.download_ready = False
if "download_data" not in st.session_state:
    st.session_state.download_data = None


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
                "summary_status_filter": [], "summary_kabupaten_filter": [],
                "reco_status_filter": [], "reco_kec_filter": [], "reco_school_select": "-- Pilih Sekolah --",
                "rekap_pelatihan_filter": "Pendidik"
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
        if 'NPSN' in df_sekolah.columns:
            df_sekolah['NPSN'] = df_sekolah['NPSN'].astype(str)
        if 'KECAMATAN' in df_sekolah.columns:
            df_sekolah['KECAMATAN'] = df_sekolah['KECAMATAN'].astype(str)
        if 'KABUPATEN' in df_sekolah.columns:
            df_sekolah['KABUPATEN'] = df_sekolah['KABUPATEN'].astype(str)
        return df_sekolah

    @st.cache_data
    def load_dapodik_data(json_keyfile_str, spreadsheet_id):
        df_dapodik = load_data_from_gsheets(json_keyfile_str, spreadsheet_id, 'data_dapodik_name')
        df_dapodik.columns = [col.strip().upper() for col in df_dapodik.columns]
        NAMA_KOLOM_NAMA = 'NAMA_LENGKAP' 
        if 'NPSN' not in df_dapodik.columns or NAMA_KOLOM_NAMA not in df_dapodik.columns:
            st.error(f"Sheet 'data_dapodik_name' harus memiliki kolom 'NPSN' dan '{NAMA_KOLOM_NAMA}'")
            return pd.DataFrame()
        df_dapodik['NPSN'] = df_dapodik['NPSN'].astype(str)
        df_dapodik[NAMA_KOLOM_NAMA] = df_dapodik[NAMA_KOLOM_NAMA].astype(str).str.strip()
        df_dapodik = df_dapodik.dropna(subset=['NPSN', NAMA_KOLOM_NAMA])
        return df_dapodik

    # --- Load Data ---
    json_keyfile_str = st.secrets["GSHEET_SERVICE_ACCOUNT"]
    spreadsheet_id = '1_YeSK2zgoExnC8n6tlmoJFQDVEWZbncdBLx8S5k-ljc'
    sheet_names = ['Tendik', 'Pendidik', 'Kejuruan']
    dfs = [load_data_from_gsheets(json_keyfile_str, spreadsheet_id, name) for name in sheet_names]
    df = pd.concat(dfs, ignore_index=True)
    df_sekolah_sumber = load_school_data(json_keyfile_str, spreadsheet_id)
    df_sekolah_sumber['TIPE'] = df_sekolah_sumber['TIPE'].replace('DIKMAS', 'PKBM')

    # --- Data Cleaning ---
    df.columns = [col.strip().upper() for col in df.columns]
    if 'STASUS_SEKOLAH' in df.columns:
        df.rename(columns={'STASUS_SEKOLAH': 'STATUS_SEKOLAH'}, inplace=True)
    df = df.loc[:, ~df.columns.duplicated(keep='first')]
    
    # ==================================================================
    # === START: Perbaikan (Mengatasi UserWarning) ===
    # ==================================================================
    df['TANGGAL'] = pd.to_datetime(df['TANGGAL'], errors='coerce', dayfirst=True)
    # ==================================================================
    # === END: Perbaikan ===
    # ==================================================================
    
    if 'NPSN' in df.columns:
        df['NPSN'] = df['NPSN'].astype(str)
    if 'STATUS_SEKOLAH' not in df.columns:
        df['STATUS_SEKOLAH'] = pd.NA
    df['JENJANG'] = df['JENJANG'].replace('DIKMAS', 'PKBM')
    if 'NAMA_PESERTA' in df.columns:
        df['NAMA_PESERTA'] = df['NAMA_PESERTA'].astype(str).str.strip()

    # --- PEMBUATAN TAB ---
    tab_data_peserta, tab_rekap, tab_rekomendasi, tab_upload = st.tabs([
        "📊 Data Peserta Pelatihan", 
        "📈 Rekap Pencapaian", 
        "💡 Rekomendasi Peserta", 
        "📤 Upload Data Terbaru"
    ])

    # --- TAB 1: DATA PESERTA PELATIHAN ---
    with tab_data_peserta:
        pelatihan_choice_tab1 = st.session_state.get("pelatihan_filter", [None])[0] if len(st.session_state.get("pelatihan_filter", [])) == 1 else None
        title_map = {'Tendik': 'Data Peserta Pelatihan Tenaga Kependidikan', 'Pendidik': 'Data Peserta Pelatihan Pendidik', 'Kejuruan': 'Data Peserta Pelatihan Kejuruan'}
        main_title = title_map.get(pelatihan_choice_tab1, 'Data Peserta Pelatihan Tenaga Kependidikan')
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

        search_results_df = filtered_df.copy()
        if search_name:
            search_results_df = search_results_df[search_results_df['NAMA_PESERTA'].str.contains(search_name, case=False, na=False)]
        if search_school:
            search_results_df = search_results_df[search_results_df['ASAL_SEKOLAH'].str.contains(search_school, case=False, na=False)]

        # --- DISPLAY SECTION (CARD VIEW / TABLE VIEW) ---
        st.write(f'Showing {len(search_results_df)} records')
        view_mode = st.radio("Display mode:", ['Card View', 'Table View'], horizontal=True, label_visibility="collapsed")
        
        if 'last_record_count' not in st.session_state:
            st.session_state.last_record_count = len(search_results_df)
        if st.session_state.last_record_count != len(search_results_df):
            st.session_state.current_page = 1
            st.session_state.last_record_count = len(search_results_df)

        if view_mode == 'Card View':
            page_size = 8
            total_pages = (len(search_results_df) // page_size) + (1 if len(search_results_df) % page_size > 0 else 0)
            total_pages = max(1, total_pages) 
            st.session_state.current_page = min(st.session_state.current_page, total_pages)
            start_index = (st.session_state.current_page - 1) * page_size
            end_index = start_index + page_size
            paginated_df = search_results_df.iloc[start_index:end_index]
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
        elif view_mode == 'Table View':
            display_df = search_results_df.copy()
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

        if 'selected_participant_details' in st.session_state and st.session_state.selected_participant_details:
            with st.container(border=True):
                selected_row = st.session_state.selected_participant_details
                selected_name = str(selected_row.get('NAMA_PESERTA', 'N/A')).strip() 
                selected_npsn = str(selected_row.get('NPSN', 'N/A'))
                selected_school = selected_row.get('ASAL_SEKOLAH', 'N/A') 
                st.markdown("### Detail Peserta")
                st.write(f"Semua pelatihan yang diikuti oleh: **{selected_name}** dari **{selected_school}**")
                participant_trainings = df[
                    (df['NAMA_PESERTA'].astype(str).str.strip() == selected_name) & 
                    (df['NPSN'].astype(str) == selected_npsn) 
                ][['NAMA_PELATIHAN', 'TANGGAL', 'ASAL_SEKOLAH', 'NPSN']].drop_duplicates().reset_index(drop=True)
                participant_trainings['TANGGAL'] = pd.to_datetime(participant_trainings['TANGGAL']).dt.strftime('%Y-%m-%d')
                participant_trainings.index += 1
                st.dataframe(participant_trainings, use_container_width=True)
                st.write(f"Jumlah pelatihan: {len(participant_trainings)}")
                if st.button("Tutup Detail"):
                    del st.session_state.selected_participant_details
                    st.rerun()

    # --- TAB 2: REKAP PENCAPAIAN ---
    with tab_rekap:
        st.subheader("Filter untuk Rekap Pencapaian")

        rekap_pelatihan_choice = st.selectbox(
            "Pilih Kategori Pelatihan untuk Rekap",
            options=["Pendidik", "Tendik", "Kejuruan"],
            key="rekap_pelatihan_filter"
        )

        # ==================================================================
        # === START: Perbaikan (Filter Kabupaten Hardcode + Perbaikan Logika) ===
        # ==================================================================
        target_kabupaten_rekap = ['KOTA ADM. JAKARTA UTARA', 'KAB. ADM. KEP. SERIBU']

        # 1. Pre-filter data master sekolah (TARGET)
        if 'KABUPATEN' not in df_sekolah_sumber.columns:
            st.error("Kolom 'KABUPATEN' tidak ditemukan di 'data_sekolah'. Filter Jakut/Kep. Seribu tidak dapat diterapkan.")
            df_sekolah_sumber_rekap = df_sekolah_sumber.copy()
        else:
            df_sekolah_sumber_rekap = df_sekolah_sumber[
                df_sekolah_sumber['KABUPATEN'].isin(target_kabupaten_rekap)
            ].copy()

        # 2. Dapatkan SET NPSN dari data master yang sudah difilter
        npsn_jakut_ks = set(df_sekolah_sumber_rekap['NPSN'].astype(str))

        # 3. Pre-filter data PELATIHAN (df) berdasarkan SET NPSN
        df_pelatihan_rekap = df[df['NPSN'].astype(str).isin(npsn_jakut_ks)].copy()
        
        # 4. Hapus filter multiselect kabupaten, sisakan status
        summary_status_filter = st.multiselect(
            'Filter Status Sekolah (Negeri/Swasta)',
            options=df_sekolah_sumber_rekap['STATUS'].dropna().unique(), # Opsi dari data yg sudah difilter
            key="summary_status_filter"
        )
        # ==================================================================
        # === END: Perbaikan ===
        # ==================================================================

        # Gunakan `df_sekolah_sumber_rekap` sebagai basis
        filtered_school_data = df_sekolah_sumber_rekap.copy()
        if summary_status_filter:
            filtered_school_data = filtered_school_data[filtered_school_data['STATUS'].isin(summary_status_filter)]
        
        # ==================================================================
        # === START: Perbaikan (Mengembalikan fungsi yang hilang) ===
        # ==================================================================
        def get_dynamic_targets(filtered_df_sekolah, pelatihan_filter_choice):
            df_sekolah = filtered_df_sekolah.copy() 
            if pelatihan_filter_choice != 'Pendidik':
                df_sekolah = df_sekolah[df_sekolah['TIPE'] != 'SLB'].copy()
            df_sekolah['KEPALA_SEKOLAH'] = pd.to_numeric(df_sekolah['KEPALA_SEKOLAH'], errors='coerce').fillna(0).astype(int)
            df_sekolah['TENAGA_KEPENDIDIKAN'] = pd.to_numeric(df_sekolah['TENAGA_KEPENDIDIKAN'], errors='coerce').fillna(0).astype(int)
            df_sekolah['GURU'] = pd.to_numeric(df_sekolah['GURU'], errors='coerce').fillna(0).astype(int)
            if pelatihan_filter_choice == 'Pendidik':
                df_sekolah['TARGET_PESERTA'] = df_sekolah['GURU']
            else: 
                df_sekolah['TARGET_PESERTA'] = df_sekolah['KEPALA_SEKOLAH'] + df_sekolah['TENAGA_KEPENDIDIKAN']
            jenjang_targets = df_sekolah.groupby('TIPE')['TARGET_PESERTA'].sum().to_dict()
            sekolah_targets = df_sekolah.groupby('TIPE').size().to_dict()
            return jenjang_targets, sekolah_targets
        # ==================================================================
        # === END: Perbaikan ===
        # ==================================================================
        
        jenjang_targets, sekolah_targets = get_dynamic_targets(filtered_school_data, rekap_pelatihan_choice)
        npsn_to_show = filtered_school_data['NPSN'].astype(str).unique() # NPSN dari data yg sudah difilter
        
        # Gunakan `df_pelatihan_rekap` sebagai basis
        summary_df = df_pelatihan_rekap.copy() 
        summary_df = summary_df[summary_df['PELATIHAN'] == rekap_pelatihan_choice]

        # Filter `summary_df` HANYA berdasarkan status (karena kabupaten sudah)
        if summary_status_filter:
            summary_df = summary_df[summary_df['NPSN'].astype(str).isin(npsn_to_show)]

        prefix = rekap_pelatihan_choice
        
        # Basis untuk `all_jenjang` sekarang adalah `df_sekolah_sumber_rekap`
        all_jenjang_from_source = sorted(df_sekolah_sumber_rekap['TIPE'].dropna().unique())
        
        if rekap_pelatihan_choice == 'Pendidik':
            all_jenjang = all_jenjang_from_source
        else:
            all_jenjang = [j for j in all_jenjang_from_source if j != 'SLB']

        summary_rows = []
        for jenjang in all_jenjang:
            target = jenjang_targets.get(jenjang, 0)
            df_jenjang = summary_df[summary_df['JENJANG'] == jenjang]
            unique_count = df_jenjang.drop_duplicates(subset=['NAMA_PESERTA', 'ASAL_SEKOLAH']).shape[0]
            
            percent = min((unique_count / target * 100), 100) if target > 0 else 0
            
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
            
        # ==================================================================
        # === START OF MODIFICATION: Logika Rekap Sekolah berdasarkan NPSN ===
        # ==================================================================
        
        sekolah_rows = []
        missing_schools_data = {} # Menyimpan data sekolah yang ada di target tapi belum ikut
        
        # Tentukan nama kolom sekolah dari data master
        NAMA_KOLOM_SEKOLAH_MASTER = 'NAMA_SEKOLAH'
        if NAMA_KOLOM_SEKOLAH_MASTER not in filtered_school_data.columns:
            if 'ASAL_SEKOLAH' in filtered_school_data.columns:
                NAMA_KOLOM_SEKOLAH_MASTER = 'ASAL_SEKOLAH'
            else:
                NAMA_KOLOM_SEKOLAH_MASTER = 'NPSN' # Fallback jika tidak ada nama

        for jenjang in all_jenjang:
            # 1. Dapatkan set NPSN dari data target (data_sekolah yang sudah difilter)
            target_npsn_set = set(filtered_school_data[
                (filtered_school_data['TIPE'] == jenjang) &
                (filtered_school_data['NPSN'].notna()) &
                (filtered_school_data['NPSN'] != '')
            ]['NPSN'].astype(str))
            
            # 2. Dapatkan set NPSN dari data pelatihan (summary_df)
            df_sekolah_jenjang = summary_df[
                (summary_df['JENJANG'] == jenjang) &
                (summary_df['NPSN'].notna()) &
                (summary_df['NPSN'] != '')
            ]
            trained_npsn_set = set(df_sekolah_jenjang['NPSN'].astype(str))

            # 3. Hitung jumlah
            target_count = len(target_npsn_set)
            trained_count = len(trained_npsn_set)
            
            # 4. Hitung persentase (tetap dibatasi 100% untuk tampilan)
            percent = min((trained_count / target_count * 100), 100) if target_count > 0 else 0
            kurang = max(0, target_count - trained_count)
            
            sekolah_rows.append({
                'Jenjang': jenjang, 'Target Jumlah Sekolah': f"{target_count:,} Sekolah",
                'Jumlah Sekolah (unique)': f"{trained_count:,} Sekolah",
                'Persentase': f"{percent:.2f} %", 'Kurang': f"{kurang:,} Sekolah"
            })
            
            # 5. Cari perbedaan (HANYA YANG ANDA MINTA)
            missing_npsn = target_npsn_set - trained_npsn_set
            
            # 6. Simpan detail sekolah yang hilang (yang Anda minta)
            if missing_npsn:
                # ==================================================================
                # === START: Perubahan (Ganti kolom KABUPATEN -> STATUS) ===
                # ==================================================================
                cols_to_show = ['NPSN', NAMA_KOLOM_SEKOLAH_MASTER, 'KECAMATAN', 'STATUS']
                # ==================================================================
                # === END: Perubahan ===
                # ==================================================================
                
                # Pastikan semua kolom ada di filtered_school_data
                cols_exist = [col for col in cols_to_show if col in filtered_school_data.columns]
                missing_df = filtered_school_data[
                    filtered_school_data['NPSN'].isin(missing_npsn)
                ][cols_exist].drop_duplicates(subset=['NPSN']).reset_index(drop=True)
                missing_df.index += 1
                missing_schools_data[jenjang] = missing_df
            
        df_summary_sekolah = pd.DataFrame(sekolah_rows).set_index('Jenjang').reindex(all_jenjang).reset_index()
        df_summary_sekolah.index += 1
        st.write(f'### Rekap Pencapaian Pelatihan {prefix} berdasarkan Jumlah Sekolah (by NPSN)')
        st.dataframe(df_summary_sekolah, use_container_width=True)

        st.markdown("---")
        st.write("### 🔍 Validasi Sekolah Target yang Belum Ikut Pelatihan")
        st.info("Bagian ini menampilkan jumlah sekolah yang belum ikut pelatihan.")
        
        # ==================================================================
        # === START: Perubahan Tampilan Expander Sesuai Permintaan ===
        # ==================================================================
        for jenjang in all_jenjang:
            missing_df = missing_schools_data.get(jenjang)
            has_missing = missing_df is not None and not missing_df.empty
            
            # Tampilkan expander untuk setiap jenjang
            label = f"**{jenjang}**: Terdapat {len(missing_df) if has_missing else 0} sekolah yang belum terdata ikut pelatihan"
            with st.expander(label):
                if has_missing:
                    # Ini adalah daftar yang Anda minta
                    st.write(f"**Daftar Sekolah di Target yang BELUM Terdata Ikut Pelatihan ({len(missing_df)}):**")
                    st.caption("Ini adalah daftar sekolah (termasuk sekolah baru) yang ada di daftar Target Anda, tetapi belum terdata di 'Jumlah Sekolah (unique)'.")
                    st.dataframe(missing_df, use_container_width=True)
                else:
                    # Ini adalah konfirmasi yang Anda minta (contoh: untuk kasus SMA)
                    st.success(f"**Validasi Berhasil:** Semua sekolah di daftar Target untuk jenjang {jenjang} sudah terdata mengikuti pelatihan.")
        # ==================================================================
        # === END: Perubahan Tampilan Expander ===
        # ==================================================================
        
    # --- TAB 3: REKOMENDASI PESERTA ---
    with tab_rekomendasi:
        st.subheader("💡 Rekomendasi Peserta")
        
        # ==================================================================
        # === BAGIAN BARU: Unduh Laporan Lengkap ===
        # ==================================================================
        st.markdown("---")
        st.subheader("Unduh Laporan")
        st.write("Unduh file Excel berisi semua peserta yang belum terdata pelatihan.")
        
        if st.button("Download Rekomendasi Peserta"):
            with st.spinner("Menggabungkan data... Ini mungkin perlu beberapa saat..."):
                try:
                    # 1. Load data
                    df_dapodik_all = load_dapodik_data(json_keyfile_str, spreadsheet_id)
                    # Data sekolah (df_sekolah_sumber) dan data peserta (df) sudah di-load
                    
                    if not df_dapodik_all.empty:
                        NAMA_KOLOM_NAMA_DAPODIK = 'NAMA_LENGKAP'
                        
                        # 2. Get master list (Dapodik)
                        master_list_df = df_dapodik_all[['NPSN', NAMA_KOLOM_NAMA_DAPODIK]].copy()
                        master_list_df['NPSN'] = master_list_df['NPSN'].astype(str).str.strip()
                        master_list_df[NAMA_KOLOM_NAMA_DAPODIK] = master_list_df[NAMA_KOLOM_NAMA_DAPODIK].astype(str).str.strip()
                        master_list_df = master_list_df.dropna().drop_duplicates()
                        master_set = set(zip(master_list_df['NPSN'], master_list_df[NAMA_KOLOM_NAMA_DAPODIK]))

                        # 3. Get trained list (from all tabs)
                        trained_list_df = df[['NPSN', 'NAMA_PESERTA']].copy()
                        trained_list_df['NPSN'] = trained_list_df['NPSN'].astype(str).str.strip()
                        trained_list_df['NAMA_PESERTA'] = trained_list_df['NAMA_PESERTA'].astype(str).str.strip()
                        trained_list_df = trained_list_df.dropna().drop_duplicates()
                        trained_set = set(zip(trained_list_df['NPSN'], trained_list_df['NAMA_PESERTA']))

                        # 4. Find the difference
                        untained_set = master_set - trained_set
                        
                        # 5. Convert back to DataFrame
                        untained_df = pd.DataFrame(list(untained_set), columns=['NPSN', 'Nama peserta'])
                        
                        # ==================================================================
                        # === PERBAIKAN: Ambil Nama Sekolah dari Master Data Sekolah (df_sekolah_sumber) ===
                        # ==================================================================
                        # 6. Add School Name
                        # Buat peta NPSN -> NAMA_SEKOLAH dari data master (df_sekolah_sumber)
                        # Pastikan sheet 'data_sekolah' Anda memiliki kolom 'NAMA_SEKOLAH' (atau sesuaikan namanya)
                        
                        # Ganti 'NAMA_SEKOLAH' jika nama kolomnya berbeda di sheet 'data_sekolah' Anda
                        NAMA_KOLOM_SEKOLAH_MASTER_RECO = 'NAMA_SEKOLAH' 
                        if NAMA_KOLOM_SEKOLAH_MASTER_RECO not in df_sekolah_sumber.columns:
                            # Fallback jika kolom 'NAMA_SEKOLAH' tidak ada, coba 'ASAL_SEKOLAH'
                            if 'ASAL_SEKOLAH' in df_sekolah_sumber.columns:
                                NAMA_KOLOM_SEKOLAH_MASTER_RECO = 'ASAL_SEKOLAH'
                            else:
                                st.error("Kolom nama sekolah (NAMA_SEKOLAH atau ASAL_SEKOLAH) tidak ditemukan di sheet 'data_sekolah'.")
                                # Buat kolom kosong agar tidak error
                                NAMA_KOLOM_SEKOLAH_MASTER_RECO = 'NAMA_SEKOLAH' # set fiktif
                                df_sekolah_sumber[NAMA_KOLOM_SEKOLAH_MASTER_RECO] = pd.NA

                        school_map_df = df_sekolah_sumber[['NPSN', NAMA_KOLOM_SEKOLAH_MASTER_RECO]].copy()
                        school_map_df['NPSN'] = school_map_df['NPSN'].astype(str).str.strip()
                        school_map_df = school_map_df.dropna(subset=['NPSN', NAMA_KOLOM_SEKOLAH_MASTER_RECO])
                        school_map_df = school_map_df.drop_duplicates(subset=['NPSN'], keep='first')
                        
                        final_df = untained_df.merge(school_map_df, on='NPSN', how='left')
                        # ==================================================================
                        
                        # 7. Format
                        # Pastikan kolom (misal 'NAMA_SEKOLAH') ada
                        if NAMA_KOLOM_SEKOLAH_MASTER_RECO not in final_df.columns:
                            final_df[NAMA_KOLOM_SEKOLAH_MASTER_RECO] = pd.NA
                        
                        final_df = final_df[[NAMA_KOLOM_SEKOLAH_MASTER_RECO, 'NPSN', 'Nama peserta']]
                        final_df.rename(columns={NAMA_KOLOM_SEKOLAH_MASTER_RECO: 'Sekolah'}, inplace=True)
                        
                        # 8. Create Excel in memory
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            final_df.to_excel(writer, index=False, sheet_name='Belum Pelatihan')
                        data_to_download = output.getvalue()
                        
                        st.session_state['download_data'] = data_to_download
                        st.session_state['download_ready'] = True
                        st.success(f"Laporan siap! Ditemukan {len(final_df)} peserta. Klik tombol 'Unduh' di bawah.")

                    else:
                        st.error("Data Dapodik (data_dapodik_name) tidak dapat dimuat.")
                except Exception as e:
                    st.error(f"Gagal memproses laporan: {e}")

        # Tombol download akan muncul di sini setelah data siap
        if st.session_state.get('download_ready', False):
            st.download_button(
                label="✅ Unduh File Excel Sekarang",
                data=st.session_state['download_data'],
                file_name=f"rekomendasi_peserta_belum_pelatihan_{pd.Timestamp.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                on_click=lambda: st.session_state.update(download_ready=False) # Reset state
            )
        
        st.markdown("---")
        # ==================================================================
        # === AKHIR BAGIAN BARU ===
        # ==================================================================
        
        st.subheader("💡 Rekomendasi per Sekolah") # <-- Judul diubah
        st.write("Pilih sekolah untuk melihat daftar nama di Dapodik yang belum terdata mengikuti pelatihan.")

        try:
            school_list_df = df[['NPSN', 'ASAL_SEKOLAH']].dropna(subset=['NPSN'])
            school_list_df = school_list_df.drop_duplicates(subset=['NPSN'], keep='first')
            school_list_df = school_list_df.merge(df_sekolah_sumber[['NPSN', 'STATUS', 'KECAMATAN', 'KABUPATEN']], on='NPSN', how='left')
            school_list_df = school_list_df.dropna(subset=['STATUS', 'KECAMATAN', 'KABUPATEN']) 

            if 'KECAMATAN' in school_list_df.columns:
                school_list_df['KECAMATAN'] = school_list_df['KECAMATAN'].astype(str).str.replace("KEC. ", "").str.strip()
        except Exception as e:
            st.error(f"Gagal memproses daftar sekolah untuk filter: {e}")
            school_list_df = pd.DataFrame(columns=['ASAL_SEKOLAH', 'NPSN', 'STATUS', 'KECAMATAN', 'KABUPATEN'])

        reco_col1, reco_col2 = st.columns(2)
        with reco_col1:
            status_reco_filter = st.multiselect(
                "Filter Status Sekolah",
                options=school_list_df['STATUS'].unique(),
                key="reco_status_filter"
            )
        with reco_col2:
            target_kabupaten = ['KOTA ADM. JAKARTA UTARA', 'KAB. ADM. KEP. SERIBU']
            kecamatan_options = school_list_df[
                school_list_df['KABUPATEN'].isin(target_kabupaten)
            ]['KECAMATAN'].unique()

            kec_reco_filter = st.multiselect(
                "Filter Kecamatan",
                options=sorted(kecamatan_options),
                key="reco_kec_filter"
            )

        filtered_schools_for_reco = school_list_df.copy()
        if status_reco_filter:
            filtered_schools_for_reco = filtered_schools_for_reco[filtered_schools_for_reco['STATUS'].isin(status_reco_filter)]
        if kec_reco_filter:
            filtered_schools_for_reco = filtered_schools_for_reco[filtered_schools_for_reco['KECAMATAN'].isin(kec_reco_filter)]
        
        display_schools_df = filtered_schools_for_reco
        if not kec_reco_filter: 
            temp_df_status_only = school_list_df.copy()
            if status_reco_filter: 
                temp_df_status_only = temp_df_status_only[temp_df_status_only['STATUS'].isin(status_reco_filter)]
            display_schools_df = temp_df_status_only

        school_name_list = ["-- Pilih Sekolah --"] + sorted(display_schools_df['ASAL_SEKOLAH'].unique())
        selected_school_name = st.selectbox(
            "Pilih Sekolah",
            school_name_list,
            key="reco_school_select"
        )

        if selected_school_name != "-- Pilih Sekolah --":
            try:
                selected_npsn = str(display_schools_df[
                    display_schools_df['ASAL_SEKOLAH'] == selected_school_name
                ].iloc[0]['NPSN'])
                
                df_dapodik = load_dapodik_data(json_keyfile_str, spreadsheet_id)
                NAMA_KOLOM_NAMA_DAPODIK = 'NAMA_LENGKAP'

                if not df_dapodik.empty:
                    master_names = set(df_dapodik[df_dapodik['NPSN'] == selected_npsn][NAMA_KOLOM_NAMA_DAPODIK])
                    trained_names = set(df[df['NPSN'] == selected_npsn]['NAMA_PESERTA'])
                    recommendation_list = sorted(list(master_names - trained_names))
                    
                    st.write(f"Ditemukan **{len(recommendation_list)}** orang di **{selected_school_name}** (NPSN: {selected_npsn}) yang belum terdata pelatihan:")
                    
                    if recommendation_list:
                        reco_df = pd.DataFrame(recommendation_list, columns=["Nama (Rekomendasi)"])
                        reco_df.index += 1
                        st.dataframe(reco_df, use_container_width=True, height=300)
                    else:
                        if not master_names:
                            st.warning("Tidak ada data nama ditemukan di sheet 'data_dapodik_name' untuk sekolah ini.")
                        else:
                            st.success("Semua nama di data Dapodik sekolah ini sudah terdata mengikuti pelatihan.")
            except Exception as e:
                st.error(f"Gagal memproses data rekomendasi. Pastikan sheet 'data_dapodik_name' ada. Error: {e}")
    
    # --- TAB 4: UPLOAD DATA ---
    with tab_upload:
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
    
    # --- FOOTER (DI LUAR SEMUA TAB) ---
    st.markdown("---")
    st.markdown(f'*Data cutoff: {pd.Timestamp.now(tz="Asia/Jakarta").strftime("%d %B %Y")}*')
    st.markdown(
        """
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


