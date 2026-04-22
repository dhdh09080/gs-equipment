import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# ==========================================
# [관리자 대시보드용]
# ==========================================
def get_dashboard_data():
    """장비별 등록 및 점검 통계 조회"""
    return supabase.table("dashboard_stats").select("*").execute().data

def get_all_equipments():
    """전체 장비 리스트 조회"""
    return supabase.table("equipments").select("*, equipment_types(equipment_type)").execute().data

# ==========================================
# [장비 및 체크리스트 관리용]
# ==========================================
def get_equipment_types():
    """장비 종류(굴삭기, 크레인 등) 목록 가져오기"""
    res = supabase.table("equipment_types").select("*").execute()
    return res.data

def get_items_by_type(type_id):
    """특정 장비 종류의 점검 항목 목록 조회"""
    return supabase.table("inspection_items").select("*").eq("equipment_type_id", type_id).order("item_number").execute().data

def add_inspection_item(type_id, name, desc, number):
    """새 점검 항목 추가"""
    data = {
        "equipment_type_id": type_id, 
        "item_name": name, 
        "item_description": desc, 
        "item_number": number
    }
    return supabase.table("inspection_items").insert(data).execute()

def delete_inspection_item(item_id):
    """점검 항목 삭제"""
    return supabase.table("inspection_items").delete().eq("item_id", item_id).execute()

# ==========================================
# [현장 장비 등록 및 점검 로직]
# ==========================================
def check_equipment_exists(reg_number):
    """장비 존재 여부 확인"""
    res = supabase.table("equipments").select("*, equipment_types(*)").eq("registration_number", reg_number).execute()
    return res.data[0] if res.data else None

def create_equipment(reg_number, type_id, model):
    """현장에서 신규 장비 바로 등록"""
    data = {
        "registration_number": reg_number, 
        "equipment_type_id": type_id, 
        "equipment_model": model
    }
    return supabase.table("equipments").insert(data).execute()

def get_partners(project_code: str):
    """특정 프로젝트의 협력업체 목록 조회"""
    response = supabase.table("partners").select("*").eq("project_code", project_code).execute()
    return response.data

def create_inspection_log(project_code, reg_number, partner_id, item_id, status, note, inspector):
    """최종 점검 결과 저장"""
    data = {
        "project_code": project_code,
        "registration_number": reg_number,
        "partner_id": partner_id,
        "item_id": item_id,
        "status": status,
        "inspection_note": note,
        "inspector": inspector
    }
    response = supabase.table("inspection_logs").insert(data).execute()
    return response.data
