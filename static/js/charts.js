/*
 * Enerlytics dashboard charts — Light Mode Optimized.
 *
 * Reads the chart specs injected by the Django view (see
 * `{{ charts|json_script:"chart-data" }}` in dashboard/index.html) and
 * renders one Chart.js chart per <canvas id="chart-<id>">. All calculation
 * happens server-side in insights/services.py; this file only draws.
 */

(function () {
  "use strict";

  // Modern light-mode color palette
  var PALETTE = [
    "#2563eb", // Royal Blue
    "#10b981", // Emerald
    "#8b5cf6", // Purple
    "#f59e0b", // Amber
    "#06b6d4", // Cyan
    "#ef4444", // Rose
    "#6366f1", // Indigo
    "#ec4899", // Pink
    "#14b8a6", // Teal
    "#f97316", // Orange
    "#84cc16", // Lime
    "#64748b"  // Slate
  ];

  function parseSpecs() {
    var node = document.getElementById("chart-data");
    if (!node) return [];
    try {
      return JSON.parse(node.textContent);
    } catch (err) {
      console.error("Enerlytics: invalid chart data", err);
      return [];
    }
  }

  function solid(color, alpha) {
    var hex = color.replace("#", "");
    var r = parseInt(hex.slice(0, 2), 16);
    var g = parseInt(hex.slice(2, 4), 16);
    var b = parseInt(hex.slice(4, 6), 16);
    return "rgba(" + r + ", " + g + ", " + b + ", " + alpha + ")";
  }

  function isMobileView() {
    return window.innerWidth <= 768;
  }

  // Chart chrome colors are picked from the active theme (light default).
  // Charts re-render via the "theme-change" event when the mode is toggled.
  function chartTheme() {
    var dark = document.documentElement.getAttribute("data-theme") === "dark";
    return {
      legendLabel: dark ? "#cbd5e1" : "#475569",
      tick: dark ? "#94a3b8" : "#64748b",
      grid: dark ? "rgba(51, 65, 85, 0.7)" : "rgba(226, 232, 240, 0.7)"
    };
  }

  function baseOptions() {
    var mobile = isMobileView();
    var theme = chartTheme();
    return {
      responsive: true,
      maintainAspectRatio: false,
      resizeDelay: 50,
      font: {
        family: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
      },
      plugins: {
        legend: {
          display: true,
          position: "bottom",
          labels: {
            color: theme.legendLabel,
            font: {
              family: "'Inter', -apple-system, sans-serif",
              size: mobile ? 10 : 11,
              weight: "500"
            },
            padding: mobile ? 8 : 14,
            usePointStyle: true,
            pointStyle: "circle",
            boxWidth: mobile ? 6 : 8,
            boxHeight: mobile ? 6 : 8
          }
        },
        tooltip: {
          backgroundColor: "#0f172a",
          titleColor: "#ffffff",
          bodyColor: "#f8fafc",
          titleFont: { weight: "600", size: mobile ? 11 : 12 },
          bodyFont: { size: mobile ? 10 : 11 },
          padding: mobile ? 8 : 10,
          cornerRadius: 8,
          boxPadding: 4,
          borderColor: "#334155",
          borderWidth: 1
        }
      }
    };
  }

  function axisOptions() {
    var mobile = isMobileView();
    var theme = chartTheme();
    return {
      scales: {
        x: {
          beginAtZero: true,
          grid: {
            color: theme.grid,
            drawBorder: false
          },
          ticks: {
            color: theme.tick,
            autoSkip: true,
            maxRotation: mobile ? 45 : 0,
            font: {
              family: "'Inter', -apple-system, sans-serif",
              size: mobile ? 9 : 11
            }
          }
        },
        y: {
          beginAtZero: true,
          grid: {
            color: theme.grid,
            drawBorder: false
          },
          ticks: {
            color: theme.tick,
            font: {
              family: "'Inter', -apple-system, sans-serif",
              size: mobile ? 9 : 11
            }
          }
        }
      }
    };
  }

  function buildConfig(spec, ctx) {
    switch (spec.type) {
      case "bar":
        return buildBar(spec, ctx);
      case "doughnut":
        return buildDoughnut(spec);
      case "line":
        return buildLine(spec, ctx);
      case "scatter":
        return buildScatter(spec);
      default:
        console.warn("Enerlytics: unknown chart type", spec.type);
        return null;
    }
  }

  function buildBar(spec, ctx) {
    var options = baseOptions();
    Object.assign(options, axisOptions());
    if (spec.labels && spec.labels.length > 6) {
      options.plugins.legend = { display: false };
    }

    var primaryColor = PALETTE[0];
    if (spec.id === "topics") primaryColor = PALETTE[1];
    else if (spec.id === "regions") primaryColor = PALETTE[2];
    else if (spec.id === "intensity") primaryColor = PALETTE[3];

    var dataset = {
      label: spec.title,
      data: spec.values,
      backgroundColor: solid(primaryColor, 0.85),
      hoverBackgroundColor: primaryColor,
      borderColor: primaryColor,
      borderWidth: 1,
      borderRadius: spec.horizontal ? { topRight: 6, bottomRight: 6 } : 6
    };

    if (spec.horizontal) {
      var mobile = isMobileView();
      var theme = chartTheme();
      options.indexAxis = "y";
      options.scales = {
        x: {
          beginAtZero: true,
          grid: { color: theme.grid, drawBorder: false },
          ticks: { color: theme.tick, font: { size: mobile ? 9 : 11 } }
        },
        y: {
          beginAtZero: true,
          grid: { display: false },
          ticks: { color: theme.tick, autoSkip: false, font: { size: mobile ? 9 : 11 } }
        }
      };
    }

    return {
      type: "bar",
      data: { labels: spec.labels, datasets: [dataset] },
      options: options
    };
  }

  function buildDoughnut(spec) {
    var mobile = isMobileView();
    var options = baseOptions();
    options.cutout = mobile ? "60%" : "68%";
    options.plugins.legend.position = mobile ? "bottom" : "right";
    options.plugins.legend.labels.padding = mobile ? 8 : 10;

    var colors = spec.labels.map(function (_, i) {
      return PALETTE[i % PALETTE.length];
    });

    return {
      type: "doughnut",
      data: {
        labels: spec.labels,
        datasets: [{
          data: spec.values,
          backgroundColor: colors,
          borderColor: "#ffffff",
          borderWidth: 2,
          hoverOffset: 4
        }]
      },
      options: options
    };
  }

  function buildLine(spec, ctx) {
    var options = baseOptions();
    Object.assign(options, axisOptions());
    options.plugins.legend = { display: false };
    options.elements = { line: { tension: 0.35 } };

    var gradient = null;
    if (ctx) {
      gradient = ctx.createLinearGradient(0, 0, 0, 280);
      gradient.addColorStop(0, "rgba(37, 99, 235, 0.25)");
      gradient.addColorStop(1, "rgba(37, 99, 235, 0.01)");
    }

    return {
      type: "line",
      data: {
        labels: spec.labels,
        datasets: [{
          label: spec.title,
          data: spec.values,
          borderColor: PALETTE[0],
          borderWidth: 2.5,
          backgroundColor: gradient || solid(PALETTE[0], 0.15),
          fill: true,
          pointRadius: 3,
          pointHoverRadius: 6,
          pointBackgroundColor: "#ffffff",
          pointBorderColor: PALETTE[0],
          pointBorderWidth: 2
        }]
      },
      options: options
    };
  }

  function buildScatter(spec) {
    var theme = chartTheme();
    var options = baseOptions();
    options.plugins.legend = { display: false };
    options.scales = {
      x: {
        title: {
          display: true,
          text: "Intensity",
          color: theme.tick,
          font: { weight: "600", size: 11 }
        },
        beginAtZero: true,
        grid: { color: theme.grid, drawBorder: false },
        ticks: { color: theme.tick }
      },
      y: {
        title: {
          display: true,
          text: "Likelihood",
          color: theme.tick,
          font: { weight: "600", size: 11 }
        },
        beginAtZero: true,
        grid: { color: theme.grid, drawBorder: false },
        ticks: { color: theme.tick }
      }
    };

    return {
      type: "scatter",
      data: {
        datasets: [{
          label: spec.title,
          data: spec.points,
          backgroundColor: solid(PALETTE[0], 0.5),
          borderColor: PALETTE[0],
          borderWidth: 1.5,
          pointRadius: 4,
          pointHoverRadius: 7
        }]
      },
      options: options
    };
  }

  function destroyAll() {
    if (typeof Chart === "undefined") return;
    Object.keys(Chart.instances || {}).forEach(function (key) {
      try {
        if (Chart.instances[key]) {
          Chart.instances[key].destroy();
        }
      } catch (err) {}
    });
  }

  function render(spec, skipAnimation) {
    var canvas = document.getElementById("chart-" + spec.id);
    if (!canvas || typeof Chart === "undefined") return;

    var existing = Chart.getChart(canvas);
    if (existing) {
      try {
        existing.destroy();
      } catch (err) {}
    }

    // Chart.js writes inline width/height on the canvas while rendering.
    // Clear them so a stale size from a previous render can never inflate the
    // (fixed-height) container on re-render.
    canvas.style.width = "";
    canvas.style.height = "";

    var ctx = canvas.getContext("2d");
    var config = buildConfig(spec, ctx);
    if (!config) return;

    // Theme-change re-renders happen inside the View Transitions update
    // callback: the browser captures the "new" snapshot the moment the
    // callback returns, and Chart.js's first (animated) frame would not be
    // painted yet. Disabling animation makes Chart.js draw synchronously, so
    // the snapshot shows fully rendered charts in the new palette.
    if (skipAnimation && config.options) {
      config.options.animation = false;
    }

    new Chart(canvas, config);
  }

  function renderAll(skipAnimation) {
    destroyAll();
    parseSpecs().forEach(function (spec) {
      render(spec, skipAnimation);
    });
  }

  // Handle smooth resize when sidebar collapses/expands or window resizes
  var resizeTimer = null;
  function handleResize() {
    if (typeof Chart === "undefined") return;
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () {
      Object.keys(Chart.instances || {}).forEach(function (key) {
        var chart = Chart.instances[key];
        if (chart && chart.canvas && chart.canvas.isConnected) {
          chart.resize();
        }
      });
    }, 150);
  }

  // Teardown previous chart instances before HTMX swaps new DOM in
  document.addEventListener("htmx:beforeSwap", function (evt) {
    var target = evt.detail && evt.detail.target;
    if (target && (target.id === "dashboard-content" || target.closest("#dashboard-content"))) {
      destroyAll();
    }
  });

  window.addEventListener("sidebar-toggle", handleResize);
  window.addEventListener("resize", handleResize);

  // Re-render charts with the new palette when the light/dark mode is toggled.
  // skipAnimation=true so the canvases are painted synchronously and the
  // view-transition snapshot captures them fully rendered.
  window.addEventListener("theme-change", function () {
    renderAll(true);
  });

  document.addEventListener("DOMContentLoaded", renderAll);
  document.addEventListener("htmx:afterSettle", renderAll);
})();
