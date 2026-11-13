/* ==========================================================================
   Enerlytics Dashboard — Frontend Interactions
   ========================================================================== */

(function () {
  "use strict";

  var STORAGE_KEY = "enerlytics_sidebar_collapsed";
  var THEME_KEY = "enerlytics_theme";
  var MOBILE_BREAKPOINT = 768;

  function initSidebar() {
    var sidebar = document.getElementById("app-sidebar");
    var toggleBtn = document.getElementById("sidebar-toggle-btn");
    var mobileToggle = document.getElementById("mobile-menu-toggle");
    if (!sidebar) return;

    var backdrop = document.getElementById("sidebar-backdrop");

    function isMobileView() {
      return window.innerWidth <= MOBILE_BREAKPOINT;
    }

    // Single source of truth for collapse state (sidebar, body and <html> —
    // the FOUC script in base.html sets the class on <html>).
    function applyCollapsed(collapsed) {
      sidebar.classList.toggle("collapsed", collapsed);
      document.body.classList.toggle("sidebar-is-collapsed", collapsed);
      document.documentElement.classList.toggle("sidebar-is-collapsed", collapsed);
    }

    // Apply saved state before rendering
    applyCollapsed(localStorage.getItem(STORAGE_KEY) === "true");

    // Collapse (icon-only) mode is desktop-only. On mobile the drawer must
    // always render fully expanded — a saved "collapsed" preference must
    // never leak into the mobile drawer (it causes the wide-but-icon-only
    // stuck state).
    if (isMobileView()) {
      applyCollapsed(false);
    }

    function toggleSidebar() {
      if (isMobileView()) return; // no-op in mobile drawer mode

      var willCollapse = !sidebar.classList.contains("collapsed");
      applyCollapsed(willCollapse);
      localStorage.setItem(STORAGE_KEY, willCollapse ? "true" : "false");

      // Notify Chart.js and layout observers to resize smoothly
      window.dispatchEvent(new Event("resize"));
      window.dispatchEvent(new CustomEvent("sidebar-toggle", { detail: { collapsed: willCollapse } }));
    }

    // Mobile sidebar toggle & backdrop
    function closeMobileSidebar() {
      sidebar.classList.remove("mobile-open");
      if (backdrop) backdrop.classList.remove("active");
      document.body.classList.remove("sidebar-mobile-locked");
    }

    function openMobileSidebar() {
      // Defensive: the drawer is always fully expanded, never icon-only
      sidebar.classList.remove("collapsed");
      document.body.classList.remove("sidebar-is-collapsed");
      document.documentElement.classList.remove("sidebar-is-collapsed");

      sidebar.classList.add("mobile-open");
      if (backdrop) backdrop.classList.add("active");
      document.body.classList.add("sidebar-mobile-locked");
    }

    if (toggleBtn) {
      toggleBtn.addEventListener("click", function (e) {
        e.preventDefault();
        toggleSidebar();
      });
    }

    if (mobileToggle) {
      mobileToggle.addEventListener("click", function (e) {
        e.stopPropagation();
        if (sidebar.classList.contains("mobile-open")) {
          closeMobileSidebar();
        } else {
          openMobileSidebar();
        }
      });
    }

    if (backdrop) {
      backdrop.addEventListener("click", function () {
        closeMobileSidebar();
      });
    }

    // Close mobile sidebar when clicking outside
    document.addEventListener("click", function (e) {
      if (sidebar.classList.contains("mobile-open") &&
          !sidebar.contains(e.target) &&
          (!mobileToggle || !mobileToggle.contains(e.target))) {
        closeMobileSidebar();
      }
    });

    // Auto-close mobile sidebar when clicking internal navigation anchor links
    sidebar.querySelectorAll(".sidebar-nav a").forEach(function (link) {
      link.addEventListener("click", function () {
        if (isMobileView()) {
          closeMobileSidebar();
        }
      });
    });

    // Keyboard shortcut '[' to toggle sidebar, 'Escape' to close mobile drawer
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && sidebar.classList.contains("mobile-open")) {
        closeMobileSidebar();
        return;
      }
      if (e.key === "[" && !["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement.tagName)) {
        e.preventDefault();
        toggleSidebar();
      }
    });

    // Keep drawer/collapse state consistent when crossing the breakpoint
    // (rotating a phone, or resizing a desktop window across 768px).
    var breakpointTimer = null;
    window.addEventListener("resize", function () {
      clearTimeout(breakpointTimer);
      breakpointTimer = setTimeout(function () {
        closeMobileSidebar();
        if (isMobileView()) {
          applyCollapsed(false); // drawer is always expanded on mobile
        } else {
          applyCollapsed(localStorage.getItem(STORAGE_KEY) === "true");
        }
      }, 150);
    });
  }

  // Light / Dark mode toggle (sun = light, moon = dark; default: light).
  // The new theme does not switch instantly — it slides in from the toggler
  // as a circular reveal anchored at the button (View Transitions API), with
  // an instant fallback for browsers that don't support it.
  function initThemeToggle() {
    var btn = document.getElementById("theme-toggle-btn");
    if (!btn) return;

    function currentTheme() {
      return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
    }

    function reflectState() {
      var isDark = currentTheme() === "dark";
      btn.setAttribute("aria-pressed", isDark ? "true" : "false");
      btn.title = isDark ? "Switch to light mode" : "Switch to dark mode";
    }

    function applyTheme(next) {
      document.documentElement.setAttribute("data-theme", next);
      try {
        localStorage.setItem(THEME_KEY, next);
      } catch (e) {}
      reflectState();
    }

    btn.addEventListener("click", function (e) {
      e.preventDefault();
      var next = currentTheme() === "dark" ? "light" : "dark";

      // Anchor the slide-in reveal at the toggler itself
      var rect = btn.getBoundingClientRect();
      var x = rect.left + rect.width / 2 + window.scrollX;
      var y = rect.top + rect.height / 2 + window.scrollY;
      document.documentElement.style.setProperty("--theme-toggle-x", x + "px");
      document.documentElement.style.setProperty("--theme-toggle-y", y + "px");

      function change() {
        applyTheme(next);
        // Charts read theme colors at render time — re-render them with the
        // new palette while still inside the transition's update callback.
        window.dispatchEvent(new CustomEvent("theme-change", { detail: { theme: next } }));
      }

      if (typeof document.startViewTransition === "function") {
        document.startViewTransition(change);
      } else {
        change();
      }
    });

    reflectState();
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
    initThemeToggle();
    initTableSearch();
    initExportCsv();
  });
})();

