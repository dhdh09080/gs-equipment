import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# --- 관리자 대시보드용 ---
def get_dashboard_data():
    return supabase.table("dashboard_stats").select("*").execute().data

def get_all_equipments():
    return supabase.table("equipments").select("*, equipment_types(equipment_type)").execute().data

# --- 체크리스트 관리용 ---
def get_items_by_type(type_id):
    return supabase.table("inspection_items").select("*").eq("equipment_type_id", type_id).order("item_number").execute().data

def add_inspection_item(type_id, name, desc, number):
    data = {"equipment_type_id": type_id, "item_name": name, "item_description": desc, "item_number": number}
    return supabase.table("inspection_items").insert(data).execute()

def delete_inspection_item(item_id):
    return supabase.table("inspection_items").delete().eq("item_id", item_id).execute()

# --- 기존 함수 유지 및 보강 ---
def check_equipment_exists(reg_number):
    res = supabase.table("equipments").select("*, equipment_types(*)").eq("registration_number", reg_number).execute()
    return res.data[0] if res.data else None
