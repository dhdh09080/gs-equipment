import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# ==========================================
# [신규: 업체 관리 기능]
# ==========================================
def get_partners(project_code: str):
    """해당 현장의 업체 목록 조회"""
    res = supabase.table("partners").select("*").eq("project_code", project_code).execute()
    return res.data

def add_partner(project_code, partner_name):
    """신규 업체 등록"""
    data = {"project_code": project_code, "partner_name": partner_name}
    return supabase.table("partners").insert(data).execute()

def delete_partner(partner_id):
    """업체 삭제"""
    return supabase.table("partners").delete().eq("partner_id", partner_id).execute()

# ==========================================
# [기존 기능 유지]
# ==========================================
def get_dashboard_data():
    return supabase.table("dashboard_stats").select("*").execute().data

def get_all_equipments():
    return supabase.table("equipments").select("*, equipment_types(equipment_type)").execute().data

def get_equipment_types():
    return supabase.table("equipment_types").select("*").execute().data

def get_items_by_type(type_id):
    return supabase.table("inspection_items").select("*").eq("equipment_type_id", type_id).order("item_number").execute().data

def add_inspection_item(type_id, name, desc, number):
    data = {"equipment_type_id": type_id, "item_name": name, "item_description": desc, "item_number": number}
    return supabase.table("inspection_items").insert(data).execute()

def delete_inspection_item(item_id):
    return supabase.table("inspection_items").delete().eq("item_id", item_id).execute()

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
