/* @ds-bundle: {"format":3,"namespace":"VerasigDesignSystem_fd565b","components":[{"name":"Avatar","sourcePath":"components/core/Avatar.jsx"},{"name":"Badge","sourcePath":"components/core/Badge.jsx"},{"name":"Button","sourcePath":"components/core/Button.jsx"},{"name":"IconButton","sourcePath":"components/core/IconButton.jsx"},{"name":"Tabs","sourcePath":"components/core/Tabs.jsx"},{"name":"Tag","sourcePath":"components/core/Tag.jsx"},{"name":"Card","sourcePath":"components/data/Card.jsx"},{"name":"ConfidenceBar","sourcePath":"components/data/ConfidenceBar.jsx"},{"name":"MetricStat","sourcePath":"components/data/MetricStat.jsx"},{"name":"SignalRow","sourcePath":"components/data/SignalRow.jsx"},{"name":"StatusPill","sourcePath":"components/data/StatusPill.jsx"},{"name":"Banner","sourcePath":"components/feedback/Banner.jsx"},{"name":"Dialog","sourcePath":"components/feedback/Dialog.jsx"},{"name":"Toast","sourcePath":"components/feedback/Toast.jsx"},{"name":"ToastStack","sourcePath":"components/feedback/Toast.jsx"},{"name":"Tooltip","sourcePath":"components/feedback/Tooltip.jsx"},{"name":"Checkbox","sourcePath":"components/forms/Checkbox.jsx"},{"name":"Input","sourcePath":"components/forms/Input.jsx"},{"name":"Select","sourcePath":"components/forms/Select.jsx"},{"name":"Switch","sourcePath":"components/forms/Switch.jsx"}],"sourceHashes":{"components/core/Avatar.jsx":"1e94cda1ab1d","components/core/Badge.jsx":"c83e0a5fa5c8","components/core/Button.jsx":"d86c770f3edd","components/core/IconButton.jsx":"1a80a3c7192d","components/core/Tabs.jsx":"0cc36bb8939e","components/core/Tag.jsx":"391e3370b176","components/data/Card.jsx":"b83fe3decf50","components/data/ConfidenceBar.jsx":"d293f2192168","components/data/MetricStat.jsx":"003ec96ad175","components/data/SignalRow.jsx":"73c4dff8ebee","components/data/StatusPill.jsx":"0753a41f3055","components/feedback/Banner.jsx":"85659b50a3a9","components/feedback/Dialog.jsx":"af30be3e39f3","components/feedback/Toast.jsx":"96162a41c6c1","components/feedback/Tooltip.jsx":"8db8e528a5d0","components/forms/Checkbox.jsx":"7e1e04f25b90","components/forms/Input.jsx":"164eb0fac8ff","components/forms/Select.jsx":"77e5b00d21ac","components/forms/Switch.jsx":"21fae340c1c9","ui_kits/app/App.jsx":"ace8da29d547","ui_kits/app/OverviewView.jsx":"030e0e2c5c5a","ui_kits/app/ProvidersView.jsx":"990623064518","ui_kits/app/Sidebar.jsx":"616a3bfc3334","ui_kits/app/SignalDrawer.jsx":"5212baf217d0","ui_kits/app/SignalsView.jsx":"35d9fa731583","ui_kits/app/Topbar.jsx":"3d44b96e7778","ui_kits/app/app.data.jsx":"4dfffbe411d8","ui_kits/marketing/Hero.jsx":"e315f91c0222","ui_kits/marketing/Nav.jsx":"1102de05f5a8","ui_kits/marketing/Products.jsx":"9787ac588fd4","ui_kits/marketing/Site.jsx":"b2af42b5d663","ui_kits/marketing/Why.jsx":"4840f6fa6a25","ui_kits/marketing/site.data.jsx":"f49b0a47d30f"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.VerasigDesignSystem_fd565b = window.VerasigDesignSystem_fd565b || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// components/core/Avatar.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.vrs-avatar {
  --_s: 36px;
  display: inline-flex; align-items: center; justify-content: center;
  width: var(--_s); height: var(--_s); flex: none; position: relative;
  border-radius: var(--radius-pill); overflow: hidden;
  font-family: var(--font-mono); font-size: calc(var(--_s) * 0.36); font-weight: var(--fw-medium);
  color: var(--text-on-accent); background: var(--accent);
  letter-spacing: 0; text-transform: uppercase; user-select: none;
}
.vrs-avatar img { width: 100%; height: 100%; object-fit: cover; }
.vrs-avatar__sz-xs { --_s: 24px; }
.vrs-avatar__sz-sm { --_s: 30px; }
.vrs-avatar__sz-lg { --_s: 48px; }
.vrs-avatar__square { border-radius: var(--radius-md); }
.vrs-avatar__status {
  position: absolute; right: -1px; bottom: -1px;
  width: 30%; height: 30%; min-width: 8px; min-height: 8px;
  border-radius: 50%; border: 2px solid var(--surface-card);
}
`;
if (typeof document !== 'undefined' && !document.getElementById('vrs-avatar-css')) {
  const s = document.createElement('style');
  s.id = 'vrs-avatar-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}
const TONE = {
  verified: 'var(--verified-500)',
  pending: 'var(--pending-500)',
  rejected: 'var(--rejected-500)',
  offline: 'var(--ink-500)'
};

/** Avatar — image, or initials fallback on a tinted chip. */
function Avatar({
  src,
  name = '',
  size = 'md',
  square = false,
  status,
  tint,
  className = '',
  ...rest
}) {
  const initials = name.split(/\s+/).filter(Boolean).slice(0, 2).map(w => w[0]).join('');
  const cls = ['vrs-avatar', size !== 'md' ? `vrs-avatar__sz-${size}` : '', square ? 'vrs-avatar__square' : '', className].filter(Boolean).join(' ');
  return /*#__PURE__*/React.createElement("span", _extends({
    className: cls,
    style: tint ? {
      background: tint
    } : undefined
  }, rest), src ? /*#__PURE__*/React.createElement("img", {
    src: src,
    alt: name
  }) : /*#__PURE__*/React.createElement("span", null, initials || '—'), status && /*#__PURE__*/React.createElement("span", {
    className: "vrs-avatar__status",
    style: {
      background: TONE[status] || status
    }
  }));
}
Object.assign(__ds_scope, { Avatar });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Avatar.jsx", error: String((e && e.message) || e) }); }

// components/core/Badge.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.vrs-badge {
  display: inline-flex; align-items: center; gap: 5px;
  height: 22px; padding: 0 9px;
  font-family: var(--font-mono); font-size: var(--text-3xs); font-weight: var(--fw-medium);
  letter-spacing: 0.06em; text-transform: uppercase; line-height: 1;
  border-radius: var(--radius-pill); white-space: nowrap;
  border: 1px solid transparent;
}
.vrs-badge__dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; flex: none; }
.vrs-badge__neutral  { background: var(--surface-hover); color: var(--text-muted); }
.vrs-badge__verified { background: var(--verified-bg); color: var(--verified-500); }
.vrs-badge__pending  { background: var(--pending-bg);  color: var(--pending-500); }
.vrs-badge__rejected { background: var(--rejected-bg); color: var(--rejected-500); }
.vrs-badge__info     { background: var(--info-bg);     color: var(--info-500); }
.vrs-badge__outline  { background: transparent; border-color: var(--border-strong); color: var(--text-body); }
.vrs-badge__solid    { background: var(--accent); color: var(--text-on-accent); }
`;
if (typeof document !== 'undefined' && !document.getElementById('vrs-badge-css')) {
  const s = document.createElement('style');
  s.id = 'vrs-badge-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

/** Status badge — small, mono, uppercase. */
function Badge({
  tone = 'neutral',
  dot = false,
  className = '',
  children,
  ...rest
}) {
  const cls = ['vrs-badge', `vrs-badge__${tone}`, className].filter(Boolean).join(' ');
  return /*#__PURE__*/React.createElement("span", _extends({
    className: cls
  }, rest), dot && /*#__PURE__*/React.createElement("span", {
    className: "vrs-badge__dot",
    "aria-hidden": "true"
  }), children);
}
Object.assign(__ds_scope, { Badge });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Badge.jsx", error: String((e && e.message) || e) }); }

// components/core/Button.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/* Inject component styles once (self-contained, token-driven). */
const CSS = `
.vrs-btn {
  --_h: 38px; --_px: 15px; --_fs: var(--text-sm);
  position: relative; isolation: isolate;
  display: inline-flex; align-items: center; justify-content: center;
  gap: 8px; height: var(--_h); padding: 0 var(--_px);
  font-family: var(--font-sans); font-size: var(--_fs); font-weight: var(--fw-medium);
  letter-spacing: 0.005em; line-height: 1; white-space: nowrap;
  border-radius: 7px; border: 1px solid transparent;
  cursor: pointer; user-select: none; text-decoration: none;
  transition: background-color var(--dur-fast) var(--ease-out),
              background-image var(--dur-fast) var(--ease-out),
              border-color var(--dur-fast) var(--ease-out),
              color var(--dur-fast) var(--ease-out),
              transform var(--dur-instant) var(--ease-out),
              box-shadow var(--dur-fast) var(--ease-out);
}
.vrs-btn:focus-visible { outline: none; box-shadow: 0 0 0 2px color-mix(in srgb, var(--accent) 60%, transparent), 0 0 18px var(--signal-glow); }
.vrs-btn:disabled:not(.vrs-btn__loading) { opacity: 0.4; cursor: not-allowed; }
.vrs-btn__loading { cursor: progress; }
.vrs-btn__sz-sm { --_h: 30px; --_px: 12px; --_fs: var(--text-xs); }
.vrs-btn__sz-lg { --_h: 46px; --_px: 22px; --_fs: var(--text-md); border-radius: 9px; }

/* icons sit slightly inset & optically aligned */
.vrs-btn svg { width: 1.15em; height: 1.15em; flex: none; }

/* ---- Primary: a machined signal key ---- */
/* No border: the bevel is drawn with inset shadows, which clip to the padding
   box. A 1px transparent border would leave a ring of un-shaded fill OUTSIDE
   the bevel (a pale halo around the edge). Padding compensates so geometry
   matches the bordered variants exactly. */
