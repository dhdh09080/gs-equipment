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
# [1] 관리자 대시보드 및 통계
# ==========================================
def get_daily_stats(target_date):
    """(홈) 장비 종류별 점검 완료/미완료 상세 통계"""
    all_types = supabase.table("equipment_types").select("equipment_type_id, equipment_type").execute().data
    all_eqs = supabase.table("equipments").select("registration_number, equipment_type_id, equipment_model").execute().data
    
    # 점검 로그에서 파트너 정보까지 함께 가져옵니다.
    logs = supabase.table("inspection_logs") \
        .select("registration_number, partners(partner_name)") \
        .filter("created_at", "gte", f"{target_date}T00:00:00") \
        .filter("created_at", "lte", f"{target_date}T23:59:59") \
        .execute().data
    
    # 점검을 완료한 장비 번호와 해당 업체를 매핑
    completed_info = {}
    for l in logs:
        reg = l['registration_number']
        pt_data = l.get('partners') or {}
        partner_name = pt_data.get('partner_name', '알수없음')
        completed_info[reg] = partner_name

    stats = []
    for t in all_types:
        t_id = t['equipment_type_id']
        # 해당 종류에 속하는 모든 등록 장비
        type_eqs = [e for e in all_eqs if e['equipment_type_id'] == t_id]
        
        completed_list = []
        pending_list = []
        
        for e in type_eqs:
            reg = e['registration_number']
            model = e['equipment_model'] or ""
            if reg in completed_info:
                completed_list.append({"reg": reg, "model": model, "partner": completed_info[reg]})
            else:
                pending_list.append({"reg": reg, "model": model, "partner": "미점검 (업체미정)"})
                
        if type_eqs: # 등록된 장비가 1대라도 있는 종류만 통계에 포함
            stats.append({
                "type": t['equipment_type'],
                "total": len(type_eqs),
                "completed": len(completed_list),
                "completed_list": completed_list,
                "pending_list": pending_list
            })
    return stats

def get_daily_logs_summary(target_date):
    """(일일점검현황 탭) 그날 점검한 장비 리스트와 상태 요약"""
    res = supabase.table("inspection_logs") \
        .select("created_at, registration_number, inspector, status, inspection_note, partners(partner_name), equipments(equipment_types(equipment_type), equipment_model), inspection_items(item_name)") \
        .filter("created_at", "gte", f"{target_date}T00:00:00") \
        .filter("created_at", "lte", f"{target_date}T23:59:59") \
        .order("created_at", desc=True) \
        .execute()
    return res.data

def get_daily_logs_for_excel(target_date):
    return get_daily_logs_summary(target_date)

def get_all_equipments():
    return supabase.table("equipments").select("*, equipment_types(equipment_type)").execute().data

def update_equipment(original_reg, new_reg, type_id, model):
    data = {"registration_number": new_reg, "equipment_type_id": type_id, "equipment_model": model}
    return supabase.table("equipments").update(data).eq("registration_number", original_reg).execute()

def delete_equipment(reg_number):
    try:
        supabase.table("equipments").delete().eq("registration_number", reg_number).execute()
        return True, "삭제 성공"
    except Exception as e:
        return False, "점검 기록이 남아있는 장비는 삭제할 수 없습니다. (데이터 보호)"

# ==========================================
# [2] 업체 관리
# ==========================================
def get_partners(project_code):
    return supabase.table("partners").select("*").eq("project_code", project_code).execute().data

def add_partner(project_code, partner_name):
    return supabase.table("partners").insert({"project_code": project_code, "partner_name": partner_name}).execute()

def delete_partner(partner_id):
    return supabase.table("partners").delete().eq("partner_id", partner_id).execute()

# ==========================================
# [3] 체크리스트 & 장비 종류 관리
# ==========================================
def get_equipment_types():
    return supabase.table("equipment_types").select("*").order("equipment_type_id").execute().data

def add_equipment_type(type_name):
    return supabase.table("equipment_types").insert({"equipment_type": type_name}).execute()

def delete_equipment_type(type_id):
    try:
        supabase.table("equipment_types").delete().eq("equipment_type_id", type_id).execute()
        return True, "장비 종류가 삭제되었습니다."
    except Exception as e:
        return False, "이 장비 종류에 속한 장비나 항목이 있어 삭제가 불가능합니다."

def get_items_by_type(type_id):
    return supabase.table("inspection_items").select("*").eq("equipment_type_id", type_id).eq("is_active", True).order("item_number").execute().data

def add_inspection_item(type_id, name, desc, number):
    data = {"equipment_type_id": type_id, "item_name": name, "item_description": desc, "item_number": number, "is_active": True}
    return supabase.table("inspection_items").insert(data).execute()

def delete_inspection_item(item_id):
    try:
        supabase.table("inspection_items").update({"is_active": False, "modified_at": datetime.now().isoformat()}).eq("item_id", item_id).execute()
        return True, "항목이 제외되었습니다."
    except Exception as e:
        return False, f"오류 발생: {str(e)}"

# ==========================================
# [4] 근로자 점검 및 장비 등록
# ==========================================
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
