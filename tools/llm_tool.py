

import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()




def call_llm(query:str,system_instruction:str)->str:
    api_key=os.getenv("DASHSCOPE_API_KEY")
    api_base=os.getenv("DASHSCOPE_API_BASE")
    model_name = os.getenv("DASHSCOPE_MODEL_NAME")
    if not api_key or not api_base or not model_name:   
        raise ValueError("模型配置信息不全")
    #1.定义一个模型客户端
    llm = ChatOpenAI(
        openai_api_key=api_key,
        openai_api_base=api_base,
        model_name=model_name
    )

    #2.定义提示词模板对象（PromptTemplate，ChatPromptTemplate)
    chat_prompt_template = ChatPromptTemplate.from_messages([
        ("system","{system_instruction}"),
        ("human","{query}") 
    ])

    #3.定义链（chain）----->通过LCEL语法构建链""|""
    chain =  chat_prompt_template | llm

    #4.执行链（分别执行链上的每一个组件）Runnable（可运行）--invoke()[llm实例，提示词模板对象，chain，工具]
    response = chain.invoke({"system_instruction": system_instruction, "query": query})
    #5.直接解析结果
    return response.content

# if __name__ == "__main__":
    # print(call_llm("给我讲一个冷笑话","你是脱口秀演员"))
