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
# db_api.py (주요 수정 부분)

def get_items_by_type(type_id):
    """현재 '활성 상태(is_active=True)'인 항목만 가져와서 새 점검에 사용합니다."""
    return supabase.table("inspection_items") \
        .select("*") \
        .eq("equipment_type_id", type_id) \
        .eq("is_active", True) \
        .order("item_number") \
        .execute().data

def delete_inspection_item(item_id):
    """
    실제로 삭제하지 않고 '비활성화' 처리합니다.
    이렇게 하면 과거 inspection_logs에 있는 item_id 참조가 깨지지 않습니다.
    """
    try:
        supabase.table("inspection_items") \
            .update({"is_active": False, "modified_at": datetime.now().isoformat()}) \
            .eq("item_id", item_id) \
            .execute()
        return True, "항목이 성공적으로 제외되었습니다. (과거 기록은 보존됨)"
    except Exception as e:
        return False, f"오류 발생: {str(e)}"

def update_inspection_item(item_id, type_id, new_name, new_desc, new_num):
    """
    내용을 수정할 때 기존 것을 고치면 과거 기록의 이름도 바뀌어 버립니다.
    따라서 [기존 항목 비활성화] -> [새 항목 생성] 방식으로 처리하여 이력을 분리합니다.
    """
    # 1. 기존 항목 비활성화
    delete_inspection_item(item_id)
    # 2. 새 항목으로 등록 (이 시점부터 새로운 타임스탬프가 적용됨)
    return add_inspection_item(type_id, new_name, new_desc, new_num)

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
