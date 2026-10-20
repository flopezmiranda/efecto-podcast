// Carga el reproductor de YouTube solo al hacer clic: la página queda liviana y rápida (Core Web Vitals).
(function () {
  var player = document.querySelector(".player");
  if (!player) return;
  var id = player.dataset.id;

  function load(start) {
    var src = "https://www.youtube-nocookie.com/embed/" + id + "?autoplay=1&rel=0" + (start ? "&start=" + start : "");
    player.innerHTML = '<iframe src="' + src + '" title="Reproductor" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen></iframe>';
  }

  // ?t=123 (enlaces de capítulos desde Google) empieza el video en ese segundo.
  var start = parseInt(new URLSearchParams(location.search).get("t"), 10) || 0;
  player.querySelector(".player-facade").addEventListener("click", function () { load(start); });
  if (start) player.scrollIntoView({ block: "center" });

  document.querySelectorAll("[data-seek]").forEach(function (a) {
    a.addEventListener("click", function (e) {
      e.preventDefault();
      load(a.dataset.seek);
      player.scrollIntoView({ behavior: "smooth", block: "center" });
    });
  });

  var more = document.querySelector("[data-expand]");
  if (more) more.addEventListener("click", function () {
    document.querySelector(".transcript").classList.remove("collapsed");
    more.remove();
  });
})();