.vrs-btn__primary {
  border: none; padding: 0 calc(var(--_px) + 1px);
  color: var(--text-on-accent);
  background-color: var(--accent);
  background-image: linear-gradient(180deg, color-mix(in srgb, var(--accent) 87%, #fff), var(--accent));
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.45), inset 0 -1px 0 rgba(0,0,0,0.10), 0 1px 1.5px rgba(0,0,0,0.4);
}
.vrs-btn__primary:hover:not(:disabled) {
  background-image: linear-gradient(180deg, color-mix(in srgb, var(--accent) 76%, #fff), color-mix(in srgb, var(--accent) 99%, #fff));
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.55), 0 0 16px var(--signal-glow), 0 5px 14px -4px var(--signal-glow);
}
.vrs-btn__primary:active:not(:disabled) {
  background-image: none; background-color: var(--accent-press);
  transform: translateY(1px);
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.12);
}

/* ---- Secondary: brushed instrument surface ---- */
.vrs-btn__secondary {
  color: var(--text-strong); border-color: var(--border-strong);
  background-color: var(--surface-raised);
  background-image: linear-gradient(180deg, color-mix(in srgb, var(--surface-raised) 90%, #fff), color-mix(in srgb, var(--surface-raised) 94%, #000));
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.07), 0 1px 1.5px rgba(0,0,0,0.3);
}
.vrs-btn__secondary:hover:not(:disabled) {
  border-color: color-mix(in srgb, var(--accent) 48%, var(--border-strong));
  background-image: linear-gradient(180deg, color-mix(in srgb, var(--surface-hover) 90%, #fff), var(--surface-hover));
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.09), 0 0 12px -2px var(--signal-glow), 0 2px 8px -4px rgba(0,0,0,0.5);
}
.vrs-btn__secondary:active:not(:disabled) { transform: translateY(1px); background-image: none; background-color: var(--surface-card); box-shadow: inset 0 2px 4px rgba(0,0,0,0.3); }

/* ---- Ghost: quiet until touched ---- */
.vrs-btn__ghost { background: transparent; color: var(--text-body); }
.vrs-btn__ghost:hover:not(:disabled) { background: var(--surface-hover); color: var(--text-strong); }
.vrs-btn__ghost:active:not(:disabled) { transform: translateY(1px); background: var(--surface-card); }

/* ---- Danger: armed ---- */
.vrs-btn__danger {
  color: var(--rejected-500); background: transparent;
  border-color: color-mix(in srgb, var(--rejected-500) 38%, transparent);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
}
.vrs-btn__danger:hover:not(:disabled) { background: var(--rejected-bg); border-color: color-mix(in srgb, var(--rejected-500) 62%, transparent); box-shadow: 0 0 14px -2px color-mix(in srgb, var(--rejected-500) 40%, transparent); }
.vrs-btn__danger:active:not(:disabled) { transform: translateY(1px); background: color-mix(in srgb, var(--rejected-500) 18%, transparent); }

.vrs-btn__full { width: 100%; }
.vrs-btn__spin { width: 1em; height: 1em; border-radius: 50%;
  border: 2px solid currentColor; border-top-color: transparent;
  animation: vrs-btn-spin 0.6s linear infinite; }
@keyframes vrs-btn-spin { to { transform: rotate(360deg); } }
`;
if (typeof document !== 'undefined' && !document.getElementById('vrs-button-css')) {
  const s = document.createElement('style');
  s.id = 'vrs-button-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

/**
 * Verasig primary button.
 */
function Button({
  variant = 'primary',
  size = 'md',
  iconLeft = null,
  iconRight = null,
  loading = false,
  fullWidth = false,
  disabled = false,
  as = 'button',
  className = '',
  children,
  ...rest
}) {
  const Tag = as;
  const cls = ['vrs-btn', `vrs-btn__${variant}`, size !== 'md' ? `vrs-btn__sz-${size}` : '', fullWidth ? 'vrs-btn__full' : '', loading ? 'vrs-btn__loading' : '', className].filter(Boolean).join(' ');
  return /*#__PURE__*/React.createElement(Tag, _extends({
    className: cls,
    disabled: Tag === 'button' ? disabled || loading : undefined
  }, rest), loading && /*#__PURE__*/React.createElement("span", {
    className: "vrs-btn__spin",
    "aria-hidden": "true"
  }), !loading && iconLeft, children, !loading && iconRight);
}
Object.assign(__ds_scope, { Button });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Button.jsx", error: String((e && e.message) || e) }); }

// components/core/IconButton.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.vrs-iconbtn {
  --_s: 38px;
  display: inline-flex; align-items: center; justify-content: center;
  width: var(--_s); height: var(--_s); padding: 0; flex: none;
  border-radius: 7px; border: 1px solid transparent;
  background: transparent; color: var(--text-muted); cursor: pointer;
  transition: background var(--dur-fast) var(--ease-out),
              background-image var(--dur-fast) var(--ease-out),
              color var(--dur-fast) var(--ease-out),
              border-color var(--dur-fast) var(--ease-out),
              transform var(--dur-instant) var(--ease-out),
              box-shadow var(--dur-fast) var(--ease-out);
}
.vrs-iconbtn svg { width: 18px; height: 18px; display: block; }
.vrs-iconbtn:hover:not(:disabled) { background: var(--surface-hover); color: var(--text-strong); }
.vrs-iconbtn:active:not(:disabled) { transform: translateY(1px); background: var(--surface-card); box-shadow: inset 0 2px 4px rgba(0,0,0,0.25); }
.vrs-iconbtn:focus-visible { outline: none; box-shadow: 0 0 0 2px color-mix(in srgb, var(--accent) 60%, transparent), 0 0 18px var(--signal-glow); }
.vrs-iconbtn:disabled { opacity: 0.4; cursor: not-allowed; }
.vrs-iconbtn__sz-sm { --_s: 30px; }
.vrs-iconbtn__sz-sm svg { width: 15px; height: 15px; }
.vrs-iconbtn__sz-lg { --_s: 46px; }
.vrs-iconbtn__sz-lg svg { width: 20px; height: 20px; }
.vrs-iconbtn__solid {
  color: var(--text-body); border-color: var(--border-strong);
  background-color: var(--surface-raised);
  background-image: linear-gradient(180deg, color-mix(in srgb, var(--surface-raised) 90%, #fff), color-mix(in srgb, var(--surface-raised) 94%, #000));
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.07), 0 1px 1.5px rgba(0,0,0,0.3);
}
.vrs-iconbtn__solid:hover:not(:disabled) { color: var(--text-strong); border-color: color-mix(in srgb, var(--accent) 48%, var(--border-strong)); background-image: linear-gradient(180deg, color-mix(in srgb, var(--surface-hover) 90%, #fff), var(--surface-hover)); }
.vrs-iconbtn__solid:active:not(:disabled) { transform: translateY(1px); background-image: none; background-color: var(--surface-card); box-shadow: inset 0 2px 4px rgba(0,0,0,0.3); }
.vrs-iconbtn__accent { background: var(--accent-quiet); color: var(--accent-text); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--accent) 22%, transparent); }
.vrs-iconbtn__accent:hover:not(:disabled) { color: var(--accent); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--accent) 22%, transparent), 0 0 14px var(--signal-glow); }
.vrs-iconbtn__accent:active:not(:disabled) { transform: translateY(1px); }
`;
if (typeof document !== 'undefined' && !document.getElementById('vrs-iconbtn-css')) {
  const s = document.createElement('style');
  s.id = 'vrs-iconbtn-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

/** Square icon-only button. */
function IconButton({
  variant = 'ghost',
  size = 'md',
  label,
  className = '',
  children,
  ...rest
}) {
  const cls = ['vrs-iconbtn', variant !== 'ghost' ? `vrs-iconbtn__${variant}` : '', size !== 'md' ? `vrs-iconbtn__sz-${size}` : '', className].filter(Boolean).join(' ');
  return /*#__PURE__*/React.createElement("button", _extends({
    className: cls,
    "aria-label": label,
    title: label
  }, rest), children);
}
Object.assign(__ds_scope, { IconButton });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/IconButton.jsx", error: String((e && e.message) || e) }); }

// components/core/Tabs.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.vrs-tabs { display: flex; align-items: center; gap: 2px; position: relative; }
.vrs-tabs__line { border-bottom: 1px solid var(--border-default); }
.vrs-tab {
  appearance: none; background: transparent; border: 0; cursor: pointer;
  font-family: var(--font-sans); font-size: var(--text-sm); font-weight: var(--fw-medium);
  color: var(--text-muted); padding: 9px 13px; position: relative;
  display: inline-flex; align-items: center; gap: 7px;
  transition: color var(--dur-fast) var(--ease-out);
}
.vrs-tab:hover { color: var(--text-strong); }
.vrs-tab[aria-selected="true"] { color: var(--text-strong); }
.vrs-tabs__line .vrs-tab { padding-bottom: 11px; }
.vrs-tabs__line .vrs-tab::after {
  content: ''; position: absolute; left: 10px; right: 10px; bottom: -1px; height: 2px;
  background: var(--accent); border-radius: 2px 2px 0 0;
  transform: scaleX(0); transform-origin: center;
  transition: transform var(--dur-base) var(--ease-out);
}
.vrs-tabs__line .vrs-tab[aria-selected="true"]::after { transform: scaleX(1); }
.vrs-tabs__pill { background: var(--surface-sunken); padding: 4px; border-radius: var(--radius-md); gap: 2px; }
.vrs-tabs__pill .vrs-tab { padding: 6px 13px; border-radius: var(--radius-sm); }
.vrs-tabs__pill .vrs-tab[aria-selected="true"] { background: var(--surface-raised); box-shadow: var(--shadow-xs); }
.vrs-tab__count {
  font-family: var(--font-mono); font-size: var(--text-3xs); color: var(--text-faint);
  background: var(--surface-hover); border-radius: var(--radius-pill); padding: 1px 6px;
}
.vrs-tab[aria-selected="true"] .vrs-tab__count { color: var(--accent-text); }
`;
if (typeof document !== 'undefined' && !document.getElementById('vrs-tabs-css')) {
  const s = document.createElement('style');
  s.id = 'vrs-tabs-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

/** Tab bar — underline or pill style. Controlled via `value`/`onChange`. */
function Tabs({
  items = [],
  value,
  onChange,
  variant = 'line',
  className = '',
  ...rest
}) {
  const cls = ['vrs-tabs', variant === 'line' ? 'vrs-tabs__line' : 'vrs-tabs__pill', className].filter(Boolean).join(' ');
  return /*#__PURE__*/React.createElement("div", _extends({
    className: cls,
    role: "tablist"
  }, rest), items.map(it => {
    const id = typeof it === 'string' ? it : it.id;
    const label = typeof it === 'string' ? it : it.label;
    const count = typeof it === 'string' ? undefined : it.count;
    return /*#__PURE__*/React.createElement("button", {
      key: id,
      role: "tab",
      "aria-selected": value === id,
      className: "vrs-tab",
      onClick: () => onChange && onChange(id)
    }, label, count != null && /*#__PURE__*/React.createElement("span", {
      className: "vrs-tab__count"
    }, count));
  }));
}
Object.assign(__ds_scope, { Tabs });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Tabs.jsx", error: String((e && e.message) || e) }); }

// components/core/Tag.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.vrs-tag {
  display: inline-flex; align-items: center; gap: 6px;
  height: 26px; padding: 0 10px;
  font-family: var(--font-sans); font-size: var(--text-xs); font-weight: var(--fw-medium);
  color: var(--text-body); background: var(--surface-raised);
  border: 1px solid var(--border-default); border-radius: var(--radius-sm);
  line-height: 1; white-space: nowrap;
  transition: border-color var(--dur-fast) var(--ease-out), background var(--dur-fast) var(--ease-out);
}
.vrs-tag__sw { width: 8px; height: 8px; border-radius: 2px; flex: none; }
.vrs-tag__rm {
  display: inline-flex; align-items: center; justify-content: center;
  width: 15px; height: 15px; margin-right: -3px; border-radius: 3px;
  border: 0; background: transparent; color: var(--text-faint); cursor: pointer;
  font-size: 13px; line-height: 1;
}
.vrs-tag__rm:hover { background: var(--surface-hover); color: var(--text-strong); }
.vrs-tag__clickable { cursor: pointer; }
.vrs-tag__clickable:hover { border-color: var(--border-strong); background: var(--surface-hover); }
`;
if (typeof document !== 'undefined' && !document.getElementById('vrs-tag-css')) {
  const s = document.createElement('style');
  s.id = 'vrs-tag-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

/** Interactive tag / chip for filters, channels and providers. */
function Tag({
  swatch,
  onRemove,
  onClick,
  className = '',
  children,
  ...rest
}) {
  const cls = ['vrs-tag', onClick ? 'vrs-tag__clickable' : '', className].filter(Boolean).join(' ');
  return /*#__PURE__*/React.createElement("span", _extends({
    className: cls,
    onClick: onClick
  }, rest), swatch && /*#__PURE__*/React.createElement("span", {
    className: "vrs-tag__sw",
    style: {
      background: swatch
    },
    "aria-hidden": "true"
  }), children, onRemove && /*#__PURE__*/React.createElement("button", {
    className: "vrs-tag__rm",
    "aria-label": "Remove",
    onClick: e => {
      e.stopPropagation();
      onRemove(e);
    }
  }, "\xD7"));
}
Object.assign(__ds_scope, { Tag });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Tag.jsx", error: String((e && e.message) || e) }); }

// components/data/Card.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.vrs-card {
  background: var(--surface-card); border: 1px solid var(--border-default);
  border-radius: var(--radius-lg); overflow: hidden;
  transition: border-color var(--dur-fast) var(--ease-out), box-shadow var(--dur-fast) var(--ease-out);
}
.vrs-card__pad { padding: var(--space-5); }
.vrs-card__interactive { cursor: pointer; }
.vrs-card__interactive:hover { border-color: var(--border-strong); box-shadow: var(--shadow-md); }
.vrs-card__glow { border-color: transparent; box-shadow: var(--glow-signal); }
.vrs-card__head { display: flex; align-items: center; gap: 12px; padding: 14px var(--space-5); border-bottom: 1px solid var(--border-subtle); }
.vrs-card__title { font-family: var(--font-display); font-size: var(--text-md); font-weight: var(--fw-semibold); color: var(--text-strong); }
.vrs-card__sub { font-family: var(--font-sans); font-size: var(--text-2xs); color: var(--text-muted); margin-top: 1px; }
.vrs-card__head-actions { margin-left: auto; display: flex; align-items: center; gap: 8px; }
.vrs-card__foot { padding: 12px var(--space-5); border-top: 1px solid var(--border-subtle); display: flex; align-items: center; gap: 10px; }
`;
if (typeof document !== 'undefined' && !document.getElementById('vrs-card-css')) {
  const s = document.createElement('style');
  s.id = 'vrs-card-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

/** Surface container with optional header / footer. */
function Card({
  title,
  subtitle,
  headerActions,
  footer,
  padded = true,
  interactive = false,
  glow = false,
  className = '',
  children,
  ...rest
}) {
  const cls = ['vrs-card', interactive ? 'vrs-card__interactive' : '', glow ? 'vrs-card__glow' : '', className].filter(Boolean).join(' ');
  const hasHead = title || subtitle || headerActions;
  return /*#__PURE__*/React.createElement("div", _extends({
    className: cls
  }, rest), hasHead && /*#__PURE__*/React.createElement("div", {
    className: "vrs-card__head"
  }, /*#__PURE__*/React.createElement("div", null, title && /*#__PURE__*/React.createElement("div", {
    className: "vrs-card__title"
  }, title), subtitle && /*#__PURE__*/React.createElement("div", {
    className: "vrs-card__sub"
  }, subtitle)), headerActions && /*#__PURE__*/React.createElement("div", {
    className: "vrs-card__head-actions"
  }, headerActions)), /*#__PURE__*/React.createElement("div", {
    className: padded && !hasHead ? 'vrs-card__pad' : padded ? 'vrs-card__pad' : ''
  }, children), footer && /*#__PURE__*/React.createElement("div", {
    className: "vrs-card__foot"
  }, footer));
}
Object.assign(__ds_scope, { Card });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data/Card.jsx", error: String((e && e.message) || e) }); }

// components/data/ConfidenceBar.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.vrs-conf { display: flex; flex-direction: column; gap: 6px; width: 100%; }
.vrs-conf__top { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
.vrs-conf__label { font-family: var(--font-sans); font-size: var(--text-2xs); color: var(--text-muted); }
.vrs-conf__val { font-family: var(--font-mono); font-feature-settings: "tnum" 1; font-size: var(--text-xs); font-weight: var(--fw-medium); color: var(--text-strong); }
.vrs-conf__track { position: relative; height: 6px; border-radius: var(--radius-pill); background: var(--surface-hover); overflow: hidden; }
.vrs-conf__fill { position: absolute; inset: 0 auto 0 0; border-radius: var(--radius-pill); transition: width var(--dur-slow) var(--ease-out); }
.vrs-conf__threshold { position: absolute; top: -2px; bottom: -2px; width: 2px; background: var(--text-faint); border-radius: 2px; }
.vrs-conf__seg { display: flex; gap: 3px; }
.vrs-conf__tick { flex: 1; height: 6px; border-radius: 2px; background: var(--surface-hover); }
`;
if (typeof document !== 'undefined' && !document.getElementById('vrs-conf-css')) {
  const s = document.createElement('style');
  s.id = 'vrs-conf-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}
function colorFor(value, threshold) {
  if (value < threshold) return 'var(--rejected-500)';
  if (value < threshold + 8) return 'var(--pending-500)';
  return 'var(--verified-500)';
}

/** Confidence meter — a bar (or segmented) showing a 0–100 score vs a quorum threshold. */
function ConfidenceBar({
  value = 0,
  threshold = 80,
  label = 'Confidence',
  showValue = true,
  segments = 0,
  className = '',
  ...rest
}) {
  const v = Math.max(0, Math.min(100, value));
  const color = colorFor(v, threshold);
  return /*#__PURE__*/React.createElement("div", _extends({
    className: ['vrs-conf', className].filter(Boolean).join(' ')
  }, rest), (label || showValue) && /*#__PURE__*/React.createElement("div", {
    className: "vrs-conf__top"
  }, label && /*#__PURE__*/React.createElement("span", {
    className: "vrs-conf__label"
  }, label), showValue && /*#__PURE__*/React.createElement("span", {
    className: "vrs-conf__val"
  }, v.toFixed(1), "%")), segments > 0 ? /*#__PURE__*/React.createElement("div", {
    className: "vrs-conf__seg"
  }, Array.from({
    length: segments
  }).map((_, i) => /*#__PURE__*/React.createElement("span", {
    key: i,
    className: "vrs-conf__tick",
    style: {
      background: i < Math.round(v / 100 * segments) ? color : undefined
    }
  }))) : /*#__PURE__*/React.createElement("div", {
    className: "vrs-conf__track"
  }, /*#__PURE__*/React.createElement("span", {
    className: "vrs-conf__fill",
    style: {
      width: `${v}%`,
      background: color
    }
  }), threshold > 0 && threshold < 100 && /*#__PURE__*/React.createElement("span", {
    className: "vrs-conf__threshold",
    style: {
      left: `${threshold}%`
    },
    title: `Quorum threshold ${threshold}%`
  })));
}
Object.assign(__ds_scope, { ConfidenceBar });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data/ConfidenceBar.jsx", error: String((e && e.message) || e) }); }

// components/data/MetricStat.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.vrs-stat { display: flex; flex-direction: column; gap: 6px; }
.vrs-stat__label { font-family: var(--font-mono); font-size: var(--text-3xs); letter-spacing: 0.1em; text-transform: uppercase; color: var(--text-muted); }
.vrs-stat__value { font-family: var(--font-mono); font-feature-settings: "tnum" 1; font-size: var(--text-3xl); font-weight: var(--fw-medium); color: var(--text-strong); line-height: 1; letter-spacing: -0.01em; display: flex; align-items: baseline; gap: 4px; }
.vrs-stat__unit { font-size: var(--text-lg); color: var(--text-muted); font-weight: var(--fw-regular); }
.vrs-stat__row { display: flex; align-items: center; gap: 10px; }
.vrs-stat__delta { display: inline-flex; align-items: center; gap: 3px; font-family: var(--font-mono); font-size: var(--text-2xs); font-weight: var(--fw-medium); }
.vrs-stat__delta.up { color: var(--verified-500); }
.vrs-stat__delta.down { color: var(--rejected-500); }
.vrs-stat__delta.flat { color: var(--text-muted); }
.vrs-stat__caption { font-family: var(--font-sans); font-size: var(--text-2xs); color: var(--text-faint); }
.vrs-stat__sm .vrs-stat__value { font-size: var(--text-xl); }
`;
if (typeof document !== 'undefined' && !document.getElementById('vrs-stat-css')) {
  const s = document.createElement('style');
  s.id = 'vrs-stat-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}
const ARROW = {
  up: /*#__PURE__*/React.createElement("path", {
    d: "M7 17 17 7M17 7H9M17 7v8"
  }),
  down: /*#__PURE__*/React.createElement("path", {
    d: "M7 7l10 10M17 17H9M17 17V9"
  }),
  flat: /*#__PURE__*/React.createElement("path", {
    d: "M5 12h14"
  })
};

/** Big metric value with label, unit, delta and caption. */
function MetricStat({
  label,
  value,
  unit,
  delta,
  trend = 'flat',
  caption,
  size = 'md',
  className = '',
  ...rest
}) {
  const cls = ['vrs-stat', size === 'sm' ? 'vrs-stat__sm' : '', className].filter(Boolean).join(' ');
  return /*#__PURE__*/React.createElement("div", _extends({
    className: cls
  }, rest), label && /*#__PURE__*/React.createElement("div", {
    className: "vrs-stat__label"
  }, label), /*#__PURE__*/React.createElement("div", {
    className: "vrs-stat__row"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vrs-stat__value"
  }, value, unit && /*#__PURE__*/React.createElement("span", {
    className: "vrs-stat__unit"
  }, unit)), delta != null && /*#__PURE__*/React.createElement("span", {
    className: `vrs-stat__delta ${trend}`
  }, /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 24 24",
    width: "13",
    height: "13",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: "2.2",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }, ARROW[trend]), delta)), caption && /*#__PURE__*/React.createElement("div", {
    className: "vrs-stat__caption"
  }, caption));
}
Object.assign(__ds_scope, { MetricStat });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data/MetricStat.jsx", error: String((e && e.message) || e) }); }

// components/data/StatusPill.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.vrs-status {
  display: inline-flex; align-items: center; gap: 7px;
  height: 26px; padding: 0 11px 0 9px;
  border-radius: var(--radius-pill); border: 1px solid transparent;
  font-family: var(--font-sans); font-size: var(--text-xs); font-weight: var(--fw-medium); line-height: 1;
}
.vrs-status__ic { display: inline-flex; }
.vrs-status__ic svg { width: 14px; height: 14px; display: block; }
.vrs-status__verified { background: var(--verified-bg); color: var(--verified-500); border-color: color-mix(in srgb, var(--verified-500) 28%, transparent); }
.vrs-status__pending  { background: var(--pending-bg);  color: var(--pending-500);  border-color: color-mix(in srgb, var(--pending-500) 28%, transparent); }
.vrs-status__rejected { background: var(--rejected-bg); color: var(--rejected-500); border-color: color-mix(in srgb, var(--rejected-500) 28%, transparent); }
.vrs-status__observing{ background: var(--info-bg);     color: var(--info-500);     border-color: color-mix(in srgb, var(--info-500) 28%, transparent); }
.vrs-status__pulse { position: relative; }
.vrs-status__pulse .vrs-status__ic::after {
  content: ''; position: absolute; left: 9px; top: 50%; width: 14px; height: 14px;
  transform: translateY(-50%); border-radius: 50%;
  box-shadow: 0 0 0 0 currentColor; opacity: 0.5;
  animation: vrs-status-pulse 1.8s var(--ease-out) infinite;
}
@keyframes vrs-status-pulse { 70%,100% { box-shadow: 0 0 0 7px transparent; opacity: 0; } }
`;
if (typeof document !== 'undefined' && !document.getElementById('vrs-status-css')) {
  const s = document.createElement('style');
  s.id = 'vrs-status-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}
const GLYPH = {
  verified: /*#__PURE__*/React.createElement("path", {
    d: "M20 6 9 17l-5-5"
  }),
  pending: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("circle", {
    cx: "12",
    cy: "12",
    r: "9"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M12 7v5l3 2"
  })),
  rejected: /*#__PURE__*/React.createElement("path", {
    d: "M18 6 6 18M6 6l12 12"
  }),
  observing: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("circle", {
    cx: "12",
    cy: "12",
    r: "3"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z"
  }))
};
const LABELS = {
  verified: 'Verified',
  pending: 'Pending',
  rejected: 'Rejected',
  observing: 'Observing'
};

/** Verification status pill with icon. */
function StatusPill({
  status = 'pending',
  label,
  pulse = false,
  className = '',
  ...rest
}) {
  const cls = ['vrs-status', `vrs-status__${status}`, pulse ? 'vrs-status__pulse' : '', className].filter(Boolean).join(' ');
  return /*#__PURE__*/React.createElement("span", _extends({
    className: cls
  }, rest), /*#__PURE__*/React.createElement("span", {
    className: "vrs-status__ic"
  }, /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: "2.2",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }, GLYPH[status])), label || LABELS[status]);
}
Object.assign(__ds_scope, { StatusPill });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data/StatusPill.jsx", error: String((e && e.message) || e) }); }

// components/data/SignalRow.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.vrs-srow {
  display: grid;
  grid-template-columns: 22px minmax(150px, 1.4fr) minmax(120px, 1fr) 130px auto;
  align-items: center; gap: 16px;
  padding: 12px 16px; background: var(--surface-card);
  border: 1px solid var(--border-default); border-radius: var(--radius-md);
  transition: border-color var(--dur-fast) var(--ease-out), background var(--dur-fast) var(--ease-out);
}
.vrs-srow.is-interactive { cursor: pointer; }
.vrs-srow.is-interactive:hover { border-color: var(--border-strong); background: var(--surface-raised); }
.vrs-srow__rail { width: 3px; height: 26px; border-radius: 3px; background: var(--text-faint); }
.vrs-srow.s-verified .vrs-srow__rail { background: var(--verified-500); }
.vrs-srow.s-pending  .vrs-srow__rail { background: var(--pending-500); }
.vrs-srow.s-rejected .vrs-srow__rail { background: var(--rejected-500); }
.vrs-srow.s-observing .vrs-srow__rail { background: var(--info-500); }
.vrs-srow__main { min-width: 0; }
.vrs-srow__sym { font-family: var(--font-mono); font-size: var(--text-sm); font-weight: var(--fw-medium); color: var(--text-strong); }
.vrs-srow__id  { font-family: var(--font-mono); font-size: var(--text-3xs); color: var(--text-faint); margin-top: 2px; }
.vrs-srow__src { display: flex; align-items: center; gap: 7px; min-width: 0; }
.vrs-srow__srcname { font-family: var(--font-sans); font-size: var(--text-xs); color: var(--text-body); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.vrs-srow__ch { font-family: var(--font-mono); font-size: var(--text-3xs); color: var(--text-muted); }
.vrs-srow__right { display: flex; align-items: center; gap: 14px; justify-content: flex-end; }
.vrs-srow__time { font-family: var(--font-mono); font-size: var(--text-3xs); color: var(--text-faint); white-space: nowrap; }
.vrs-srow__avatar { width: 22px; height: 22px; border-radius: var(--radius-sm); flex: none; display: inline-flex; align-items: center; justify-content: center; font-family: var(--font-mono); font-size: 9px; font-weight: 600; color: var(--text-on-accent); text-transform: uppercase; }
`;
if (typeof document !== 'undefined' && !document.getElementById('vrs-srow-css')) {
  const s = document.createElement('style');
  s.id = 'vrs-srow-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

/** A single signal row — symbol, source, channel, confidence, status, time. */
function SignalRow({
  symbol,
  signalId,
  provider,
  providerTint = 'var(--viz-2)',
  channel,
  confidence,
  threshold = 80,
  status = 'pending',
  time,
  onClick,
  className = '',
  ...rest
}) {
  const initials = (provider || '').slice(0, 2);
  const cls = ['vrs-srow', `s-${status}`, onClick ? 'is-interactive' : '', className].filter(Boolean).join(' ');
  return /*#__PURE__*/React.createElement("div", _extends({
    className: cls,
    onClick: onClick
  }, rest), /*#__PURE__*/React.createElement("span", {
    className: "vrs-srow__rail",
    "aria-hidden": "true"
  }), /*#__PURE__*/React.createElement("div", {
    className: "vrs-srow__main"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vrs-srow__sym"
  }, symbol), signalId && /*#__PURE__*/React.createElement("div", {
    className: "vrs-srow__id"
  }, signalId)), /*#__PURE__*/React.createElement("div", {
    className: "vrs-srow__src"
  }, /*#__PURE__*/React.createElement("span", {
    className: "vrs-srow__avatar",
    style: {
      background: providerTint
    }
  }, initials), /*#__PURE__*/React.createElement("div", {
    style: {
      minWidth: 0
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "vrs-srow__srcname"
  }, provider), channel && /*#__PURE__*/React.createElement("div", {
    className: "vrs-srow__ch"
  }, channel))), /*#__PURE__*/React.createElement("div", null, confidence != null && /*#__PURE__*/React.createElement(__ds_scope.ConfidenceBar, {
    value: confidence,
    threshold: threshold,
    label: null
  })), /*#__PURE__*/React.createElement("div", {
    className: "vrs-srow__right"
  }, /*#__PURE__*/React.createElement(__ds_scope.StatusPill, {
    status: status,
    pulse: status === 'pending'
  }), time && /*#__PURE__*/React.createElement("span", {
    className: "vrs-srow__time"
  }, time)));
}
Object.assign(__ds_scope, { SignalRow });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data/SignalRow.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Banner.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.vrs-banner {
  display: flex; align-items: flex-start; gap: 12px;
  padding: 12px 14px; border-radius: var(--radius-md);
  border: 1px solid var(--border-default); background: var(--surface-card);
  font-family: var(--font-sans);
}
.vrs-banner__accent { width: 3px; border-radius: 3px; align-self: stretch; flex: none; background: var(--text-muted); }
.vrs-banner__icon { flex: none; margin-top: 1px; color: var(--text-muted); }
.vrs-banner__icon svg { width: 18px; height: 18px; display: block; }
.vrs-banner__body { flex: 1; min-width: 0; }
.vrs-banner__title { font-size: var(--text-sm); font-weight: var(--fw-semibold); color: var(--text-strong); margin-bottom: 2px; }
.vrs-banner__msg { font-size: var(--text-xs); color: var(--text-body); line-height: 1.5; }
.vrs-banner__close { flex: none; border: 0; background: transparent; color: var(--text-faint); cursor: pointer; font-size: 16px; line-height: 1; padding: 2px; border-radius: var(--radius-xs); }
.vrs-banner__close:hover { color: var(--text-strong); background: var(--surface-hover); }
.vrs-banner__actions { display: flex; gap: 8px; margin-top: 10px; }

.vrs-banner__verified .vrs-banner__accent, .vrs-banner__verified .vrs-banner__icon { background: var(--verified-500); color: var(--verified-500); }
.vrs-banner__pending  .vrs-banner__accent, .vrs-banner__pending .vrs-banner__icon  { background: var(--pending-500);  color: var(--pending-500); }
.vrs-banner__rejected .vrs-banner__accent, .vrs-banner__rejected .vrs-banner__icon { background: var(--rejected-500); color: var(--rejected-500); }
.vrs-banner__info     .vrs-banner__accent, .vrs-banner__info .vrs-banner__icon     { background: var(--info-500);     color: var(--info-500); }
.vrs-banner__verified .vrs-banner__icon, .vrs-banner__pending .vrs-banner__icon, .vrs-banner__rejected .vrs-banner__icon, .vrs-banner__info .vrs-banner__icon { background: transparent; }
`;
if (typeof document !== 'undefined' && !document.getElementById('vrs-banner-css')) {
  const s = document.createElement('style');
  s.id = 'vrs-banner-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}
const ICONS = {
  verified: /*#__PURE__*/React.createElement("path", {
    d: "M20 6 9 17l-5-5"
  }),
  pending: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("circle", {
    cx: "12",
    cy: "12",
    r: "9"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M12 7v5l3 2"
  })),
  rejected: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("circle", {
    cx: "12",
    cy: "12",
    r: "9"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M12 8v5M12 16h.01"
  })),
  info: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("circle", {
    cx: "12",
    cy: "12",
    r: "9"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M12 11v5M12 8h.01"
  })),
  neutral: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("circle", {
    cx: "12",
    cy: "12",
    r: "9"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M12 11v5M12 8h.01"
  }))
};

