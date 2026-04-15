(function () {
  const bootstrapElement = document.getElementById("bootstrap-data");
  const bootstrap = bootstrapElement ? JSON.parse(bootstrapElement.textContent) : {};

  function byId(id) {
    return document.getElementById(id);
  }

  function togglePassword(event) {
    const button = event.currentTarget;
    const targetId = button.dataset.target;
    const field = byId(targetId);
    if (!field) return;
    const visible = field.type === "text";
    field.type = visible ? "password" : "text";
    button.textContent = visible ? "Show" : "Hide";
  }

  function updateStrength(password) {
    const bar = byId("passwordStrengthBar");
    const label = byId("passwordStrengthLabel");
    if (!bar || !label) return;
    let score = 0;
    if (password.length >= 12) score += 1;
    if (/[A-Z]/.test(password)) score += 1;
    if (/[a-z]/.test(password)) score += 1;
    if (/\d/.test(password)) score += 1;
    if (/[^A-Za-z0-9]/.test(password)) score += 1;
    if (password.length >= 16) score += 1;
    bar.style.width = `${Math.max(8, score * 16)}%`;
    label.textContent = score <= 2 ? "Needs work" : score <= 4 ? "Solid" : "Strong";
  }

  function initPasswordStrength() {
    const field = document.querySelector("[data-password-strength]");
    if (!field) return;
    updateStrength(field.value || "");
    field.addEventListener("input", () => updateStrength(field.value || ""));
  }

  function drawScribble() {
    const canvas = byId("scribbleCanvas");
    const code = bootstrap.human_payload?.scribble?.code;
    if (!canvas || !code) return;
    const ctx = canvas.getContext("2d");
    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = "rgba(255,255,255,0.16)";
    ctx.fillRect(0, 0, width, height);

    for (let i = 0; i < 12; i += 1) {
      ctx.strokeStyle = `hsla(${Math.random() * 360}, 78%, 62%, 0.22)`;
      ctx.lineWidth = 1 + Math.random() * 2;
      ctx.beginPath();
      ctx.moveTo(Math.random() * width, Math.random() * height);
      ctx.bezierCurveTo(
        Math.random() * width,
        Math.random() * height,
        Math.random() * width,
        Math.random() * height,
        Math.random() * width,
        Math.random() * height
      );
      ctx.stroke();
    }

    ctx.textBaseline = "middle";
    code.split("").forEach((character, index) => {
      const x = 48 + index * 68 + (Math.random() * 12 - 6);
      const y = height / 2 + (Math.random() * 26 - 13);
      ctx.save();
      ctx.translate(x, y);
      ctx.rotate((Math.random() * 0.7) - 0.35);
      ctx.font = `${54 + Math.floor(Math.random() * 8)}px Segoe UI`;
      ctx.fillStyle = ["#234b6d", "#157a6e", "#b3563b", "#3a4e61"][index % 4];
      ctx.fillText(character, 0, 0);
      ctx.restore();
    });

    for (let i = 0; i < 120; i += 1) {
      ctx.fillStyle = `rgba(35,75,109,${Math.random() * 0.12})`;
      ctx.beginPath();
      ctx.arc(Math.random() * width, Math.random() * height, Math.random() * 2.4, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  function initEmojiSelection() {
    const hidden = byId("emoji_choice");
    const options = Array.from(document.querySelectorAll("[data-emoji-choice]"));
    if (!hidden || !options.length) return;
    options.forEach((option) => {
      option.addEventListener("click", () => {
        hidden.value = option.dataset.emojiChoice;
        options.forEach((candidate) => candidate.classList.toggle("active", candidate === option));
      });
    });
  }

  function initHumanVerify() {
    if (!document.querySelector("[data-human-verify]")) return;
    drawScribble();
    initEmojiSelection();
  }

  function initAutoDisplayName() {
    const first = byId("first_name");
    const display = byId("display_name");
    if (!first || !display) return;
    const sync = () => {
      if (!display.dataset.userEdited && !display.value.trim()) {
        display.value = first.value.trim();
      }
    };
    display.addEventListener("input", () => {
      if (display.value.trim()) display.dataset.userEdited = "1";
    });
    first.addEventListener("input", sync);
  }

  document.querySelectorAll("[data-password-toggle]").forEach((button) => {
    button.addEventListener("click", togglePassword);
  });

  initPasswordStrength();
  initHumanVerify();
  initAutoDisplayName();
})();
