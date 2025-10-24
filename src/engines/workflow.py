import yaml
import os
from typing import Dict, Any

# 导入现有的模块
from ..qwen.intention_recognizer import recognize_intent
from ..qwen.parse_the_order_number import extract_order_number

class WorkflowEngine:
    def __init__(self):
        # 1. 加载DSL工作流文件
        dsl_path = os.path.join(os.path.dirname(__file__), 
            "../../",
            "config/workflow_dsl.yaml")
        if not os.path.exists(dsl_path):
            raise FileNotFoundError(f"DSL配置文件不存在：{dsl_path}")
        with open(dsl_path, "r", encoding="utf-8") as f:
            self.dsl = yaml.safe_load(f)
        
        self.workflow_rules = self.dsl.get("workflow", {})
        
        # 2. 初始化对话状态
        self.session_state: Dict[str, Any] = {
            "chat_history": [],
            "filled_slots": {}  # 存储已提取到的参数，如 "order_number"
        }

    def process_message(self, user_input: str) -> str:
        """
        处理用户消息并执行DSL定义的工作流
        """
        # 将当前输入加入历史记录
        self.session_state["chat_history"].append(f"User: {user_input}")
        
        # 1. 意图识别
        config_path = os.path.join(os.path.dirname(__file__), "../../config/workflow_dsl.yaml")
        intent = recognize_intent(user_input, config_path)
        print(f"[Engine] 识别到意图: {intent}")

        # 2. 根据意图查找工作流规则
        rule = self.workflow_rules.get(intent)
        if not rule:
            return "抱歉，我不知道如何处理这个请求。"

        # 3. 执行工作流动作
        action_type = rule.get("action_type")

        # 动作类型 (1): 直接回复
        if action_type == "reply":
            response = rule.get("message", "我没有配置回复。")
            self.session_state["chat_history"].append(f"Assistant: {response}")
            return response

        # 动作类型 (2): 提取参数并执行
        elif action_type == "extract_and_execute":
            # 检查所有必需的槽位
            required_slots = rule.get("required_slots", [])
            for slot in required_slots:
                slot_name = slot["name"]
                
                # 如果槽位还未填充，尝试从当前对话中提取
                if slot_name not in self.session_state["filled_slots"]:
                    print(f"[Engine] 正在尝试提取缺失的槽位: {slot_name}")
                    
                    # *** 这里调用了你的 parse_the_order_number 模块 ***
                    # (为了演示，我们假设只提取订单号)
                    if slot_name == "order_number":
                        extracted_value = extract_order_number(self.session_state["chat_history"])
                        
                        if extracted_value:
                            print(f"[Engine] 成功提取到: {extracted_value}")
                            self.session_state["filled_slots"][slot_name] = extracted_value
                        else:
                            # 如果提取失败，返回 "反问" 提示
                            print(f"[Engine] 提取失败，向用户提问。")
                            response = slot["clarification_prompt"]
                            self.session_state["chat_history"].append(f"Assistant: {response}")
                            return response

            # 如果所有槽位都已填充
            print(f"[Engine] 所有槽位已填充: {self.session_state['filled_slots']}")
            # 清空槽位，准备下一次
            order_num = self.session_state["filled_slots"].pop("order_number") 
            
            # TODO: 在这里调用 "handler_module" 定义的真实业务逻辑
            # 例如: db_result = db_api.query_status(order_num)
            # 我们这里只是模拟一下
            response = f"正在为您查询订单 {order_num} 的状态... (模拟执行)"
            self.session_state["chat_history"].append(f"Assistant: {response}")
            return response
            
        else:
            return "未知的动作类型。"
