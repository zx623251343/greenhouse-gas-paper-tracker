const papers = [
  {
    date: "2026年6月12日",
    title: "Greenhouse gas emissions from river-reservoir continuum: controls of hydrology, sediment carbon, and nitrogen loading",
    authors: "Ying Chen, Hao Wang, Laura Smith 等",
    journal: "Water Research",
    citations: 3,
    references: 86,
    source: "Semantic Scholar",
    url: "#",
    doi: "10.1016/j.watres.2026.00011",
    tags: ["水库", "河流", "CO2", "CH4", "N2O", "通量"]
  },
  {
    date: "2026年5月28日",
    title: "Hot moments of methane ebullition in littoral zones of shallow lakes after water-level fluctuations",
    authors: "Ming Zhao, Qian Chen, Rui Yang",
    journal: "Science of the Total Environment",
    citations: 7,
    references: 94,
    source: "Semantic Scholar",
    url: "#",
    doi: "10.1016/j.scitotenv.2026.00012",
    tags: ["湖泊", "岸带", "消落带", "CH4", "冒泡释放", "水位波动"]
  },
  {
    date: "2026年5月10日",
    title: "Riparian wetlands regulate nitrous oxide emissions through coupled nitrification and denitrification",
    authors: "Hao Sun, Yiting Luo, James Miller",
    journal: "Environmental Microbiology",
    citations: 5,
    references: 78,
    source: "Crossref",
    url: "#",
    doi: "10.1111/emi.2026.00013",
    tags: ["湿地", "岸带", "N2O", "碳氮循环", "微生物过程"]
  },
  {
    date: "2026年4月23日",
    title: "Carbon dioxide and methane fluxes across aquatic-terrestrial interfaces in urban river networks",
    authors: "Yue Zhang, Lin Xu, Peter Wang 等",
    journal: "Biogeosciences",
    citations: 9,
    references: 83,
    source: "PubMed",
    url: "#",
    doi: "10.5194/bg-2026-00014",
    tags: ["城市水体", "河流", "岸带", "CO2", "CH4", "扩散通量"]
  },
  {
    date: "2026年4月4日",
    title: "Sediment methane production and oxidation shape greenhouse gas budgets in reservoir drawdown zones",
    authors: "Jiawen Liu, Ning Ma, Sara Jones",
    journal: "Limnology and Oceanography",
    citations: 13,
    references: 101,
    source: "Semantic Scholar",
    url: "#",
    doi: "10.1002/lno.2026.00015",
    tags: ["水库", "消落带", "沉积物", "CH4", "甲烷氧化", "温室气体预算"]
  },
  {
    date: "2026年3月18日",
    title: "Seasonal controls on CO2 and N2O emissions from eutrophic lakes and adjacent riparian soils",
    authors: "Wei Huang, Chen Li, Min Zhou",
    journal: "Journal of Geophysical Research: Biogeosciences",
    citations: 18,
    references: 69,
    source: "Semantic Scholar",
    url: "#",
    doi: "10.1029/2026JG000016",
    tags: ["湖泊", "岸带", "CO2", "N2O", "富营养化", "季节变化"]
  },
  {
    date: "2026年2月25日",
    title: "Floating chamber measurements reveal spatial heterogeneity of greenhouse gas fluxes in constructed wetlands",
    authors: "Xuan Li, Wenhui Wang, Yunhui Liu 等",
    journal: "Ecological Engineering",
    citations: 11,
    references: 72,
    source: "Crossref",
    url: "#",
    doi: "10.1016/j.ecoleng.2026.00017",
    tags: ["湿地", "CO2", "CH4", "N2O", "浮箱法", "通量"]
  },
  {
    date: "2026年2月6日",
    title: "Global synthesis of methane emissions from ponds, ditches, and small water bodies",
    authors: "Anna Brown, Lei Fang, Maria Garcia",
    journal: "Nature Communications",
    citations: 32,
    references: 128,
    source: "Semantic Scholar",
    url: "#",
    doi: "10.1038/s41467-026-00018",
    tags: ["池塘", "沟渠", "CH4", "全球综合", "小型水体"]
  }
];

const chips = ["全部", "CO2", "CH4", "N2O", "水体", "河流", "湖泊", "水库", "湿地", "河口", "池塘", "沟渠", "岸带", "消落带", "沉积物", "扩散通量", "冒泡释放", "浮箱法", "碳氮循环", "微生物过程", "稳定同位素", "甲烷同位素", "甲烷团簇同位素", "同位素示踪", "甲烷来源解析", "δ13C-CH4", "δD-CH4", "δ13C-CO2", "clumped isotope", "methane clumped isotope", "stable isotope", "城市水体"];
const fixedMetrics = [
  ["近一周发表", "3"],
  ["近一月发表", "12"],
  ["近一年发表", "126"],
  ["总引用数", "9,842"],
  ["开放 PDF", "214"],
  ["岸带相关", "76"]
];

const state = { chip: "岸带", source: "all", query: "" };

const chipFilters = document.querySelector("#chipFilters");
const metricCards = document.querySelector("#metricCards");
const paperRows = document.querySelector("#paperRows");
const resultSummary = document.querySelector("#resultSummary");
const searchInput = document.querySelector("#searchInput");
const sourceSelect = document.querySelector("#sourceSelect");
const pageSizeSelect = document.querySelector("#pageSizeSelect");

function renderChips() {
  chipFilters.innerHTML = chips.map(chip => (
    `<button class="chip ${chip === state.chip ? "is-active" : ""}" type="button" data-chip="${chip}">${chip}</button>`
  )).join("");
}

function renderMetrics() {
  metricCards.innerHTML = fixedMetrics.map(([label, value]) => (
    `<article class="metric-card"><span>${label}</span><strong>${value}</strong></article>`
  )).join("");
}

function getFilteredPapers() {
  const q = state.query.trim().toLowerCase();
  return papers.filter(paper => {
    const matchesChip = state.chip === "全部" || paper.tags.includes(state.chip);
    const matchesSource = state.source === "all" || paper.source === state.source;
    const haystack = [paper.title, paper.authors, paper.journal, paper.doi, paper.source, paper.tags.join(" ")].join(" ").toLowerCase();
    return matchesChip && matchesSource && (!q || haystack.includes(q));
  });
}

function renderRows() {
  const filtered = getFilteredPapers();
  const pageSize = Number(pageSizeSelect.value);
  const rows = filtered.slice(0, pageSize);
  resultSummary.textContent = `${state.chip} · ${filtered.length} 篇`;

  if (!rows.length) {
    paperRows.innerHTML = `<tr><td class="empty" colspan="8">没有匹配的论文，请调整关键词或筛选条件。</td></tr>`;
    return;
  }

  paperRows.innerHTML = rows.map(paper => `
    <tr>
      <td>${paper.date}</td>
      <td>
        <div class="paper-title">${paper.title}</div>
        <div class="tags">${paper.tags.map(tag => `<span class="tag">${tag}</span>`).join("")}</div>
      </td>
      <td>${paper.authors}</td>
      <td>${paper.journal}</td>
      <td><strong>${paper.citations}</strong></td>
      <td><strong>${paper.references}</strong></td>
      <td><span class="source-pill">${paper.source}</span></td>
      <td class="links"><a href="${paper.url}">打开</a><a href="https://doi.org/${paper.doi}">DOI</a></td>
    </tr>
  `).join("");
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
renderMetrics();
renderRows();
