/* ==========================================================================
   Enerlytics Dashboard — Frontend Interactions
   ========================================================================== */

(function () {
  "use strict";

  var STORAGE_KEY = "enerlytics_sidebar_collapsed";

  function initSidebar() {
    var sidebar = document.getElementById("app-sidebar");
    var toggleBtn = document.getElementById("sidebar-toggle-btn");
    var mobileToggle = document.getElementById("mobile-menu-toggle");
    if (!sidebar) return;

    // Apply saved state before rendering
    var isCollapsed = localStorage.getItem(STORAGE_KEY) === "true";
    if (isCollapsed) {
      sidebar.classList.add("collapsed");
      document.body.classList.add("sidebar-is-collapsed");
    }

    function toggleSidebar() {
      var willCollapse = !sidebar.classList.contains("collapsed");
      sidebar.classList.toggle("collapsed", willCollapse);
      document.body.classList.toggle("sidebar-is-collapsed", willCollapse);
      localStorage.setItem(STORAGE_KEY, willCollapse ? "true" : "false");

      // Notify Chart.js and layout observers to resize smoothly
      window.dispatchEvent(new Event("resize"));
      window.dispatchEvent(new CustomEvent("sidebar-toggle", { detail: { collapsed: willCollapse } }));
    }

    if (toggleBtn) {
      toggleBtn.addEventListener("click", function (e) {
        e.preventDefault();
        toggleSidebar();
      });
    }

    // Mobile sidebar toggle
    if (mobileToggle) {
      mobileToggle.addEventListener("click", function () {
        sidebar.classList.toggle("mobile-open");
      });

      // Close mobile sidebar when clicking outside
      document.addEventListener("click", function (e) {
        if (sidebar.classList.contains("mobile-open") &&
            !sidebar.contains(e.target) &&
            !mobileToggle.contains(e.target)) {
          sidebar.classList.remove("mobile-open");
        }
      });
    }

    // Keyboard shortcut '[' to toggle sidebar
    document.addEventListener("keydown", function (e) {
      if (e.key === "[" && !["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement.tagName)) {
        e.preventDefault();
        toggleSidebar();
      }
    });
  }

  // Real-time table search/filter
  function initTableSearch() {
    var searchInput = document.getElementById("table-quick-search");
    var table = document.getElementById("insights-table-body");
    if (!searchInput || !table) return;

    searchInput.addEventListener("input", function () {
      var query = searchInput.value.toLowerCase().trim();
      var rows = table.querySelectorAll("tr");
      var visibleCount = 0;

      rows.forEach(function (row) {
        var text = row.textContent.toLowerCase();
        if (!query || text.indexOf(query) !== -1) {
          row.style.display = "";
          visibleCount++;
        } else {
          row.style.display = "none";
        }
      });

      var countBadge = document.getElementById("table-visible-count");
      if (countBadge) {
        countBadge.textContent = query ? visibleCount + " matching" : rows.length + " shown";
      }
    });
  }

  // Export table to CSV
  function initExportCsv() {
    var exportBtn = document.getElementById("export-table-csv-btn");
    if (!exportBtn) return;

    exportBtn.addEventListener("click", function (e) {
      e.preventDefault();
      var table = document.querySelector(".insights-table");
      if (!table) return;

      var rows = table.querySelectorAll("tr");
      var csv = [];

      rows.forEach(function (row) {
        if (row.style.display === "none") return; // Skip hidden rows
        var cols = row.querySelectorAll("th, td");
        var rowData = [];
        cols.forEach(function (col) {
          var cleanText = col.innerText.replace(/"/g, '""').trim();
          rowData.push('"' + cleanText + '"');
        });
        if (rowData.length > 0) {
          csv.push(rowData.join(","));
        }
      });

      var blob = new Blob([csv.join("\n")], { type: "text/csv;charset=utf-8;" });
      var url = URL.createObjectURL(blob);
      var link = document.createElement("a");
      link.setAttribute("href", url);
      link.setAttribute("download", "enerlytics_insights_" + new Date().toISOString().slice(0, 10) + ".csv");
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    });
  }

  // Drop empty filter params from HTMX requests to keep URLs clean
  document.addEventListener("htmx:configRequest", function (evt) {
    var params = evt.detail.parameters;
    if (params) {
      Object.keys(params).forEach(function (key) {
        if (params[key] === "") delete params[key];
      });
    }
  });

  // Re-initialize dynamic handlers after HTMX partial swap
  document.addEventListener("htmx:afterSettle", function () {
    initTableSearch();
    initExportCsv();
  });

  // Initialize on page load
  document.addEventListener("DOMContentLoaded", function () {
    initSidebar();
    initTableSearch();
    initExportCsv();
  });
})();

