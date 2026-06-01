# Guideline Lab 3 - Nhom 5 Nguoi

## 1. Chu De

**Retail/E-commerce: Tro ly ban hang thong minh cho cua hang dien tu**

Muc tieu demo: so sanh **Chatbot Baseline dung Phi-3** voi **ReAct Agent dung Phi-3**, trong do Agent biet goi tool, kiem tra ton kho, ap ma giam gia, tinh phi ship va hien thi log tung buoc.

Demo chinh:

```text
Toi muon mua 2 iPhone 15, dung ma WINNER, giao den Ha Noi. Tong tien la bao nhieu va con hang khong?
```

## 2. Kien Truc Tong Quan

```text
User nhap cau hoi
        |
        v
UX Demo
        |
        +--> Chatbot Baseline dung Phi-3 tra loi truc tiep
        |
        +--> ReAct Agent dung Phi-3
                 |
                 v
          Agent phan tich Thought / Action
                 |
                 v
          Goi tools trong src/tools/
                 |
                 v
          Tools doc mock data trong src/data/
                 |
                 v
          Tra Observation ve Agent
                 |
                 v
          Agent tra Final Answer
                 |
                 v
          UX hien thi answer + log
```

## 3. Phan Cong Cho Nhom 5 Nguoi

## Nguoi 1: Data + Tools

### Muc tieu

Tao du lieu gia va cac tool de Agent goi.

### File can tao

```text
src/data/products.json
src/data/coupons.json
src/data/shipping_rules.json
src/tools/__init__.py
src/tools/retail_tools.py
```

### Dau viec

1. Tao `products.json`
   - Chua san pham: `id`, `name`, `category`, `price`, `stock`, `weight_kg`.
   - Nen co ca san pham con hang va het hang.

2. Tao `coupons.json`
   - Chua ma giam gia: `code`, `discount_percent`, `min_order_value`, `active`.
   - Co ma hop le nhu `WINNER`, ma het han nhu `EXPIRED`.

3. Tao `shipping_rules.json`
   - Chua phi ship theo thanh pho.
   - Vi du: `Hanoi`, `Ho Chi Minh City`, `Da Nang`.

4. Implement tools trong `retail_tools.py`
   - `search_product(product_name)`
   - `check_stock(product_id, quantity)`
   - `get_discount(coupon_code, order_value)`
   - `calc_shipping(weight_kg, destination)`

5. Tao danh sach tool definitions de Agent dung:

```python
RETAIL_TOOLS = [
    {
        "name": "search_product",
        "description": "Search product by product name. Input JSON: {\"product_name\": string}.",
        "function": search_product,
    },
]
```

### Noi voi ai

- Nguoi 2 dung `RETAIL_TOOLS` de Agent goi tool.
- Nguoi 4 dung output cua tool de hien thi log.
- Nguoi 5 dung data nay de viet test cases.

## Nguoi 2: ReAct Agent Core

### Muc tieu

Hoan thien Agent chinh.

### File can sua/tao

```text
src/agent/agent.py
src/agent/parser.py
```

### Dau viec

1. Hoan thien `get_system_prompt()`
   - Liet ke tool name va description.
   - Bat Phi-3 tra format co dinh:

```text
Thought: ...
Action: tool_name({"key": "value"})
```

hoac:

```text
Final Answer: ...
```

2. Hoan thien `run(user_input)`
   - Gui prompt vao Phi-3.
   - Nhan response.
   - Neu co `Final Answer` thi dung.
   - Neu co `Action` thi parse tool name va arguments.
   - Goi `_execute_tool()`.
   - Lay ket qua tool lam `Observation`.
   - Gan observation vao prompt vong tiep theo.

3. Hoan thien `_execute_tool(tool_name, args)`
   - Tim tool trong `self.tools`.
   - Parse args JSON.
   - Goi function tuong ung.
   - Tra ket qua dang string hoac dict.

4. Them logging
   - `AGENT_START`
   - `AGENT_STEP`
   - `TOOL_CALL`
   - `TOOL_RESULT`
   - `AGENT_END`
   - `AGENT_ERROR`

5. Chong loi
   - Sai JSON action.
   - Tool khong ton tai.
   - Thieu argument.
   - Qua `max_steps`.

### Noi voi ai

- Nhan `RETAIL_TOOLS` tu Nguoi 1.
- Nhan Phi-3 provider tu Nguoi 3.
- Tra response/log cho Nguoi 4.
- Tao log de Nguoi 5 phan tich.

## Nguoi 3: Phi-3 Setup + Chatbot Baseline

### Muc tieu

Chay model local va tao chatbot thuong de so sanh voi Agent.

### File can tao/sua

```text
.env
src/chatbot.py
src/run_demo.py
```

### Dau viec

1. Tai model:

```text
Phi-3-mini-4k-instruct-q4.gguf
```

Dat vao:

```text
models/Phi-3-mini-4k-instruct-q4.gguf
```

2. Tao `.env` tu `.env.example`

Cau hinh:

```env
DEFAULT_PROVIDER=local
LOCAL_MODEL_PATH=./models/Phi-3-mini-4k-instruct-q4.gguf
```

3. Test model:

```powershell
python tests\test_local.py
```

4. Tao `src/chatbot.py`
   - Chatbot baseline chi goi Phi-3 truc tiep.
   - Khong dung tool.
   - Dung de chung minh chatbot de bia gia, ton kho, phi ship.

5. Tao `src/run_demo.py`
   - Load Phi-3 provider.
   - Load chatbot baseline.
   - Load ReAct Agent.
   - Load `RETAIL_TOOLS`.
   - Cho phep chay thu tu terminal.

