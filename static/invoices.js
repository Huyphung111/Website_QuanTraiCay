(function () {
  "use strict";

  var currentShop = null;
  var currentInvoice = null;
  var shopsCache = [];
  var itemCounter = 0;
  var invoiceMode = "create";
  var editingInvoiceId = null;
  var photoCleared = false;
  var invoicesCache = [];
  var invoicesTotalCache = 0;
  var deleteAllInterval = null;

  var shopGrid = document.getElementById("shopGrid");
  var invoiceList = document.getElementById("invoiceList");
  var totalAmount = document.getElementById("totalAmount");
  var totalLabelSub = document.getElementById("totalLabelSub");
  var fab = document.getElementById("fab");
  var toastTimer = null;

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function formatMoney(n) {
    return Number(n || 0).toLocaleString("vi-VN") + " đ";
  }

  function formatDate(dateStr) {
    if (!dateStr) return "";
    var parts = dateStr.split("-");
    return parts.length === 3 ? parts[2] + "/" + parts[1] + "/" + parts[0] : dateStr;
  }

  function formatFileSize(bytes) {
    var size = Number(bytes || 0);
    if (size < 1024) return size + " B";
    if (size < 1024 * 1024) return Math.round(size / 1024) + " KB";
    return (size / 1024 / 1024).toFixed(1) + " MB";
  }

  function showToast(message, type) {
    var toast = document.getElementById("toast");
    toast.textContent = message;
    toast.className = "toast " + (type || "ok");
    toast.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
      toast.hidden = true;
    }, 2600);
  }

  function api(url, options) {
    return fetch(url, options || {}).then(function (r) {
      return r.json().then(function (data) {
        if (!r.ok || data.ok === false) {
          throw new Error(data.error || "Có lỗi xảy ra.");
        }
        return data;
      });
    });
  }

  function goTo(screenId) {
    document.querySelectorAll(".screen").forEach(function (screen) {
      screen.classList.remove("active");
    });
    document.getElementById(screenId).classList.add("active");
    fab.classList.toggle("show", screenId === "screen-shop-detail");
    window.scrollTo(0, 0);
  }

  function openModal(id) {
    document.getElementById(id).classList.add("open");
  }

  function closeModal(id) {
    document.getElementById(id).classList.remove("open");
  }

  function renderShops(shops) {
    shopsCache = shops || [];
    if (!shops.length) {
      shopGrid.innerHTML = '<div class="empty-state"><div class="empty-icon">🏬</div><p>Chưa có quán nào.</p></div>';
      return;
    }
    shopGrid.innerHTML = shops.map(function (shop) {
      return [
        '<button class="shop-card" type="button" data-id="' + shop.id + '" data-name="' + escapeHtml(shop.name) + '">',
        '<span class="hd-badge">' + shop.invoice_count + ' HĐ</span>',
        '<span class="shop-tools">',
        '<span class="shop-tool btn-edit-shop" data-action="edit" title="Sửa">✏️</span>',
        '<span class="shop-tool btn-delete-shop" data-action="delete" title="Xóa">🗑️</span>',
        '</span>',
        '<div class="shop-icon-big">🏬</div>',
        '<div class="shop-name">' + escapeHtml(shop.name) + '</div>',
        '<div class="shop-meta">' + escapeHtml(shop.address || "Chưa cập nhật") + '</div>',
        '</button>'
      ].join("");
    }).join("");
  }

  function loadShops() {
    shopGrid.innerHTML = '<div class="loading">Đang tải danh sách quán...</div>';
    return api("/api/invoice-shops")
      .then(function (data) { renderShops(data.shops || []); })
      .catch(function (err) {
        shopGrid.innerHTML = '<div class="empty-state"><p>' + escapeHtml(err.message) + '</p></div>';
      });
  }

  function loadInvoices(filterDate) {
    if (!currentShop) return;
    invoiceList.innerHTML = '<div class="loading">Đang tải hóa đơn...</div>';
    var url = "/api/invoice-shops/" + currentShop.id + "/invoices";
    if (filterDate) url += "?date=" + encodeURIComponent(filterDate);

    api(url)
      .then(function (data) {
        invoicesCache = data.invoices || [];
        invoicesTotalCache = data.total || 0;
        if (data.shop) {
          currentShop.address = data.shop.address || "";
        }
        renderInvoiceList(invoicesCache, invoicesTotalCache, filterDate);
      })
      .catch(function (err) {
        invoicesCache = [];
        invoicesTotalCache = 0;
        invoiceList.innerHTML = '<div class="empty-state"><p>' + escapeHtml(err.message) + '</p></div>';
        totalAmount.textContent = "0 đ";
      });
  }

  function renderInvoiceList(invoices, total, filterDate) {
    totalLabelSub.textContent = filterDate ? "Ngày " + formatDate(filterDate) : "Tất cả hóa đơn";
    totalAmount.textContent = formatMoney(total);
    if (document.getElementById("printFilterDate")) {
      document.getElementById("printFilterDate").textContent = filterDate ? "Ngày: " + formatDate(filterDate) : "Tất cả hóa đơn";
    }

    if (!invoices.length) {
      invoiceList.innerHTML = [
        '<div class="empty-state">',
        '<div class="empty-icon">🧾</div>',
        '<p>Chưa có hóa đơn nào' + (filterDate ? " ngày này" : "") + ".</p>",
        '</div>'
      ].join("");
      return;
    }

    invoiceList.innerHTML = invoices.map(function (inv) {
      var itemSummary = (inv.items || []).map(function (item) { return item.fruit; }).join(", ");
      return [
        '<button class="invoice-item" type="button" data-id="' + inv.id + '">',
        '<div class="inv-num">' + escapeHtml(inv.code) + '</div>',
        '<div class="inv-info">',
        '<div class="inv-date">' + formatDate(inv.date) + (inv.note ? " · " + escapeHtml(inv.note) : "") + '</div>',
        '<div class="inv-items">' + escapeHtml(itemSummary) + '</div>',
        '</div>',
        '<div class="inv-amount">' + formatMoney(inv.total) + '</div>',
        '<div class="inv-arrow">›</div>',
        '</button>'
      ].join("");
    }).join("");
  }

  function openShop(id, name) {
    currentShop = { id: id, name: name };
    document.getElementById("shopDetailTitle").textContent = name;
    document.getElementById("printShopName").textContent = name;
    document.getElementById("printFilterDate").textContent = "Tất cả hóa đơn";
    document.getElementById("dateFilter").value = "";
    loadInvoices(null);
    goTo("screen-shop-detail");
  }

  function openInvoiceDetail(invoiceId) {
    api("/api/invoice-shops/" + currentShop.id + "/invoices/" + invoiceId)
      .then(function (data) {
        currentInvoice = data.invoice;
        renderInvoiceDetail(currentInvoice);
        goTo("screen-invoice-detail");
      })
      .catch(function (err) { alert(err.message); });
  }

  function renderInvoiceDetail(inv) {
    document.getElementById("invoiceDetailTitle").textContent = "Hóa đơn #" + inv.code;
    var rows = (inv.items || []).map(function (item, idx) {
      var lineTotal = Number(item.price || 0) * Number(item.kg || 0);
      return [
        "<tr>",
        '<td class="col-stt">' + (idx + 1) + '</td>',
        '<td class="col-fruit">' + escapeHtml(item.fruit) + '</td>',
        '<td class="col-price">' + Number(item.price || 0).toLocaleString("vi-VN") + '</td>',
        '<td class="col-kg">' + Number(item.kg || 0).toLocaleString("vi-VN") + '</td>',
        '<td class="col-total">' + formatMoney(lineTotal) + '</td>',
        "</tr>"
      ].join("");
    }).join("");

    var photoHtml = inv.photo_url
      ? '<img src="' + escapeHtml(inv.photo_url) + '" alt="Ảnh hóa đơn" class="invoice-detail-img" style="cursor: zoom-in;">'
      : '<div class="no-photo">Chưa có ảnh đính kèm</div>';

    document.getElementById("invoiceDetailContent").innerHTML = [
      '<div class="hd-header-info">',
      '<div class="hd-row"><span class="hd-label">Mã hóa đơn</span><span class="hd-value">#' + escapeHtml(inv.code) + '</span></div>',
      '<div class="hd-row"><span class="hd-label">Quán</span><span class="hd-value">' + escapeHtml(currentShop.name) + '</span></div>',
      '<div class="hd-row"><span class="hd-label">Ngày tạo</span><span class="hd-value">' + formatDate(inv.date) + '</span></div>',
      inv.note ? '<div class="hd-row"><span class="hd-label">Ghi chú</span><span class="hd-value">' + escapeHtml(inv.note) + '</span></div>' : "",
      '<div class="hd-row"><span class="hd-label">Trạng thái</span><span class="hd-value status">Đã lưu</span></div>',
      '</div>',
      '<div class="photo-preview"><div class="photo-label">Ảnh hóa đơn</div>' + photoHtml + '</div>',
      '<div class="detail-table-wrap">',
      '<div class="table-title">Chi tiết hàng hóa</div>',
      '<table class="detail-table"><thead><tr><th>STT</th><th>Trái cây</th><th>Giá/kg</th><th>Kg</th><th>Thành tiền</th></tr></thead><tbody>',
      rows,
      '</tbody></table></div>',
      '<div class="hd-total-row"><div class="ht-label">Tổng tiền hóa đơn</div><div class="ht-amount">' + formatMoney(inv.total) + '</div></div>'
    ].join("");
  }

  function formatInvoiceItems(items) {
    return (items || []).map(function (item) {
      return escapeHtml(item.fruit);
    }).join(', ');
  }

  function generatePDF() {
    if (!currentShop) return;
    if (!invoicesCache || !invoicesCache.length) {
      showToast("Không có hóa đơn nào để in.", "error");
      return;
    }

    var filterDate = document.getElementById("dateFilter").value || "";
    var url = "/api/invoice-shops/" + currentShop.id + "/export-pdf";
    if (filterDate) {
      url += "?date=" + encodeURIComponent(filterDate);
    }
    window.open(url, "_blank");
  }

  function renderPhotoArchive(photos) {
    var grid = document.getElementById("photoArchiveGrid");
    if (!photos.length) {
      grid.innerHTML = '<div class="empty-state"><div class="empty-icon">🖼️</div><p>Chưa có ảnh nào trong kho.</p></div>';
      return;
    }
    grid.innerHTML = photos.map(function (photo) {
      return [
        '<div class="archive-photo-card" data-id="' + photo.id + '" data-name="' + escapeHtml(photo.original_name) + '">',
        '<button class="delete-photo-btn" data-action="delete-photo" title="Xóa ảnh" type="button">🗑️</button>',
        '<a href="' + escapeHtml(photo.url) + '" download>',
        '<img src="' + escapeHtml(photo.url) + '" alt="' + escapeHtml(photo.original_name) + '">',
        '</a>',
        '<div class="archive-photo-meta">',
        '<div class="photo-name-wrapper">',
        '<b class="photo-name">' + escapeHtml(photo.original_name) + '</b>',
        '<button class="edit-photo-name-btn" data-action="edit-photo-name" title="Sửa tên" type="button">✏️</button>',
        '</div>',
        '<span>' + formatFileSize(photo.file_size) + ' · ' + escapeHtml(photo.source === "invoice" ? "Ảnh hóa đơn" : "Kho ảnh") + '</span>',
        '</div>',
        '</div>'
      ].join("");
    }).join("");
  }

  function loadPhotoArchive() {
    var grid = document.getElementById("photoArchiveGrid");
    grid.innerHTML = '<div class="loading">Đang tải kho ảnh...</div>';
    var countEl = document.getElementById("photoArchiveCount");
    if (countEl) countEl.textContent = "";
    return api("/api/invoice-photos")
      .then(function (data) {
        var photos = data.photos || [];
        if (countEl) {
          countEl.textContent = "(" + photos.length + " ảnh)";
        }
        renderPhotoArchive(photos);
      })
      .catch(function (err) {
        grid.innerHTML = '<div class="empty-state"><p>' + escapeHtml(err.message) + '</p></div>';
        showToast(err.message, "error");
      });
  }

  function openPhotoArchive() {
    goTo("screen-photo-archive");
    loadPhotoArchive();
  }

  function uploadArchivePhotos(files) {
    if (!files || !files.length) return;
    var fd = new FormData();
    Array.prototype.forEach.call(files, function (file) {
      fd.append("photos", file);
    });
    api("/api/invoice-photos/upload", {
      method: "POST",
      body: fd
    }).then(function (data) {
      showToast(data.message || "Đã lưu ảnh thành công.", "ok");
      document.getElementById("archivePhotoInput").value = "";
      loadPhotoArchive();
    }).catch(function (err) {
      showToast(err.message || "Lưu ảnh không thành công.", "error");
    });
  }

  function deletePhoto(photoId, photoName) {
    if (!confirm('Xóa ảnh "' + photoName + '"? LƯU Ý: Nếu ảnh đang được gắn vào hóa đơn, liên kết ảnh của hóa đơn đó cũng sẽ bị xóa.')) return;
    api("/api/invoice-photos/" + photoId + "/delete", { method: "POST" })
      .then(function () {
        showToast("Đã xóa ảnh thành công.", "ok");
        loadPhotoArchive();
      })
      .catch(function (err) {
        showToast(err.message, "error");
      });
  }

  function editPhotoName(photoId, oldName) {
    var newName = prompt("Nhập tên mới cho ảnh:", oldName);
    if (newName === null) return;
    newName = newName.trim();
    if (!newName) {
      showToast("Tên ảnh không được để trống.", "error");
      return;
    }
    api("/api/invoice-photos/" + photoId + "/edit-name", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: newName })
    }).then(function () {
      showToast("Đã đổi tên ảnh thành công.", "ok");
      loadPhotoArchive();
    }).catch(function (err) {
      showToast(err.message, "error");
    });
  }

  function saveShop() {
    var errBox = document.getElementById("addShopError");
    errBox.textContent = "";
    var editingId = document.getElementById("editingShopId").value;
    var name = document.getElementById("newShopName").value.trim();
    var address = document.getElementById("newShopAddress").value.trim();
    if (!name) {
      errBox.textContent = "Vui lòng nhập tên quán.";
      return;
    }

    var url = editingId ? "/api/invoice-shops/" + editingId + "/edit" : "/api/invoice-shops";
    api(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: name, address: address })
    }).then(function () {
      document.getElementById("editingShopId").value = "";
      document.getElementById("newShopName").value = "";
      document.getElementById("newShopAddress").value = "";
      closeModal("modalAddShop");
      showToast(editingId ? "Đã cập nhật quán thành công." : "Đã thêm quán thành công.", "ok");
      if (currentShop && editingId && currentShop.id === parseInt(editingId, 10)) {
        currentShop.name = name;
        document.getElementById("shopDetailTitle").textContent = name;
      }
      loadShops();
    }).catch(function (err) {
      errBox.textContent = err.message;
      showToast(err.message, "error");
    });
  }

  function openAddShopModal() {
    document.getElementById("shopModalTitle").textContent = "Thêm quán mới";
    document.getElementById("btnSaveShop").textContent = "Thêm quán";
    document.getElementById("editingShopId").value = "";
    document.getElementById("newShopName").value = "";
    document.getElementById("newShopAddress").value = "";
    document.getElementById("addShopError").textContent = "";
    openModal("modalAddShop");
  }

  function openEditShopModal(shop) {
    document.getElementById("shopModalTitle").textContent = "Sửa quán";
    document.getElementById("btnSaveShop").textContent = "Cập nhật quán";
    document.getElementById("editingShopId").value = shop.id;
    document.getElementById("newShopName").value = shop.name || "";
    document.getElementById("newShopAddress").value = shop.address || "";
    document.getElementById("addShopError").textContent = "";
    openModal("modalAddShop");
  }

  function deleteShop(shop) {
    var message = 'Xóa "' + shop.name + '" và toàn bộ hóa đơn của quán này?';
    if (!confirm(message)) return;
    api("/api/invoice-shops/" + shop.id + "/delete", { method: "POST" })
      .then(function () {
        showToast("Đã xóa quán thành công.", "ok");
        if (currentShop && currentShop.id === shop.id) {
          currentShop = null;
          currentInvoice = null;
          goTo("screen-shops");
        }
        loadShops();
      })
      .catch(function (err) {
        showToast(err.message, "error");
      });
  }

  function addItemRow(item) {
    itemCounter++;
    var row = document.createElement("div");
    row.className = "item-row";
    row.innerHTML = [
      '<input type="text" placeholder="Tên trái cây" class="item-fruit">',
      '<input type="number" placeholder="Giá/kg" class="item-price" min="0">',
      '<input type="number" placeholder="Kg" class="item-kg" min="0" step="0.1">',
      '<button class="remove-item" type="button" title="Xóa dòng">×</button>'
    ].join("");
    if (item) {
      row.querySelector(".item-fruit").value = item.fruit || "";
      row.querySelector(".item-price").value = item.price != null ? item.price : "";
      row.querySelector(".item-kg").value = item.kg != null ? item.kg : "";
    }
    row.querySelector(".remove-item").addEventListener("click", function () {
      row.remove();
    });
    document.getElementById("invoiceItemsContainer").appendChild(row);
  }

  function openCreateInvoiceModal() {
    invoiceMode = "create";
    editingInvoiceId = null;
    photoCleared = false;
    document.getElementById("invoiceModalTitle").textContent = "Tạo hóa đơn mới";
    document.getElementById("btnSaveInvoice").textContent = "Lưu hóa đơn";
    document.getElementById("invoiceItemsContainer").innerHTML = "";
    document.getElementById("invoiceNote").value = "";
    document.getElementById("invoiceError").textContent = "";
    document.getElementById("invoiceDate").value = new Date().toISOString().slice(0, 10);
    clearPhoto();
    addItemRow();
    openModal("modalCreateInvoice");
  }

  function openEditInvoiceModal() {
    if (!currentInvoice) return;
    invoiceMode = "edit";
    editingInvoiceId = currentInvoice.id;
    photoCleared = false;
    document.getElementById("invoiceModalTitle").textContent = "Sửa hóa đơn #" + currentInvoice.code;
    document.getElementById("btnSaveInvoice").textContent = "Cập nhật hóa đơn";
    document.getElementById("invoiceItemsContainer").innerHTML = "";
    document.getElementById("invoiceError").textContent = "";
    document.getElementById("invoiceDate").value = currentInvoice.date || "";
    document.getElementById("invoiceNote").value = currentInvoice.note || "";
    clearPhoto();
    if (currentInvoice.photo_url) {
      document.getElementById("previewImg").src = currentInvoice.photo_url;
      document.getElementById("photoPreviewBar").hidden = false;
    }
    (currentInvoice.items || []).forEach(function (item) { addItemRow(item); });
    if (!(currentInvoice.items || []).length) addItemRow();
    openModal("modalCreateInvoice");
  }

  function collectItems() {
    var rows = document.querySelectorAll("#invoiceItemsContainer .item-row");
    var items = [];
    var valid = true;
    rows.forEach(function (row) {
      var fruit = row.querySelector(".item-fruit").value.trim();
      var price = parseFloat(row.querySelector(".item-price").value);
      var kg = parseFloat(row.querySelector(".item-kg").value);
      if (!fruit || isNaN(price) || isNaN(kg) || price < 0 || kg <= 0) {
        valid = false;
        return;
      }
      items.push({ fruit: fruit, price: price, kg: kg });
    });
    return valid && items.length ? items : null;
  }

  function saveInvoice() {
    var errBox = document.getElementById("invoiceError");
    var saveBtn = document.getElementById("btnSaveInvoice");
    errBox.textContent = "";
    var date = document.getElementById("invoiceDate").value;
    var items = collectItems();
    if (!date) {
      errBox.textContent = "Vui lòng chọn ngày.";
      return;
    }
    if (!items) {
      errBox.textContent = "Vui lòng điền đủ thông tin hàng hóa.";
      return;
    }

    var fd = new FormData();
    fd.append("date", date);
    fd.append("note", document.getElementById("invoiceNote").value.trim());
    fd.append("items", JSON.stringify(items));
    fd.append("clear_photo", photoCleared ? "1" : "0");
    var fileInput = document.getElementById("fileInput");
    if (fileInput.files && fileInput.files[0]) {
      fd.append("photo", fileInput.files[0]);
    }

    saveBtn.disabled = true;
    var url = "/api/invoice-shops/" + currentShop.id + "/invoices";
    if (invoiceMode === "edit" && editingInvoiceId) {
      url += "/" + editingInvoiceId + "/edit";
    }

    api(url, {
      method: "POST",
      body: fd
    }).then(function (data) {
      saveBtn.disabled = false;
      closeModal("modalCreateInvoice");
      clearPhoto();
      showToast(invoiceMode === "edit" ? "Đã cập nhật hóa đơn thành công." : "Đã thêm hóa đơn thành công.", "ok");
      if (invoiceMode === "edit" && data.invoice) {
        currentInvoice = data.invoice;
        renderInvoiceDetail(currentInvoice);
      }
      loadInvoices(document.getElementById("dateFilter").value || null);
      loadShops();
    }).catch(function (err) {
      saveBtn.disabled = false;
      errBox.textContent = err.message;
      showToast(err.message || "Lưu hóa đơn không thành công.", "error");
    });
  }

  function deleteInvoice() {
    if (!currentInvoice) return;
    if (!confirm("Xóa hóa đơn #" + currentInvoice.code + "?")) return;
    api("/api/invoice-shops/" + currentShop.id + "/invoices/" + currentInvoice.id + "/delete", {
      method: "POST"
    }).then(function () {
      currentInvoice = null;
      goTo("screen-shop-detail");
      showToast("Đã xóa hóa đơn.", "ok");
      loadInvoices(document.getElementById("dateFilter").value || null);
      loadShops();
    }).catch(function (err) {
      showToast(err.message, "error");
    });
  }

  function openConfirmDeleteAll() {
    if (!currentShop) return;
    openModal("modalConfirmDeleteAll");
  }

  function proceedToDeleteAll() {
    closeModal("modalConfirmDeleteAll");
    openModal("modalCountdownDeleteAll");

    var countdownSeconds = document.getElementById("countdownSeconds");
    var countdownTimerContainer = document.getElementById("countdownTimerContainer");
    var countdownBlurredContent = document.getElementById("countdownBlurredContent");
    var btnFinalDeleteAll = document.getElementById("btnFinalDeleteAll");

    countdownSeconds.textContent = "5";
    countdownTimerContainer.innerHTML = 'Vui lòng đợi <span id="countdownSeconds">5</span> giây...';
    countdownTimerContainer.style.color = '#dc3545';

    countdownBlurredContent.style.filter = "blur(4px)";
    countdownBlurredContent.style.opacity = "0.5";
    countdownBlurredContent.style.pointerEvents = "none";
    btnFinalDeleteAll.disabled = true;
    btnFinalDeleteAll.textContent = "🔴 ĐỒNG Ý XÓA TOÀN BỘ HÓA ĐƠN";

    var count = 5;
    if (deleteAllInterval) {
      clearInterval(deleteAllInterval);
    }

    deleteAllInterval = setInterval(function () {
      count--;
      var secondsSpan = document.getElementById("countdownSeconds");
      if (secondsSpan) {
        secondsSpan.textContent = count;
      }
      if (count <= 0) {
        clearInterval(deleteAllInterval);
        deleteAllInterval = null;
        countdownTimerContainer.innerHTML = 'Nút xóa đã sẵn sàng!';
        countdownTimerContainer.style.color = '#2E7D32';
        countdownBlurredContent.style.filter = "none";
        countdownBlurredContent.style.opacity = "1";
        countdownBlurredContent.style.pointerEvents = "auto";
        btnFinalDeleteAll.disabled = false;
      }
    }, 1000);
  }

  function cancelDeleteAll() {
    if (deleteAllInterval) {
      clearInterval(deleteAllInterval);
      deleteAllInterval = null;
    }
    closeModal("modalConfirmDeleteAll");
    closeModal("modalCountdownDeleteAll");
  }

  function finalDeleteAll() {
    if (!currentShop) return;
    var btn = document.getElementById("btnFinalDeleteAll");
    btn.disabled = true;
    btn.textContent = "ĐANG XÓA...";

    api("/api/invoice-shops/" + currentShop.id + "/invoices/delete-all", {
      method: "POST"
    }).then(function () {
      cancelDeleteAll();
      showToast("Đã xóa toàn bộ hóa đơn.", "ok");
      loadInvoices(document.getElementById("dateFilter").value || null);
      loadShops();
    }).catch(function (err) {
      showToast(err.message, "error");
      btn.disabled = false;
      btn.textContent = "🔴 ĐỒNG Ý XÓA TOÀN BỘ HÓA ĐƠN";
    });
  }

  function previewPhoto() {
    var fileInput = document.getElementById("fileInput");
    var file = fileInput.files[0];
    if (!file) return;
    photoCleared = false;
    var reader = new FileReader();
    reader.onload = function (e) {
      document.getElementById("previewImg").src = e.target.result;
      document.getElementById("photoPreviewBar").hidden = false;
    };
    reader.readAsDataURL(file);
  }

  function clearPhoto() {
    document.getElementById("photoPreviewBar").hidden = true;
    document.getElementById("previewImg").src = "";
    document.getElementById("fileInput").value = "";
    photoCleared = true;
  }

  shopGrid.addEventListener("click", function (e) {
    var card = e.target.closest(".shop-card");
    if (!card) return;
    var shopId = parseInt(card.dataset.id, 10);
    var shop = shopsCache.filter(function (item) { return item.id === shopId; })[0];
    if (!shop) return;
    var actionEl = e.target.closest("[data-action]");
    var action = actionEl ? actionEl.dataset.action : null;
    if (action === "edit") {
      openEditShopModal(shop);
      return;
    }
    if (action === "delete") {
      deleteShop(shop);
      return;
    }
    openShop(shop.id, shop.name);
  });

  invoiceList.addEventListener("click", function (e) {
    var item = e.target.closest(".invoice-item");
    if (!item) return;
    openInvoiceDetail(parseInt(item.dataset.id, 10));
  });

  document.getElementById("btnOpenAddShop").addEventListener("click", openAddShopModal);
  document.getElementById("btnSaveShop").addEventListener("click", saveShop);
  document.getElementById("btnBackShops").addEventListener("click", function () { goTo("screen-shops"); loadShops(); });
  document.getElementById("btnBackShopDetail").addEventListener("click", function () { goTo("screen-shop-detail"); });
  document.getElementById("btnBackFromPhotos").addEventListener("click", function () { goTo("screen-shop-detail"); });
  document.getElementById("btnDownloadAllPhotos").addEventListener("click", function () {
    window.open("/api/invoice-photos/download-all", "_blank");
  });
  document.getElementById("btnPrintInvoices").addEventListener("click", generatePDF);
  document.getElementById("btnPhotoArchive").addEventListener("click", openPhotoArchive);
  document.getElementById("fab").addEventListener("click", openCreateInvoiceModal);
  document.getElementById("btnAddItem").addEventListener("click", function () { addItemRow(); });
  document.getElementById("btnSaveInvoice").addEventListener("click", saveInvoice);
  document.getElementById("btnEditInvoice").addEventListener("click", openEditInvoiceModal);
  document.getElementById("btnDeleteInvoice").addEventListener("click", deleteInvoice);
  document.getElementById("btnDeleteAllInvoices").addEventListener("click", openConfirmDeleteAll);
  document.getElementById("btnProceedDeleteAll").addEventListener("click", proceedToDeleteAll);
  document.getElementById("btnCancelFinalDeleteAll").addEventListener("click", cancelDeleteAll);
  document.getElementById("btnFinalDeleteAll").addEventListener("click", finalDeleteAll);
  document.getElementById("dateFilter").addEventListener("change", function (e) { loadInvoices(e.target.value || null); });
  document.getElementById("btnClearDate").addEventListener("click", function () {
    document.getElementById("dateFilter").value = "";
    loadInvoices(null);
  });
  document.getElementById("fileInput").addEventListener("change", previewPhoto);
  document.getElementById("btnClearPhoto").addEventListener("click", clearPhoto);
  document.getElementById("btnPickArchivePhotos").addEventListener("click", function () {
    document.getElementById("archivePhotoInput").click();
  });
  document.getElementById("btnArchiveUploadBox").addEventListener("click", function () {
    document.getElementById("archivePhotoInput").click();
  });
  document.getElementById("archivePhotoInput").addEventListener("change", function (e) {
    uploadArchivePhotos(e.target.files);
  });

  document.getElementById("photoArchiveGrid").addEventListener("click", function (e) {
    var card = e.target.closest(".archive-photo-card");
    if (!card) return;
    var photoId = parseInt(card.dataset.id, 10);
    var photoName = card.dataset.name;
    var actionEl = e.target.closest("[data-action]");
    var action = actionEl ? actionEl.dataset.action : null;
    if (action === "delete-photo") {
      deletePhoto(photoId, photoName);
      return;
    }
    if (action === "edit-photo-name") {
      editPhotoName(photoId, photoName);
      return;
    }
  });

  document.getElementById("invoiceDetailContent").addEventListener("click", function (e) {
    if (e.target.classList.contains("invoice-detail-img")) {
      document.getElementById("lightboxImg").src = e.target.src;
      openModal("modalLightbox");
    }
  });

  document.querySelectorAll(".modal-overlay").forEach(function (overlay) {
    overlay.addEventListener("click", function (e) {
      if (e.target === overlay || e.target.hasAttribute("data-close")) {
        overlay.classList.remove("open");
        if (overlay.id === "modalCountdownDeleteAll" || overlay.id === "modalConfirmDeleteAll") {
          cancelDeleteAll();
        }
      }
    });
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      document.querySelectorAll(".modal-overlay.open").forEach(function (overlay) {
        overlay.classList.remove("open");
        if (overlay.id === "modalCountdownDeleteAll" || overlay.id === "modalConfirmDeleteAll") {
          cancelDeleteAll();
        }
      });
    }
  });

  loadShops();
})();
