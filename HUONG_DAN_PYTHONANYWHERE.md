# 🚀 Hướng dẫn đưa web lên PythonAnywhere (từng bước)

> Quy ước: trong hướng dẫn này tôi dùng `tentaikhoan` = tên tài khoản PythonAnywhere của bạn,
> và `Website_QuanTraiCay` = tên thư mục dự án (đổi theo đúng tên repo GitHub của bạn).

---

## Bước 0 — Đẩy code lên GitHub (nếu chưa)

Trên máy bạn, trong thư mục dự án:
```bash
git init
git add .
git commit -m "Web bang gia Bich Trai Cay"
git branch -M main
git remote add origin https://github.com/<ten-github>/Website_QuanTraiCay.git
git push -u origin main
```
> File `.gitignore` đã được tạo sẵn để **không** đẩy database và ảnh test lên GitHub.

---

## Bước 1 — Tạo tài khoản PythonAnywhere

1. Vào **https://www.pythonanywhere.com** → bấm **Pricing & signup** → chọn gói **"Create a Beginner account"** (miễn phí).
2. Đăng ký, xác nhận email, đăng nhập.

---

## Bước 2 — Tải code về server bằng Git

1. Ở thanh menu trên cùng, vào **Consoles** → bấm **Bash** để mở một cửa sổ dòng lệnh.
2. Gõ lệnh tải code về (đổi link thành repo của bạn):
   ```bash
   git clone https://github.com/<ten-github>/Website_QuanTraiCay.git
   ```
3. Vào thư mục và xem đường dẫn đầy đủ (ghi nhớ để dùng ở bước sau):
   ```bash
   cd Website_QuanTraiCay
   pwd
   ```
   Kết quả `pwd` sẽ giống: `/home/tentaikhoan/Website_QuanTraiCay`

---

## Bước 3 — Tạo môi trường ảo & cài Flask

Vẫn trong cửa sổ Bash đó, gõ lần lượt:
```bash
mkvirtualenv --python=/usr/bin/python3.10 bichenv
pip install -r requirements.txt
```
> Sau lệnh đầu, đầu dòng lệnh sẽ có chữ `(bichenv)` — nghĩa là đang ở trong môi trường ảo.
> Nếu lỡ đóng cửa sổ, bật lại bằng: `workon bichenv`

---

## Bước 4 — Tạo Web app

1. Lên menu trên cùng → vào tab **Web** → bấm **Add a new web app** → **Next**.
2. Chọn **Manual configuration** (KHÔNG chọn "Flask") → **Next**.
3. Chọn **Python 3.10** → **Next**. Xong, nó tạo một web app trống.

---

## Bước 5 — Cấu hình đường dẫn & môi trường ảo

Vẫn ở tab **Web**, kéo xuống và điền:

1. Mục **Source code**:  `/home/tentaikhoan/Website_QuanTraiCay`
2. Mục **Working directory**:  `/home/tentaikhoan/Website_QuanTraiCay`
3. Mục **Virtualenv** → nhập:  `/home/tentaikhoan/.virtualenvs/bichenv`
   (hoặc gõ ngắn `bichenv` rồi nó tự điền đường dẫn).

---

## Bước 6 — Sửa file WSGI (quan trọng nhất)

1. Vẫn ở tab **Web**, mục **Code**, bấm vào đường dẫn file kết thúc bằng **`_wsgi.py`**
   (vd `/var/www/tentaikhoan_pythonanywhere_com_wsgi.py`) để mở trình sửa.
2. **Xóa toàn bộ** nội dung có sẵn, rồi **dán đoạn dưới đây vào** (tham khảo file
   `wsgi_pythonanywhere.py` trong dự án):
   ```python
   import os
   import sys

   project_home = "/home/tentaikhoan/Website_QuanTraiCay"
   if project_home not in sys.path:
       sys.path.insert(0, project_home)

   # Đặt mật khẩu + khóa bí mật tại đây (KHÔNG bị lộ vì file này nằm trên server)
   os.environ["BICH_ADMIN_USER"] = "admin"
   os.environ["BICH_ADMIN_PASS"] = "ĐỔI_mật_khẩu_mạnh_1"
   os.environ["BICH_ADMIN_PASS2"] = "ĐỔI_mật_khẩu_mạnh_2"
   os.environ["BICH_SECRET_KEY"] = "dan-mot-chuoi-ngau-nhien-that-dai-vao-day"

   from app import app as application
   ```
3. **ĐỔI** `tentaikhoan` và các mật khẩu cho đúng. Bấm **Save** (nút màu xanh góc trên).

---

## Bước 7 — Cho ảnh hiển thị nhanh (Static files)

Vẫn ở tab **Web**, kéo xuống mục **Static files**, bấm **Enter URL / Enter path** và thêm:

| URL | Directory |
|--------|-----------|
| `/static/` | `/home/tentaikhoan/Website_QuanTraiCay/static` |

> Bước này giúp ảnh logo và ảnh trái cây tải lên hiển thị nhanh. (Có thể bỏ qua, web vẫn chạy.)

---

## Bước 8 — Khởi động & truy cập

1. Kéo lên đầu tab **Web**, bấm nút xanh lớn **Reload**.
2. Bấm vào link web của bạn ở đầu trang: **`https://tentaikhoan.pythonanywhere.com`**
3. Xong! Bấm **🔑 Truy cập** và đăng nhập bằng mật khẩu bạn vừa đặt ở Bước 6.

---

## 🔄 Sau này muốn cập nhật code (đã sửa trên máy & push GitHub)

Mở **Consoles → Bash**, gõ:
```bash
cd Website_QuanTraiCay
git pull
```
Rồi sang tab **Web** bấm **Reload**. Xong.

> 💡 Dữ liệu (giá, ảnh đã nhập trên web thật) **không bị mất** khi `git pull` hay `Reload`,
> vì `fruits.db` và thư mục `uploads` được `.gitignore` (chỉ nằm trên server).

---

## ❗ Lỗi thường gặp

| Hiện tượng | Cách xử lý |
|-----------|-----------|
| Mở web báo **"Something went wrong"** | Vào tab **Web** → mục **Log files** → mở **Error log**, đọc dòng cuối. Thường do sai đường dẫn `project_home` hoặc quên `pip install`. |
| Web hiện nhưng **không có ảnh** | Kiểm tra lại mục **Static files** ở Bước 7 (đường dẫn đúng `.../static`). |
| **ModuleNotFoundError: flask** | Chưa cài Flask trong môi trường ảo: `workon bichenv` rồi `pip install -r requirements.txt`, sau đó **Reload**. |
| Đăng nhập không được | Xem lại mật khẩu đã đặt trong file WSGI (Bước 6) và đã bấm **Save** + **Reload** chưa. |

---

## 🔐 Nhắc về bảo mật
Khi lên mạng, **ai biết link cũng vào được trang xem**. Phần admin được khóa bằng mật khẩu,
nên hãy đặt **mật khẩu mạnh** (không dùng `123456`) ở Bước 6. Mật khẩu nằm trong file WSGI
trên server, **không** bị lộ trên GitHub.
