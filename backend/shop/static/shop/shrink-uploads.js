/* Aiman Royale admin: shrink large photos in the browser before they are uploaded.
   Photos wider/taller than 2400 px or bigger than 2 MB are re-saved as JPEG (quality 0.88),
   so a product can be saved with many photos without hitting server upload limits. */
(function () {
  'use strict';
  var MAX_SIDE = 2400, MAX_BYTES = 2 * 1024 * 1024, LIMIT = 10 * 1024 * 1024;
  if (!window.DataTransfer || !window.HTMLCanvasElement) return;

  function shrink(file) {
    return new Promise(function (resolve) {
      if (!/^image\/(jpeg|png|webp)$/.test(file.type)) return resolve(file);
      var url = URL.createObjectURL(file), img = new Image();
      img.onload = function () {
        var w = img.naturalWidth, h = img.naturalHeight, s = Math.min(1, MAX_SIDE / Math.max(w, h));
        URL.revokeObjectURL(url);
        if (s === 1 && file.size <= MAX_BYTES) return resolve(file);
        var c = document.createElement('canvas');
        c.width = Math.round(w * s); c.height = Math.round(h * s);
        var ctx = c.getContext('2d');
        ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, c.width, c.height);
        ctx.drawImage(img, 0, 0, c.width, c.height);
        c.toBlob(function (blob) {
          if (!blob || blob.size >= file.size) return resolve(file);
          resolve(new File([blob], file.name.replace(/\.(png|webp|jpe?g)$/i, '') + '.jpg', {type: 'image/jpeg', lastModified: Date.now()}));
        }, 'image/jpeg', 0.88);
      };
      img.onerror = function () { URL.revokeObjectURL(url); resolve(file); };
      img.src = url;
    });
  }

  function note(input, text, bad) {
    var n = input.parentNode.querySelector('.ar-shrink-note');
    if (!n) { n = document.createElement('div'); n.className = 'ar-shrink-note'; input.parentNode.appendChild(n); }
    n.textContent = text; n.style.cssText = 'font-size:12px;margin-top:4px;color:' + (bad ? '#a10000' : '#555');
  }

  var busy = 0;
  document.addEventListener('change', function (e) {
    var input = e.target;
    if (!input || input.type !== 'file' || !input.files || !input.files.length || input.dataset.arShrunk === '1') return;
    if (!input.accept || input.accept.indexOf('image') < 0) { if (!/image/.test(input.name) && !/photo/.test(input.name)) return; }
    var files = Array.prototype.slice.call(input.files), before = files.reduce(function (n, f) { return n + f.size; }, 0);
    busy++; note(input, 'Preparing ' + files.length + ' photo(s)…');
    Promise.all(files.map(shrink)).then(function (out) {
      var dt = new DataTransfer(), after = 0, tooBig = [];
      out.forEach(function (f) { dt.items.add(f); after += f.size; if (f.size > LIMIT) tooBig.push(f.name); });
      input.dataset.arShrunk = '1'; input.files = dt.files;
      setTimeout(function () { delete input.dataset.arShrunk; }, 0);
      if (tooBig.length) note(input, 'Too large (over 10 MB): ' + tooBig.join(', '), true);
      else note(input, out.length + ' photo(s) ready · ' + (after / 1048576).toFixed(1) + ' MB' + (after < before ? ' (reduced from ' + (before / 1048576).toFixed(1) + ' MB)' : ''));
    }).finally(function () { busy--; });
  }, true);

  // Don't submit while photos are still being prepared.
  document.addEventListener('submit', function (e) {
    if (busy > 0) { e.preventDefault(); var f = e.target; var t = setInterval(function () { if (busy === 0) { clearInterval(t); f.submit(); } }, 200); }
  }, true);
})();
