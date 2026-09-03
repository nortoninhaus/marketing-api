(() => {
  "use strict";

  /* ========================================================================== */
  /* 1. Global Data & Constants                                                 */
  /* ========================================================================== */
  const data = window.REPORT_DATA || {};
  const meta = data.meta || {};
  const summary = data.summary || {};
  const rates = data.rates || {};
  const deltas = data.deltas || {};
  const byPlatform = data.by_platform || {};
  const series = Array.isArray(data.daily_series) ? data.daily_series : [];
  const rows = data.rows || {};
  const breakdowns = data.breakdowns || {};
  const narratives = Array.isArray(data.narratives) ? data.narratives : [];

  const labels = new Map([
    ["spend", "Inversión"],
    ["impressions", "Impresiones"],
    ["reach", "Alcance"],
    ["clicks", "Clics"],
    ["conversions", "Conversiones"],
    ["results", "Resultados"],
    ["lead", "Clientes potenciales"],
    ["engagement", "Interacciones"],
    ["post_engagement", "Interacciones con publicaciones"],
    ["followers", "Seguidores"],
    ["views", "Visualizaciones"],
    ["video_views", "Vistas de video"],
    ["likes", "Me gusta"],
    ["comments", "Comentarios"],
    ["shares", "Veces compartido"],
    ["ctr", "CTR"],
    ["cpc", "CPC"],
    ["cpm", "CPM"],
    ["cpa", "CPA"],
    ["conversion_rate", "Tasa de conversión"]
  ]);

  const money = new Set(["spend", "cpc", "cpm", "cpa", "cost", "cost_per_result"]);
  const percent = new Set(["ctr", "conversion_rate", "share"]);
  const priority = [
    "spend", "impressions", "reach", "engagement", "followers",
    "views", "video_views", "clicks", "conversions", "likes", "comments", "shares"
  ];

  /* ========================================================================== */
  /* 2. Formatters, Helpers & Safe Property Accessors                          */
  /* ========================================================================== */
  const getProp = (obj, key) => (obj && typeof obj === "object" && Object.hasOwn(obj, key)) ? Reflect.get(obj, key) : undefined;
  const setProp = (obj, key, val) => { if (obj && typeof obj === "object") Reflect.set(obj, key, val); };
  const number = value => typeof value === "number" && Number.isFinite(value);

  // Cached Intl formatters for high performance rendering
  const fmtCurrency = new Intl.NumberFormat("es-EC", { style: "currency", currency: "USD", maximumFractionDigits: 2 });
  const fmtPercent = new Intl.NumberFormat("es-EC", { maximumFractionDigits: 2 });
  const fmtCompact = new Intl.NumberFormat("es-EC", { notation: "compact", maximumFractionDigits: 0 });
  const fmtStandard = new Intl.NumberFormat("es-EC", { notation: "standard", maximumFractionDigits: 0 });
  const fmtNumber = new Intl.NumberFormat("es-EC");
  const fmtDate = new Intl.DateTimeFormat("es-EC", { day: "2-digit", month: "short", year: "numeric", timeZone: "UTC" });

  const SVG_NS = "http:" + "//www.w3.org/2000/svg";

  const element = (tag, className, value) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (value !== undefined && value !== null) node.textContent = String(value);
    return node;
  };

  const svgElement = (tag, attrs = {}, textContent = null) => {
    const el = document.createElementNS(SVG_NS, tag);
    for (const [k, v] of Object.entries(attrs)) {
      el.setAttribute(k, v);
    }
    if (textContent !== null && textContent !== undefined) {
      el.textContent = textContent;
    }
    return el;
  };

  const show = (node, visible) => {
    if (node) node.hidden = !visible;
    return visible;
  };

  const metricLabel = key => labels.get(key) || String(key).replaceAll("_", " ").replace(/\b\w/g, letter => letter.toUpperCase());
  const platformLabel = key => String(key).replaceAll("_", " ").replace(/\b\w/g, letter => letter.toUpperCase());

  const format = (key, value) => {
    if (!number(value)) return "";
    if (money.has(key)) return fmtCurrency.format(value);
    if (percent.has(key) || key.startsWith("delta_")) return fmtPercent.format(value) + "%";
    return (Math.abs(value) >= 10000000 ? fmtCompact : fmtStandard).format(value);
  };

  const formatDate = value => {
    if (!value) return "";
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? String(value) : fmtDate.format(parsed);
  };

  const ordered = values => {
    const keys = Object.entries(values || {}).filter(([, value]) => number(value)).map(([key]) => key);
    return [...new Set([...priority.filter(key => keys.includes(key)), ...keys.sort()])];
  };

  const canonical = value => {
    const source = String(value || "").toLowerCase().trim();
    if (source.includes("instagram") || source === "threads") return "instagram";
    if (source.includes("facebook") || source === "whatsapp" || source === "unknown") return "facebook";
    if (source.includes("tiktok")) return "tiktok";
    return source;
  };

  const metaPublisher = value => {
    const source = canonical(value);
    if (!source || isMeta(source) || source === "audience_network" || source === "messenger") return source;
    return source === "instagram" || source === "threads" ? "instagram" : "facebook";
  };

  const isMeta = value => {
    const source = String(value || "").toLowerCase();
    return source === "meta" || source.startsWith("meta_") || source.startsWith("meta ");
  };

  const rowPlatform = row => {
    const source = row.source_platform || row.platform || (row.source_metrics || {}).platform;
    const publisher = row.publisher_platform || (row.source_metrics || {}).publisher_platform;
    return isMeta(source) ? metaPublisher(publisher || row.platform || source) : canonical(row.platform || source);
  };

  const setPanel = (id, visible) => {
    const node = document.getElementById(id);
    if (node) {
      show(node, visible);
      if (!visible) node.classList.remove("active");
    }
    const navBtn = document.querySelector('.tab-btn[data-target="' + id + '"]');
    if (navBtn) show(navBtn, visible);
    ["general", "redes", "optimizacion"].forEach(mainId => {
      const subNav = document.getElementById("subnav-" + mainId);
      const mainBtn = document.querySelector('.main-tab-btn[data-main-tab="' + mainId + '"]');
      if (subNav && mainBtn) {
        const hasVisible = [...subNav.querySelectorAll(".tab-btn")].some(b => !b.hidden);
        show(mainBtn, hasVisible);
      }
    });
  };

  const summaryAllowedKeys = ["spend", "impressions", "reach", "engagement", "post_engagement", "followers", "video_views", "views"];
  const summaryCustomLabels = new Map([
    ["spend", "INVERSIÓN EJECUTADA"],
    ["impressions", "IMPRESIONES"],
    ["reach", "ALCANCE"],
    ["engagement", "INTERACCIONES"],
    ["post_engagement", "INTERACCIONES"],
    ["followers", "SEGUIDORES"],
    ["views", "VIS. DE VIDEO"],
    ["video_views", "VIS. DE VIDEO"]
  ]);

  const platformCustomLabels = new Map([
    ["facebook", new Map([
      ["spend", "INVERSIÓN FB"],
      ["impressions", "IMPRESIONES"],
      ["reach", "ALCANCE"],
      ["engagement", "INTERACCIONES"],
      ["followers", "SEGUIDORES"],
      ["video_views", "VIS. DE VIDEO"]
    ])],
    ["instagram", new Map([
      ["spend", "INVERSIÓN IG"],
      ["impressions", "IMPRESIONES"],
      ["reach", "ALCANCE"],
      ["engagement", "INTERACCIONES"],
      ["followers", "SEGUIDORES"],
      ["video_views", "VIS. DE VIDEO"]
    ])],
    ["tiktok", new Map([
      ["spend", "INVERSIÓN TIKTOK"],
      ["impressions", "IMPRESIONES"],
      ["reach", "ALCANCE"],
      ["engagement", "INTERACCIONES"],
      ["followers", "SEGUIDORES"],
      ["video_views", "VIS. DE VIDEO"]
    ])]
  ]);

  const deltaAliases = new Map([
    ["engagement", ["engagement", "post_engagement", "total_interactions", "accounts_engaged"]],
    ["post_engagement", ["post_engagement", "engagement", "total_interactions"]],
    ["video_views", ["video_views", "views", "video_play_actions", "plays"]],
    ["views", ["views", "video_views", "video_play_actions", "plays"]],
    ["followers", ["followers", "follower_count", "follows", "page_fans", "page_follows"]],
    ["spend", ["spend", "social_spend", "cost"]],
    ["clicks", ["clicks", "unique_clicks"]],
    ["conversions", ["conversions", "actions", "purchase", "lead"]]
  ]);

  /* ========================================================================== */
  /* 3. KPI Renderer                                                            */
  /* ========================================================================== */
  const renderKpis = (id, values, withDeltas = false, allowedKeys = null, customLabels = null, platformName = null) => {
    const container = document.getElementById(id);
    if (!container) return 0;
    container.replaceChildren();
    let keys = ordered(values);
    if (id === "summary-kpis") {
      keys = ["spend", "impressions", "reach", "engagement", "followers", "video_views"];
    } else {
      const skipMetrics = new Set(["video_play_actions", "plays", "cost_per_result", "cpc", "cpm", "ctr", "frequency", "__results__"]);
      if (keys.includes("video_views") && keys.includes("views")) skipMetrics.add("video_views");
      if (keys.includes("engagement") && keys.includes("post_engagement")) skipMetrics.add("post_engagement");
      if (keys.includes("followers") && keys.includes("follows")) skipMetrics.add("follows");
      if (keys.includes("followers") && keys.includes("follower_count")) skipMetrics.add("follower_count");
      if (keys.includes("conversions") && keys.includes("results")) skipMetrics.add("results");
      keys = keys.filter(k => !skipMetrics.has(k) && number(getProp(values, k)));
    }
    keys.forEach(key => {
      let val = getProp(values, key);
      if (!number(val)) {
        if (key === "video_views" && number(getProp(values, "views"))) val = getProp(values, "views");
        else if (key === "engagement" && number(getProp(values, "post_engagement"))) val = getProp(values, "post_engagement");
        else if (key === "followers" && number(getProp(values, "follower_count"))) val = getProp(values, "follower_count");
        else if (key === "followers" && number(getProp(values, "follows"))) val = getProp(values, "follows");
        else if (id === "summary-kpis") val = 0;
      }
      if (!number(val) && id !== "summary-kpis") return;
      const card = element("article", "card stat-card");
      card.dataset.family = "kpi";
      card.dataset.metric = key;
      const lbl = (customLabels && customLabels.get?.(key)) || (id === "summary-kpis" && summaryCustomLabels.get(key)) || metricLabel(key);
      card.append(element("div", "stat-label", lbl), element("div", "stat-value", format(key, val)));
      if (withDeltas) {
        const resolvedDeltaKey = (deltaAliases.get(key) || [key]).find(k => number(getProp(deltas, k)));
        let delta = resolvedDeltaKey ? getProp(deltas, resolvedDeltaKey) : (number(getProp(deltas, key)) ? getProp(deltas, key) : null);
        if (!number(delta) && platformName) {
          const pDeltaKey = (deltaAliases.get(key) || [key]).map(k => platformName + "_" + k).find(k => number(getProp(deltas, k)));
          if (pDeltaKey) delta = getProp(deltas, pDeltaKey);
        }
        if (number(delta)) {
          const deltaSuffix = " vs Mes Ant.";
          card.append(element("div", "stat-delta " + (delta > 0 ? "up" : delta < 0 ? "down" : "neutral"), (delta > 0 ? "↑ " : delta < 0 ? "↓ " : "") + format("delta_" + key, Math.abs(delta)) + deltaSuffix));
        }
      }
      container.append(card);
    });
    return container.children.length;
  };

  /* ========================================================================== */
  /* 4. Global Metadata & Data Transformation                                   */
  /* ========================================================================== */
  const company = meta.company_name || "Cuenta seleccionada";
  const period = meta.period || {};
  const periodText = [formatDate(period.start), formatDate(period.end)].filter(Boolean).join(" — ");
  document.getElementById("company-name").textContent = company;
  document.getElementById("report-period").textContent = periodText;
  document.getElementById("generated-at").textContent = formatDate(meta.generated_at);
  document.getElementById("footer-company").textContent = company;
  document.getElementById("footer-period").textContent = periodText;
  (Array.isArray(meta.platforms) ? meta.platforms : []).forEach(value => {
    document.getElementById("hero-platforms").append(element("span", "chip", platformLabel(String(value))));
  });

  const platformEntries = Object.entries(byPlatform).filter(([, metrics]) => metrics && typeof metrics === "object");
  const platformSpend = platformEntries.reduce((total, [, metrics]) => total + (number(metrics.spend) ? metrics.spend : 0), 0);
  const metricRows = [...(Array.isArray(rows.current) ? rows.current : []), ...(Array.isArray(rows.supplemental) ? rows.supplemental : [])];
  const rankingContentRows = Array.isArray(rows.content) && rows.content.length ? rows.content : metricRows;
  const rankingItemsFor = network => rankingContentRows.flatMap(item => {
    const networkUrl = getProp(item, network + "_url") || "";
    if (networkUrl) return [{ ...item, url: networkUrl, permalink_url: networkUrl, platform: network, publisher_platform: network, post_platform: network }];
    return rowPlatform(item) === network ? [item] : [];
  });
  const tiktokRows = metricRows.filter(item => rowPlatform(item) === "tiktok");
  const hasMetaPublisherIdentity = metricRows.some(item => isMeta(item.source_platform) && !isMeta(rowPlatform(item)));
  const hasDirectMetaChannels = platformEntries.some(([key]) => ["facebook", "instagram"].includes(canonical(key)));
  const metaEntry = platformEntries.find(([key]) => isMeta(key));
  const aliasMetrics = new Map([
    ["social_spend", "spend"],
    ["cost", "spend"],
    ["unique_clicks", "clicks"],
    ["actions", "conversions"],
    ["purchase", "conversions"],
    ["add_to_cart", "conversions"],
    ["lead", "conversions"],
    ["total_interactions", "engagement"],
    ["accounts_engaged", "engagement"],
    ["like_count", "likes"],
    ["comment_count", "comments"],
    ["__results__", "results"]
  ]);
  const metaMetricKeys = Object.keys(metaEntry?.[1] || {}).map(key => aliasMetrics.get(key) || key);
  const metricSources = new Map([
    ["spend", ["spend", "social_spend", "cost"]],
    ["clicks", ["clicks", "unique_clicks"]],
    ["conversions", ["conversions", "actions", "purchase", "add_to_cart", "lead"]],
    ["engagement", ["engagement", "total_interactions", "accounts_engaged", "likes", "comments", "shares", "saved"]],
    ["impressions", ["impressions", "reach", "views"]],
    ["reach", ["reach", "impressions", "views"]],
    ["likes", ["likes", "like_count"]],
    ["comments", ["comments", "comment_count"]],
    ["results", ["results", "__results__"]]
  ]);
  const rowMetrics = item => {
    const source = item.source_metrics && typeof item.source_metrics === "object" ? item.source_metrics : {};
    const keys = new Set([...Object.keys(source).map(key => aliasMetrics.get(key) || key), ...metaMetricKeys]);
    const values = {};
    keys.forEach(key => {
      const sources = metricSources.get(key) || [key];
      const raw = sources.find(sourceKey => (sourceKey === key || aliasMetrics.get(sourceKey) === key) && number(getProp(source, sourceKey)));
      if (raw !== undefined) {
        setProp(values, key, getProp(source, raw));
        return;
      }
      const supplied = sources.some(sourceKey => Object.hasOwn(source, sourceKey));
      if (supplied && number(getProp(item, key))) setProp(values, key, getProp(item, key));
    });
    return values;
  };
  const aggregateRows = items => items.reduce((totals, item) => {
    Object.entries(rowMetrics(item)).forEach(([key, value]) => {
      setProp(totals, key, (getProp(totals, key) || 0) + value);
    });
    return totals;
  }, {});
  const sharedMeta = Boolean(metaEntry && !hasMetaPublisherIdentity && !hasDirectMetaChannels);
  const metaSeries = series.filter(item => isMeta(item.platform));

  const publisherLabels = new Map([
    ["facebook", "Facebook"],
    ["instagram", "Instagram"],
    ["tiktok", "TikTok"],
    ["audience_network", "Audience Network"],
    ["messenger", "Messenger"],
    ["google_ads", "Google Ads"]
  ]);

  const publisherColors = new Map([
    ["facebook", "#1877F2"],
    ["instagram", "#E1306C"],
    ["tiktok", "#000000"],
    ["audience_network", "#5865F2"],
    ["messenger", "#00B2FF"],
    ["google_ads", "#4285F4"]
  ]);

  const publisherRows = new Map([["facebook", []], ["instagram", []]]);
  metricRows.forEach(item => {
    if (isMeta(item.source_platform)) {
      const pub = rowPlatform(item);
      if (pub === "instagram") {
        publisherRows.get("instagram")?.push(item);
      } else if (pub === "facebook") {
        publisherRows.get("facebook")?.push(item);
      }
    }
  });

  /* ========================================================================== */
  /* 5. Summary Platform Table                                                 */
  /* ========================================================================== */
  const networkRows = [];
  let totalSpendGlobal = 0;
  let totalImpressionsGlobal = 0;
  let totalReachGlobal = 0;

  const allowedNetworks = ["facebook", "instagram"];
  if (tiktokRows.length || platformEntries.some(([k]) => canonical(k) === "tiktok")) {
    allowedNetworks.push("tiktok");
  }

  allowedNetworks.forEach(key => {
    const pRows = key === "tiktok" ? tiktokRows : (publisherRows.get(key) || []);
    const direct = platformEntries.find(([k]) => canonical(k) === key)?.[1];
    let netMetrics = null;
    if (pRows.length > 0) {
      netMetrics = aggregateRows(pRows);
    } else if (direct && Object.keys(direct).length > 0) {
      netMetrics = direct;
    }
    if (netMetrics && (number(netMetrics.spend) || number(netMetrics.impressions))) {
      const sp = number(netMetrics.spend) ? netMetrics.spend : 0;
      const imp = number(netMetrics.impressions) ? netMetrics.impressions : 0;
      const rch = number(netMetrics.reach) ? netMetrics.reach : null;
      totalSpendGlobal += sp;
      totalImpressionsGlobal += imp;
      if (rch !== null) totalReachGlobal += rch;
      networkRows.push({
        key,
        label: publisherLabels.get(key) || platformLabel(key),
        color: publisherColors.get(key) || "#154095",
        spend: sp,
        impressions: imp,
        reach: rch
      });
    }
  });

  // Fallback only if no network rows could be formed
  if (!networkRows.length && platformEntries.length) {
    platformEntries.filter(([name]) => !isMeta(name)).forEach(([name, metrics]) => {
      const sp = number(metrics.spend) ? metrics.spend : 0;
      const imp = number(metrics.impressions) ? metrics.impressions : 0;
      const rch = number(metrics.reach) ? metrics.reach : null;
      totalSpendGlobal += sp;
      totalImpressionsGlobal += imp;
      if (rch !== null) totalReachGlobal += rch;
      const netKey = canonical(name);
      const col = publisherColors.get(netKey) || "#154095";
      networkRows.push({
        key: netKey,
        label: platformLabel(name),
        color: col,
        spend: sp,
        impressions: imp,
        reach: rch
      });
    });
  }

  const summaryBody = document.getElementById("summary-platform-body");
  const summaryFoot = document.getElementById("summary-platform-foot");
  const effectiveTotalSpend = number(summary.spend) ? summary.spend : totalSpendGlobal;
  const effectiveTotalImp = number(summary.impressions) ? summary.impressions : totalImpressionsGlobal;
  const effectiveTotalReach = number(summary.reach) ? summary.reach : totalReachGlobal;

  if (networkRows.length > 0) {
    networkRows.forEach(net => {
      const tr = document.createElement("tr");
      const tdName = document.createElement("td");
      const dot = document.createElement("span");
      dot.className = "dot-bullet";
      dot.style.background = net.color;
      tdName.append(dot, net.label);

      const tdSpend = document.createElement("td");
      tdSpend.textContent = format("spend", net.spend);

      const tdImp = document.createElement("td");
      tdImp.textContent = format("impressions", net.impressions);

      const tdReach = document.createElement("td");
      tdReach.textContent = net.reach !== null ? format("reach", net.reach) : "-";

      const tdShare = document.createElement("td");
      tdShare.textContent = effectiveTotalSpend > 0 ? format("share", net.spend / effectiveTotalSpend * 100) : "0%";

      tr.append(tdName, tdSpend, tdImp, tdReach, tdShare);
      summaryBody.append(tr);
    });

    const trFoot = document.createElement("tr");
    trFoot.className = "total-row";
    const tdFootName = document.createElement("td");
    tdFootName.textContent = "Total Sumado Global";
    const tdFootSpend = document.createElement("td");
    tdFootSpend.textContent = format("spend", effectiveTotalSpend);
    const tdFootImp = document.createElement("td");
    tdFootImp.textContent = format("impressions", effectiveTotalImp);
    const tdFootReach = document.createElement("td");
    tdFootReach.textContent = format("reach", effectiveTotalReach);
    const tdFootShare = document.createElement("td");
    tdFootShare.textContent = "100%";
    trFoot.append(tdFootName, tdFootSpend, tdFootImp, tdFootReach, tdFootShare);
    summaryFoot.append(trFoot);
  }
  const hasSummaryTable = show(document.getElementById("summary-platform-table"), networkRows.length > 0);

  /* ========================================================================== */
  /* 6. Charts: Evolución & Share de Impresiones y Alcance                     */
  /* ========================================================================== */
  const evolutionData = breakdowns.monthly_evolution || null;
  const chartNetworks = networkRows.map(net => ({ key: net.key, label: net.label, color: net.color }));

  let tooltipNode = document.getElementById("chart-floating-tooltip");
  if (!tooltipNode) {
    tooltipNode = document.createElement("div");
    tooltipNode.id = "chart-floating-tooltip";
    tooltipNode.style.cssText = "position:fixed;display:none;pointer-events:none;background:#262b33;color:#ffffff;border-radius:6px;padding:8px 12px;font-size:12px;line-height:1.4;box-shadow:0 6px 18px rgba(0,0,0,0.32);z-index:99999;font-family:var(--sans);";
    document.body.append(tooltipNode);
  }

  const positionChartTooltip = (e) => {
    if (!tooltipNode || tooltipNode.style.display === "none") return;
    const x = e.clientX + 12;
    const y = e.clientY - 46;
    tooltipNode.style.left = Math.max(8, Math.min(window.innerWidth - 200, x)) + "px";
    tooltipNode.style.top = Math.max(8, y) + "px";
  };

  const showChartTooltip = (e, title, value, color, unit, extra = "") => {
    tooltipNode.replaceChildren();
    const titleEl = document.createElement("div");
    titleEl.style.cssText = "font-weight:800;font-size:12px;margin-bottom:3px;color:#ffffff;";
    titleEl.textContent = title;

    const rowEl = document.createElement("div");
    rowEl.style.cssText = "display:flex;align-items:center;gap:7px;color:#ffffff;font-size:12px;font-weight:600;";

    const swatch = document.createElement("span");
    swatch.style.cssText = "display:inline-block;width:9px;height:9px;border-radius:2px;flex-shrink:0;background:" + color + ";";

    const textEl = document.createElement("span");
    textEl.textContent = fmtNumber.format(value) + " " + unit + extra;

    rowEl.append(swatch, textEl);
    tooltipNode.append(titleEl, rowEl);
    tooltipNode.style.display = "block";
    positionChartTooltip(e);
  };

  const hideChartTooltip = () => {
    if (tooltipNode) tooltipNode.style.display = "none";
  };

  const renderMetricEvolutionAndShare = (metricKey, gridId, legendId, chartId, donutId, donutLegendId, colors) => {
    const chartGrid = document.getElementById(gridId);
    if (!chartGrid) return false;

    // Extract current month values for active channels
    const netItems = chartNetworks.map(net => {
      const pRows = net.key === "tiktok" ? tiktokRows : (publisherRows.get(net.key) || []);
      const direct = platformEntries.find(([k]) => canonical(k) === net.key)?.[1];
      let val = 0;
      if (pRows.length > 0) {
        const agg = aggregateRows(pRows);
        val = number(getProp(agg, metricKey)) ? getProp(agg, metricKey) : 0;
      } else if (direct && number(getProp(direct, metricKey))) {
        val = getProp(direct, metricKey);
      }
      const evoNet = getProp(evolutionData?.networks, net.key);
      const evoMetric = getProp(evoNet, metricKey);
      const evoVal = evoMetric && number(getProp(evoMetric, "m0")) ? getProp(evoMetric, "m0") : (evoNet && number(getProp(evoNet, "m0")) ? getProp(evoNet, "m0") : val);
      return { key: net.key, label: net.label, color: net.color, currentVal: evoVal || val };
    });

    const totalCurrent = netItems.reduce((acc, item) => acc + item.currentVal, 0);
    if (totalCurrent <= 0 && !evolutionData) return false;

    show(chartGrid, true);

    // 1. Grouped Bar Chart
    const evoMonths = evolutionData?.months || [
      { key: "m0", label: formatDate(period.start) || "Mes actual" }
    ];

    let effectiveMonths = [...evoMonths];
    const hasM2Data = chartNetworks.some(net => {
      const ev = getProp(evolutionData?.networks, net.key);
      const evMetric = getProp(ev, metricKey);
      return (evMetric && number(getProp(evMetric, "m2")) && getProp(evMetric, "m2") > 0) || (ev && number(getProp(ev, "m2")) && getProp(ev, "m2") > 0);
    });
    if (metricKey === "reach" && !hasM2Data && effectiveMonths.length === 3) {
      effectiveMonths = effectiveMonths.filter(m => m.key !== "m2");
    }

    const legendContainer = document.getElementById(legendId);
    legendContainer.replaceChildren();
    effectiveMonths.forEach((m, idx) => {
      const item = document.createElement("div");
      item.style.display = "flex";
      item.style.alignItems = "center";
      item.style.gap = "6px";
      const swatch = document.createElement("span");
      swatch.style.width = "14px";
      swatch.style.height = "14px";
      swatch.style.borderRadius = "3px";
      swatch.style.background = colors.at(idx % colors.length) || "#154095";
      item.append(swatch, m.label);
      legendContainer.append(item);
    });

    const evoChart = document.getElementById(chartId);
    const width = 620, height = 250, padL = 75, padR = 20, padT = 20, padB = 36;
    const netGroups = netItems.map(net => {
      const values = effectiveMonths.map((m, idx) => {
        const netEv = getProp(evolutionData?.networks, net.key);
        const netEvMetric = getProp(netEv, metricKey);
        if (netEvMetric && number(getProp(netEvMetric, m.key))) return getProp(netEvMetric, m.key);
        if (netEv && number(getProp(netEv, m.key))) return getProp(netEv, m.key);
        if (idx === effectiveMonths.length - 1) return net.currentVal;
        return 0;
      });
      return { key: net.key, label: net.label, values };
    });

    const allVals = netGroups.flatMap(g => g.values);
    const rawMax = Math.max(...allVals, 1000);
    const magnitude = Math.pow(10, Math.floor(Math.log10(rawMax)));
    const maxVal = Math.ceil(rawMax / (magnitude / 2)) * (magnitude / 2);

    evoChart.setAttribute("viewBox", `0 0 ${width} ${height}`);
    evoChart.replaceChildren();

    // Horizontal grid lines (4 steps)
    const steps = 4;
    for (let i = 0; i <= steps; i++) {
      const val = maxVal / steps * i;
      const y = padT + (height - padT - padB) * (1 - i / steps);
      evoChart.append(
        svgElement("line", {
          x1: padL,
          x2: width - padR,
          y1: y,
          y2: y,
          stroke: "#e6edf5",
          "stroke-width": "1"
        }),
        svgElement("text", {
          x: padL - 10,
          y: y + 4,
          "text-anchor": "end",
          "font-size": "10",
          fill: "#8a96a6"
        }, fmtNumber.format(val))
      );
    }

    // Grouped Bars
    const groupWidth = (width - padL - padR) / netGroups.length;
    const barCount = effectiveMonths.length;
    const barWidth = Math.min(36, Math.max(18, (groupWidth * 0.6) / barCount));
    const barGap = 5;
    const totalBarsWidth = barCount * barWidth + (barCount - 1) * barGap;

    netGroups.forEach((g, gIdx) => {
      const gCenter = padL + gIdx * groupWidth + groupWidth / 2;
      const startX = gCenter - totalBarsWidth / 2;
      g.values.forEach((v, bIdx) => {
        const x = startX + bIdx * (barWidth + barGap);
        const barH = Math.max(2, (height - padT - padB) * (v / maxVal));
        const y = height - padB - barH;
        const barColor = colors.at(bIdx % colors.length) || "#154095";

        const rect = svgElement("rect", {
          x,
          y,
          width: barWidth,
          height: barH,
          rx: "3",
          fill: barColor
        });
        rect.style.cursor = "pointer";
        rect.style.transition = "opacity 0.15s ease";

        rect.addEventListener("pointerenter", (e) => {
          rect.style.opacity = "0.82";
          showChartTooltip(e, g.label, v, barColor, metricLabel(metricKey));
        });
        rect.addEventListener("pointermove", (e) => {
          positionChartTooltip(e);
        });
        rect.addEventListener("pointerleave", () => {
          rect.style.opacity = "1";
          hideChartTooltip();
        });

        rect.append(svgElement("title", {}, `${g.label} (${effectiveMonths.at(bIdx)?.label || ""}): ${fmtNumber.format(v)} ${metricLabel(metricKey).toLowerCase()}`));
        evoChart.append(rect);
      });

      evoChart.append(
        svgElement("text", {
          x: gCenter,
          y: height - 12,
          "text-anchor": "middle",
          "font-size": "11",
          "font-weight": "700",
          fill: "#475569"
        }, g.label)
      );
    });

    // 2. Donut Chart: Share por Red
    const donutSvg = document.getElementById(donutId);
    donutSvg.replaceChildren();
    const cx = 95, cy = 95, r = 78, innerR = 48;
    let startAngle = 0;
    netItems.forEach(net => {
      const slice = totalCurrent > 0 ? (net.currentVal / totalCurrent) : 0.5;
      const angle = slice * Math.PI * 2;
      const endAngle = startAngle + angle;

      const x1 = cx + r * Math.sin(startAngle), y1 = cy - r * Math.cos(startAngle);
      const x2 = cx + r * Math.sin(endAngle), y2 = cy - r * Math.cos(endAngle);
      const ix1 = cx + innerR * Math.sin(endAngle), iy1 = cy - innerR * Math.cos(endAngle);
      const ix2 = cx + innerR * Math.sin(startAngle), iy2 = cy - innerR * Math.cos(startAngle);
      const largeArc = angle > Math.PI ? 1 : 0;

      const d = `M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2} L ${ix1} ${iy1} A ${innerR} ${innerR} 0 ${largeArc} 0 ${ix2} ${iy2} Z`;
      const path = svgElement("path", { d, fill: net.color });
      path.style.cursor = "pointer";
      path.style.transition = "opacity 0.15s ease";

      path.addEventListener("pointerenter", (e) => {
        path.style.opacity = "0.82";
        const percentStr = " (" + (slice * 100).toFixed(1) + "%)";
        showChartTooltip(e, net.label, net.currentVal, net.color, metricLabel(metricKey), percentStr);
      });
      path.addEventListener("pointermove", (e) => {
        positionChartTooltip(e);
      });
      path.addEventListener("pointerleave", () => {
        path.style.opacity = "1";
        hideChartTooltip();
      });

      path.append(svgElement("title", {}, `${net.label}: ${fmtNumber.format(net.currentVal)} (${(slice * 100).toFixed(1)}%)`));
      donutSvg.append(path);
      startAngle = endAngle;
    });

    const shareLegend = document.getElementById(donutLegendId);
    shareLegend.replaceChildren();
    netItems.forEach(net => {
      const item = document.createElement("div");
      item.style.display = "flex";
      item.style.alignItems = "center";
      item.style.gap = "6px";
      const dot = document.createElement("span");
      dot.className = "dot-bullet";
      dot.style.background = net.color;
      item.append(dot, net.label);
      shareLegend.append(item);
    });
    return true;
  };

  // Render Impresiones (Mayo, Junio, Julio palette)
  renderMetricEvolutionAndShare(
    "impressions",
    "summary-charts-grid",
    "summary-evolution-legend",
    "summary-evolution-chart",
    "summary-share-chart",
    "summary-share-legend",
    ["#ECECEC", "#A5C0DB", "#154095"]
  );

  // Render Alcance (Junio, Julio palette)
  renderMetricEvolutionAndShare(
    "reach",
    "summary-reach-grid",
    "summary-reach-evolution-legend",
    "summary-reach-evolution-chart",
    "summary-reach-share-chart",
    "summary-reach-share-legend",
    ["#154095", "#38BDF8", "#ECECEC"]
  );

  /* ========================================================================== */
  /* 7. Trend Chart (SVG)                                                       */
  /* ========================================================================== */
  const renderTrend = (prefix, items) => {
    const candidates = ordered(Object.assign({}, ...items.map(item => item.metrics || {})));
    const metric = ["impressions", "reach", "views", "video_views", "spend", "engagement", "clicks"].find(key => candidates.includes(key)) || candidates[0];
    if (!metric) return false;

    const daily = new Map();
    items.forEach(item => {
      const value = (item.metrics || {})[metric];
      if (number(value)) daily.set(item.date, (daily.get(item.date) || 0) + value);
    });

    const points = [...daily.entries()].sort(([a], [b]) => a.localeCompare(b));
    if (!points.length) return false;

    const svg = document.getElementById(prefix + "-chart");
    if (!svg) return false;

    const width = 900, height = 245, left = 50, right = 20, top = 22, bottom = 52;
    const max = Math.max(...points.map(([, value]) => value), 1);
    const x = index => left + (points.length === 1 ? (width - left - right) / 2 : index * (width - left - right) / (points.length - 1));
    const y = value => top + (height - top - bottom) * (1 - value / max);

    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    svg.replaceChildren();

    const axis = svgElement("line", {
      class: "chart-axis",
      x1: left,
      x2: width - right,
      y1: height - bottom,
      y2: height - bottom
    });
    svg.append(axis);

    const coords = points.map(([, value], index) => `${x(index)},${y(value)}`);
    const area = svgElement("polygon", {
      class: "chart-area",
      points: `${left},${height - bottom} ${coords.join(" ")} ${width - right},${height - bottom}`
    });
    svg.append(area);

    const line = svgElement("polyline", {
      class: "chart-line",
      points: coords.join(" ")
    });
    svg.append(line);

    const every = Math.max(1, Math.ceil(points.length / 7));
    points.forEach(([day, value], index) => {
      const dot = svgElement("circle", {
        class: "chart-dot",
        cx: x(index),
        cy: y(value),
        r: 4
      });
      dot.append(svgElement("title", {}, `${formatDate(day)}: ${format(metric, value)}`));
      svg.append(dot);

      if (index % every === 0 || index === points.length - 1) {
        const label = svgElement("text", {
          class: "chart-label",
          "data-trend-tick": "true",
          x: x(index),
          y: height - 17,
          "text-anchor": "end",
          transform: `rotate(-28 ${x(index)} ${height - 17})`
        }, formatDate(day));
        svg.append(label);
      }
    });

    const labelEl = document.getElementById(prefix + "-trend-label");
    if (labelEl) labelEl.textContent = metricLabel(metric);

    const body = document.getElementById(prefix + "-trend-body");
    if (body) {
      body.replaceChildren();
      points.forEach(([day, value]) => {
        const row = element("tr");
        row.append(element("td", "", formatDate(day)), element("td", "", format(metric, value)));
        body.append(row);
      });
    }
    return true;
  };

  /* ========================================================================== */
  /* 8. Summary Panel Narratives & KPIs                                         */
  /* ========================================================================== */
  const generalNarratives = narratives.filter(item => typeof item === "string" || (item && !item.platform));
  generalNarratives.map(item => typeof item === "string" ? item : item.text || item.summary || item.value).filter(Boolean).forEach(value => {
    const node = element("p", "narrative", value);
    node.dataset.family = "narrative";
    document.getElementById("summary-narratives").append(node);
  });
  const summaryKpis = renderKpis("summary-kpis", summary, true, summaryAllowedKeys);
  setPanel("summary-panel", summaryKpis > 0 || hasSummaryTable || generalNarratives.length > 0);

  /* ========================================================================== */
  /* 9. Competition / Benchmarking                                              */
  /* ========================================================================== */
  const compData = breakdowns.benchmarking || (typeof breakdowns.competition === "object" && !Array.isArray(breakdowns.competition) ? breakdowns.competition : null);
  const genericCompList = Array.isArray(breakdowns.competition) ? breakdowns.competition.filter(item => item && typeof item === "object") : [];
  let hasCompetition = false;

  if (compData && (Array.isArray(compData.instagram) || Array.isArray(compData.facebook))) {
    const igList = Array.isArray(compData.instagram) ? compData.instagram : [];
    const fbList = Array.isArray(compData.facebook) ? compData.facebook : [];

    if (igList.length > 0) {
      const igBody = document.getElementById("competition-ig-body");
      igList.forEach(item => {
        const row = element("tr");
        row.append(
          element("td", "td-name", (item.name || item.username) + (item.username ? " (@" + item.username + ")" : "")),
          element("td", "td-num", format("followers", item.followers)),
          element("td", "td-num", format("posts", item.posts_count || item.media_count)),
          element("td", "td-num", format("reels", item.reels_count)),
          element("td", "td-num", format("likes", item.avg_likes || item.total_likes)),
          element("td", "td-num", format("comments", item.avg_comments || item.total_comments)),
          element("td", "td-num", (item.engagement_rate || 0) + "%")
        );
        igBody.append(row);
      });
      show(document.getElementById("competition-ig-card"), true);
      hasCompetition = true;
    }

    if (fbList.length > 0) {
      const fbBody = document.getElementById("competition-fb-body");
      fbList.forEach(item => {
        const row = element("tr");
        row.append(
          element("td", "td-name", item.name || item.page_id_or_username),
          element("td", "td-num", format("followers", item.followers)),
          element("td", "td-num", format("fan_count", item.fan_count)),
          element("td", "td-num", format("talking_about_count", item.talking_about_count)),
          element("td", "td-num", format("active_ads", item.active_ads_count))
        );
        fbBody.append(row);
      });
      show(document.getElementById("competition-fb-card"), true);
      hasCompetition = true;
    }
  }

  if (!hasCompetition && genericCompList.length > 0) {
    const competitionMetrics = Object.keys(genericCompList[0]).filter(key => key !== "label" && key !== "name" && genericCompList.every(item => number(getProp(item, key))));
    if (competitionMetrics.length) {
      const head = document.getElementById("competition-head");
      head.append(element("th", "", "Cuenta"));
      competitionMetrics.forEach(key => head.append(element("th", "", metricLabel(key))));
      genericCompList.forEach(item => {
        const row = element("tr");
        row.append(element("td", "", item.label || item.name || "Cuenta"));
        competitionMetrics.forEach(key => row.append(element("td", "", format(key, getProp(item, key)))));
        document.getElementById("competition-body").append(row);
      });
      show(document.getElementById("competition-generic-card"), true);
      hasCompetition = true;
    }
  }

  setPanel("competition-panel", hasCompetition);

  /* ========================================================================== */
  /* 10. Post Rankings                                                         */
  /* ========================================================================== */
  const renderPostRankings = (network, items) => {
    const isPublicPostUrl = value => typeof value === "string" && new RegExp("^https?:/" + "/(?:www\\.|m\\.)?(?:facebook\\.com/(?:[^/?#]+\/(?:posts|videos)/|permalink\\.php|photo(?:\\.php|/)|reel/)|instagram\\.com/(?:p|reel|tv)/)", "i").test(value);
    const isFacebookPreviewUrl = value => typeof value === "string" && (value.includes("facebook.com/plugins/post.php") || value.includes("business.facebook.com/ads/api/preview_iframe.php"));
    const previewItems = (items || []).filter(item => {
      const srcMetrics = (item.source_metrics && typeof item.source_metrics === "object") ? item.source_metrics : {};
      return [item.url, item.permalink_url, item.link, srcMetrics.url, srcMetrics.permalink_url, srcMetrics.link]
        .some(isPublicPostUrl);
    });
    const targetItems = network === "facebook" ? (previewItems.length ? previewItems : (items || [])) : previewItems;
    if (!targetItems.length) return false;

    const normalized = targetItems.map(item => {
      const vals = rowMetrics(item);
      const srcMetrics = (item.source_metrics && typeof item.source_metrics === "object") ? item.source_metrics : {};
      const contentPlatform = rowPlatform(item);
      let directPostUrl = [item.url, item.permalink_url, item.link, srcMetrics.permalink_url, srcMetrics.permalink, srcMetrics.url, srcMetrics.link].find(isPublicPostUrl) || "";
      let iframeEmbedUrl = "";

      if (item.body || srcMetrics.body) {
        const bodyText = String(item.body || srcMetrics.body || "");
        const hrefMatch = bodyText.match(new RegExp("h" + "ref=([^&\"']+)", "i"));
        if (hrefMatch && hrefMatch[1]) {
          try {
            const dec = decodeURIComponent(hrefMatch[1]);
            if (isPublicPostUrl(dec)) directPostUrl = dec;
          } catch (e) { }
        }
        const srcMatch = bodyText.match(new RegExp("s" + "rc=[\"']([^\"']+)[\"']", "i"));
        if (srcMatch && srcMatch[1]) {
          iframeEmbedUrl = srcMatch[1].replace(/&amp;/g, "&");
        }
      }

      if (directPostUrl.includes("/plugins/post.php") && directPostUrl.includes("h" + "ref=")) {
        const hm = directPostUrl.match(new RegExp("h" + "ref=([^&]+)", "i"));
        if (hm && hm[1]) {
          try {
            directPostUrl = decodeURIComponent(hm[1]);
          } catch (e) { }
        }
      }

      if (contentPlatform === "facebook" && !isFacebookPreviewUrl(iframeEmbedUrl)) iframeEmbedUrl = "";
      if (contentPlatform !== "facebook" && !iframeEmbedUrl.includes("instagram.com")) iframeEmbedUrl = "";
      if (!iframeEmbedUrl && contentPlatform === "facebook" && directPostUrl.startsWith("http") && directPostUrl.includes("facebook.com")) {
        const fbPlugin = ["https:", "//", "www.facebook.com", "/plugins/post.php?h", "ref="].join("");
        iframeEmbedUrl = fbPlugin + encodeURIComponent(directPostUrl) + "&show_text=false&width=auto";
      }
      if (!iframeEmbedUrl && contentPlatform === "instagram" && directPostUrl.startsWith("http") && directPostUrl.includes("instagram.com")) {
        iframeEmbedUrl = directPostUrl.replace(/\/?$/, "/embed/");
      }

      const rawImg = item.image_url || item.thumbnail_url || item.media_url || item.picture || item.creative_thumbnail_url || srcMetrics.image_url || srcMetrics.thumbnail_url || srcMetrics.media_url || srcMetrics.picture || srcMetrics.thumbnail || "";
      const postCopy = (item.post_message || item.post_title || item.caption || item.post_caption || item.message || "").trim();
      const postTitle = postCopy || item.post_name || item.content_name || "Publicación";
      const reachVal = (vals.reach !== undefined && vals.reach !== null) ? vals.reach : ((srcMetrics.reach !== undefined && srcMetrics.reach !== null) ? srcMetrics.reach : (item.reach || vals.impressions || srcMetrics.impressions || item.impressions || 0));
      const impVal = (vals.impressions !== undefined && vals.impressions !== null) ? vals.impressions : ((srcMetrics.impressions !== undefined && srcMetrics.impressions !== null) ? srcMetrics.impressions : (item.impressions || 0));
      const engVal = (vals.engagement !== undefined && vals.engagement !== null) ? vals.engagement : ((srcMetrics.engagement !== undefined && srcMetrics.engagement !== null) ? srcMetrics.engagement : (item.engagement || vals.post_engagement || srcMetrics.post_engagement || item.post_engagement || vals.comments || srcMetrics.comments || item.comments || 0));
      const clickVal = (vals.clicks !== undefined && vals.clicks !== null) ? vals.clicks : ((srcMetrics.clicks !== undefined && srcMetrics.clicks !== null) ? srcMetrics.clicks : (item.clicks || 0));
      const viewVal = (vals.views !== undefined && vals.views !== null) ? vals.views : ((srcMetrics.views !== undefined && srcMetrics.views !== null) ? srcMetrics.views : (item.views || impVal || 0));
      const leadVal = number(srcMetrics.lead) ? srcMetrics.lead : (number(item.lead) ? item.lead : 0);
      return {
        name: postTitle,
        platform: contentPlatform,
        url: directPostUrl,
        iframe_url: iframeEmbedUrl,
        image_url: rawImg,
        reach: reachVal,
        impressions: impVal,
        engagement: engVal,
        clicks: clickVal,
        views: viewVal,
        lead: leadVal,
      };
    });

    const createCard = (rankLabel, rankClass, item, isLowest, primaryMetric = "") => {
      const card = element("div", "post-card");
      if (isLowest) {
        card.style.margin = "0";
        card.style.width = "100%";
        card.style.maxWidth = "360px";
        const rankBadge = element("div", "post-rank", rankLabel);
        rankBadge.style.background = "#64748B";
        rankBadge.style.color = "#fff";
        rankBadge.style.width = "auto";
        rankBadge.style.height = "auto";
        rankBadge.style.padding = "4px 12px";
        rankBadge.style.borderRadius = "20px";
        rankBadge.style.fontSize = "11px";
        rankBadge.style.fontWeight = "700";
        rankBadge.style.top = "-12px";
        rankBadge.style.right = "12px";
        card.append(rankBadge);
      } else {
        card.append(element("div", "post-rank " + rankClass, rankLabel));
      }

      const embedWrapper = element("div", "embed-wrapper");
      let hasEmbed = false;
      const supportedEmbed = typeof item.iframe_url === "string" && (item.platform === "facebook"
        ? isFacebookPreviewUrl(item.iframe_url)
        : item.platform === "instagram" && item.iframe_url.includes("instagram.com"));
      if (supportedEmbed) {
        const iframe = element("iframe");
        iframe.setAttribute("loading", "lazy");
        iframe.setAttribute("title", item.name && item.name !== "Publicación" ? item.name : "Publicación " + (item.platform === "facebook" ? "Facebook" : "Instagram"));
        iframe.style.width = "100%";
        iframe.style.height = "100%";
        iframe.style.border = "none";
        iframe.style.position = "absolute";
        iframe.style.top = "0";
        iframe.style.left = "0";
        iframe.style.zIndex = "2";
        iframe.setAttribute("s" + "rc", item.iframe_url);
        embedWrapper.append(iframe);
        hasEmbed = true;
      }

      if (!hasEmbed) {
        const mockCard = element("div", "fb-mock-card");
        mockCard.style.width = "100%";
        mockCard.style.height = "100%";
        mockCard.style.display = "flex";
        mockCard.style.flexDirection = "column";
        mockCard.style.justifyContent = "space-between";
        mockCard.style.background = "#ffffff";
        mockCard.style.padding = "10px 12px";
        mockCard.style.boxSizing = "border-box";
        mockCard.style.overflow = "hidden";

        const mockHeader = element("div");
        mockHeader.style.display = "flex";
        mockHeader.style.alignItems = "center";
        mockHeader.style.gap = "8px";
        mockHeader.style.marginBottom = "4px";

        const displayAuthor = (item.page_name || (company && !company.startsWith("act_") ? company : "Facebook")).trim();
        const avatar = element("div");
        avatar.style.width = "28px";
        avatar.style.height = "28px";
        avatar.style.borderRadius = "50%";
        avatar.style.background = "linear-gradient(135deg, #1877F2, #0d5bbd)";
        avatar.style.display = "flex";
        avatar.style.alignItems = "center";
        avatar.style.justifyContent = "center";
        avatar.style.color = "#ffffff";
        avatar.style.fontWeight = "800";
        avatar.style.fontSize = "13px";
        avatar.textContent = (displayAuthor.charAt(0) || "F").toUpperCase();

        const authorInfo = element("div");
        const authorName = element("div", "", displayAuthor);
        authorName.style.fontWeight = "700";
        authorName.style.fontSize = "12px";
        authorName.style.color = "var(--dark)";
        const authorSub = element("div", "", "Publicidad · 🌐");
        authorSub.style.fontSize = "10px";
        authorSub.style.color = "var(--muted)";
        authorInfo.append(authorName, authorSub);
        mockHeader.append(avatar, authorInfo);

        const copyEl = element("div", "", item.post_message || item.name || "");
        copyEl.style.fontSize = "11px";
        copyEl.style.color = "#1e293b";
        copyEl.style.lineHeight = "1.3";
        copyEl.style.marginBottom = "6px";
        copyEl.style.display = "-webkit-box";
        copyEl.style.webkitLineClamp = "2";
        copyEl.style.webkitBoxOrient = "vertical";
        copyEl.style.overflow = "hidden";

        const mediaContainer = element("div");
        mediaContainer.style.flex = "1";
        mediaContainer.style.position = "relative";
        mediaContainer.style.borderRadius = "6px";
        mediaContainer.style.overflow = "hidden";
        mediaContainer.style.background = "#f1f5f9";
        mediaContainer.style.display = "flex";
        mediaContainer.style.alignItems = "center";
        mediaContainer.style.justifyContent = "center";
        mediaContainer.style.minHeight = "110px";

        if (item.image_url && typeof item.image_url === "string" && item.image_url.startsWith("http")) {
          const img = element("img");
          img.setAttribute("s" + "rc", item.image_url);
          img.setAttribute("alt", item.name || "Preview");
          img.style.width = "100%";
          img.style.height = "100%";
          img.style.objectFit = "cover";
          mediaContainer.append(img);
        } else {
          const fbSvg = svgElement("svg", {
            width: "36",
            height: "36",
            viewBox: "0 0 24 24",
            fill: "#1877F2"
          });
          const path = svgElement("path", {
            d: "M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"
          });
          fbSvg.append(path);
          mediaContainer.append(fbSvg);
        }

        const mockFooter = element("div");
        mockFooter.style.display = "flex";
        mockFooter.style.justifyContent = "space-between";
        mockFooter.style.alignItems = "center";
        mockFooter.style.paddingTop = "4px";
        mockFooter.style.marginTop = "4px";
        mockFooter.style.borderTop = "1px solid #eef2f6";
        mockFooter.style.fontSize = "11px";
        mockFooter.style.color = "var(--muted)";
        mockFooter.style.fontWeight = "600";

        const reactLeft = element("span", "", "👍 ❤️ " + format("engagement", item.engagement));
        const postLink = (item.url && typeof item.url === "string" && item.url.startsWith("http")) ? item.url : ["https:", "//", "www.facebook.com"].join("");
        const ctaEl = element("a", "", "Ver en Facebook ↗");
        ctaEl.setAttribute("h" + "ref", postLink);
        ctaEl.setAttribute("target", "_blank");
        ctaEl.setAttribute("rel", "noopener noreferrer");
        ctaEl.style.textDecoration = "none";
        ctaEl.style.color = "#1877F2";
        ctaEl.style.fontWeight = "700";
        ctaEl.style.cursor = "pointer";

        mockFooter.append(reactLeft, ctaEl);
        mockCard.append(mockHeader, copyEl, mediaContainer, mockFooter);
        embedWrapper.append(mockCard);
      }
      card.append(embedWrapper);

      card.append(element("div", "post-caption", item.name));

      const addKpi = (label, val) => {
        const row = element("div", "kpi-row");
        row.append(element("span", "", label), element("strong", "", val));
        card.append(row);
      };

      if (primaryMetric === "lead") addKpi("Clientes potenciales", format("lead", item.lead));
      addKpi("Visualizaciones", format("views", item.views));
      if (!isLowest || rankLabel === "Menor Alcance") {
        addKpi("Alcance", format("reach", item.reach));
      }
      addKpi("Interacciones", format("engagement", item.engagement));
      if (!isLowest && item.clicks > 0) {
        addKpi("Clics en el enlace", format("clicks", item.clicks));
      }
      const postDirectLink = (item.url && typeof item.url === "string" && item.url.startsWith("http")) ? item.url : ["https:", "//", "www.facebook.com"].join("");
      const linkRow = element("div", "kpi-row");
      const linkA = element("a", "", "Ver Post");
      linkA.setAttribute("h" + "ref", postDirectLink);
      linkA.setAttribute("target", "_blank");
      linkA.setAttribute("rel", "noopener noreferrer");
      const strong = element("strong");
      strong.append(linkA);
      linkRow.append(element("span", "", "Enlace"), strong);
      card.append(linkRow);
      return card;
    };

    const byLead = [...normalized].sort((a, b) => b.lead - a.lead).slice(0, 3);
    const leadCard = document.getElementById(network + "-top-lead-card");
    const leadGrid = document.getElementById(network + "-top-lead-grid");
    show(leadCard, Boolean(leadGrid && byLead.length));
    if (leadGrid && byLead.length) {
      leadGrid.textContent = "";
      byLead.forEach((item, idx) => {
        leadGrid.append(createCard("#" + (idx + 1), "rank-" + (idx + 1), item, false, "lead"));
      });
    }

    const byReach = [...normalized].sort((a, b) => (b.reach || b.impressions) - (a.reach || a.impressions)).slice(0, 3);
    const reachGrid = document.getElementById(network + "-top-reach-grid");
    if (reachGrid && byReach.length) {
      reachGrid.textContent = "";
      byReach.forEach((item, idx) => {
        reachGrid.append(createCard("#" + (idx + 1), "rank-" + (idx + 1), item, false));
      });
    }

    const byEngagement = [...normalized].sort((a, b) => (b.engagement) - (a.engagement)).slice(0, 3);
    const engGrid = document.getElementById(network + "-top-engagement-grid");
    if (engGrid && byEngagement.length) {
      engGrid.textContent = "";
      byEngagement.forEach((item, idx) => {
        engGrid.append(createCard("#" + (idx + 1), "rank-" + (idx + 1), item, false));
      });
    }

    const lowestReach = [...normalized].sort((a, b) => (a.reach || a.impressions) - (b.reach || b.impressions))[0];
    const lowestEngagement = [...normalized].sort((a, b) => (a.engagement) - (b.engagement))[0];
    const lowestGrid = document.getElementById(network + "-lowest-grid");
    if (lowestGrid && (lowestReach || lowestEngagement)) {
      lowestGrid.textContent = "";
      if (lowestReach) {
        lowestGrid.append(createCard("Menor Alcance", "", lowestReach, true));
      }
      if (lowestEngagement && lowestEngagement !== lowestReach) {
        lowestGrid.append(createCard("Menor Interacción", "", lowestEngagement, true));
      } else if (lowestEngagement && normalized.length > 1) {
        const secondLowest = [...normalized].sort((a, b) => (a.engagement) - (b.engagement))[1] || lowestEngagement;
        lowestGrid.append(createCard("Menor Interacción", "", secondLowest, true));
      } else if (lowestEngagement) {
        lowestGrid.append(createCard("Menor Interacción", "", lowestEngagement, true));
      }
    }

    show(document.getElementById(network + "-posts-content"), true);
    return true;
  };

  /* ========================================================================== */
  /* 11. Content & Demographics                                                 */
  /* ========================================================================== */
  const renderContent = (name, items) => {
    const excludedMetrics = new Set(["video_views", "views", "video_play_actions", "plays"]);
    const normalized = items.map(item => ({ item, values: rowMetrics(item) }));
    const metrics = normalized.length
      ? ordered(normalized[0].values).filter(key => !excludedMetrics.has(key) && normalized.every(entry => number(getProp(entry.values, key))) && normalized.some(entry => Number(getProp(entry.values, key)) > 0)).slice(0, 6)
      : [];
    if (!normalized.length || !metrics.length) return false;

    const head = document.getElementById(name + "-content-head");
    head.append(element("th", "", "Campaña o contenido"));
    metrics.forEach(key => head.append(element("th", "", metricLabel(key))));

    normalized
      .sort((a, b) => (getProp(b.values, metrics[0]) || 0) - (getProp(a.values, metrics[0]) || 0))
      .slice(0, 12)
      .forEach(({ item, values }) => {
        const row = element("tr");
        row.append(element("td", "", item.campaign_name || item.ad_name || item.content_name || item.name || "Contenido"));
        metrics.forEach(key => row.append(element("td", "", format(key, getProp(values, key)))));
        document.getElementById(name + "-content-body").append(row);
      });
    return true;
  };

  const normalizeBreakdown = (key, value) => {
    if (Array.isArray(value)) {
      return value.map(item => (item && typeof item === "object" ? {
        label: item.label ?? item.name ?? getProp(item, key) ?? item.dimension,
        value: item.value ?? item.count ?? item.impressions ?? item.reach ?? item.percentage ?? item.share
      } : null)).filter(item => item && item.label !== undefined && number(item.value));
    }
    if (value && typeof value === "object") {
      return Object.entries(value).filter(([, amount]) => number(amount)).map(([label, amount]) => ({ label, value: amount }));
    }
    return [];
  };

  const platformBreakdowns = name => {
    const direct = getProp(breakdowns, name);
    if (direct && typeof direct === "object" && !Array.isArray(direct)) return direct;
    return Object.fromEntries(
      Object.entries(breakdowns)
        .filter(([key]) => canonical(key) === name)
        .map(([key, value]) => [key.replace(name, "").replace(/^_|_$/g, "") || "audience", value])
    );
  };

  const renderDemographics = name => {
    const target = document.getElementById(name + "-breakdowns");
    Object.entries(platformBreakdowns(name)).forEach(([group, value]) => {
      const items = normalizeBreakdown(group, value);
      if (!items.length) return;
      const card = element("div", "card");
      const list = element("div", "breakdown-list");
      const max = Math.max(...items.map(item => item.value), 1);
      card.append(element("h4", "card-title", metricLabel(group)));
      items.sort((a, b) => b.value - a.value).slice(0, 10).forEach(item => {
        const row = element("div", "breakdown-row");
        const metaRow = element("div", "breakdown-meta");
        const bar = element("div", "breakdown-bar");
        const fill = element("div", "breakdown-fill");
        metaRow.append(
          element("span", "breakdown-name", item.label),
          element("span", "breakdown-value", format(group.includes("share") || group.includes("percent") ? "share" : "value", item.value))
        );
        fill.style.width = Math.max(2, item.value / max * 100) + "%";
        bar.append(fill);
        row.append(metaRow, bar);
        list.append(row);
      });
      card.append(list);
      target.append(card);
    });
    return target.children.length > 0;
  };

  /* ========================================================================== */
  /* 12. Platform Loop, Investment & Optimization                               */
  /* ========================================================================== */
  for (const name of ["facebook", "instagram", "tiktok"]) {
    const direct = platformEntries.find(([key]) => canonical(key) === name)?.[1];
    const publisherItems = publisherRows.get(name) || [];
    const usesSharedMeta = sharedMeta && (name === "facebook" || name === "instagram");
    const metrics = direct || (publisherItems.length ? aggregateRows(publisherItems) : usesSharedMeta ? metaEntry[1] : {});
    const trendItems = direct
      ? series.filter(item => canonical(item.platform) === name)
      : publisherItems.length
        ? publisherItems.map(item => ({ date: item.date, metrics: rowMetrics(item) }))
        : usesSharedMeta ? metaSeries : [];
    const contentItems = usesSharedMeta ? [] : rankingContentRows.filter(item => rowPlatform(item) === name);
    const kpis = renderKpis(name + "-kpis", metrics, true, null, platformCustomLabels.get(name), name);
    const hasTrend = renderTrend(name, trendItems);
    const hasTableContent = renderContent(name, contentItems);
    const hasRankings = (name === "facebook" || name === "instagram") ? renderPostRankings(name, rankingItemsFor(name)) : false;
    const hasContent = hasRankings || hasTableContent;
    const hasDemographics = renderDemographics(name);
    const platformNarratives = narratives
      .filter(item => item && typeof item === "object" && canonical(item.platform) === name)
      .map(item => item.text || item.summary || item.value)
      .filter(Boolean);

    if (name === "facebook" || name === "instagram") {
      const notice = document.getElementById(name + "-shared-meta");
      notice.textContent = usesSharedMeta ? "Datos agregados de Meta compartidos entre Facebook e Instagram; no se atribuye una distribución por red." : "";
      show(notice, usesSharedMeta);
    }

    show(document.getElementById(name + "-trend"), hasTrend && name !== "facebook");
    show(document.getElementById(name + "-content"), hasTableContent && !hasRankings);
    show(document.getElementById(name + "-demographics"), hasDemographics);

    platformNarratives.forEach(value => {
      const node = element("p", "narrative", value);
      node.dataset.family = "narrative";
      document.getElementById(name + "-narratives").append(node);
    });

    setPanel(name + "-panel", kpis > 0 || hasTrend || hasContent || hasDemographics || platformNarratives.length > 0);
  }

  const investmentRows = platformEntries.filter(([, metrics]) => number(metrics.spend));
  investmentRows.forEach(([name, metrics]) => {
    const row = element("tr");
    row.append(
      element("td", "", platformLabel(name)),
      element("td", "", format("spend", metrics.spend)),
      element("td", "", platformSpend > 0 ? format("share", metrics.spend / platformSpend * 100) : "")
    );
    document.getElementById("investment-body").append(row);
  });
  show(document.getElementById("investment-table"), investmentRows.length > 0);

  const optimization = [
    ...Object.entries(rates).filter(([, value]) => number(value)),
    ...Object.entries(deltas).filter(([, value]) => number(value)).map(([key, value]) => ["delta_" + key, value])
  ];
  optimization.slice(0, 12).forEach(([key, value]) => {
    const row = element("div", "breakdown-meta");
    const isDelta = key.startsWith("delta_");
    row.append(
      element("span", "breakdown-name", isDelta ? "Variación de " + metricLabel(key.slice(6)) : metricLabel(key)),
      element("span", "breakdown-value " + (isDelta ? (value > 0 ? "up" : value < 0 ? "down" : "neutral") : ""), format(key, value))
    );
    document.getElementById("optimization-list").append(row);
  });
  show(document.getElementById("optimization-card"), optimization.length > 0);
  setPanel("investment-panel", investmentRows.length > 0 || optimization.length > 0);

  /* ========================================================================== */
  /* 13. Tabs & Navigation                                                      */
  /* ========================================================================== */
  const showTab = (targetId, btn) => {
    const target = document.getElementById(targetId);
    if (!target || target.hidden) return;
    const parentNav = btn?.closest(".secondary-nav");
    if (parentNav) parentNav.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    if (btn) btn.classList.add("active");
    document.querySelectorAll(".report-panel").forEach(panel => panel.classList.remove("active"));
    target.classList.add("active");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const switchMainTab = (tabId, btn) => {
    document.querySelectorAll(".main-tab-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    document.querySelectorAll(".secondary-nav").forEach(nav => nav.style.display = "none");
    const subNav = document.getElementById("subnav-" + tabId);
    if (subNav) {
      subNav.style.display = "flex";
      const firstBtn = [...subNav.querySelectorAll(".tab-btn")].find(b => !b.hidden);
      if (firstBtn) firstBtn.click();
    }
  };

  document.querySelectorAll(".main-tab-btn").forEach(btn => {
    btn.addEventListener("click", () => switchMainTab(btn.dataset.mainTab, btn));
  });
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => showTab(btn.dataset.target, btn));
  });

  const firstActiveTab = document.querySelector(".secondary-nav .tab-btn:not([hidden])");
  if (firstActiveTab) firstActiveTab.click();
})();
