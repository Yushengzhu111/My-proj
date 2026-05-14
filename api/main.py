from pydantic import BaseModel
from typing import List,Optional
from fastapi import FastAPI, HTTPException
from tools.amap_tool import PathInputModel
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="智能点餐助手的API接口",description="智能点餐应用主要暴露三个接口分别为智能对话接口、配送查询接口、菜品列表接口")

@app.get("/")
def hello_world():
    """测试项目根路径访问是否可用"""
    return {"hello":"world"}

@app.get("/healthy")
def healthy():
    """测试项目请求路径是否可用"""
    return{"message":"请求路径访问健康"}
    
#定义数据模型
#菜品列表展示
class MenuListResponse(BaseModel):
    """菜品列表响应"""
    success: bool
    menu_items: List[dict] # 菜品列表
    count: int # 菜品数
    message: str # 响应消息提示

class DeliveryResponse(BaseModel):
    """配送查询响应"""
    success: bool  # 成功(True) or 失败的标识（False）
    in_range: bool #  配送是否在配送范围内(True False)
    distance: float # 配送距离(公里 km)
    formatted_address: str # 格式化地址
    duration:float # 配送时间（秒）
    message: str  # (前端要展示的配送完整消息内容)
    travel_mode: PathInputModel # 配送模式 (1:步行 2:骑电动车 3:驾车)
    input_address: str # 输入原始内容

class ChatResponse(BaseModel):
    """智能对话响应"""
    success: bool # 成功失败表示
    query: str # 原始查询内容
    response: Optional[str] = None # 响应内容
    recommendation: Optional[str] = None # 推荐内容
    menu_ids: Optional[List[str]] = None # 推荐的菜品id

class DeliveryRequest(BaseModel):
    """配送查询请求"""
    address: str
    travel_mode: PathInputModel = "2"  # 1=步行, 2=骑电动车, 3=驾车

class ChatRequest(BaseModel):
    """智能对话请求"""
    query: str

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    智能对话接口
    
    接收用户问题，返回智能助手回复
    """
    try:
        # 调用智能对话服务
        from service.diancan_service import smart_chat
        result = smart_chat(request.query)
        
        # 处理不同类型的返回值
        if isinstance(result, dict) and "recommendation" in result and "menu_ids" in result:
            # 菜品推荐返回
            return ChatResponse(
                success=True,
                query=request.query,
                recommendation=result.get("recommendation"),
                menu_ids=result.get("menu_ids"),
            )
        else:
            # 普通文本回复
            return ChatResponse(
                success=True,
                query=request.query,
                response=str(result),
            )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"智能对话服务失败: {str(e)}")

@app.get("/menu/list", response_model=MenuListResponse)
async def menu_list_endpoint():
    """菜品列表区域展示"""
    #调用service
    from service.diancan_service import get_menu
    #调用方法
    menu_items = get_menu()
    #封装结果返回
    if not menu_items:
        return MenuListResponse(
            success=False,
            menu_items=[],
            count=0,
            message="暂无菜品列表可用"
        )
    return MenuListResponse(
        success=True,
        menu_items=menu_items,
        count=len(menu_items),
        message=f"成功查询到{len(menu_items)}道菜品"
    )

@app.post("/delivery", response_model=DeliveryResponse)

async def delivery_endpoint(request: DeliveryRequest):
    """
    配送查询接口
    
    检查指定地址是否在配送范围内
    """
    try:
        from service.diancan_service import check_delivery_range

        check_delivery_range_response = check_delivery_range(request.address,request.travel_mode)

        if check_delivery_range_response['status'] == "fail":
            return DeliveryResponse(
                success=False,
                in_range=False,
                distance=0.0,
                formatted_address=request.address,
                duration=0.0,
                message="配送查询失败",
                travel_mode=request.travel_mode,
                input_address=request.address
            )
        return DeliveryResponse(
                success=True,
                in_range=check_delivery_range_response['in_range'],
                distance=check_delivery_range_response['distance'],
                formatted_address=check_delivery_range_response['formatted_address'],
                duration=check_delivery_range_response['duration'],
                message = check_delivery_range_response['message'],
                travel_mode=request.travel_mode,
                input_address=request.address
            )
    except Exception as e:
        logger.error(f"配送范围查询失败：{e}")
        return DeliveryResponse(
            success=False,
            in_range=False,
            distance=0.0,
            formatted_address=request.address,
            duration=0.0,
            message=f"配送范围查询失败: {e}",
            travel_mode=request.travel_mode,
            input_address=request.address
        )