Vi du nhiem vu cua `run_demo.py`:

```python
provider = LocalProvider(model_path)
agent = ReActAgent(llm=provider, tools=RETAIL_TOOLS)

print(chatbot_answer(question))
print(agent.run(question))
```

### Noi voi ai

- Cung cap provider Phi-3 cho Nguoi 2.
- Cung cap mode baseline cho Nguoi 4.
- Cung cap output so sanh cho Nguoi 5.

## Nguoi 4: UX Demo + Log Viewer

### Muc tieu

Tao giao dien demo co chat va log.

### File can tao

Goi y dung Streamlit de lam nhanh:

```text
src/app.py
```

Neu dung Streamlit, them vao `requirements.txt`:

```text
streamlit
```

### Dau viec

1. Lam UI co:
   - O nhap cau hoi.
   - Nut gui.
   - Nut reset.
   - Chon mode:
     - `Chatbot Baseline`
     - `ReAct Agent v1`
     - `ReAct Agent v2`

2. Co nut chon nhanh scenario:
   - Tu van san pham.
   - Kiem tra ton kho.
   - Ap ma giam gia.
   - Tinh tong don hang.

3. Hien thi phan chat:
   - User message.
   - Assistant answer.

4. Hien thi log panel:
   - Step number.
   - Thought.
   - Action.
   - Tool input.
   - Observation.
   - Final Answer.
   - Latency neu co.

5. Doc log tu:

```text
logs/YYYY-MM-DD.log
```

hoac nhan trace truc tiep tu Agent neu Nguoi 2 tra them structured trace.

### Noi voi ai

- Goi `src/chatbot.py` cua Nguoi 3 khi chon baseline.
- Goi `ReActAgent` cua Nguoi 2 khi chon agent.
- Agent dung tools cua Nguoi 1.
- Log tu UX duoc Nguoi 5 dung trong report/demo.

## Nguoi 5: Evaluation + Report + Presentation

### Muc tieu

Do ket qua, phan tich loi, hoan thien bao cao.

### File can tao

```text
tests/test_retail_agent.py
report/group_report/GROUP_REPORT_<TEAM_NAME>.md
report/individual_reports/REPORT_<NAME>.md
```

Co the tao them:

```text
src/evaluate_lab.py
```

### Dau viec

1. Tao bo test 8-12 cau hoi.

Vi du:

```text
iPhone 15 con hang khong?
Toi mua 2 iPhone 15 dung ma WINNER giao Ha Noi, tong bao nhieu?
Toi mua AirPods Pro, con hang khong?
Ma EXPIRED co dung duoc khong?
Giao den Nha Trang phi bao nhieu?
```

2. Chay tung case voi:
   - Chatbot baseline.
   - Agent v1.
   - Agent v2.

3. Ghi bang ket qua:
   - Dung/sai.
   - So buoc Agent da chay.
   - Co goi dung tool khong.
   - Latency.
   - Loi neu co.

4. Phan tich failure tu log:
   - Phi-3 sai format action.
   - Agent goi nham tool.
   - Agent thieu argument.
   - Agent loop qua nhieu buoc.
   - Coupon/tool tra loi.

5. Viet group report theo template:

```text
report/group_report/TEMPLATE_GROUP_REPORT.md
```

6. Nhac tung nguoi viet individual report theo:

```text
report/individual_reports/TEMPLATE_INDIVIDUAL_REPORT.md
```

### Noi voi ai

- Lay test case tu data cua Nguoi 1.
- Lay log tu Agent cua Nguoi 2.
- Lay baseline tu Nguoi 3.
- Lay anh/demo flow tu Nguoi 4.
- Tong hop thanh bao cao cuoi.

## 4. Thu Tu Lam Viec De Xuat

1. Nguoi 1 tao data va tools truoc.
2. Nguoi 3 setup Phi-3 song song.
3. Nguoi 2 noi Phi-3 + tools vao ReAct Agent.
4. Nguoi 3 tao chatbot baseline.
5. Nguoi 4 lam UX goi duoc baseline va Agent.
6. Nguoi 5 tao test cases, chay thu, ghi log.
7. Ca nhom xem failure trace.
8. Nguoi 2 + Nguoi 3 cai tien Agent v2.
9. Nguoi 5 hoan thien report.
10. Nguoi 4 chuan bi demo live.

## 5. Cac File Quan Trong Cuoi Cung

```text
src/data/products.json
src/data/coupons.json
src/data/shipping_rules.json

src/tools/__init__.py
src/tools/retail_tools.py

src/agent/agent.py
src/agent/parser.py

src/chatbot.py
src/run_demo.py
src/app.py

src/evaluate_lab.py
tests/test_retail_agent.py

logs/YYYY-MM-DD.log

report/group_report/GROUP_REPORT_<TEAM_NAME>.md
report/individual_reports/REPORT_<NAME>.md
```

## 6. Phan Cong Gon Theo San Pham Ban Giao

| Nguoi | San pham chinh |
|---|---|
| Nguoi 1 | Data JSON + retail tools |
| Nguoi 2 | ReAct Agent + parser + tool execution |
| Nguoi 3 | Phi-3 local + chatbot baseline + run demo |
| Nguoi 4 | UX chat + log viewer |
| Nguoi 5 | Test cases + metrics + report + presentation |

## 7. Diem Mau Chot Khi Demo

- Chatbot thuong co the bia ton kho, gia hoac phi ship.
- ReAct Agent khong tu doan ma goi tool.
- Phi-3 local nho hon model cloud nen de sai format, nhung co the cai thien bang prompt v2, tool spec ro va parser tot hon.
- Log la bang chung quan trong nhat de debug va cai tien Agent.
