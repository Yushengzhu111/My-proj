from dataclasses import dataclass
from json import JSONDecodeError
import logging
import os
from typing import Dict, Any, Literal, Optional, Union
import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry
from dotenv import load_dotenv
load_dotenv()

PathInputModel = Literal["1","2","3"]#外部用
PathModel = Literal["walking","electrobike","driving"]#内部用 


# 路径模式转换工具
class PathModeConverter:
    """路径模式转换工具类"""

    # 映射关系  外部输入的路径模式 -> 内部使用的路径模式
    MODE_MAPPING = {
        "1": "walking",
        "2": "electrobike",
        "3": "driving",
    }

    @classmethod
    def to_mode(cls, mode_input: Union[PathInputModel]) -> PathModel:
        """将输入的模式转换为内部使用的模式"""

        if mode_input in cls.MODE_MAPPING:
            return cls.MODE_MAPPING[mode_input]
        else:
            raise ValueError(f"不支持的路径模式: {mode_input}, 支持的模式: {list(cls.MODE_MAPPING.keys())}")


@dataclass  # 快速的对对象做一些赋值(重复工作少做)
class AmapConfig:
    AMAP_API_KEY: str = os.getenv("AMAP_API_KEY")
    MERCHANT_LONGITUDE: str = os.getenv("MERCHANT_LONGITUDE")
    MERCHANT_LATITUDE: str = os.getenv("MERCHANT_LATITUDE")
    DELIVERY_RADIUS: int = int(os.getenv("DELIVERY_RADIUS"))
    DEFAULT_PATH_MODE: str = os.getenv("DEFAULT_PATH_MODE")

    def __post_init__(self):
        """自动调用"""
        if self.AMAP_API_KEY is None:
            raise ValueError("AMAP_API_KEY不存在")

config = AmapConfig()

def create_session_with_retries():
    """创建带重试机制的requests会话"""
    #1.创建session对象
    session=requests.Session()

    #2.定义重试机制(规则)
    retry_strategy=Retry(
        total=3,#总共重试次数(不包含第一次请求
        backoff_factor=1,
        status_forcelist=[429,500,502,503,504,505]
    )

    #3.创建HttpAdapter(自定义Http的行为)
    adapter = HTTPAdapter(max_retries=retry_strategy)

    #5.将适配器挂载到session中
    session.mount('https://',adapter)
    session.mount('http://',adapter)

    return session
