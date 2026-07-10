
(function () {
  "use strict";

  // ── mobile nav ──────────────────────────────────────────────────────────
  var toggle = document.querySelector(".nav-toggle");
  var nav = document.querySelector("nav.main");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    nav.addEventListener("click", function (ev) {
      if (ev.target.tagName === "A") nav.classList.remove("open");
    });
  }

  // ── expertise tabs ──────────────────────────────────────────────────────
  var tabBtns = document.querySelectorAll(".tab-btn");
  function selectTab(id) {
    tabBtns.forEach(function (b) {
      b.setAttribute("aria-selected", b.dataset.tab === id ? "true" : "false");
    });
    document.querySelectorAll(".tab-panel").forEach(function (p) {
      p.classList.toggle("active", p.id === "panel-" + id);
    });
  }
  tabBtns.forEach(function (b) {
    b.addEventListener("click", function () { selectTab(b.dataset.tab); });
  });

  // ── filter pills (code vault + discussions) ─────────────────────────────
  document.querySelectorAll("[data-filter-group]").forEach(function (group) {
    var pills = group.querySelectorAll(".pill");
    var items = document.querySelectorAll(group.dataset.filterGroup);
    pills.forEach(function (pill) {
      pill.addEventListener("click", function () {
        pills.forEach(function (p) { p.setAttribute("aria-pressed", "false"); });
        pill.setAttribute("aria-pressed", "true");
        var want = pill.dataset.cat;
        items.forEach(function (it) {
          it.classList.toggle("hidden", want !== "all" && it.dataset.cat !== want);
        });
      });
    });
  });

  // ── copy buttons ────────────────────────────────────────────────────────
  document.querySelectorAll(".copybtn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var pre = btn.closest(".codecard").querySelector("pre");
      // textContent strips the syntax-highlight spans — raw code only.
      navigator.clipboard.writeText(pre.textContent).then(function () {
        var old = btn.textContent;
        btn.textContent = "Copied!";
        btn.classList.add("done");
        setTimeout(function () {
          btn.textContent = old;
          btn.classList.remove("done");
        }, 1600);
      }, function () {
        btn.textContent = "Press Ctrl+C";
      });
    });
  });

  // ── scroll reveal + active nav link ─────────────────────────────────────
  if ("IntersectionObserver" in window) {
    var ro = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add("in"); ro.unobserve(e.target); }
      });
    }, { threshold: 0.12 });
    document.querySelectorAll(".reveal").forEach(function (el) { ro.observe(el); });

    var links = document.querySelectorAll("nav.main a[href^='#'], nav.main a[href^='/#']");
    var map = {};
    links.forEach(function (l) {
      var id = l.getAttribute("href").split("#")[1];
      if (id) map[id] = l;
    });
    var so = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        var link = map[e.target.id];
        if (link && e.isIntersecting) {
          links.forEach(function (l) { l.classList.remove("active"); });
          link.classList.add("active");
        }
      });
    }, { rootMargin: "-40% 0px -55% 0px" });
    Object.keys(map).forEach(function (id) {
      var sec = document.getElementById(id);
      if (sec) so.observe(sec);
    });
  } else {
    document.querySelectorAll(".reveal").forEach(function (el) { el.classList.add("in"); });
  }

  // ── contact form → POST /api/contact ────────────────────────────────────
  function show(msg, ok, text) {
    msg.textContent = text;
    msg.className = "form-msg show " + (ok ? "ok" : "err");
  }
  document.querySelectorAll("form[data-contact]").forEach(function (form) {
    var msg = form.querySelector(".form-msg");
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var btn = form.querySelector('button[type="submit"]');
      var payload = {
        name: form.elements["name"].value.trim(),
        email: form.elements["email"].value.trim(),
        company: form.elements["company"].value.trim(),
        topic: form.elements["topic"].value,
        message: form.elements["message"].value.trim(),
        website: form.elements["website"].value
      };
      if (!payload.name || !payload.email || !payload.message) {
        show(msg, false, "Please fill in your name, email, and message.");
        return;
      }
      btn.disabled = true;
      fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      }).then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (d) {
          if (r.ok && d && d.ok) {
            form.reset();
            show(msg, true, "Thanks — your message has been sent.");
          } else {
            show(msg, false, (d && d.error) ||
              "Something went wrong. Please email derek@derekcoleman.com instead.");
          }
        });
      }).catch(function () {
        show(msg, false, "Network error — please try again, or email derek@derekcoleman.com.");
      }).finally(function () {
        btn.disabled = false;
      });
    });
  });
})();
