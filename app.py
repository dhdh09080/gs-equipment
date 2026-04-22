import streamlit as st
import db_api

st.set_page_config(page_title="GS E&C 안전시스템", layout="wide")

# --- 세션 상태 ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "role" not in st.session_state: st.session_state.role = "Worker"
if "worker_step" not in st.session_state: st.session_state.worker_step = "input"

# --- 사이드바 로그인/로그아웃 ---
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
# [관리자 화면] 대시보드 & 체크리스트 관리
# ==========================================
if st.session_state.role == "Admin":
    menu = st.tabs(["📊 현황 대시보드", "📋 체크리스트 관리", "🚜 장비 마스터"])
    
    with menu[0]:
        st.header("현장 장비 등록 현황")
        stats = db_api.get_dashboard_data()
        cols = st.columns(len(stats))
        for i, s in enumerate(stats):
            cols[i].metric(s['equipment_type'], f"{s['total_equipments']}대", f"점검 {s['total_inspections']}건")
        
        st.subheader("전체 장비 리스트")
        st.dataframe(db_api.get_all_equipments(), use_container_width=True)

    with menu[1]:
        st.header("장비 종류별 체크리스트 설정")
        types = db_api.get_equipment_types()
        type_map = {t['equipment_type']: t['equipment_type_id'] for t in types}
        selected_type = st.selectbox("수정할 장비 종류", options=list(type_map.keys()))
        
        target_id = type_map[selected_type]
        items = db_api.get_items_by_type(target_id)
        
        st.write(f"**현재 {selected_type} 점검 항목:** {len(items)}개")
        for item in items:
            col1, col2 = st.columns([0.8, 0.2])
            col1.write(f"{item['item_number']}. {item['item_name']}")
            if col2.button("삭제", key=f"del_{item['item_id']}"):
                db_api.delete_inspection_item(item['item_id'])
                st.rerun()
        
        with st.expander("➕ 새 점검 항목 추가"):
            new_name = st.text_input("항목명 (예: 브레이크 상태)")
            new_desc = st.text_area("상세 설명")
            new_num = st.number_input("순서", value=len(items)+1)
            if st.button("항목 저장"):
                db_api.add_inspection_item(target_id, new_name, new_desc, new_num)
                st.rerun()

# ==========================================
# [근로자 화면] 장비별 맞춤 점검
# ==========================================
else:
    st.title("🚜 현장 장비 안전 점검")
    
    if st.session_state.worker_step == "input":
        reg_no = st.text_input("1. 장비 등록번호 (Serial Num.)").replace(" ", "")
        partner = st.text_input("2. 업체명 입력")
        
        if st.button("다음 단계로"):
            if reg_no and partner:
                eq = db_api.check_equipment_exists(reg_no)
                st.session_state.temp_reg = reg_no
                st.session_state.temp_partner = partner
                
                if eq:
                    st.session_state.eq_data = eq
                    st.session_state.worker_step = "checklist"
                else:
                    st.session_state.worker_step = "register"
                st.rerun()
            else: st.warning("모든 정보를 입력해주세요.")

    elif st.session_state.worker_step == "register":
        st.warning(f"등록되지 않은 장비입니다. [{st.session_state.temp_reg}] 장비를 먼저 등록합니다.")
        types = db_api.get_equipment_types()
        type_options = {t['equipment_type']: t['equipment_type_id'] for t in types}
        
        new_type = st.selectbox("장비 종류", options=list(type_options.keys()))
        new_model = st.text_input("모델명 (선택)")
        
        if st.button("장비 등록 및 점검 시작"):
            db_api.create_equipment(st.session_state.temp_reg, type_options[new_type], new_model)
            st.session_state.eq_data = db_api.check_equipment_exists(st.session_state.temp_reg)
            st.session_state.worker_step = "checklist"
            st.rerun()

    elif st.session_state.worker_step == "checklist":
        eq = st.session_state.eq_data
        st.subheader(f"📋 {eq['equipment_types']['equipment_type']} 점검표 ({st.session_state.temp_reg})")
        
        # 장비 종류별로 다른 항목 로드
        items = db_api.get_items_by_type(eq['equipment_type_id'])
        
        for item in items:
            st.write(f"**{item['item_number']}. {item['item_name']}**")
            st.radio("결과", ["양호", "불량", "해당없음"], key=f"check_{item['item_id']}", horizontal=True)
        
        if st.button("최종 제출"):
            st.success("점검 결과가 성공적으로 제출되었습니다!")
            st.session_state.worker_step = "input"
            st.rerun()
