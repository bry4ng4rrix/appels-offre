/* Guide pas a pas : une bulle d'aide pres de chaque bouton marque data-aide.
 *
 *   <a data-aide="Texte" data-aide-titre="Titre" data-aide-ordre="2"
 *      data-aide-page="web-pour-vous">   (page : facultatif, noms d'URL separes par des espaces)
 *
 * Demarre seul a la premiere visite d'une page (body[data-guide-auto]) ; le bouton
 * « ? » de l'en-tete le relance. Vu ou passe : le serveur s'en souvient (/guide/vu/).
 * Les elements caches (onglet ferme, menu replie) sont sautes.
 */
(function () {
  "use strict";
  var corps = document.body;
  var page = corps.dataset.guidePage || "";
  var bouton = document.getElementById("bouton-guide");
  var calme = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var etapes = [], indice = 0, cible = null, bulle = null, retourFocus = null;

  function aPlacer() {
    var vues = {};
    return Array.prototype.filter.call(document.querySelectorAll("[data-aide]"), function (el) {
      var pages = el.dataset.aidePage;
      if (pages && pages.split(" ").indexOf(page) === -1) return false;
      // La meme aide sur chaque carte d'offre : seule la premiere visible compte.
      if (vues[el.dataset.aide] || !el.getClientRects().length) return false;
      vues[el.dataset.aide] = true;
      return true;
    }).sort(function (a, b) {
      return (Number(a.dataset.aideOrdre) || 99) - (Number(b.dataset.aideOrdre) || 99);
    });
  }

  if (bouton && aPlacer().length) bouton.hidden = false;

  function jeton() {
    try { return JSON.parse(corps.getAttribute("hx-headers"))["X-CSRFToken"]; } catch (e) { return ""; }
  }

  function marquerVu() {
    fetch("/guide/vu/", {
      method: "POST", credentials: "same-origin",
      headers: { "X-CSRFToken": jeton(), "Content-Type": "application/x-www-form-urlencoded" },
      body: "page=" + encodeURIComponent(page)
    }).catch(function () {});
    corps.removeAttribute("data-guide-auto");
  }

  function construire() {
    bulle = document.createElement("div");
    bulle.className = "guide-bulle";
    bulle.setAttribute("role", "dialog");
    bulle.setAttribute("aria-labelledby", "guide-titre");
    bulle.setAttribute("aria-describedby", "guide-texte");
    bulle.innerHTML =
      '<p class="guide-compte" id="guide-compte"></p>' +
      '<h2 class="guide-titre" id="guide-titre"></h2>' +
      '<p class="guide-texte" id="guide-texte"></p>' +
      '<div class="guide-actions">' +
      '  <button type="button" class="guide-passer" data-guide="passer">Passer le guide</button>' +
      '  <span class="guide-nav">' +
      '    <button type="button" class="btn btn-xs" data-guide="precedent">Précédent</button>' +
      '    <button type="button" class="btn btn-xs btn-primaire" data-guide="suivant">Suivant</button>' +
      '  </span>' +
      '</div>';
    bulle.addEventListener("click", function (e) {
      var action = e.target.closest("[data-guide]");
      if (!action) return;
      if (action.dataset.guide === "passer") fermer();
      else aller(indice + (action.dataset.guide === "suivant" ? 1 : -1));
    });
    document.body.appendChild(bulle);
  }

  function placer() {
    if (!bulle || !cible) return;
    var marge = 16;
    if (window.innerWidth < 640) {
      // Mobile : la bulle se cale en bas de l'ecran, la cible reste visible au-dessus.
      bulle.style.left = marge + "px";
      bulle.style.right = marge + "px";
      bulle.style.top = "auto";
      bulle.style.bottom = marge + "px";
      return;
    }
    var r = cible.getBoundingClientRect();
    var h = bulle.offsetHeight, w = bulle.offsetWidth;
    var haut = r.bottom + 12 + h <= window.innerHeight - marge ? r.bottom + 12 : r.top - 12 - h;
    var gauche = Math.min(Math.max(marge, r.left), window.innerWidth - w - marge);
    bulle.style.right = "auto";
    bulle.style.bottom = "auto";
    bulle.style.top = Math.max(marge, haut) + "px";
    bulle.style.left = gauche + "px";
  }

  function aller(n) {
    if (n < 0) return;
    if (n >= etapes.length) { fermer(); return; }
    if (cible) cible.classList.remove("guide-cible");
    indice = n;
    cible = etapes[n];
    cible.classList.add("guide-cible");
    bulle.querySelector("#guide-compte").textContent = (n + 1) + " sur " + etapes.length;
    bulle.querySelector("#guide-titre").textContent = cible.dataset.aideTitre || "";
    bulle.querySelector("#guide-texte").textContent = cible.dataset.aide;
    bulle.querySelector('[data-guide="precedent"]').hidden = n === 0;
    bulle.querySelector('[data-guide="suivant"]').textContent = n === etapes.length - 1 ? "Terminer" : "Suivant";
    cible.scrollIntoView({ block: "center", behavior: calme ? "auto" : "smooth" });
    placer();
    bulle.querySelector('[data-guide="suivant"]').focus({ preventScroll: true });
  }

  function clavier(e) {
    if (e.key === "Escape") fermer();
    else if (e.key === "ArrowRight") aller(indice + 1);
    else if (e.key === "ArrowLeft") aller(indice - 1);
  }

  function fermer() {
    if (cible) cible.classList.remove("guide-cible");
    if (bulle) bulle.remove();
    bulle = cible = null;
    window.removeEventListener("scroll", placer, true);
    window.removeEventListener("resize", placer);
    document.removeEventListener("keydown", clavier);
    marquerVu();
    if (retourFocus && retourFocus.focus) retourFocus.focus({ preventScroll: true });
  }

  function lancer() {
    etapes = aPlacer();
    if (!etapes.length || bulle) return;
    retourFocus = document.activeElement;
    construire();
    window.addEventListener("scroll", placer, true);
    window.addEventListener("resize", placer);
    document.addEventListener("keydown", clavier);
    aller(0);
  }

  if (bouton) bouton.addEventListener("click", lancer);
  if (corps.hasAttribute("data-guide-auto")) setTimeout(lancer, 500);
})();
