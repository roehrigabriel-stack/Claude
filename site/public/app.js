const $ = (id) => document.getElementById(id);

let password = "";
try {
  password = sessionStorage.getItem("password") || "";
} catch {}

// --- Mini rendu Markdown ---------------------------------------------------
// Le texte est echappe avant toute mise en forme : rien de ce que renvoie
// l'IA n'est interprete comme du HTML.

function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function inline(text) {
  return escapeHtml(text)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*\s][^*]*)\*/g, "$1<em>$2</em>");
}

function renderMarkdown(source) {
  const html = [];
  let list = null;
  let paragraph = [];
  let code = null;

  const closeParagraph = () => {
    if (paragraph.length) html.push(`<p>${paragraph.join("<br>")}</p>`);
    paragraph = [];
  };
  const closeList = () => {
    if (list) html.push(`</${list}>`);
    list = null;
  };

  for (const line of source.split("\n")) {
    if (line.trim().startsWith("```")) {
      if (code === null) {
        closeParagraph();
        closeList();
        code = [];
      } else {
        html.push(`<pre><code>${escapeHtml(code.join("\n"))}</code></pre>`);
        code = null;
      }
      continue;
    }
    if (code !== null) {
      code.push(line);
      continue;
    }

    const heading = line.match(/^(#{1,4})\s+(.*)$/);
    const bullet = line.match(/^\s*[-*]\s+(.*)$/);
    const numbered = line.match(/^\s*\d+[.)]\s+(.*)$/);

    if (heading) {
      closeParagraph();
      closeList();
      const level = Math.min(Math.max(heading[1].length, 2), 3);
      html.push(`<h${level}>${inline(heading[2])}</h${level}>`);
    } else if (bullet || numbered) {
      closeParagraph();
      const type = bullet ? "ul" : "ol";
      if (list !== type) {
        closeList();
        html.push(`<${type}>`);
        list = type;
      }
      html.push(`<li>${inline((bullet || numbered)[1])}</li>`);
    } else if (!line.trim()) {
      closeParagraph();
      closeList();
    } else {
      closeList();
      paragraph.push(inline(line.trim()));
    }
  }
  if (code !== null) html.push(`<pre><code>${escapeHtml(code.join("\n"))}</code></pre>`);
  closeParagraph();
  closeList();
  return html.join("");
}

// --- Appels au serveur -----------------------------------------------------

function context() {
  return { subject: $("subject").value, level: $("level").value };
}

function askPassword() {
  return new Promise((resolve) => {
    const dialog = $("password-dialog");
    $("password-input").value = "";
    dialog.addEventListener(
      "close",
      () => {
        password = $("password-input").value;
        try {
          sessionStorage.setItem("password", password);
        } catch {}
        resolve();
      },
      { once: true },
    );
    dialog.showModal();
  });
}

async function post(url, body) {
  for (;;) {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Site-Password": password },
      body: JSON.stringify({ ...context(), ...body }),
    });
    if (response.status === 401) {
      await askPassword();
      continue;
    }
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || `Erreur ${response.status}`);
    }
    return response;
  }
}

// Lit une reponse au fil de l'eau et appelle onText avec le texte cumule.
async function readStream(response, onText) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let text = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    text += decoder.decode(value, { stream: true });
    onText(text);
  }
  return text;
}

function showError(target, error) {
  target.classList.remove("loading");
  target.innerHTML = `<p class="error">${escapeHtml(error.message)}</p>`;
}

async function withBusy(form, task) {
  const buttons = form.querySelectorAll("button");
  buttons.forEach((b) => (b.disabled = true));
  try {
    await task();
  } finally {
    buttons.forEach((b) => (b.disabled = false));
  }
}

// --- Onglets ---------------------------------------------------------------

document.querySelectorAll(".tabs button").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tabs button").forEach((t) => {
      t.setAttribute("aria-selected", String(t === tab));
    });
    document.querySelectorAll(".panel").forEach((panel) => {
      panel.hidden = panel.id !== tab.dataset.tab;
    });
  });
});

// --- Explication -----------------------------------------------------------

let history = [];

