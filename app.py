import streamlit as st
import db_api

st.set_page_config(page_title="GS E&C 안전 점검 시스템", layout="wide")

# --- 세션 상태 초기화 ---
if "page" not in st.session_state: st.session_state.page = "inspection"
if "reg_no" not in st.session_state: st.session_state.reg_no = ""

# --- 사이드바: 관리자 메뉴 ---
with st.sidebar:
    st.header("⚙️ 관리자 도구")
    menu = st.radio("메뉴 선택", ["📱 현장 점검 (근로자용)", "🏗️ 장비 등록/수정 (관리자용)"])
    
    if menu == "📱 현장 점검 (근로자용)":
        st.session_state.page = "inspection"
    else:
        st.session_state.page = "admin_manage"

# --- [관리자 전용] 장비 관리 페이지 ---
def render_admin_manage():
    st.title("🏗️ 장비 마스터 관리")
    
    tab1, tab2 = st.tabs(["신규 장비 등록", "기존 정보 수정"])
    
    types = db_api.get_equipment_types()
    type_options = {t['equipment_type']: t['equipment_type_id'] for t in types}

    with tab1:
        st.subheader("새로운 장비를 시스템에 추가합니다.")
        new_reg = st.text_input("장비 등록번호 (예: 01가1234)", key="add_reg").replace(" ", "")
        new_type = st.selectbox("장비 종류", options=list(type_options.keys()), key="add_type")
        new_model = st.text_input("모델명 (선택)", key="add_model")
        
        if st.button("장비 등록하기", type="primary"):
            if new_reg:
                db_api.create_equipment(new_reg, type_options[new_type], new_model)
                st.success(f"[{new_reg}] 등록 완료!")
            else:
                st.error("등록번호를 입력해주세요.")

    with tab2:
        st.subheader("기존 장비의 정보를 수정합니다.")
        search_reg = st.text_input("수정할 장비 번호 조회").replace(" ", "")
        if search_reg:
            eq = db_api.check_equipment_exists(search_reg)
            if eq:
                edit_reg = st.text_input("등록번호 수정", value=eq['registration_number'])
                edit_type = st.selectbox("장비 종류 수정", options=list(type_options.keys()), 
                                        index=list(type_options.values()).index(eq['equipment_type_id']))
                edit_model = st.text_input("모델명 수정", value=eq['equipment_model'] or "")
                
                if st.button("정보 수정 저장"):
                    db_api.update_equipment(search_reg, edit_reg, type_options[edit_type], edit_model)
                    st.success("정보가 업데이트되었습니다.")
            else:
                st.warning("해당 번호로 등록된 장비가 없습니다.")

# --- [근로자 전용] 점검 흐름 ---
def render_inspection_flow():
    # 기존에 작성했던 장비 확인 -> 업체 선택 -> 점검 항목 로직이 여기 들어갑니다.
    # (코드 간결화를 위해 핵심 단계만 표시)
    st.title("🚜 현장 장비 안전 점검")
    reg_input = st.text_input("장비 번호를 입력하세요", value=st.session_state.reg_no)
    
    if st.button("점검 시작"):
        eq = db_api.check_equipment_exists(reg_input.replace(" ", ""))
        if eq:
            st.session_state.reg_no = reg_input
            st.success(f"[{eq['equipment_types']['equipment_type']}] 확인되었습니다. 다음 단계로 이동합니다.")
            # 이후 로직 진행...
        else:
            st.error("등록되지 않은 장비입니다.")
            if st.button("관리자 모드에서 이 장비 등록하기"):
                st.session_state.page = "admin_manage"
                st.rerun()

# --- 메인 라우팅 ---
if st.session_state.page == "admin_manage":
    render_admin_manage()
else:
    render_inspection_flow()
