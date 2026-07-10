(function () {
  "use strict";
  function show(msg, ok, text) {
    msg.textContent = text;
    msg.className = "form-msg show " + (ok ? "ok" : "err");
  }
  function init(form) {
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
  }
  var forms = document.querySelectorAll("form[data-contact]");
  for (var i = 0; i < forms.length; i++) init(forms[i]);
})();
