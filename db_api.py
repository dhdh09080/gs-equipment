import streamlit as st
from supabase import create_client, Client

# ==========================================
# Supabase 초기화 (Streamlit Secrets 사용)
# .streamlit/secrets.toml 파일에 아래 항목을 추가하세요.
# SUPABASE_URL = "https://[YOUR_PROJECT].supabase.co"
# SUPABASE_KEY = "[YOUR_ANON_KEY]"
# ==========================================
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# ------------------------------------------
# 1. 장비 존재 여부 확인
# ------------------------------------------
def check_equipment_exists(registration_number: str) -> bool:
    response = supabase.table("equipments").select("registration_number").eq("registration_number", registration_number).execute()
    return len(response.data) > 0

# ------------------------------------------
# 2. 장비 등록
# ------------------------------------------
def create_equipment(reg_number: str, type_id: int, model: str):
    data = {
        "registration_number": reg_number,
        "equipment_type_id": type_id,
        "equipment_model": model
    }
    response = supabase.table("equipments").insert(data).execute()
    return response.data

# ------------------------------------------
# 3. 장비 정보 상세 조회
# ------------------------------------------
def get_equipment_detail(registration_number: str):
    response = supabase.table("equipments").select("*").eq("registration_number", registration_number).execute()
    return response.data[0] if response.data else None

# ------------------------------------------
# 4. 장비 수정
# ------------------------------------------
def update_equipment(original_reg_number: str, new_reg_number: str, type_id: int, model: str):
    data = {
        "registration_number": new_reg_number,
        "equipment_type_id": type_id,
        "equipment_model": model
    }
    response = supabase.table("equipments").update(data).eq("registration_number", original_reg_number).execute()
    return response.data

# ------------------------------------------
# 5. 장비 종류 목록 조회
# ------------------------------------------
def get_equipment_types():
    response = supabase.table("equipment_types").select("*").execute()
    return response.data

# ------------------------------------------
# 6. 업체 목록 조회 (프로젝트 코드 기준)
# ------------------------------------------
def get_partners(project_code: str):
    response = supabase.table("partners").select("*").eq("project_code", project_code).execute()
    return response.data

# ------------------------------------------
# 7. 신규 업체 등록
# ------------------------------------------
def create_partner(project_code: str, partner_name: str):
    data = {
        "project_code": project_code,
        "partner_name": partner_name
    }
    response = supabase.table("partners").insert(data).execute()
    return response.data

# ------------------------------------------
# 8. 점검 항목 조회
# ------------------------------------------
def get_inspection_items(inspection_type_id: int = 1):
    response = supabase.table("inspection_items").select("*").eq("inspection_type_id", inspection_type_id).order("item_number").execute()
    return response.data

# ------------------------------------------
# 9. 기존 점검 기록 조회
# ------------------------------------------
def get_existing_inspection_logs(project_code: str, registration_number: str):
    response = supabase.table("inspection_logs").select("*").eq("project_code", project_code).eq("registration_number", registration_number).execute()
    return response.data

# ------------------------------------------
# 10. 점검 기록 유무 확인 (존재 여부만 빠르게 체크)
# ------------------------------------------
def check_inspection_log_exists(registration_number: str) -> bool:
    response = supabase.table("inspection_logs").select("log_id").eq("registration_number", registration_number).limit(1).execute()
    return len(response.data) > 0
