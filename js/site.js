/* =========================================================
   AYARLAR — e-posta ve Instagram adresinizi YALNIZCA burada yazın.
   Sitedeki tüm e-posta / Instagram bağlantıları buradan dolar.
   ========================================================= */
var SITE = {
    email: "selim.baltaci@gmail.com",
    instagram: "pestepo"
};

(function () {
    var doc = document;
    var body = doc.body;
    var root = doc.documentElement;

    /* ---------- E-posta ve Instagram bağlantıları ---------- */
    doc.querySelectorAll("[data-email]").forEach(function (a) { a.href = "mailto:" + SITE.email; });
    doc.querySelectorAll("[data-instagram]").forEach(function (a) {
        a.href = "https://www.instagram.com/" + SITE.instagram + "/";
        a.target = "_blank";
        a.rel = "noopener";
    });
    doc.querySelectorAll("[data-email-text]").forEach(function (s) { s.textContent = SITE.email; });
    doc.querySelectorAll("[data-instagram-text]").forEach(function (s) { s.textContent = "@" + SITE.instagram; });
    /* Tek odak sınırı: arkadaki sayfa açık pencere kapanana kadar etkisiz. */
    var activeDialog = null;
    var blocked = [];
    function lockDialog(dialog) {
        unlockDialog();
        activeDialog = dialog;
        Array.prototype.forEach.call(body.children, function (element) {
            if (element === dialog || element.contains(dialog) || element.tagName === "SCRIPT" ||
                (dialog.id === "menu" && element.classList.contains("scrim"))) return;
            blocked.push({ element: element, inert: element.inert });
            element.inert = true;
        });
    }
    function unlockDialog() {
        blocked.forEach(function (item) { item.element.inert = item.inert; });
        blocked = [];
        activeDialog = null;
    }
    doc.addEventListener("keydown", function (e) {
        if (e.key !== "Tab" || !activeDialog) return;
        var controls = Array.prototype.filter.call(activeDialog.querySelectorAll(
            'a[href], button:not([disabled]), input, textarea, [tabindex="0"]'), function (el) {
                return !el.hidden && el.getClientRects().length > 0;
            });
        if (!controls.length) { e.preventDefault(); activeDialog.focus(); return; }
        var first = controls[0], last = controls[controls.length - 1];
        if (e.shiftKey && (doc.activeElement === first || !activeDialog.contains(doc.activeElement))) {
            e.preventDefault(); last.focus();
        } else if (!e.shiftKey && (doc.activeElement === last || !activeDialog.contains(doc.activeElement))) {
            e.preventDefault(); first.focus();
        }
    });

    /* ---------- Açılır menü ---------- */
    var drawer = doc.getElementById("menu");
    var burgers = doc.querySelectorAll(".burger");
    var lastOpener = null;
    function openMenu(e) {
        if (!drawer) return;
        lastOpener = e && e.currentTarget;
        body.classList.add("menu-open");
        drawer.setAttribute("aria-hidden", "false");
        lockDialog(drawer);
        burgers.forEach(function (b) { b.setAttribute("aria-expanded", "true"); });
        var first = drawer.querySelector("nav a");
        setTimeout(function () { if (first) first.focus({ preventScroll: true }); }, 60);
    }
    function closeMenu() {
        if (!drawer || !body.classList.contains("menu-open")) return;
        body.classList.remove("menu-open");
        drawer.setAttribute("aria-hidden", "true");
        unlockDialog();
        burgers.forEach(function (b) { b.setAttribute("aria-expanded", "false"); });
        if (lastOpener) lastOpener.focus({ preventScroll: true });
    }
    burgers.forEach(function (b) { b.addEventListener("click", openMenu); });
    doc.querySelectorAll("[data-close-menu]").forEach(function (el) { el.addEventListener("click", closeMenu); });

    /* ---------- Sayfalar arası yumuşak geçiş ---------- */
    function leave(href) {
        closeMenu();
        body.classList.add("is-leaving");
        setTimeout(function () { window.location.href = href; }, 380);
    }
    doc.addEventListener("click", function (e) {
        if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
        var a = e.target.closest ? e.target.closest("a") : null;
        if (!a || !a.getAttribute("href") || a.target === "_blank" || a.hasAttribute("download")) return;
        var url;
        try { url = new URL(a.href, window.location.href); } catch (err) { return; }
        if (url.protocol !== "http:" && url.protocol !== "https:" && url.protocol !== "file:") return;
        if (url.origin !== window.location.origin) return;
        var samePage = url.pathname === window.location.pathname;
        if (samePage && url.hash) { closeMenu(); return; }   // aynı sayfada yumuşak kayma
        if (!/\.html?$/i.test(url.pathname) && !/\/$/.test(url.pathname)) return;
        e.preventDefault();
        if (samePage) { closeMenu(); return; }
        leave(url.href);
    });
    window.addEventListener("pageshow", function (e) {
        if (e.persisted) body.classList.remove("is-leaving");
    });

    /* ---------- Büyük fotoğraf (beyaz zemin) ---------- */
    var viewer, vImg, vCount, vCap, vPrev, vNext, vMessage, list = [], index = 0, opener = null, touchX = null;
    function buildViewer() {
        viewer = doc.createElement("div");
        viewer.className = "viewer";
        viewer.setAttribute("role", "dialog");
        viewer.setAttribute("aria-modal", "true");
        viewer.setAttribute("aria-label", "Büyük fotoğraf");
        viewer.setAttribute("tabindex", "-1");
        viewer.innerHTML =
            '<div class="v-top"><span class="v-count caps"></span>' +
            '<button class="v-close" type="button" aria-label="Kapat">×</button></div>' +
            '<div class="v-stage"><button class="v-nav v-prev" type="button" aria-label="Önceki fotoğraf">‹</button>' +
            '<img alt="">' +
            '<div class="v-message" hidden><span role="status">Fotoğraf yüklenemedi.</span><button type="button" class="v-retry">Yeniden dene</button></div>' +
            '<button class="v-nav v-next" type="button" aria-label="Sonraki fotoğraf">›</button></div>' +
            '<div class="v-cap"></div>';
        body.appendChild(viewer);
        vImg = viewer.querySelector("img");
        vCount = viewer.querySelector(".v-count");
        vCap = viewer.querySelector(".v-cap");
        vPrev = viewer.querySelector(".v-prev");
        vNext = viewer.querySelector(".v-next");
        vMessage = viewer.querySelector(".v-message");
        vMessage.querySelector("button").addEventListener("click", function () {
            show(index, true);
        });
        viewer.querySelector(".v-close").addEventListener("click", closeViewer);
        vPrev.addEventListener("click", function () { show(index - 1); });
        vNext.addEventListener("click", function () { show(index + 1); });
        viewer.querySelector(".v-stage").addEventListener("click", function (e) {
            if (e.target === e.currentTarget) closeViewer();
        });
        vImg.addEventListener("load", function () {
            vImg.classList.remove("is-loading"); viewer.classList.remove("is-error"); vMessage.hidden = true;
        });
        vImg.addEventListener("error", function () {
            vImg.classList.remove("is-loading"); viewer.classList.add("is-error"); vMessage.hidden = false;
        });
        viewer.addEventListener("touchstart", function (e) { touchX = e.touches[0].clientX; }, { passive: true });
        viewer.addEventListener("touchend", function (e) {
            if (touchX === null) return;
            var dx = e.changedTouches[0].clientX - touchX;
            if (Math.abs(dx) > 50 && list.length > 1) show(index + (dx < 0 ? 1 : -1));
            touchX = null;
        });
    }
    function show(i, retry) {
        index = (i + list.length) % list.length;
        var item = list[index];
        vMessage.hidden = true;
        viewer.classList.remove("is-error");
        if (vImg.getAttribute("src") !== item.href) vImg.classList.add("is-loading");
        vImg.src = retry ? item.href + (item.href.indexOf("?") < 0 ? "?" : "&") + "retry=" + Date.now() : item.href;
        vImg.alt = item.alt;
        vCount.textContent = String(index + 1).padStart(2, "0") + " / " + String(list.length).padStart(2, "0");
        vCap.textContent = item.title;
        vPrev.hidden = vNext.hidden = list.length < 2;
        [1, -1].forEach(function (d) {          // komşu fotoğrafları önceden yükle
            var n = list[(index + d + list.length) % list.length];
            if (n) { var p = new Image(); p.src = n.href; }
        });
    }
    function openViewer(items, i, from) {
        closeMenu();
        if (!viewer) buildViewer();
        list = items; opener = from;
        show(i);
        viewer.classList.add("is-open");
        lockDialog(viewer);
        root.style.overflow = "hidden";
        viewer.querySelector(".v-close").focus({ preventScroll: true });
    }
    function closeViewer() {
        if (!viewer || !viewer.classList.contains("is-open")) return;
        viewer.classList.remove("is-open");
        unlockDialog();
        root.style.overflow = "";
        if (opener) opener.focus({ preventScroll: true });
    }
    doc.querySelectorAll("[data-lightbox]").forEach(function (group) {
        var links = Array.prototype.slice.call(group.querySelectorAll("a[href]"));
        var items = links.map(function (a) {
            var img = a.querySelector("img");
            return {
                href: a.getAttribute("href"),
                alt: img ? img.alt : "",
                title: a.getAttribute("data-title") || group.getAttribute("data-title") || ""
            };
        });
        links.forEach(function (a, i) {
            a.addEventListener("click", function (e) {
                if (e.metaKey || e.ctrlKey) return;
                e.preventDefault();
                openViewer(items, i, a);
            });
        });
    });

    doc.addEventListener("keydown", function (e) {
        if (viewer && viewer.classList.contains("is-open")) {
            if (e.key === "Escape") closeViewer();
            if (e.key === "ArrowRight" && list.length > 1) show(index + 1);
            if (e.key === "ArrowLeft" && list.length > 1) show(index - 1);
            return;
        }
        if (e.key === "Escape") closeMenu();
    });

    /* ---------- Kaydırınca yumuşak belirme ---------- */
    var reveals = doc.querySelectorAll(".reveal");
    if ("IntersectionObserver" in window) {
        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (en) {
                if (en.isIntersecting) { en.target.classList.add("is-in"); io.unobserve(en.target); }
            });
        }, { rootMargin: "0px 0px -6% 0px" });
        reveals.forEach(function (el) { io.observe(el); });
    } else {
        reveals.forEach(function (el) { el.classList.add("is-in"); });
    }

    /* ---------- İletişim formu ---------- */
    var form = doc.querySelector(".contact-form");
    if (form) {
        var status = form.querySelector(".form-status");
        form.addEventListener("submit", function (e) {
            e.preventDefault();
            if (form.reportValidity && !form.reportValidity()) return;
            var name = form.elements.ad.value.trim();
            var mail = form.elements.eposta.value.trim();
            var text = form.elements.mesaj.value.trim();
            var subject = "Siteden mesaj — " + name;
            var content = text + "\n\n— " + name + "\n" + mail;
            window.location.href = "mailto:" + SITE.email +
                "?subject=" + encodeURIComponent(subject) +
                "&body=" + encodeURIComponent(content);
            if (status) status.textContent = "Mesaj henüz gönderilmedi. E-posta uygulamanız açılırsa oradan “Gönder”e basın. Açılmazsa " + SITE.email + " adresine yazabilirsiniz.";
        });
    }
    doc.addEventListener("contextmenu", function (e) { if (e.target.tagName === "IMG") e.preventDefault(); });
    doc.addEventListener("dragstart", function (e) { if (e.target.tagName === "IMG") e.preventDefault(); });
})();
