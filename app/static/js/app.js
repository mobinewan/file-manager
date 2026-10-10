// 通用脚本：表单提交时不让按钮重复点击
document.addEventListener('submit', function (e) {
  var btn = e.target.querySelector('button[type=submit], button:not([type=button])');
  if (btn && !btn.dataset.locked) {
    btn.dataset.locked = '1';
    setTimeout(function () { btn.disabled = true; }, 0);
    setTimeout(function () { btn.disabled = false; delete btn.dataset.locked; }, 2000);
  }
});

// 表格行悬停提示
document.querySelectorAll('table.table-hover tbody tr').forEach(function (tr) {
  tr.addEventListener('mouseenter', function () { tr.style.cursor = 'pointer'; });
});
