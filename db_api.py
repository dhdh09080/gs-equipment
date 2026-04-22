import streamlit as st
from supabase import create_client, Client
from datetime import datetime

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# ==========================================
# [신규: 날짜별 이행률 대시보드 함수]
# ==========================================
def get_daily_stats(target_date):
    """
    특정 날짜의 장비 종류별 점검 이행 현황을 가져옵니다.
    결과: [{'type': '덤프트럭', 'total': 10, 'completed': 8}, ...]
    """
    # 1. 전체 장비 종류 및 종류별 등록 대수 조회
    all_types = supabase.table("equipment_types").select("equipment_type_id, equipment_type").execute().data
    all_eqs = supabase.table("equipments").select("registration_number, equipment_type_id").execute().data
    
    # 2. 해당 날짜에 점검을 완료한 장비 목록 (중복 제거)
    # created_at::date 필터 사용
    logs = supabase.table("inspection_logs") \
        .select("registration_number") \
        .filter("created_at", "gte", f"{target_date}T00:00:00") \
        .filter("created_at", "lte", f"{target_date}T23:59:59") \
        .execute().data
    
    completed_regs = set(l['registration_number'] for l in logs)
    
    stats = []
    for t in all_types:
        t_id = t['equipment_type_id']
        # 해당 종류에 속하는 전체 장비들
        type_eqs = [e for e in all_eqs if e['equipment_type_id'] == t_id]
        total_count = len(type_eqs)
        
        # 그 중 오늘 점검 완료한 장비들
        done_count = len([e for e in type_eqs if e['registration_number'] in completed_regs])
        
        stats.append({
            "type": t['equipment_type'],
            "total": total_count,
            "completed": done_count
        })
    return stats

# 기존 업체/체크리스트/장비 등록 함수들은 그대로 유지합니다...
