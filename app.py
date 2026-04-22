import streamlit as st
import db_api
import base64
from io import BytesIO
from PIL import Image
from datetime import datetime, timedelta
import pandas as pd

# --- [UI] 고령자 맞춤형 및 GS E&C 모바일 스타일 CSS ---
st.markdown("""
    <style>
    /* 배경색 (GS E&C 스타일 밝은 회색) */
    body, .stApp { background-color: #f4f5f7 !important; }
    
    /* 🔥 1. 입력창 & 드롭다운 글자 잘림 완벽 해결 🔥 */
    div[data-baseweb="select"] > div, 
    div[data-baseweb="input"] > div > input {
        font-size: 18px !important;
        padding: 12px !important;
        min-height: 55px !important;
        line-height: 1.5 !important;
        border-radius: 8px !important;
        border: 1px solid #ced4da !important;
    }
    /* 드롭다운 리스트(팝업) 안쪽 글자 크기도 키움 */
    ul[data-baseweb="menu"] li {
        font-size: 18px !important;
        padding: 15px !important;
    }

    /* 2. 관리자 탭 (홈, 일일점검현황, 관리) 및 카드 디자인 */
    div.stTabs [data-baseweb="tab-list"] {
        background-color: white;
        padding: 0;
        border-bottom: 2px solid #e9ecef;
    }
    div.stTabs [data-baseweb="tab"] {
        font-size: 18px !important;
        font-weight: bold;
        padding: 15px 20px;
    }
    
    /* 카드형 컨테이너 스타일 (GS E&C 앱 스타일) */
    .custom-card {
        background-color: white;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0px 2px 5px rgba(0,0,0,0.05);
        border: 1px solid #e9ecef;
    }

    /* 3. 라디오 버튼 -> 4색상 대형 블록 버튼화 */
    div[data-testid="stRadio"] > div[role="radiogroup"] {
        display: flex !important; flex-direction: row !important; gap: 8px !important; width: 100% !important;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label {
        flex: 1 !important; display: flex !important; justify-content: center !important; align-items: center !important;
        padding: 18px 0px !important; border-radius: 8px !important; margin: 0 !important;
        border: 2px solid transparent !important; cursor: pointer !important; transition: all 0.2s ease !important;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:first-child { display: none !important; }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label p {
        margin: 0 !important; padding: 0 !important; font-weight: 900 !important; font-size: 18px !important;
    }

    /* 버튼 색상 지정 (양호/수리요/불량/기타) */
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:nth-child(1) { background-color: #78be20 !important; } /* GS Green */
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:nth-child(1) * { color: white !important; }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:nth-child(2) { background-color: #f2a900 !important; } /* GS Yellow */
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:nth-child(2) * { color: white !important; }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:nth-child(3) { background-color: #cf4520 !important; } /* GS Red */
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:nth-child(3) * { color: white !important; }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:nth-child(4) { background-color: #75787b !important; } /* GS Gray */
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:nth-child(4) * { color: white !important; }

    /* 선택 효과 */
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:not(:checked)) { opacity: 0.25 !important; }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:checked) {
        opacity: 1.0 !important; transform: scale(1.02) !important;
        box-shadow: 0px 4px 8px rgba(0,0,0,0.2) !important; border: 2px solid #122d43 !important;
    }

    /* 4. 엑셀 다운로드 플로팅 버튼 고정 */
    .floating-excel-btn {
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 9999;
    }
    
    /* 모바일 환경 텍스트 크기 일괄 조정 */
    @media (max-width: 768px) {
        html, body, [class*="st-"] { font-size: 16px !important; }
        .stButton button { font-size: 18px !important; padding: 12px !important; }
        div[data-testid="stRadio"] > div[role="radiogroup"] > label p { font-size: 16px !important; }
    }
    </style>
    """, unsafe_allow_html=True)

# 초기 설정
st.set_page_config(page_title="GS E&C 안전관리", layout="wide", initial_sidebar_state="collapsed")

if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "role" not in st.session_state: st.session_state.role = "Worker"
if "worker_step" not in st.session_state: st.session_state.worker_step = "input"
if "target_date" not in st.session_state: st.session_state.target_date = datetime.now().date()

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
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_stats.to_excel(writer, index=False, sheet_name='점검 요약')
        df_logs.to_excel(writer, index=False, sheet_name='점검 상세 내역')
    return output.getvalue()

