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

# ... (근로자 화면 로직 동일)