/** Inline banner / alert with semantic tone. */
function Banner({
  tone = 'info',
  title,
  icon,
  onClose,
  actions,
  className = '',
  children,
  ...rest
}) {
  const cls = ['vrs-banner', `vrs-banner__${tone}`, className].filter(Boolean).join(' ');
  return /*#__PURE__*/React.createElement("div", _extends({
    className: cls,
    role: "status"
  }, rest), /*#__PURE__*/React.createElement("span", {
    className: "vrs-banner__accent",
    "aria-hidden": "true"
  }), /*#__PURE__*/React.createElement("span", {
    className: "vrs-banner__icon"
  }, icon || /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: "2",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }, ICONS[tone] || ICONS.info)), /*#__PURE__*/React.createElement("div", {
    className: "vrs-banner__body"
  }, title && /*#__PURE__*/React.createElement("div", {
    className: "vrs-banner__title"
  }, title), children && /*#__PURE__*/React.createElement("div", {
    className: "vrs-banner__msg"
  }, children), actions && /*#__PURE__*/React.createElement("div", {
    className: "vrs-banner__actions"
  }, actions)), onClose && /*#__PURE__*/React.createElement("button", {
    className: "vrs-banner__close",
    "aria-label": "Dismiss",
    onClick: onClose
  }, "\xD7"));
}
Object.assign(__ds_scope, { Banner });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Banner.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Dialog.jsx
try { (() => {
const CSS = `
.vrs-dialog__scrim {
  position: fixed; inset: 0; z-index: var(--z-modal);
  background: rgba(6,7,9,0.66); backdrop-filter: blur(var(--blur-sm));
  display: flex; align-items: center; justify-content: center; padding: 24px;
  animation: vrs-dialog-fade var(--dur-base) var(--ease-out);
}
@keyframes vrs-dialog-fade { from { opacity: 0; } to { opacity: 1; } }
.vrs-dialog {
  width: 100%; max-width: 460px;
  background: var(--surface-card); border: 1px solid var(--border-strong);
  border-radius: var(--radius-xl); box-shadow: var(--shadow-pop);
  animation: vrs-dialog-rise var(--dur-base) var(--ease-out);
}
@keyframes vrs-dialog-rise { from { opacity: 0; transform: translateY(10px) scale(0.99); } to { opacity: 1; transform: none; } }
.vrs-dialog__head { display: flex; align-items: flex-start; gap: 14px; padding: 20px 20px 0; }
.vrs-dialog__icon { flex: none; width: 38px; height: 38px; border-radius: var(--radius-md); display: inline-flex; align-items: center; justify-content: center; background: var(--accent-quiet); color: var(--accent-text); }
.vrs-dialog__icon svg { width: 19px; height: 19px; }
.vrs-dialog__titles { flex: 1; min-width: 0; }
.vrs-dialog__title { font-family: var(--font-display); font-size: var(--text-lg); font-weight: var(--fw-semibold); color: var(--text-strong); }
.vrs-dialog__desc { font-family: var(--font-sans); font-size: var(--text-sm); color: var(--text-muted); margin-top: 4px; line-height: 1.5; }
.vrs-dialog__close { flex: none; border: 0; background: transparent; color: var(--text-faint); cursor: pointer; font-size: 19px; line-height: 1; padding: 4px; border-radius: var(--radius-xs); }
.vrs-dialog__close:hover { color: var(--text-strong); background: var(--surface-hover); }
.vrs-dialog__body { padding: 16px 20px; font-family: var(--font-sans); font-size: var(--text-sm); color: var(--text-body); line-height: 1.55; }
.vrs-dialog__foot { display: flex; justify-content: flex-end; gap: 10px; padding: 12px 20px 20px; }
`;
if (typeof document !== 'undefined' && !document.getElementById('vrs-dialog-css')) {
  const s = document.createElement('style');
  s.id = 'vrs-dialog-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

/** Modal dialog. Render conditionally on `open`. */
function Dialog({
  open,
  title,
  description,
  icon,
  onClose,
  footer,
  className = '',
  children
}) {
  if (!open) return null;
  return /*#__PURE__*/React.createElement("div", {
    className: "vrs-dialog__scrim",
    onClick: onClose
  }, /*#__PURE__*/React.createElement("div", {
    className: ['vrs-dialog', className].filter(Boolean).join(' '),
    role: "dialog",
    "aria-modal": "true",
    onClick: e => e.stopPropagation()
  }, /*#__PURE__*/React.createElement("div", {
    className: "vrs-dialog__head"
  }, icon && /*#__PURE__*/React.createElement("span", {
    className: "vrs-dialog__icon"
  }, icon), /*#__PURE__*/React.createElement("div", {
    className: "vrs-dialog__titles"
  }, title && /*#__PURE__*/React.createElement("div", {
    className: "vrs-dialog__title"
  }, title), description && /*#__PURE__*/React.createElement("div", {
    className: "vrs-dialog__desc"
  }, description)), onClose && /*#__PURE__*/React.createElement("button", {
    className: "vrs-dialog__close",
    "aria-label": "Close",
    onClick: onClose
  }, "\xD7")), children && /*#__PURE__*/React.createElement("div", {
    className: "vrs-dialog__body"
  }, children), footer && /*#__PURE__*/React.createElement("div", {
    className: "vrs-dialog__foot"
  }, footer)));
}
Object.assign(__ds_scope, { Dialog });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Dialog.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Toast.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.vrs-toast {
  display: flex; align-items: flex-start; gap: 11px;
  width: 340px; padding: 13px 14px;
  background: var(--ink-800); border: 1px solid var(--border-strong);
  border-radius: var(--radius-lg); box-shadow: var(--shadow-lg);
  font-family: var(--font-sans);
  animation: vrs-toast-in var(--dur-base) var(--ease-out);
}
@keyframes vrs-toast-in { from { opacity: 0; transform: translateY(8px) scale(0.98); } to { opacity: 1; transform: none; } }
.vrs-toast__dot { flex: none; width: 8px; height: 8px; margin-top: 5px; border-radius: 50%; background: var(--text-muted); }
.vrs-toast__verified .vrs-toast__dot { background: var(--verified-500); box-shadow: 0 0 10px var(--signal-glow); }
.vrs-toast__pending  .vrs-toast__dot { background: var(--pending-500); }
.vrs-toast__rejected .vrs-toast__dot { background: var(--rejected-500); }
.vrs-toast__info     .vrs-toast__dot { background: var(--info-500); }
.vrs-toast__body { flex: 1; min-width: 0; }
.vrs-toast__title { font-size: var(--text-sm); font-weight: var(--fw-semibold); color: var(--text-strong); display: flex; align-items: center; gap: 8px; }
.vrs-toast__time { font-family: var(--font-mono); font-size: var(--text-3xs); color: var(--text-faint); margin-left: auto; }
.vrs-toast__msg { font-size: var(--text-xs); color: var(--text-muted); margin-top: 3px; line-height: 1.45; }
.vrs-toast__close { flex: none; border: 0; background: transparent; color: var(--text-faint); cursor: pointer; font-size: 15px; line-height: 1; padding: 2px; border-radius: var(--radius-xs); }
.vrs-toast__close:hover { color: var(--text-strong); }
.vrs-toast-stack { position: fixed; bottom: 20px; right: 20px; z-index: var(--z-toast); display: flex; flex-direction: column; gap: 10px; }
`;
if (typeof document !== 'undefined' && !document.getElementById('vrs-toast-css')) {
  const s = document.createElement('style');
  s.id = 'vrs-toast-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

/** A single toast notification (presentational). */
function Toast({
  tone = 'info',
  title,
  time,
  onClose,
  className = '',
  children,
  ...rest
}) {
  const cls = ['vrs-toast', `vrs-toast__${tone}`, className].filter(Boolean).join(' ');
  return /*#__PURE__*/React.createElement("div", _extends({
    className: cls,
    role: "status"
  }, rest), /*#__PURE__*/React.createElement("span", {
    className: "vrs-toast__dot",
    "aria-hidden": "true"
  }), /*#__PURE__*/React.createElement("div", {
    className: "vrs-toast__body"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vrs-toast__title"
  }, title, time && /*#__PURE__*/React.createElement("span", {
    className: "vrs-toast__time"
  }, time)), children && /*#__PURE__*/React.createElement("div", {
    className: "vrs-toast__msg"
  }, children)), onClose && /*#__PURE__*/React.createElement("button", {
    className: "vrs-toast__close",
    "aria-label": "Dismiss",
    onClick: onClose
  }, "\xD7"));
}

/** Fixed bottom-right container for stacking toasts. */
function ToastStack({
  className = '',
  children,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("div", _extends({
    className: ['vrs-toast-stack', className].filter(Boolean).join(' ')
  }, rest), children);
}
Object.assign(__ds_scope, { Toast, ToastStack });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Toast.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Tooltip.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.vrs-tip { position: relative; display: inline-flex; }
.vrs-tip__pop {
  position: absolute; z-index: var(--z-tooltip);
  bottom: calc(100% + 8px); left: 50%; transform: translateX(-50%) translateY(4px);
  background: var(--ink-800); color: var(--text-strong);
  border: 1px solid var(--border-strong); border-radius: var(--radius-sm);
  padding: 6px 9px; font-family: var(--font-sans); font-size: var(--text-2xs); line-height: 1.4;
  white-space: nowrap; box-shadow: var(--shadow-md);
  opacity: 0; pointer-events: none;
  transition: opacity var(--dur-fast) var(--ease-out), transform var(--dur-fast) var(--ease-out);
}
.vrs-tip__pop[data-side="bottom"] { bottom: auto; top: calc(100% + 8px); transform: translateX(-50%) translateY(-4px); }
.vrs-tip:hover .vrs-tip__pop, .vrs-tip:focus-within .vrs-tip__pop { opacity: 1; transform: translateX(-50%) translateY(0); }
.vrs-tip__pop kbd { font-family: var(--font-mono); color: var(--text-muted); margin-left: 6px; }
`;
if (typeof document !== 'undefined' && !document.getElementById('vrs-tip-css')) {
  const s = document.createElement('style');
  s.id = 'vrs-tip-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

/** Hover/focus tooltip wrapping its single child. */
function Tooltip({
  label,
  side = 'top',
  shortcut,
  className = '',
  children,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("span", _extends({
    className: ['vrs-tip', className].filter(Boolean).join(' ')
  }, rest), children, /*#__PURE__*/React.createElement("span", {
    className: "vrs-tip__pop",
    role: "tooltip",
    "data-side": side
  }, label, shortcut && /*#__PURE__*/React.createElement("kbd", null, shortcut)));
}
Object.assign(__ds_scope, { Tooltip });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Tooltip.jsx", error: String((e && e.message) || e) }); }

// components/forms/Checkbox.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.vrs-check { display: inline-flex; align-items: flex-start; gap: 10px; cursor: pointer; user-select: none; }
.vrs-check.is-disabled { opacity: 0.5; cursor: not-allowed; }
.vrs-check input { position: absolute; opacity: 0; width: 0; height: 0; }
.vrs-check__box {
  flex: none; width: 18px; height: 18px; margin-top: 1px;
  border-radius: var(--radius-xs); border: 1.5px solid var(--border-strong);
  background: var(--surface-sunken);
  display: inline-flex; align-items: center; justify-content: center;
  color: var(--text-on-accent);
  transition: background var(--dur-fast) var(--ease-out), border-color var(--dur-fast) var(--ease-out);
}
.vrs-check:hover .vrs-check__box { border-color: var(--accent); }
.vrs-check input:checked + .vrs-check__box { background: var(--accent); border-color: var(--accent); }
.vrs-check input:focus-visible + .vrs-check__box { box-shadow: var(--focus-ring); }
.vrs-check__box svg { width: 12px; height: 12px; stroke-width: 3; opacity: 0; transform: scale(0.6); transition: opacity var(--dur-fast) var(--ease-out), transform var(--dur-fast) var(--ease-snap); }
.vrs-check input:checked + .vrs-check__box svg { opacity: 1; transform: scale(1); }
.vrs-check__text { display: flex; flex-direction: column; gap: 2px; }
.vrs-check__label { font-family: var(--font-sans); font-size: var(--text-sm); color: var(--text-strong); line-height: 1.3; }
.vrs-check__desc { font-family: var(--font-sans); font-size: var(--text-2xs); color: var(--text-muted); }
`;
if (typeof document !== 'undefined' && !document.getElementById('vrs-check-css')) {
  const s = document.createElement('style');
  s.id = 'vrs-check-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

/** Checkbox with optional label + description. */
function Checkbox({
  label,
  description,
  disabled = false,
  className = '',
  id,
  ...rest
}) {
  const cls = ['vrs-check', disabled ? 'is-disabled' : '', className].filter(Boolean).join(' ');
  return /*#__PURE__*/React.createElement("label", {
    className: cls
  }, /*#__PURE__*/React.createElement("input", _extends({
    type: "checkbox",
    disabled: disabled,
    id: id
  }, rest)), /*#__PURE__*/React.createElement("span", {
    className: "vrs-check__box"
  }, /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M20 6 9 17l-5-5"
  }))), (label || description) && /*#__PURE__*/React.createElement("span", {
    className: "vrs-check__text"
  }, label && /*#__PURE__*/React.createElement("span", {
    className: "vrs-check__label"
  }, label), description && /*#__PURE__*/React.createElement("span", {
    className: "vrs-check__desc"
  }, description)));
}
Object.assign(__ds_scope, { Checkbox });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Checkbox.jsx", error: String((e && e.message) || e) }); }

// components/forms/Input.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.vrs-field { display: flex; flex-direction: column; gap: 6px; }
.vrs-field__label { font-family: var(--font-sans); font-size: var(--text-xs); font-weight: var(--fw-medium); color: var(--text-body); display: flex; gap: 6px; align-items: center; }
.vrs-field__req { color: var(--accent-text); }
.vrs-field__hint { font-family: var(--font-sans); font-size: var(--text-2xs); color: var(--text-muted); }
.vrs-field__hint.is-error { color: var(--rejected-500); }

.vrs-input {
  display: flex; align-items: center; gap: 8px;
  height: 38px; padding: 0 12px;
  background: var(--surface-sunken); color: var(--text-strong);
  border: 1px solid var(--border-default); border-radius: var(--radius-md);
  transition: border-color var(--dur-fast) var(--ease-out), box-shadow var(--dur-fast) var(--ease-out), background var(--dur-fast) var(--ease-out);
}
.vrs-input:hover { border-color: var(--border-strong); }
.vrs-input:focus-within { border-color: var(--border-focus); box-shadow: 0 0 0 3px var(--accent-quiet); background: var(--surface-card); }
.vrs-input input {
  flex: 1; min-width: 0; border: 0; outline: 0; background: transparent;
  font-family: var(--font-sans); font-size: var(--text-sm); color: inherit;
}
/* The wrapper owns the focus affordance (border + ring) via :focus-within above.
   Neutralize the inner control's own ring so the global :focus-visible catch-all
   in base.css can't paint a second, concentric ring inside the wrapper. */
.vrs-input input:focus,
.vrs-input input:focus-visible {
  outline: none;
  box-shadow: none;
}
.vrs-input input::placeholder { color: var(--text-faint); }
.vrs-input__icon { color: var(--text-muted); display: inline-flex; flex: none; }
.vrs-input__icon svg { width: 16px; height: 16px; display:block; }
.vrs-input.is-error { border-color: var(--rejected-500); }
.vrs-input.is-error:focus-within { box-shadow: 0 0 0 3px var(--rejected-bg); }
.vrs-input.is-mono input { font-family: var(--font-mono); font-size: var(--text-xs); letter-spacing: 0.01em; }
.vrs-input.is-disabled { opacity: 0.5; pointer-events: none; }
.vrs-input__kbd { font-family: var(--font-mono); font-size: var(--text-3xs); color: var(--text-faint); border: 1px solid var(--border-default); border-radius: var(--radius-xs); padding: 1px 5px; }
`;
if (typeof document !== 'undefined' && !document.getElementById('vrs-input-css')) {
  const s = document.createElement('style');
  s.id = 'vrs-input-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

/** Text input with optional label, icon, hint and error state. */
function Input({
  label,
  hint,
  error,
  required = false,
  iconLeft,
  trailing,
  mono = false,
  disabled = false,
  id,
  className = '',
  ...rest
}) {
  const fieldId = id || (label ? `vrs-${label.replace(/\s+/g, '-').toLowerCase()}` : undefined);
  const boxCls = ['vrs-input', error ? 'is-error' : '', mono ? 'is-mono' : '', disabled ? 'is-disabled' : '', className].filter(Boolean).join(' ');
  return /*#__PURE__*/React.createElement("div", {
    className: "vrs-field"
  }, label && /*#__PURE__*/React.createElement("label", {
    className: "vrs-field__label",
    htmlFor: fieldId
  }, label, required && /*#__PURE__*/React.createElement("span", {
    className: "vrs-field__req"
  }, "*")), /*#__PURE__*/React.createElement("div", {
    className: boxCls
  }, iconLeft && /*#__PURE__*/React.createElement("span", {
    className: "vrs-input__icon"
  }, iconLeft), /*#__PURE__*/React.createElement("input", _extends({
    id: fieldId,
    disabled: disabled
  }, rest)), trailing), (error || hint) && /*#__PURE__*/React.createElement("span", {
    className: `vrs-field__hint ${error ? 'is-error' : ''}`
  }, error || hint));
}
Object.assign(__ds_scope, { Input });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Input.jsx", error: String((e && e.message) || e) }); }

// components/forms/Select.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.vrs-select { position: relative; display: flex; flex-direction: column; gap: 6px; }
.vrs-select__label { font-family: var(--font-sans); font-size: var(--text-xs); font-weight: var(--fw-medium); color: var(--text-body); }
.vrs-select__box { position: relative; display: flex; align-items: center; }
.vrs-select select {
  appearance: none; width: 100%; height: 38px;
  padding: 0 36px 0 12px;
  font-family: var(--font-sans); font-size: var(--text-sm); color: var(--text-strong);
  background: var(--surface-sunken); border: 1px solid var(--border-default);
  border-radius: var(--radius-md); cursor: pointer;
  transition: border-color var(--dur-fast) var(--ease-out), box-shadow var(--dur-fast) var(--ease-out);
}
.vrs-select select:hover { border-color: var(--border-strong); }
.vrs-select select:focus-visible { outline: none; border-color: var(--border-focus); box-shadow: 0 0 0 3px var(--accent-quiet); }
.vrs-select__chev {
  position: absolute; right: 12px; pointer-events: none; color: var(--text-muted);
  display: inline-flex;
}
.vrs-select__chev svg { width: 15px; height: 15px; display:block; }
.vrs-select.is-disabled { opacity: 0.5; pointer-events: none; }
`;
if (typeof document !== 'undefined' && !document.getElementById('vrs-select-css')) {
  const s = document.createElement('style');
  s.id = 'vrs-select-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

/** Native select, styled. Pass `options` or `children`. */
function Select({
  label,
  options,
  disabled = false,
  className = '',
  children,
  ...rest
}) {
  const cls = ['vrs-select', disabled ? 'is-disabled' : '', className].filter(Boolean).join(' ');
  return /*#__PURE__*/React.createElement("div", {
    className: cls
  }, label && /*#__PURE__*/React.createElement("label", {
    className: "vrs-select__label"
  }, label), /*#__PURE__*/React.createElement("div", {
    className: "vrs-select__box"
  }, /*#__PURE__*/React.createElement("select", _extends({
    disabled: disabled
  }, rest), options ? options.map(o => {
    const value = typeof o === 'string' ? o : o.value;
    const text = typeof o === 'string' ? o : o.label;
    return /*#__PURE__*/React.createElement("option", {
      key: value,
      value: value
    }, text);
  }) : children), /*#__PURE__*/React.createElement("span", {
    className: "vrs-select__chev"
  }, /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: "2",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }, /*#__PURE__*/React.createElement("path", {
    d: "m6 9 6 6 6-6"
  })))));
}
Object.assign(__ds_scope, { Select });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Select.jsx", error: String((e && e.message) || e) }); }

// components/forms/Switch.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.vrs-switch { display: inline-flex; align-items: center; gap: 10px; cursor: pointer; user-select: none; }
.vrs-switch.is-disabled { opacity: 0.5; cursor: not-allowed; }
.vrs-switch input { position: absolute; opacity: 0; width: 0; height: 0; }
.vrs-switch__track {
  position: relative; flex: none; width: 38px; height: 22px;
  background: var(--surface-hover); border: 1px solid var(--border-strong);
  border-radius: var(--radius-pill);
  transition: background var(--dur-base) var(--ease-out), border-color var(--dur-base) var(--ease-out);
}
.vrs-switch__thumb {
  position: absolute; top: 2px; left: 2px; width: 16px; height: 16px;
  background: var(--text-muted); border-radius: 50%;
  transition: transform var(--dur-base) var(--ease-snap), background var(--dur-base) var(--ease-out);
}
.vrs-switch input:checked + .vrs-switch__track { background: var(--accent); border-color: var(--accent); }
.vrs-switch input:checked + .vrs-switch__track .vrs-switch__thumb { transform: translateX(16px); background: var(--text-on-accent); }
.vrs-switch input:focus-visible + .vrs-switch__track { box-shadow: var(--focus-ring); }
.vrs-switch__label { font-family: var(--font-sans); font-size: var(--text-sm); color: var(--text-strong); }
`;
if (typeof document !== 'undefined' && !document.getElementById('vrs-switch-css')) {
  const s = document.createElement('style');
  s.id = 'vrs-switch-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

/** Toggle switch. */
function Switch({
  label,
  disabled = false,
  className = '',
  id,
  ...rest
}) {
  const cls = ['vrs-switch', disabled ? 'is-disabled' : '', className].filter(Boolean).join(' ');
  return /*#__PURE__*/React.createElement("label", {
    className: cls
  }, /*#__PURE__*/React.createElement("input", _extends({
    type: "checkbox",
    role: "switch",
    disabled: disabled,
    id: id
  }, rest)), /*#__PURE__*/React.createElement("span", {
    className: "vrs-switch__track"
  }, /*#__PURE__*/React.createElement("span", {
    className: "vrs-switch__thumb"
  })), label && /*#__PURE__*/React.createElement("span", {
    className: "vrs-switch__label"
  }, label));
}
Object.assign(__ds_scope, { Switch });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Switch.jsx", error: String((e && e.message) || e) }); }

// ui_kits/app/App.jsx
try { (() => {
/* Verasig App — shell */
function EmptyView({
  label
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: "vrs-page"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vrs-empty"
  }, /*#__PURE__*/React.createElement("svg", {
    width: "34",
    height: "34",
    viewBox: "0 0 40 40",
    fill: "none",
    style: {
      color: 'var(--text-faint)'
    }
  }, /*#__PURE__*/React.createElement("path", {
    d: "M4 22 L11 22 L17 30 L24 9 L30 18",
    stroke: "currentColor",
    strokeWidth: "3",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "30",
    cy: "18",
    r: "3",
    fill: "currentColor"
  })), /*#__PURE__*/React.createElement("div", {
    className: "vrs-empty__t"
  }, label), /*#__PURE__*/React.createElement("div", {
    className: "vrs-empty__s"
  }, "This area is part of the Verasig kit \u2014 wire it up to your data.")));
}
function App() {
  const {
    Sidebar,
    Topbar,
    OverviewView,
    SignalsView,
    ProvidersView,
    SignalDrawer
  } = window;
  const {
    Dialog,
    Button,
    Toast,
    ToastStack
  } = window.VerasigDesignSystem_fd565b;
  const {
    useState
  } = React;
  const [nav, setNav] = useState('overview');
  const [signal, setSignal] = useState(null);
  const [confirmReject, setConfirmReject] = useState(false);
  const [toast, setToast] = useState(null);
  const TITLES = {
    overview: ['Overview', 'Real-time verification across every channel'],
    signals: ['Signals', '248 signals in the last hour'],
    providers: ['Providers', '6 sources connected'],
    channels: ['Channels', 'Webhook · REST · gRPC · WebSocket'],
    settings: ['Settings', 'Workspace & verification policy']
  };
  function openSignal(s) {
    if (s === null) {
      setNav('signals');
      return;
    }
    setSignal(s);
  }
  function doReject() {
    setConfirmReject(false);
    setSignal(null);
    setToast({
      tone: 'rejected',
      title: 'Signal rejected',
      msg: 'Quarantined and removed from the live feed.',
      time: '11:32:40'
    });
    setTimeout(() => setToast(null), 4200);
  }
  let view;
  if (nav === 'overview') view = /*#__PURE__*/React.createElement(OverviewView, {
    onOpenSignal: openSignal
  });else if (nav === 'signals') view = /*#__PURE__*/React.createElement(SignalsView, {
    onOpenSignal: openSignal
  });else if (nav === 'providers') view = /*#__PURE__*/React.createElement(ProvidersView, null);else view = /*#__PURE__*/React.createElement(EmptyView, {
    label: TITLES[nav][0]
  });
  return /*#__PURE__*/React.createElement("div", {
    className: "vrs-shell"
  }, /*#__PURE__*/React.createElement(Sidebar, {
    active: nav,
    onNavigate: setNav
  }), /*#__PURE__*/React.createElement("main", {
    className: "vrs-main"
  }, /*#__PURE__*/React.createElement(Topbar, {
    title: TITLES[nav][0],
    subtitle: TITLES[nav][1]
  }), /*#__PURE__*/React.createElement("div", {
    className: "vrs-scroll"
  }, view)), /*#__PURE__*/React.createElement(SignalDrawer, {
    signal: signal,
    onClose: () => setSignal(null),
    onReject: () => setConfirmReject(true)
  }), /*#__PURE__*/React.createElement(Dialog, {
    open: confirmReject,
    onClose: () => setConfirmReject(false),
    title: "Reject this signal?",
    description: "It will be quarantined and downstream consumers won't receive it.",
    footer: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement(Button, {
      variant: "ghost",
      onClick: () => setConfirmReject(false)
    }, "Cancel"), /*#__PURE__*/React.createElement(Button, {
      variant: "danger",
      onClick: doReject
    }, "Reject signal"))
  }, "Rejecting ", /*#__PURE__*/React.createElement("strong", {
    style: {
      color: 'var(--text-strong)',
      fontFamily: 'var(--font-mono)'
    }
  }, signal && signal.id), " removes it from the live feed immediately."), toast && /*#__PURE__*/React.createElement(ToastStack, null, /*#__PURE__*/React.createElement(Toast, {
    tone: toast.tone,
    title: toast.title,
    time: toast.time,
    onClose: () => setToast(null)
  }, toast.msg)));
}
window.App = App;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/app/App.jsx", error: String((e && e.message) || e) }); }

// ui_kits/app/OverviewView.jsx
try { (() => {
/* Verasig App — Overview (dashboard) */
function MiniTrace({
  color = 'var(--signal-500)'
}) {
  // tiny static sparkline-ish verified trace
  return /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 120 36",
    fill: "none",
    preserveAspectRatio: "none",
    style: {
      width: '100%',
      height: '36px'
    }
  }, /*#__PURE__*/React.createElement("path", {
    d: "M0 26 L18 24 L30 27 L44 14 L58 20 L72 9 L86 17 L100 7 L120 12",
    stroke: color,
    strokeWidth: "1.8",
    strokeLinecap: "round",
    strokeLinejoin: "round",
    opacity: "0.9"
  }));
}
function OverviewView({
  onOpenSignal
}) {
  const {
    Card,
    MetricStat,
    SignalRow,
    Badge,
    StatusPill,
    ConfidenceBar,
    Button
  } = window.VerasigDesignSystem_fd565b;
  const {
    signals,
    providers
  } = window.VRS_DATA;
  return /*#__PURE__*/React.createElement("div", {
    className: "vrs-page"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vrs-grid-metrics"
  }, /*#__PURE__*/React.createElement(Card, null, /*#__PURE__*/React.createElement(MetricStat, {
    label: "Verified \xB7 24h",
    value: "11,204",
    delta: "+4.2%",
    trend: "up",
    caption: "of 11,247 signals"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 10
    }
  }, /*#__PURE__*/React.createElement(MiniTrace, null))), /*#__PURE__*/React.createElement(Card, null, /*#__PURE__*/React.createElement(MetricStat, {
    label: "Median latency",
    value: "182",
    unit: "ms",
    delta: "\u221212ms",
    trend: "up",
    caption: "p50 across channels"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 10
    }
  }, /*#__PURE__*/React.createElement(MiniTrace, {
    color: "var(--viz-2)"
  }))), /*#__PURE__*/React.createElement(Card, null, /*#__PURE__*/React.createElement(MetricStat, {
    label: "Quorum rate",
    value: "99.6",
    unit: "%",
    delta: "+0.1",
    trend: "up",
    caption: "reached threshold"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 10
    }
  }, /*#__PURE__*/React.createElement(MiniTrace, {
    color: "var(--viz-5)"
  }))), /*#__PURE__*/React.createElement(Card, null, /*#__PURE__*/React.createElement(MetricStat, {
    label: "Rejected \xB7 24h",
    value: "43",
    delta: "+7",
    trend: "down",
    caption: "quarantined"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 10
    }
  }, /*#__PURE__*/React.createElement(MiniTrace, {
    color: "var(--rejected-500)"
  })))), /*#__PURE__*/React.createElement("div", {
    className: "vrs-grid-two"
  }, /*#__PURE__*/React.createElement(Card, {
    title: "Live verification",
    subtitle: "Most recent signals across all channels",
    headerActions: /*#__PURE__*/React.createElement(Badge, {
      tone: "verified",
      dot: true
    }, "Live"),
    padded: false
  }, /*#__PURE__*/React.createElement("div", {
    className: "vrs-feed"
  }, signals.slice(0, 5).map(s => /*#__PURE__*/React.createElement(SignalRow, {
    key: s.id,
    symbol: s.symbol,
    signalId: s.id,
    provider: s.provider,
    providerTint: s.tint,
    channel: s.channel,
    confidence: s.confidence,
    status: s.status,
    time: s.time,
    onClick: () => onOpenSignal(s)
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '12px 16px'
    }
  }, /*#__PURE__*/React.createElement(Button, {
    variant: "ghost",
    size: "sm",
    onClick: () => onOpenSignal(null)
  }, "View all signals \u2192"))), /*#__PURE__*/React.createElement(Card, {
    title: "Provider health",
    subtitle: "Source uptime & quorum",
    padded: false
  }, /*#__PURE__*/React.createElement("div", {
    className: "vrs-provhealth"
  }, providers.map(p => /*#__PURE__*/React.createElement("div", {
    className: "vrs-provhealth__row",
    key: p.id
  }, /*#__PURE__*/React.createElement("span", {
    className: "vrs-prov__sw",
    style: {
      background: p.tint
    }
  }, p.name.slice(0, 2)), /*#__PURE__*/React.createElement("div", {
    className: "vrs-provhealth__main"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vrs-provhealth__name"
  }, p.name), /*#__PURE__*/React.createElement("div", {
    className: "vrs-provhealth__ch"
  }, p.channel)), /*#__PURE__*/React.createElement("span", {
    className: "vrs-mono-faint"
  }, p.uptime.toFixed(2), "%"), /*#__PURE__*/React.createElement(StatusPill, {
    status: p.health,
    pulse: p.health === 'pending'
  })))))));
}
window.OverviewView = OverviewView;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/app/OverviewView.jsx", error: String((e && e.message) || e) }); }

// ui_kits/app/ProvidersView.jsx
try { (() => {
/* Verasig App — Providers */
function ProvidersView() {
  const {
    Card,
    StatusPill,
    Badge,
    Button,
    MetricStat,
    Avatar
  } = window.VerasigDesignSystem_fd565b;
  const {
    providers
  } = window.VRS_DATA;
  const Plus = () => /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 24 24",
    width: "16",
    height: "16",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: "2",
    strokeLinecap: "round"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M12 5v14M5 12h14"
  }));
  return /*#__PURE__*/React.createElement("div", {
    className: "vrs-page"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vrs-grid-metrics",
    style: {
      gridTemplateColumns: 'repeat(3, 1fr)'
    }
  }, /*#__PURE__*/React.createElement(Card, null, /*#__PURE__*/React.createElement(MetricStat, {
    label: "Active providers",
    value: "6",
    caption: "across 4 channels"
  })), /*#__PURE__*/React.createElement(Card, null, /*#__PURE__*/React.createElement(MetricStat, {
    label: "Avg uptime",
    value: "99.66",
    unit: "%",
    delta: "+0.04",
    trend: "up",
    caption: "last 30 days"
  })), /*#__PURE__*/React.createElement(Card, null, /*#__PURE__*/React.createElement(MetricStat, {
    label: "Data points \xB7 24h",
    value: "3.5",
    unit: "M",
    delta: "+120k",
    trend: "up",
    caption: "ingested"
  }))), /*#__PURE__*/React.createElement(Card, {
    title: "Providers",
    subtitle: "Signal sources connected to this workspace",
    headerActions: /*#__PURE__*/React.createElement(Button, {
      variant: "primary",
      size: "sm",
      iconLeft: /*#__PURE__*/React.createElement(Plus, null)
    }, "Connect provider"),
    padded: false
  }, /*#__PURE__*/React.createElement("div", {
    className: "vrs-provtable__head"
  }, /*#__PURE__*/React.createElement("span", null, "Provider"), /*#__PURE__*/React.createElement("span", null, "Channel"), /*#__PURE__*/React.createElement("span", null, "Uptime"), /*#__PURE__*/React.createElement("span", {
    style: {
      textAlign: 'right'
    }
  }, "Status")), /*#__PURE__*/React.createElement("div", {
    className: "vrs-provtable"
  }, providers.map(p => /*#__PURE__*/React.createElement("div", {
    className: "vrs-provtable__row",
    key: p.id
  }, /*#__PURE__*/React.createElement("div", {
    className: "vrs-provtable__name"
  }, /*#__PURE__*/React.createElement(Avatar, {
    name: p.name,
    square: true,
    tint: p.tint,
    size: "sm"
  }), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "vrs-provhealth__name"
  }, p.name), /*#__PURE__*/React.createElement("div", {
    className: "vrs-provhealth__ch"
  }, p.id, ".verasig.io"))), /*#__PURE__*/React.createElement("span", {
    className: "vrs-mono-faint"
  }, p.channel), /*#__PURE__*/React.createElement("span", {
    className: "vrs-mono-faint"
  }, p.uptime.toFixed(2), "%"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: 'flex-end'
    }
  }, /*#__PURE__*/React.createElement(StatusPill, {
    status: p.health,
    pulse: p.health === 'pending'
  })))))));
}
window.ProvidersView = ProvidersView;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/app/ProvidersView.jsx", error: String((e && e.message) || e) }); }

