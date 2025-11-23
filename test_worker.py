import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# 假设你的 worker.py 在 src/qwen/ 目录下
# 我们需要把项目根目录加入路径，才能 import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from src.qwen import worker

class TestWorker(unittest.TestCase):

    def setUp(self):
        """
        【测试驱动 - Setup】
        每次执行测试函数前，都会运行这里的代码。
        我们可以在这里做一些初始化工作。
        """
        self.fake_api_key = "sk-fake-key-123"

    # ----------------------------------------------------------
    # 场景一：测试 recognize_intent (依赖 API)
    # ----------------------------------------------------------
    @patch("src.qwen.worker.log")  # 桩1：把 log 函数屏蔽掉，不让它打印乱七八糟的
    @patch("src.qwen.worker.os.getenv") # 桩2：伪造环境变量
    @patch("src.qwen.worker.Generation.call") # 桩3：【核心桩】伪造通义千问API
    def test_recognize_intent_success(self, mock_generation, mock_getenv, mock_log):
        """
        测试意图识别成功的情况
        """
        # --- 1. 设置桩的行为 (Stubbing) ---
        
        # 让 os.getenv 返回假的 Key
        mock_getenv.return_value = self.fake_api_key
        
        # 构造一个假的 API 响应对象 (Mock Object)
        # 结构要模仿 dashscope 返回的真实结构：response.output.choices[0].message.content
        mock_response = MagicMock()
        mock_response.output.choices[0].message.content = "REFUND" # 假定 AI 返回了“退款”
        mock_generation.return_value = mock_response

        # --- 2. 驱动代码 (Driver) ---
        user_input = "我要退款"
        intent_dict = {"REFUND": "退款业务", "ORDER": "查询订单"}
        
        # 调用待测函数
        result = worker.recognize_intent(user_input, intent_dict)

        # --- 3. 断言验证 (Assertion) ---
        self.assertEqual(result, "REFUND", "意图识别结果应该与桩返回的一致")
        
        # 验证是否真的调用了 API (验证交互)
        mock_generation.assert_called_once()

    # ----------------------------------------------------------
    # 场景二：测试 pharse_phone_number (提取手机号)
    # ----------------------------------------------------------
    @patch("src.qwen.worker.log")
    @patch("src.qwen.worker.os.getenv")
    @patch("src.qwen.worker.Generation.call")
    def test_pharse_phone_number(self, mock_api, mock_getenv, mock_log):
        """
        测试手机号提取功能
        """
        # 1. 准备桩
        mock_getenv.return_value = "sk-fake-key"
        
        # 模拟 AI 成功提取到号码
        mock_response = MagicMock()
        mock_response.output.choices[0].message.content = "13812345678"
        mock_api.return_value = mock_response

        # 2. 调用 (注意你的函数名里有个拼写小瑕疵 pharse，测试要随代码保持一致)
        result = worker.pharse_phone_number("我的电话是13812345678，请联系我")

        # 3. 验证
        self.assertEqual(result, "13812345678")
        
        # 测试提取失败的情况（模拟 AI 返回空）
        mock_response.output.choices[0].message.content = ""
        result_none = worker.pharse_phone_number("我没有电话")
        self.assertIsNone(result_none)

    # ----------------------------------------------------------
    # 场景三：测试 get_order_info (依赖文件系统)
    # ----------------------------------------------------------
    @patch("src.qwen.worker.log")
    @patch("src.qwen.worker.os.path.exists") # 桩：伪造文件存在检测
    @patch("builtins.open", new_callable=unittest.mock.mock_open, read_data='{"13800138000": {"order_id": "1001", "status": "已发货"}}') # 桩：伪造文件读取
    def test_get_order_info_found(self, mock_file, mock_exists, mock_log):
        """
        测试从文件中成功读取订单
        """
        # --- 设置桩 ---
        mock_exists.return_value = True # 告诉程序：文件是存在的

        # --- 驱动代码 ---
        phone = "13800138000"
        result = worker.get_order_info(phone)

        # --- 断言 ---
        self.assertIsNotNone(result)
        self.assertEqual(result["order_id"], "1001")
        self.assertEqual(result["status"], "已发货")

    # ----------------------------------------------------------
    # 场景四：测试 query_details (投诉详情归纳)
    # ----------------------------------------------------------
    @patch("src.qwen.worker.log")
    @patch("src.qwen.worker.os.getenv")
    @patch("src.qwen.worker.Generation.call")
    def test_query_details(self, mock_api, mock_getenv, mock_log):
        """
        测试投诉内容归纳功能
        """
        # 1. 准备桩
        mock_getenv.return_value = "sk-fake-key"
        
        mock_response = MagicMock()
        mock_response.output.choices[0].message.content = "用户投诉物流太慢"
        mock_api.return_value = mock_response

        # 2. 调用
        result = worker.query_details("你们快递太慢了，我要投诉！")

        # 3. 验证
        self.assertEqual(result, "用户投诉物流太慢")

    # ----------------------------------------------------------
    # 场景五：测试 product_recommendation (文件+API混合双打)
    # ----------------------------------------------------------
    @patch("src.qwen.worker.log")  # 屏蔽日志，让输出干净点
    @patch("src.qwen.worker.os.getenv") # 桩：伪造环境变量(API Key)
    @patch("src.qwen.worker.Generation.call") # 桩：伪造通义千问 API
    @patch("src.qwen.worker.os.path.exists")  # 桩：伪造文件存在检查
    # 桩：伪造文件读取 (mock_open)。注意 read_data 里必须填入符合你代码逻辑的完整 JSON 结构
    @patch("builtins.open", new_callable=unittest.mock.mock_open, 
           read_data='[{"产品类型": "手机", "热度": 100, "品牌": "小米", "名字": "小米14", "描述": "旗舰性能", "功能": "拍照强"}]') 
    def test_product_recommendation_success(self, mock_file, mock_exists, mock_api, mock_getenv, mock_log):
        """
        测试产品推荐功能：成功读取文件并调用API返回推荐结果
        """
        # --- 1. 准备桩的行为 (Setup Stubs) ---
        
        # 假装 API Key 存在
        mock_getenv.return_value = "sk-test-key-123" 
        
        # 假装 products.json 文件是存在的
        mock_exists.return_value = True          
        
        # 假装 API 调用成功并返回了推荐语
        mock_response = MagicMock()
        mock_response.status_code = 200 # 模拟 HTTP 200 OK
        mock_response.output.choices[0].message.content = "根据您的需求，推荐您购买：小米14"
        mock_api.return_value = mock_response

        # --- 2. 执行测试 (Execute) ---
        user_pref = "我想买个拍照好的手机"
        result = worker.product_recommendation(user_pref)

        # --- 3. 验证结果 (Assert) ---
        
        # 验证 A: 函数返回值是否就是 API 里的假数据
        self.assertEqual(result, "根据您的需求，推荐您购买：小米14")
        
        # 验证 B (进阶): 验证你的代码是否真的把文件里的数据读出来并发给 AI 了？
        # 获取 mock_api 被调用时的参数
        args, kwargs = mock_api.call_args
        # 拿到发送给 AI 的 messages
        sent_messages = kwargs['messages']
        system_prompt = sent_messages[0]['content']
        
        # 既然我们在 read_data 里伪造了"小米14"，那发给 AI 的提示词里必须包含它
        self.assertIn("小米14", system_prompt, "严重错误：产品数据没有被正确读取并拼接到 Prompt 里！")
        self.assertIn("拍照强", system_prompt)
        
        print("\n[通过] 产品推荐测试：文件读取正常，Prompt拼接正确，API调用模拟成功。")

    # ----------------------------------------------------------
    # 场景六：测试 get_order_info (测试异常逻辑)
    # ----------------------------------------------------------
    @patch("src.qwen.worker.log")
    def test_get_order_info_invalid_phone(self, mock_log):
        """
        测试手机号格式错误的情况（不需要桩文件，因为逻辑在读文件前就拦截了）
        """
        phone = "123" # 错误的手机号
        result = worker.get_order_info(phone)
        
        self.assertIsNone(result)
        # 验证是否记录了日志
        mock_log.assert_called_with("手机号码格式不正确", 2, unittest.mock.ANY)
        
    # ----------------------------------------------------------
    # 场景七：测试 get_membership_info (会员信息 - 特殊路径处理)
    # ----------------------------------------------------------
    # 注意：这个函数在你的代码里使用了 pathlib.Path 而不是 os.path
    # 所以我们需要 mock 掉 Path 类，防止它真的去磁盘找文件
    @patch("src.qwen.worker.log")
    @patch("src.qwen.worker.Path") # 关键点：Mock 掉 Path 类
    @patch("builtins.open", new_callable=unittest.mock.mock_open, 
           read_data='{"userMemberList": [{"phone": "13999999999", "level": "Diamond", "points": 5000}]}')
    def test_get_membership_info(self, mock_file, mock_path_cls, mock_log):
        """
        测试会员信息查询：模拟 pathlib.Path 和 JSON 读取
        """
        # 1. 准备复杂的 Path 桩
        # 因为你的代码是链式调用：Path(...).resolve().parent... / "config" / "file"
        # 我们需要配置这一长串调用，最后让 .exists() 返回 True
        
        # 获得最终的文件路径对象模拟
        mock_final_path_obj = MagicMock()
        mock_final_path_obj.exists.return_value = True # 骗过代码：文件存在！
        
        # 拼接链条：让所有除法操作符 (/) 最终都指向这个“存在”的文件对象
        # 这里的 __truediv__ 对应代码里的 / 操作符
        mock_path_cls.return_value.resolve.return_value.parent.parent.parent.__truediv__.return_value.__truediv__.return_value = mock_final_path_obj

        # 2. 调用
        result = worker.get_membership_info("13999999999")

        # 3. 验证
        self.assertIsNotNone(result)
        self.assertEqual(result['level'], "Diamond")
        self.assertEqual(result['points'], 5000)
        
        # 测试找不到用户的情况
        result_not_found = worker.get_membership_info("13000000000") # 这是一个不在 read_data 里的号码
        self.assertIsNone(result_not_found)

# ----------------------------------------------------------
# 测试驱动入口 (Test Driver Main)
# ----------------------------------------------------------
if __name__ == "__main__":
    # 这就是“驱动”：它负责查找并运行上面写的所有测试用例
    unittest.main()