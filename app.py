import streamlit as st
import db_api
import base64
from io import BytesIO
from PIL import Image
from datetime import datetime
import pandas as pd

# --- [UI] 고령자 맞춤형 UI 및 레이아웃 깨짐 방지 CSS ---
st.markdown("""
    <style>
    body { background-color: #f4f6f9 !important; }
    
    /* 1. 입력창 잘림 현상 방지: 강제 높이 지정 대신 내부 폰트와 패딩만 조절 */
    div[data-baseweb="input"] input, 
    div[data-baseweb="select"] div {
        font-size: 20px !important;
        padding: 10px !important;
    }

    /* 2. 라디오 버튼 -> 4색상 대형 블록 버튼화 */
    div[data-testid="stRadio"] > div[role="radiogroup"] {
        display: flex !important;
        flex-direction: row !important;
        gap: 10px !important;
        width: 100% !important;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label {
        flex: 1 !important; 
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        padding: 20px 0px !important; 
        border-radius: 12px !important;
        margin: 0 !important;
        border: 2px solid transparent !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:first-child {
        display: none !important;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:last-child,
    div[data-testid="stRadio"] > div[role="radiogroup"] > label p {
        margin: 0 !important; padding: 0 !important;
        font-weight: 900 !important; font-size: 20px !important;
        white-space: nowrap !important; display: block !important;
    }

    /* 4색 버튼 색상 지정 */
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:nth-child(1) { background-color: #2b8a3e !important; }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:nth-child(1) * { color: white !important; }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:nth-child(2) { background-color: #fcc419 !important; }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:nth-child(2) * { color: #212529 !important; }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:nth-child(3) { background-color: #e03131 !important; }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:nth-child(3) * { color: white !important; }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:nth-child(4) { background-color: #868e96 !important; }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:nth-child(4) * { color: white !important; }

    /* 선택 효과 */
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:not(:checked)) { opacity: 0.3 !important; }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:checked) {
        opacity: 1.0 !important; transform: scale(1.05) !important;
        box-shadow: 0px 6px 12px rgba(0,0,0,0.3) !important;
        border: 3px solid #212529 !important;
    }

    /* 3. 모바일 화면 최적화 */
    @media (max-width: 768px) {
        html, body, [class*="st-"] { font-size: 18px !important; }
        .stButton button { font-size: 20px !important; padding: 15px !important; border-radius: 12px !important; }
        h1 { font-size: 30px !important; }
        h2 { font-size: 24px !important; }
        h3 { font-size: 20px !important; margin-bottom: 15px !important;}
        div[data-testid="stRadio"] > div[role="radiogroup"] > label p { font-size: 18px !important; }
    }
    </style>
    """, unsafe_allow_html=True)

# 🌟 관리자 사이드바 기본 숨김 처리 (collapsed)
st.set_page_config(page_title="GS E&C 안전관리", layout="wide", initial_sidebar_state="collapsed")

# 세션 상태 초기화
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "role" not in st.session_state: st.session_state.role = "Worker"
if "worker_step" not in st.session_state: st.session_state.worker_step = "input"

project_code = st.query_params.get("projectCode", "GS_PROJECT_001")

def resize_image_to_base64(image_file, max_width=1024):
    img = Image.open(image_file)
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.Resampling.LANCZOS)
    buffered = BytesIO()
    if img.mode == 'RGBA': img = img.convert('RGB')
    img.save(buffered, format="JPEG", quality=80)
    return base64.b64encode(buffered.getvalue()).decode()