// ui_kits/app/Sidebar.jsx
try { (() => {
/* Verasig App — Sidebar */
const VRS_ICONS = {
  overview: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("rect", {
    x: "3",
    y: "3",
    width: "7",
    height: "9",
    rx: "1.5"
  }), /*#__PURE__*/React.createElement("rect", {
    x: "14",
    y: "3",
    width: "7",
    height: "5",
    rx: "1.5"
  }), /*#__PURE__*/React.createElement("rect", {
    x: "14",
    y: "12",
    width: "7",
    height: "9",
    rx: "1.5"
  }), /*#__PURE__*/React.createElement("rect", {
    x: "3",
    y: "16",
    width: "7",
    height: "5",
    rx: "1.5"
  })),
  signals: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("path", {
    d: "M3 12h3l2 6 4-14 3 10 2-4h4"
  })),
  providers: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("circle", {
    cx: "6",
    cy: "6",
    r: "2.5"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "18",
    cy: "6",
    r: "2.5"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "12",
    cy: "18",
    r: "2.5"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M7.7 7.7 11 15M16.3 7.7 13 15"
  })),
  channels: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("path", {
    d: "M4 7h16M4 12h16M4 17h16"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "8",
    cy: "7",
    r: "1.6",
    fill: "currentColor",
    stroke: "none"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "15",
    cy: "12",
    r: "1.6",
    fill: "currentColor",
    stroke: "none"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "10",
    cy: "17",
    r: "1.6",
    fill: "currentColor",
    stroke: "none"
  })),
  settings: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("circle", {
    cx: "12",
    cy: "12",
    r: "3"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-2.7 1.1V21a2 2 0 1 1-4 0v-.1A1.6 1.6 0 0 0 7 19.4a1.6 1.6 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1A1.6 1.6 0 0 0 2.6 14H2.5a2 2 0 1 1 0-4h.1A1.6 1.6 0 0 0 4 7.4l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1A1.6 1.6 0 0 0 9 4.6V4.5a2 2 0 1 1 4 0v.1A1.6 1.6 0 0 0 17 4.6l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0-.3 1.8V9.5a1.6 1.6 0 0 0 1.4 1h.1a2 2 0 1 1 0 4h-.1a1.6 1.6 0 0 0-1.4 1Z"
  }))
};
function VrsIcon({
  name
}) {
  return /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 24 24",
    width: "18",
    height: "18",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: "1.8",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }, VRS_ICONS[name]);
}
function Sidebar({
  active,
  onNavigate
}) {
  const {
    Avatar
  } = window.VerasigDesignSystem_fd565b;
  const items = [{
    id: 'overview',
    label: 'Overview'
  }, {
    id: 'signals',
    label: 'Signals',
    count: 248
  }, {
    id: 'providers',
    label: 'Providers'
  }, {
    id: 'channels',
    label: 'Channels'
  }, {
    id: 'settings',
    label: 'Settings'
  }];
  return /*#__PURE__*/React.createElement("aside", {
    className: "vrs-sb"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vrs-sb__brand"
  }, /*#__PURE__*/React.createElement("svg", {
    width: "26",
    height: "26",
    viewBox: "0 0 40 40",
    fill: "none",
    style: {
      color: 'var(--signal-500)'
    }
  }, /*#__PURE__*/React.createElement("path", {
    d: "M4 22 L11 22 L17 30 L24 9 L30 18",
    stroke: "currentColor",
    strokeWidth: "3.2",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "30",
    cy: "18",
    r: "3.4",
    fill: "currentColor"
  })), /*#__PURE__*/React.createElement("span", {
    className: "vrs-sb__word"
  }, "Verasig", /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--signal-500)'
    }
  }, "."))), /*#__PURE__*/React.createElement("div", {
    className: "vrs-sb__ws"
  }, /*#__PURE__*/React.createElement(Avatar, {
    name: "Northwave",
    square: true,
    tint: "var(--viz-2)",
    size: "sm"
  }), /*#__PURE__*/React.createElement("div", {
    className: "vrs-sb__ws-txt"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vrs-sb__ws-name"
  }, "Northwave"), /*#__PURE__*/React.createElement("div", {
    className: "vrs-sb__ws-plan"
  }, "Production \xB7 EU")), /*#__PURE__*/React.createElement("svg", {
    width: "14",
    height: "14",
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: "2",
    strokeLinecap: "round",
    strokeLinejoin: "round",
    style: {
      color: 'var(--text-faint)'
    }
  }, /*#__PURE__*/React.createElement("path", {
    d: "m8 9 4-4 4 4M16 15l-4 4-4-4"
  }))), /*#__PURE__*/React.createElement("nav", {
    className: "vrs-sb__nav"
  }, items.map(it => /*#__PURE__*/React.createElement("button", {
    key: it.id,
    className: `vrs-sb__item ${active === it.id ? 'is-active' : ''}`,
    onClick: () => onNavigate(it.id)
  }, /*#__PURE__*/React.createElement(VrsIcon, {
    name: it.id
  }), /*#__PURE__*/React.createElement("span", null, it.label), it.count != null && /*#__PURE__*/React.createElement("span", {
    className: "vrs-sb__count"
  }, it.count)))), /*#__PURE__*/React.createElement("div", {
    className: "vrs-sb__foot"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vrs-sb__live"
  }, /*#__PURE__*/React.createElement("span", {
    className: "vrs-sb__live-dot"
  }), /*#__PURE__*/React.createElement("span", null, "All systems verified")), /*#__PURE__*/React.createElement("div", {
    className: "vrs-sb__user"
  }, /*#__PURE__*/React.createElement(Avatar, {
    name: "Mara Voss",
    status: "verified",
    size: "sm"
  }), /*#__PURE__*/React.createElement("div", {
    className: "vrs-sb__ws-txt"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vrs-sb__ws-name"
  }, "Mara Voss"), /*#__PURE__*/React.createElement("div", {
    className: "vrs-sb__ws-plan"
  }, "mara@northwave.io")))));
}
window.Sidebar = Sidebar;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/app/Sidebar.jsx", error: String((e && e.message) || e) }); }

