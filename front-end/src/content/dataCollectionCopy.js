/**
 * Plain-language data inventory aligned with the desktop agent (desktop-agent/continous_task.py)
 * and web APIs. Keep marketing and in-app copy consistent with this file.
 */

export const DISCLOSURE_VERSION = "v1";

export const TRACKING_SOURCE_PARAGRAPH =
  "Usage and attendance numbers come from the SmartAgile desktop agent on your work PC when it is installed and running. The web app displays data your organization’s server stores; logging in to the website alone does not capture desktop activity.";

export const COLLECTED_ITEMS = [
  {
    title: "Foreground application",
    body: "Which program is in the active (focused) window, resolved to an application name (e.g. from the process).",
  },
  {
    title: "Window / page title",
    body: "The OS window title while that app is in focus. For most desktop apps, time is rolled up per application; for browsers, titles help separate sites or tabs into different rows.",
  },
  {
    title: "Time in focus (duration)",
    body: "How long each app or browser context was the foreground window, in seconds, aggregated over the day.",
  },
  {
    title: "Idle time",
    body: "Time treated as idle during those segments, based on how long the OS reports no keyboard or mouse activity (not what you typed).",
  },
  {
    title: "Key press, click, and scroll counts",
    body: "Totals of key presses, mouse clicks, and scroll events during each segment. These are counts only—there is no recording of which keys were pressed or typed text.",
  },
  {
    title: "Attendance-style totals",
    body: "Login time for the agent session, accumulated duration for the day, and related fields used to show attendance in the app.",
  },
  {
    title: "App open counts",
    body: "How often applications were brought to the foreground (open/focus events), aggregated per day.",
  },
  {
    title: "Derived category labels",
    body: "Machine-assigned categories for apps or sites (for dashboards).",
  },
];

export const NOT_COLLECTED_ITEMS = [
  "Keystroke logging or keylogger-style capture (no typed content, passwords, or message text).",
  "Screenshots, screen video, or continuous screen capture.",
  "Audio or camera recording.",
  "Clipboard contents.",
];

export const WHO_CAN_SEE_EMPLOYEE =
  "You can see your own tasks, attendance, apps/sites usage, and related dashboard views when you sign in. Other employees do not see your personal usage rows through the default employee views.";

export const WHO_CAN_SEE_ADMIN =
  "Organization admins and anyone with admin tools your deployment enables can see employee-level usage and attendance that the server stores (for example, per-person app and browser breakdowns where the product exposes them). Exact screens depend on your SmartAgile configuration.";

export const RETENTION_PARAGRAPH =
  "Automated retention or deletion policies are not built into this product version yet. Data remains available on your organization’s database and infrastructure until it is removed by an operator or your organization’s processes. Ask your admin how long data is kept in practice.";

export const ABOUT_PRIVACY_REPLACEMENT = {
  title: "Privacy and workplace data",
  items: [
    "Collects activity metrics tied to your account (app names, window titles for context, durations, idle time, and input event counts)—not “anonymous-only” summaries.",
    "Does not record keystroke content, screenshots, or screen capture; only counts of keys, clicks, and scrolls during a time segment.",
    "Read the full data inventory before the desktop agent runs: use the link on login or open “Data we collect” in Settings.",
  ],
};
