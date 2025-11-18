import yaml
from pathlib import Path
from src.utils.log import log
from src.qwen import worker
import os
import json
from datetime import datetime

class Receiver:
    def __init__(self):
        # 1. 获取当前文件的 Path 对象
        current_file_path = Path(__file__) # .../src/qwen/receiver.py
        log("QwenReceiver init", 3, str(current_file_path))

        # 2. 获取当前文件所在的目录
        self.work_dir = current_file_path.parent # .../src/qwen
        
        # 3. 获取项目根目录 (祖父目录)
        #    .parent -> .../src
        #    .parent -> .../ (项目根目录)
        project_root = self.work_dir.parent.parent 
        
        try:
            # 4. 使用 / 运算符拼接路径 (pathlib 的特性)
            intentsFilePath = project_root / 'config' / 'intents.yaml'
            
            with open(intentsFilePath, 'r') as file:
                self.intents = yaml.safe_load(file)

            self.intents_type = self._extract_intents_for_nlp()
            self.intent_actions_map = self._extract_actions_for_nlp()
                
        except FileNotFoundError:
            log(f"Error: intentions.yaml file not found in {intentsFilePath}", 1, str(current_file_path))
            self.intents = {}

        #记录用户相关信息
        self.phone_number=None
        self.preferences=None

        #意图行为字典
        self.action_handlers = {
            "greet": self._greet,
            "check_phone_number": self._check_phone_number,
            "get_order_info": self._get_order_info,
            "query_details": self._query_details,
            "asking_preferences": self._asking_preferences,
            "product_recommendation": self._product_recommendation
        }

    def _extract_intents_for_nlp(self):
        """
        从DSL数据中提取意图名称和描述，用于大模型意图识别
        """
        intents_map = {}

        for key, value in self.intents.items():
            if isinstance(value, dict) and 'description' in value:
                description = value['description']
                # 格式：意图名称:描述
                intents_map[key] = description
            else:
                log(f"意图文件配置格式出错！{key}缺少描述(description)字段！",2,__file__)
                continue

        return intents_map
    
    def _extract_actions_for_nlp(self):
        """
        从DSL数据中提取意图名称和对应动作，用于大模型意图识别
        """
        actions_map = {}
        
        for key, value in self.intents.items():
            if isinstance(value, dict) and 'actions' in value:
                actions = value['actions']
                # 格式：意图名称:操作列表
                actions_map[key] = actions
            else:
                log(f"意图文件配置格式出错！{key}缺少操作(actions)字段！",2,__file__)
                continue

        return actions_map

    def execute(self):
        while True:
            user_input=input("您: ").strip()
            if user_input.lower() == 'exit':
                print("机器人: 再见！")
                break
            if not user_input:
                continue
            user_intent = worker.recognize_intent(user_input, self.intents_type)
            if user_intent is None:
                print("==========程序意图识别出错，请联系开发者==========")
                continue
            self.handle_intent(user_intent)
            
    def handle_intent(self, intent: str):
        actions = self.intent_actions_map.get(intent)
        if not actions:
            log(f"未找到意图 '{intent}' 的对应动作。", 2, __file__)
            return
        for action in actions:
            func=self.action_handlers.get(action)
            log(f"意图: {intent}, 动作: {action}, 函数: {func}", 2, __file__)
            if func:
                func()
            else:
                log(f"未找到动作处理函数 '{action}'。", 2, __file__)
                print(f"机器人: 抱歉，我无法执行动作 '{action}'。")

    def _greet(self):
        print("Hello! How can I assist you today?")

    def _check_phone_number(self):
        self.phone_number=None
        while not self.phone_number:
            print("机器人: 请提供您的手机号码以继续查询订单。")
            phone = input("您（请输入手机号码）: ").strip()
            res=worker.pharse_phone_number(phone).strip()
            if res and res.isdigit() and len(res) == 11:
                self.phone_number=res
                print(f"机器人: 已记录您的手机号码：{self.phone_number}")
            else:
                print("机器人: 抱歉，未能识别有效的手机号码。请重试。")
                
    def _get_order_info(self):
        order_info = worker.get_order_info(self.phone_number)
        if order_info:
            print(f"机器人: 您的订单信息如下：")
            print(f"用户名：{order_info['user_name']}")
            print(f"订单状态：{order_info['order_status']}")
        else:
            print("机器人: 抱歉，未能获取到您的订单信息。")

    def _query_details(self):
        # 动态计算JSON文件路径（基于当前文件的相对路径，不硬编码绝对路径）
        # 当前文件（receiver.py）的绝对路径
        current_file_path = os.path.abspath(__file__)
        # 当前文件所在目录（src/qwen）
        current_dir = os.path.dirname(current_file_path)
        # 项目根目录（Intelligent_E-Commerce_Customer_Service）- 向上两级目录
        project_root = os.path.abspath(os.path.join(current_dir, "../../"))
        # 目标JSON文件路径（根目录/config/complain_summary.json）
        json_path = os.path.join(project_root, "config", "complain_summary.json")
        
        print("机器人: 十分抱歉给您带来了不好的体验，我们愿意倾听您的意见，请您详细描述您遇到的问题，我们会尽快处理。")
        complaint = input("您（请输入投诉内容）: ").strip()
        
        while True:
            # 确保用户输入不为空
            if not complaint:
                print("机器人: 您的输入不能为空，请重新描述您遇到的问题。")
                complaint = input("您（请输入投诉内容）: ").strip()
                continue
            
            complaint_summary = worker.query_details(complaint)
            if complaint_summary:
                print(f"机器人: 您的投诉内容已经记录，感谢您的反馈！")
                
                # 准备要写入的数据（包含时间戳、原始投诉、总结，便于后续分析）
                complaint_data = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # 时间戳
                    "original_complaint": complaint,  # 原始投诉内容
                    "summary": complaint_summary  # 投诉总结
                }
                
                # 处理JSON文件追加
                try:
                    # 检查目录是否存在，不存在则创建
                    config_dir = os.path.dirname(json_path)
                    if not os.path.exists(config_dir):
                        os.makedirs(config_dir)
                        log(f"自动创建配置目录: {config_dir}", 2, __file__)
                    
                    # 读取现有数据或创建新列表
                    if os.path.exists(json_path) and os.path.getsize(json_path) > 0:
                        with open(json_path, 'r', encoding='utf-8') as f:
                            try:
                                # 尝试解析JSON数据
                                data_list = json.load(f)
                                # 确保数据是列表格式
                                if not isinstance(data_list, list):
                                    data_list = [data_list]
                            except json.JSONDecodeError as e:
                                # JSON格式错误时，创建新列表并备份错误文件
                                log(f"警告: JSON文件格式错误，将创建新文件。错误信息: {e}", 2, __file__)
                                # 备份错误文件（添加时间戳避免覆盖）
                                backup_path = f"{json_path}.backup.{datetime.now().strftime('%Y%m%d%H%M%S')}"
                                os.rename(json_path, backup_path)
                                log(f"错误文件已备份至: {backup_path}", 2, __file__)
                                data_list = []
                    else:
                        # 文件不存在或为空，创建新列表
                        data_list = []
                    
                    # 追加新数据
                    data_list.append(complaint_data)
                    
                    # 写入JSON文件（带格式化，便于阅读）
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(data_list, f, ensure_ascii=False, indent=2)
                    
                    log(f"投诉总结已成功保存至: {json_path}", 2, __file__)
                    break
                except Exception as e:
                    # 捕获所有异常，确保程序不崩溃
                    log(f"警告: 保存投诉总结时发生错误，但您的投诉已记录。错误信息: {e}", 2, __file__)
                    break
            
            # 总结失败时提示用户重新输入
            print("机器人: 抱歉，未能归纳总结您的投诉内容，请您重新描述您遇到的问题。")
            complaint = input("您（请输入投诉内容）: ").strip()

    def _asking_preferences(self):
        while True:
            if not self.preferences:
                print("机器人: 请问您对商品有什么特殊要求吗？")
                self.preferences = input("您（请输入特殊要求）: ").strip()
                continue
            else:
                break

    def _product_recommendation(self):
        res=worker.product_recommendation(self.preferences)
        if res:
            print(f"机器人: 为您推荐以下商品：{res}")
        else:
            print("机器人: 抱歉，未能推荐商品。")