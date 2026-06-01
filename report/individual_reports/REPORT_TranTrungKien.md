# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Tran Trung Kien
- **Student ID**: 2A202600850
- **Date**: 1/6/2026

---

## I. Technical Contribution (15 Points)

Trong dự án này, tôi chịu trách nhiệm chính về phần thiết kế và chuẩn hóa hệ thống công cụ (Tool Design) cho ReAct Agent. Mục tiêu của tôi là đảm bảo Agent có đủ công cụ để tương tác với dữ liệu bán lẻ và các công cụ được định nghĩa rõ ràng để tránh bị "hallucination" khi gọi.

- **Modules Implemented**: `src/tools/retail_tools.py`
- **Code Highlights**:
  Tôi đã triển khai và quy chuẩn hóa các hàm xử lý logic nghiệp vụ thành các công cụ cho Agent, bao gồm: `search_product`, `check_stock`, `get_discount`, và `calc_shipping`.
  Ví dụ về việc quy chuẩn hóa đầu ra để Agent dễ tiếp nhận (Observation):
  ```python
  def check_stock(product_id: str, quantity: int = 1):
      # ... logic xử lý ...
      # Trả về dictionary có cấu trúc thay vì plain text để parser của Agent dễ đọc hơn
      if p["stock"] >= quantity:
          return {"in_stock": True, "available": p["stock"], "price": p["price"]}
      else:
          return {"in_stock": False, "message": f"Only {p['stock']} items available"}
  ```
- **Documentation**: Tôi thiết kế mảng `RETAIL_TOOLS` chứa docstring và cấu trúc JSON giả lập để Agent hiểu rõ ràng định dạng tham số đầu vào. Việc định nghĩa rõ `"Input JSON: {\"product_id\": string}"` giúp giảm thiểu lỗi cú pháp khi Agent sinh ra bước `Action Input`.

---

## II. Debugging Case Study (10 Points)

- **Problem Description**: Trong những phiên bản đầu tiên của Agent, hệ thống thường xuyên bị lỗi dừng đột ngột (Crash) khi khách hàng hỏi về phí vận chuyển. Agent cố gắng gọi tool `calc_shipping` nhưng liên tục truyền sai kiểu dữ liệu cho tham số `weight_kg`.
- **Log Source**: *(Trích xuất từ log hệ thống giám sát nội bộ)*
  ```
  [ERROR] Tool Execution Failed: calc_shipping
  Action: calc_shipping
  Action Input: {"weight_kg": "2 kilograms", "destination": "Hanoi"}
  Error: TypeError - unsupported operand type(s) for *: 'float' and 'str'
  ```
- **Diagnosis**: 
  Khi phân tích log, tôi nhận thấy LLM đã sinh ra giá trị string `"2 kilograms"` thay vì kiểu float `2.0`. Nguyên nhân cốt lõi là do mô tả (description) ban đầu của tool chỉ ghi chung chung là `Input: weight_kg and destination`. LLM không hiểu rõ định dạng chính xác nên tự động thêm chữ "kilograms" theo thói quen ngôn ngữ tự nhiên, dẫn đến lỗi hàm Python không thể nhân số nguyên với chuỗi string.
- **Solution**: 
  Tôi đã sửa lại phần mô tả của tool trong `RETAIL_TOOLS` để ép buộc LLM phải tuân thủ nghiêm ngặt kiểu dữ liệu. Sửa mô tả thành: 
  `"description": "Calculate shipping costs. Input MUST be valid JSON: {'weight_kg': float (ONLY numbers, no text), 'destination': string}"`. 
  Sau khi cập nhật mô tả này, Agent đã luôn truyền đúng số thực (ví dụ: `2.0`) và lỗi này hoàn toàn biến mất.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1.  **Reasoning**: Khối `Thought` thực sự là "game-changer". So với Chatbot thông thường (chỉ đoán câu trả lời dựa trên trọng số xác suất), khối `Thought` ép LLM phải chia nhỏ vấn đề (Chain-of-Thought). Ví dụ: Thay vì báo giá ngay một cách vô căn cứ, Agent tự nhận thức được: "Mình cần tìm ID sản phẩm trước -> sau đó kiểm tra tồn kho -> rồi mới tính tổng tiền".
2.  **Reliability**: Mặc dù Agent thông minh hơn, nhưng đôi khi nó hoạt động tệ hơn Chatbot ở độ trễ (latency). Chatbot trả lời ngay lập tức, trong khi Agent có thể tốn 3-4 vòng lặp (vài chục giây) để gọi các tool chỉ để trả lời một câu hỏi đơn giản. Nếu parser của Agent không tốt, nó có thể rơi vào vòng lặp vô hạn (Infinite Loop).
3.  **Observation**: Phản hồi từ môi trường là mấu chốt để "sửa sai". Khi Agent tìm một mã giảm giá bị hết hạn, tool trả về `{"valid": False}`. Dựa vào `Observation` đó, Agent ngay lập tức thay đổi hành vi và tạo ra khối `Thought` mới: "Mã này đã hết hạn, mình cần thông báo cho khách hàng biết" thay vì tiếp tục tính toán sai lầm.

---

## IV. Future Improvements (5 Points)

Để mở rộng hệ thống này thành một ứng dụng AI cấp độ Production:

- **Scalability**: Thay vì nạp toàn bộ danh sách tools (nếu có hàng trăm tools) vào system prompt làm tốn token và gây nhầm lẫn cho LLM, tôi sẽ sử dụng **Vector Database** (như ChromaDB hoặc Pinecone) để truy xuất các công cụ (Tool Retrieval). Chỉ những tools liên quan đến ngữ cảnh câu hỏi hiện tại mới được nhúng vào prompt.
- **Safety**: Cần bổ sung thêm một **Output Guardrail** hoặc một "Supervisor Agent" nhỏ đứng chặn trước khi gửi tin nhắn cho người dùng cuối. Supervisor này sẽ kiểm tra xem phản hồi có bịa đặt thông tin (hallucination) về giá cả không có trong cơ sở dữ liệu hay không.