// ui_kits/app/SignalDrawer.jsx
try { (() => {
/* Verasig App — Signal detail drawer */
function SignalDrawer({
  signal,
  onClose,
  onReject
}) {
  const {
    StatusPill,
    ConfidenceBar,
    Badge,
    Button,
    Avatar
  } = window.VerasigDesignSystem_fd565b;
  const {
    sources
  } = window.VRS_DATA;
  if (!signal) return null;
  return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
    className: "vrs-drawer__scrim",
    onClick: onClose
  }), /*#__PURE__*/React.createElement("aside", {
    className: "vrs-drawer",
    role: "dialog",
    "aria-label": "Signal detail"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vrs-drawer__head"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "vrs-drawer__sym"
  }, signal.symbol), /*#__PURE__*/React.createElement("div", {
    className: "vrs-drawer__id"
  }, signal.id)), /*#__PURE__*/React.createElement("button", {
    className: "vrs-drawer__close",
    "aria-label": "Close",
    onClick: onClose
  }, "\xD7")), /*#__PURE__*/React.createElement("div", {
    className: "vrs-drawer__statusbar"
  }, /*#__PURE__*/React.createElement(StatusPill, {
    status: signal.status,
    pulse: signal.status === 'pending'
  }), /*#__PURE__*/React.createElement("span", {
    className: "vrs-mono-faint"
  }, signal.channel), /*#__PURE__*/React.createElement("span", {
    className: "vrs-mono-faint",
    style: {
      marginLeft: 'auto'
    }
  }, signal.time)), /*#__PURE__*/React.createElement("div", {
    className: "vrs-drawer__body"
  }, /*#__PURE__*/React.createElement("section", {
    className: "vrs-drawer__sec"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vrs-drawer__sec-h"
  }, "Quorum"), /*#__PURE__*/React.createElement(ConfidenceBar, {
    value: signal.confidence,
    threshold: 80,
    label: "Aggregate confidence"
  }), /*#__PURE__*/React.createElement("div", {
    className: "vrs-quorum"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vrs-quorum__cell"
  }, /*#__PURE__*/React.createElement("span", {
    className: "vrs-mono-faint"
  }, "Sources"), /*#__PURE__*/React.createElement("span", {
    className: "vrs-quorum__v"
  }, signal.sources)), /*#__PURE__*/React.createElement("div", {
    className: "vrs-quorum__cell"
  }, /*#__PURE__*/React.createElement("span", {
    className: "vrs-mono-faint"
  }, "Agreed"), /*#__PURE__*/React.createElement("span", {
    className: "vrs-quorum__v",
    style: {
      color: 'var(--verified-500)'
    }
  }, signal.agree)), /*#__PURE__*/React.createElement("div", {
    className: "vrs-quorum__cell"
  }, /*#__PURE__*/React.createElement("span", {
    className: "vrs-mono-faint"
  }, "Threshold"), /*#__PURE__*/React.createElement("span", {
    className: "vrs-quorum__v"
  }, "\u2265 80%")))), /*#__PURE__*/React.createElement("section", {
    className: "vrs-drawer__sec"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vrs-drawer__sec-h"
  }, "Source breakdown"), /*#__PURE__*/React.createElement("div", {
    className: "vrs-srclist"
  }, sources.map(s => /*#__PURE__*/React.createElement("div", {
    className: "vrs-srclist__row",
    key: s.name
  }, /*#__PURE__*/React.createElement("span", {
    className: `vrs-srclist__dot ${s.ok ? 'ok' : 'bad'}`
  }), /*#__PURE__*/React.createElement("span", {
    className: "vrs-srclist__name"
  }, s.name), /*#__PURE__*/React.createElement("span", {
    className: "vrs-srclist__val"
  }, s.value), /*#__PURE__*/React.createElement("span", {
    className: `vrs-srclist__dev ${s.ok ? '' : 'bad'}`
  }, s.dev))))), /*#__PURE__*/React.createElement("section", {
    className: "vrs-drawer__sec"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vrs-drawer__sec-h"
  }, "Timeline"), /*#__PURE__*/React.createElement("div", {
    className: "vrs-timeline"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vrs-tl__item"
  }, /*#__PURE__*/React.createElement("span", {
    className: "vrs-tl__t"
  }, "11:32:01"), /*#__PURE__*/React.createElement("span", {
    className: "vrs-tl__d"
  }, "Ingested from ", signal.provider)), /*#__PURE__*/React.createElement("div", {
    className: "vrs-tl__item"
  }, /*#__PURE__*/React.createElement("span", {
    className: "vrs-tl__t"
  }, "11:32:02"), /*#__PURE__*/React.createElement("span", {
    className: "vrs-tl__d"
  }, "Cross-checked ", signal.sources, " sources")), /*#__PURE__*/React.createElement("div", {
    className: "vrs-tl__item"
  }, /*#__PURE__*/React.createElement("span", {
    className: "vrs-tl__t"
  }, "11:32:04"), /*#__PURE__*/React.createElement("span", {
    className: "vrs-tl__d",
    style: {
      color: 'var(--text-strong)'
    }
  }, "Quorum ", signal.status === 'rejected' ? 'failed — quarantined' : 'reached — verified'))))), /*#__PURE__*/React.createElement("div", {
    className: "vrs-drawer__foot"
  }, /*#__PURE__*/React.createElement(Button, {
    variant: "secondary",
    fullWidth: true
  }, "Replay"), signal.status !== 'rejected' ? /*#__PURE__*/React.createElement(Button, {
    variant: "danger",
    fullWidth: true,
    onClick: onReject
  }, "Reject") : /*#__PURE__*/React.createElement(Button, {
    variant: "primary",
    fullWidth: true
  }, "Re-verify"))));
}
window.SignalDrawer = SignalDrawer;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/app/SignalDrawer.jsx", error: String((e && e.message) || e) }); }