def safe_request(base_url: str, params: dict) -> Optional[Dict]:
    """安全的HTTP请求，处理重试和SSL降级"""
    try:
        session = create_session_with_retries()
        response = session.get(url=base_url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.SSLError as e:
        try:
            http_request_url = base_url.replace("https://", "http://")
            response = session.get(url=http_request_url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logging.error(f"HTTP协议的请求发送失败，原因是{e}")
            raise requests.exceptions.RequestException(f"HTTP协议的请求发送失败，原因是{e}")

    except requests.exceptions.RequestException as e:
        logging.error(f"HTTP协议的请求发送失败，原因是{e}")
        raise requests.exceptions.RequestException(f"HTTP协议的请求发送失败，原因是{e}")

    except JSONDecodeError as e:
        logging.error(f"解析响应结果失败，原因{e}")
        raise JSONDecodeError(f"反序列化失败，原因{e}", doc="", pos=0)


def geocode_address(address:str)->Dict[str,Any]:
    """通过地址获取经纬度
    Args:
        address (str): 地址
    Returns:
        Dict[str,Any]: 经纬度
    """
    try:
        #1.构建请求URL
        request_url = "https://restapi.amap.com/v3/geocode/geo"
        #2.构建请求param
        params = {
            "address":address,
            "key":os.getenv("AMAP_API_KEY")
        }
        #3.发送请求
        response = safe_request(request_url,params)
        #4.根据响应，解析结果
        #4.1失败
        if response['status']!='1':
            return {
                "success":False,
                "message":response['info']
            }
        #4.1成功#提取地址编码信息列表
        geocodes = response['geocodes'][0]
        return {
            "formatted_address":geocodes['formatted_address'],
            "location":geocodes['location'],
            "success":True
        }
        
    except Exception as e:
        logging.error(f"获取经纬度失败，原因是{e}")
        raise Exception(f"获取经纬度失败，原因是{e}")

def calculate_distance(origin_location: str, destination_location: str,
                       path_mode_input: PathInputModel or None) -> Dict[str, Any]:
    """
    不同的路径模式计算两个地点之间的距离和预计时间

    Args:
        origin_location: 起点经纬度
        destination_location: 终点经纬度
        path_mode_input: 路径模式, 1:步行, 2:骑行, 3:驾车

    Returns:
        Dict: 路径结果, 包含路径模式、距离、预计时间等

    """
    try:
        # 1.计算高德的API_KEY
        if config.AMAP_API_KEY is None:
            raise ValueError("AMAP_API_KEY 不存在")

        # 2.构建请求的URL
        path_endpoint = {
            "walking": "https://restapi.amap.com/v5/direction/walking",
            "electrobike": "https://restapi.amap.com/v5/direction/electrobike",
            "driving": "https://restapi.amap.com/v5/direction/driving"
        }

        # 3.构建param
        params = {
            "origin": origin_location,
            "destination": destination_location,
            "key": config.AMAP_API_KEY,
        }
        inner_mode = PathModeConverter.to_mode(path_mode_input)
        if inner_mode == "driving":
            params["show_fields"]="cost"

        # 4.发送请求获取响应
        response = safe_request(path_endpoint[inner_mode],params)

        # 5.解析响应结果
        if response.get('status') == '0':
            raise ValueError(f"高德API返回错误: {response.get('info')} ({response.get('infocode')})")
        path = response['route']["paths"][0]
        duration = path["duration"] if inner_mode == "electrobike" else path["cost"]["duration"]
        return{
            "distance":int(path["distance"]),
            "duration":duration,
            "status":"success"
        }
    except Exception as e:
        logging.error(f"调用高德地图进行路径规划失败,原因是{e}")
        raise e
        
def check_delivery_range(address: str, path_mode_input: PathInputModel =  None) -> Dict[str,Any]:
    """检查地址是否在配送范围内

    Args:
        address: 用户输入的地址

        path_mode_input: 路径模式，支持 "1"(walking), "2"(bicycling), "3"(driving)。如果为None则使用配置的默认模式

    Returns:
          包含检查结果的 Dict 对象
    """

    try:
        # 1. 使用传入的模式或默认模式
        if path_mode_input is None:
            path_mode_input = config.DEFAULT_PATH_MODE

        # 2. 地理编码获取经纬度
        geocode_result = geocode_address(address)
        if not geocode_result['success']:
           logging.error("地理位置编码失败")
           return {
               "status": "fail",
               "in_range": False,
               "distance": 0.0,
               "duration": 0,
               "formatted_address": address,
               "message": f"地理编码失败: {geocode_result.get('message', '未知错误')}"
           }

        # 3. 计算距离
        origin_location = f"{config.MERCHANT_LONGITUDE},{config.MERCHANT_LATITUDE}"
        distance_result = calculate_distance(origin_location, geocode_result['location'], path_mode_input)
        if distance_result['status']!="success":
            return distance_result

        # 4. 检查是否在配送范围内 并返回结果
        in_range = distance_result['distance'] <= config.DELIVERY_RADIUS
        distance_km = round(distance_result['distance'] / 1000, 2)
        return {
            "status": "success",
            "in_range":in_range,
            "distance":distance_km,
            "duration":int(distance_result['duration']),
            "formatted_address":geocode_result['formatted_address'],
            "message": (
                f"配送地址：{geocode_result['formatted_address']}\n"
                f"配送距离：{distance_km:.2f}公里\n"
                f"配送状态：{'在配送范围内' if in_range else '超出配送范围'}"
            )
        }
    except Exception as e:
       raise

if __name__ == '__main__':
    # print(geocode_address("苏州大学"))
    print(geocode_address("格林华城"))
    # print(calculate_distance("120.640536,31.304817","120.678199,31.181552","1"))
    pass
    test_address = "武汉大学" #  测试地址
    print("\n=== 测试不同路径模式 ===")
    # 测试步行模式 (1)
    print("\n1. 步行模式测试:")
    result1 = check_delivery_range(test_address, "1")
    minutes = result1['duration'] // 60
    seconds = result1['duration'] % 60
    print(f"步行模式距离: {result1['distance']}公里 时间: {result1['duration']}秒 ({minutes}分{round(seconds, 2)}秒)")
    print(f"是否在配送范围内: {result1['message']}")
    
    # 测试骑行模式 (2)
    print("\n2. 骑行模式测试:")
    result2 = check_delivery_range(test_address, "2")
    minutes = result2['duration'] // 60
    seconds = result2['duration'] % 60
    print(f"骑行模式距离: {result2['distance']}公里 时间: {result2['duration']}秒 ({minutes}分{round(seconds, 2)}秒)")
    print(f"是否在配送范围内: {result2['message']}")

    # 测试驾车模式 (3)
    print("\n3. 驾车模式测试:")
    result3 = check_delivery_range(test_address, "3")
    minutes = result3['duration'] // 60
    seconds = result3['duration'] % 60
    print(f"驾车模式距离: {result3['distance']}公里 时间: {result3['duration']}秒 ({minutes}分{round(seconds, 2)}秒)")
    print(f"是否在配送范围内: {result3['message']}")


