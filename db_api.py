import streamlit as st
from supabase import create_client, Client
from datetime import datetime

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# --- [관리자] 장비 마스터 조회 ---
def get_all_equipments():
    """전체 장비 리스트 조회 (종류명 포함)"""
    res = supabase.table("equipments").select("*, equipment_types(equipment_type)").execute()
    return res.data

# --- [관리자] 업체 관리 ---
def get_partners(project_code: str):
    return supabase.table("partners").select("*").eq("project_code", project_code).execute().data

def add_partner(project_code, partner_name):
    return supabase.table("partners").insert({"project_code": project_code, "partner_name": partner_name}).execute()

def delete_partner(partner_id):
    return supabase.table("partners").delete().eq("partner_id", partner_id).execute()

# --- [관리자] 체크리스트 관리 ---
def get_equipment_types():
    return supabase.table("equipment_types").select("*").execute().data

def get_items_by_type(type_id):
    return supabase.table("inspection_items").select("*").eq("equipment_type_id", type_id).order("item_number").execute().data

def add_inspection_item(type_id, name, desc, number):
    return supabase.table("inspection_items").insert({
        "equipment_type_id": type_id, "item_name": name, "item_description": desc, "item_number": number
    }).execute()

def delete_inspection_item(item_id):
    return supabase.table("inspection_items").delete().eq("item_id", item_id).execute()

# --- [공통] 통계 및 점검 로직 ---
def get_daily_stats(target_date):
    all_types = supabase.table("equipment_types").select("equipment_type_id, equipment_type").execute().data
    all_eqs = supabase.table("equipments").select("registration_number, equipment_type_id").execute().data
    logs = supabase.table("inspection_logs").select("registration_number") \
        .filter("created_at", "gte", f"{target_date}T00:00:00") \
        .filter("created_at", "lte", f"{target_date}T23:59:59").execute().data
    completed_regs = set(l['registration_number'] for l in logs)
    stats = []
    for t in all_types:
        t_id = t['equipment_type_id']
        type_eqs = [e for e in all_eqs if e['equipment_type_id'] == t_id]
        done = len([e for e in type_eqs if e['registration_number'] in completed_regs])
        stats.append({"type": t['equipment_type'], "total": len(type_eqs), "completed": done})
    return stats

def check_equipment_exists(reg):
    res = supabase.table("equipments").select("*, equipment_types(*)").eq("registration_number", reg).execute()
    return res.data[0] if res.data else None

def create_equipment(reg, t_id, model):
    return supabase.table("equipments").insert({"registration_number": reg, "equipment_type_id": t_id, "equipment_model": model}).execute()

def create_inspection_log(project_code, reg_number, partner_id, item_id, status, note, photo, inspector):
    data = {
        "project_code": project_code, "registration_number": reg_number, "partner_id": partner_id,
        "item_id": item_id, "status": status, "inspection_note": note, "inspection_photo": photo, "inspector": inspector
    }
    return supabase.table("inspection_logs").insert(data).execute()