// ui_kits/app/SignalsView.jsx
try { (() => {
/* Verasig App — Signals (table + filters) */
function SignalsView({
  onOpenSignal
}) {
  const {
    Tabs,
    Tag,
    SignalRow,
    Input,
    Button
  } = window.VerasigDesignSystem_fd565b;
  const {
    useState
  } = React;
  const {
    signals
  } = window.VRS_DATA;
  const [tab, setTab] = useState('all');
  const [chans, setChans] = useState({
    Webhook: true,
    REST: true,
    gRPC: true,
    WebSocket: true
  });
  const counts = {
    all: signals.length,
    verified: signals.filter(s => s.status === 'verified').length,
    pending: signals.filter(s => s.status === 'pending').length,
    rejected: signals.filter(s => s.status === 'rejected').length
  };
  const filtered = signals.filter(s => tab === 'all' || s.status === tab);
  const Filter = () => /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: "2",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M3 5h18l-7 8v6l-4 2v-8L3 5Z"
  }));
  return /*#__PURE__*/React.createElement("div", {
    className: "vrs-page"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vrs-signals__bar"
  }, /*#__PURE__*/React.createElement(Tabs, {
    value: tab,
    onChange: setTab,
    items: [{
      id: 'all',
      label: 'All',
      count: counts.all
    }, {
      id: 'verified',
      label: 'Verified',
      count: counts.verified
    }, {
      id: 'pending',
      label: 'Pending',
      count: counts.pending
    }, {
      id: 'rejected',
      label: 'Rejected',
      count: counts.rejected
    }]
  }), /*#__PURE__*/React.createElement("div", {
    className: "vrs-signals__filters"
  }, Object.keys(chans).map(c => /*#__PURE__*/React.createElement(Tag, {
    key: c,
    swatch: chans[c] ? 'var(--signal-500)' : 'var(--ink-600)',
    onClick: () => setChans({
      ...chans,
      [c]: !chans[c]
    }),
    style: {
      opacity: chans[c] ? 1 : 0.5
    }
  }, c)), /*#__PURE__*/React.createElement(Button, {
    variant: "secondary",
    size: "sm",
    iconLeft: /*#__PURE__*/React.createElement(Filter, null)
  }, "Filters"))), /*#__PURE__*/React.createElement("div", {
    className: "vrs-table"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vrs-table__head"
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      gridColumn: '1 / 3'
    }
  }, "Signal"), /*#__PURE__*/React.createElement("span", null, "Source"), /*#__PURE__*/React.createElement("span", null, "Confidence"), /*#__PURE__*/React.createElement("span", {
    style: {
      textAlign: 'right'
    }
  }, "Status \xB7 time")), /*#__PURE__*/React.createElement("div", {
    className: "vrs-feed"
  }, filtered.map(s => /*#__PURE__*/React.createElement(SignalRow, {
    key: s.id,
    symbol: s.symbol,
    signalId: s.id,
    provider: s.provider,
    providerTint: s.tint,
    channel: s.channel,
    confidence: s.confidence,
    status: s.status,
    time: s.time,
    onClick: () => onOpenSignal(s)
  })))));
}
window.SignalsView = SignalsView;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/app/SignalsView.jsx", error: String((e && e.message) || e) }); }

