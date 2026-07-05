let papers = [];

const chips = [
  "全部", "CO2", "CH4", "N2O", "水体", "河流", "湖泊", "水库", "湿地", "河口",
  "池塘", "沟渠", "岸带", "消落带", "沉积物", "扩散通量", "冒泡释放", "浮箱法",
  "碳氮循环", "微生物过程", "稳定同位素", "甲烷同位素", "甲烷团簇同位素",
  "同位素示踪", "甲烷来源解析", "δ13C-CH4", "δD-CH4", "δ13C-CO2",
  "clumped isotope", "methane clumped isotope", "stable isotope", "城市水体"
];

const fixedMetrics = [
  ["已收录论文", "0"],
  ["近一年发表", "0"],
  ["总引用数", "0"],
  ["开放 PDF", "0"],
  ["DOI 可用", "0"],
  ["同位素相关", "0"]
];

const state = { chip: "全部", source: "all", query: "" };

const chipFilters = document.querySelector("#chipFilters");
const metricCards = document.querySelector("#metricCards");
const paperRows = document.querySelector("#paperRows");
const resultSummary = document.querySelector("#resultSummary");
const searchInput = document.querySelector("#searchInput");
const sourceSelect = document.querySelector("#sourceSelect");
const pageSizeSelect = document.querySelector("#pageSizeSelect");

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;"
  }[char]));
}

function renderChips() {
  chipFilters.innerHTML = chips.map(chip => (
    `<button class="chip ${chip === state.chip ? "is-active" : ""}" type="button" data-chip="${escapeHtml(chip)}">${escapeHtml(chip)}</button>`
  )).join("");
}

function calculateMetrics() {
  const currentYear = new Date().getFullYear();
  const totalCitations = papers.reduce((sum, paper) => sum + Number(paper.citations || 0), 0);
  const recent = papers.filter(paper => Number(paper.year) >= currentYear - 1).length;
  const openPdf = papers.filter(paper => paper.pdfUrl).length;
  const doiCount = papers.filter(paper => paper.doi).length;
  const isotopeCount = papers.filter(paper => {
    const text = [paper.title, paper.abstract, paper.tags?.join(" ")].join(" ").toLowerCase();
    return text.includes("isotope") || text.includes("δ13c") || text.includes("δd") || text.includes("clumped");
  }).length;

  return [
    ["已收录论文", papers.length],
    ["近一年发表", recent],
    ["总引用数", totalCitations.toLocaleString()],
    ["开放 PDF", openPdf],
    ["DOI 可用", doiCount],
    ["同位素相关", isotopeCount]
  ];
}

function renderMetrics() {
  metricCards.innerHTML = calculateMetrics().map(([label, value]) => (
    `<article class="metric-card"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></article>`
  )).join("");
}

function getFilteredPapers() {
  const q = state.query.trim().toLowerCase();

  return papers.filter(paper => {
    const tags = paper.tags || [];
    const matchesChip = state.chip === "全部" || tags.includes(state.chip);
    const matchesSource = state.source === "all" || paper.source === state.source;
    const haystack = [
      paper.title,
      paper.authors,
      paper.journal,
      paper.year,
      paper.doi,
      paper.source,
      paper.abstract,
      tags.join(" ")
    ].join(" ").toLowerCase();

    return matchesChip && matchesSource && (!q || haystack.includes(q));
  });
}

function renderRows() {
  const filtered = getFilteredPapers();
  const pageSize = Number(pageSizeSelect.value);
  const rows = filtered.slice(0, pageSize);

  resultSummary.textContent = `${state.chip} · ${filtered.length} 篇`;

  if (!rows.length) {
    paperRows.innerHTML = `<tr><td class="empty" colspan="8">没有匹配的论文，请调整关键词或等待自动更新。</td></tr>`;
    return;
  }

  paperRows.innerHTML = rows.map(paper => {
    const title = escapeHtml(paper.title || "Untitled");
    const authors = escapeHtml(paper.authors || "Unknown authors");
    const journal = escapeHtml(paper.journal || "Unknown journal");
    const date = escapeHtml(paper.publicationDate || paper.year || "");
    const citations = escapeHtml(paper.citations || 0);
    const references = escapeHtml(paper.references || 0);
    const source = escapeHtml(paper.source || "Semantic Scholar");
    const tags = paper.tags || [];
    const paperUrl = paper.paperUrl || "#";
    const doiUrl = paper.doi ? `https://doi.org/${encodeURIComponent(paper.doi)}` : "";
    const pdfUrl = paper.pdfUrl || "";

    return `
      <tr>
        <td>${date}</td>
        <td>
          <div class="paper-title">${title}</div>
          <div class="tags">${tags.map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join("")}</div>
        </td>
        <td>${authors}</td>
        <td>${journal}</td>
        <td><strong>${citations}</strong></td>
        <td><strong>${references}</strong></td>
        <td><span class="source-pill">${source}</span></td>
        <td class="links">
          <a href="${escapeHtml(paperUrl)}" target="_blank" rel="noopener">打开</a>
          ${doiUrl ? `<a href="${escapeHtml(doiUrl)}" target="_blank" rel="noopener">DOI</a>` : ""}
          ${pdfUrl ? `<a href="${escapeHtml(pdfUrl)}" target="_blank" rel="noopener">PDF</a>` : ""}
        </td>
      </tr>
    `;
  }).join("");
}

async function loadPapers() {
  try {
    const response = await fetch(`papers.json?v=${Date.now()}`);
    if (!response.ok) throw new Error("papers.json not found");
    papers = await response.json();
  } catch (error) {
    papers = [];
    console.warn("无法读取 papers.json，请确认文件已上传并等待自动更新。", error);
  }

  renderMetrics();
  renderRows();
}

chipFilters.addEventListener("click", event => {
  const button = event.target.closest("button[data-chip]");
  if (!button) return;
  state.chip = button.dataset.chip;
  renderChips();
  renderRows();
});

searchInput.addEventListener("input", event => {
  state.query = event.target.value;
  renderRows();
});

sourceSelect.addEventListener("change", event => {
  state.source = event.target.value;
  renderRows();
});

pageSizeSelect.addEventListener("change", renderRows);

renderChips();
loadPapers();
