// 首页搜索联想
(function () {
  var input = document.getElementById('search-input');
  var box = document.getElementById('suggestions');
  if (!input || !box) return;

  var timer = null;
  input.addEventListener('input', function () {
    clearTimeout(timer);
    var q = input.value.trim();
    if (!q) { box.innerHTML = ''; box.style.display = 'none'; return; }
    timer = setTimeout(function () {
      fetch('/search/api?q=' + encodeURIComponent(q))
        .then(function (r) { return r.json(); })
        .then(function (data) {
          var items = [];
          (data.manufacturers || []).forEach(function (m) {
            items.push('<a class="list-group-item list-group-item-action" href="/manufacturers?q=' + encodeURIComponent(m) + '"><i class="bi bi-building"></i> 厂家：' + escapeHtml(m) + '</a>');
          });
          (data.products || []).forEach(function (p) {
            items.push('<a class="list-group-item list-group-item-action" href="/search?q=' + encodeURIComponent(p) + '"><i class="bi bi-box-seam"></i> 商品：' + escapeHtml(p) + '</a>');
          });
          if (items.length === 0) {
            box.innerHTML = '<div class="list-group-item text-muted small">无匹配项</div>';
          } else {
            box.innerHTML = items.join('');
          }
          box.style.display = 'block';
        })
        .catch(function () { box.innerHTML = ''; box.style.display = 'none'; });
    }, 250);
  });

  document.addEventListener('click', function (e) {
    if (!box.contains(e.target) && e.target !== input) {
      box.style.display = 'none';
    }
  });

  function escapeHtml(s) {
    return s.replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
})();