// ui_kits/app/Topbar.jsx
try { (() => {
/* Verasig App — Topbar */
function Topbar({
  title,
  subtitle,
  onReject
}) {
  const {
    Input,
    Button,
    IconButton,
    Tooltip,
    Badge
  } = window.VerasigDesignSystem_fd565b;
  const Search = () => /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: "2",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }, /*#__PURE__*/React.createElement("circle", {
    cx: "11",
    cy: "11",
    r: "7"
  }), /*#__PURE__*/React.createElement("path", {
    d: "m21 21-4.3-4.3"
  }));
  const Bell = () => /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: "1.8",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0"
  }));
  const Docs = () => /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: "1.8",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M4 19.5A2.5 2.5 0 0 1 6.5 17H20"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"
  }));
  return /*#__PURE__*/React.createElement("header", {
    className: "vrs-top"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vrs-top__titles"
  }, /*#__PURE__*/React.createElement("h1", {
    className: "vrs-top__title"
  }, title), subtitle && /*#__PURE__*/React.createElement("span", {
    className: "vrs-top__sub"
  }, subtitle)), /*#__PURE__*/React.createElement("div", {
    className: "vrs-top__search"
  }, /*#__PURE__*/React.createElement(Input, {
    iconLeft: /*#__PURE__*/React.createElement(Search, null),
    placeholder: "Search signals, providers, IDs\u2026",
    trailing: /*#__PURE__*/React.createElement("span", {
      className: "vrs-input__kbd"
    }, "\u2318K")
  })), /*#__PURE__*/React.createElement("div", {
    className: "vrs-top__actions"
  }, /*#__PURE__*/React.createElement(Tooltip, {
    label: "Documentation",
    side: "bottom"
  }, /*#__PURE__*/React.createElement(IconButton, {
    label: "Docs"
  }, /*#__PURE__*/React.createElement(Docs, null))), /*#__PURE__*/React.createElement(Tooltip, {
    label: "Alerts",
    side: "bottom"
  }, /*#__PURE__*/React.createElement(IconButton, {
    label: "Alerts"
  }, /*#__PURE__*/React.createElement(Bell, null))), /*#__PURE__*/React.createElement(Button, {
    variant: "primary",
    size: "sm"
  }, "New feed")));
}
window.Topbar = Topbar;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/app/Topbar.jsx", error: String((e && e.message) || e) }); }

// ui_kits/app/app.data.jsx
try { (() => {
/* Verasig App — fake data + shared helpers (assigned to window). */
const VRS_DATA = function () {
  const providers = [{
    id: 'coinbase',
    name: 'Coinbase',
    tint: 'var(--viz-2)',
    channel: 'WebSocket',
    health: 'verified',
    uptime: 99.99
  }, {
    id: 'polymarket',
    name: 'Polymarket',
    tint: 'var(--viz-3)',
    channel: 'REST · us-east',
    health: 'verified',
    uptime: 99.94
  }, {
    id: 'caplight',
    name: 'Caplight',
    tint: 'var(--viz-4)',
    channel: 'gRPC',
    health: 'pending',
    uptime: 99.71
  }, {
    id: 'stork',
    name: 'Stork',
    tint: 'var(--viz-5)',
    channel: 'WebSocket',
    health: 'verified',
    uptime: 99.98
  }, {
    id: 'kalshi',
    name: 'Kalshi',
    tint: 'var(--viz-6)',
    channel: 'REST',
    health: 'rejected',
    uptime: 98.40
  }, {
    id: 'pyth',
    name: 'Pyth',
    tint: 'var(--viz-1)',
    channel: 'gRPC · global',
    health: 'verified',
    uptime: 99.97
  }];
  const signals = [{
    id: 'SIG-7F2A·0x9d4e',
    symbol: 'BTC/USD',
    provider: 'Coinbase',
    tint: 'var(--viz-2)',
    channel: 'WebSocket',
    confidence: 99.4,
    status: 'verified',
    time: '11:32:04',
    sources: 12,
    agree: 12
  }, {
    id: 'SIG-7F22·0x4c10',
    symbol: 'ETH/USD',
    provider: 'Pyth',
    tint: 'var(--viz-1)',
    channel: 'gRPC · global',
    confidence: 98.7,
    status: 'verified',
    time: '11:32:01',
    sources: 11,
    agree: 11
  }, {
    id: 'SIG-7F19·0x2b81',
    symbol: 'ELECTION-2028',
    provider: 'Polymarket',
    tint: 'var(--viz-3)',
    channel: 'REST · us-east',
    confidence: 62.0,
    status: 'pending',
    time: '11:31:58',
    sources: 14,
    agree: 9
  }, {
    id: 'SIG-7F11·0x88fa',
    symbol: 'USA500.idx',
    provider: 'Stork',
    tint: 'var(--viz-5)',
    channel: 'WebSocket',
    confidence: 96.2,
    status: 'verified',
    time: '11:31:50',
    sources: 9,
    agree: 9
  }, {
    id: 'SIG-7F03·0x77ac',
    symbol: 'AAPL.pre',
    provider: 'Caplight',
    tint: 'var(--viz-4)',
    channel: 'gRPC',
    confidence: 41.0,
    status: 'rejected',
    time: '11:30:51',
    sources: 8,
    agree: 3
  }, {
    id: 'SIG-7EF8·0x10dd',
    symbol: 'NVDA.pre',
    provider: 'Caplight',
    tint: 'var(--viz-4)',
    channel: 'gRPC',
    confidence: 84.5,
    status: 'verified',
    time: '11:30:39',
    sources: 8,
    agree: 7
  }, {
    id: 'SIG-7EE0·0x5a92',
    symbol: 'SB-FINALS-W',
    provider: 'Kalshi',
    tint: 'var(--viz-6)',
    channel: 'REST',
    confidence: 73.1,
    status: 'observing',
    time: '11:30:12',
    sources: 10,
    agree: 7
  }, {
    id: 'SIG-7ED4·0x3f6b',
    symbol: 'XAU/USD',
    provider: 'Pyth',
    tint: 'var(--viz-1)',
    channel: 'gRPC · global',
    confidence: 99.1,
    status: 'verified',
    time: '11:29:55',
    sources: 11,
    agree: 11
  }];
  const sources = [{
    name: 'Coinbase',
    value: '67,412.08',
    dev: '0.00%',
    ok: true
  }, {
    name: 'Binance',
    value: '67,409.51',
    dev: '−0.004%',
    ok: true
  }, {
    name: 'Kraken',
    value: '67,418.20',
    dev: '+0.009%',
    ok: true
  }, {
    name: 'Pyth',
    value: '67,411.94',
    dev: '0.00%',
    ok: true
  }, {
    name: 'Stork',
    value: '67,402.10',
    dev: '−0.015%',
    ok: true
  }, {
    name: 'CoinGecko',
    value: '67,512.40',
    dev: '+0.148%',
    ok: false
  }];
  return {
    providers,
    signals,
    sources
  };
}();
window.VRS_DATA = VRS_DATA;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/app/app.data.jsx", error: String((e && e.message) || e) }); }

// ui_kits/marketing/Hero.jsx
try { (() => {
/* Verasig Marketing — Hero */
function HeroTrace() {
  return /*#__PURE__*/React.createElement("svg", {
    className: "mk-hero__trace",
    viewBox: "0 0 520 120",
    fill: "none",
    preserveAspectRatio: "none"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M0 78 L60 78 L92 78 L120 96 L150 34 L182 64 L212 64 L260 64 L300 50 L340 70 L380 26 L430 56 L470 44 L520 44",
    stroke: "var(--signal-500)",
    strokeWidth: "2",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "520",
    cy: "44",
    r: "4",
    fill: "var(--signal-500)"
  }));
}
function Hero() {
  const {
    Button,
    StatusPill,
    ConfidenceBar
  } = window.VerasigDesignSystem_fd565b;
  const Arrow = () => /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 24 24",
    width: "16",
    height: "16",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: "2",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M5 12h14M13 6l6 6-6 6"
  }));
  return /*#__PURE__*/React.createElement("section", {
    className: "mk-hero v-lattice"
  }, /*#__PURE__*/React.createElement("div", {
    className: "mk-hero__glow"
  }), /*#__PURE__*/React.createElement("div", {
    className: "mk-hero__inner"
  }, /*#__PURE__*/React.createElement("div", {
    className: "mk-hero__copy"
  }, /*#__PURE__*/React.createElement("span", {
    className: "v-eyebrow mk-hero__eyebrow"
  }, /*#__PURE__*/React.createElement("span", {
    className: "mk-dot"
  }), "Signal verification infrastructure"), /*#__PURE__*/React.createElement("h1", {
    className: "mk-hero__title"
  }, "Trust", /*#__PURE__*/React.createElement("br", null), "every signal."), /*#__PURE__*/React.createElement("p", {
    className: "mk-hero__sub"
  }, "Verasig sits between your providers and the systems that act on them \u2014 cross-checking every signal across independent sources before it ever reaches production."), /*#__PURE__*/React.createElement("div", {
    className: "mk-hero__cta"
  }, /*#__PURE__*/React.createElement(Button, {
    variant: "primary",
    size: "lg",
    iconRight: /*#__PURE__*/React.createElement(Arrow, null)
  }, "Talk to us"), /*#__PURE__*/React.createElement(Button, {
    variant: "secondary",
    size: "lg"
  }, "Explore products")), /*#__PURE__*/React.createElement("div", {
    className: "mk-hero__meta"
  }, /*#__PURE__*/React.createElement("span", null, /*#__PURE__*/React.createElement("b", null, "4.1B+"), " signals verified"), /*#__PURE__*/React.createElement("span", {
    className: "mk-sep"
  }), /*#__PURE__*/React.createElement("span", null, /*#__PURE__*/React.createElement("b", null, "120+"), " providers"), /*#__PURE__*/React.createElement("span", {
    className: "mk-sep"
  }), /*#__PURE__*/React.createElement("span", null, /*#__PURE__*/React.createElement("b", null, "99.98%"), " uptime"))), /*#__PURE__*/React.createElement("div", {
    className: "mk-hero__panel"
  }, /*#__PURE__*/React.createElement("div", {
    className: "mk-panel"
  }, /*#__PURE__*/React.createElement("div", {
    className: "mk-panel__head"
  }, /*#__PURE__*/React.createElement("span", {
    className: "mk-mono"
  }, "SIG-7F2A \xB7 BTC/USD"), /*#__PURE__*/React.createElement(StatusPill, {
    status: "verified"
  })), /*#__PURE__*/React.createElement(HeroTrace, null), /*#__PURE__*/React.createElement("div", {
    className: "mk-panel__rows"
  }, /*#__PURE__*/React.createElement("div", {
    className: "mk-panel__row"
  }, /*#__PURE__*/React.createElement("span", {
    className: "mk-mono-f"
  }, "Sources"), /*#__PURE__*/React.createElement("span", {
    className: "mk-mono"
  }, "12 / 12 agreed")), /*#__PURE__*/React.createElement("div", {
    className: "mk-panel__row"
  }, /*#__PURE__*/React.createElement("span", {
    className: "mk-mono-f"
  }, "Latency"), /*#__PURE__*/React.createElement("span", {
    className: "mk-mono"
  }, "182\xA0ms")), /*#__PURE__*/React.createElement(ConfidenceBar, {
    value: 99.4,
    threshold: 80,
    label: "Confidence"
  }))), /*#__PURE__*/React.createElement("div", {
    className: "mk-panel mk-panel--ghost"
  }, /*#__PURE__*/React.createElement("div", {
    className: "mk-panel__head"
  }, /*#__PURE__*/React.createElement("span", {
    className: "mk-mono"
  }, "SIG-7F19 \xB7 ELECTION-2028"), /*#__PURE__*/React.createElement(StatusPill, {
    status: "pending",
    pulse: true
  })), /*#__PURE__*/React.createElement("div", {
    className: "mk-panel__rows"
  }, /*#__PURE__*/React.createElement("div", {
    className: "mk-panel__row"
  }, /*#__PURE__*/React.createElement("span", {
    className: "mk-mono-f"
  }, "Quorum"), /*#__PURE__*/React.createElement("span", {
    className: "mk-mono"
  }, "9 / 14 \xB7 holding")))))));
}
window.Hero = Hero;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/marketing/Hero.jsx", error: String((e && e.message) || e) }); }

// ui_kits/marketing/Nav.jsx
try { (() => {
/* Verasig Marketing — Nav */
function Nav() {
  const {
    Button
  } = window.VerasigDesignSystem_fd565b;
  return /*#__PURE__*/React.createElement("header", {
    className: "mk-nav"
  }, /*#__PURE__*/React.createElement("div", {
    className: "mk-nav__inner"
  }, /*#__PURE__*/React.createElement("a", {
    className: "mk-nav__brand",
    href: "#"
  }, /*#__PURE__*/React.createElement("svg", {
    width: "26",
    height: "26",
    viewBox: "0 0 40 40",
    fill: "none",
    style: {
      color: 'var(--signal-500)'
    }
  }, /*#__PURE__*/React.createElement("path", {
    d: "M4 22 L11 22 L17 30 L24 9 L30 18",
    stroke: "currentColor",
    strokeWidth: "3.2",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "30",
    cy: "18",
    r: "3.4",
    fill: "currentColor"
  })), /*#__PURE__*/React.createElement("span", null, "Verasig", /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--signal-500)'
    }
  }, "."))), /*#__PURE__*/React.createElement("nav", {
    className: "mk-nav__links"
  }, /*#__PURE__*/React.createElement("a", {
    href: "#products"
  }, "Products"), /*#__PURE__*/React.createElement("a", {
    href: "#why"
  }, "Why Verasig"), /*#__PURE__*/React.createElement("a", {
    href: "#providers"
  }, "Providers"), /*#__PURE__*/React.createElement("a", {
    href: "#docs"
  }, "Docs")), /*#__PURE__*/React.createElement("div", {
    className: "mk-nav__actions"
  }, /*#__PURE__*/React.createElement("a", {
    className: "mk-nav__signin",
    href: "#"
  }, "Sign in"), /*#__PURE__*/React.createElement(Button, {
    variant: "primary",
    size: "sm"
  }, "Talk to us"))));
}
window.Nav = Nav;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/marketing/Nav.jsx", error: String((e && e.message) || e) }); }

// ui_kits/marketing/Products.jsx
try { (() => {
/* Verasig Marketing — Products + Stats + Marquee */
function Products() {
  const {
    products
  } = window.VRS_SITE;
  const Arrow = () => /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 24 24",
    width: "15",
    height: "15",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: "2",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M5 12h14M13 6l6 6-6 6"
  }));
  return /*#__PURE__*/React.createElement("section", {
    className: "mk-sec",
    id: "products"
  }, /*#__PURE__*/React.createElement("div", {
    className: "mk-sec__head"
  }, /*#__PURE__*/React.createElement("span", {
    className: "v-eyebrow"
  }, /*#__PURE__*/React.createElement("span", {
    className: "mk-dot"
  }), "Products"), /*#__PURE__*/React.createElement("h2", {
    className: "mk-sec__title"
  }, "One integration.", /*#__PURE__*/React.createElement("br", null), "Every signal verified."), /*#__PURE__*/React.createElement("p", {
    className: "mk-sec__lead"
  }, "Compose the building blocks of trust \u2014 from ingestion to a signed, auditable decision.")), /*#__PURE__*/React.createElement("div", {
    className: "mk-products"
  }, products.map(p => /*#__PURE__*/React.createElement("a", {
    className: "mk-prod",
    key: p.id,
    href: "#"
  }, /*#__PURE__*/React.createElement("div", {
    className: "mk-prod__top"
  }, /*#__PURE__*/React.createElement("span", {
    className: "mk-prod__sw",
    style: {
      background: p.tint
    }
  }), /*#__PURE__*/React.createElement("span", {
    className: "mk-prod__name"
  }, p.name)), /*#__PURE__*/React.createElement("div", {
    className: "mk-prod__tag"
  }, p.tagline), /*#__PURE__*/React.createElement("p", {
    className: "mk-prod__body"
  }, p.body), /*#__PURE__*/React.createElement("div", {
    className: "mk-prod__foot"
  }, /*#__PURE__*/React.createElement("div", {
    className: "mk-prod__stat"
  }, /*#__PURE__*/React.createElement("span", {
    className: "mk-prod__statv",
    style: {
      color: p.tint
    }
  }, p.stat), /*#__PURE__*/React.createElement("span", {
    className: "mk-prod__statl"
  }, p.statLabel)), /*#__PURE__*/React.createElement("span", {
    className: "mk-prod__more"
  }, "Learn more ", /*#__PURE__*/React.createElement(Arrow, null)))))));
}
window.Products = Products;
function Stats() {
  const {
    stats
  } = window.VRS_SITE;
  return /*#__PURE__*/React.createElement("section", {
    className: "mk-stats"
  }, /*#__PURE__*/React.createElement("div", {
    className: "mk-stats__inner"
  }, stats.map(s => /*#__PURE__*/React.createElement("div", {
    className: "mk-stat",
    key: s.label
  }, /*#__PURE__*/React.createElement("div", {
    className: "mk-stat__v"
  }, s.value), /*#__PURE__*/React.createElement("div", {
    className: "mk-stat__l"
  }, s.label)))));
}
window.Stats = Stats;
function Marquee() {
  const {
    providers
  } = window.VRS_SITE;
  const loop = [...providers, ...providers];
  return /*#__PURE__*/React.createElement("section", {
    className: "mk-marquee",
    id: "providers"
  }, /*#__PURE__*/React.createElement("div", {
    className: "mk-marquee__label v-eyebrow"
  }, "Verifying signals from"), /*#__PURE__*/React.createElement("div", {
    className: "mk-marquee__viewport"
  }, /*#__PURE__*/React.createElement("div", {
    className: "mk-marquee__track"
  }, loop.map((p, i) => /*#__PURE__*/React.createElement("span", {
    className: "mk-chip",
    key: i
  }, p)))));
}
window.Marquee = Marquee;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/marketing/Products.jsx", error: String((e && e.message) || e) }); }

// ui_kits/marketing/Site.jsx
try { (() => {
/* Verasig Marketing — page composition */
function Site() {
  const {
    Nav,
    Hero,
    Products,
    Stats,
    Marquee,
    Why,
    CTA,
    Footer
  } = window;
  return /*#__PURE__*/React.createElement("div", {
    className: "mk-page"
  }, /*#__PURE__*/React.createElement(Nav, null), /*#__PURE__*/React.createElement(Hero, null), /*#__PURE__*/React.createElement(Marquee, null), /*#__PURE__*/React.createElement(Products, null), /*#__PURE__*/React.createElement(Stats, null), /*#__PURE__*/React.createElement(Why, null), /*#__PURE__*/React.createElement(CTA, null), /*#__PURE__*/React.createElement(Footer, null));
}
window.Site = Site;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/marketing/Site.jsx", error: String((e && e.message) || e) }); }

// ui_kits/marketing/Why.jsx
try { (() => {
/* Verasig Marketing — Why + CTA + Footer */
const MK_WHY_ICONS = {
  pulse: /*#__PURE__*/React.createElement("path", {
    d: "M3 12h4l2 6 4-14 3 10 2-4h3"
  }),
  sources: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("circle", {
    cx: "6",
    cy: "6",
    r: "2.5"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "18",
    cy: "6",
    r: "2.5"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "12",
    cy: "18",
    r: "2.5"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M7.7 7.7 11 15M16.3 7.7 13 15"
  })),
  tune: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("path", {
    d: "M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M1 14h6M9 8h6M17 16h6"
  })),
  shield: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("path", {
    d: "M12 3 4 6v6c0 5 3.5 7.5 8 9 4.5-1.5 8-4 8-9V6l-8-3Z"
  }), /*#__PURE__*/React.createElement("path", {
    d: "m9 12 2 2 4-4"
  }))
};
function Why() {
  const {
    why
  } = window.VRS_SITE;
  return /*#__PURE__*/React.createElement("section", {
    className: "mk-sec",
    id: "why"
  }, /*#__PURE__*/React.createElement("div", {
    className: "mk-sec__head"
  }, /*#__PURE__*/React.createElement("span", {
    className: "v-eyebrow"
  }, /*#__PURE__*/React.createElement("span", {
    className: "mk-dot"
  }), "Why Verasig"), /*#__PURE__*/React.createElement("h2", {
    className: "mk-sec__title"
  }, "The trust layer", /*#__PURE__*/React.createElement("br", null), "signals were missing.")), /*#__PURE__*/React.createElement("div", {
    className: "mk-why"
  }, why.map(w => /*#__PURE__*/React.createElement("div", {
    className: "mk-why__item",
    key: w.title
  }, /*#__PURE__*/React.createElement("span", {
    className: "mk-why__ic"
  }, /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 24 24",
    width: "22",
    height: "22",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: "1.7",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }, MK_WHY_ICONS[w.icon])), /*#__PURE__*/React.createElement("div", {
    className: "mk-why__t"
  }, w.title), /*#__PURE__*/React.createElement("p", {
    className: "mk-why__b"
  }, w.body)))));
}
window.Why = Why;
function CTA() {
  const {
    Button
  } = window.VerasigDesignSystem_fd565b;
  const Arrow = () => /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 24 24",
    width: "16",
    height: "16",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: "2",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M5 12h14M13 6l6 6-6 6"
  }));
  const Book = () => /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 24 24",
    width: "16",
    height: "16",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: "1.8",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M4 19.5A2.5 2.5 0 0 1 6.5 17H20M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"
  }));
  return /*#__PURE__*/React.createElement("section", {
    className: "mk-cta v-lattice"
  }, /*#__PURE__*/React.createElement("div", {
    className: "mk-cta__glow"
  }), /*#__PURE__*/React.createElement("div", {
    className: "mk-cta__inner"
  }, /*#__PURE__*/React.createElement("h2", {
    className: "mk-cta__title"
  }, "Tell us what you're verifying."), /*#__PURE__*/React.createElement("p", {
    className: "mk-cta__sub"
  }, "From market data to device telemetry to real-world outcomes \u2014 bring us the signal, we'll bring it to production."), /*#__PURE__*/React.createElement("div", {
    className: "mk-cta__btns"
  }, /*#__PURE__*/React.createElement(Button, {
    variant: "primary",
    size: "lg",
    iconRight: /*#__PURE__*/React.createElement(Arrow, null)
  }, "Talk to us"), /*#__PURE__*/React.createElement(Button, {
    variant: "secondary",
    size: "lg",
    iconLeft: /*#__PURE__*/React.createElement(Book, null)
  }, "Read the docs"))));
}
window.CTA = CTA;
function Footer() {
  const cols = [{
    h: 'Products',
    links: ['Verify', 'Quorum', 'Channels', 'Provenance']
  }, {
    h: 'Developers',
    links: ['Docs', 'API reference', 'Status', 'Changelog']
  }, {
    h: 'Company',
    links: ['About', 'Customers', 'Careers', 'Contact']
  }];
  return /*#__PURE__*/React.createElement("footer", {
    className: "mk-foot"
  }, /*#__PURE__*/React.createElement("div", {
    className: "mk-foot__inner"
  }, /*#__PURE__*/React.createElement("div", {
    className: "mk-foot__brand"
  }, /*#__PURE__*/React.createElement("a", {
    className: "mk-nav__brand",
    href: "#"
  }, /*#__PURE__*/React.createElement("svg", {
    width: "24",
    height: "24",
    viewBox: "0 0 40 40",
    fill: "none",
    style: {
      color: 'var(--signal-500)'
    }
  }, /*#__PURE__*/React.createElement("path", {
    d: "M4 22 L11 22 L17 30 L24 9 L30 18",
    stroke: "currentColor",
    strokeWidth: "3.2",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "30",
    cy: "18",
    r: "3.4",
    fill: "currentColor"
  })), /*#__PURE__*/React.createElement("span", null, "Verasig", /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--signal-500)'
    }
  }, "."))), /*#__PURE__*/React.createElement("p", {
    className: "mk-foot__tag"
  }, "The trust layer for signals.")), /*#__PURE__*/React.createElement("div", {
    className: "mk-foot__cols"
  }, cols.map(c => /*#__PURE__*/React.createElement("div", {
    className: "mk-foot__col",
    key: c.h
  }, /*#__PURE__*/React.createElement("div", {
    className: "mk-foot__h"
  }, c.h), c.links.map(l => /*#__PURE__*/React.createElement("a", {
    key: l,
    href: "#"
  }, l)))))), /*#__PURE__*/React.createElement("div", {
    className: "mk-foot__bar"
  }, /*#__PURE__*/React.createElement("span", null, "\xA9 2026 Verasig, Inc."), /*#__PURE__*/React.createElement("span", {
    className: "mk-foot__legal"
  }, /*#__PURE__*/React.createElement("a", {
    href: "#"
  }, "Privacy"), /*#__PURE__*/React.createElement("a", {
    href: "#"
  }, "Terms"), /*#__PURE__*/React.createElement("a", {
    href: "#"
  }, "Security"))));
}
window.Footer = Footer;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/marketing/Why.jsx", error: String((e && e.message) || e) }); }