# --- 사이드바 ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/ca/GS_E%26C_logo.svg/512px-GS_E%26C_logo.svg.png", width=150)
    st.title("⚙️ 관리자 로그인")
    if not st.session_state.logged_in:
        with st.form("login_form"):
            admin_id = st.text_input("ID", value="gsmaster")
            admin_pw = st.text_input("PW", type="password", value="1234")
            if st.form_submit_button("로그인", use_container_width=True):
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
    
    # 상단 날짜 컨트롤러 (화살표 포함)
    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
    col_l, col_d, col_r = st.columns([1, 4, 1])
    if col_l.button("◀ 이전일", use_container_width=True):
        st.session_state.target_date -= timedelta(days=1)
        st.rerun()
    
    # 날짜 캘린더 선택
    sel_date = col_d.date_input("조회일자", value=st.session_state.target_date, label_visibility="collapsed")
    if sel_date != st.session_state.target_date:
        st.session_state.target_date = sel_date
        st.rerun()
        
    if col_r.button("다음일 ▶", use_container_width=True):
        st.session_state.target_date += timedelta(days=1)
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # 탭 구성: 홈(대시보드), 일일점검현황, 관리
    menu = st.tabs(["🏠 홈 (점검장비 현황)", "📋 일일점검현황", "⚙️ 관리"])
    
    # 공통 데이터 로드
    date_str = st.session_state.target_date.strftime("%Y-%m-%d")
    stats = db_api.get_daily_stats(date_str)
    logs = db_api.get_daily_logs_summary(date_str)

    with menu[0]: # 1. 홈 (이미지 2 스타일)
        st.markdown(f"### 점검장비 현황: 총 {sum(s['completed'] for s in stats)}대 완료")
        if stats:
            for s in stats:
                st.markdown(f"""
                <div class="custom-card" style="display:flex; justify-content:space-between; align-items:center;">
                    <h2 style="margin:0; color:#122d43;">{s['type']}</h2>
                    <h1 style="margin:0; color:#122d43;">{s['completed']} <span style="font-size:18px;">대</span></h1>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("등록된 장비 데이터가 없습니다.")

    with menu[1]: # 2. 일일점검현황 (이미지 3 스타일)
        st.markdown("### 일일점검 리스트")
        if logs:
            # 장비별로 로그 그룹화
            grouped_logs = {}
            for l in logs:
                reg = l['registration_number']
                if reg not in grouped_logs:
                    # 안전한 딕셔너리 접근 방어 로직 (데이터 누락 방지)
                    eq_data = l.get('equipments') or {}
                    eq_type_data = eq_data.get('equipment_types') or {}
                    pt_data = l.get('partners') or {}
                    
                    grouped_logs[reg] = {
                        "type": eq_type_data.get('equipment_type', '알수없음'),
                        "model": eq_data.get('equipment_model', ''),
                        "partner": pt_data.get('partner_name', '알수없음'),
                        "status_counts": {"양호":0, "수리요":0, "불량":0, "기타":0},
                        "details": []
                    }
                
                # 🔥 KeyError 방어: 이상한 과거 데이터가 있으면 무조건 '기타'로 취급
                status_val = l.get('status', '기타')
                if status_val not in grouped_logs[reg]["status_counts"]:
                    status_val = "기타"
                
                grouped_logs[reg]["status_counts"][status_val] += 1
                grouped_logs[reg]["details"].append(l)

            # 리스트 출력 (클릭 시 펼쳐짐)
            for reg, data in grouped_logs.items():
                # 요약 상태 동그라미 생성
                dots = ""
                if data['status_counts']['불량'] > 0: dots = "🔴 불량발견"
                elif data['status_counts']['수리요'] > 0: dots = "🟡 수리필요"
                else: dots = "🟢 전항목 양호"

                with st.expander(f"🚜 {data['partner']} | {data['type']}({data['model']}) | {reg}  ➔ {dots}"):
                    for d in data['details']:
                        item_data = d.get('inspection_items') or {}
                        item_name = item_data.get('item_name', '알수없음')
                        note = f"({d.get('inspection_note')})" if d.get('inspection_note') else ""
                        st.write(f"- **{item_name}**: {d.get('status', '알수없음')} {note}")
        else:
            st.info("해당 날짜에 점검된 기록이 없습니다.")

    with menu[2]: # 3. 관리 탭
        st.markdown("### 시스템 관리")
        admin_tabs = st.tabs(["🏢 업체 관리", "📋 장비/체크리스트 관리", "🛠️ 장비 마스터"])
        
        with admin_tabs[0]: # 업체
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

        with admin_tabs[1]: # 체크리스트/종류 관리
            col_l, col_r = st.columns(2)
            with col_l:
                st.write("**[장비 종류 관리]**")
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
            with col_r:
                st.write("**[체크리스트 관리]**")
                t_map = {t['equipment_type']: t['equipment_type_id'] for t in types}
                if t_map:
                    sel_t = st.selectbox("수정할 장비 종류", options=list(t_map.keys()))
                    t_id = t_map[sel_t]
                    items = db_api.get_items_by_type(t_id)
                    with st.form("add_item_form", clear_on_submit=True):
                        i_n = st.text_input("새 항목명 (Enter)")
                        if st.form_submit_button("항목 추가"):
                            if i_n: db_api.add_inspection_item(t_id, i_n, "", len(items)+1); st.rerun()
                    for it in items:
                        c1, c2 = st.columns([0.7, 0.3])
                        c1.write(f"- {it['item_name']}")
                        if c2.button("제외", key=f"it_{it['item_id']}"):
                            db_api.delete_inspection_item(it['item_id']); st.rerun()

        with admin_tabs[2]: # 장비 마스터 (표 클릭 수정)
            all_eqs = db_api.get_all_equipments()
            df_display = pd.DataFrame([{"번호": eq['registration_number'], "종류": eq['equipment_types']['equipment_type'], "모델": eq['equipment_model'] or "-"} for eq in all_eqs])
            
            st.write("👇 **표에서 장비를 클릭하면 수정/삭제할 수 있습니다.**")
            event = st.dataframe(df_display, use_container_width=True, hide_index=True, selection_mode="single-row", on_select="rerun")
            
            if event.selection.rows:
                selected_idx = event.selection.rows[0]
                selected_reg = df_display.iloc[selected_idx]['번호']
                target_data = next(eq for eq in all_eqs if eq['registration_number'] == selected_reg)
                
                st.markdown(f'<div class="custom-card">', unsafe_allow_html=True)
                st.subheader(f"✏️ [{selected_reg}] 수정")
                with st.form("edit_eq_form"):
                    new_reg = st.text_input("장비 번호", value=target_data['registration_number'])
                    type_names = list(t_map.keys())
                    current_type = target_data['equipment_types']['equipment_type']
                    new_type = st.selectbox("장비 종류", options=type_names, index=type_names.index(current_type) if current_type in type_names else 0)
                    new_model = st.text_input("모델명", value=target_data['equipment_model'] or "")
                    
                    c1, c2 = st.columns(2)
                    if c1.form_submit_button("💾 정보 저장", type="primary", use_container_width=True):
                        db_api.update_equipment(selected_reg, new_reg, t_map[new_type], new_model)
                        st.success("수정 완료!"); st.rerun()
                    if c2.form_submit_button("🗑️ 장비 삭제", use_container_width=True):
                        success, msg = db_api.delete_equipment(selected_reg)
                        if success: st.rerun()
                        else: st.error(msg)
                st.markdown('</div>', unsafe_allow_html=True)

    # --- 엑셀 다운로드 플로팅 버튼 ---
    if stats and logs:
        df_stats = pd.DataFrame(stats)
        logs_formatted = []
        for l in logs:
            # 방어 로직 추가 (결측치에 의한 에러 방지)
            pt_name = l.get("partners", {}).get("partner_name", "") if l.get("partners") else ""
            eq_data = l.get("equipments") or {}
            eq_type_data = eq_data.get("equipment_types") or {}
            eq_name = eq_type_data.get("equipment_type", "")
            item_data = l.get("inspection_items") or {}
            item_name = item_data.get("item_name", "")
            
            logs_formatted.append({
                "점검시간": l.get("created_at", "")[:16].replace("T", " "),
                "장비번호": l.get("registration_number", ""),
                "점검업체": pt_name,
                "장비종류": eq_name,
                "점검항목": item_name,
                "상태": l.get("status", ""),
                "비고": l.get("inspection_note", "")
            })
        df_logs = pd.DataFrame(logs_formatted)
        
        st.markdown('<div class="floating-excel-btn">', unsafe_allow_html=True)
        st.download_button(
            label="📥 점검결과 Excel 다운로드",
            data=to_excel(df_stats, df_logs),
            file_name=f"안전점검결과_{date_str}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# [WORKER] 근로자 점검 화면 (어르신 맞춤형)
# ==========================================
else:
    st.title("🚜 장비 일일 안전 점검")
    st.write("---")
    
    if st.session_state.worker_step == "input":
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.subheader("1️⃣ 장비 번호를 입력해주세요")
        reg = st.text_input("장비 번호 (예: 01가1234)", placeholder="터치하여 입력하세요", label_visibility="collapsed").replace(" ", "")
        
        st.write("")
        st.subheader("2️⃣ 소속 업체를 선택해주세요")
        partners = db_api.get_partners(project_code)
        p_names = [p['partner_name'] for p in partners]
        sel_p = st.selectbox("업체 목록", options=["여기를 눌러 선택하세요"] + p_names, label_visibility="collapsed")
        
        st.write("") 
        if st.button("🚀 점검 시작하기", type="primary", use_container_width=True):
            if reg and sel_p != "여기를 눌러 선택하세요":
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
        st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.worker_step == "register":
        st.error("⚠️ 처음 오신 장비입니다. 최초 1회 등록이 필요합니다.")
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
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
        st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.worker_step == "checklist":
        eq = st.session_state.eq_data
        
        # 뒤로가기 버튼과 타이틀
        col1, col2 = st.columns([0.2, 0.8])
        if col1.button("⬅️ 뒤로"):
            st.session_state.worker_step = "input"
            st.rerun()
        col2.success(f"📋 {st.session_state.temp_reg} ({eq['equipment_types']['equipment_type']}) 점검표")
            
        items = db_api.get_items_by_type(eq['equipment_type_id'])
        ins_results = []

        for it in items:
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            st.write(f"### {it['item_number']}. {it['item_name']}")
            res = st.radio("상태", ["양호", "수리요", "불량", "기타"], key=f"r_{it['item_id']}", horizontal=True, label_visibility="collapsed")
            
            note, img_b64 = "", ""
            if res != "양호":
                st.warning("⚠️ 이상 발견: 사진과 내용을 남겨주세요.")
                cam = st.camera_input("📸 여기를 눌러 사진 촬영", key=f"cam_{it['item_id']}")
                if cam: img_b64 = resize_image_to_base64(cam)
                note = st.text_area("📝 조치 사항", key=f"n_{it['item_id']}", placeholder="어떤 문제가 있는지 적어주세요.")
            
            ins_results.append({"id": it['item_id'], "res": res, "note": note, "img": img_b64})
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.write("")
        if st.button("✅ 오늘 점검 모두 완료하고 제출하기", type="primary", use_container_width=True):
            for r in ins_results:
                db_api.create_inspection_log(project_code, st.session_state.temp_reg, st.session_state.temp_p_id, r['id'], r['res'], r['note'], r['img'], st.session_state.temp_p_name)
            st.session_state.worker_step = "complete"
            st.rerun()

    elif st.session_state.worker_step == "complete":
        st.markdown('<div class="custom-card" style="text-align:center; padding: 40px 20px;">', unsafe_allow_html=True)
        st.markdown("<h1 style='font-size: 50px;'>🎉</h1>", unsafe_allow_html=True)
        st.markdown("<h2>점검이 완료되었습니다.</h2>", unsafe_allow_html=True)
        st.info("오늘도 현장의 안전을 지켜주셔서 감사합니다.")
        
        st.write("")
        st.write("")
        if st.button("🔄 추가 장비 점검하기", type="primary", use_container_width=True):
            st.session_state.worker_step = "input"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
