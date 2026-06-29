// Shared brand palette so every chart across the app reads as one product.
// Indigo-forward, with violet + cool/warm accents that complement (no clashing rainbow).
export const BRAND_CHART_COLORS = [
  "#4f46e5", // indigo-600 (primary)
  "#7c3aed", // violet-600 (secondary)
  "#818cf8", // indigo-400
  "#a78bfa", // violet-400
  "#0ea5e9", // sky-500 (cool accent)
  "#f59e0b", // amber-500 (warm accent)
  "#64748b", // slate-500 (neutral)
];

// Indigo -> violet gradient used by every dashboard AppBar (matches EmployeeDashboard).
export const APPBAR_GRADIENT =
  "linear-gradient(90deg, #4338ca 0%, #4f46e5 45%, #7c3aed 100%)";

export const APPBAR_SHADOW = "0 4px 24px rgba(79, 70, 229, 0.28)";

// Chart.js-friendly: a single brand color for a dataset's points/line.
export const BRAND_PRIMARY = "#4f46e5";
export const BRAND_PRIMARY_SOFT = "rgba(79, 70, 229, 0.12)";
export const BRAND_SECONDARY = "#7c3aed";
