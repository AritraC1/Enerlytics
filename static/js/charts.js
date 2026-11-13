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

  function baseOptions() {
    return {
      responsive: true,
      maintainAspectRatio: false,
      font: {
        family: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
      },
      plugins: {
        legend: {
          display: true,
          position: "bottom",
          labels: {
            color: "#475569",
            font: {
              family: "'Inter', -apple-system, sans-serif",
              size: 11,
              weight: "500"
            },
            padding: 14,
            usePointStyle: true,
            pointStyle: "circle"
          }
        },
        tooltip: {
          backgroundColor: "#0f172a",
          titleColor: "#ffffff",
          bodyColor: "#f8fafc",
          titleFont: { weight: "600", size: 12 },
          bodyFont: { size: 11 },
          padding: 10,
          cornerRadius: 8,
          boxPadding: 4,
          borderColor: "#334155",
          borderWidth: 1
        }
      }
    };
  }

  function axisOptions() {
    return {
      scales: {
        x: {
          beginAtZero: true,
          grid: {
            color: "rgba(226, 232, 240, 0.7)",
            drawBorder: false
          },
          ticks: {
            color: "#64748b",
            font: {
              family: "'Inter', -apple-system, sans-serif",
              size: 11
            }
          }
        },
        y: {
          beginAtZero: true,
          grid: {
            color: "rgba(226, 232, 240, 0.7)",
            drawBorder: false
          },
          ticks: {
            color: "#64748b",
            font: {
              family: "'Inter', -apple-system, sans-serif",
              size: 11
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
      options.indexAxis = "y";
      options.scales = {
        x: {
          beginAtZero: true,
          grid: { color: "rgba(226, 232, 240, 0.7)", drawBorder: false },
          ticks: { color: "#64748b", font: { size: 11 } }
        },
        y: {
          beginAtZero: true,
          grid: { display: false },
          ticks: { color: "#64748b", font: { size: 11 } }
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
    var options = baseOptions();
    options.cutout = "68%";
    options.plugins.legend.position = "right";
    options.plugins.legend.labels.padding = 10;

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
    var options = baseOptions();
    options.plugins.legend = { display: false };
    options.scales = {
      x: {
        title: {
          display: true,
          text: "Intensity",
          color: "#475569",
          font: { weight: "600", size: 11 }
        },
        beginAtZero: true,
        grid: { color: "rgba(226, 232, 240, 0.7)", drawBorder: false },
        ticks: { color: "#64748b" }
      },
      y: {
        title: {
          display: true,
          text: "Likelihood",
          color: "#475569",
          font: { weight: "600", size: 11 }
        },
        beginAtZero: true,
        grid: { color: "rgba(226, 232, 240, 0.7)", drawBorder: false },
        ticks: { color: "#64748b" }
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

  function render(spec) {
    var canvas = document.getElementById("chart-" + spec.id);
    if (!canvas || typeof Chart === "undefined") return;

    var existing = Chart.getChart(canvas);
    if (existing) existing.destroy();

    var ctx = canvas.getContext("2d");
    var config = buildConfig(spec, ctx);
    if (!config) return;

    new Chart(canvas, config);
  }

  function renderAll() {
    parseSpecs().forEach(render);
  }

  // Handle smooth resize when sidebar collapses or expands
  function handleResize() {
    if (typeof Chart === "undefined") return;
    setTimeout(function () {
      Object.keys(Chart.instances || {}).forEach(function (key) {
        if (Chart.instances[key]) {
          Chart.instances[key].resize();
        }
      });
    }, 260);
  }

  window.addEventListener("sidebar-toggle", handleResize);
  window.addEventListener("resize", handleResize);

  document.addEventListener("DOMContentLoaded", renderAll);
  document.addEventListener("htmx:afterSettle", renderAll);
})();
