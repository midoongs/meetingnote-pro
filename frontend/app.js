// 모든 화면이 함께 쓰는 도우미 - API 호출 · 토큰 · 팀 정보 · 공통 클래스 적용
// 클래스는 화면에서 조합하지 않는다. window.UI 의 이름을 data-ui 로 적으면 여기서 붙인다
(function () {
  const KEY = { token: "token", team: "team_id", role: "role" };
  const store = {
    get: (k) => { try { return localStorage.getItem(KEY[k]); } catch (_) { return null; } },
    set: (k, v) => { try { v == null ? localStorage.removeItem(KEY[k]) : localStorage.setItem(KEY[k], v); } catch (_) {} },
  };

  const App = (window.App = {
    store,

    token: () => store.get("token"),
    teamId: () => store.get("team"),
    role: () => store.get("role"),

    // 로그인 · 가입 · 합류 · 팀 생성 응답의 team_id 를 저장한다
    saveSession(token, teamId, role) {
      if (token) store.set("token", token);
      store.set("team", teamId == null ? null : String(teamId));
      store.set("role", role || null);
    },

    clearSession() {
      ["token", "team", "role"].forEach((k) => store.set(k, null));
    },

    // API 호출. 실패하면 {status, code, msg} 를 던진다
    async api(method, path, body, form) {
      const headers = {};
      if (App.token()) headers.Authorization = "Bearer " + App.token();
      let payload;
      if (form) payload = form;
      else if (body !== undefined) { headers["Content-Type"] = "application/json"; payload = JSON.stringify(body); }
      let res;
      try {
        res = await fetch("/api" + path, { method, headers, body: payload });
      } catch (_) {
        throw { status: 0, code: "NETWORK", msg: "서버에 연결할 수 없음" };
      }
      if (res.status === 204) return null;
      let data = null;
      try { data = await res.json(); } catch (_) {}
      if (!res.ok) {
        const err = { status: res.status, code: (data && data.code) || "ERROR", msg: (data && data.msg) || "오류" };
        // 24시간이 지난 토큰 - 토큰을 지우고 로그인 화면으로 보낸다
        if (err.code === "TOKEN_EXPIRED") {
          App.clearSession();
          location.href = "/login.html?expired=1";
          return new Promise(() => {});   // 화면이 바뀌는 중이므로 뒤 작업을 이어 가지 않는다
        }
        throw err;
      }
      return data;
    },

    // 로그인하지 않았으면 로그인 화면으로 보낸다
    requireLogin() {
      if (!App.token()) { location.href = "/login.html"; return false; }
      return true;
    },

    // 내 정보를 읽어 팀 정보를 갱신한다. needTeam 이면 팀이 없을 때 팀 화면으로 보낸다
    async loadMe(needTeam) {
      const me = await App.api("GET", "/auth/me");
      App.saveSession(null, me.team_id, me.role);
      const chip = document.getElementById("teamName");
      if (chip) chip.textContent = me.team_name || "";
      if (needTeam && me.team_id == null) { location.href = "/team.html"; return null; }
      return me;
    },

    logout() {
      return App.api("POST", "/auth/logout").catch(() => {}).then(() => {
        App.clearSession();
        location.href = "/login.html";
      });
    },

    // 서버의 UTC ISO 시각을 현지 시간으로 보인다
    when(iso) {
      if (!iso) return "";
      const d = new Date(iso);
      const p = (n) => String(n).padStart(2, "0");
      return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
    },

    // 활동 · 댓글 시각은 짧게
    ago(iso) {
      const d = new Date(iso);
      const p = (n) => String(n).padStart(2, "0");
      const t = `${p(d.getHours())}:${p(d.getMinutes())}`;
      const now = new Date();
      const days = Math.floor((new Date(now.getFullYear(), now.getMonth(), now.getDate()) -
        new Date(d.getFullYear(), d.getMonth(), d.getDate())) / 864e5);
      if (days === 0) return "오늘 " + t;
      if (days === 1) return "어제 " + t;
      return `${d.getMonth() + 1}월 ${d.getDate()}일`;
    },

    esc(s) {
      return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
    },

    // 기한 지남 판정은 화면이 한다 (서버는 비교하지 않음). 완료한 것은 제외
    isLate(t) {
      if (t.status === "DONE") return false;
      return /^(어제|지난\s?(주|달)|그제)/.test(t.due_text || "") || /^\d{4}-\d{2}-\d{2}$/.test(t.due_text || "") && new Date(t.due_text) < new Date(new Date().toDateString());
    },

    // data-ui="btnPrimary" 처럼 적힌 요소에 window.UI 의 클래스를 붙인다
    applyUI(root) {
      (root || document).querySelectorAll("[data-ui]").forEach((el) => {
        el.className = (el.className ? el.className + " " : "") + el.dataset.ui.split(/\s+/).map((n) => window.UI[n] || "").join(" ");
        el.removeAttribute("data-ui");
      });
    },
  });

  document.addEventListener("DOMContentLoaded", () => {
    const slot = document.getElementById("themeSlot");
    if (slot) slot.innerHTML = window.THEME_BTN;
    window.initTheme(() => { if (window.onThemeChange) window.onThemeChange(); });
    App.applyUI();
  });
})();
