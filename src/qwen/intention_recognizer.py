# intention_recognizer.py
import os
import json
import yaml
from dashscope import Generation

def load_intent_config(config_path: str) -> dict:
    """
    从 YAML 文件加载意图配置
    
    参数:
        config_path: 完整的DSL配置文件路径
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"意图配置文件不存在：{config_path}")
    
    # 读取 YAML 文件
    with open(config_path, "r", encoding="utf-8") as f:
        try:
            # 加载整个DSL文件
            dsl_data = yaml.safe_load(f)
            
            # *** 关键改动: 只提取 "intents" 部分用于识别 ***
            intent_dict = dsl_data.get("intents")
            
            if not isinstance(intent_dict, dict):
                raise ValueError("YAML 文件格式错误，'intents' 块必须是键值对结构")
            return intent_dict
        except yaml.YAMLError as e:
            raise ValueError(f"解析 YAML 文件失败：{str(e)}")

def recognize_intent(user_input: str, config_path: str) -> str or None:
    """
    识别用户输入的意图（从 YAML 加载配置，序列化后调用 API）
    
    参数:
        user_input: 用户输入的文本
        config_path: DSL配置文件的路径
        
    返回:
        意图标签（字符串），如果未识别则返回 None
    """
    try:
        # 1. 加载 YAML 中的意图配置 (使用新函数)
        intent_dict = load_intent_config(config_path)
        
        # 2. 将意图字典序列化为 JSON 字符串
        intent_json_str = json.dumps(intent_dict, ensure_ascii=False, indent=2)
        
        # 3. 构建系统提示
        system_prompt = f"""You are Qwen, created by Alibaba Cloud. You are a helpful assistant. 
You should choose one tag from the tag list:
{intent_json_str}
Just reply with the chosen tag."""

        # 4. 构造对话消息
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]
        
        # 5. 调用通义千问 API
        response = Generation.call(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            model="tongyi-intent-detect-v3",
            messages=messages,
            result_format="message",
        )
        
        # 6. 解析返回结果
        return response.output.choices[0].message.content.strip()
            
    except Exception:
        return None

# 测试
if __name__ == "__main__":
    # 获取 config/workflow_dsl.yaml 的路径
    test_config_path = os.path.join(
        os.path.dirname(__file__), 
        "../../",
        "config/workflow_dsl.yaml"
    )
    
    test_input = "hello!"
    print(f"输入: {test_input}")
    print(f"识别: {recognize_intent(test_input, test_config_path)}") # 预期输出: GREETING
    
    test_input_2 = "我的订单ORD12345 什么时候发货？"
    print(f"输入: {test_input_2}")
    print(f"识别: {recognize_intent(test_input_2, test_config_path)}") # 预期输出: CHECK_ORDER_STATUS
