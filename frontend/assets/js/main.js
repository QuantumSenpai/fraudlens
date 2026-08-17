const form = document.getElementById("predict-form");
const resultBox = document.getElementById("result");
const errorBox = document.getElementById("error");
const submitBtn = document.getElementById("submit-btn");

const timestampInput = document.getElementById("timestamp");
if (timestampInput && !timestampInput.value) {
  const now = new Date();
  now.setSeconds(0, 0);
  timestampInput.value = now.toISOString().slice(0, 16);
}

anime({
  targets: ".card label, .card input, .card button",
  opacity: [0, 1],
  translateY: [12, 0],
  delay: anime.stagger(35),
  duration: 500,
  easing: "easeOutQuad",
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  errorBox.style.display = "none";
  resultBox.style.display = "none";
  submitBtn.disabled = true;
  submitBtn.textContent = "Checking...";

  anime({
    targets: submitBtn,
    scale: [1, 0.97, 1],
    duration: 300,
    easing: "easeInOutQuad",
  });

  const txn = {
    user_id: document.getElementById("user_id").value,
    device_id: document.getElementById("device_id").value,
    amount: parseFloat(document.getElementById("amount").value),
    time: parseFloat(document.getElementById("time").value),
    lat: parseFloat(document.getElementById("lat").value),
    lon: parseFloat(document.getElementById("lon").value),
    timestamp: document.getElementById("timestamp").value + ":00",
  };

  try {
    const data = await predictTransaction(txn);
    renderResult(data);
  } catch (err) {
    errorBox.textContent = "Prediction failed: " + err.message;
    errorBox.style.display = "block";
    anime({
      targets: errorBox,
      translateX: [-8, 8, -6, 6, -3, 3, 0],
      duration: 400,
      easing: "easeInOutSine",
    });
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Check transaction";
  }
});

function animateCount(el, endValue, decimals) {
  const obj = { val: 0 };
  anime({
    targets: obj,
    val: endValue,
    round: decimals ? Math.pow(10, decimals) : 1,
    duration: 900,
    easing: "easeOutExpo",
    update: () => {
      el.textContent = decimals ? obj.val.toFixed(decimals) : obj.val;
    },
  });
}

function renderResult(data) {
  resultBox.style.display = "block";
  const flaggedClass = data.flagged ? "flagged" : "";

  let html = `<div class="score-card ${flaggedClass}">`;
  html += `<div class="verdict"><span class="dot ${data.flagged ? "flagged" : "safe"}"></span>${data.flagged ? "Flagged" : "Clean"}</div>`;
  html += `<div class="score-row"><span>ML score</span><span id="v-ml">0</span></div>`;
  html += `<div class="score-row"><span>Rule score</span><span id="v-rule">0</span></div>`;
  html += `<div class="score-row"><span>Final score</span><span id="v-final">0</span></div>`;

  if (data.triggered_rules.length > 0) {
    html += `<div class="rules">`;
    data.triggered_rules.forEach((r) => {
      html += `<div class="rule"><b>${r.rule}</b> — ${r.detail} (+${r.weight})</div>`;
    });
    html += `</div>`;
  }
  html += `</div>`;

  resultBox.innerHTML = html;

  const card = resultBox.querySelector(".score-card");
  anime({
    targets: card,
    opacity: [0, 1],
    translateY: [16, 0],
    scale: [0.96, 1],
    duration: 500,
    easing: "easeOutQuad",
  });

  const dot = resultBox.querySelector(".dot");
  if (data.flagged) {
    anime({
      targets: dot,
      scale: [1, 1.6, 1],
      duration: 700,
      loop: 2,
      easing: "easeInOutSine",
    });
  }

  animateCount(document.getElementById("v-ml"), data.ml_score, 2);
  animateCount(document.getElementById("v-rule"), data.rule_score, 0);
  animateCount(document.getElementById("v-final"), data.final_score, 2);

  const rules = resultBox.querySelectorAll(".rule");
  if (rules.length) {
    anime({
      targets: rules,
      opacity: [0, 1],
      translateX: [-10, 0],
      delay: anime.stagger(80, { start: 400 }),
      duration: 350,
      easing: "easeOutQuad",
    });
  }
}

anime({
  targets: ".orb-1",
  translateX: [0, 30, -10, 0],
  translateY: [0, 20, -15, 0],
  duration: 12000,
  loop: true,
  easing: "easeInOutSine",
});
anime({
  targets: ".orb-2",
  translateX: [0, -25, 15, 0],
  translateY: [0, -20, 10, 0],
  duration: 14000,
  loop: true,
  easing: "easeInOutSine",
});

submitBtn.addEventListener("mouseenter", () => {
  anime({ targets: submitBtn, translateY: -2, duration: 200, easing: "easeOutQuad" });
});
submitBtn.addEventListener("mouseleave", () => {
  anime({ targets: submitBtn, translateY: 0, duration: 200, easing: "easeOutQuad" });
});