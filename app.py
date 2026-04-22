import streamlit as st
import db_api
import base64
from io import BytesIO
from PIL import Image
from datetime import datetime

# --- [UI] 모바일 최적화 및 4색상 네모 버튼 CSS 주입 ---
st.markdown("""
    <style>
    /* 1. 기본 버튼 및 텍스트 줄바꿈 설정 */
    .stButton button {
        white-space: nowrap !important;
        word-break: keep-all !important;
        min-height: 50px !important;
        height: auto !important;
        padding: 0.5rem 1rem !important;
        width: 100% !important;
    }
    div[data-testid="stMarkdownContainer"] p {
        word-break: keep-all !important;
    }

    /* 🌟 2. 라디오 버튼을 4색 컬러 블록 버튼으로 완벽 변환 🌟 */
    
    /* 가로로 꽉 차게 4등분 배치 */
    div[data-testid="stRadio"] div[role="radiogroup"] {
        display: flex !important;
        flex-direction: row !important;
        gap: 8px !important;
        flex-wrap: nowrap !important; /* 모바일에서도 무조건 한 줄 유지 */
        width: 100% !important;
    }
    
    /* 각 옵션 라벨을 박스 형태로 디자인 */
    div[data-testid="stRadio"] div[role="radiogroup"] label {
        flex: 1 !important; /* 공간을 1/4씩 공평하게 나눠 가짐 */
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        padding: 15px 0 !important;
        border-radius: 8px !important;
        margin: 0 !important;
        border: 2px solid transparent !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
    }

    /* 기본 동그라미 아이콘 완벽하게 숨기기 */
    div[data-testid="stRadio"] div[role="radiogroup"] label div:first-child {
        display: none !important;
    }

    /* 버튼 안의 텍스트 설정 */
    div[data-testid="stRadio"] div[role="radiogroup"] label p {
        margin: 0 !important;
        font-weight: 900 !important;
        font-size: 16px !important; /* 모바일에서 깨지지 않게 글자크기 조정 */
        white-space: nowrap !important;
    }

    /* --- [버튼별 고유 색상 지정] --- */
    /* 1번: 양호 (초록) */
    div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(1) { background-color: #2b8a3e !important; }
    div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(1) p { color: white !important; }

    /* 2번: 수리요 (노랑) */
    div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(2) { background-color: #fcc419 !important; }
    div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(2) p { color: #212529 !important; }

    /* 3번: 불량 (빨강) */
    div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(3) { background-color: #e03131 !important; }
    div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(3) p { color: white !important; }

    /* 4번: 기타 (회색) */
    div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(4) { background-color: #868e96 !important; }
    div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(4) p { color: white !important; }

    /* --- [선택 및 미선택 상태 시각화] --- */
    /* 선택되지 않은 버튼은 투명도를 낮춰 흐리게 (선택된 것 강조) */
    div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:not(:checked)) {
        opacity: 0.25 !important;
    }
    
    /* 선택된 버튼은 진하게 + 까만 테두리와 그림자 */
    div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {
        opacity: 1.0 !important;
        transform: scale(1.02);
        box-shadow: 0px 4px 8px rgba(0,0,0,0.2);
        border: 2px solid #212529 !important;
    }

    /* 3. 모바일/데스크탑 반응형 폰트 크기 */
    @media (max-width: 768px) {
        html, body, [class*="st-"] { font-size: 16px !important; }
        .stButton button { font-size: 16px !important; }
        h1 { font-size: 26px !important; }
        h2 { font-size: 22px !important; }
        h3 { font-size: 18px !important; }
        div[data-testid="stRadio"] div[role="radiogroup"] label p { font-size: 15px !important; } /* 네 칸이라 약간 작게 */
    }
    @media (min-width: 769px) {
        html, body, [class*="st-"] { font-size: 20px !important; }
        h1 { font-size: 36px !important; }
        h2 { font-size: 28px !important; }
        h3 { font-size: 24px !important; }
        div[data-testid="stRadio"] div[role="radiogroup"] label p { font-size: 18px !important; }
    }
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

# --- 사이드바 ---
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
# [ADMIN] 관리자 페이지
# ==========================================
if st.session_state.role == "Admin":
    menu = st.tabs(["📊 이행률", "🏢 업체 관리", "📋 체크리스트", "🚜 장비 마스터"])
    
    with menu[0]: # 1. 이행률 대시보드
        st.header("📅 일일 점검 현황")
        sel_date = st.date_input("날짜 선택", value=datetime.now().date())
        stats = db_api.get_daily_stats(sel_date.strftime("%Y-%m-%d"))
        if stats:
            cols = st.columns(len(stats))
            for i, s in enumerate(stats):
                rate = (s['completed'] / s['total'] * 100) if s['total'] > 0 else 0
                cols[i].metric(s['type'], f"{s['completed']}/{s['total']}대", f"{rate:.1f}%")
                st.progress(rate / 100)
        else: st.info("데이터가 없습니다.")

    with menu[1]: # 2. 업체 관리
        st.header("🏢 협력업체 관리")
        with st.form("add_partner_form", clear_on_submit=True):
            new_p = st.text_input("새 업체명 입력 후 Enter")
            if st.form_submit_button("업체 추가"):
                if new_p: db_api.add_partner(project_code, new_p); st.rerun()
        
        partners = db_api.get_partners(project_code)
        for p in partners:
            c1, c2 = st.columns([0.7, 0.3])
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
            it1, it2 = st.columns([0.7, 0.3])
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

    with menu[3]: # 4. 장비 마스터
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
    st.title("🚜 장비 일일 점검")
    
    if st.session_state.worker_step == "input":
        reg = st.text_input("1. 장비 번호 입력").replace(" ", "")
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
        st.error("미등록 장비입니다. 등록을 진행합니다.")
        types = db_api.get_equipment_types()
        t_opts = {t['equipment_type']: t['equipment_type_id'] for t in types}
        n_t = st.selectbox("장비 종류", options=list(t_opts.keys()))
        n_m = st.text_input("모델명")
        if st.button("장비 등록 및 점검", use_container_width=True):
            db_api.create_equipment(st.session_state.temp_reg, t_opts[n_t], n_m)
            st.session_state.eq_data = db_api.check_equipment_exists(st.session_state.temp_reg)
            st.session_state.worker_step = "checklist"; st.rerun()

    elif st.session_state.worker_step == "checklist":
        eq = st.session_state.eq_data
        st.subheader(f"📋 {eq['equipment_types']['equipment_type']} 점검 중")
        st.info(f"번호: {st.session_state.temp_reg} / 업체: {st.session_state.temp_p_name}")
        
        items = db_api.get_items_by_type(eq['equipment_type_id'])
        ins_results = []

        for it in items:
            st.write(f"### {it['item_number']}. {it['item_name']}")
            
            # CSS로 네모 버튼화 된 라디오 입력 (이모티콘 제거, 상태 라벨 숨김)
            res = st.radio(
                "상태", 
                ["양호", "수리요", "불량", "기타"], 
                key=f"r_{it['item_id']}", 
                horizontal=True, 
                label_visibility="collapsed"
            )
            
            note, img_b64 = "", ""
            if res != "양호":
                st.warning("⚠️ 사진 촬영과 메모가 필요합니다.")
                cam = st.camera_input("📸 사진 촬영", key=f"cam_{it['item_id']}")
                if cam: img_b64 = resize_image_to_base64(cam)
                note = st.text_area("📝 조치 사항 입력", key=f"n_{it['item_id']}")
            
            ins_results.append({"id": it['item_id'], "res": res, "note": note, "img": img_b64})
            st.divider()
        
        if st.button("✅ 점검 결과 최종 제출", type="primary", use_container_width=True):
            for r in ins_results:
                db_api.create_inspection_log(project_code, st.session_state.temp_reg, st.session_state.temp_p_id, r['id'], r['res'], r['note'], r['img'], st.session_state.temp_p_name)
            st.success("점검 제출 완료!"); st.session_state.worker_step = "input"; st.rerun()
