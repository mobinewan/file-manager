// 三段式日期输入：4 位年份输完自动跳月份，2 位月份输完自动跳日。
// 任意段变化都会同步合并到隐藏字段 name=YYYY-MM-DD。
(function () {
  function pad(n) {
    n = String(n).replace(/\D/g, '');
    return n.length < 2 ? '0' + n : n;
  }

  function clamp(val, max) {
    var n = parseInt(val, 10);
    if (isNaN(n) || n < 1) return '';
    if (n > max) return String(max);
    return String(n);
  }

  function sync(container) {
    var y = container.querySelector('.date-y').value.trim();
    var m = container.querySelector('.date-m').value.trim();
    var d = container.querySelector('.date-d').value.trim();
    var hidden = container.querySelector('input[type=hidden]');
    if (y && m && d) {
      hidden.value = y + '-' + pad(m) + '-' + pad(d);
    } else {
      hidden.value = '';
    }
  }

  function initContainer(container) {
    var yInput = container.querySelector('.date-y');
    var mInput = container.querySelector('.date-m');
    var dInput = container.querySelector('.date-d');

    [yInput, mInput, dInput].forEach(function (inp) {
      inp.addEventListener('input', function (e) {
        // 仅保留数字
        var cleaned = e.target.value.replace(/\D/g, '');
        if (e.target.value !== cleaned) e.target.value = cleaned;
        sync(container);
      });
      inp.addEventListener('keydown', function (e) {
        // 退格到空时自动回到上一段
        if (e.key === 'Backspace' && e.target.value === '') {
          if (e.target === mInput) yInput.focus();
          else if (e.target === dInput) mInput.focus();
        }
      });
    });

    yInput.addEventListener('input', function () {
      if (yInput.value.length >= 4) mInput.focus();
    });
    mInput.addEventListener('input', function () {
      var v = clamp(mInput.value, 12);
      if (v !== mInput.value) mInput.value = v;
      if (mInput.value.length >= 2) dInput.focus();
    });
    dInput.addEventListener('input', function () {
      var v = clamp(dInput.value, 31);
      if (v !== dInput.value) dInput.value = v;
    });
    dInput.addEventListener('blur', function () {
      if (dInput.value) dInput.value = pad(dInput.value);
    });
    mInput.addEventListener('blur', function () {
      if (mInput.value) mInput.value = pad(mInput.value);
    });
  }

  function initAll() {
    document.querySelectorAll('.date-picker').forEach(initContainer);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }

  // 对动态插入的模态框兼容：监听 DOM 变更
  var observer = new MutationObserver(function (mutations) {
    mutations.forEach(function (m) {
      m.addedNodes.forEach(function (node) {
        if (node.nodeType !== 1) return;
        if (node.classList && node.classList.contains('date-picker')) {
          initContainer(node);
        } else {
          node.querySelectorAll && node.querySelectorAll('.date-picker').forEach(initContainer);
        }
      });
    });
  });
  observer.observe(document.body, { childList: true, subtree: true });
})();
