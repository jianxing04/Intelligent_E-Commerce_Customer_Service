import os
import json
from typing import Optional
from dashscope import Generation
from src.utils.log import log

def recognize_intent(user_input: str, intent_dict: dict) -> Optional[str]:
    """
    识别用户输入的意图（从意图字典中选择最匹配的标签）
    
    参数:
        user_input: 用户输入的文本
        intent_dict: 意图字典，包含意图标签和描述（格式：{标签: 描述, ...}）
    返回:
        意图标签（字符串），仅在自身逻辑异常时返回None；第三方/未知异常直接抛出
    """
    # 1. 输入合法性验证（自身逻辑异常：主动处理）
    if not isinstance(user_input, str) or not user_input.strip():
        log("用户输入为空或非字符串类型", 2, __file__)
        return None
    if not isinstance(intent_dict, dict) or not intent_dict:
        log("意图字典为空或非字典类型", 2, __file__)
        return None

    # 2. 意图字典JSON序列化（自身逻辑异常：主动处理）
    try:
        intent_json_str = json.dumps(intent_dict, ensure_ascii=False, indent=2)
    except json.JSONEncodeError as e:
        log(f"意图字典JSON序列化失败：{str(e)}，字典内容：{intent_dict}", 1, __file__)
        return None

    # 3. 构建系统提示和对话消息（无异常风险，不处理）
    system_prompt = f"""你是意图识别工具，需从以下意图标签中选择最匹配的一个：
{intent_json_str}
仅返回标签本身，不添加任何额外内容。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input.strip()}
    ]

    # 4. API密钥验证（自身逻辑异常：主动处理）
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        log("环境变量DASHSCOPE_API_KEY未设置或为空", 1, __file__)
        return None
    if not isinstance(api_key, str) or not api_key.strip():
        log("环境变量DASHSCOPE_API_KEY的值无效（非字符串或空）", 1, __file__)
        return None

    # 5. 调用通义千问API（第三方异常：不捕获，直接抛出）
    response = Generation.call(
        api_key=api_key,
        model="tongyi-intent-detect-v3",
        messages=messages,
        result_format="message",
    )

    # 6. 解析API响应（第三方响应格式异常：不捕获，直接抛出）
    # 检查响应结构完整性
    if not hasattr(response, "output"):
        raise AttributeError("API响应缺少output字段")
    if not response.output.choices:
        raise IndexError("API响应的choices列表为空")
    
    detected_intent = response.output.choices[0].message.content.strip()
    
    # 验证结果是否在意图字典中（自身逻辑校验：主动处理）
    if detected_intent not in intent_dict:
        log(f"API返回的意图不在字典中：{detected_intent}，可选意图：{list(intent_dict.keys())}", 1, __file__)
        return None

    return detected_intent

def pharse_phone_number(user_input: str) -> Optional[str]:
    """
    从文本中提取手机号码（假设手机号码为11位数字）
    
    参数:
        user_input: 输入文本
    返回:
        提取到的手机号码字符串，若未找到则返回None
    """
    # 输入合法性验证（自身逻辑异常：主动处理）
    if not isinstance(user_input, str) or not user_input.strip():
        log("用户输入为空或非字符串类型", 2, __file__)
        return None
    
    system_prompt = f"""你是电话号码识别工具，需从以下聊天记录中识别出手机号码，仅返回手机号码本身，不添加任何额外内容。
假设手机号码为11位数字。若未找到手机号码，则返回空字符串。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input.strip()}
    ]

    # API密钥验证（自身逻辑异常：主动处理）
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        log("环境变量DASHSCOPE_API_KEY未设置或为空", 1, __file__)
        return None
    if not isinstance(api_key, str) or not api_key.strip():
        log("环境变量DASHSCOPE_API_KEY的值无效（非字符串或空）", 1, __file__)
        return None

    # 调用通义千问API（第三方异常：不捕获，直接抛出）
    response = Generation.call(
        api_key=api_key,
        model="qwen-plus",
        messages=messages,
        result_format="message",
    )

    phone_number=response.output.choices[0].message.content.strip()
    if phone_number == "":
        return None
    return phone_number

def get_order_info(phone_number: str) -> Optional[dict]:
    """
    获取订单信息
    
    参数:
        phone_number: 手机号码
    返回:
        订单信息字典，若未找到则返回None
    """
    
    phone_number = phone_number.strip()
    if not phone_number.isdigit() or len(phone_number) != 11:
        log("手机号码格式不正确", 2, __file__)
        return None
    
    # 1. 动态获取项目根目录（基于当前文件的相对路径计算）
    # 当前文件路径：worker.py -> 所在目录：src/qwen/
    # 项目根目录 = worker.py目录 -> 上两级目录（src/ -> 项目根目录）
    current_file_dir = os.path.dirname(os.path.abspath(__file__))  # 获取worker.py的绝对目录
    project_root = os.path.abspath(os.path.join(current_file_dir, "../.."))  # 向上两级：/src/qwen -> /src -> /
    
    # 2. 拼接配置文件的相对路径（项目根目录/config/user_orders.json）
    order_file_path = os.path.join(
        project_root,
        "config",
        "user_orders.json"
    )
    
    # 验证文件是否存在
    if not os.path.exists(order_file_path):
        log(f"订单配置文件不存在 - {order_file_path}", 1, __file__)
        return None
    
    try:
        # 读取JSON文件（指定utf-8编码避免中文乱码）
        with open(order_file_path, 'r', encoding='utf-8') as f:
            order_data = json.load(f)  # 加载JSON数据（电话号码为key）
        
        # 主键查询：检查手机号是否存在
        if phone_number in order_data:
            return order_data[phone_number].copy()  # 深拷贝避免修改原数据
        else:
            log(f"未查询到手机号 {phone_number} 对应的订单", 2, __file__)
            return None
    
    except json.JSONDecodeError as e:
        log(f"订单配置文件格式无效 - {str(e)}", 1, __file__)
        return None
    except PermissionError:
        log(f"无权限访问订单配置文件 - {order_file_path}", 1, __file__)
        return None
    except Exception as e:
        log(f"获取订单信息失败：{str(e)}", 1, __file__)
        return None
    
# 测试代码
if __name__ == "__main__":
    # 测试时打印文件路径，验证是否正确（移植后可通过该输出调试路径问题）
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_file_dir, "../.."))
    order_file_path = os.path.join(project_root, "config", "user_orders.json")
    print(f"项目根目录：{project_root}")
    print(f"订单文件路径：{order_file_path}")
    
    # 测试查询逻辑
    test_phone1 = "13888888888"
    order1 = get_order_info(test_phone1)
    if order1:
        print(f"\n查询成功（{test_phone1}）：")
        print(f"用户名：{order1['user_name']}")
        print(f"订单状态：{order1['order_status']}\n")