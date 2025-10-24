import os
from dashscope import Generation

def extract_order_number(chat_history: list[str]) -> str or None:
    """
    通过通义千问API从聊天记录中提取订单号
    
    参数:
        chat_history: 用户历史聊天记录列表
        
    返回:
        提取到的订单号字符串；若未提取到则返回None
    """
    try:
        # 构建系统提示（明确提取规则）
        system_prompt = """你是一个订单号提取助手，需要从用户提供的聊天记录中提取订单号。
订单号通常是包含数字、字母的组合（可能带有ORD、ORDER等前缀），长度一般在8-20位。
请严格按照以下规则处理：
1. 只返回提取到的订单号本身，不要添加任何额外文字
2. 如果存在多个订单号，只返回用户最近一次提到的订单号
3. 如果没有找到订单号，返回"NOT_FOUND"
"""

        # 构造对话消息（将聊天记录拼接为上下文）
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"聊天记录：{chr(10).join(chat_history)}"}
        ]
        
        # 调用通义千问API
        response = Generation.call(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            model="qwen-plus",  # 可根据需要更换模型
            messages=messages,
            result_format="message"
        )
        
        # 解析返回结果
        result = response.output.choices[0].message.content.strip()
        
        if result == "NOT_FOUND":
            return None
        return result
        
    except Exception as e:
        print(f"提取订单号出错：{str(e)}")
        return None

# 测试代码
if __name__ == "__main__":
    test_chat1 = ["我的订单是123456789012", "帮我查一下这个订单状态"]
    print(extract_order_number(test_chat1))  # 预期输出: 123456789012
    
    test_chat2 = ["我的订单是123456789012", "帮我查一下这个订单状态","我买的东西订单号是ORD87654321", "什么时候发货？"]
    print(extract_order_number(test_chat2))  # 预期输出: ORD87654321
    
    test_chat3 = ["你好", "请问退货政策是什么？"]
    print(extract_order_number(test_chat3))  # 预期输出: None