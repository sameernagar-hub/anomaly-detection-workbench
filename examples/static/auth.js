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

  function scribbleThemeConfig(theme) {
    const configs = {
      campus: {
        wash: ["rgba(31, 40, 51, 0.06)", "rgba(35, 75, 109, 0.14)", "rgba(179, 86, 59, 0.1)"],
        glyphs: ["#2d3f52", "#3f5d76", "#6b4d45", "#56697b", "#314b41"],
        noise: ["rgba(52, 74, 92, 0.24)", "rgba(179, 86, 59, 0.18)", "rgba(21, 122, 110, 0.18)"],
        dots: ["rgba(35,75,109,0.16)", "rgba(179,86,59,0.12)", "rgba(31,40,51,0.12)"],
      },
      signal: {
        wash: ["rgba(39, 52, 74, 0.05)", "rgba(74, 54, 112, 0.12)", "rgba(13, 148, 136, 0.1)"],
        glyphs: ["#384962", "#5a3ca3", "#245f7d", "#7f5340", "#1c645e"],
        noise: ["rgba(93, 40, 184, 0.18)", "rgba(13, 148, 136, 0.18)", "rgba(56, 73, 98, 0.2)"],
        dots: ["rgba(93,40,184,0.1)", "rgba(13,148,136,0.12)", "rgba(56,73,98,0.12)"],
      },
      midnight: {
        wash: ["rgba(255,255,255,0.04)", "rgba(138, 180, 255, 0.08)", "rgba(91, 214, 176, 0.08)"],
        glyphs: ["#a6c4ff", "#8fe2cf", "#ffb08f", "#d8e5ff", "#b7d8c8"],
        noise: ["rgba(138,180,255,0.18)", "rgba(91,214,176,0.18)", "rgba(255,142,107,0.16)"],
        dots: ["rgba(138,180,255,0.12)", "rgba(91,214,176,0.1)", "rgba(255,255,255,0.08)"],
      },
    };
    return configs[theme] || configs.campus;
  }

  function pick(list) {
    return list[Math.floor(Math.random() * list.length)];
  }

  function drawScribble() {
    const canvas = byId("scribbleCanvas");
    const code = bootstrap.human_payload?.scribble?.code;
    if (!canvas || !code) return;
    const ctx = canvas.getContext("2d");
    const width = canvas.width;
    const height = canvas.height;
    const theme = document.body.dataset.theme || "campus";
    const config = scribbleThemeConfig(theme);
    ctx.clearRect(0, 0, width, height);
    const background = ctx.createLinearGradient(0, 0, width, height);
    background.addColorStop(0, pick(config.wash));
    background.addColorStop(0.5, "rgba(255,255,255,0.02)");
    background.addColorStop(1, pick(config.wash));
    ctx.fillStyle = background;
    ctx.fillRect(0, 0, width, height);

    for (let i = 0; i < 16; i += 1) {
      ctx.strokeStyle = pick(config.noise);
      ctx.lineWidth = 1 + Math.random() * 2.6;
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

    for (let i = 0; i < 8; i += 1) {
      ctx.strokeStyle = pick(config.noise);
      ctx.lineWidth = 1.4 + Math.random() * 2.2;
      ctx.beginPath();
      ctx.moveTo(10 + Math.random() * (width - 20), 14 + Math.random() * (height - 28));
      ctx.lineTo(10 + Math.random() * (width - 20), 14 + Math.random() * (height - 28));
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
      ctx.shadowBlur = theme === "midnight" ? 0 : 1.5;
      ctx.shadowColor = pick(config.noise);
      ctx.fillStyle = config.glyphs[(index + Math.floor(Math.random() * config.glyphs.length)) % config.glyphs.length];
      ctx.fillText(character, 0, 0);
      ctx.restore();
    });

    for (let i = 0; i < 160; i += 1) {
      ctx.fillStyle = pick(config.dots);
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
    window.addEventListener("adw:theme-change", drawScribble);
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
