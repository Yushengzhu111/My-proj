from tools.amap_tool import PathInputModel,check_delivery_range

def get_menu():
    """获取菜品区域数据的展示"""
    from tools.db_tool import get_menu_items

    return get_menu_items()

def check_delivery_range(address: str, travel_mode: str = "2"):
    from tools.amap_tool import check_delivery_range as amap_check_delivery_range
    return amap_check_delivery_range(address, travel_mode)

def smart_chat_service(user_query: str):
    """对话服务"""
    from agent.assistant import chat_with_assistant
    return chat_with_assistant(user_query)

def smart_chat(user_query:str):
    """对话接口"""
    from agent.assistant import chat_with_assistant
    return chat_with_assistant(user_query)