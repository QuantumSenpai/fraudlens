async function loadDashboard() {
  const totalEl = document.getElementById("stat-total");
  const flaggedEl = document.getElementById("stat-flagged");
  const rateEl = document.getElementById("stat-rate");
  const listEl = document.getElementById("tx-list");

  try {
    const data = await getStats();

    animateCount(totalEl, data.total_transactions, 0);
    animateCount(flaggedEl, data.flagged_transactions, 0);
    animateCount(rateEl, data.flagged_rate_percent, 1, "%");

    if (data.recent_transactions.length === 0) {
      listEl.innerHTML = `<div class="empty">No transactions yet</div>`;
      return;
    }

    listEl.innerHTML = data.recent_transactions
      .map((txn) => {
        const badge = txn.flagged
          ? `<span class="badge flagged">Flagged</span>`
          : `<span class="badge clean">Clean</span>`;
        return `<div class="row">
          <span>${txn.user_id}</span>
          <span>${txn.device_id}</span>
          <span>₹${txn.amount}</span>
          <span>${txn.final_score}</span>
          ${badge}
        </div>`;
      })
      .join("");

    anime({
      targets: "#tx-list .row",
      opacity: [0, 1],
      translateX: [-14, 0],
      delay: anime.stagger(60),
      duration: 400,
      easing: "easeOutQuad",
    });
  } catch (err) {
    listEl.innerHTML = `<div class="empty">Failed to load: ${err.message}</div>`;
  }
}

function animateCount(el, endValue, decimals, suffix) {
  const obj = { val: 0 };
  anime({
    targets: obj,
    val: endValue,
    round: decimals ? Math.pow(10, decimals) : 1,
    duration: 900,
    easing: "easeOutExpo",
    update: () => {
      el.textContent = (decimals ? obj.val.toFixed(decimals) : obj.val) + (suffix || "");
    },
  });
}

anime({
  targets: ".stat-card",
  opacity: [0, 1],
  translateY: [14, 0],
  delay: anime.stagger(90),
  duration: 500,
  easing: "easeOutQuad",
});

document.getElementById("refresh-btn").addEventListener("click", () => {
  anime({ targets: "#refresh-btn", rotate: "1turn", duration: 500, easing: "easeInOutQuad" });
  loadDashboard();
});

loadDashboard();

anime({
  targets: ".orb-1",
  translateX: [0, 35, -15, 0],
  translateY: [0, 25, -10, 0],
  duration: 13000,
  loop: true,
  easing: "easeInOutSine",
});
anime({
  targets: ".orb-2",
  translateX: [0, -30, 20, 0],
  translateY: [0, -15, 15, 0],
  duration: 15000,
  loop: true,
  easing: "easeInOutSine",
});