import os
import json
from typing import Optional
from dashscope import Generation
from src.utils.log import log
from http import HTTPStatus
from pathlib import Path

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
    {intent_json_str}仅返回标签本身，不添加任何额外内容。"""

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

    if response is None:
        return "DEFAULT"
    
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
        return "DEFAULT"

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

def query_details(complaint: str) -> Optional[str]:
    """
    查询投诉详情
    
    参数:
        complaint: 投诉内容
    返回:
        投诉详情字符串，若未找到则返回None
    """
    complaint = complaint.strip()
    if not complaint:
        log("投诉内容为空", 2, __file__)
        return None
    
    system_prompt = f"""你是投诉内容识别工具，需从以下聊天记录中归纳总结投诉内容，帮助客户经理快速理解用户需求，仅返回归纳总结后的投诉内容本身，不添加任何额外内容。"""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": complaint.strip()}
    ]
    
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        log("环境变量DASHSCOPE_API_KEY未设置或为空", 1, __file__)
        return None
    
    response = Generation.call(
        api_key=api_key,
        model="qwen-plus",
        messages=messages,
        result_format="message",
    )
    
    complaint_summary = response.output.choices[0].message.content.strip()
    if complaint_summary == "":
        return None
    return complaint_summary

def product_recommendation(preferences: str) -> str | None:
    """
    根据用户偏好推荐产品
    :param preferences: 用户偏好描述字符串
    :return: 通义千问返回的产品推荐结果，失败返回None
    """

    if not preferences:
        log("用户偏好描述为空", 2, __file__)
        return None
    
    # 1. 动态计算products.json路径（跨机器兼容，基于当前文件相对路径）
    current_file = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file)
    project_root = os.path.abspath(os.path.join(current_dir, "../../"))  # 向上两级到项目根目录
    products_json_path = os.path.join(project_root, "config", "products.json")
    
    # 2. 读取并解析产品JSON文件
    try:
        if not os.path.exists(products_json_path):
            log(f"产品配置文件不存在：{products_json_path}", 2, __file__)
            return None
        
        with open(products_json_path, 'r', encoding='utf-8') as f:
            try:
                product_list = json.load(f)
                # 验证JSON格式是否为列表，且每个产品包含必填字段
                required_fields = ["产品类型", "热度", "品牌", "名字", "描述", "功能"]
                if not isinstance(product_list, list) or len(product_list) == 0:
                    log("products.json格式错误：必须是非空列表", 2, __file__)
                    return None
                
                # 验证每个产品的必填字段
                for idx, product in enumerate(product_list):
                    missing_fields = [field for field in required_fields if field not in product]
                    if missing_fields:
                        log(f"产品{idx+1}缺少必填字段：{','.join(missing_fields)}", 1, __file__)
                        continue  # 跳过字段不完整的产品
            
            except json.JSONDecodeError as e:
                log(f"products.json解析失败：{str(e)}", 2, __file__)
                return None
    except Exception as e:
        log(f"读取产品文件时发生错误：{str(e)}", 2, __file__)
        return None
    
    # 3. 构建提示词（清晰告知AI任务、产品库、输出要求）
    system_prompt = """你是专业的电商产品推荐助手，需要根据用户的偏好描述，从提供的产品库中推荐最匹配的产品。
    要求：
    1. 先理解用户核心需求（如产品类型、功能偏好、品牌倾向等）
    2. 从产品库中筛选出3-5个最匹配的产品，匹配度优先于热度
    3. 每个推荐产品需包含：名字、品牌
    4. 推荐理由简洁明了（1-2句话），说明为何该产品符合用户偏好
    5. 输出格式清晰易读，分点列出推荐结果，不添加任何额外内容
    6. 如果没有匹配的产品，直接返回"未找到符合您偏好的产品，建议尝试其他描述
    7. 谨记，你只需要输出推荐结果，不需要输出任何其他内容。
    产品库数据：
    {}""".format(json.dumps(product_list, ensure_ascii=False, indent=0))  # 序列化产品库为字符串

    # 4. 构建消息体（遵循通义千问API调用格式）
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": preferences.strip()}
    ]
    
    # 5. 调用通义千问API
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        log("环境变量DASHSCOPE_API_KEY未设置或为空", 1, __file__)
        return None
    
    try:
        response = Generation.call(
            api_key=api_key,
            model="qwen-plus",
            messages=messages,
            result_format="message",
            temperature=0.3,  # 降低随机性，确保推荐结果更精准
            top_p=0.8  # 控制生成的多样性
        )
        
        # 验证响应状态
        if response.status_code != HTTPStatus.OK:
            log(f"API调用失败，状态码：{response.status_code}，错误信息：{response.message}", 2, __file__)
            return None
        
        # 提取推荐结果
        recommendation = response.output.choices[0].message.content.strip()
        if not recommendation:
            log("API返回空的推荐结果", 1, __file__ )
            return None
        
        return recommendation

    except Exception as e:
        log(f"产品推荐过程中发生未知错误：{str(e)}", 2, __file__)
        return None

def get_membership_info(phone_number: str) -> Optional[dict]:
    """
    获取会员信息
    
    参数:
        phone_number: 手机号码
    返回:
        会员信息字典，若未找到则返回None
    """
    # 1. 计算JSON文件的相对路径
    # worker.py 路径：src/qwen/worker.py
    # JSON文件路径：config/userMemberList.json
    # 相对路径：从worker.py所在目录向上两级 -> 进入config目录 -> 找到JSON文件
    current_file = Path(__file__).resolve()  # 获取当前文件的绝对路径
    json_file_path = current_file.parent.parent.parent / "config" / "userMemberList.json"
    
    # 2. 验证文件存在性
    if not json_file_path.exists():
        log(f"警告：会员信息文件不存在 - {json_file_path}", 1, __file__)
        return None
    
    try:
        # 3. 读取JSON文件
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 4. 提取用户会员列表（兼容JSON结构）
        user_member_list = data.get("userMemberList", [])
        if not isinstance(user_member_list, list):
            log("警告：JSON文件格式错误，userMemberList应为数组类型", 1, __file__)
            return None
        
        # 5. 匹配手机号码（去除空格，支持灵活输入）
        cleaned_phone = phone_number.strip()
        for member_info in user_member_list:
            # 确保会员信息中存在phone字段且格式正确
            if isinstance(member_info, dict) and member_info.get("phone", "").strip() == cleaned_phone:
                # 返回匹配的会员信息副本，避免修改原数据
                return member_info.copy()
        
        # 6. 未找到匹配用户
        return None
    
    except json.JSONDecodeError as e:
        log(f"错误：JSON文件解析失败 - {e}", 2, __file__)
        return None
    except PermissionError:
        log(f"错误：没有读取文件的权限 - {json_file_path}", 2, __file__)
        return None
    except Exception as e:
        log(f"错误：获取会员信息时发生异常 - {str(e)}", 2, __file__)
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