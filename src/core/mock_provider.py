import time
from typing import Dict, Any, Generator, Optional
from src.core.llm_provider import LLMProvider

class MockProvider(LLMProvider):
    """
    Mock LLM Provider that simulates responses for evaluation test cases.
    Supports three modes: 'chatbot', 'agent_v1', and 'agent_v2'.
    """
    def __init__(self, mode: str = "agent_v2", model_name: str = "phi3-mock"):
        super().__init__(model_name=model_name)
        self.mode = mode

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()
        
        # Determine the last user instruction
        # Since prompt can have history, let's find the original user query.
        # The prompt will typically start with the conversation history or contain it.
        # Let's extract the main query by finding the first user message.
        lines = prompt.split("\n")
        user_query = ""
        for line in lines:
            # Look for lines that don't start with standard ReAct prefixes
            line_str = line.strip()
            if line_str and not any(line_str.startswith(p) for p in ["Thought:", "Action:", "Observation:", "System:", "User:"]):
                user_query = line_str
                break
        
        if not user_query:
            # Fallback to the last line if we couldn't parse
            user_query = lines[0].strip() if lines else ""

        # Count the number of observations in the prompt to know which step we are on
        obs_count = prompt.count("Observation:")
        
        # Check for standard refusal cases (out of bounds or jailbreak) first, regardless of mode
        # Case 9: Weather
        if "thời tiết" in user_query.lower() or "weather" in user_query.lower():
            content = "Úi, chủ đề này nằm ngoài phạm vi chuyên môn của tôi rồi nè. Bạn có muốn đặt một câu hỏi khác liên quan đến Retail/E-commerce: Trợ lý bán hàng thông minh cho cửa hàng điện tử để tôi hỗ trợ nhanh nhất không? 💛"
            usage = {"prompt_tokens": len(prompt)//4, "completion_tokens": len(content)//4, "total_tokens": (len(prompt)+len(content))//4}
            time.sleep(0.1)
            return {
                "content": f"Final Answer: {content}",
                "usage": usage,
                "latency_ms": 150,
                "provider": "mock"
            }
            
        # Case 10: Prompt injection
        if "bỏ qua" in user_query.lower() or "ignore" in user_query.lower() or "system prompt" in user_query.lower():
            content = "Úi, chủ đề này nằm ngoài phạm vi chuyên môn của tôi rồi nè. Bạn có muốn đặt một câu hỏi khác liên quan đến Retail/E-commerce: Trợ lý bán hàng thông minh cho cửa hàng điện tử để tôi hỗ trợ nhanh nhất không? 💛"
            usage = {"prompt_tokens": len(prompt)//4, "completion_tokens": len(content)//4, "total_tokens": (len(prompt)+len(content))//4}
            time.sleep(0.1)
            return {
                "content": f"Final Answer: {content}",
                "usage": usage,
                "latency_ms": 150,
                "provider": "mock"
            }

        # ----------------------------------------------------
        # MODE: CHATBOT BASELINE
        # ----------------------------------------------------
        if self.mode == "chatbot":
            time.sleep(0.2)
            content = ""
            if "iphone 15" in user_query.lower():
                if "winner" in user_query.lower():
                    content = "Sản phẩm iPhone 15 còn hàng. 2 iPhone 15 có giá 2000 USD. Sau khi áp mã WINNER giảm giá 10%, tổng tiền là 1800 USD và phí giao hàng đến Hà Nội là miễn phí nhé!"
                else:
                    content = "Chào bạn, sản phẩm iPhone 15 bên mình đang có giá khoảng 25 triệu đồng và còn hàng nhé."
            elif "macbook air" in user_query.lower():
                content = "MacBook Air bên mình vẫn còn hàng nha bạn, bạn có muốn đặt mua luôn không?"
            elif "ipad pro" in user_query.lower():
                if "hello" in user_query.lower():
                    content = "iPad Pro có giá 800 USD, áp dụng mã giảm giá HELLO giảm 5% còn 760 USD. Giao hàng đến Hồ Chí Minh phí là 50 USD, tổng cộng là 810 USD nhé."
                elif "welcome" in user_query.lower():
                    content = "Dạ iPad Pro giá 800 USD, áp mã WELCOME giảm 15% là còn 680 USD. Phí ship Hà Nội là 30 USD, tổng là 710 USD nha."
            elif "toshiba" in user_query.lower():
                content = "Dạ có máy giặt Toshiba nha bạn, bên mình đang có mẫu Toshiba 9kg giá 7.5 triệu đồng."
            elif "so sánh" in user_query.lower():
                content = "Dạ, iPhone 15 có giá 25 triệu và còn hàng nhiều, còn iPad Pro giá 20 triệu còn ít hàng ạ."
            elif "airpods pro" in user_query.lower():
                if "welcome" in user_query.lower():
                    content = "Dạ AirPods Pro giá 200 USD, áp mã WELCOME giảm 15% là còn 170 USD nha bạn."
            else:
                content = "Tôi có thể giúp gì cho bạn về các sản phẩm tại cửa hàng?"

            # Chatbot baseline just returns the final answer directly
            usage = {"prompt_tokens": len(prompt)//4, "completion_tokens": len(content)//4, "total_tokens": (len(prompt)+len(content))//4}
            return {
                "content": f"Final Answer: {content}",
                "usage": usage,
                "latency_ms": 220,
                "provider": "mock"
            }

        # ----------------------------------------------------
        # MODE: AGENT V1 (Has some errors, typos, format issues)
        # ----------------------------------------------------
        elif self.mode == "agent_v1":
            time.sleep(0.3)
            content = ""
            
            # Case 1: Simple search
            if "iphone 15" in user_query.lower() and "winner" not in user_query.lower() and "so sánh" not in user_query.lower():
                if obs_count == 0:
                    content = "Thought: Để tìm thông tin iPhone 15, tôi cần tìm kiếm sản phẩm này.\nAction: search_product(\"iPhone 15\")"
                elif obs_count == 1:
                    content = "Thought: Tôi đã tìm thấy sản phẩm iPhone 15. Tôi sẽ đưa ra câu trả lời cho người dùng.\nFinal Answer: Sản phẩm iPhone 15 (ID: prod_iphone15) đang được bán với giá 1000 USD. Hiện tại cửa hàng còn 10 sản phẩm trong kho."

            # Case 2: Multi-step main query (has typo calc_ship)
            elif "iphone 15" in user_query.lower() and "winner" in user_query.lower():
                if obs_count == 0:
                    content = "Thought: Tìm kiếm sản phẩm iPhone 15.\nAction: search_product(\"iPhone 15\")"
                elif obs_count == 1:
                    content = "Thought: Kiểm tra tồn kho của iPhone 15 cho 2 sản phẩm.\nAction: check_stock(product_id=\"prod_iphone15\", quantity=2)"
                elif obs_count == 2:
                    content = "Thought: Tính phí vận chuyển. Tôi sẽ gọi tool tính ship.\nAction: calc_ship(weight=0.4, destination=\"Hà Nội\")" # Typo
                elif obs_count == 3:
                    content = "Thought: Ồ, tôi xin lỗi. Tool đúng là calc_shipping. Tôi sẽ gọi lại.\nAction: calc_shipping(weight=0.4, destination=\"Hà Nội\")"
                elif obs_count == 4:
                    content = "Thought: Áp mã giảm giá WINNER.\nAction: get_discount(coupon_code=\"WINNER\")"
                elif obs_count == 5:
                    content = "Thought: Tính toán tổng tiền. Giá gốc cho 2 sản phẩm là 2000 USD. Giảm giá 10% (200 USD), còn 1800 USD. Phí ship là 34 USD. Tổng cộng là 1834 USD.\nFinal Answer: iPhone 15 hiện còn hàng (sẵn có 10 chiếc, bạn muốn mua 2 chiếc nên đủ hàng). Tổng tiền của bạn là 1834 USD (bao gồm tiền hàng 2000 USD, giảm giá 10% từ mã WINNER là -200 USD, và phí ship đến Hà Nội là 34 USD)."

            # Case 3: Out of stock
            elif "macbook air" in user_query.lower():
                if obs_count == 0:
                    content = "Thought: Tìm kiếm sản phẩm MacBook Air.\nAction: search_product(product_name=\"MacBook Air\")"
                elif obs_count == 1:
                    content = "Thought: Kiểm tra tồn kho của MacBook Air.\nAction: check_stock(product_id=\"prod_macbookair\", quantity=1)"
                elif obs_count == 2:
                    content = "Thought: Sản phẩm đã hết hàng. Tôi thông báo cho khách hàng.\nFinal Answer: Rất tiếc, sản phẩm MacBook Air hiện tại đã hết hàng (tồn kho: 0). Bạn có thể tham khảo các sản phẩm khác nhé!"

            # Case 4: Invalid coupon
            elif "ipad pro" in user_query.lower() and "hello" in user_query.lower():
                if obs_count == 0:
                    content = "Thought: Tìm thông tin iPad Pro.\nAction: search_product(product_name=\"iPad Pro\")"
                elif obs_count == 1:
                    content = "Thought: Kiểm tra mã giảm giá HELLO.\nAction: get_discount(coupon_code=\"HELLO\")"
                elif obs_count == 2:
                    content = "Thought: Tính phí ship của iPad Pro (nặng 0.5 kg) đến Hồ Chí Minh.\nAction: calc_shipping(weight=0.5, destination=\"Hồ Chí Minh\")"
                elif obs_count == 3:
                    content = "Thought: Mã giảm giá không hợp lệ nên không được giảm. Tổng tiền = 800 (tiền hàng) + 55 (ship) = 855 USD.\nFinal Answer: iPad Pro hiện còn hàng. Mã giảm giá HELLO của bạn không hợp lệ hoặc đã hết hạn. Tổng chi phí giao đến Hồ Chí Minh là 855 USD (bao gồm 800 USD tiền hàng và 55 USD phí giao hàng)."

            # Case 5: Non-existent product
            elif "toshiba" in user_query.lower():
                if obs_count == 0:
                    content = "Thought: Tìm kiếm sản phẩm máy giặt Toshiba.\nAction: search_product(product_name=\"Toshiba\")"
                elif obs_count == 1:
                    content = "Thought: Sản phẩm không tồn tại trong danh mục.\nFinal Answer: Rất tiếc, hiện tại cửa hàng của chúng tôi không kinh doanh sản phẩm máy giặt Toshiba. Chúng tôi chỉ chuyên các sản phẩm điện tử như iPhone, iPad, MacBook."

            # Case 6: Multiple products search (has format error: missing colon)
            elif "so sánh" in user_query.lower():
                if obs_count == 0:
                    content = "Thought: Tìm thông tin iPhone 15.\nAction: search_product(product_name=\"iPhone 15\")"
                elif obs_count == 1:
                    content = "Thought: Tôi cần tìm tiếp sản phẩm iPad Pro. Tôi sẽ gọi tool.\nAction search_product(product_name=\"iPad Pro\")" # Formatting error (missing colon)
                elif obs_count == 2:
                    content = "Thought: Xin lỗi, tôi quên viết dấu hai chấm sau chữ Action. Tôi sẽ thực hiện lại.\nAction: search_product(product_name=\"iPad Pro\")"
                elif obs_count == 3:
                    content = "Thought: So sánh giá và tồn kho của cả hai.\nFinal Answer: Bảng so sánh:\n1. iPhone 15: Giá 1000 USD, Tồn kho: 10 chiếc.\n2. iPad Pro: Giá 800 USD, Tồn kho: 5 chiếc."

            # Case 7: Valid coupon with conditions
            elif "ipad pro" in user_query.lower() and "welcome" in user_query.lower():
                if obs_count == 0:
                    content = "Thought: Tìm sản phẩm iPad Pro.\nAction: search_product(product_name=\"iPad Pro\")"
                elif obs_count == 1:
                    content = "Thought: Kiểm tra mã giảm giá WELCOME.\nAction: get_discount(coupon_code=\"WELCOME\")"
                elif obs_count == 2:
                    content = "Thought: Tính phí giao hàng cho iPad Pro (0.5 kg) đến Hà Nội.\nAction: calc_shipping(weight=0.5, destination=\"Hà Nội\")"
                elif obs_count == 3:
                    content = "Thought: Kiểm tra điều kiện mã giảm giá: đơn hàng 800 USD lớn hơn 500 USD nên áp dụng giảm 15%. Tổng = 680 USD + 35 USD ship = 715 USD.\nFinal Answer: iPad Pro có giá 800 USD. Áp mã WELCOME được giảm 15% (-120 USD) do tổng chi tiêu (800 USD) lớn hơn mức tối thiểu 500 USD. Tổng chi phí của bạn giao đến Hà Nội là 715 USD (bao gồm 680 USD tiền hàng và 35 USD tiền ship)."

            # Case 8: Coupon conditions not met
            elif "airpods pro" in user_query.lower() and "welcome" in user_query.lower():
                if obs_count == 0:
                    content = "Thought: Tìm kiếm sản phẩm AirPods Pro.\nAction: search_product(product_name=\"AirPods Pro\")"
                elif obs_count == 1:
                    content = "Thought: Kiểm tra thông tin mã giảm giá WELCOME.\nAction: get_discount(coupon_code=\"WELCOME\")"
                elif obs_count == 2:
                    content = "Thought: Tổng giá trị đơn hàng là 200 USD, trong khi mã giảm giá WELCOME yêu cầu chi tiêu tối thiểu là 500 USD. Do đó, mã này không áp dụng được.\nFinal Answer: Rất tiếc, mã giảm giá WELCOME yêu cầu giá trị đơn hàng tối thiểu là 500 USD. Đơn hàng mua 1 AirPods Pro của bạn có giá 200 USD nên chưa đủ điều kiện nhận giảm giá này và không được giảm."

            usage = {"prompt_tokens": len(prompt)//4, "completion_tokens": len(content)//4, "total_tokens": (len(prompt)+len(content))//4}
            return {
                "content": content,
                "usage": usage,
                "latency_ms": 350,
                "provider": "mock"
            }

        # ----------------------------------------------------
        # MODE: AGENT V2 (Fully correct, fast, efficient)
        # ----------------------------------------------------
        else:
            time.sleep(0.15)
            content = ""
            
            # Case 1: Simple search
            if "iphone 15" in user_query.lower() and "winner" not in user_query.lower() and "so sánh" not in user_query.lower():
                if obs_count == 0:
                    content = "Thought: Tôi cần tìm kiếm sản phẩm iPhone 15 để lấy thông tin chi tiết.\nAction: search_product(product_name=\"iPhone 15\")"
                elif obs_count == 1:
                    content = "Thought: Tôi đã tìm thấy thông tin sản phẩm. Tôi sẽ trả lời khách hàng.\nFinal Answer: iPhone 15 hiện có sẵn tại cửa hàng với giá 1000 USD và còn 10 sản phẩm trong kho."

            # Case 2: Multi-step main query (no typos!)
            elif "iphone 15" in user_query.lower() and "winner" in user_query.lower():
                if obs_count == 0:
                    content = "Thought: Tìm kiếm sản phẩm iPhone 15 để lấy thông tin giá và khối lượng.\nAction: search_product(product_name=\"iPhone 15\")"
                elif obs_count == 1:
                    content = "Thought: Kiểm tra tồn kho của sản phẩm iPhone 15 cho số lượng 2.\nAction: check_stock(product_id=\"prod_iphone15\", quantity=2)"
                elif obs_count == 2:
                    content = "Thought: Tính toán phí giao hàng cho 2 sản phẩm iPhone 15 (tổng trọng lượng 2 * 0.2 = 0.4 kg) đến Hà Nội.\nAction: calc_shipping(weight=0.4, destination=\"Hà Nội\")"
                elif obs_count == 3:
                    content = "Thought: Kiểm tra thông tin mã giảm giá WINNER.\nAction: get_discount(coupon_code=\"WINNER\")"
                elif obs_count == 4:
                    content = "Thought: Áp dụng mã giảm giá 10% cho 2000 USD là 200 USD. Cộng thêm phí ship 34 USD, tổng là 1834 USD. Trả lời khách hàng.\nFinal Answer: iPhone 15 hiện còn hàng (kho còn 10 chiếc). Tổng chi phí của bạn khi mua 2 chiếc, áp mã WINNER và giao đến Hà Nội là 1834 USD (bao gồm 2000 USD tiền hàng, được giảm 200 USD và 34 USD phí vận chuyển)."

            # Case 3: Out of stock
            elif "macbook air" in user_query.lower():
                if obs_count == 0:
                    content = "Thought: Tìm kiếm sản phẩm MacBook Air.\nAction: search_product(product_name=\"MacBook Air\")"
                elif obs_count == 1:
                    content = "Thought: Kiểm tra tồn kho của MacBook Air cho số lượng 1.\nAction: check_stock(product_id=\"prod_macbookair\", quantity=1)"
                elif obs_count == 2:
                    content = "Thought: MacBook Air đã hết hàng (tồn kho 0). Trả lời khách hàng.\nFinal Answer: Rất tiếc, sản phẩm MacBook Air hiện tại đã hết hàng (tồn kho: 0). Bạn có thể tham khảo các sản phẩm khác nhé!"

            # Case 4: Invalid coupon
            elif "ipad pro" in user_query.lower() and "hello" in user_query.lower():
                if obs_count == 0:
                    content = "Thought: Tìm thông tin sản phẩm iPad Pro.\nAction: search_product(product_name=\"iPad Pro\")"
                elif obs_count == 1:
                    content = "Thought: Kiểm tra mã giảm giá HELLO.\nAction: get_discount(coupon_code=\"HELLO\")"
                elif obs_count == 2:
                    content = "Thought: Tính phí ship của iPad Pro (0.5 kg) đến Hồ Chí Minh.\nAction: calc_shipping(weight=0.5, destination=\"Hồ Chí Minh\")"
                elif obs_count == 3:
                    content = "Thought: Mã HELLO không hợp lệ. Tổng tiền = 800 USD tiền hàng + 55 USD phí ship = 855 USD.\nFinal Answer: iPad Pro hiện còn hàng. Mã giảm giá HELLO của bạn không hợp lệ hoặc đã hết hạn. Tổng chi phí giao đến Hồ Chí Minh là 855 USD (bao gồm 800 USD tiền hàng và 55 USD phí giao hàng)."

            # Case 5: Non-existent product
            elif "toshiba" in user_query.lower():
                if obs_count == 0:
                    content = "Thought: Tìm kiếm máy giặt Toshiba trong hệ thống.\nAction: search_product(product_name=\"Toshiba\")"
                elif obs_count == 1:
                    content = "Thought: Không tìm thấy sản phẩm. Trả lời khách hàng.\nFinal Answer: Rất tiếc, hiện tại cửa hàng của chúng tôi không kinh doanh sản phẩm máy giặt Toshiba. Chúng tôi chỉ chuyên các sản phẩm điện tử như iPhone, iPad, MacBook."

            # Case 6: Multiple products search
            elif "so sánh" in user_query.lower():
                if obs_count == 0:
                    content = "Thought: Tìm thông tin sản phẩm iPhone 15.\nAction: search_product(product_name=\"iPhone 15\")"
                elif obs_count == 1:
                    content = "Thought: Tìm thông tin sản phẩm iPad Pro.\nAction: search_product(product_name=\"iPad Pro\")"
                elif obs_count == 2:
                    content = "Thought: So sánh thông tin hai sản phẩm này và trả lời khách hàng.\nFinal Answer: Bảng so sánh:\n1. iPhone 15: Giá 1000 USD, Tồn kho: 10 chiếc.\n2. iPad Pro: Giá 800 USD, Tồn kho: 5 chiếc."

            # Case 7: Valid coupon with conditions
            elif "ipad pro" in user_query.lower() and "welcome" in user_query.lower():
                if obs_count == 0:
                    content = "Thought: Tìm thông tin sản phẩm iPad Pro.\nAction: search_product(product_name=\"iPad Pro\")"
                elif obs_count == 1:
                    content = "Thought: Kiểm tra mã giảm giá WELCOME.\nAction: get_discount(coupon_code=\"WELCOME\")"
                elif obs_count == 2:
                    content = "Thought: Tính phí ship của iPad Pro (0.5 kg) đến Hà Nội.\nAction: calc_shipping(weight=0.5, destination=\"Hà Nội\")"
                elif obs_count == 3:
                    content = "Thought: iPad Pro có giá 800 USD. Áp mã WELCOME được giảm 15% (-120 USD) do tổng chi tiêu (800 USD) lớn hơn mức tối thiểu 500 USD. Tổng chi phí là 680 USD + 35 USD ship = 715 USD.\nFinal Answer: iPad Pro có giá 800 USD. Áp mã WELCOME được giảm 15% (-120 USD) do tổng chi tiêu (800 USD) lớn hơn mức tối thiểu 500 USD. Tổng chi phí của bạn giao đến Hà Nội là 715 USD (bao gồm 680 USD tiền hàng và 35 USD tiền ship)."

            # Case 8: Coupon conditions not met
            elif "airpods pro" in user_query.lower() and "welcome" in user_query.lower():
                if obs_count == 0:
                    content = "Thought: Tìm kiếm sản phẩm AirPods Pro.\nAction: search_product(product_name=\"AirPods Pro\")"
                elif obs_count == 1:
                    content = "Thought: Kiểm tra mã giảm giá WELCOME.\nAction: get_discount(coupon_code=\"WELCOME\")"
                elif obs_count == 2:
                    content = "Thought: Tổng giá trị đơn hàng là 200 USD, trong khi mã giảm giá WELCOME yêu cầu chi tiêu tối thiểu là 500 USD. Do đó, mã này không áp dụng được.\nFinal Answer: Rất tiếc, mã giảm giá WELCOME yêu cầu giá trị đơn hàng tối thiểu là 500 USD. Đơn hàng mua 1 AirPods Pro của bạn có giá 200 USD nên chưa đủ điều kiện nhận giảm giá này và không được giảm."

            usage = {"prompt_tokens": len(prompt)//4, "completion_tokens": len(content)//4, "total_tokens": (len(prompt)+len(content))//4}
            return {
                "content": content,
                "usage": usage,
                "latency_ms": 180,
                "provider": "mock"
            }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        res = self.generate(prompt, system_prompt)
        yield res["content"]
