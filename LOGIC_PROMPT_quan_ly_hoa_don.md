# 📋 PROMPT MÔ TẢ LOGIC — Quản Lý Hoá Đơn (Bích Trái Cây)

> Tài liệu này mô tả toàn bộ logic, luồng màn hình, cấu trúc dữ liệu và các chức năng của app **Quản lý hoá đơn** dành cho chuỗi quán trái cây. Dev có thể dùng tài liệu này để build lại hoặc tích hợp vào web thuần HTML/JS.

---

## 1. TỔNG QUAN APP

- **Tên app:** Quản lý hoá đơn — Bích Trái Cây
- **Nền tảng:** Web thuần HTML + CSS + JavaScript (không dùng framework)
- **Lưu trữ dữ liệu:** In-memory (biến JS) — không có backend, không reload dữ liệu
- **Giao diện:** Mobile-first, single-page app (SPA) — chuyển màn hình bằng cách show/hide div
- **Màu chủ đạo:** `#E8A020` (vàng cam)

---

## 2. CẤU TRÚC MÀN HÌNH

App có **3 màn hình chính** (screen), mỗi lúc chỉ hiện 1 màn:

| ID màn hình | Tên | Mô tả |
|---|---|---|
| `screen-shops` | Danh sách quán | Màn hình khởi đầu — hiện tất cả quán |
| `screen-shop-detail` | Chi tiết quán | Hiện danh sách hoá đơn của 1 quán |
| `screen-invoice-detail` | Chi tiết hoá đơn | Xem đầy đủ 1 hoá đơn |

### Luồng điều hướng:
```
[Danh sách quán]
      ↓ click vào quán
[Chi tiết quán — danh sách HĐ]
      ↓ click vào hoá đơn
[Chi tiết hoá đơn]
      ↓ nút "←" quay lại
[Chi tiết quán]
      ↓ nút "←" quay lại
[Danh sách quán]
```

### Cách chuyển màn hình:
- Tất cả `.screen` đều `display: none` mặc định
- Màn hình active có class `.active` → `display: flex`
- Hàm `goTo(screenId)` xử lý việc chuyển màn hình:
  - Bỏ class `.active` khỏi tất cả screen
  - Thêm class `.active` vào screen mục tiêu
  - Scroll về đầu trang
  - Hiện/ẩn nút FAB (+) — chỉ hiện ở màn `screen-shop-detail`

---

## 3. CẤU TRÚC DỮ LIỆU

### 3.1 Danh sách quán (mảng tĩnh)
```js
const shops = [
  { id: 1, name: 'Quán 1', address: '157 Nguyễn Hữu Tiến' },
  { id: 2, name: 'Quán 2', address: 'Chi nhánh 2' },
  { id: 3, name: 'Quán 3', address: 'Chi nhánh 3' },
];
```

### 3.2 Database hoá đơn (object in-memory)
```js
const invoicesDB = {
  'Quán 1': [ ...danh sách hoá đơn... ],
  'Quán 2': [ ...danh sách hoá đơn... ],
};
```

### 3.3 Cấu trúc 1 hoá đơn
```js
{
  id: 'HD001',           // String — mã hoá đơn, tự sinh: 'HD' + số thứ tự 3 chữ số
  date: '2025-06-20',    // String — định dạng YYYY-MM-DD
  note: 'Khách sỉ',     // String — ghi chú, có thể rỗng
  photo: null,           // String base64 hoặc null — ảnh đính kèm
  items: [               // Array — danh sách mặt hàng
    {
      fruit: 'Xoài Cát', // String — tên trái cây
      price: 60000,      // Number — giá/kg (VNĐ)
      kg: 3,             // Number — số kg
    }
  ]
}
```

### 3.4 Biến trạng thái toàn cục
```js
let currentShop = null;        // Tên quán đang xem
let currentInvoiceId = null;   // ID hoá đơn đang xem
let itemCounter = 0;           // Đếm số dòng hàng trong form tạo HĐ
```

---

## 4. CHI TIẾT TỪNG MÀN HÌNH

---

### 4.1 Màn hình: DANH SÁCH QUÁN (`screen-shops`)

**Hiển thị:**
- Topbar: tiêu đề "Quản lý hoá đơn" (không có nút back)
- Lưới 2 cột các thẻ quán (`.shop-card`)
- Mỗi thẻ hiện: icon 🏬, tên quán, địa chỉ, badge số lượng HĐ (vàng cam, góc trên phải)
- Nút "+ Thêm quán mới" (dạng dashed border) ở cuối

**Tương tác:**
- Click vào thẻ quán → gọi `openShop(shopName)`
- Click "+ Thêm quán mới" → mở modal `modal-add-shop`

**Badge số HĐ:** Hiển thị tĩnh khi render, cần cập nhật nếu thêm HĐ mới (hiện tại chưa tự cập nhật badge sau khi thêm HĐ — đây là điểm cần cải thiện)

---

### 4.2 Màn hình: CHI TIẾT QUÁN (`screen-shop-detail`)

**Hiển thị:**
- Topbar: nút "←" (về danh sách quán), tên quán, nút "+ Tạo HĐ"
- Khu vực chụp ảnh (camera area)
- Bộ lọc ngày
- Danh sách hoá đơn
- Thanh tổng doanh thu ở cuối
- FAB button "+" góc dưới phải

**Khu vực chụp ảnh:**
- Input file ẩn (`<input type="file" accept="image/*" capture="environment">`)
- Click vào khu vực → trigger click input file → mở camera/thư viện
- Sau khi chọn ảnh: đọc bằng `FileReader`, hiện preview (ảnh + nút xoá)
- Ảnh này sẽ được gắn vào hoá đơn khi tạo mới

