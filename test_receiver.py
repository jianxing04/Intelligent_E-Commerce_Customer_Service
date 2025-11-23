import unittest
from unittest.mock import patch, MagicMock, mock_open
import sys
import os
from io import StringIO

# 添加项目根目录到 sys.path，确保能 import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from src.qwen.receiver import Receiver

class TestReceiver(unittest.TestCase):

    def setUp(self):
        """
        【关键】每次测试前的“大清洗”
        因为 Receiver 的 __init__ 会去读 yaml 文件，为了避免它报错，
        我们需要在实例化之前就 patch 掉文件读取。
        """
        # 准备一份假的 intents.yaml 内容
        self.fake_yaml_content = """
        greet:
          description: "打招呼"
          actions: ["greet"]
        check_phone_number:
          description: "查手机号"
          actions: ["check_phone_number"]
        """
        
    @patch("src.qwen.receiver.log") # 屏蔽日志
    @patch("builtins.open", new_callable=mock_open, read_data="fake_yaml_content") 
    @patch("src.qwen.receiver.yaml.safe_load") # Mock yaml 解析
    @patch("src.qwen.receiver.Path") # Mock 路径处理，防止找不着文件报错
    def test_init_success(self, mock_path, mock_yaml, mock_file, mock_log):
        """
        测试类的初始化 (__init__)
        """
        # 1. 设置 Mock 行为
        mock_yaml.return_value = {
            "greet": {"description": "打招呼", "actions": ["greet"]},
            "check_phone_number": {"description": "查手机", "actions": ["check_phone_number"]}
        }
        
        # 2. 实例化对象
        receiver = Receiver()
        
        # 3. 验证状态
        self.assertEqual(len(receiver.intents), 2)
        self.assertIn("greet", receiver.intents_type)
        self.assertIn("greet", receiver.intent_actions_map)
        self.assertEqual(receiver.intent_actions_map["greet"], ["greet"])

    @patch("src.qwen.receiver.log")
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.qwen.receiver.yaml.safe_load")
    @patch("src.qwen.receiver.Path")
    @patch("builtins.print") # 捕获 print，不让它输出到屏幕
    def test_greet_action(self, mock_print, mock_path, mock_yaml, mock_file, mock_log):
        """
        测试 _greet 方法
        """
        # 1. 实例化 (为了省事，这里 yaml mock 返回空字典也可以，只要不报错)
        mock_yaml.return_value = {}
        receiver = Receiver()
        
        # 2. 调用方法
        receiver._greet()
        
        # 3. 验证是否打印了问候语
        mock_print.assert_called_with("Hello! How can I assist you today?")

    @patch("src.qwen.receiver.log")
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.qwen.receiver.yaml.safe_load")
    @patch("src.qwen.receiver.Path")
    @patch("src.qwen.receiver.worker.pharse_phone_number") # Mock worker 模块
    @patch("src.qwen.receiver.Receiver._timeout_input") # Mock 用户输入方法
    def test_check_phone_number_success(self, mock_input, mock_worker_parse, mock_path, mock_yaml, mock_file, mock_log):
        """
        测试 _check_phone_number：用户输入正确手机号的流程
        """
        # 1. 实例化
        mock_yaml.return_value = {}
        receiver = Receiver()
        
        # 2. 设置 Mock 行为
        mock_input.return_value = "13800138000" # 模拟用户在控制台输入了号码
        mock_worker_parse.return_value = "13800138000" # 模拟 worker 识别出了号码
        
        # 3. 调用方法
        receiver._check_phone_number()
        
        # 4. 验证类的状态是否改变 (Side Effect)
        self.assertEqual(receiver.phone_number, "13800138000")

    @patch("src.qwen.receiver.log")
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.qwen.receiver.yaml.safe_load")
    @patch("src.qwen.receiver.Path")
    @patch("src.qwen.receiver.worker.get_order_info") # Mock worker
    @patch("builtins.print")
    def test_get_order_info(self, mock_print, mock_worker_order, mock_path, mock_yaml, mock_file, mock_log):
        """
        测试 _get_order_info
        """
        # 1. 实例化并预设状态
        mock_yaml.return_value = {}
        receiver = Receiver()
        receiver.phone_number = "13800138000" # 预先设置好手机号
        
        # 2. 模拟 worker 返回订单信息
        mock_worker_order.return_value = {"user_name": "张三", "order_status": "配送中"}
        
        # 3. 调用
        receiver._get_order_info()
        
        # 4. 验证输出
        # assert_any_call 只要曾经打印过这句话就算通过
        mock_print.assert_any_call("用户名：张三")
        mock_print.assert_any_call("订单状态：配送中")

    @patch("src.qwen.receiver.log")
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.qwen.receiver.yaml.safe_load")
    @patch("src.qwen.receiver.Path")
    @patch("src.qwen.receiver.worker.recognize_intent") # Mock 意图识别
    @patch("src.qwen.receiver.Receiver._timeout_input") # Mock 输入
    @patch("src.qwen.receiver.Receiver.handle_intent") # Mock 动作分发 (我们只想测试 execute 的循环逻辑)
    @patch("builtins.print")
    def test_execute_loop(self, mock_print, mock_handle, mock_input, mock_recognize, mock_path, mock_yaml, mock_file, mock_log):
        """
        测试 execute 主循环：输入 -> 识别 -> 分发 -> 退出
        这是一个集成度稍高的测试
        """
        # 1. 实例化
        mock_yaml.return_value = {}
        receiver = Receiver()
        
        # 2. 设置 Mock 序列 (Side Effect 可以是一个列表，表示第1次调用返回什么，第2次返回什么...)
        # 第一次输入 "查订单"，第二次输入 "exit" 退出循环
        mock_input.side_effect = ["查订单", "exit"]
        
        mock_recognize.return_value = "query_order" # 模拟 AI 识别出了意图
        
        # 3. 运行主循环
        receiver.execute()
        
        # 4. 验证
        # 验证是否调用了 handle_intent，参数是否正确
        mock_handle.assert_called_with("query_order")
        # 验证是否最后打印了再见
        mock_print.assert_any_call("机器人: 再见！")

if __name__ == "__main__":
    unittest.main()