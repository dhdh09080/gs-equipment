import streamlit as st
import db_api
import base64
from io import BytesIO
from PIL import Image
from datetime import datetime

# --- [UI] 고령자 친화형 대형 글자 스타일 ---
st.markdown("""
    <style>
    html, body, [class*="st-"] { font-size: 22px !important; }
    .stButton button { height: 60px !important; font-size: 24px !important; font-weight: bold !important; }
    h1 { font-size: 40px !important; }
    h2 { font-size: 32px !important; }
    h3 { font-size: 28px !important; }
    div[data-baseweb="radio"] label { font-size: 26px !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

st.set_page_config(page_title="GS E&C 안전관리", layout="wide")

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

# --- 사이드바 로그인 ---
with st.sidebar:
    st.title("🛡️ 관리자 메뉴")
    if not st.session_state.logged_in:
        with st.expander("🔐 로그인 (gsmaster/1234)"):
            admin_id = st.text_input("ID", value="gsmaster")
            admin_pw = st.text_input("PW", type="password", value="1234")
            if st.button("로그인 실행"):
                if admin_id == "gsmaster" and admin_pw == "1234":
                    st.session_state.logged_in = True
                    st.session_state.role = "Admin"
                    st.rerun()
                else: st.error("정보 불일치")
    else:
        st.success(f"{st.session_state.role} 접속 중")
        if st.button("로그아웃"):
            st.session_state.logged_in = False
            st.session_state.role = "Worker"
            st.rerun()

# ==========================================
# [ADMIN] 관리자 대시보드 및 설정
# ==========================================
if st.session_state.role == "Admin":
    menu = st.tabs(["📊 일일 이행률", "🏢 업체 관리", "📋 체크리스트", "🚜 장비 마스터"])
    
    with menu[0]: # 1. 이행률 대시보드
        st.header("📅 일일 점검 현황")
        sel_date = st.date_input("날짜 선택", value=datetime.now().date())
        stats = db_api.get_daily_stats(sel_date.strftime("%Y-%m-%d"))
        if stats:
            cols = st.columns(len(stats))
            for i, s in enumerate(stats):
                rate = (s['completed'] / s['total'] * 100) if s['total'] > 0 else 0
                cols[i].metric(s['type'], f"{s['completed']}/{s['total']}대", f"{rate:.1f}% 이행")
                st.progress(rate / 100)
        else: st.info("선택한 날짜의 데이터가 없습니다.")

    with menu[1]: # 2. 업체 관리 (Enter 키 지원)
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

    with menu[2]: # 3. 체크리스트 관리 (소프트 딜리트)
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
            st.subheader("➕ 신규 항목 추가 (Enter)")
            i_n = st.text_input("항목명 (예: 타이어 마모)")
            i_d = st.text_area("항목 설명")
            if st.form_submit_button("항목 저장"):
                if i_n: db_api.add_inspection_item(t_id, i_n, i_d, len(items)+1); st.rerun()

    with menu[3]: # 4. 장비 마스터 (종류별 필터)
        st.header("🚜 등록 장비 마스터")
        all_eqs = db_api.get_all_equipments()
        filter_t = st.selectbox("종류 필터", options=["전체 보기"] + [t['equipment_type'] for t in types])
        
        display = []
        for eq in all_eqs:
            etype = eq['equipment_types']['equipment_type']
            if filter_t == "전체 보기" or filter_t == etype:
                display.append({
                    "번호": eq['registration_number'], "종류": etype, 
                    "모델": eq['equipment_model'] or "-", "등록일": eq['created_at'][:10]
                })
        st.table(display)

# ==========================================
# [WORKER] 근로자 점검 화면
# ==========================================
else:
    st.title("🚜 장비 안전 점검 (근로자용)")
    
    if st.session_state.worker_step == "input":
        reg = st.text_input("1. 장비 번호 입력 (Serial No.)").replace(" ", "")
        partners = db_api.get_partners(project_code)
        p_names = [p['partner_name'] for p in partners]
        sel_p = st.selectbox("2. 소속 업체 선택", options=["선택하세요"] + p_names)
        
        if st.button("점검 시작", type="primary", use_container_width=True):
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

    elif st.session_state.worker_step == "register":
        st.error("미등록 장비입니다. 시스템 등록을 진행합니다.")
        types = db_api.get_equipment_types()
        t_opts = {t['equipment_type']: t['equipment_type_id'] for t in types}
        n_t = st.selectbox("장비 종류", options=list(t_opts.keys()))
        n_m = st.text_input("모델명 (선택)")
        if st.button("장비 등록 및 점검", use_container_width=True):
            db_api.create_equipment(st.session_state.temp_reg, t_opts[n_t], n_m)
            st.session_state.eq_data = db_api.check_equipment_exists(st.session_state.temp_reg)
            st.session_state.worker_step = "checklist"; st.rerun()

    elif st.session_state.worker_step == "checklist":
        eq = st.session_state.eq_data
        st.subheader(f"📋 {eq['equipment_types']['equipment_type']} 점검 중")
        st.info(f"장비번호: {st.session_state.temp_reg} / 업체: {st.session_state.temp_p_name}")
        
        items = db_api.get_items_by_type(eq['equipment_type_id'])
        ins_results = []

        for it in items:
            st.divider()
            st.write(f"### {it['item_number']}. {it['item_name']}")
            res = st.radio("상태 선택", ["🟢 양호", "🟡 수리요", "🔴 불량", "⚫ 기타"], key=f"r_{it['item_id']}", horizontal=True)
            
            note, img_b64 = "", ""
            if res != "🟢 양호":
                st.warning("⚠️ 사진 촬영과 메모가 필요합니다.")
                cam = st.camera_input("📸 사진 촬영", key=f"cam_{it['item_id']}")
                if cam: img_b64 = resize_image_to_base64(cam)
                note = st.text_area("📝 조치 사항 입력", key=f"n_{it['item_id']}")
            
            ins_results.append({"id": it['item_id'], "res": res, "note": note, "img": img_b64})
        
        st.divider()
        if st.button("✅ 점검 결과 최종 제출", type="primary", use_container_width=True):
            for r in ins_results:
                db_api.create_inspection_log(project_code, st.session_state.temp_reg, st.session_state.temp_p_id, r['id'], r['res'], r['note'], r['img'], st.session_state.temp_p_name)
            st.success("점검 제출 완료! 감사합니다."); st.session_state.worker_step = "input"; st.rerun()
