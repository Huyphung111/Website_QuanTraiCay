# 🍊 Bích Trái Cây — Web bảng giá trái cây

Web xem **bảng giá trái cây** cho quán *Bích Trái Cây*.
Mục đích: giúp **admin** nhớ giá đã nhập, và để **khách** xem quán đang có những trái cây gì.

> ⚠️ Đây **không** phải web bán hàng — không có giỏ hàng, không thanh toán.

---

## ✨ Tính năng

- **Khách (ai cũng xem được):** chỉ XEM danh sách trái cây — tên, giá, ảnh, xuất xứ, trạng thái, thời gian cập nhật.
- **🔍 Tìm kiếm:** thanh tìm kiếm lọc nhanh theo **tên** hoặc **xuất xứ** (cho cả khách lẫn admin).
- **Trạng thái trái cây:** **Còn bán** (nhãn xanh) hoặc **Hết hàng** — khi hết hàng, ảnh bị **làm xám** và hiện chữ đỏ **"HẾT HÀNG"**.
- **Admin (cần đăng nhập):** bấm nút **🔑 Truy cập** ở góc phải, nhập tài khoản + mật khẩu để:
  - ➕ **Thêm** trái cây (tên, giá VND, đơn vị, **xuất xứ chọn từ 34 tỉnh/thành**, trạng thái, **tải ảnh lên**)
  - ✏️ **Sửa** trái cây
  - 🗑️ **Xóa** trái cây
- **Xuất xứ** là **danh sách chọn** lấy từ file `data/tinh_thanh_viet_nam_34*.md` (34 tỉnh/thành sau sáp nhập 2025) + tùy chọn **"Nhập khẩu"**.
- Giao diện giữ đúng thiết kế mẫu `bich-trai-cay.html` (tông vàng).
- Ảnh đại diện quán lấy từ ảnh trong thư mục `src` (mít).

---

## ▶️ Cách chạy

### Cách 1 — Đơn giản nhất (Windows)
Nhấp đúp vào file **`run.bat`**. Lần đầu nó sẽ tự cài Flask.
Sau đó mở trình duyệt vào: **http://127.0.0.1:5000**

### Cách 2 — Bằng dòng lệnh
```bash
pip install -r requirements.txt
python app.py
```
Rồi mở: **http://127.0.0.1:5000**

Tắt web: bấm `Ctrl + C` trong cửa sổ đang chạy.

---

## 🔐 Tài khoản admin

Có sẵn **2 tài khoản** (đều quyền admin):

| Tài khoản | Mật khẩu |
|-----------|----------|
| `admin` | `bich123` |
| `bichtraicay` | `123456` |

> 🔴 **Nên đổi mật khẩu** trước khi dùng thật. Có 2 cách:
>
> **a) Sửa trực tiếp** trong file `app.py` (phần `ADMIN_USERS` — thêm/sửa tài khoản tại đây).
>
> **b) Dùng biến môi trường** (không cần sửa code), ví dụ trên Windows:
> ```bat
> set BICH_ADMIN_USER=tendangnhap
> set BICH_ADMIN_PASS=matkhaumoi
> python app.py
> ```

---

## 📁 Cấu trúc thư mục

```
QuanTraiCayBich/
├── app.py                 # Mã nguồn web (Flask)
├── run.bat                # Nhấp đúp để chạy (Windows)
├── requirements.txt       # Thư viện cần cài (Flask)
├── bich-trai-cay.html     # Bản thiết kế mẫu gốc (giữ lại tham khảo)
├── data/
│   └── fruits.db          # Cơ sở dữ liệu (tự tạo, lưu trái cây)
├── static/
│   ├── style.css          # Giao diện
│   ├── app.js             # Xử lý đăng nhập + thêm/sửa/xóa
│   ├── img/logo.png       # Ảnh đại diện quán
│   └── uploads/           # Ảnh trái cây admin tải lên
├── templates/
│   └── index.html         # Trang web chính
└── src/                   # Ảnh gốc của bạn
```

---

## ❓ Một vài lưu ý

- Dữ liệu trái cây lưu trong `data/fruits.db`. Muốn **làm lại từ đầu** (về 12 trái cây mẫu): xóa file `data/fruits.db` rồi chạy lại.
- Ảnh tải lên lưu trong `static/uploads/`. Định dạng cho phép: png, jpg, jpeg, gif, webp (tối đa 8MB/ảnh).
- Web chạy ở chế độ máy chủ phát triển (development). Dùng nội bộ là đủ.
- Muốn người khác trong cùng mạng wifi xem được: họ vào `http://<địa-chỉ-IP-máy-bạn>:5000`.
# Website_QuanTraiCay
