(() => {
      "use strict";
      const data = window.REPORT_DATA || {}, meta = data.meta || {}, summary = data.summary || {}, rates = data.rates || {}, deltas = data.deltas || {}, byPlatform = data.by_platform || {}, series = Array.isArray(data.daily_series) ? data.daily_series : [], rows = data.rows || {}, breakdowns = data.breakdowns || {}, narratives = Array.isArray(data.narratives) ? data.narratives : [];
      const labels = { spend: "Inversión", impressions: "Impresiones", reach: "Alcance", clicks: "Clics", conversions: "Conversiones", results: "Resultados", lead: "Clientes potenciales", engagement: "Interacciones", post_engagement: "Interacciones con publicaciones", followers: "Seguidores", views: "Visualizaciones", video_views: "Vistas de video", likes: "Me gusta", comments: "Comentarios", shares: "Veces compartido", ctr: "CTR", cpc: "CPC", cpm: "CPM", cpa: "CPA", conversion_rate: "Tasa de conversión" }, money = new Set(["spend", "cpc", "cpm", "cpa", "cost", "cost_per_result"]), percent = new Set(["ctr", "conversion_rate", "share"]), priority = ["spend", "impressions", "reach", "engagement", "followers", "views", "video_views", "clicks", "conversions", "likes", "comments", "shares"];
      const number = value => typeof value === "number" && Number.isFinite(value), element = (tag, className, value) => { const node = document.createElement(tag); if (className) node.className = className; if (value !== undefined && value !== null) node.textContent = String(value); return node }, show = (node, visible) => { if (node) node.hidden = !visible; return visible }, metricLabel = key => labels[key] || key.replaceAll("_", " ").replace(/\b\w/g, letter => letter.toUpperCase()), platformLabel = key => key.replaceAll("_", " ").replace(/\b\w/g, letter => letter.toUpperCase());
      const format = (key, value) => { if (!number(value)) return ""; if (money.has(key)) return new Intl.NumberFormat("es-EC", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(value); if (percent.has(key) || key.startsWith("delta_")) return new Intl.NumberFormat("es-EC", { maximumFractionDigits: 2 }).format(value) + "%"; return new Intl.NumberFormat("es-EC", { notation: Math.abs(value) >= 10000000 ? "compact" : "standard", maximumFractionDigits: 0 }).format(value) }, formatDate = value => { if (!value) return ""; const parsed = new Date(value); return Number.isNaN(parsed.getTime()) ? String(value) : new Intl.DateTimeFormat("es-EC", { day: "2-digit", month: "short", year: "numeric", timeZone: "UTC" }).format(parsed) }, ordered = values => { const keys = Object.entries(values || {}).filter(([, value]) => number(value)).map(([key]) => key); return [...new Set([...priority.filter(key => keys.includes(key)), ...keys.sort()])] }, canonical = value => { const source = String(value || "").toLowerCase(); if (source.includes("instagram")) return "instagram"; if (source.includes("facebook")) return "facebook"; if (source.includes("tiktok")) return "tiktok"; return source }, isMeta = value => { const source = String(value || "").toLowerCase(); return source === "meta" || source.startsWith("meta_") || source.startsWith("meta ") }, rowPlatform = row => { const source = row.source_platform || row.platform || (row.source_metrics || {}).platform, publisher = row.publisher_platform || (row.source_metrics || {}).publisher_platform; return canonical(isMeta(source) ? publisher || row.platform || source : row.platform || source) };
      const setPanel = (id, visible) => { const node = document.getElementById(id); if (node) { show(node, visible); if (!visible) node.classList.remove('active') } const navBtn = document.querySelector('.tab-btn[data-target="' + id + '"]'); if (navBtn) show(navBtn, visible);['general', 'redes', 'optimizacion'].forEach(mainId => { const subNav = document.getElementById('subnav-' + mainId), mainBtn = document.querySelector('.main-tab-btn[data-main-tab="' + mainId + '"]'); if (subNav && mainBtn) { const hasVisible = [...subNav.querySelectorAll('.tab-btn')].some(b => !b.hidden); show(mainBtn, hasVisible) } }) };
      const summaryAllowedKeys = ["spend", "impressions", "reach", "engagement", "post_engagement", "followers", "video_views", "views"];
      const summaryCustomLabels = {
        spend: "INVERSIÓN EJECUTADA",
        impressions: "IMPRESIONES",
        reach: "ALCANCE",
        engagement: "INTERACCIONES",
        post_engagement: "INTERACCIONES",
        followers: "SEGUIDORES",
        views: "VIS. DE VIDEO",
        video_views: "VIS. DE VIDEO"
      };

      const renderKpis = (id, values, withDeltas = false, allowedKeys = null) => {
        const container = document.getElementById(id);
        container.replaceChildren();
        let keys = ordered(values);
        if (id === "summary-kpis") {
          keys = ["spend", "impressions", "reach", "engagement", "followers", "video_views"];
        } else if (allowedKeys) {
          const present = new Set(keys);
          keys = allowedKeys.filter(k => present.has(k) || number(values[k]));
          if (keys.includes("video_views") && keys.includes("views")) {
            keys = keys.filter(k => k !== "views");
          }
          if (keys.includes("engagement") && keys.includes("post_engagement")) {
            keys = keys.filter(k => k !== "post_engagement");
          }
        }
        keys.forEach(key => {
          let val = values[key];
          if (!number(val)) {
            if (key === "video_views" && number(values["views"])) val = values["views"];
            else if (key === "engagement" && number(values["post_engagement"])) val = values["post_engagement"];
            else if (key === "followers" && number(values["follower_count"])) val = values["follower_count"];
            else if (key === "followers" && number(values["follows"])) val = values["follows"];
            else if (id === "summary-kpis") val = 0;
          }
          if (!number(val) && id !== "summary-kpis") return;
          const card = element("article", "card stat-card");
          card.dataset.family = "kpi";
          card.dataset.metric = key;
          const lbl = (id === "summary-kpis" && summaryCustomLabels[key]) ? summaryCustomLabels[key] : metricLabel(key);
          card.append(element("div", "stat-label", lbl), element("div", "stat-value", format(key, val)));
          const deltaAliases = {
            engagement: ["engagement", "post_engagement", "total_interactions", "accounts_engaged"],
            post_engagement: ["post_engagement", "engagement", "total_interactions"],
            video_views: ["video_views", "views", "video_play_actions", "plays"],
            views: ["views", "video_views", "video_play_actions", "plays"],
            followers: ["followers", "follower_count", "follows", "page_fans", "page_follows"],
            spend: ["spend", "social_spend", "cost"],
            clicks: ["clicks", "unique_clicks"],
            conversions: ["conversions", "actions", "purchase", "lead"]
          };
          const resolvedDeltaKey = (deltaAliases[key] || [key]).find(k => number(deltas[k]));
          const delta = resolvedDeltaKey ? deltas[resolvedDeltaKey] : (number(deltas[key]) ? deltas[key] : null);
          if (withDeltas && number(delta)) {
            const deltaSuffix = id === "summary-kpis" ? " vs Mes Ant." : " vs. período anterior";
            card.append(element("div", "stat-delta " + (delta > 0 ? "up" : delta < 0 ? "down" : "neutral"), (delta > 0 ? "↑ " : delta < 0 ? "↓ " : "") + format("delta_" + key, Math.abs(delta)) + deltaSuffix));
          }
          container.append(card);
        });
        return keys.length;
      };

      const company = meta.company_name || "Cuenta seleccionada", period = meta.period || {}, periodText = [formatDate(period.start), formatDate(period.end)].filter(Boolean).join(" — "); document.getElementById("company-name").textContent = company; document.getElementById("report-period").textContent = periodText; document.getElementById("generated-at").textContent = formatDate(meta.generated_at); document.getElementById("footer-company").textContent = company; document.getElementById("footer-period").textContent = periodText; (Array.isArray(meta.platforms) ? meta.platforms : []).forEach(value => document.getElementById("hero-platforms").append(element("span", "chip", platformLabel(String(value)))));

      const platformEntries = Object.entries(byPlatform).filter(([, metrics]) => metrics && typeof metrics === "object");
      const platformSpend = platformEntries.reduce((total, [, metrics]) => total + (number(metrics.spend) ? metrics.spend : 0), 0);
      const contentRows = [...(Array.isArray(rows.current) ? rows.current : []), ...(Array.isArray(rows.supplemental) ? rows.supplemental : [])];
      const tiktokRows = contentRows.filter(item => rowPlatform(item) === "tiktok");
      const hasMetaPublisherIdentity = contentRows.some(item => isMeta(item.source_platform) && !isMeta(rowPlatform(item)));
      const hasDirectMetaChannels = platformEntries.some(([key]) => ["facebook", "instagram"].includes(canonical(key)));
      const metaEntry = platformEntries.find(([key]) => isMeta(key));
      const aliasMetrics = { social_spend: "spend", cost: "spend", unique_clicks: "clicks", actions: "conversions", purchase: "conversions", add_to_cart: "conversions", lead: "conversions", total_interactions: "engagement", accounts_engaged: "engagement", like_count: "likes", comment_count: "comments", __results__: "results" };
      const metaMetricKeys = Object.keys(metaEntry?.[1] || {}).map(key => aliasMetrics[key] || key);
      const metricSources = { spend: ["spend", "social_spend", "cost"], clicks: ["clicks", "unique_clicks"], conversions: ["conversions", "actions", "purchase", "add_to_cart", "lead"], engagement: ["engagement", "total_interactions", "accounts_engaged", "likes", "comments", "shares", "saved"], impressions: ["impressions", "reach", "views"], reach: ["reach", "impressions", "views"], likes: ["likes", "like_count"], comments: ["comments", "comment_count"], results: ["results", "__results__"] };
      const rowMetrics = item => { const source = item.source_metrics && typeof item.source_metrics === "object" ? item.source_metrics : {}, keys = new Set([...Object.keys(source).map(key => aliasMetrics[key] || key), ...metaMetricKeys]), values = {}; keys.forEach(key => { const sources = metricSources[key] || [key], raw = sources.find(sourceKey => (sourceKey === key || aliasMetrics[sourceKey] === key) && number(source[sourceKey])); if (raw !== undefined) { values[key] = source[raw]; return } const supplied = sources.some(sourceKey => Object.hasOwn(source, sourceKey)); if (supplied && number(item[key])) values[key] = item[key] }); return values };
      const aggregateRows = items => items.reduce((totals, item) => { Object.entries(rowMetrics(item)).forEach(([key, value]) => { totals[key] = (totals[key] || 0) + value }); return totals }, {});
      const sharedMeta = Boolean(metaEntry && !hasMetaPublisherIdentity && !hasDirectMetaChannels);
      const metaSeries = series.filter(item => isMeta(item.platform));

      const publisherLabels = {
        facebook: "Facebook",
        instagram: "Instagram",
        tiktok: "TikTok",
        audience_network: "Audience Network",
        messenger: "Messenger",
        google_ads: "Google Ads"
      };

      const publisherColors = {
        facebook: "#1877F2",
        instagram: "#E1306C",
        tiktok: "#000000",
        audience_network: "#5865F2",
        messenger: "#00B2FF",
        google_ads: "#4285F4"
      };

      const publisherRows = {};
      contentRows.forEach(item => {
        if (isMeta(item.source_platform)) {
          const pub = rowPlatform(item);
          if (pub) {
            if (!publisherRows[pub]) publisherRows[pub] = [];
            publisherRows[pub].push(item);
          }
        }
      });

      const detectedPubKeys = Object.keys(publisherRows);
      const orderedKeys = Array.from(new Set(["facebook", "instagram", "tiktok", "audience_network", "messenger", ...detectedPubKeys, ...platformEntries.map(([k]) => canonical(k))]));

      // ── DESGLOSE DE KPIS POR RED SOCIAL (Plataformas y Publishers Detectados) ──
      const networkRows = [];
      let totalSpendGlobal = 0, totalImpressionsGlobal = 0, totalReachGlobal = 0;

      orderedKeys.forEach(key => {
        const pRows = key === "tiktok" ? tiktokRows : (publisherRows[key] || []);
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
            label: publisherLabels[key] || platformLabel(key),
            color: publisherColors[key] || "#154095",
            spend: sp,
            impressions: imp,
            reach: rch
          });
        }
      });

      // Fallback to platformEntries if no network separation found
      if (!networkRows.length && platformEntries.length) {
        platformEntries.forEach(([name, metrics]) => {
          const sp = number(metrics.spend) ? metrics.spend : 0;
          const imp = number(metrics.impressions) ? metrics.impressions : 0;
          const rch = number(metrics.reach) ? metrics.reach : null;
          totalSpendGlobal += sp;
          totalImpressionsGlobal += imp;
          if (rch !== null) totalReachGlobal += rch;
          const netKey = canonical(name);
          const col = publisherColors[netKey] || "#154095";
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

      // ── CHARTS: EVOLUCIÓN & SHARE DE IMPRESIONES Y ALCANCE (Plataformas Activas) ──
      const evolutionData = breakdowns.monthly_evolution || null;
      const chartNetworks = networkRows.map(net => ({ key: net.key, label: net.label, color: net.color }));

      let tooltipNode = document.getElementById("chart-floating-tooltip");
      if (!tooltipNode) {
        tooltipNode = document.createElement("div");
        tooltipNode.id = "chart-floating-tooltip";
        tooltipNode.style.cssText = "position:fixed;display:none;pointer-events:none;background:#262b33;color:#ffffff;border-radius:6px;padding:8px 12px;font-size:12px;line-height:1.4;box-shadow:0 6px 18px rgba(0,0,0,0.32);z-index:99999;font-family:var(--sans);";
        document.body.append(tooltipNode);
      }

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
        textEl.textContent = new Intl.NumberFormat("es-EC").format(value) + " " + unit + extra;

        rowEl.append(swatch, textEl);
        tooltipNode.append(titleEl, rowEl);
        tooltipNode.style.display = "block";
        positionChartTooltip(e);
      };

      const positionChartTooltip = (e) => {
        if (!tooltipNode || tooltipNode.style.display === "none") return;
        const x = e.clientX + 12;
        const y = e.clientY - 46;
        tooltipNode.style.left = Math.max(8, Math.min(window.innerWidth - 200, x)) + "px";
        tooltipNode.style.top = Math.max(8, y) + "px";
      };

      const hideChartTooltip = () => {
        if (tooltipNode) tooltipNode.style.display = "none";
      };

      const renderMetricEvolutionAndShare = (metricKey, gridId, legendId, chartId, donutId, donutLegendId, colors) => {
        const chartGrid = document.getElementById(gridId);
        if (!chartGrid) return false;

        // Extract current month values for active channels
        const netItems = chartNetworks.map(net => {
          const pRows = net.key === "tiktok" ? tiktokRows : (publisherRows[net.key] || []);
          const direct = platformEntries.find(([k]) => canonical(k) === net.key)?.[1];
          let val = 0;
          if (pRows.length > 0) {
            const agg = aggregateRows(pRows);
            val = number(agg[metricKey]) ? agg[metricKey] : 0;
          } else if (direct && number(direct[metricKey])) {
            val = direct[metricKey];
          }
          const evoNet = evolutionData?.networks?.[net.key];
          const evoVal = evoNet && evoNet[metricKey] && number(evoNet[metricKey].m0) ? evoNet[metricKey].m0 : (evoNet && number(evoNet.m0) ? evoNet.m0 : val);
          return { key: net.key, label: net.label, color: net.color, currentVal: evoVal || val };
        });

        const totalCurrent = netItems.reduce((acc, item) => acc + item.currentVal, 0);
        if (totalCurrent <= 0 && !evolutionData) return false;

        show(chartGrid, true);

        // 1. Grouped Bar Chart
        let evoMonths = evolutionData?.months || [
          { key: "m0", label: formatDate(period.start) || "Mes actual" }
        ];

        let effectiveMonths = [...evoMonths];
        const hasM2Data = chartNetworks.some(net => {
          const ev = evolutionData?.networks?.[net.key];
          return (ev && ev[metricKey] && number(ev[metricKey].m2) && ev[metricKey].m2 > 0) || (ev && number(ev.m2) && ev.m2 > 0);
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
          swatch.style.background = colors[idx % colors.length];
          item.append(swatch, m.label);
          legendContainer.append(item);
        });

        const evoChart = document.getElementById(chartId);
        const width = 620, height = 250, padL = 75, padR = 20, padT = 20, padB = 36;
        const netGroups = netItems.map(net => {
          const values = effectiveMonths.map((m, idx) => {
            const netEv = evolutionData?.networks?.[net.key];
            if (netEv && netEv[metricKey] && number(netEv[metricKey][m.key])) return netEv[metricKey][m.key];
            if (netEv && number(netEv[m.key])) return netEv[m.key];
            if (idx === effectiveMonths.length - 1) return net.currentVal;
            return 0;
          });
          return { key: net.key, label: net.label, values };
        });

        const allVals = netGroups.flatMap(g => g.values);
        const rawMax = Math.max(...allVals, 1000);
        const magnitude = Math.pow(10, Math.floor(Math.log10(rawMax)));
        const maxVal = Math.ceil(rawMax / (magnitude / 2)) * (magnitude / 2);
        const ns = "http:" + "//www.w3.org/2000/svg";
        evoChart.setAttribute("viewBox", "0 0 " + width + " " + height);
        evoChart.replaceChildren();

        // Horizontal grid lines (4 steps)
        const steps = 4;
        for (let i = 0; i <= steps; i++) {
          const val = maxVal / steps * i;
          const y = padT + (height - padT - padB) * (1 - i / steps);
          const line = document.createElementNS(ns, "line");
          line.setAttribute("x1", padL);
          line.setAttribute("x2", width - padR);
          line.setAttribute("y1", y);
          line.setAttribute("y2", y);
          line.setAttribute("stroke", "#e6edf5");
          line.setAttribute("stroke-width", "1");
          evoChart.append(line);

          const lbl = document.createElementNS(ns, "text");
          lbl.setAttribute("x", padL - 10);
          lbl.setAttribute("y", y + 4);
          lbl.setAttribute("text-anchor", "end");
          lbl.setAttribute("font-size", "10");
          lbl.setAttribute("fill", "#8a96a6");
          lbl.textContent = new Intl.NumberFormat("es-EC").format(val);
          evoChart.append(lbl);
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
            const rect = document.createElementNS(ns, "rect");
            rect.setAttribute("x", x);
            rect.setAttribute("y", y);
            rect.setAttribute("width", barWidth);
            rect.setAttribute("height", barH);
            rect.setAttribute("rx", "3");
            rect.setAttribute("fill", colors[bIdx % colors.length]);
            rect.style.cursor = "pointer";
            rect.style.transition = "opacity 0.15s ease";

            rect.addEventListener("pointerenter", (e) => {
              rect.style.opacity = "0.82";
              showChartTooltip(e, g.label, v, colors[bIdx % colors.length], metricLabel(metricKey));
            });
            rect.addEventListener("pointermove", (e) => {
              positionChartTooltip(e);
            });
            rect.addEventListener("pointerleave", () => {
              rect.style.opacity = "1";
              hideChartTooltip();
            });

            const tip = document.createElementNS(ns, "title");
            tip.textContent = g.label + " (" + effectiveMonths[bIdx].label + "): " + new Intl.NumberFormat("es-EC").format(v) + " " + metricLabel(metricKey).toLowerCase();
            rect.append(tip);
            evoChart.append(rect);
          });

          const nameLbl = document.createElementNS(ns, "text");
          nameLbl.setAttribute("x", gCenter);
          nameLbl.setAttribute("y", height - 12);
          nameLbl.setAttribute("text-anchor", "middle");
          nameLbl.setAttribute("font-size", "11");
          nameLbl.setAttribute("font-weight", "700");
          nameLbl.setAttribute("fill", "#475569");
          nameLbl.textContent = g.label;
          evoChart.append(nameLbl);
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

          const path = document.createElementNS(ns, "path");
          const d = ["M", x1, y1, "A", r, r, 0, largeArc, 1, x2, y2, "L", ix1, iy1, "A", innerR, innerR, 0, largeArc, 0, ix2, iy2, "Z"].join(" ");
          path.setAttribute("d", d);
          path.setAttribute("fill", net.color);
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

          const tip = document.createElementNS(ns, "title");
          tip.textContent = net.label + ": " + new Intl.NumberFormat("es-EC").format(net.currentVal) + " (" + (slice * 100).toFixed(1) + "%)";
          path.append(tip);
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

      // Render Impresiones (Mayo, Junio, Julio palette: gray, steel blue, corporate blue)
      renderMetricEvolutionAndShare(
        "impressions",
        "summary-charts-grid",
        "summary-evolution-legend",
        "summary-evolution-chart",
        "summary-share-chart",
        "summary-share-legend",
        ["#ECECEC", "#A5C0DB", "#154095"]
      );

      // Render Alcance (Junio, Julio palette: corporate blue, sky blue)
      renderMetricEvolutionAndShare(
        "reach",
        "summary-reach-grid",
        "summary-reach-evolution-legend",
        "summary-reach-evolution-chart",
        "summary-reach-share-chart",
        "summary-reach-share-legend",
        ["#154095", "#38BDF8", "#ECECEC"]
      );

      const renderTrend = (prefix, items) => { const candidates = ordered(Object.assign({}, ...items.map(item => item.metrics || {}))), metric = ["impressions", "reach", "views", "video_views", "spend", "engagement", "clicks"].find(key => candidates.includes(key)) || candidates[0]; if (!metric) return false; const daily = new Map; items.forEach(item => { const value = (item.metrics || {})[metric]; if (number(value)) daily.set(item.date, (daily.get(item.date) || 0) + value) }); const points = [...daily.entries()].sort(([a], [b]) => a.localeCompare(b)); if (!points.length) return false; const svg = document.getElementById(prefix + "-chart"), width = 900, height = 245, left = 50, right = 20, top = 22, bottom = 52, max = Math.max(...points.map(([, value]) => value), 1), x = index => left + (points.length === 1 ? (width - left - right) / 2 : index * (width - left - right) / (points.length - 1)), y = value => top + (height - top - bottom) * (1 - value / max), ns = "http:" + "//www.w3.org/2000/svg"; svg.setAttribute("viewBox", "0 0 " + width + " " + height); const axis = document.createElementNS(ns, "line"); for (const [key, value] of Object.entries({ class: "chart-axis", x1: left, x2: width - right, y1: height - bottom, y2: height - bottom })) axis.setAttribute(key, value); svg.append(axis); const coords = points.map(([, value], index) => x(index) + "," + y(value)), area = document.createElementNS(ns, "polygon"); area.setAttribute("class", "chart-area"); area.setAttribute("points", left + "," + (height - bottom) + " " + coords.join(" ") + " " + (width - right) + "," + (height - bottom)); svg.append(area); const line = document.createElementNS(ns, "polyline"); line.setAttribute("class", "chart-line"); line.setAttribute("points", coords.join(" ")); svg.append(line); const every = Math.max(1, Math.ceil(points.length / 7)); points.forEach(([day, value], index) => { const dot = document.createElementNS(ns, "circle"); dot.setAttribute("class", "chart-dot"); dot.setAttribute("cx", x(index)); dot.setAttribute("cy", y(value)); dot.setAttribute("r", 4); const title = document.createElementNS(ns, "title"); title.textContent = formatDate(day) + ": " + format(metric, value); dot.append(title); svg.append(dot); if (index % every === 0 || index === points.length - 1) { const label = document.createElementNS(ns, "text"); label.setAttribute("class", "chart-label"); label.setAttribute("data-trend-tick", "true"); label.setAttribute("x", x(index)); label.setAttribute("y", height - 17); label.setAttribute("text-anchor", "end"); label.setAttribute("transform", "rotate(-28 " + x(index) + " " + (height - 17) + ")"); label.textContent = formatDate(day); svg.append(label) } }); document.getElementById(prefix + "-trend-label").textContent = metricLabel(metric); const body = document.getElementById(prefix + "-trend-body"); points.forEach(([day, value]) => { const row = element("tr"); row.append(element("td", "", formatDate(day)), element("td", "", format(metric, value))); body.append(row) }); return true };
      const generalNarratives = narratives.filter(item => typeof item === "string" || (item && !item.platform)); generalNarratives.map(item => typeof item === "string" ? item : item.text || item.summary || item.value).filter(Boolean).forEach(value => { const node = element("p", "narrative", value); node.dataset.family = "narrative"; document.getElementById("summary-narratives").append(node) }); const summaryKpis = renderKpis("summary-kpis", summary, true, summaryAllowedKeys); setPanel("summary-panel", summaryKpis > 0 || hasSummaryTable || generalNarratives.length > 0);

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
        const competitionMetrics = Object.keys(genericCompList[0]).filter(key => key !== "label" && key !== "name" && genericCompList.every(item => number(item[key])));
        if (competitionMetrics.length) {
          const head = document.getElementById("competition-head");
          head.append(element("th", "", "Cuenta"));
          competitionMetrics.forEach(key => head.append(element("th", "", metricLabel(key))));
          genericCompList.forEach(item => {
            const row = element("tr");
            row.append(element("td", "", item.label || item.name || "Cuenta"));
            competitionMetrics.forEach(key => row.append(element("td", "", format(key, item[key]))));
            document.getElementById("competition-body").append(row);
          });
          show(document.getElementById("competition-generic-card"), true);
          hasCompetition = true;
        }
      }

      setPanel("competition-panel", hasCompetition);

      const renderContent = (name, items) => { const excludedMetrics = new Set(["video_views", "views", "video_play_actions", "plays"]); const normalized = items.map(item => ({ item, values: rowMetrics(item) })), metrics = normalized.length ? ordered(normalized[0].values).filter(key => !excludedMetrics.has(key) && normalized.every(entry => number(entry.values[key])) && normalized.some(entry => Number(entry.values[key]) > 0)).slice(0, 6) : []; if (!normalized.length || !metrics.length) return false; const head = document.getElementById(name + "-content-head"); head.append(element("th", "", "Campaña o contenido")); metrics.forEach(key => head.append(element("th", "", metricLabel(key)))); normalized.sort((a, b) => b.values[metrics[0]] - a.values[metrics[0]]).slice(0, 12).forEach(({ item, values }) => { const row = element("tr"); row.append(element("td", "", item.campaign_name || item.ad_name || item.content_name || item.name || "Contenido")); metrics.forEach(key => row.append(element("td", "", format(key, values[key])))); document.getElementById(name + "-content-body").append(row) }); return true }, renderDemographics = name => { const target = document.getElementById(name + "-breakdowns"); Object.entries(platformBreakdowns(name)).forEach(([group, value]) => { const items = normalizeBreakdown(group, value); if (!items.length) return; const card = element("div", "card"), list = element("div", "breakdown-list"), max = Math.max(...items.map(item => item.value), 1); card.append(element("h4", "card-title", metricLabel(group))); items.sort((a, b) => b.value - a.value).slice(0, 10).forEach(item => { const row = element("div", "breakdown-row"), metaRow = element("div", "breakdown-meta"), bar = element("div", "breakdown-bar"), fill = element("div", "breakdown-fill"); metaRow.append(element("span", "breakdown-name", item.label), element("span", "breakdown-value", format(group.includes("share") || group.includes("percent") ? "share" : "value", item.value))); fill.style.width = Math.max(2, item.value / max * 100) + "%"; bar.append(fill); row.append(metaRow, bar); list.append(row) }); card.append(list); target.append(card) }); return target.children.length > 0 };
      const normalizeBreakdown = (key, value) => { if (Array.isArray(value)) return value.map(item => item && typeof item === "object" ? { label: item.label ?? item.name ?? item[key] ?? item.dimension, value: item.value ?? item.count ?? item.impressions ?? item.reach ?? item.percentage ?? item.share } : null).filter(item => item && item.label !== undefined && number(item.value)); if (value && typeof value === "object") return Object.entries(value).filter(([, amount]) => number(amount)).map(([label, amount]) => ({ label, value: amount })); return [] };
      const platformBreakdowns = name => { const direct = breakdowns[name]; if (direct && typeof direct === "object" && !Array.isArray(direct)) return direct; return Object.fromEntries(Object.entries(breakdowns).filter(([key]) => canonical(key) === name).map(([key, value]) => [key.replace(name, "").replace(/^_|_$/g, "") || "audience", value])) };

      for (const name of ["facebook", "instagram", "tiktok"]) { const direct = platformEntries.find(([key]) => canonical(key) === name)?.[1], publisherItems = publisherRows[name] || [], usesSharedMeta = sharedMeta && (name === "facebook" || name === "instagram"), metrics = direct || (publisherItems.length ? aggregateRows(publisherItems) : usesSharedMeta ? metaEntry[1] : {}), trendItems = direct ? series.filter(item => canonical(item.platform) === name) : publisherItems.length ? publisherItems.map(item => ({ date: item.date, metrics: rowMetrics(item) })) : usesSharedMeta ? metaSeries : [], contentItems = usesSharedMeta ? [] : contentRows.filter(item => rowPlatform(item) === name), kpis = renderKpis(name + "-kpis", metrics), hasTrend = renderTrend(name, trendItems), hasContent = renderContent(name, contentItems), hasDemographics = renderDemographics(name), platformNarratives = narratives.filter(item => item && typeof item === "object" && canonical(item.platform) === name).map(item => item.text || item.summary || item.value).filter(Boolean); if (name === "facebook" || name === "instagram") { const notice = document.getElementById(name + "-shared-meta"); notice.textContent = usesSharedMeta ? "Datos agregados de Meta compartidos entre Facebook e Instagram; no se atribuye una distribución por red." : ""; show(notice, usesSharedMeta) } show(document.getElementById(name + "-trend"), hasTrend); show(document.getElementById(name + "-content"), hasContent); show(document.getElementById(name + "-demographics"), hasDemographics); platformNarratives.forEach(value => { const node = element("p", "narrative", value); node.dataset.family = "narrative"; document.getElementById(name + "-narratives").append(node) }); setPanel(name + "-panel", kpis > 0 || hasTrend || hasContent || hasDemographics || platformNarratives.length > 0) }
      const investmentRows = platformEntries.filter(([, metrics]) => number(metrics.spend)); investmentRows.forEach(([name, metrics]) => { const row = element("tr"); row.append(element("td", "", platformLabel(name)), element("td", "", format("spend", metrics.spend)), element("td", "", platformSpend > 0 ? format("share", metrics.spend / platformSpend * 100) : "")); document.getElementById("investment-body").append(row) }); show(document.getElementById("investment-table"), investmentRows.length > 0); const optimization = [...Object.entries(rates).filter(([, value]) => number(value)), ...Object.entries(deltas).filter(([, value]) => number(value)).map(([key, value]) => ["delta_" + key, value])]; optimization.slice(0, 12).forEach(([key, value]) => { const row = element("div", "breakdown-meta"), isDelta = key.startsWith("delta_"); row.append(element("span", "breakdown-name", isDelta ? "Variación de " + metricLabel(key.slice(6)) : metricLabel(key)), element("span", "breakdown-value " + (isDelta ? (value > 0 ? "up" : value < 0 ? "down" : "neutral") : ""), format(key, value))); document.getElementById("optimization-list").append(row) }); show(document.getElementById("optimization-card"), optimization.length > 0); setPanel("investment-panel", investmentRows.length > 0 || optimization.length > 0);
      const showTab = (targetId, btn) => { const target = document.getElementById(targetId); if (!target || target.hidden) return; const parentNav = btn?.closest('.secondary-nav'); if (parentNav) parentNav.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active')); if (btn) btn.classList.add('active'); document.querySelectorAll('.report-panel').forEach(panel => panel.classList.remove('active')); target.classList.add('active'); window.scrollTo({ top: 0, behavior: 'smooth' }) };
      const switchMainTab = (tabId, btn) => { document.querySelectorAll('.main-tab-btn').forEach(b => b.classList.remove('active')); btn.classList.add('active'); document.querySelectorAll('.secondary-nav').forEach(nav => nav.style.display = 'none'); const subNav = document.getElementById('subnav-' + tabId); if (subNav) { subNav.style.display = 'flex'; const firstBtn = [...subNav.querySelectorAll('.tab-btn')].find(b => !b.hidden); if (firstBtn) firstBtn.click() } };
      document.querySelectorAll('.main-tab-btn').forEach(btn => { btn.addEventListener('click', () => switchMainTab(btn.dataset.mainTab, btn)) });
      document.querySelectorAll('.tab-btn').forEach(btn => { btn.addEventListener('click', () => showTab(btn.dataset.target, btn)) });
      const firstActiveTab = document.querySelector('.secondary-nav .tab-btn:not([hidden])'); if (firstActiveTab) firstActiveTab.click();
    })();