function addMessage(role, text) {
  const chat = $("chat");
  chat.querySelector(".hint")?.remove();
  const el = document.createElement("div");
  el.className = `msg ${role}${role === "assistant" ? " md" : ""}`;
  el.textContent = text;
  chat.append(el);
  el.scrollIntoView({ block: "nearest" });
  return el;
}

$("explain-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const question = $("question").value.trim();
  if (!question) return;
  $("question").value = "";
  addMessage("user", question);
  history.push({ role: "user", content: question });
  const bubble = addMessage("assistant", "");
  bubble.classList.add("loading");

  withBusy(event.target, async () => {
    try {
      const response = await post("/api/explain", { messages: history });
      const answer = await readStream(response, (text) => {
        bubble.classList.remove("loading");
        bubble.innerHTML = renderMarkdown(text);
      });
      history.push({ role: "assistant", content: answer });
    } catch (error) {
      history.pop();
      showError(bubble, error);
    }
  });
});

$("question").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    $("explain-form").requestSubmit();
  }
});

$("reset-chat").addEventListener("click", () => {
  history = [];
  $("chat").innerHTML = '<p class="hint">Nouvelle conversation. Pose ta question.</p>';
});

// --- Fiche -----------------------------------------------------------------

let sheetText = "";

$("sheet-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const output = $("sheet-output");
  output.textContent = "Rédaction de la fiche";
  output.classList.add("loading");
  $("copy-sheet").hidden = $("print-sheet").hidden = true;

  withBusy(event.target, async () => {
    try {
      const response = await post("/api/sheet", {
        topic: $("sheet-topic").value,
        notes: $("sheet-notes").value,
      });
      sheetText = await readStream(response, (text) => {
        output.classList.remove("loading");
        output.innerHTML = renderMarkdown(text);
      });
      $("copy-sheet").hidden = $("print-sheet").hidden = false;
    } catch (error) {
      showError(output, error);
    }
  });
});

$("copy-sheet").addEventListener("click", async () => {
  await navigator.clipboard.writeText(sheetText);
  $("copy-sheet").textContent = "Copié";
  setTimeout(() => ($("copy-sheet").textContent = "Copier"), 1500);
});

$("print-sheet").addEventListener("click", () => window.print());

// --- Quiz ------------------------------------------------------------------

function renderQuiz(questions) {
  const output = $("quiz-output");
  output.innerHTML = "";
  let answered = 0;
  let correct = 0;

  const score = document.createElement("p");
  score.className = "score";
  score.hidden = true;

  questions.forEach((q, index) => {
    const block = document.createElement("div");
    block.className = "question";
    const title = document.createElement("h3");
    title.textContent = `${index + 1}. ${q.question}`;
    const choices = document.createElement("div");
    choices.className = "choices";
    const explanation = document.createElement("p");
    explanation.className = "explanation";
    explanation.hidden = true;
    explanation.textContent = q.explanation;

    q.choices.forEach((choice, choiceIndex) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "choice";
      button.textContent = choice;
      button.addEventListener("click", () => {
        const buttons = choices.querySelectorAll("button");
        buttons.forEach((b) => (b.disabled = true));
        buttons[q.answer_index].classList.add("correct");
        if (choiceIndex === q.answer_index) correct += 1;
        else button.classList.add("wrong");
        explanation.hidden = false;
        answered += 1;
        if (answered === questions.length) {
          score.textContent = `Score : ${correct} / ${questions.length}`;
          score.hidden = false;
          score.scrollIntoView({ block: "nearest" });
        }
      });
      choices.append(button);
    });

    block.append(title, choices, explanation);
    output.append(block);
  });
  output.append(score);
}

$("quiz-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const output = $("quiz-output");
  output.textContent = "Préparation du quiz";
  output.classList.add("loading");

  withBusy(event.target, async () => {
    try {
      const response = await post("/api/quiz", {
        topic: $("quiz-topic").value,
        count: Number($("quiz-count").value),
      });
      const data = await response.json();
      output.classList.remove("loading");
      renderQuiz(data.questions);
    } catch (error) {
      showError(output, error);
    }
  });
});

// --- Demarrage -------------------------------------------------------------

const config = await fetch("/api/config").then((r) => r.json());
for (const subject of config.subjects) $("subject").add(new Option(subject));
for (const level of config.levels) $("level").add(new Option(level));
