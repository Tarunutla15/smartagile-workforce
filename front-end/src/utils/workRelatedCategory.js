/**
 * Work-related bucket: category is exactly the keyword "work" or "work-related"
 * (hyphenated), any letter casing. All other category strings count as "other".
 */
export function isWorkRelatedCategory(category) {
  const c = String(category ?? "").trim();
  if (!c) return false;
  const lower = c.toLowerCase();
  return lower === "work" || lower === "work-related";
}
