document.addEventListener("click", function (e) {
  var t = e.target.closest("[data-toggle]");
  if (!t) return;
  e.preventDefault();
  var id = t.getAttribute("data-toggle");
  var el = document.getElementById(id);
  if (!el) return;
  el.classList.toggle("hidden");
  if (!el.classList.contains("hidden")) {
    var first = el.querySelector("input, textarea, select");
    if (first) first.focus();
    el.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
});

setTimeout(function () {
  document.querySelectorAll(".flash").forEach(function (f) {
    f.style.transition = "opacity 400ms";
    f.style.opacity = "0";
    setTimeout(function () { f.remove(); }, 500);
  });
}, 4000);
