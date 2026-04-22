import streamlit as st
from supabase import create_client, Client
from datetime import datetime

# Supabase 연결 초기화
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# ==========================================
# [1] 관리자 대시보드 및 통계 함수
# ==========================================
def get_daily_stats(target_date):
    """특정 날짜의 장비 종류별 점검 이행 현황 계산"""
    all_types = supabase.table("equipment_types").select("equipment_type_id, equipment_type").execute().data
    all_eqs = supabase.table("equipments").select("registration_number, equipment_type_id").execute().data
    
    # 해당 날짜(00:00~23:59) 사이의 점검 로그 조회
    logs = supabase.table("inspection_logs") \
        .select("registration_number") \
        .filter("created_at", "gte", f"{target_date}T00:00:00") \
        .filter("created_at", "lte", f"{target_date}T23:59:59") \
        .execute().data
    
    completed_regs = set(l['registration_number'] for l in logs)
    
    stats = []
    for t in all_types:
        t_id = t['equipment_type_id']
        type_eqs = [e for e in all_eqs if e['equipment_type_id'] == t_id]
        total = len(type_eqs)
        done = len([e for e in type_eqs if e['registration_number'] in completed_regs])
        stats.append({"type": t['equipment_type'], "total": total, "completed": done})
    return stats

def get_all_equipments():
    return supabase.table("equipments").select("*, equipment_types(equipment_type)").execute().data

# ==========================================
# [2] 업체(Partner) 관리 함수
# ==========================================
def get_partners(project_code: str):
    res = supabase.table("partners").select("*").eq("project_code", project_code).execute()
    return res.data

def add_partner(project_code, partner_name):
    return supabase.table("partners").insert({"project_code": project_code, "partner_name": partner_name}).execute()

def delete_partner(partner_id):
    return supabase.table("partners").delete().eq("partner_id", partner_id).execute()

# ==========================================
# [3] 장비 및 체크리스트 관리 함수
# ==========================================
def get_equipment_types():
    return supabase.table("equipment_types").select("*").execute().data

def get_items_by_type(type_id):
    return supabase.table("inspection_items").select("*").eq("equipment_type_id", type_id).order("item_number").execute().data

def add_inspection_item(type_id, name, desc, number):
    data = {"equipment_type_id": type_id, "item_name": name, "item_description": desc, "item_number": number}
    return supabase.table("inspection_items").insert(data).execute()

def delete_inspection_item(item_id):
    return supabase.table("inspection_items").delete().eq("item_id", item_id).execute()

# ==========================================
# [4] 근로자 점검 실행 함수
# ==========================================
def check_equipment_exists(reg_number):
    res = supabase.table("equipments").select("*, equipment_types(*)").eq("registration_number", reg_number).execute()
    return res.data[0] if res.data else None

def create_equipment(reg_number, type_id, model):
    data = {"registration_number": reg_number, "equipment_type_id": type_id, "equipment_model": model}
    return supabase.table("equipments").insert(data).execute()

def create_inspection_log(project_code, reg_number, partner_id, item_id, status, note, inspector):
    data = {
        "project_code": project_code, "registration_number": reg_number, "partner_id": partner_id,
        "item_id": item_id, "status": status, "inspection_note": note, "inspector": inspector
    }
    return supabase.table("inspection_logs").insert(data).execute()
