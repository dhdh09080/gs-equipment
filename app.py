import streamlit as st
import db_api
import base64
from io import BytesIO
from PIL import Image
from datetime import datetime

# UI 스타일 설정
st.markdown("""
    <style>
    html, body, [class*="st-"] { font-size: 20px !important; }
    .stButton button { height: 50px !important; font-size: 20px !important; }
    </style>
    """, unsafe_allow_html=True)

st.set_page_config(page_title="GS E&C 안전관리", layout="wide")

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
    img.save(buffered, format="JPEG", quality=85)
    return base64.b64encode(buffered.getvalue()).decode()

# --- 사이드바 ---
with st.sidebar:
    st.title("🛡️ 관리 메뉴")
    if not st.session_state.logged_in:
        with st.expander("🔐 관리자 로그인"):
            admin_id = st.text_input("ID", value="gsmaster")
            admin_pw = st.text_input("PW", type="password", value="1234")
            if st.button("로그인"):
                if admin_id == "gsmaster" and admin_pw == "1234":
                    st.session_state.logged_in = True
                    st.session_state.role = "Admin"
                    st.rerun()
                else: st.error("정보 불일치")
    else:
        st.write(f"✅ **{st.session_state.role} 모드**")
        if st.button("로그아웃"):
            st.session_state.logged_in = False
            st.session_state.role = "Worker"
            st.rerun()

# ==========================================
# [ADMIN] 관리자 페이지
# ==========================================
if st.session_state.role == "Admin":
    menu = st.tabs(["📊 이행률", "🏢 업체 관리", "📋 체크리스트", "🚜 장비 마스터"])
    
    with menu[0]: # 이행률
        sel_date = st.date_input("날짜 선택", value=datetime.now().date())
        stats = db_api.get_daily_stats(sel_date.strftime("%Y-%m-%d"))
        if stats:
            cols = st.columns(len(stats))
            for i, s in enumerate(stats):
                rate = (s['completed'] / s['total'] * 100) if s['total'] > 0 else 0
                cols[i].metric(s['type'], f"{s['completed']}/{s['total']}", f"{rate:.1f}%")

    with menu[1]: # 업체 관리 (Enter 지원)
        st.header("협력업체 관리")
        with st.form("add_partner_form", clear_on_submit=True):
            new_p = st.text_input("추가할 업체명을 입력하고 엔터를 누르세요")
            if st.form_submit_button("업체 등록"):
                if new_p: db_api.add_partner(project_code, new_p); st.rerun()
        
        partners = db_api.get_partners(project_code)
        for p in partners:
            c1, c2 = st.columns([0.8, 0.2])
            c1.write(f"• {p['partner_name']}")
            if c2.button("삭제", key=f"p_{p['partner_id']}"):
                db_api.delete_partner(p['partner_id']); st.rerun()

    with menu[2]: # 체크리스트 관리 (Enter 지원)
        types = db_api.get_equipment_types()
        t_map = {t['equipment_type']: t['equipment_type_id'] for t in types}
        sel_t = st.selectbox("장비 종류 선택", options=list(t_map.keys()))
        t_id = t_map[sel_t]
        items = db_api.get_items_by_type(t_id)
        
        for it in items:
            it1, it2 = st.columns([0.8, 0.2])
            it1.write(f"{it['item_number']}. {it['item_name']}")
            if it2.button("항목 삭제", key=f"it_{it['item_id']}"):
                db_api.delete_inspection_item(it['item_id']); st.rerun()
        
        with st.form("add_item_form", clear_on_submit=True):
            i_n = st.text_input("새 점검 항목명 입력 (엔터로 저장)")
            i_d = st.text_area("항목 설명 (선택)")
            if st.form_submit_button("항목 추가"):
                if i_n: db_api.add_inspection_item(t_id, i_n, i_d, len(items)+1); st.rerun()

    with menu[3]: # 장비 마스터 관리 (필터링 추가)
        st.header("🚜 등록 장비 마스터 리스트")
        all_eqs = db_api.get_all_equipments()
        
        # 종류별 필터링 기능
        types_list = ["전체 보기"] + [t['equipment_type'] for t in types]
        filter_type = st.selectbox("종류별로 보기", options=types_list)
        
        # 데이터 가공 및 필터링
        display_data = []
        for eq in all_eqs:
            eq_type = eq['equipment_types']['equipment_type']
            if filter_type == "전체 보기" or filter_type == eq_type:
                display_data.append({
                    "등록번호": eq['registration_number'],
                    "장비종류": eq_type,
                    "모델명": eq['equipment_model'] or "-",
                    "등록일": eq['created_at'][:10]
                })
        
        st.table(display_data) if display_data else st.info("등록된 장비가 없습니다.")

