# Báo cáo Cá nhân: Bài Thực Hành 3 - Chatbot vs Tác tử ReAct

- **Họ và Tên Sinh viên**: Đặng Tiến Quyến (Trưởng nhóm Đánh giá & Đo lường)
- **Mã Sinh viên**: 2S202600896
- **Ngày thực hiện**: 2026-06-01

---

## I. Đóng góp Kỹ thuật (15 Điểm)

*Mô tả đóng góp cụ thể của bạn cho mã nguồn (ví dụ: đã triển khai một công cụ cụ thể, sửa lỗi bộ phân tích cú pháp (parser), v.v.).*

- **Các Module Đã triển khai**: 
  - `tests/test_suite.py`: Thiết kế 10 tình huống kiểm thử toàn diện, bao gồm các lượt tìm kiếm đơn giản, logic xử lý đa bước về giảm giá/vận chuyển, cạn kiệt hàng hóa, lỗi phân tích cú pháp, và rào chắn chống tiêm prompt.
  - `tests/run_evaluation.py`: Triển khai trình chạy đánh giá tự động kiểm thử tất cả các thiết lập, thu thập log, tổng hợp số liệu hiệu năng (độ trễ, lượng token, số bước lặp) và xuất báo cáo.
- **Điểm nhấn Mã nguồn**:
  - `run_evaluation.py`: Đóng gói quy trình thực thi tác tử ReAct, đặt lại các biến đo lường (telemetry), tính toán tổng thời gian vòng lặp và đếm số bước đã hoàn thành.
  - `test_suite.py`: Thiết lập các mảng từ khóa để xác thực kết quả tự động.
- **Tài liệu**: 
  Khung đánh giá thực thi vòng lặp tác tử trên mỗi tình huống kiểm thử. Khi tác tử gọi các bước, lớp nhà cung cấp (provider) cập nhật và ghi nhận lượng token và độ trễ, lưu các log thông qua lớp `IndustryLogger`.

---

## II. Case Study Xử lý Lỗi (Debugging) (10 Điểm)

*Phân tích một sự kiện lỗi cụ thể mà bạn gặp phải trong quá trình làm bài thực hành thông qua hệ thống log.*

- **Mô tả Vấn đề**: 
  Trong Tác tử v1, khi thực thi Tình huống 2 (Mua 2 iPhone 15 + Mã WINNER + Giao Hà Nội), tác tử đã gặp phải ảo giác và tạo ra một công cụ tên là `calc_ship` thay vì đúng tên là `calc_shipping`, dẫn đến một ngoại lệ khi thực thi (execution exception).
- **Nguồn Log**: 
  Dấu vết ghi lại từ lượt chạy kiểm thử:
  ```json
  {"timestamp": "2026-06-01T05:56:41.830111", "event": "TOOL_CALL", "data": {"step": 3, "tool": "calc_ship", "args": "weight=0.4, destination=\"Hà Nội\""}}
  {"timestamp": "2026-06-01T05:56:41.831200", "event": "AGENT_ERROR", "data": {"step": 3, "error": "Error: Tool 'calc_ship' not found. Available tools: search_product, check_stock, get_discount, calc_shipping"}}
  ```
- **Chẩn đoán**: 
  System prompt (hướng dẫn hệ thống) dành cho Tác tử v1 mô tả công cụ tính phí vận chuyển theo văn bản thường mà không đưa ra chữ ký hàm cụ thể. Mô hình ngôn ngữ nhỏ (Phi-3) đã tự suy đoán và rút gọn tên công cụ thành `calc_ship` theo ngôn ngữ tự nhiên.
- **Giải pháp**: 
  Cập nhật cấu hình prompt trong `agent.py` để quy định chính xác các chữ ký hàm (`calc_shipping(weight: float, destination: str)`) và thêm một vài ví dụ mẫu cách gọi hàm đúng. Điều này đã giải quyết triệt để lỗi đánh máy trong Tác tử v2, làm giảm số bước cần thiết của Tình huống 2 từ 6 xuống còn 5.

---

## III. Quan điểm Cá nhân: Chatbot so với ReAct (10 Điểm)

*Đánh giá sự khác biệt về năng lực suy luận.*

1.  **Sự suy luận**: Khối `Thought` đóng vai trò như một giấy nháp, cho phép mô hình tính toán các trạng thái trung gian (ví dụ: cộng trọng lượng, so sánh với điều kiện mã giảm giá). Chatbot cơ sở cố gắng dự đoán mức giá cuối cùng chỉ trong một lần chạy, dẫn đến hiện tượng ảo giác (hallucination).
2.  **Độ tin cậy**: Tác tử ReAct có thể biểu hiện tệ hơn chatbot đơn giản khi chúng bị mắc kẹt ở lỗi định dạng/phân tích cú pháp hoặc trong vòng lặp vô hạn. Khi đó, tác tử sẽ tiêu tốn hàng ngàn token mà không mang lại kết quả, còn chatbot chí ít cũng đáp lại một câu theo kiểu trò chuyện.
3.  **Quan sát (Observation)**: Quan sát là yếu tố đại diện cho thực tế ("ground truth") trong chu trình ReAct. Khi một công cụ trả về `{"status": "error", "message": "Coupon expired"}`, hệ thống buộc tác tử phải điều chỉnh quy trình suy luận (ví dụ: chuyển sang việc bỏ mã giảm giá và báo lại cho khách hàng) thay vì giả định rằng mã giảm giá đã thành công.

---

## IV. Đề xuất Cải tiến Tương lai (5 Điểm)

*Làm cách nào bạn có thể mở rộng hệ thống này để thành một sản phẩm tác tử AI thực thụ?*

- **Khả năng Mở rộng (Scalability)**: Triển khai việc gọi các công cụ song song một cách độc lập. Ví dụ, nếu người dùng muốn so sánh hai sản phẩm, tác tử có thể gọi lệnh `search_product` cho cả hai cùng một lúc qua asyncio để giảm thiểu thời gian chờ.
- **Bảo mật (Safety)**: Tích hợp cấu trúc "Hai Lớp Rào Chắn", trong đó một bộ phân loại tốc độ cao (fast classifier) kiểm tra cả đầu vào của người dùng (chống tiêm prompt) và cả tham số công cụ do tác tử tạo ra (ngăn chặn SQL injection hoặc sửa đổi tham số ác ý) trước khi thực thi bất kỳ logic Python nào.
- **Hiệu năng (Performance)**: Áp dụng định tuyến công cụ theo ngữ nghĩa. Khi hệ thống tác tử được nâng cấp với hàng trăm công cụ hỗ trợ văn phòng, việc đưa toàn bộ đặc tả vào system prompt sẽ quá giới hạn context. Một cơ sở dữ liệu vector có thể lấy ra 5 mô tả công cụ phù hợp nhất dựa trên nội dung phần `Thought` hiện tại.
