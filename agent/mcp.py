import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.tools import ToolException, tool
from tools.llm_tool import call_llm
from typing import Dict,Any
from tools.pinecone_tool import search_menu_items_with_ids
from tools.amap_tool import check_delivery_range,PathInputModel
import os


def load_prompt_template(prompt_file_name)->str:
    """加载指定目录下的提示词文件"""
    try:
        #1.定位到当前文件的路径
        current_file_path = os.path.abspath(__file__)
        current_dir_dir = os.path.dirname(current_file_path)
        project_dir = os.path.dirname(current_dir_dir)
        #2.拼接提示词完整路径
        prompt_path = os.path.join(project_dir, 'prompt', f"{prompt_file_name}.txt")

        #3.读取指定路径文件下的文件
        with open(prompt_path,"r",encoding="utf-8") as f:
            return f.read().strip()

    except Exception as e:
        logging.error(f"无法加载指定文件{prompt_file_name}的提示词内容")
        return "无法加载到指定的提示词内容，请根据用户的问题，直接提供帮助"
@tool
def general_inquiry(query: str) -> str:
    """常规问题工具

    处理用户的一般性问题，包括但不限于：
    - 餐厅介绍和服务信息
    - 营业时间和联系方式
    - 优惠活动和会员服务
    - 其他非菜品相关的咨询

    Args: 
        query: 用户的询问内容
        context: 可选的上下文信息，用于提供更精准的回复

    Returns:
        str: 针对用户问题的智能回复

    Raises:
        ToolException: 当处理查询时发生错误
    """
    try:
        #1.加载常规问题的提示词
        prompt_template = load_prompt_template("general_inquiry")


        #2.调用LLM模型
        llm_response = call_llm(query,prompt_template)

        #3.组装自定义数据 再返回
        return llm_response
    except Exception as e:
        raise ToolException(f"常规问询失败{e}")

@tool
def menu_inquiry(query: str) -> Dict[str, Any]:
    """智能菜品咨询工具

    专门处理与菜品相关的所有查询，包括：
    - 菜品介绍和详细信息
    - 价格和营养信息
    - 菜品推荐和搭配建议
    - 过敏原和饮食限制相关问题
    - 菜品制作和特色介绍

    该工具会自动通过语义搜索查找最相关的菜品信息，然后基于这些信息回答用户问题。

    Args:
        query: 用户关于菜品的具体问题

    Returns:
        Dict[str, Any]: 包含推荐建议和菜品ID的字典
        {
            "recommendation": "基于菜品信息的推荐建议",
            "menu_ids": ["菜品ID1", "菜品ID2"]
        }

    Raises:
        ToolException: 当处理菜品查询时发生错误
    """
    try:
        # 1.加载菜品推荐问题的提示词
        prompt_template = load_prompt_template("menu_inquiry")

        # 2.上下文（向量数据库）
        #2.1利用文本嵌入模型
        similar_result = search_menu_items_with_ids(query)

        if similar_result and similar_result["contents"]:
            menu_contents_context = "\n".join([f" - {item}" for item in similar_result["contents"]])
            full_query = f"当前从向量数据库中检索到的菜品信息:\n{menu_contents_context}\n\n当前用户问题:\n{query}\n\n请基于以上检索到的菜品信息，回答用户提出的相关问题"
        else:
            full_query = f"暂无相关菜品信息:\n\n当前用户问题:\n{query}\n\n请基于一般的菜品知识信息，回答用户提出的相关问题"
            

        # 3.调用模型
        #3.1利用文本模型
        llm_response = call_llm(full_query, prompt_template)

        # 4.组装结构化返回
        return {
            "recommendation": llm_response,
            "menu_ids": (similar_result.get("ids") if isinstance(similar_result, dict) else []),
        }
    except Exception as e:
        raise ToolException(f"菜品咨询处理失败: {str(e)}")

@tool
def delivery_check_tool(address,travel_mode) -> str:
    """配送范围检查工具

    Args:
        address: 用户输入的配送地址
        travel_mode: 出行方式（1:步行, 2:骑行, 3:驾车）

    Returns:
        str: 配送查询结果描述
    """
        
    try:
        #1.调用配送范围查询函数
        result = check_delivery_range(address,travel_mode)

        mode_mapping = {
            "1": "步行",
            "2": "骑行",
            "3": "驾车",
        }

        #2.处理数据直接返回
        if result["status"] == "success":
                status_text = "✅ 可以配送" if result["in_range"] else "❌ 超出配送范围"

                response = f"""
            配送信息查询结果：
        
            配送地址：{result['formatted_address']}
            配送距离：{result['distance']}公里 ({mode_mapping.get(str(travel_mode), str(travel_mode))})
            配送状态：{status_text}
                        """.strip()

        else:
            response = f"❌ 配送查询失败：{result['message']}"

        return response
    
    except Exception as e:
        raise ToolException(f"配送范围检查失败{e}")

if __name__ == '__main__':
#     current_file_path = os.path.abspath(__file__)
#     print(repr(current_file_path)) #机器认识的内容

    # general_inquiry_result =  general_inquiry.invoke(input="请问你们餐厅的营业时间是什么时候？")
    # print(f"常规问题工具的结果：{general_inquiry_result}")

    # menu_inquiry_result = menu_inquiry.invoke({"query":"请给我推荐一些素食的菜品"})
    # print(f"菜品推荐问题工具的结果：{menu_inquiry_result}")

    delivery_check_result = delivery_check_tool.invoke({"address":"吴江市海悦花园","travel_mode":"3"})
    # delivery_check_result = delivery_check_tool(address = "吴江市海悦花园",travel_mode = 2)
    print(f"配送范围检查工具的结果：{delivery_check_result}")