# ==========================================
# [WORKER] 근로자 점검 페이지
# ==========================================
else:
    # ... (기존 근로자 로직 유지)
    st.title("🚜 장비 일일 점검")
    if st.session_state.worker_step == "input":
        reg = st.text_input("1. 장비 번호 입력").replace(" ", "")
        partners = db_api.get_partners(project_code)
        p_names = [p['partner_name'] for p in partners]
        sel_p = st.selectbox("2. 소속 업체 선택", options=["선택하세요"] + p_names)
        if st.button("점검 시작하기", type="primary", use_container_width=True):
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
    # ... (생략된 checklist 및 register 로직은 이전과 동일하게 유지)
    elif st.session_state.worker_step == "register":
        st.error("처음 보는 장비입니다. 등록이 필요합니다.")
        types = db_api.get_equipment_types()
        t_opts = {t['equipment_type']: t['equipment_type_id'] for t in types}
        n_t = st.selectbox("장비 종류", options=list(t_opts.keys()))
        n_m = st.text_input("모델명 (예: DX140)")
        if st.button("등록하고 점검 시작"):
            db_api.create_equipment(st.session_state.temp_reg, t_opts[n_t], n_m)
            st.session_state.eq_data = db_api.check_equipment_exists(st.session_state.temp_reg)
            st.session_state.worker_step = "checklist"; st.rerun()

    elif st.session_state.worker_step == "checklist":
        eq = st.session_state.eq_data
        st.subheader(f"📋 {eq['equipment_types']['equipment_type']} 점검 중")
        items = db_api.get_items_by_type(eq['equipment_type_id'])
        
        inspection_results = []

        for it in items:
            st.divider()
            st.write(f"### {it['item_number']}. {it['item_name']}")
            # 신호등 방식 선택지
            res = st.radio(
                f"{it['item_name']} 상태", 
                ["🟢 양호", "🟡 수리요", "🔴 불량", "⚫ 기타"], 
                key=f"r_{it['item_id']}", 
                horizontal=True
            )
            
            note = ""
            img_base64 = ""
            
            # [조건부 로직] 양호가 아닐 때만 노출
            if res != "🟢 양호":
                st.warning("⚠️ 사진 촬영과 내용을 적어주세요.")
                cam_img = st.camera_input("📸 현장 사진 찍기", key=f"cam_{it['item_id']}")
                if cam_img:
                    img_base64 = resize_image_to_base64(cam_img)
                note = st.text_area("📝 조치 사항/메모 입력", key=f"n_{it['item_id']}")
            
            inspection_results.append({
                "item_id": it['item_id'],
                "status": res,
                "note": note,
                "photo": img_base64
            })
        
        st.divider()
        if st.button("✅ 모든 점검 제출하기", type="primary", use_container_width=True):
            with st.spinner('서버에 저장 중...'):
                for result in inspection_results:
                    db_api.create_inspection_log(
                        project_code=project_code,
                        reg_number=st.session_state.temp_reg,
                        partner_id=st.session_state.temp_p_id,
                        item_id=result['item_id'],
                        status=result['status'],
                        note=result['note'],
                        photo=result['photo'],
                        inspector=st.session_state.temp_p_name
                    )
            st.success("오늘 점검을 마쳤습니다. 고생하셨습니다!")
            st.session_state.worker_step = "input"
            st.rerun()
