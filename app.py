import streamlit as st
import db_api

st.set_page_config(page_title="GS E&C 안전관리 시스템", layout="wide")

# --- 세션 상태 ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "role" not in st.session_state: st.session_state.role = "Worker"
if "worker_step" not in st.session_state: st.session_state.worker_step = "input"

# URL에서 프로젝트 코드 추출 (기본값 설정)
project_code = st.query_params.get("projectCode", "GS_PROJECT_001")

# --- 사이드바 로그인 ---
with st.sidebar:
    st.title("🛡️ 안전시스템")
    if not st.session_state.logged_in:
        with st.expander("🔐 관리자 로그인"):
            admin_id = st.text_input("ID", value="gsmaster")
            admin_pw = st.text_input("PW", type="password", value="1234")
            if st.button("로그인"):
                if admin_id == "gsmaster" and admin_pw == "1234":
                    st.session_state.logged_in = True
                    st.session_state.role = "Admin"
                    st.rerun()
                else: st.error("정보가 일치하지 않습니다.")
    else:
        st.write(f"✅ **{st.session_state.role} 모드**")
        if st.button("로그아웃"):
            st.session_state.logged_in = False
            st.session_state.role = "Worker"
            st.rerun()

# ==========================================
# [관리자 화면] 
# ==========================================
if st.session_state.role == "Admin":
    menu = st.tabs(["📊 현황", "🏢 업체 관리", "📋 체크리스트", "🚜 장비 마스터"])
    
    with menu[0]: # 현황
        stats = db_api.get_dashboard_data()
        if stats:
            cols = st.columns(len(stats))
            for i, s in enumerate(stats):
                cols[i].metric(s['equipment_type'], f"{s['total_equipments']}대")
        st.dataframe(db_api.get_all_equipments(), use_container_width=True)

    with menu[1]: # 업체 관리 (신설)
        st.header("현장 협력업체 관리")
        partners = db_api.get_partners(project_code)
        
        col_add1, col_add2 = st.columns([0.8, 0.2])
        new_partner_name = col_add1.text_input("신규 등록 업체명")
        if col_add2.button("업체 추가", use_container_width=True):
            if new_partner_name:
                db_api.add_partner(project_code, new_partner_name)
                st.success(f"[{new_partner_name}] 등록 완료")
                st.rerun()

        st.subheader("등록된 업체 목록")
        for p in partners:
            c1, c2 = st.columns([0.8, 0.2])
            c1.write(f"• {p['partner_name']}")
            if c2.button("삭제", key=f"del_p_{p['partner_id']}"):
                db_api.delete_partner(p['partner_id'])
                st.rerun()

    with menu[2]: # 체크리스트 관리 (기존 유지)
        types = db_api.get_equipment_types()
        type_map = {t['equipment_type']: t['equipment_type_id'] for t in types}
        selected_type = st.selectbox("수정할 장비 종류", options=list(type_map.keys()))
        target_id = type_map[selected_type]
        items = db_api.get_items_by_type(target_id)
        for item in items:
            it1, it2 = st.columns([0.8, 0.2])
            it1.write(f"{item['item_number']}. {item['item_name']}")
            if it2.button("항목 삭제", key=f"del_item_{item['item_id']}"):
                db_api.delete_inspection_item(item['item_id'])
                st.rerun()
        with st.expander("➕ 점검 항목 추가"):
            n_name = st.text_input("항목명")
            n_desc = st.text_area("설명")
            n_num = st.number_input("순번", value=len(items)+1)
            if st.button("저장"):
                db_api.add_inspection_item(target_id, n_name, n_desc, n_num)
                st.rerun()

# ==========================================
# [근로자 화면] 
# ==========================================
else:
    st.title("🚜 현장 장비 안전 점검")
    
    if st.session_state.worker_step == "input":
        reg_no = st.text_input("1. 장비 등록번호 (Serial Num.)").replace(" ", "")
        
        # 업체명을 드롭다운으로 선택 (개선된 부분)
        partners = db_api.get_partners(project_code)
        partner_list = [p['partner_name'] for p in partners]
        selected_partner = st.selectbox("2. 업체명 선택", options=["선택하세요"] + partner_list)
        
        if st.button("다음 단계로"):
            if reg_no and selected_partner != "선택하세요":
                eq = db_api.check_equipment_exists(reg_no)
                st.session_state.temp_reg = reg_no
                # 선택된 업체의 ID 찾기
                p_id = next(p['partner_id'] for p in partners if p['partner_name'] == selected_partner)
                st.session_state.temp_partner_id = p_id
                st.session_state.temp_partner_name = selected_partner
                
                if eq:
                    st.session_state.eq_data = eq
                    st.session_state.worker_step = "checklist"
                else:
                    st.session_state.worker_step = "register"
                st.rerun()
            else: st.warning("정보를 모두 입력/선택해주세요.")

    elif st.session_state.worker_step == "register":
        st.warning(f"미등록 장비입니다. [{st.session_state.temp_reg}] 등록 후 점검을 시작합니다.")
        types = db_api.get_equipment_types()
        type_options = {t['equipment_type']: t['equipment_type_id'] for t in types}
        new_type = st.selectbox("장비 종류", options=list(type_options.keys()))
        new_model = st.text_input("모델명 (선택)")
        
        if st.button("등록 및 점검 시작"):
            db_api.create_equipment(st.session_state.temp_reg, type_options[new_type], new_model)
            st.session_state.eq_data = db_api.check_equipment_exists(st.session_state.temp_reg)
            st.session_state.worker_step = "checklist"
            st.rerun()

    elif st.session_state.worker_step == "checklist":
        eq = st.session_state.eq_data
        st.subheader(f"📋 {eq['equipment_types']['equipment_type']} 점검 ({st.session_state.temp_reg})")
        st.write(f"🏢 업체: {st.session_state.temp_partner_name}")
        
        items = db_api.get_items_by_type(eq['equipment_type_id'])
        for item in items:
            st.write(f"**{item['item_number']}. {item['item_name']}**")
            st.radio("결과", ["양호", "불량", "N/A"], key=f"res_{item['item_id']}", horizontal=True)
            st.text_input("비고", key=f"note_{item['item_id']}")
        
        if st.button("최종 제출"):
            st.success("점검 완료!")
            st.session_state.worker_step = "input"
            st.rerun()