// ui_kits/marketing/site.data.jsx
try { (() => {
/* Verasig Marketing — content data */
const VRS_SITE = {
  products: [{
    id: 'verify',
    name: 'Verify',
    tint: 'var(--viz-1)',
    tagline: 'Cross-check any signal in milliseconds.',
    body: 'Every inbound signal is checked against independent sources, scored for confidence, and verified before it reaches production.',
    stat: '< 200ms',
    statLabel: 'Median verification'
  }, {
    id: 'quorum',
    name: 'Quorum',
    tint: 'var(--viz-2)',
    tagline: 'Consensus on your terms.',
    body: 'Configure thresholds, source weighting and tolerance. Hold or reject anything that fails to reach quorum — automatically.',
    stat: '99.6%',
    statLabel: 'Quorum rate'
  }, {
    id: 'channels',
    name: 'Channels',
    tint: 'var(--viz-5)',
    tagline: 'Ingest from anywhere.',
    body: 'Webhook, REST, gRPC or WebSocket. One integration ingests every provider and every channel through a single endpoint.',
    stat: '4',
    statLabel: 'Transport channels'
  }, {
    id: 'provenance',
    name: 'Provenance',
    tint: 'var(--viz-3)',
    tagline: 'A signed, auditable trail.',
    body: 'Every verification is signed and logged with its sources, timing and decision — a tamper-evident record you can replay.',
    stat: '100%',
    statLabel: 'Signals signed'
  }],
  stats: [{
    value: '4.1B+',
    label: 'Signals verified'
  }, {
    value: '99.98%',
    label: 'Uptime'
  }, {
    value: '182ms',
    label: 'Median latency'
  }, {
    value: '120+',
    label: 'Connected providers'
  }],
  providers: ['Coinbase', 'Pyth', 'Polymarket', 'Kalshi', 'Caplight', 'Stork', 'Binance', 'Kraken', 'dxFeed', 'CoinGecko', 'Finage', 'Blocksize'],
  why: [{
    icon: 'pulse',
    title: 'Signals that never sleep',
    body: 'Always-on verification across markets, telemetry and events — 365 days a year, sub-second.'
  }, {
    icon: 'sources',
    title: 'Sources others can\u2019t reach',
    body: 'If a provider exists — public or private, push or pull — Verasig can ingest and verify it.'
  }, {
    icon: 'tune',
    title: 'Verification you control',
    body: 'Bespoke quorum logic: source selection, weighting, smoothing and tolerance. No one-size-fits-all.'
  }, {
    icon: 'shield',
    title: 'Tamper-evident by default',
    body: 'Signed provenance for every signal. Replay any decision with its full source breakdown.'
  }]
};
window.VRS_SITE = VRS_SITE;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/marketing/site.data.jsx", error: String((e && e.message) || e) }); }

__ds_ns.Avatar = __ds_scope.Avatar;

__ds_ns.Badge = __ds_scope.Badge;

__ds_ns.Button = __ds_scope.Button;

__ds_ns.IconButton = __ds_scope.IconButton;

__ds_ns.Tabs = __ds_scope.Tabs;

__ds_ns.Tag = __ds_scope.Tag;

__ds_ns.Card = __ds_scope.Card;

__ds_ns.ConfidenceBar = __ds_scope.ConfidenceBar;

__ds_ns.MetricStat = __ds_scope.MetricStat;

__ds_ns.SignalRow = __ds_scope.SignalRow;

__ds_ns.StatusPill = __ds_scope.StatusPill;

__ds_ns.Banner = __ds_scope.Banner;

__ds_ns.Dialog = __ds_scope.Dialog;

__ds_ns.Toast = __ds_scope.Toast;

__ds_ns.ToastStack = __ds_scope.ToastStack;

__ds_ns.Tooltip = __ds_scope.Tooltip;

__ds_ns.Checkbox = __ds_scope.Checkbox;

__ds_ns.Input = __ds_scope.Input;

__ds_ns.Select = __ds_scope.Select;

__ds_ns.Switch = __ds_scope.Switch;

})();
