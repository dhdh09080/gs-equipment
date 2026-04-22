import streamlit as st
import db_api
import base64
from io import BytesIO
from PIL import Image
from datetime import datetime
import pandas as pd

# --- [UI] 고령자 맞춤형 초거대 UI 및 시각화 CSS ---
st.markdown("""
    <style>
    /* 배경색을 살짝 어둡게 하여 눈부심 방지, 컨텐츠 박스를 하얗게 띄움 */
    body { background-color: #f4f6f9 !important; }
    
    /* 1. 고령자용 거대 입력창 & 드롭다운 */
    input, select, textarea {
        font-size: 22px !important;
        padding: 15px !important;
        min-height: 60px !important;
        border: 2px solid #adb5bd !important;
        border-radius: 10px !important;
    }
    input:focus, select:focus { border-color: #228be6 !important; }

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

    /* 버튼 색상 지정 */
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

# 🌟 중요: initial_sidebar_state="collapsed" 를 통해 처음에 사이드바를 완벽히 숨깁니다.
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

# --- 사이드바 ---
with st.sidebar:
    st.title("⚙️ 관리자 전용 메뉴")
    if not st.session_state.logged_in:
        with st.expander("🔐 관리자 로그인"):
            admin_id = st.text_input("ID", value="gsmaster")
            admin_pw = st.text_input("PW", type="password", value="1234")
            if st.button("로그인 실행", use_container_width=True):
                if admin_id == "gsmaster" and admin_pw == "1234":
                    st.session_state.logged_in = True
                    st.session_state.role = "Admin"
                    st.rerun()
                else: st.error("정보 불일치")
    else:
        st.success("✅ Admin 접속 중")
        if st.button("로그아웃", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.role = "Worker"
            st.rerun()

# ==========================================
# [ADMIN] 관리자 페이지
# ==========================================
if st.session_state.role == "Admin":
    menu = st.tabs(["📊 이행률 시각화", "🏢 업체 관리", "📋 체크리스트", "🛠️ 장비 관리 (수정/삭제)"])
    
    with menu[0]: # 1. 이행률 대시보드 (차트 추가)
        st.header("📅 일일 점검 현황 대시보드")
        sel_date = st.date_input("조회할 날짜 선택", value=datetime.now().date())
        stats = db_api.get_daily_stats(sel_date.strftime("%Y-%m-%d"))
        
        if stats:
            # 텍스트 메트릭
            cols = st.columns(len(stats))
            chart_data = []
            for i, s in enumerate(stats):
                rate = (s['completed'] / s['total'] * 100) if s['total'] > 0 else 0
                cols[i].metric(s['type'], f"{s['completed']} / {s['total']}대", f"{rate:.1f}%")
                chart_data.append({"장비 종류": s['type'], "완료 대수": s['completed'], "미완료 대수": s['total'] - s['completed']})
            
            # 시각화 바 차트 (UI/UX 강화)
            st.divider()
            st.subheader("📈 장비별 점검 완료 현황")
            df = pd.DataFrame(chart_data).set_index("장비 종류")
            st.bar_chart(df, color=["#2b8a3e", "#e03131"]) # 완료(초록), 미완료(빨강)
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

    with menu[2]: # 3. 체크리스트 관리
        types = db_api.get_equipment_types()
        t_map = {t['equipment_type']: t['equipment_type_id'] for t in types}
        sel_t = st.selectbox("수정할 장비 종류", options=list(t_map.keys()))
        t_id = t_map[sel_t]
        items = db_api.get_items_by_type(t_id)
        
        for it in items:
            it1, it2 = st.columns([0.8, 0.2])
            it1.write(f"**{it['item_number']}. {it['item_name']}**")
            if it2.button("항목 제외", key=f"it_{it['item_id']}"):
                success, msg = db_api.delete_inspection_item(it['item_id'])
                if success: st.rerun()
                else: st.error(msg)

        with st.form("add_item_form", clear_on_submit=True):
            i_n = st.text_input("새 항목명 (Enter)")
            i_d = st.text_area("항목 설명")
            if st.form_submit_button("항목 저장"):
                if i_n: db_api.add_inspection_item(t_id, i_n, i_d, len(items)+1); st.rerun()

    with menu[3]: # 4. 장비 마스터 (수정/삭제 기능 완벽 추가)
        st.header("🛠️ 등록 장비 정보 수정 및 삭제")
        all_eqs = db_api.get_all_equipments()
        
        # 장비 선택 드롭다운
        eq_list = ["선택하세요"] + [f"{eq['registration_number']} ({eq['equipment_types']['equipment_type']})" for eq in all_eqs]
        selected_eq_label = st.selectbox("수정 또는 삭제할 장비를 선택하세요", options=eq_list)
        
        if selected_eq_label != "선택하세요":
            # 선택한 장비의 실제 번호 추출
            selected_reg = selected_eq_label.split(" (")[0]
            target_data = next(eq for eq in all_eqs if eq['registration_number'] == selected_reg)
            
            with st.form("edit_eq_form"):
                st.info(f"현재 선택된 장비: {selected_reg}")
                new_reg = st.text_input("장비 번호 변경 (선택)", value=target_data['registration_number'])
                
                # 기존 장비 종류의 인덱스 찾기
                types = db_api.get_equipment_types()
                t_map = {t['equipment_type']: t['equipment_type_id'] for t in types}
                type_names = list(t_map.keys())
                current_type_name = target_data['equipment_types']['equipment_type']
                current_type_idx = type_names.index(current_type_name) if current_type_name in type_names else 0
                
                new_type = st.selectbox("장비 종류 변경", options=type_names, index=current_type_idx)
                new_model = st.text_input("모델명 변경", value=target_data['equipment_model'] or "")
                
                col1, col2 = st.columns(2)
                if col1.form_submit_button("💾 정보 수정 (저장)", type="primary", use_container_width=True):
                    db_api.update_equipment(selected_reg, new_reg, t_map[new_type], new_model)
                    st.success("수정되었습니다!")
                    st.rerun()
                    
                if col2.form_submit_button("🗑️ 장비 완전 삭제", use_container_width=True):
                    success, msg = db_api.delete_equipment(selected_reg)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
        
        st.divider()
        st.subheader("전체 장비 리스트 보기")
        display = [{"번호": eq['registration_number'], "종류": eq['equipment_types']['equipment_type'], "모델": eq['equipment_model'] or "-", "등록일": eq['created_at'][:10]} for eq in all_eqs]
        st.dataframe(display, use_container_width=True)

# ==========================================
# [WORKER] 근로자 점검 화면 (어르신 맞춤형)
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
        
        st.write("") # 여백
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
        n_m = st.text_input("모델명이 있다면 적어주세요 (선택사항)")
        
        st.write("") # 여백
        if st.button("✅ 장비 등록하고 점검 시작하기", type="primary", use_container_width=True):
            db_api.create_equipment(st.session_state.temp_reg, t_opts[n_t], n_m)
            st.session_state.eq_data = db_api.check_equipment_exists(st.session_state.temp_reg)
            st.session_state.worker_step = "checklist"
            st.rerun()

    elif st.session_state.worker_step == "checklist":
        eq = st.session_state.eq_data
        st.success(f"📋 {st.session_state.temp_reg} ({eq['equipment_types']['equipment_type']}) 점검을 시작합니다.")
        
        items = db_api.get_items_by_type(eq['equipment_type_id'])
        ins_results = []

        for it in items:
            st.write(f"### 📍 {it['item_number']}. {it['item_name']}")
            
            res = st.radio(
                "상태", 
                ["양호", "수리요", "불량", "기타"], 
                key=f"r_{it['item_id']}", 
                horizontal=True, 
                label_visibility="collapsed"
            )
            
            note, img_b64 = "", ""
            if res != "양호":
                st.warning("⚠️ 이상이 발견되었습니다. 현장 사진과 내용을 꼭 남겨주세요.")
                cam = st.camera_input("📸 여기를 눌러 사진 촬영", key=f"cam_{it['item_id']}")
                if cam: img_b64 = resize_image_to_base64(cam)
                note = st.text_area("📝 조치 사항 입력란", key=f"n_{it['item_id']}", placeholder="어떤 문제가 있는지 적어주세요.")
            
            ins_results.append({"id": it['item_id'], "res": res, "note": note, "img": img_b64})
            st.divider()
        
        st.write("") # 여백
        if st.button("✅ 오늘 점검 모두 완료하고 제출하기", type="primary", use_container_width=True):
            for r in ins_results:
                db_api.create_inspection_log(project_code, st.session_state.temp_reg, st.session_state.temp_p_id, r['id'], r['res'], r['note'], r['img'], st.session_state.temp_p_name)
            st.success("🎉 점검 제출 완료! 오늘도 안전 작업 하십시오.")
            st.session_state.worker_step = "input"
            st.rerun()
