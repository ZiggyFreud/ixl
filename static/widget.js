(function () {
  // ── Config ────────────────────────────────────────────────────────────────
  const BOT_ENDPOINT = "https://ixl-bot.onrender.com/chat"; // update after deploy
  const PRIMARY_COLOR = "#1a2b4a";   // IXL navy
  const ACCENT_COLOR  = "#c9a84c";   // IXL gold
  const BOT_NAME      = "IXL Assistant";
  const WELCOME_MSG   = "Hi! I'm the IXL Public Adjuster virtual assistant. I can answer questions about our services, the claims process, and how we can help you maximize your settlement. What can I help you with today?";

  // ── Styles ────────────────────────────────────────────────────────────────
  const style = document.createElement("style");
  style.textContent = `
    #ixl-widget-btn {
      position: fixed; bottom: 24px; right: 24px; z-index: 9999;
      width: 60px; height: 60px; border-radius: 50%;
      background: ${PRIMARY_COLOR}; color: #fff;
      border: none; cursor: pointer; font-size: 26px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.25);
      display: flex; align-items: center; justify-content: center;
      transition: transform 0.2s;
    }
    #ixl-widget-btn:hover { transform: scale(1.08); }

    #ixl-chat-window {
      position: fixed; bottom: 96px; right: 24px; z-index: 9999;
      width: 360px; max-width: calc(100vw - 48px);
      height: 520px; border-radius: 14px;
      background: #fff; box-shadow: 0 8px 32px rgba(0,0,0,0.18);
      display: none; flex-direction: column; overflow: hidden;
      font-family: sans-serif;
    }
    #ixl-chat-window.open { display: flex; }

    #ixl-header {
      background: ${PRIMARY_COLOR}; color: #fff;
      padding: 14px 16px; font-size: 15px; font-weight: 600;
      display: flex; align-items: center; gap: 10px;
    }
    #ixl-header span { font-size: 20px; }

    #ixl-messages {
      flex: 1; overflow-y: auto; padding: 14px;
      display: flex; flex-direction: column; gap: 10px;
      background: #f7f8fa;
    }

    .ixl-msg {
      max-width: 82%; padding: 10px 13px; border-radius: 12px;
      font-size: 14px; line-height: 1.5; word-wrap: break-word;
    }
    .ixl-msg.bot {
      background: #fff; color: #222;
      border: 1px solid #e0e0e0; align-self: flex-start;
      border-bottom-left-radius: 3px;
    }
    .ixl-msg.user {
      background: ${PRIMARY_COLOR}; color: #fff;
      align-self: flex-end; border-bottom-right-radius: 3px;
    }

    #ixl-input-row {
      display: flex; gap: 8px; padding: 12px;
      border-top: 1px solid #e8e8e8; background: #fff;
    }
    #ixl-input {
      flex: 1; padding: 9px 13px; border-radius: 20px;
      border: 1px solid #ddd; font-size: 14px; outline: none;
    }
    #ixl-input:focus { border-color: ${PRIMARY_COLOR}; }
    #ixl-send {
      background: ${ACCENT_COLOR}; color: #fff;
      border: none; border-radius: 20px; padding: 9px 16px;
      font-size: 14px; cursor: pointer; font-weight: 600;
    }
    #ixl-send:hover { opacity: 0.9; }

    .ixl-typing { display: flex; gap: 5px; padding: 8px; align-self: flex-start; }
    .ixl-typing span {
      width: 8px; height: 8px; background: #aaa; border-radius: 50%;
      animation: ixl-bounce 1.2s infinite;
    }
    .ixl-typing span:nth-child(2) { animation-delay: 0.2s; }
    .ixl-typing span:nth-child(3) { animation-delay: 0.4s; }
    @keyframes ixl-bounce {
      0%, 60%, 100% { transform: translateY(0); }
      30% { transform: translateY(-6px); }
    }
  `;
  document.head.appendChild(style);

  // ── HTML ──────────────────────────────────────────────────────────────────
  const btn = document.createElement("button");
  btn.id = "ixl-widget-btn";
  btn.innerHTML = "💬";
  document.body.appendChild(btn);

  const win = document.createElement("div");
  win.id = "ixl-chat-window";
  win.innerHTML = `
    <div id="ixl-header"><span>🏠</span>${BOT_NAME}</div>
    <div id="ixl-messages"></div>
    <div id="ixl-input-row">
      <input id="ixl-input" type="text" placeholder="Type your message..." autocomplete="off" />
      <button id="ixl-send">Send</button>
    </div>
  `;
  document.body.appendChild(win);

  // ── State ─────────────────────────────────────────────────────────────────
  const messages = document.getElementById("ixl-messages");
  const input    = document.getElementById("ixl-input");
  const sendBtn  = document.getElementById("ixl-send");
  let history    = [];
  let isOpen     = false;
  let greeted    = false;

  // ── Functions ─────────────────────────────────────────────────────────────
  function addMsg(text, role) {
    const div = document.createElement("div");
    div.className = `ixl-msg ${role}`;
    div.textContent = text;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }

  function showTyping() {
    const dots = document.createElement("div");
    dots.className = "ixl-typing";
    dots.id = "ixl-typing";
    dots.innerHTML = "<span></span><span></span><span></span>";
    messages.appendChild(dots);
    messages.scrollTop = messages.scrollHeight;
  }

  function hideTyping() {
    const dots = document.getElementById("ixl-typing");
    if (dots) dots.remove();
  }

  async function sendMessage() {
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    addMsg(text, "user");
    history.push({ role: "user", content: text });
    showTyping();
    sendBtn.disabled = true;

    try {
      const res = await fetch(BOT_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, history })
      });
      const data = await res.json();
      hideTyping();
      const reply = data.response || "Sorry, I couldn't get a response. Please try again.";
      addMsg(reply, "bot");
      history.push({ role: "assistant", content: reply });
    } catch {
      hideTyping();
      addMsg("I'm having trouble connecting. Please contact us at (609) 246-0616 or admin@ixlpa.com.", "bot");
    }

    sendBtn.disabled = false;
    input.focus();
  }

  // ── Events ────────────────────────────────────────────────────────────────
  btn.addEventListener("click", () => {
    isOpen = !isOpen;
    win.classList.toggle("open", isOpen);
    if (isOpen && !greeted) {
      addMsg(WELCOME_MSG, "bot");
      greeted = true;
      input.focus();
    }
  });

  sendBtn.addEventListener("click", sendMessage);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendMessage();
  });
})();