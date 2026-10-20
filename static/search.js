(function () {
  var input = document.getElementById("q");
  var list = document.getElementById("results");
  var count = document.getElementById("count");
  var data = [];

  function norm(s) {
    return s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  }

  function esc(s) {
    return s.replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; });
  }

  function run() {
    var words = norm(input.value.trim()).split(/\s+/).filter(Boolean);
    if (!words.length) { list.innerHTML = ""; count.textContent = data.length + " episodios"; return; }
    var hits = data.filter(function (e) {
      var hay = e._n;
      return words.every(function (w) { return hay.indexOf(w) !== -1; });
    });
    count.textContent = hits.length + (hits.length === 1 ? " resultado" : " resultados");
    list.innerHTML = hits.slice(0, 100).map(function (e) {
      return '<li><a href="' + e.u + '">' + esc(e.t) + "</a><p>" + esc(e.d) + " · " + esc(e.s) + "</p></li>";
    }).join("");
    history.replaceState(null, "", "?q=" + encodeURIComponent(input.value));
  }

  fetch("/search.json").then(function (r) { return r.json(); }).then(function (d) {
    data = d.map(function (e) { e._n = norm(e.t + " " + e.s + " " + e.k); return e; });
    var q = new URLSearchParams(location.search).get("q");
    if (q) input.value = q;
    run();
  });
  input.addEventListener("input", run);
})();
