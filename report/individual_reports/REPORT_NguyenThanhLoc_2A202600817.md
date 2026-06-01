# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: [Điền họ tên của bạn]
- **Student ID**: [Điền mã sinh viên của bạn]
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

Trong phần lab này, em phụ trách hoàn thiện luồng chạy local model Phi-3, xây dựng chatbot baseline không dùng tool, chuẩn bị script so sánh chatbot với ReAct agent, và thêm giao diện xem log phục vụ demo.

- **Modules Implemented**:
  - `src/core/local_provider.py`: Cấu hình provider chạy Phi-3 local qua GGUF, dùng prompt format của Phi-3 và xử lý lỗi native `llama-cpp-python` rõ ràng hơn.
  - `tests/test_local.py`: Script kiểm tra Phi-3 local bằng lệnh `python tests\test_local.py`, đồng thời sửa lỗi hiển thị Unicode trên Windows console.
  - `chatbot_baseline.py`: Chatbot baseline nhận input từ người dùng, gọi Phi-3 trực tiếp, không dùng tool và không dùng ReAct loop.
  - `compare_chatbot_agent.py`: Script chạy so sánh ban đầu giữa chatbot baseline và agent, lưu kết quả vào `logs/baseline_vs_agent.json`.
  - `log_viewer.html`: Giao diện demo đơn giản để chọn file log/json và xem số dòng, loại event, pass rate và chi tiết từng record.
  - `src/agent/agent.py`: Hoàn thiện vòng lặp ReAct cơ bản: đọc `Thought/Action`, parse tool call, chạy tool, thêm `Observation`, và dừng khi có `Final Answer`.

- **Code Highlights**:
  - `LocalProvider` sử dụng `_format_prompt()` để đóng gói prompt theo dạng:
    ```text
    <|system|>
    ...
    <|end|>
    <|user|>
    ...
    <|end|>
    <|assistant|>
    ```
  - `chatbot_baseline.py` cố tình không truyền danh sách tool cho model. Điều này giúp tạo baseline đúng nghĩa: model trả lời trực tiếp dựa trên kiến thức nội tại, nên dễ sai với các câu hỏi cần dữ liệu tồn kho, mã giảm giá hoặc phí vận chuyển.
  - `compare_chatbot_agent.py` tạo cùng một bộ test cho hai mode. Kết quả mock ban đầu:
    ```text
    chatbot: 2/10 passed
    agent: 10/10 passed
    ```

- **Documentation**:
  - Đã cập nhật `README.md` với các lệnh chạy:
    ```bash
    python tests\test_local.py
    python chatbot_baseline.py
    python compare_chatbot_agent.py mock
    ```
  - README cũng ghi chú cách xử lý lỗi `access violation reading 0x0000000000000000` bằng cách pin `llama-cpp-python==0.2.90`, vì phiên bản 0.3.x bị lỗi native DLL trên môi trường Windows/Python 3.13 hiện tại.

---

## II. Debugging Case Study (10 Points)

- **Problem Description**:
  Khi chạy local provider với Phi-3 bằng lệnh:
  ```bash
  python tests\test_local.py
  ```
  chương trình bị lỗi:
  ```text
  exception: access violation reading 0x0000000000000000
  ```
  Lỗi xảy ra ngay tại bước khởi tạo backend `llama.cpp`, trước khi model thực sự sinh câu trả lời.

- **Log Source**:
  Output kiểm thử sau khi xử lý:
  ```text
  --- Testing Local Provider with Phi-3 ---
  Model Path: ./models/Phi-3-mini-4k-instruct-q4.gguf

  User: Explain what an AI Agent is in one sentence.
  Assistant: An AI Agent is a system capable of perceiving its environment, analyzing information, making decisions, and taking actions to achieve specific goals autonomously.

  OK: Local Provider is working correctly!
  ```

- **Diagnosis**:
  Lỗi không nằm ở prompt, ReAct loop hay file model GGUF, vì crash xảy ra tại native backend init của `llama-cpp-python`. Trên máy Windows/Python 3.13, bản `llama-cpp-python` 0.3.x gây lỗi access violation. Sau khi thử lại với CPU wheel cũ hơn, bản `0.2.90` chạy ổn định.

- **Solution**:
  - Pin dependency trong `requirements.txt`:
    ```text
    llama-cpp-python==0.2.90
    ```
  - Cập nhật `LocalProvider` để bắt `OSError` và in hướng dẫn sửa lỗi rõ ràng.
  - Sửa `tests/test_local.py` để không bị lỗi Unicode console che mất lỗi thật.
  - Kiểm tra lại bằng `python tests\test_local.py` và xác nhận Phi-3 chạy local thành công.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1. **Reasoning**:
   `Thought` giúp agent chia bài toán thành từng bước nhỏ. Với câu hỏi "mua 2 iPhone 15, dùng mã WINNER, giao đến Hà Nội", agent có thể lần lượt tìm sản phẩm, kiểm tra tồn kho, tính shipping, kiểm tra coupon, rồi tổng hợp kết quả. Chatbot baseline chỉ trả lời một lần nên dễ đoán sai phí ship hoặc tình trạng kho.

2. **Reliability**:
   Agent có thể kém chatbot nếu parser bắt sai `Action`, model gọi nhầm tên tool, hoặc vòng lặp không dừng. Khi đó agent tốn nhiều token hơn và có thể trả lời chậm hơn. Tuy nhiên, khi tool spec rõ ràng và parser ổn định, agent đáng tin cậy hơn vì có dữ liệu quan sát từ môi trường.

3. **Observation**:
   `Observation` là phần phản hồi thực tế sau khi gọi tool. Nó giúp agent điều chỉnh suy luận thay vì tiếp tục đoán. Ví dụ, nếu `check_stock` trả về tồn kho `0`, agent phải kết luận hết hàng. Nếu `get_discount` trả về mã không hợp lệ, agent không được tự áp mã giảm giá vào tổng tiền.

---

## IV. Future Improvements (5 Points)

- **Scalability**:
  Tách tool execution thành lớp riêng và hỗ trợ gọi tool bất đồng bộ. Với các truy vấn so sánh nhiều sản phẩm, agent có thể tìm nhiều sản phẩm song song để giảm latency.

- **Safety**:
  Thêm lớp kiểm tra input và output để chặn prompt injection, lọc câu hỏi ngoài phạm vi retail/e-commerce, và xác thực tham số tool trước khi thực thi.

- **Performance**:
  Cache kết quả các tool ít thay đổi như danh sách sản phẩm, bảng phí vận chuyển, hoặc coupon. Với nhiều tool hơn, có thể dùng tool retrieval để chỉ đưa các tool liên quan vào system prompt thay vì nhồi toàn bộ danh sách tool vào context.

---

> [!NOTE]
> Trước khi nộp, đổi tên file nếu cần theo format `REPORT_[YOUR_NAME].md` và thay thông tin họ tên/MSSV ở đầu file.
