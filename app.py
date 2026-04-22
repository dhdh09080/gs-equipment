import streamlit as st
import db_api
from datetime import datetime

st.set_page_config(page_title="GS E&C 안전관리 시스템", layout="wide")

# --- 세션 상태 관리 ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "role" not in st.session_state: st.session_state.role = "Worker"
if "worker_step" not in st.session_state: st.session_state.worker_step = "input"

# URL에서 프로젝트 코드 추출 (기본값 설정)
project_code = st.query_params.get("projectCode", "GS_PROJECT_001")

# --- 사이드바: 모드 전환 및 로그인 ---
with st.sidebar:
    st.title("🛡️ GS E&C 안전관리")
    if not st.session_state.logged_in:
        with st.expander("🔐 관리자 로그인"):
            admin_id = st.text_input("ID", value="gsmaster")
            admin_pw = st.text_input("PW", type="password", value="1234")
            if st.button("로그인"):
                if admin_id == "gsmaster" and admin_pw == "1234":
                    st.session_state.logged_in = True
                    st.session_state.role = "Admin"
                    st.rerun()
                else: st.error("로그인 정보 오류")
    else:
        st.success(f"현재: {st.session_state.role} 모드")
        if st.button("로그아웃"):
            st.session_state.logged_in = False
            st.session_state.role = "Worker"
            st.rerun()

# ==========================================
# [ADMIN] 관리자 페이지 로직
# ==========================================
if st.session_state.role == "Admin":
    menu = st.tabs(["📊 일일 이행률", "🏢 업체 관리", "📋 체크리스트", "🚜 장비 관리"])
    
    with menu[0]: # 일일 이행률 대시보드
        st.header("📅 장비별 점검 이행 현황")
        sel_date = st.date_input("조회 날짜", value=datetime.now().date())
        stats = db_api.get_daily_stats(sel_date.strftime("%Y-%m-%d"))
        
        if stats:
            cols = st.columns(len(stats))
            for i, s in enumerate(stats):
                rate = (s['completed'] / s['total'] * 100) if s['total'] > 0 else 0
                cols[i].metric(s['type'], f"{s['completed']}/{s['total']}", f"{rate:.1f}%")
                st.progress(rate / 100)
        else: st.info("데이터가 없습니다.")

    with menu[1]: # 업체 관리
        st.header("협력업체 리스트")
        partners = db_api.get_partners(project_code)
        new_p = st.text_input("신규 업체명")
        if st.button("업체 등록"):
            if new_p: db_api.add_partner(project_code, new_p); st.rerun()
        for p in partners:
            c1, c2 = st.columns([0.8, 0.2])
            c1.write(p['partner_name'])
            if c2.button("삭제", key=f"p_{p['partner_id']}"):
                db_api.delete_partner(p['partner_id']); st.rerun()

    with menu[2]: # 체크리스트 관리
        types = db_api.get_equipment_types()
        t_map = {t['equipment_type']: t['equipment_type_id'] for t in types}
        sel_t = st.selectbox("장비 종류 선택", options=list(t_map.keys()))
        t_id = t_map[sel_t]
        items = db_api.get_items_by_type(t_id)
        for it in items:
            it1, it2 = st.columns([0.8, 0.2])
            it1.write(f"{it['item_number']}. {it['item_name']}")
            if it2.button("삭제", key=f"it_{it['item_id']}"):
                db_api.delete_inspection_item(it['item_id']); st.rerun()
        with st.expander("➕ 항목 추가"):
            i_n = st.text_input("항목명"); i_d = st.text_area("설명")
            if st.button("항목 저장"):
                db_api.add_inspection_item(t_id, i_n, i_d, len(items)+1); st.rerun()

# ==========================================
# [WORKER] 근로자 점검 페이지 로직
# ==========================================
else:
    st.title("🚜 장비 일일 안전 점검")
    
    if st.session_state.worker_step == "input":
        reg = st.text_input("장비 번호 (Serial No.)").replace(" ", "")
        partners = db_api.get_partners(project_code)
        p_names = [p['partner_name'] for p in partners]
        sel_p = st.selectbox("소속 업체 선택", options=["선택하세요"] + p_names)
        
        if st.button("점검 시작"):
            if reg and sel_p != "선택하세요":
                eq = db_api.check_equipment_exists(reg)
                st.session_state.temp_reg = reg
                st.session_state.temp_p_id = next(p['partner_id'] for p in partners if p['partner_name'] == sel_p)
                st.session_state.temp_p_name = sel_p
                if eq:
                    st.session_state.eq_data = eq
                    st.session_state.worker_step = "checklist"
                else: st.session_state.worker_step = "register"
                st.rerun()
            else: st.warning("정보를 입력하세요.")

    elif st.session_state.worker_step == "register":
        st.warning(f"미등록 장비입니다. [{st.session_state.temp_reg}] 등록")
        types = db_api.get_equipment_types()
        t_opts = {t['equipment_type']: t['equipment_type_id'] for t in types}
        n_t = st.selectbox("장비 종류", options=list(t_opts.keys()))
        n_m = st.text_input("모델명 (선택)")
        if st.button("등록 완료 및 점검"):
            db_api.create_equipment(st.session_state.temp_reg, t_opts[n_t], n_m)
            st.session_state.eq_data = db_api.check_equipment_exists(st.session_state.temp_reg)
            st.session_state.worker_step = "checklist"; st.rerun()

    elif st.session_state.worker_step == "checklist":
        eq = st.session_state.eq_data
        st.subheader(f"📋 {eq['equipment_types']['equipment_type']} 점검표")
        items = db_api.get_items_by_type(eq['equipment_type_id'])
        results = {}
        for it in items:
            st.write(f"**{it['item_number']}. {it['item_name']}**")
            res = st.radio("결과", ["양호", "불량", "N/A"], key=f"r_{it['item_id']}", horizontal=True)
            note = st.text_input("비고", key=f"n_{it['item_id']}")
            results[it['item_id']] = {"res": res, "note": note}
        
        if st.button("✅ 점검 제출"):
            for i_id, val in results.items():
                db_api.create_inspection_log(project_code, st.session_state.temp_reg, st.session_state.temp_p_id, i_id, val['res'], val['note'], st.session_state.temp_p_name)
            st.success("점검이 완료되었습니다!"); st.session_state.worker_step = "input"; st.rerun()
