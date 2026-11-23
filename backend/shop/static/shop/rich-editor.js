/* Classic rich-text editor for admin text areas marked .ar-rich.
   No external libraries: a toolbar over a contenteditable box that writes HTML back into the
   original <textarea> (the server cleans it again with shop.richtext.clean_html). */
(function () {
  'use strict';
  var BUTTONS = [
    ['formatBlock', 'p', 'Paragraph', 'P'],
    ['formatBlock', 'h2', 'Heading', 'H2'],
    ['formatBlock', 'h3', 'Sub heading', 'H3'],
    ['|'],
    ['bold', null, 'Bold (Ctrl+B)', '<b>B</b>'],
    ['italic', null, 'Italic (Ctrl+I)', '<i>I</i>'],
    ['|'],
    ['insertUnorderedList', null, 'Bulleted list', '&bull; List'],
    ['insertOrderedList', null, 'Numbered list', '1. List'],
    ['|'],
    ['link', null, 'Insert link', 'Link'],
    ['unlink', null, 'Remove link', 'Unlink'],
    ['removeFormat', null, 'Clear formatting', 'Clear'],
    ['|'],
    ['undo', null, 'Undo', '&#8630;'],
    ['redo', null, 'Redo', '&#8631;'],
    ['source', null, 'Edit HTML', 'HTML']
  ];

  function toHtml(text) {
    // Plain text (older entries) -> paragraphs, so it looks the same as on the website.
    if (!text || /<[a-z/][^>]*>/i.test(text)) return text || '';
    return text.split(/\n\s*\n/).filter(function (p) { return p.trim(); }).map(function (p) {
      var d = document.createElement('div'); d.textContent = p.trim();
      return '<p>' + d.innerHTML.replace(/\n/g, '<br>') + '</p>';
    }).join('');
  }

  function init(area) {
    if (area.dataset.arRich || /__prefix__/.test(area.name)) return;
    area.dataset.arRich = '1';
    var wrap = document.createElement('div'); wrap.className = 'ar-rich-wrap';
    var bar = document.createElement('div'); bar.className = 'ar-rich-bar'; bar.setAttribute('role', 'toolbar');
    var box = document.createElement('div'); box.className = 'ar-rich-box'; box.contentEditable = 'true';
    box.setAttribute('role', 'textbox'); box.setAttribute('aria-multiline', 'true');
    box.innerHTML = toHtml(area.value);
    area.parentNode.insertBefore(wrap, area);
    wrap.appendChild(bar); wrap.appendChild(box); wrap.appendChild(area);
    area.classList.add('ar-rich-source');
    var source = false;
    var sync = function () { if (!source) area.value = box.innerHTML.trim() === '<br>' ? '' : box.innerHTML; };

    BUTTONS.forEach(function (b) {
      if (b[0] === '|') { var s = document.createElement('span'); s.className = 'ar-rich-sep'; bar.appendChild(s); return; }
      var btn = document.createElement('button');
      btn.type = 'button'; btn.title = b[2]; btn.setAttribute('aria-label', b[2]); btn.innerHTML = b[3];
      btn.addEventListener('mousedown', function (e) { e.preventDefault(); }); // keep the selection
      btn.addEventListener('click', function () {
        if (b[0] === 'source') {
          if (!source) sync();
          source = !source;
          if (source) { wrap.classList.add('is-source'); area.focus(); }
          else { box.innerHTML = toHtml(area.value); wrap.classList.remove('is-source'); box.focus(); }
          btn.classList.toggle('on', source);
          return;
        }
        if (source) return;
        box.focus();
        if (b[0] === 'link') {
          var url = window.prompt('Link address (https://… or /page):', 'https://');
          if (url && url !== 'https://') document.execCommand('createLink', false, url);
        } else if (b[0] === 'formatBlock') {
          document.execCommand('formatBlock', false, '<' + b[1] + '>');
        } else {
          document.execCommand(b[0], false, b[1]);
        }
        sync();
      });
      bar.appendChild(btn);
    });

    // Paste as clean text with paragraphs (Word / web pages bring a lot of hidden styling).
    box.addEventListener('paste', function (e) {
      var html = e.clipboardData && e.clipboardData.getData('text/html');
      if (html) return setTimeout(sync, 0); // the server keeps only safe tags
      var text = e.clipboardData && e.clipboardData.getData('text/plain');
      if (text) { e.preventDefault(); document.execCommand('insertHTML', false, toHtml(text) || ''); sync(); }
    });
    box.addEventListener('input', sync);
    box.addEventListener('blur', sync);
    var form = area.form; if (form) form.addEventListener('submit', sync);
  }

  function scan(root) { (root || document).querySelectorAll('textarea.ar-rich').forEach(init); }
  document.addEventListener('DOMContentLoaded', function () { scan(); });
  document.addEventListener('formset:added', function (e) { scan(e.target); });
})();
