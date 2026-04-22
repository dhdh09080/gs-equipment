# ... (앞선 설정 및 로그인 로직 동일)

if st.session_state.role == "Admin":
    menu = st.tabs(["📊 일일 이행 현황", "🏢 업체 관리", "📋 체크리스트", "🚜 장비 마스터"])
    
    with menu[0]: # 일일 이행 현황
        st.header("📅 현장 점검 이행률")
        
        # 날짜 선택기 (기본값 오늘)
        selected_date = st.date_input("조회 날짜 선택", value=datetime.now().date())
        
        stats = db_api.get_daily_stats(selected_date.strftime("%Y-%m-%d"))
        
        if stats:
            # 메트릭 카드로 요약 표시
            cols = st.columns(len(stats))
            for i, s in enumerate(stats):
                percentage = (s['completed'] / s['total'] * 100) if s['total'] > 0 else 0
                cols[i].metric(
                    label=s['type'], 
                    value=f"{s['completed']} / {s['total']}", 
                    delta=f"{percentage:.1f}% 완료",
                    delta_color="normal" if percentage == 100 else "inverse"
                )
                # 시각적인 프로그레스 바 추가
                st.write(f"**{s['type']} 이행도**")
                st.progress(percentage / 100)
        else:
            st.info("해당 날짜의 데이터가 없습니다.")

        st.divider()
        st.subheader("미실시 장비 리스트 (추가 기능 예정)")
        # 여기서 해당 날짜에 기록이 없는 장비 번호만 필터링해서 보여줄 수도 있습니다.

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
