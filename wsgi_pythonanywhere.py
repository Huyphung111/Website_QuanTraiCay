# ───────────────────────────────────────────────────────────────
#  MẪU FILE WSGI CHO PYTHONANYWHERE
# ───────────────────────────────────────────────────────────────
#  ĐỪNG chạy file này ở máy. Hãy COPY nội dung bên dưới, dán đè vào
#  file WSGI của PythonAnywhere (vào tab "Web" -> mục "Code" ->
#  bấm link file kết thúc bằng "_wsgi.py" để mở trình sửa).
#
#  Nhớ ĐỔI 2 chỗ:
#    1) "tentaikhoan"            -> tên tài khoản PythonAnywhere của bạn
#    2) "Website_QuanTraiCay"    -> đúng tên thư mục dự án sau khi git clone
# ───────────────────────────────────────────────────────────────
import os
import sys

# 1) Trỏ tới thư mục dự án
project_home = "/home/tentaikhoan/Website_QuanTraiCay"
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# 2) (QUAN TRỌNG) Đặt mật khẩu + khóa bí mật tại ĐÂY cho an toàn.
#    File này nằm trên server, KHÔNG đẩy lên GitHub nên mật khẩu không bị lộ.
os.environ["BICH_ADMIN_USER"] = "admin"           # tài khoản 1
os.environ["BICH_ADMIN_PASS"] = "ĐỔI_mật_khẩu_mạnh_1"
os.environ["BICH_ADMIN_PASS2"] = "ĐỔI_mật_khẩu_mạnh_2"  # cho tài khoản 'bichtraicay'
os.environ["BICH_SECRET_KEY"] = "dan-mot-chuoi-ngau-nhien-that-dai-vao-day"

# 3) Nạp ứng dụng Flask cho PythonAnywhere
from app import app as application