def to_excel(df_stats, df_logs):
    """데이터프레임을 엑셀 파일(바이트)로 변환"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_stats.to_excel(writer, index=False, sheet_name='점검 이행률')
        df_logs.to_excel(writer, index=False, sheet_name='상세 점검 결과')
    return output.getvalue()

# --- 사이드바 ---
with st.sidebar:
    st.title("⚙️ 관리자 메뉴")
    if not st.session_state.logged_in:
        with st.form("login_form"):
            admin_id = st.text_input("ID", value="gsmaster")
            admin_pw = st.text_input("PW", type="password", value="1234")
            if st.form_submit_button("로그인 실행", use_container_width=True):
                if admin_id == "gsmaster" and admin_pw == "1234":
                    st.session_state.logged_in = True
                    st.session_state.role = "Admin"
                    st.rerun()
                else: st.error("정보 불일치")
    else:
        st.success("✅ Admin 모드")
        if st.button("로그아웃", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.role = "Worker"
            st.rerun()

# ==========================================
# [ADMIN] 관리자 페이지
# ==========================================
if st.session_state.role == "Admin":
    # 탭 이름 변경: 이행률 시각화 -> 대시보드
    menu = st.tabs(["📊 대시보드", "🏢 업체 관리", "📋 체크리스트", "🛠️ 장비 관리 (수정/삭제)"])
    
    with menu[0]: # 1. 대시보드 & 엑셀 다운로드
        st.header("📅 일일 점검 대시보드")
        sel_date = st.date_input("조회 날짜", value=datetime.now().date())
        stats = db_api.get_daily_stats(sel_date.strftime("%Y-%m-%d"))
        logs = db_api.get_daily_logs_for_excel(sel_date.strftime("%Y-%m-%d"))
        
        if stats:
            cols = st.columns(len(stats))
            chart_data = []
            for i, s in enumerate(stats):
                rate = (s['completed'] / s['total'] * 100) if s['total'] > 0 else 0
                cols[i].metric(s['type'], f"{s['completed']} / {s['total']}대", f"{rate:.1f}%")
                chart_data.append({"장비 종류": s['type'], "점검 완료": s['completed'], "미점검": s['total'] - s['completed']})
            
            st.divider()
            df_chart = pd.DataFrame(chart_data).set_index("장비 종류")
            st.bar_chart(df_chart, color=["#2b8a3e", "#e03131"]) 
            
            # 엑셀 다운로드 버튼
            df_stats = pd.DataFrame(stats)
            # 로그 데이터를 데이터프레임으로 정리
            logs_formatted = []
            for l in logs:
                logs_formatted.append({
                    "점검시간": l.get("created_at", "")[:16].replace("T", " "),
                    "장비번호": l.get("registration_number", ""),
                    "점검업체": l.get("partners", {}).get("partner_name", "") if l.get("partners") else "",
                    "점검자": l.get("inspector", ""),
                    "점검항목": l.get("inspection_items", {}).get("item_name", "") if l.get("inspection_items") else "",
                    "상태": l.get("status", ""),
                    "비고": l.get("inspection_note", "")
                })
            df_logs = pd.DataFrame(logs_formatted)
            
            st.download_button(
                label="📥 점검결과 Excel 다운로드",
                data=to_excel(df_stats, df_logs),
                file_name=f"현장안전점검결과_{sel_date.strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
        else: 
            st.info("데이터가 없습니다.")

    with menu[1]: # 2. 업체 관리
        st.header("🏢 협력업체 관리")
        with st.form("add_partner_form", clear_on_submit=True):
            new_p = st.text_input("새 업체명 입력 후 Enter")
            if st.form_submit_button("업체 추가"):
                if new_p: db_api.add_partner(project_code, new_p); st.rerun()
        
        partners = db_api.get_partners(project_code)
        for p in partners:
            c1, c2 = st.columns([0.8, 0.2])
            c1.write(f"• {p['partner_name']}")
            if c2.button("삭제", key=f"p_{p['partner_id']}"):
                db_api.delete_partner(p['partner_id']); st.rerun()

    with menu[2]: # 3. 체크리스트 및 장비 종류 관리
        col_left, col_right = st.columns([1, 1])
        
        with col_left:
            st.subheader("🚜 장비 종류 관리")
            with st.form("add_type_form", clear_on_submit=True):
                new_t = st.text_input("새 장비 종류 (Enter)")
                if st.form_submit_button("종류 추가"):
                    if new_t: db_api.add_equipment_type(new_t); st.rerun()
            
            types = db_api.get_equipment_types()
            for t in types:
                c1, c2 = st.columns([0.7, 0.3])
                c1.write(f"• {t['equipment_type']}")
                if c2.button("삭제", key=f"del_t_{t['equipment_type_id']}"):
                    success, msg = db_api.delete_equipment_type(t['equipment_type_id'])
                    if success: st.rerun()
                    else: st.error(msg)
                    
        with col_right:
            st.subheader("📋 체크리스트 관리")
            t_map = {t['equipment_type']: t['equipment_type_id'] for t in types}
            if not t_map:
                st.warning("장비 종류를 먼저 추가하세요.")
            else:
                sel_t = st.selectbox("수정할 장비 종류", options=list(t_map.keys()))
                t_id = t_map[sel_t]
                items = db_api.get_items_by_type(t_id)
                
                with st.form("add_item_form", clear_on_submit=True):
                    i_n = st.text_input("새 항목명 (Enter)")
                    i_d = st.text_area("설명 (선택)")
                    if st.form_submit_button("항목 저장"):
                        if i_n: db_api.add_inspection_item(t_id, i_n, i_d, len(items)+1); st.rerun()
                
                for it in items:
                    c1, c2 = st.columns([0.7, 0.3])
                    c1.write(f"**{it['item_number']}. {it['item_name']}**")
                    if c2.button("제외", key=f"it_{it['item_id']}"):
                        success, msg = db_api.delete_inspection_item(it['item_id'])
                        if success: st.rerun()
                        else: st.error(msg)

    with menu[3]: # 4. 장비 마스터 (표에서 직접 클릭)
        st.header("🛠️ 등록 장비 관리 (클릭하여 선택)")
        all_eqs = db_api.get_all_equipments()
        
        # 데이터프레임 생성
        df_display = pd.DataFrame([{
            "번호": eq['registration_number'], 
            "종류": eq['equipment_types']['equipment_type'], 
            "모델": eq['equipment_model'] or "-", 
            "등록일": eq['created_at'][:10]
        } for eq in all_eqs])
        
        # 표에서 한 줄을 선택하면 on_select 이벤트를 통해 페이지가 재실행됩니다.
        st.write("👇 **수정/삭제할 장비를 아래 표에서 클릭하세요.**")
        event = st.dataframe(df_display, use_container_width=True, hide_index=True, selection_mode="single-row", on_select="rerun")
        
        # 표에서 장비가 선택되었을 경우 하단에 수정/삭제 폼 표시
        if event.selection.rows:
            selected_idx = event.selection.rows[0]
            selected_reg = df_display.iloc[selected_idx]['번호']
            target_data = next(eq for eq in all_eqs if eq['registration_number'] == selected_reg)
            
            st.divider()
            st.subheader(f"✏️ [{selected_reg}] 장비 수정/삭제")
            with st.form("edit_eq_form"):
                new_reg = st.text_input("장비 번호", value=target_data['registration_number'])
                
                types = db_api.get_equipment_types()
                type_names = [t['equipment_type'] for t in types]
                t_map = {t['equipment_type']: t['equipment_type_id'] for t in types}
                current_type = target_data['equipment_types']['equipment_type']
                
                new_type = st.selectbox("장비 종류", options=type_names, index=type_names.index(current_type) if current_type in type_names else 0)
                new_model = st.text_input("모델명", value=target_data['equipment_model'] or "")
                
                col1, col2 = st.columns(2)
                if col1.form_submit_button("💾 정보 저장", type="primary", use_container_width=True):
                    db_api.update_equipment(selected_reg, new_reg, t_map[new_type], new_model)
                    st.success("수정 완료!")
                    st.rerun()
                if col2.form_submit_button("🗑️ 장비 삭제", use_container_width=True):
                    success, msg = db_api.delete_equipment(selected_reg)
                    if success: st.rerun()
                    else: st.error(msg)

# ==========================================
# [WORKER] 근로자 점검 화면 
# ==========================================
else:
    st.title("🚜 장비 일일 안전 점검")
    st.write("---")
    
    if st.session_state.worker_step == "input":
        st.subheader("1️⃣ 장비 번호를 입력해주세요")
        reg = st.text_input("장비 번호 (예: 01가1234)", placeholder="터치하여 입력하세요").replace(" ", "")
        
        st.subheader("2️⃣ 소속 업체를 선택해주세요")
        partners = db_api.get_partners(project_code)
        p_names = [p['partner_name'] for p in partners]
        sel_p = st.selectbox("업체 목록", options=["여기를 눌러 업체를 선택하세요"] + p_names)
        
        st.write("") 
        if st.button("🚀 점검 시작하기", type="primary", use_container_width=True):
            if reg and sel_p != "여기를 눌러 업체를 선택하세요":
                eq = db_api.check_equipment_exists(reg)
                st.session_state.temp_reg = reg
                st.session_state.temp_p_id = next(p['partner_id'] for p in partners if p['partner_name'] == sel_p)
                st.session_state.temp_p_name = sel_p
                if eq:
                    st.session_state.eq_data = eq
                    st.session_state.worker_step = "checklist"
                else: 
                    st.session_state.worker_step = "register"
                st.rerun()
            else: 
                st.error("⚠️ 장비 번호와 업체를 모두 확인해주세요.")

    elif st.session_state.worker_step == "register":
        st.error("⚠️ 처음 오신 장비입니다. 최초 1회 등록이 필요합니다.")
        types = db_api.get_equipment_types()
        t_opts = {t['equipment_type']: t['equipment_type_id'] for t in types}
        n_t = st.selectbox("어떤 장비인가요?", options=list(t_opts.keys()))
        n_m = st.text_input("모델명이 있다면 적어주세요 (선택)")
        
        st.write("") 
        col1, col2 = st.columns([0.3, 0.7])
        if col1.button("⬅️ 뒤로", use_container_width=True):
            st.session_state.worker_step = "input"
            st.rerun()
        if col2.button("✅ 장비 등록 및 점검 시작", type="primary", use_container_width=True):
            db_api.create_equipment(st.session_state.temp_reg, t_opts[n_t], n_m)
            st.session_state.eq_data = db_api.check_equipment_exists(st.session_state.temp_reg)
            st.session_state.worker_step = "checklist"
            st.rerun()

    elif st.session_state.worker_step == "checklist":
        eq = st.session_state.eq_data
        st.success(f"📋 {st.session_state.temp_reg} ({eq['equipment_types']['equipment_type']}) 점검표")
        
        # 뒤로가기 버튼 추가
        if st.button("⬅️ 장비 번호 다시 입력하기"):
            st.session_state.worker_step = "input"
            st.rerun()
            
        items = db_api.get_items_by_type(eq['equipment_type_id'])
        ins_results = []

        for it in items:
            st.write(f"### 📍 {it['item_number']}. {it['item_name']}")
            res = st.radio("상태", ["양호", "수리요", "불량", "기타"], key=f"r_{it['item_id']}", horizontal=True, label_visibility="collapsed")
            
            note, img_b64 = "", ""
            if res != "양호":
                st.warning("⚠️ 이상 발견: 사진과 내용을 남겨주세요.")
                cam = st.camera_input("📸 여기를 눌러 사진 촬영", key=f"cam_{it['item_id']}")
                if cam: img_b64 = resize_image_to_base64(cam)
                note = st.text_area("📝 조치 사항", key=f"n_{it['item_id']}", placeholder="어떤 문제가 있는지 적어주세요.")
            
            ins_results.append({"id": it['item_id'], "res": res, "note": note, "img": img_b64})
            st.divider()
        
        if st.button("✅ 오늘 점검 모두 완료하고 제출하기", type="primary", use_container_width=True):
            for r in ins_results:
                db_api.create_inspection_log(project_code, st.session_state.temp_reg, st.session_state.temp_p_id, r['id'], r['res'], r['note'], r['img'], st.session_state.temp_p_name)
            # 완료 페이지로 상태 변경
            st.session_state.worker_step = "complete"
            st.rerun()

    # 완료 페이지 로직 신설
    elif st.session_state.worker_step == "complete":
        st.success("🎉 점검이 성공적으로 완료되었습니다!")
        st.info("오늘도 현장의 안전을 지켜주셔서 감사합니다. 안전 작업 하십시오!")
        
        st.write("")
        st.write("")
        if st.button("🔄 추가 장비 점검하기", type="primary", use_container_width=True):
            st.session_state.worker_step = "input"
            st.rerun()
