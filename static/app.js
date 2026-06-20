/* Bích Trái Cây - xử lý phía trình duyệt cho phần admin */
(function () {
  "use strict";

  var isAdmin = document.body.dataset.admin === "1";

  // ── Tiện ích mở/đóng modal ──
  function openModal(el) { el.classList.add("open"); }
  function closeModal(el) { el.classList.remove("open"); }

  // Đóng modal khi bấm nền tối hoặc nút có [data-close]
  document.querySelectorAll(".modal-overlay").forEach(function (overlay) {
    overlay.addEventListener("click", function (e) {
      if (e.target === overlay || e.target.hasAttribute("data-close")) {
        closeModal(overlay);
      }
    });
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      document.querySelectorAll(".modal-overlay.open").forEach(closeModal);
    }
  });

  // ─────────────────────────────────────────────
  // TÌM KIẾM (cho cả khách và admin)
  // ─────────────────────────────────────────────
  var searchInput = document.getElementById("searchInput");
  var searchClear = document.getElementById("searchClear");
  var noResults = document.getElementById("noResults");

  function runSearch() {
    var q = (searchInput.value || "").trim().toLowerCase();
    var cards = document.querySelectorAll(".fruit-card");
    var visible = 0;
    cards.forEach(function (card) {
      var hay = card.dataset.search || "";
      var match = q === "" || hay.indexOf(q) !== -1;
      card.style.display = match ? "" : "none";
      if (match) visible++;
    });
    if (searchClear) searchClear.hidden = q === "";
    if (noResults) noResults.hidden = !(cards.length > 0 && visible === 0);
  }

  if (searchInput) {
    searchInput.addEventListener("input", runSearch);
  }
  if (searchClear) {
    searchClear.addEventListener("click", function () {
      searchInput.value = "";
      runSearch();
      searchInput.focus();
    });
  }

  // ─────────────────────────────────────────────
  // ĐĂNG NHẬP (khách -> admin)
  // ─────────────────────────────────────────────
  var loginModal = document.getElementById("loginModal");
  var btnAccess = document.getElementById("btnAccess");
  if (btnAccess) {
    btnAccess.addEventListener("click", function () {
      document.getElementById("loginError").textContent = "";
      document.getElementById("loginForm").reset();
      openModal(loginModal);
    });
  }

  var loginForm = document.getElementById("loginForm");
  if (loginForm) {
    loginForm.addEventListener("submit", function (e) {
      e.preventDefault();
      var errBox = document.getElementById("loginError");
      errBox.textContent = "";
      var fd = new FormData(loginForm);

      fetch("/login", { method: "POST", body: fd })
        .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
        .then(function (res) {
          if (res.d.ok) {
            window.location.reload();
          } else {
            errBox.textContent = res.d.error || "Đăng nhập thất bại.";
          }
        })
        .catch(function () { errBox.textContent = "Lỗi kết nối máy chủ."; });
    });
  }

  // ─────────────────────────────────────────────
  // ĐĂNG XUẤT (admin -> khách)
  // ─────────────────────────────────────────────
  var btnLogout = document.getElementById("btnLogout");
  if (btnLogout) {
    btnLogout.addEventListener("click", function () {
      fetch("/logout", { method: "POST" })
        .then(function () { window.location.reload(); });
    });
  }

  // ─────────────────────────────────────────────
  // CRUD (chỉ chạy khi là admin)
  // ─────────────────────────────────────────────
  if (!isAdmin) return;

  var fruitModal = document.getElementById("fruitModal");
  var fruitForm = document.getElementById("fruitForm");
  var fruitTitle = document.getElementById("fruitModalTitle");
  var imgPreview = document.getElementById("imgPreview");

  function fillForm(data) {
    document.getElementById("fruitId").value = data.id || "";
    document.getElementById("fName").value = data.name || "";
    document.getElementById("fPrice").value = data.price != null ? data.price : "";
    document.getElementById("fUnit").value = data.unit || "đ/kg";
    document.getElementById("fOrigin").value = data.origin || "";
    document.getElementById("fBadge").value = data.badge || "";
    document.getElementById("fImage").value = "";
    document.getElementById("fruitError").textContent = "";
    if (data.image_url) {
      imgPreview.innerHTML = '<img src="' + data.image_url + '" alt="">';
    } else {
      imgPreview.innerHTML = "";
    }
  }

  // ── Nút THÊM ──
  var btnAdd = document.getElementById("btnAdd");
  if (btnAdd) {
    btnAdd.addEventListener("click", function () {
      fruitTitle.textContent = "Thêm trái cây";
      fillForm({});
      openModal(fruitModal);
    });
  }

  // ── Nút SỬA / XÓA trên từng thẻ ──
  document.querySelectorAll(".fruit-card").forEach(function (card) {
    var id = parseInt(card.dataset.id, 10);

    var editBtn = card.querySelector(".btn-edit");
    if (editBtn) {
      editBtn.addEventListener("click", function () {
        var data = (window.FRUITS || []).filter(function (x) { return x.id === id; })[0];
        if (!data) return;
        fruitTitle.textContent = "Sửa trái cây";
        fillForm(data);
        openModal(fruitModal);
      });
    }

    var delBtn = card.querySelector(".btn-delete");
    if (delBtn) {
      delBtn.addEventListener("click", function () {
        var data = (window.FRUITS || []).filter(function (x) { return x.id === id; })[0];
        var name = data ? data.name : "trái cây này";
        if (!confirm('Xóa "' + name + '" khỏi bảng giá?')) return;
        fetch("/fruits/" + id + "/delete", { method: "POST" })
          .then(function (r) { return r.json(); })
          .then(function (d) {
            if (d.ok) { window.location.reload(); }
            else { alert(d.error || "Không xóa được."); }
          })
          .catch(function () { alert("Lỗi kết nối máy chủ."); });
      });
    }
  });

  // ── Xem trước ảnh khi chọn file ──
  var fImage = document.getElementById("fImage");
  if (fImage) {
    fImage.addEventListener("change", function () {
      var file = fImage.files[0];
      if (!file) return;
      var reader = new FileReader();
      reader.onload = function (ev) {
        imgPreview.innerHTML = '<img src="' + ev.target.result + '" alt="">';
      };
      reader.readAsDataURL(file);
    });
  }

  // ── Gửi form THÊM / SỬA ──
  if (fruitForm) {
    fruitForm.addEventListener("submit", function (e) {
      e.preventDefault();
      var errBox = document.getElementById("fruitError");
      errBox.textContent = "";
      var submitBtn = document.getElementById("fruitSubmit");
      submitBtn.disabled = true;

      var id = document.getElementById("fruitId").value;
      var url = id ? ("/fruits/" + id + "/edit") : "/fruits/add";
      var fd = new FormData(fruitForm);

      fetch(url, { method: "POST", body: fd })
        .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
        .then(function (res) {
          if (res.d.ok) {
            window.location.reload();
          } else {
            errBox.textContent = res.d.error || "Lưu thất bại.";
            submitBtn.disabled = false;
          }
        })
        .catch(function () {
          errBox.textContent = "Lỗi kết nối máy chủ.";
          submitBtn.disabled = false;
        });
    });
  }
})();
