"""
数据库查询工具模块

该模块提供MySQL数据库连接和查询功能，
专门用于查询menu数据库中的menu_items表的全部信息
"""
from ast import List
import os
from pickle import LIST
from typing import Dict,Any,List
import mysql.connector
import logging
logging.basicConfig(level=logging.INFO)
logger=logging.getLogger(__name__)
from dotenv import load_dotenv
load_dotenv()


class DatasBaseConnection:
    def __init__(self):
        """初始化数据库配置信息"""
        self.host = os.getenv("MYSQL_HOST","localhost")
        self.port = os.getenv("MYSQL_PORT","3306")
        self.user = os.getenv("MYSQL_USER_NAME","root")
        self.password = os.getenv("MYSQL_USER_PASSWORD","123456")
        self.db_name = os.getenv("MYSQL_DB_NAME","menu")

        #数据库操作的两个对象
        self.connection = None#连接对象
        self.cursor = None#真正执行SQL的对象
    
    def initialize_connection(self)->bool:
        """初始化数据库连接对象和游标对象"""
        try:
            #初始化连接对象
            self.connection=mysql.connector.connect(user=self.user,
                                                    password=self.password,
                                                    host=self.host,
                                                    port=self.port,
                                                    database=self.db_name,
                                                    charset="utf8"
                                                    )
            #初始化游标对象
            self.cursor=self.connection.cursor(dictionary=True)#执行SQL语句。获取结果

            logger.info(f"数据库{self.db_name}连接初始化成功")
            return True
        except mysql.connector.Error as e:
            logger.error(f"数据库{self.db_name}连接初始化失败:{e}")
            return False

    def disconnect_connection(self)->bool:
        """关闭数据库游标和连接资源"""
        try:
            #1.关闭游标对象
            if self.cursor:
                self.cursor.close()#游标对象关闭
                self.cursor=None#内部置为空
            #2.关闭连接
            if self.connection and self.connection.is_connected():
                self.connection.close()#连接对象关闭
                self.connection=None#内部置为空
            logger.info("关闭数据库连接成功")
            return True
        except mysql.connector.Error as e:
            logger.error(f"关闭数据库资源失败：{e}")
            return False

    def __enter__(self):
        """
        上下文管理器对象入口
        调用时机:实例化完，在with代码块执行前
        返回值:一定是一个上下文管理器对象(自己:self)
        """
        if self.initialize_connection():
            logger.info("数据库初始化成功")
            return self
        else:
            raise Exception

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        上下文管理器对象出口
        调用时机:在with代码块执行之后
        exc_type:异常类型()
        exc_val:异常类型对应的具体说明
        exc_tb:记录哪个模块 哪一行代码出现(栈的跟踪)
        """
        self.disconnect_connection()

        if exc_type:
            logger.error(f"执行with代码块期间出现了异常:{exc_val}")

        
        return False #默认返回的是False.False：只是告诉有异常，不会处理会继续向上抛出。True:不会告诉有异常，而且直接处理了，不会向上抛出


def get_all_menu_items()->str:
    """作用：查询menu_items中所有的菜品信息，并且对每一条菜品信息用\n连接，最终形成一个大字符串（向量化）
    return:str
    """

    try:
        with DatasBaseConnection() as db: 
            #1.定义SQL语句
            query_sql = """
                SELECT 
                    id, dish_name, price, description, category, 
                    spice_level, flavor, main_ingredients, cooking_method, 
                    is_vegetarian, allergens, is_available
                FROM menu_items 
                WHERE is_available = 1
                ORDER BY category, dish_name
            """
            #2.执行SQL语句
            db.cursor.execute(query_sql)
            menu_items = db.cursor.fetchall()
            #3.处理结果
            if not menu_items:
                logger.info("当前没有找到任何菜品信息")#打印日志
                return "当前没有找到任何菜品信息"
            
            menu_strings = []

            for item in menu_items:
                # 3.1 处理字符串类型的值
                # 菜品描述处理
                description_text = item.get('description', '') if item.get('description', '').strip() else "未知描述"
                # 过敏原处理
                allergens_text = item.get('allergens', '') if item.get('allergens', '').strip() else "无过敏原"
                # 处理主要食材
                main_ingredients_text = item.get('main_ingredients', '') if item.get('main_ingredients',
                                                                                     '').strip() else "未知食材"

                # 3.2 处理数字类型的值
                # 辣度转换
                spice_level = {"0": "不辣", "1": "微辣", "2": "中辣", "3": "重辣"}
                spice_text = spice_level.get(item["spice_level"], "未知辣度")

                # 3.3 处理布尔类型的值
                #  是否素食转换
                vegetarian_text = "是" if item['is_vegetarian'] else "否"

                menu_string = f"菜品ID:{item['id']}|菜品名称:{item['dish_name']}|价格:¥{item['price']:.2f}|菜品描述:{description_text}|分类:{item['category']}|辣度:{spice_text}|口味:{item['flavor']}|主要食材:{main_ingredients_text}|烹饪方法:{item['cooking_method']}|素食:{vegetarian_text}|过敏原:{allergens_text}"
                menu_strings.append(menu_string)

            #4.返回处理后的结果
            all_menu_info = "\n".join(menu_strings)
            logger.info(f"已成功查询到菜品信息，菜品数量: {len(menu_strings)}个")
            return all_menu_info

    except Exception as e:
        logger.error(f"查询所有菜品信息字符串结果失败{e}")
        return "查询菜品信息失败"

def get_menu_items()->List[Dict[str, Any]]:
    """前端菜品区域展示
    :return:字典列表(菜品列表)
    """

    try:
        with DatasBaseConnection() as db:
            #1.定义SQL语句
            query_sql = """
                SELECT 
                    id, dish_name, price, description, category, 
                    spice_level, flavor, main_ingredients, cooking_method, 
                    is_vegetarian, allergens, is_available
                FROM menu_items 
                WHERE is_available = 1
                ORDER BY category, dish_name
            """
            #2.执行SQL语句
            db.cursor.execute(query_sql)
            #3.获取结果
            menu_items_result = db.cursor.fetchall()
            #4.处理结果并返回
            if not menu_items_result:
                logger.error("暂无可用菜品信息")
                return []
            menu_items = []
            for item in menu_items_result:
                # 辣度等级转换
                spice_levels = {0: "不辣", 1: "微辣", 2: "中辣", 3: "重辣"}
                spice_text = spice_levels.get(item['spice_level'], "未知")

                # 处理数据
                processed_item = {
                    "id": item['id'],
                    "dish_name": item['dish_name'],
                    "price": float(item['price']),
                    "formatted_price": f"¥{item['price']:.2f}",
                    "description": item['description'] or "暂无描述",
                    "category": item['category'],
                    "spice_level": item['spice_level'],
                    "spice_text": spice_text,
                    "flavor": item['flavor'] or "暂无口味",
                    "main_ingredients": item['main_ingredients'] or "暂无主要食材",
                    "cooking_method": item['cooking_method'] or "暂无烹饪方法",
                    "is_vegetarian": bool(item['is_vegetarian']),
                    "vegetarian_text": "是" if item['is_vegetarian'] else "否",
                    "allergens": item['allergens'] if item['allergens'] and item['allergens'].strip() else "暂无过敏原",
                    "is_available": bool(item['is_available'])
                }
                menu_items.append(processed_item)
            
            logger.info(f"已成功查询到菜品信息，菜品数量: {len(menu_items)}个,并结构化菜品信息")
            return menu_items

    except Exception as e:
        logger.error(f"查询菜品列表失败:{e}")
        return []
def test_connection():

    with DatasBaseConnection() as db: 
        #业务逻辑(定义SQL 执行SQL)
        db.cursor.execute("select 1")
        test_res=db.cursor.fetchall()#获取SQL语句的结果
        if test_res:
            print(f"测试数据库连接成功，且查询结果是:{test_res}")
        else:
            print(f"测试数据库连接失败")

if __name__ == "__main__":
    # print("\n1.测试数据库连接的可用性:")
    # test_connection()
    # print("\n2.测试数据库菜品信息:")
    # ret = get_all_menu_items()
    # print(ret)
    print("\n3.测试所有菜品信息的列表结构:前端展示")
    ret = get_menu_items()
    for index,item in enumerate(ret,1):
        print(f"这是第{index}个菜品，结构是{item}")