**Bộ lọc ngày:**
- Input type date
- Khi thay đổi → gọi `filterInvoices()` → re-render danh sách theo ngày đã chọn
- Nút "Tất cả" → xoá filter, hiện tất cả HĐ

**Danh sách hoá đơn:**
- Render bằng JS vào `#invoice-list`
- Mỗi item hiện: mã HĐ (badge), ngày + ghi chú, tên các trái cây, tổng tiền HĐ
- Click vào item → gọi `openInvoiceDetail(invId)`

**Thanh tổng doanh thu:**
- Tính tổng tất cả HĐ đang hiện (theo filter nếu có)
- Hiện nhãn phụ: "Tất cả hoá đơn" hoặc "Ngày DD/MM/YYYY"

---

### 4.3 Màn hình: CHI TIẾT HOÁ ĐƠN (`screen-invoice-detail`)

**Hiển thị:**
- Topbar: nút "←" (về chi tiết quán), mã HĐ, nút "Xoá" (đỏ)
- Thông tin HĐ: mã, tên quán, ngày tạo, ghi chú (nếu có), trạng thái "Đã lưu"
- Ảnh hoá đơn (nếu có) hoặc placeholder "Chưa có ảnh đính kèm"
- Bảng chi tiết hàng hoá: STT | Trái cây | Giá/kg | Kg | Thành tiền
- Dòng tổng tiền hoá đơn

**Tương tác:**
- Nút "Xoá" → `deleteInvoice()` → confirm → xoá khỏi `invoicesDB` → quay về màn chi tiết quán

---

## 5. CÁC MODAL

### 5.1 Modal thêm quán (`modal-add-shop`)
**Fields:**
- Tên quán (bắt buộc, max 30 ký tự)
- Địa chỉ (tuỳ chọn, mặc định "Chưa cập nhật" nếu để trống)

**Logic khi lưu (`addShop()`):**
1. Validate: tên không được rỗng
2. Thêm key mới vào `invoicesDB` với mảng rỗng
3. Tạo thẻ `.shop-card` mới và append vào `#shop-grid`
4. Gắn onclick cho thẻ mới
5. Reset form, đóng modal

---

### 5.2 Modal tạo hoá đơn (`modal-create-hd`)
**Fields:**
- Ngày tạo (bắt buộc, mặc định = hôm nay)
- Ghi chú (tuỳ chọn)
- Danh sách hàng: mỗi dòng gồm [Tên trái cây | Giá/kg | Số kg | Nút xoá dòng]
- Nút "+ Thêm mặt hàng" để thêm dòng mới

**Logic khi lưu (`saveInvoice()`):**
1. Validate ngày
2. Đọc tất cả `.item-row`, validate từng dòng (tên + giá + kg đều phải hợp lệ)
3. Sinh ID: `'HD' + String(existing.length + 1).padStart(3, '0')`
4. Lấy ảnh từ `#preview-img` (nếu có)
5. Push object hoá đơn mới vào `invoicesDB[currentShop]`
6. Đóng modal, re-render danh sách HĐ

---

## 6. CÁC HÀM TIỆN ÍCH

| Hàm | Mô tả |
|---|---|
| `formatMoney(n)` | Format số tiền VNĐ: `n.toLocaleString('vi-VN') + ' đ'` |
| `formatDate(dateStr)` | Chuyển `YYYY-MM-DD` → `DD/MM/YYYY` |
| `calcTotal(invoice)` | Tính tổng tiền HĐ: `Σ(price × kg)` của từng item |
| `getInvoices(shopName)` | Trả về mảng HĐ của quán, hoặc `[]` nếu chưa có |
| `openModal(id)` | Thêm class `.open` vào modal overlay |
| `closeModal(id)` | Xoá class `.open` khỏi modal overlay |

---

## 7. LOGIC MODAL OVERLAY

- Modal overlay click ra ngoài (vào phần overlay, không phải box) → tự đóng
- Xử lý bằng event listener trên tất cả `.modal-overlay`:
```js
overlay.addEventListener('click', e => {
  if (e.target === overlay) overlay.classList.remove('open');
});
```

---

## 8. CÁC ĐIỂM CẦN LƯU Ý KHI TÍCH HỢP

1. **Dữ liệu mất khi reload** — hiện tại lưu in-memory. Nếu muốn persist, cần thêm `localStorage` hoặc kết nối API/database thật.

2. **Badge số HĐ không tự cập nhật** — sau khi thêm HĐ mới, badge trên thẻ quán ở màn danh sách không tự cập nhật. Cần thêm logic cập nhật badge.

3. **ID hoá đơn có thể trùng giữa các quán** — mỗi quán đánh số HĐ riêng từ 001, nên HD001 có thể tồn tại ở nhiều quán. Đây là thiết kế có chủ ý.

4. **Ảnh lưu dạng base64** — nếu ảnh lớn sẽ tốn RAM. Khi tích hợp thật nên upload ảnh lên storage và chỉ lưu URL.

5. **Không có chức năng sửa hoá đơn** — hiện chỉ có tạo mới và xoá.

---

## 9. GỢI Ý MỞ RỘNG

- Thêm `localStorage` để lưu dữ liệu giữa các lần mở app
- Thêm chức năng **sửa hoá đơn**
- Thêm **xuất PDF / in hoá đơn**
- Thêm **tìm kiếm** hoá đơn theo tên trái cây
- Thêm **thống kê** doanh thu theo tuần/tháng
- Thêm **bảng giá** trái cây cập nhật hàng ngày
- Tích hợp **backend** (Node.js/PHP) + database (MySQL/MongoDB) để lưu dữ liệu thật
