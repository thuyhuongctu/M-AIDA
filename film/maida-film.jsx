const { useComposition, CompositionStage, Easing, interpolate, clamp } = window;

const C = {
  canvas: '#f6f1e7', s1: '#fbf8f1', hair: '#ded5c4', hairS: '#c4b8a1',
  ink: '#1a1714', muted: '#5c554b', subtle: '#8b8377',
  proposed: '#8b8377', verified: '#3f7a5a', locked: '#c0862a', flagged: '#a8452a',
  cCanvas: '#171a19', cSurf: '#202523', cInk: '#e8e4d9', cMuted: '#a8a396', cHair: '#333a37',
};
const F = {
  display: '"Source Serif 4", "Noto Serif", Georgia, serif',
  body: 'Inter, -apple-system, "Segoe UI", Roboto, Arial, sans-serif',
  mono: '"JetBrains Mono", Consolas, monospace',
  app: 'system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
  appMono: 'Menlo, Consolas, monospace',
};

// ---- motion: the only three curves in the piece ----
const p01 = (T, s, d) => clamp((T - s) / d, 0, 1);
const MOTION = {
  enter: (T, s, d = 0.7) => Easing.easeOutCubic(p01(T, s, d)),
  draw: (T, s, d = 1) => Easing.easeInOutCubic(p01(T, s, d)),
  pop: (T, s, d = 0.45) => Easing.easeOutBack(p01(T, s, d)),
};
const kf = (T, pts) => interpolate(pts.map(p => p[0]), pts.map(p => p[1]), Easing.easeInOutCubic)(T);
const mix = (a, b, p) => a + (b - a) * p;
const hex = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
const lerpC = (a, b, p) => { const A = hex(a), B = hex(b); return `rgb(${A.map((v, i) => Math.round(v + (B[i] - v) * p)).join(',')})`; };
const typed = (s, T, t0, d) => s.slice(0, Math.round(s.length * p01(T, t0, d)));
const inWin = (T, a, b) => T >= a && T < b;

// ---- brand mark (paths from assets/brand/maida-mark.svg, in 48-unit space) ----
function Mark({ T, t0, width }) {
  const axis = MOTION.draw(T, t0, 0.7), left = MOTION.draw(T, t0 + 0.4, 0.9), amb = MOTION.enter(T, t0 + 1.2, 0.7);
  return (
    <svg viewBox="0 10 48 28" width={width} height={width * 28 / 48} style={{ display: 'block', overflow: 'visible' }}>
      <g opacity={axis > 0.01 ? 1 : 0} stroke={C.hairS} strokeWidth="1.6" strokeLinecap="round">
        <line x1="10" y1="24" x2={10 - 9 * axis} y2="24" />
        <line x1="38" y1="24" x2={38 + 9 * axis} y2="24" />
      </g>
      <path d="M10 24 L24 14 L24 34 Z" fill="none" stroke={C.ink} strokeWidth="2" strokeLinejoin="round"
        pathLength="1" strokeDasharray="1" strokeDashoffset={1 - left} opacity={left > 0.01 ? 1 : 0} />
      <path d="M24 14 L38 24 L24 34 Z" fill={C.locked} opacity={amb} transform={`translate(${(1 - amb) * 10} 0)`} />
    </svg>
  );
}

// ---- forest plot (no values, no axis numbers) ----
const ROWS = [[0.18, 0.12], [0.32, 0.2], [-0.05, 0.14], [0.26, 0.1], [0.12, 0.16], [0.40, 0.22], [0.08, 0.09], [0.22, 0.13]];
function Forest({ T, left, top, rowsAt, lockAt, poolAt, fillAt, opacity = 1, dx = 0 }) {
  const PW = 560, X = v => (v + 0.3) / 0.9 * PW, RY = 62;
  const py = ROWS.length * RY + 34;
  const pd = MOTION.draw(T, poolAt, 1.0);
  const pf = fillAt != null ? MOTION.enter(T, fillAt, 0.8) : 0;
  return (
    <div style={{ position: 'absolute', left, top, width: PW + 110, height: py + 40, opacity, transform: `translateX(${dx}px)` }}>
      {ROWS.map((r, i) => (
        <div key={i} style={{ position: 'absolute', left: 0, top: i * RY + 20 - 13, font: `400 18px/26px ${F.mono}`, whiteSpace: 'nowrap', color: C.subtle, opacity: MOTION.enter(T, rowsAt + i * 0.22, 0.5) }}>Study {i + 1}</div>
      ))}
      <svg width={PW + 110} height={py + 40} style={{ position: 'absolute', left: 0, top: 0, overflow: 'visible' }}>
        <g transform="translate(110,0)">
          <line x1={X(0)} x2={X(0)} y1={-12} y2={py + 26} stroke={C.hairS} strokeWidth="1.5" strokeDasharray="4 6" opacity={MOTION.enter(T, rowsAt - 0.3, 0.6)} />
          <line x1={0} x2={PW} y1={py - 30} y2={py - 30} stroke={C.hair} strokeWidth="1" opacity={pd} />
          {ROWS.map(([c, hw], i) => {
            const a = MOTION.enter(T, rowsAt + i * 0.22, 0.5);
            const lk = lockAt != null ? MOTION.enter(T, lockAt + i * 0.14, 0.4) : 0;
            const col = lerpC(C.proposed, C.locked, lk);
            const cy = i * RY + 20, s = 12 + (0.24 - hw) * 80;
            return (
              <g key={i} opacity={a}>
                <line x1={X(c - hw * a)} x2={X(c + hw * a)} y1={cy} y2={cy} stroke={col} strokeWidth="2.5" />
                <rect x={X(c) - s / 2} y={cy - s / 2} width={s} height={s} fill={col} />
              </g>
            );
          })}
          <path d={`M${X(0.12)} ${py} L${X(0.19)} ${py - 15} L${X(0.26)} ${py} L${X(0.19)} ${py + 15} Z`}
            fill={C.locked} fillOpacity={pf} stroke={lerpC(C.proposed, C.locked, pf)} strokeWidth="2"
            strokeDasharray={pf > 0 ? 'none' : '5 5'} opacity={pd} strokeLinejoin="round" />
        </g>
      </svg>
    </div>
  );
}

function Huong({ src, T, inAt, outAt, left, height, width }) {
  const a = MOTION.enter(T, inAt, 0.9) * (1 - MOTION.enter(T, outAt, 0.6));
  const bob = Math.sin(T * 1.3) * 4;
  return <img src={src} alt="" style={{ position: 'absolute', left, top: 1080 - height + 20, height, width, objectFit: 'contain', opacity: a, transform: `translate(${(1 - MOTION.enter(T, inAt, 0.9)) * 80}px, ${bob}px)` }} />;
}

// ================= Mark (opening) =================
function MarkSection({ T, Q }) {
  const move = MOTION.draw(T, Q - 0.6, 1.0);
  const drift = 1 + 0.03 * p01(T, 0, 6);
  const out = 1 - MOTION.enter(T, Q - 0.6, 0.5);
  const bugOut = 1 - MOTION.enter(T, Q + 8.3, 0.6);
  const w = mix(300, 84, move), cx = mix(960, 130, move), cy = mix(360, 78, move);
  return (
    <div>
      <div style={{ position: 'absolute', left: cx - w / 2, top: cy - w * 28 / 96, opacity: bugOut, transform: `scale(${mix(drift, 1, move)})` }}>
        <Mark T={T} t0={0.3} width={w} />
      </div>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 500, textAlign: 'center', opacity: out, transform: `scale(${drift})` }}>
        <div style={{ font: `600 132px/1.12 ${F.display}`, letterSpacing: '-1.2px', color: C.ink, opacity: MOTION.enter(T, 2.0, 0.8), transform: `translateY(${(1 - MOTION.enter(T, 2.0, 0.8)) * 24}px)` }}>M-AIDA</div>
        <div style={{ font: `400 34px/1.4 ${F.body}`, color: C.muted, marginTop: 16, opacity: MOTION.enter(T, 2.6, 0.7) }}>Meta-Analysis Intelligent Data Assistant</div>
        <div style={{ font: `400 20px/1.4 ${F.mono}`, letterSpacing: '1.8px', textTransform: 'uppercase', color: C.subtle, marginTop: 40, opacity: MOTION.enter(T, 3.3, 0.7) }}>PhD Dissertation Research Tool · Asia-Pacific I→P Meta-Analysis</div>
      </div>
    </div>
  );
}

// ================= Question =================
function QuestionSection({ T, Q, X, tw }) {
  const out = MOTION.draw(T, X - 0.6, 0.7);
  const op = T < Q - 0.2 ? 0 : 1 - out;
  const line = (at) => ({ opacity: MOTION.enter(T, at, 0.8), transform: `translateY(${(1 - MOTION.enter(T, at, 0.8)) * 20}px)` });
  return (
    <div style={{ opacity: op }}>
      <div style={{ position: 'absolute', left: 140, top: 250, width: 640, transform: `translateX(${-out * 60}px)` }}>
        <div style={{ font: `600 80px/1.12 ${F.display}`, letterSpacing: '-1.2px', color: C.ink, ...line(Q + 0.4) }}>Many studies.</div>
        <div style={{ font: `600 80px/1.12 ${F.display}`, letterSpacing: '-1.2px', color: C.ink, ...line(Q + 1.1) }}>One question.</div>
        <div style={{ font: `400 30px/1.5 ${F.body}`, color: C.muted, marginTop: 40, textWrap: 'pretty', ...line(Q + 2.0) }}>Does internationalization improve firm performance? Each paper reports its answer in its own statistic.</div>
        <div style={{ font: `400 30px/1.5 ${F.body}`, color: C.ink, marginTop: 28, textWrap: 'pretty', ...line(Q + 5.2) }}>Every effect has to be found in the PDF, converted, and checked before it can be pooled.</div>
      </div>
      <Forest T={T} left={820} top={230} rowsAt={Q + 1.8} poolAt={Q + 4.4} dx={-out * 60} />
      {tw.showHuong && <Huong src="assets/img/huong/present_clean.png" T={T} inAt={Q + 0.9} outAt={X - 0.8} left={1440} height={860} width={482} />}
    </div>
  );
}

// ================= App recreation (frontend/src) =================
const A = {
  blue: '#2563eb', text: '#1a202c', gray: '#718096', gray2: '#4a5568', border: '#e2e8f0', inBorder: '#cbd5e0',
};
const badgeS = { display: 'inline-block', padding: '2.4px 8.8px', borderRadius: 12, fontSize: 12, fontWeight: 700, lineHeight: '18px' };
const BADGE = {
  success: { background: '#d1fae5', color: '#065f46' },
  medium: { background: '#fef3c7', color: '#92400e' },
  low: { background: '#fee2e2', color: '#991b1b' },
};
function Badge({ tone, children, scale = 1 }) { return <span style={{ ...badgeS, ...BADGE[tone], transform: `scale(${scale})`, transformOrigin: 'left center' }}>{children}</span>; }
function Pill({ label, tone, value }) {
  return <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6.4, whiteSpace: 'nowrap' }}>
    <span style={{ color: '#475569', fontWeight: 600, letterSpacing: '0.01em' }}>{label}</span><Badge tone={tone}>{value}</Badge></span>;
}
function Input({ value, placeholder, w = '100%', h = 34, sm }) {
  return <div style={{ width: w, height: h, boxSizing: 'border-box', padding: sm ? '4.8px 8px' : '7.2px 10.4px', border: `1px solid ${A.inBorder}`, borderRadius: 5, fontSize: sm ? 13.3 : 14.1, background: '#fff', color: value ? A.text : '#a0aec0', display: 'flex', alignItems: 'center', whiteSpace: 'nowrap', overflow: 'hidden' }}>{value || placeholder}</div>;
}
function Select({ value, dirty }) {
  return <div style={{ height: 28, boxSizing: 'border-box', padding: '4.8px 8px', border: `1px solid ${A.inBorder}`, borderRadius: 5, fontSize: 13.3, background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}><span>{value || '-'}</span><span style={{ fontSize: 10, color: A.gray2 }}>▼</span></div>;
}
function FormRow({ label, children }) {
  return <div style={{ display: 'flex', flexDirection: 'column', gap: 4.8, height: 59 }}><label style={{ fontSize: 13.1, fontWeight: 600, color: A.gray2, lineHeight: '20px', height: 20 }}>{label}</label>{children}</div>;
}
function Btn({ kind = 'primary', children, disabled, pressed }) {
  const bg = { primary: A.blue, danger: '#dc2626', secondary: '#6b7280' }[kind];
  return <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', height: 36, boxSizing: 'border-box', padding: '8px 17.6px', borderRadius: 6, fontSize: 14.1, fontWeight: 600, background: pressed ? '#1d4ed8' : bg, color: '#fff', opacity: disabled ? 0.55 : 1, transform: `scale(${pressed ? 0.96 : 1})` }}>{children}</span>;
}

const RESULT = [['Effect r', '0.2157'], ['N', '186'], ['t', '2.964'], ['beta', '-'], ['p-value', '0.0034'], ['DOI measure', 'FSTS'], ['Performance', 'ACC'], ['ICRV regime', '-'], ['DPL phase', '-']];

function ExtractTab({ s, T }) {
  const dz = s.dropped ? { border: '2px dashed #059669', background: '#ecfdf5' } : s.dragOver ? { border: `2px dashed ${A.blue}`, background: '#eff6ff' } : { border: `2px dashed ${A.inBorder}`, background: 'transparent' };
  return (
    <div>
      <div style={{ background: '#fff', border: `1px solid ${A.border}`, borderRadius: 8, padding: 24 }}>
        <h2 style={{ margin: '0 0 16px', fontSize: 17.6, fontWeight: 700, lineHeight: '26px', color: A.text }}>Extract Effect Size from PDF</h2>
        <div style={{ ...dz, borderRadius: 8, height: 104, boxSizing: 'border-box', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 20 }}>
          <p style={{ margin: 0, fontSize: 14.4, color: s.dropped ? '#065f46' : A.gray, fontWeight: s.dropped ? 600 : 400 }}>{s.dropped ? 'sample_t_statistic.pdf (842.3 KB)' : 'Drop a PDF here, or click to browse'}</p>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <FormRow label="Paper Title"><Input value={s.title} placeholder="Full paper title" /></FormRow>
          <FormRow label="Authors"><Input value={s.authors} placeholder="Last, F. M.; Last2, F." /></FormRow>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <FormRow label="Year"><Input value="2026" /></FormRow>
            <FormRow label="Country / Region"><Input value={s.country} placeholder="e.g. China, ASEAN" /></FormRow>
          </div>
          <div><Btn disabled={!s.dropped || s.loading} pressed={s.pressExtract}>{s.loading ? 'Extracting…' : 'Extract Effect Size'}</Btn></div>
        </div>
        {s.result > 0 && (
          <div style={{ marginTop: 24, border: `1px solid ${A.border}`, borderRadius: 8, padding: 20, background: '#f8fafc', opacity: s.result, transform: `translateY(${(1 - s.result) * 10}px)` }}>
            <h3 style={{ margin: '0 0 4px', fontSize: 16, fontWeight: 700, lineHeight: '24px' }}>sample_t_statistic</h3>
            <p style={{ margin: '0 0 12px', fontSize: 13.1, color: A.gray, lineHeight: '20px' }}>Sample, A. · 2026 · Vietnam</p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 8, marginBottom: 12 }}>
              {RESULT.map(([k, v], i) => (
                <div key={k} style={{ background: '#fff', border: `1px solid ${A.border}`, borderRadius: 5, padding: '6.4px 10.4px', height: 52, boxSizing: 'border-box', opacity: MOTION.enter(T, s.resultAt + 0.15 + i * 0.08, 0.35) }}>
                  <span style={{ display: 'block', fontSize: 11.5, color: A.gray, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.03em', lineHeight: '16px' }}>{k}</span>
                  <span style={{ fontSize: 14.4, fontWeight: 500, lineHeight: '20px' }}>{v}</span>
                </div>
              ))}
            </div>
            <div style={{ display: 'flex', gap: 8, height: 22 }}>
              <Badge tone="low" scale={MOTION.pop(T, s.resultAt + 1.1)}>68%</Badge>
              <Badge tone="low" scale={MOTION.pop(T, s.resultAt + 1.5)}>Needs PI Review</Badge>
            </div>
          </div>
        )}
      </div>
      {s.count > 0 && (
        <div style={{ marginTop: 16, display: 'flex', alignItems: 'center', gap: 16, padding: '12px 16px', background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 6, fontSize: 14.1, color: '#1e40af', height: 48, boxSizing: 'border-box' }}>
          <p style={{ margin: 0 }}>1 paper extracted this session.</p>
          <span style={{ color: A.blue, textDecoration: 'underline', fontSize: 14.1 }}>Go to Verify &amp; Lock</span>
        </div>
      )}
    </div>
  );
}

const STUDIES = [
  { t: 'sample_t_statistic', y: 2026, c: 'Vietnam', r: '0.216', n: 186, cf: 68, ic: null, dp: null, st: 'new' },
  { t: 'Phan et al. (2020)', y: 2020, c: 'Vietnam', r: '-0.011', n: 114, cf: 95, ic: 'III', dp: 'FOL', st: 'locked' },
  { t: 'Gaur, Kumar & Singh (2014)', y: 2014, c: 'India', r: '0.090', n: 240, cf: 94, ic: 'III', dp: 'SPN', st: 'locked' },
  { t: 'Freixanet, Renart & Segarra-Blasco (…', y: 2022, c: 'Spain', r: '0.080', n: 892, cf: 91, ic: 'II', dp: 'FOL', st: 'locked' },
  { t: 'Contractor, Kundu & Hsu (2003)', y: 2003, c: 'Multi/Service', r: '0.070', n: 103, cf: 92, ic: 'I', dp: 'PRE', st: 'approved' },
  { t: 'Grant (1987)', y: 1987, c: 'UK', r: '0.145', n: 304, cf: 96, ic: 'I', dp: 'PRE', st: 'approved' },
];
const FIELDS = [
  ['Effect r', '0.2157'], ['t-statistic', '2.964'], ['Beta (β)', null], ['df', '180'],
  ['Predictors p (for t/β from a regression; df = n − p − 1)', '5'], ['N (sample size)', '186'], ['p-value', '0.0034'],
  ['CI lower', null], ['CI upper', null], ['DOI measure', 'FSTS', 'sel'], ['Performance measure', 'ACC', 'sel'],
  ['ICRV regime (PI-assigned: WGI lookup)', null, 'sel', 'icrv'], ['DPL phase (PI-derived: median year)', null, 'sel', 'dpl'],
  ['cDAI 0-1 (PI-assigned: WB DAI/ITU DDI)', null],
];
const th = { textAlign: 'left', padding: '6.4px 9.6px', background: '#f1f5f9', borderBottom: `2px solid ${A.border}`, fontSize: 12, fontWeight: 700, textTransform: 'uppercase', color: A.gray2 };
const td = { padding: '0 9.6px', borderBottom: '1px solid #f1f5f9', verticalAlign: 'middle' };
const lbl = { fontSize: 11.5, color: A.gray, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.03em' };

function VerifyPanel({ s }) {
  const derived = [['Metric type', 'partial', 'Estimand source', 'observed'], ['r source', 'derived', 'df source', 'derived'], ['Variance of r', '0.004914', 'Formula', '(1 - r^2)^2 / (n - 1)'], ['Variance of z', '0.005464', 'Source controls', 'yes'], ['λ term applied (β ≥ 0)', 'no', 'β outside P&B domain', 'no']];
  const sub = { fontSize: 14.4, fontWeight: 600, margin: '16px 0 6.4px', color: '#334155', height: 22, lineHeight: '22px' };
  return (
    <div style={{ background: '#fff', border: `1px solid ${A.border}`, borderRadius: 8, maxHeight: 731, overflow: 'hidden', boxSizing: 'border-box' }}>
      <div style={{ padding: 24, transform: `translateY(${-s.innerS}px)` }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 34, marginBottom: 8 }}>
          <h2 style={{ margin: 0, fontSize: 17.6, fontWeight: 700 }}>PI Verification</h2><span style={{ fontSize: 16, color: A.gray }}>✕</span>
        </div>
        <p style={{ fontSize: 13.6, color: A.gray2, margin: '0 0 16px', height: 40, lineHeight: '20px' }}><strong>sample_t_statistic</strong> - Sample, A. (2026)</p>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13.4, tableLayout: 'fixed', marginBottom: 16 }}>
          <colgroup><col style={{ width: '44%' }} /><col style={{ width: '22%' }} /><col style={{ width: '34%' }} /></colgroup>
          <thead><tr style={{ height: 30 }}><th style={th}>Field</th><th style={th}>Extracted</th><th style={th}>Override</th></tr></thead>
          <tbody>
            {FIELDS.map(([l, v, kind, key]) => {
              const ov = key ? s.ov[key] : null;
              return (
                <tr key={l} style={{ height: 40, background: ov ? '#fffbeb' : 'transparent' }}>
                  <td style={{ ...td, ...lbl, lineHeight: '14px' }}>{l}</td>
                  <td style={{ ...td, color: A.gray, fontFamily: F.appMono, fontSize: 13.1 }}>{v ?? '-'}</td>
                  <td style={td}>{kind === 'sel' ? <Select value={ov || v} /> : <Input sm h={28} value={v} />}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <h3 style={sub}>Derived by the server (recomputed after each override)</h3>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13.4, marginBottom: 16 }}><tbody>
          {derived.map(r => <tr key={r[0]} style={{ height: 33 }}><td style={{ ...td, ...lbl }}>{r[0]}</td><td style={td}>{r[1]}</td><td style={{ ...td, ...lbl }}>{r[2]}</td><td style={td}>{r[2] === 'Formula' ? <code style={{ fontSize: 12.8 }}>{r[3]}</code> : r[3]}</td></tr>)}
        </tbody></table>
        <h3 style={sub}>Machine proposal (immutable)</h3>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13.4, marginBottom: 16 }}><tbody>
          <tr style={{ height: 33 }}><td style={{ ...td, ...lbl }}>Extraction confidence</td><td style={td}>0.680</td><td style={{ ...td, ...lbl }}>Requires verification</td><td style={td}>yes</td></tr>
          <tr style={{ height: 33 }}><td style={{ ...td, ...lbl }}>Evidence (effect)</td><td colSpan={3} style={td}>“t(180) = 2.964, p &lt; .01” (p. 7)</td></tr>
          <tr style={{ height: 33 }}><td style={{ ...td, ...lbl }}>Evidence (N)</td><td colSpan={3} style={td}>“186 firms” (p. 4)</td></tr>
        </tbody></table>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4.8, marginTop: 16, marginBottom: 12 }}>
          <label style={{ fontSize: 13.1, fontWeight: 600, color: A.gray2, height: 20 }}>PI Notes</label>
          <div style={{ height: 100, border: `1px solid ${A.inBorder}`, borderRadius: 5, padding: '7.2px 10.4px', fontSize: 14.1, color: '#a0aec0', boxSizing: 'border-box' }}>Add notes about decisions, ambiguities, or exclusion rationale…</div>
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, marginTop: 16 }}>
          <Btn kind="danger">Flag for Re-extraction</Btn>
          <Btn pressed={s.pressLock} disabled={s.saving}>{s.saving ? 'Saving…' : 'Approve & Lock'}</Btn>
        </div>
      </div>
    </div>
  );
}

function VerifyTab({ s, T }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '3fr 2fr', gap: 24 }}>
      <div style={{ minWidth: 0 }}>
        <h2 style={{ margin: '0 0 16px', fontSize: 17.6, fontWeight: 700, lineHeight: '26px' }}>Study Database</h2>
        <div style={{ display: 'flex', gap: 8, marginBottom: 16, height: 30 }}>
          {['All ICRV', 'All DPL', 'All verification', 'All lock status'].map(o => <span key={o} style={{ padding: '5.6px 10.4px', border: `1px solid ${A.inBorder}`, borderRadius: 5, fontSize: 13.3, background: '#fff', display: 'flex', alignItems: 'center', gap: 10 }}>{o}<span style={{ fontSize: 9, color: A.gray2 }}>▼</span></span>)}
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13.6 }}>
          <thead><tr style={{ height: 34 }}>{['Title', 'Year', 'Country', 'r', 'N', 'Confidence', 'ICRV', 'DPL', 'Status'].map(h => <th key={h} style={{ textAlign: 'left', padding: '8px 12px', background: '#f1f5f9', borderBottom: `2px solid ${A.border}`, fontSize: 12, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: A.gray2, whiteSpace: 'nowrap' }}>{h}</th>)}</tr></thead>
          <tbody>
            {STUDIES.map((r, i) => {
              const isNew = r.st === 'new';
              const locked = isNew ? s.lockedNew : r.st === 'locked';
              const tier = r.cf >= 90 ? 'success' : r.cf >= 70 ? 'medium' : 'low';
              const c = { padding: '0 12px', borderBottom: '1px solid #f1f5f9' };
              return (
                <tr key={i} style={{ height: 38, background: isNew && s.selected ? '#eff6ff' : 'transparent', opacity: MOTION.enter(T, s.rowsAt + i * 0.08, 0.35) }}>
                  <td style={{ ...c, maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.t}</td>
                  <td style={c}>{r.y}</td><td style={{ ...c, whiteSpace: 'nowrap' }}>{r.c}</td>
                  <td style={{ ...c, fontFamily: F.appMono }}>{r.r}</td><td style={{ ...c, fontFamily: F.appMono }}>{r.n}</td>
                  <td style={c}><Badge tone={tier}>{r.cf}%</Badge></td>
                  <td style={c}>{isNew ? (s.lockedNew ? 'III' : '-') : r.ic}</td><td style={c}>{isNew ? (s.lockedNew ? 'FOL' : '-') : r.dp}</td>
                  <td style={{ ...c, whiteSpace: 'nowrap' }}>{locked ? <Badge tone="success" scale={isNew ? MOTION.pop(T, s.lockAt) : 1}>Locked</Badge> : r.st === 'approved' ? <Badge tone="medium">Approved</Badge> : <Badge tone="low">Needs Review</Badge>}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div style={{ minWidth: 0, opacity: s.panel, transform: `translateX(${(1 - s.panel) * 24}px)` }}>
        {s.panel > 0 && <VerifyPanel s={s} />}
      </div>
    </div>
  );
}

function AppWindow({ s, T }) {
  const tabBtn = (active) => ({ position: 'relative', padding: '12px 24px', borderBottom: `3px solid ${active ? A.blue : 'transparent'}`, marginBottom: -2, fontSize: 14.7, fontWeight: active ? 700 : 500, color: active ? A.blue : A.gray, display: 'flex', alignItems: 'center' });
  return (
    <div style={{ position: 'absolute', left: 240, top: 110, width: 1440, height: 860, overflow: 'hidden', borderRadius: 6, boxShadow: '0 24px 48px rgba(23, 26, 25, .18)', border: `1px solid ${C.hair}`, background: '#f7f9fc', fontFamily: F.app, fontSize: 14, lineHeight: 1.5, color: A.text, opacity: s.winOp }}>
      <div style={{ transform: `translateY(${-s.scroll}px)` }}>
        <header style={{ background: '#1e3a5f', color: '#fff', padding: '16px 32px', height: 120, boxSizing: 'border-box' }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
            <h1 style={{ margin: 0, fontSize: 24, fontWeight: 700, lineHeight: '36px' }}>M-AIDA</h1>
            <span style={{ fontSize: 12, background: 'rgba(255,255,255,0.2)', padding: '1.6px 6.4px', borderRadius: 4 }}>v7.2.2</span>
          </div>
          <p style={{ margin: '4px 0 0', fontSize: 13.1, opacity: 0.8 }}>Meta-Analysis Intelligent Data Assistant - Internationalization &amp; Performance</p>
          <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
            <label style={{ fontSize: 12, opacity: 0.8 }}>Admin key</label>
            <span style={{ fontSize: 12, padding: '3.2px 8px', borderRadius: 4, border: '1px solid rgba(255,255,255,0.3)', background: 'rgba(255,255,255,0.1)', width: 220, boxSizing: 'border-box', letterSpacing: 1 }}>••••••••••••••••••••</span>
          </div>
        </header>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px 20px', padding: '0 16px', height: 40, boxSizing: 'border-box', background: '#f8fafc', borderBottom: `1px solid ${A.border}`, fontSize: 13.6 }}>
          <Pill label="Backend" tone="success" value="up · v7.2.2" />
          <Pill label="Data" tone="success" value="persistent · 6 record(s)" />
          <Pill label="Extraction" tone="success" value="live" />
          <Pill label="Network" tone="success" value="online" />
        </div>
        <nav style={{ display: 'flex', borderBottom: `2px solid ${A.border}`, background: '#fff', padding: '0 32px', height: 48, boxSizing: 'border-box' }}>
          <span style={tabBtn(s.tab === 'extract')}>Extract</span>
          <span style={tabBtn(s.tab === 'verify')}>Verify &amp; Lock
            {s.count > 0 && <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', background: '#e53e3e', color: '#fff', fontSize: 10.9, fontWeight: 700, minWidth: 18, height: 18, borderRadius: 9, padding: '0 4px', marginLeft: 6, transform: `scale(${MOTION.pop(T, s.badgeAt)})` }}>1</span>}
          </span>
        </nav>
        <main style={{ padding: '24px 32px' }}>
          {s.tab === 'extract' ? <ExtractTab s={s} T={T} /> : <VerifyTab s={s} T={T} />}
        </main>
      </div>
    </div>
  );
}

function Cursor({ x, y, op, press, file }) {
  return (
    <div style={{ position: 'absolute', left: x + 240, top: y + 110, opacity: op, pointerEvents: 'none' }}>
      {file > 0 && <div style={{ position: 'absolute', left: 18, top: 18, width: 250, height: 52, background: '#fff', border: `1px solid ${A.inBorder}`, borderRadius: 6, display: 'flex', alignItems: 'center', gap: 10, padding: '0 12px', boxSizing: 'border-box', boxShadow: '0 8px 20px rgba(23,26,25,.14)', opacity: file, fontFamily: F.app, fontSize: 13 }}>
        <span style={{ background: '#dc2626', color: '#fff', fontSize: 10, fontWeight: 700, padding: '3px 5px', borderRadius: 3 }}>PDF</span>sample_t_statistic.pdf</div>}
      <div style={{ position: 'absolute', left: -14, top: -14, width: 28, height: 28, borderRadius: 14, background: 'rgba(37,99,235,.25)', transform: `scale(${press})`, opacity: press > 0 ? 1 - press * 0.6 : 0 }}></div>
      <svg width="22" height="30" viewBox="0 0 22 30" style={{ position: 'absolute', left: -2, top: -2, overflow: 'visible' }}>
        <path d="M2 2 L2 24 L8 18.5 L12 27.5 L16 25.5 L12 16.8 L19.5 16.8 Z" fill="#111" stroke="#fff" strokeWidth="1.6" strokeLinejoin="round" />
      </svg>
    </div>
  );
}

// ================= Live Verification Console (demo/ui.html + demo/demo_seed.csv) =================
const K = { paper: '#faf7f2', ink: '#2b2620', muted: '#8a8177', line: '#e6ded2', card: '#ffffff', accent: '#7a1f2b', ok: '#2e6b46', warn: '#a05a00' };
const SEED = [
  ['S01', 'Siddharthan & Lall', 1982, 'UK', 74, -0.197], ['S02_e1', 'Grant', 1987, 'UK', 304, 0.145], ['S02_e2', 'Grant', 1987, 'UK', 304, 0.163],
  ['S02_e3', 'Grant', 1987, 'UK', 304, 0.107], ['S02_e4', 'Grant', 1987, 'UK', 304, -0.036], ['S99_e1', 'Phan et al.', 2020, 'Vietnam', 114, -0.011],
  ['S99_e2', 'Phan et al.', 2020, 'Vietnam', 285, -0.152], ['S112', 'Geringer, Beamish & daCosta', 1989, 'USA/Canada', 100, 0.145],
  ['S118', 'Contractor, Kundu & Hsu', 2003, 'Multi/Service', 103, 0.07], ['S121', 'Gaur, Kumar & Singh', 2014, 'India', 240, 0.09],
  ['S123', 'García-García, García-Canal & Guillén', 2017, 'Spain/Multi', 2256, 0.15], ['S126', 'Schmuck, Lagerström & Sallis', 2022, 'Sweden/Multi', 500, 0.06],
  ['S129_e1', 'Freixanet, Renart & Segarra-Blasco', 2022, 'Spain', 892, 0.08], ['S129_e2', 'Freixanet, Renart & Segarra-Blasco', 2022, 'Spain', 892, 0.11],
  ['S188', 'Do & Phan', 2025, 'India mfg', 380, -0.045], ['S189', 'Do & Phan', 2026, 'China mfg SME', 4290, 0.07, 1],
  ['S190', 'Phan, Ninh & Do', 2021, 'Turkey mfg', 263, -0.04, 1], ['S191', 'Phan et al.', 2021, 'Poland mfg-svc', 131, 0.05, 1],
];
const NEW_ID = '3f9c2a1e-7b4d-4c1a-9e2f-5d8b6a0c4e71';
const kB = { fontSize: 11, padding: '2px 8px', borderRadius: 999, fontWeight: 600, lineHeight: '16px' };
const KB = { locked: { background: '#e8f1ea', color: K.ok }, pending: { background: '#fbeedd', color: K.warn }, verified: { background: '#e9ecf5', color: '#3b4a7a' }, route1: { background: '#eef3ee', color: K.ok }, route06: { background: '#fbeedd', color: K.warn } };
const KBadge = ({ k, children, scale = 1 }) => <span style={{ ...kB, ...KB[k], display: 'inline-block', transform: `scale(${scale})`, transformOrigin: 'left center' }}>{children}</span>;
const kPill = (tone) => ({ fontSize: 12, padding: '3px 10px', borderRadius: 999, border: `1px solid ${tone === 'ok' ? '#bcd7c6' : K.line}`, background: K.paper, color: tone === 'ok' ? K.ok : K.muted, lineHeight: '18px', whiteSpace: 'nowrap', flexShrink: 0 });
const kGhost = { border: `1px solid ${K.line}`, borderRadius: 9, padding: '9px 16px', fontWeight: 700, fontSize: 14, background: K.paper, color: K.ink, lineHeight: '20px', height: 40, boxSizing: 'border-box', display: 'inline-flex', alignItems: 'center', whiteSpace: 'nowrap', flexShrink: 0 };
const kAct = (bg, pressed) => ({ ...kGhost, border: 0, background: bg, color: '#fff', transform: `scale(${pressed ? 0.96 : 1})` });
const kLabel = { display: 'block', fontSize: 12, color: K.muted, margin: '8px 0 2px', height: 18, lineHeight: '18px' };
const kInput = (h = 36) => ({ height: h, boxSizing: 'border-box', padding: '7px 9px', border: `1px solid ${K.line}`, borderRadius: 8, background: '#fffdf9', color: K.ink, fontSize: 15, lineHeight: '20px', overflow: 'hidden' });

function ConsoleWindow({ s, T }) {
  const st = SEED.map(r => ({ id: r[0], au: r[1], y: r[2], c: r[3], n: r[4], r: r[5], est: !!r[6], pending: !!r[6], locked: !r[6], isSel: false }));
  if (s.extracted) st.unshift({ id: NEW_ID, au: 'Sample, A.', y: 2026, c: 'Vietnam', n: 186, r: 0.2157, est: true, isNew: true, isSel: true, pending: !s.approved, locked: s.lockedNew });
  const newIn = MOTION.enter(T, s.extractAt, 0.5);
  const list = st.filter(x => s.filter === 'all' ? true : s.filter === 'locked' ? x.locked : x.pending);
  const nLocked = st.filter(x => x.locked).length, nPend = st.filter(x => x.pending).length;
  const th = { color: K.muted, fontWeight: 600, textAlign: 'left', padding: '0 8px', borderBottom: `1px solid ${K.line}`, whiteSpace: 'nowrap', height: 34, boxSizing: 'border-box' };
  const tdc = { padding: '0 8px', borderBottom: '1px solid #f0eadf', whiteSpace: 'nowrap', height: 36, boxSizing: 'border-box' };
  const card = { background: K.card, border: `1px solid ${K.line}`, borderRadius: 12, padding: '16px 18px', boxShadow: '0 1px 2px rgba(43,38,32,.04)', boxSizing: 'border-box' };
  const h2 = { margin: '0 0 10px', fontSize: 15, lineHeight: '23px', textTransform: 'uppercase', letterSpacing: '.8px', color: K.muted, fontWeight: 700 };
  const fb = (on) => ({ border: `1px solid ${on ? K.accent : K.line}`, background: on ? K.accent : K.paper, color: on ? '#fff' : K.ink, borderRadius: 999, padding: '4px 14px', fontSize: 13, lineHeight: '20px', whiteSpace: 'nowrap' });
  const stat = { flex: 1, minWidth: 110, background: K.card, border: `1px solid ${K.line}`, borderRadius: 12, padding: '10px 14px', textAlign: 'center', height: 81, boxSizing: 'border-box' };
  const rowIn = MOTION.enter(T, s.filterAt, 0.35);
  const MP = [['effect_r', '0.2157'], ['effect_t', '2.964'], ['effect_beta', '-'], ['effect_df', '180'], ['sample_n', '186'], ['doi_measure', 'FSTS'], ['performance_measure', 'ACC'], ['extraction_confidence', '0.68']];
  const status = s.lockedNew ? 'locked 2026-10-01T09:14:07' : s.approved ? 'approved' : 'needs review';
  const kv = [['r', '0.216'], ['N', '186'], ['DOI measure', 'FSTS'], ['Performance', 'ACC'], ['ICRV regime', '-'], ['DPL phase', '-'], ['Confidence', '0.68'], ['Status', status]];
  return (
    <div style={{ position: 'absolute', left: 240, top: 110, width: 1440, height: 860, overflow: 'hidden', borderRadius: 6, boxShadow: '0 24px 48px rgba(23, 26, 25, .18)', border: `1px solid ${C.hair}`, background: K.paper, color: K.ink, fontFamily: F.app, fontSize: 15, lineHeight: 1.55, opacity: s.conOp }}>
      <div style={{ transform: `translateY(${-s.scroll}px)` }}>
        <header style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap', padding: '14px 22px', borderBottom: `1px solid ${K.line}`, background: K.card, height: 123, boxSizing: 'border-box', alignContent: 'flex-start' }}>
          <div style={{ fontSize: 20, fontWeight: 800, letterSpacing: '.4px', lineHeight: '31px' }}>M-AIDA <small style={{ fontWeight: 600, color: K.muted, marginLeft: 8, fontSize: 20 }}>v7.2.2 · live</small></div>
          <span style={kPill()}>{st.length} records in store</span>
          <span style={kPill('ok')}>LLM extraction: configured</span>
          <span style={kPill('ok')}>network: online</span>
          <span style={{ flex: 1 }}></span>
          {['Presenter unlocked', 'Defense mode', 'Reset demo', 'API docs'].map(b => <span key={b} style={kGhost}>{b}</span>)}
          <span style={{ flexBasis: '100%', height: 0 }}></span>
          <span style={kGhost}>Export locked CSV</span>
        </header>
        <main style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1.35fr) minmax(0,1fr)', gap: 18, padding: '18px 22px', maxWidth: 1280, margin: '0 auto', boxSizing: 'border-box' }}>
          <section>
            <div style={{ display: 'flex', gap: 12, marginBottom: 14 }}>
              {[[st.length, 'effect records'], [nLocked, 'locked'], [nPend, 'awaiting human review']].map(([v, l]) => (
                <div key={l} style={stat}><b style={{ display: 'block', fontSize: 26, lineHeight: '40px' }}>{v}</b><span style={{ fontSize: 12, color: K.muted }}>{l}</span></div>
              ))}
            </div>
            <div style={card}>
              <h2 style={h2}>Study database (live API)</h2>
              <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
                <span style={fb(s.filter === 'all')}>All</span><span style={fb(s.filter === 'pending')}>Needs review</span><span style={fb(s.filter === 'locked')}>Locked</span>
              </div>
              <div style={{ overflow: 'hidden' }}><table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13.5, tableLayout: 'fixed' }}>
                <colgroup><col style={{ width: 68 }} /><col /><col style={{ width: 112 }} /><col style={{ width: 52 }} /><col style={{ width: 62 }} /><col style={{ width: 112 }} /><col style={{ width: 98 }} /></colgroup>
                <thead><tr>{['ID', 'Study', 'Country', 'N', 'r', 'Route', 'Status'].map(h => <th key={h} style={th}>{h}</th>)}</tr></thead>
                <tbody>
                  {list.map((x, i) => (
                    <tr key={x.id} style={{ background: x.isSel && s.selected ? '#f6efe1' : 'transparent', opacity: (s.filter === 'all' && T < s.filterAt ? 1 : clamp(rowIn * 1.4 - i * 0.04, 0, 1)) * (x.isNew ? newIn : 1) }}>
                      <td style={{ ...tdc, overflow: 'hidden', textOverflow: 'ellipsis' }}>{x.id}</td>
                      <td style={{ ...tdc, overflow: 'hidden', textOverflow: 'ellipsis' }}>{x.au} ({x.y})</td>
                      <td style={{ ...tdc, overflow: 'hidden', textOverflow: 'ellipsis' }}>{x.c}</td><td style={tdc}>{x.n}</td><td style={tdc}>{x.r.toFixed(3)}</td>
                      <td style={tdc}>{x.est ? <KBadge k="route06">estimated · {x.isNew ? '0.7' : '0.6'}</KBadge> : <KBadge k="route1">direct r · 1.0</KBadge>}</td>
                      <td style={tdc}>{x.locked ? <KBadge k="locked" scale={x.isSel ? MOTION.pop(T, s.lockAt) : 1}>locked</KBadge> : x.pending ? <KBadge k="pending">needs review</KBadge> : <KBadge k="verified">approved</KBadge>}</td>
                    </tr>
                  ))}
                </tbody>
              </table></div>
            </div>
            <div style={{ ...card, marginTop: 18 }}>
              <h2 style={h2}>Extract a new PDF (real pipeline)</h2>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 12px' }}>
                <div><label style={kLabel}>PDF file</label><div style={{ ...kInput(), padding: 6, display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, background: s.fileOver ? '#f6efe1' : '#fffdf9', borderColor: s.fileOver ? K.accent : K.line }}><span style={{ border: '1px solid #b9b1a6', borderRadius: 4, padding: '1px 8px', background: '#efeae3', whiteSpace: 'nowrap' }}>Choose File</span><span style={{ whiteSpace: 'nowrap' }}>{s.file ? 'sample_t_statistic.pdf' : 'No file chosen'}</span></div></div>
                <div><label style={kLabel}>Authors</label><div style={{ ...kInput(), color: s.exAuthors ? K.ink : '#b3aa9e', borderColor: s.focus === 'authors' ? K.accent : K.line }}>{s.exAuthors || 'e.g. Nguyen & Tran'}</div></div>
                <div><label style={kLabel}>Title</label><div style={{ ...kInput(), color: s.exTitle ? K.ink : '#b3aa9e', borderColor: s.focus === 'title' ? K.accent : K.line }}>{s.exTitle || 'Paper title'}</div></div>
                <div><label style={kLabel}>Year</label><div style={{ ...kInput(), color: s.exYear ? K.ink : '#b3aa9e', borderColor: s.focus === 'year' ? K.accent : K.line }}>{s.exYear || '2026'}</div></div>
              </div>
              <div style={{ display: 'flex', gap: 10, marginTop: 14 }}><span style={kAct(K.accent, s.pressExtract)}>Run extraction</span></div>
              {s.exMsg && <div style={{ marginTop: 12, padding: '9px 12px', borderRadius: 9, fontSize: 13.5, background: '#e8f1ea', color: K.ok, opacity: s.exMsgIn }}>{s.exMsg}</div>}
              <div style={{ fontSize: 12.5, color: K.muted, marginTop: 8 }}>Extraction calls the live language-model pipeline and requires <code>LLM_API_KEY</code> in <code>backend/.env</code>. Without a key the server answers 503 and the message is shown here unchanged; nothing is simulated.</div>
            </div>
          </section>
          <section>
            <div style={card}>
              <h2 style={h2}>Record detail &amp; PI verification</h2>
              {!s.selected ? (
                <div style={{ fontSize: 12.5, color: K.muted, marginTop: 8 }}>Select a record on the left. Records marked "needs review" show the frozen machine proposal next to the current values, and can be corrected, approved and locked here: the same governance flow used to build the dissertation database.</div>
              ) : (
                <div style={{ opacity: s.detail, transform: `translateY(${(1 - s.detail) * 8}px)` }}>
                  <h3 style={{ margin: '2px 0', fontSize: 17, lineHeight: '26px' }}>Sample, A. (2026)</h3>
                  <div style={{ color: K.muted, fontSize: 13, marginBottom: 10, height: 20, lineHeight: '20px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{NEW_ID} · Vietnam</div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 16px', fontSize: 13.5, marginBottom: 12, lineHeight: '21px' }}>
                    {kv.map(([k, v]) => <div key={k}><b style={{ color: K.muted, fontWeight: 600, marginRight: 6 }}>{k}</b>{v}</div>)}
                  </div>
                  <div style={{ border: `1px dashed ${K.line}`, borderRadius: 10, padding: '10px 12px', marginBottom: 12 }}>
                    <h4 style={{ margin: '0 0 6px', fontSize: 12, lineHeight: '18px', textTransform: 'uppercase', letterSpacing: '.6px', color: K.muted }}>Machine proposal (frozen at extraction, immutable)</h4>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12.5 }}>
                      <thead><tr>{['Field', 'Machine', 'Current'].map(h => <th key={h} style={{ ...th, height: 27 }}>{h}</th>)}</tr></thead>
                      <tbody>{MP.map(([f, v]) => <tr key={f}><td style={{ ...tdc, height: 27 }}>{f}</td><td style={{ ...tdc, height: 27 }}>{v}</td><td style={{ ...tdc, height: 27 }}>{v}</td></tr>)}</tbody>
                    </table>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 12px' }}>
                    <div><label style={kLabel}>Pearson r (override)</label><div style={kInput()}>0.2157</div></div>
                    <div><label style={kLabel}>Sample N (override)</label><div style={kInput()}>186</div></div>
                    <div><label style={kLabel}>DOI measure</label><div style={{ ...kInput(), display: 'flex', justifyContent: 'space-between' }}>FSTS<span style={{ fontSize: 10, color: K.muted }}>▼</span></div></div>
                    <div><label style={kLabel}>Performance measure</label><div style={{ ...kInput(), display: 'flex', justifyContent: 'space-between' }}>ACC<span style={{ fontSize: 10, color: K.muted }}>▼</span></div></div>
                  </div>
                  <label style={kLabel}>PI verification notes (required to approve)</label>
                  <div style={{ ...kInput(64), whiteSpace: 'normal', color: s.notes ? K.ink : '#b3aa9e', borderColor: s.notesFocus ? K.accent : K.line }}>{s.notes || 'What was checked against the paper, and why any override was made'}</div>
                  <div style={{ display: 'flex', gap: 10, marginTop: 14 }}>
                    <span style={kAct(K.accent, s.pressApprove)}>Approve &amp; save</span>
                    <span style={kAct(K.ink, s.pressLock)}>Lock record</span>
                  </div>
                  {s.msg && <div style={{ marginTop: 12, padding: '9px 12px', borderRadius: 9, fontSize: 13.5, background: '#e8f1ea', color: K.ok, opacity: s.msgIn }}>{s.msg}</div>}
                </div>
              )}
            </div>
          </section>
        </main>
      </div>
      {s.confirm > 0 && (
        <div style={{ position: 'absolute', left: 440, top: 200, width: 560, background: '#fff', borderRadius: 10, boxShadow: '0 16px 40px rgba(43,38,32,.22)', border: `1px solid ${K.line}`, padding: '20px 22px', boxSizing: 'border-box', opacity: s.confirm, transform: `translateY(${(1 - s.confirm) * -10}px)` }}>
          <div style={{ fontSize: 13, color: K.muted, marginBottom: 6 }}>localhost:8000 says</div>
          <div style={{ fontSize: 15, marginBottom: 18 }}>Locking is IRREVERSIBLE (further edits return 409). Lock {NEW_ID}?</div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
            <span style={{ ...kGhost, height: 34, padding: '6px 16px' }}>Cancel</span>
            <span style={{ ...kAct(K.accent, s.pressOk), height: 34, padding: '6px 22px' }}>OK</span>
          </div>
        </div>
      )}
    </div>
  );
}

// ================= Gate (console register) =================
function Sheet({ T, left, page, quote, hiAt, qLine }) {
  const hi = MOTION.draw(T, hiAt, 0.6);
  return (
    <div style={{ position: 'absolute', left, top: 0, width: 270, height: 380, background: C.s1, borderRadius: 3, padding: '26px 24px', boxSizing: 'border-box', display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ font: `400 15px/1 ${F.mono}`, color: C.subtle, marginBottom: 6 }}>p. {page}</div>
      {Array.from({ length: 10 }).map((_, i) => i === qLine ? (
        <div key={i} style={{ position: 'relative', font: `600 17px/22px ${F.body}`, color: C.ink, padding: '0 4px', margin: '-4px -4px' }}>
          <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: `${hi * 100}%`, background: 'rgba(63,122,90,.22)', borderBottom: `2px solid ${C.verified}` }}></div>
          <span style={{ position: 'relative' }}>{quote}</span>
        </div>
      ) : <div key={i} style={{ height: 8, borderRadius: 1, background: C.hair, width: `${[96, 88, 100, 72, 94, 84, 98, 64, 90, 78][i]}%` }}></div>)}
    </div>
  );
}
function GateSection({ T, G, V }) {
  const op = MOTION.enter(T, G + 0.3, 0.6) * (1 - MOTION.enter(T, V - 0.7, 0.5));
  const push = 1 + 0.03 * p01(T, G, V - G);
  const ln = (at) => ({ opacity: MOTION.enter(T, at, 0.4) });
  const L = { font: `400 24px/40px ${F.mono}`, color: C.cInk, whiteSpace: 'pre' };
  return (
    <div style={{ opacity: op, transform: `scale(${push})`, transformOrigin: '960px 540px' }}>
      <div style={{ position: 'absolute', left: 140, top: 130, width: 1400 }}>
        <div style={{ font: `600 72px/1.12 ${F.display}`, letterSpacing: '-1.2px', color: '#fff', ...ln(G + 0.6) }}>No evidence, no record.</div>
        <div style={{ font: `400 30px/1.5 ${F.body}`, color: C.cMuted, marginTop: 20, maxWidth: 1180, textWrap: 'pretty', ...ln(G + 1.2) }}>A record is created only when the page and quote are found for both the statistic and the sample size.</div>
      </div>
      <div style={{ position: 'absolute', left: 140, top: 430, width: 560, height: 380, ...ln(G + 1.4) }}>
        <Sheet T={T} left={0} page={4} quote="…186 firms…" hiAt={G + 3.6} qLine={4} />
        <Sheet T={T} left={290} page={7} quote="t(180) = 2.964, p < .01" hiAt={G + 2.6} qLine={6} />
      </div>
      <div style={{ position: 'absolute', left: 760, top: 430, width: 1020, height: 380, background: C.cSurf, border: `1px solid ${C.cHair}`, borderRadius: 3, padding: '28px 36px', boxSizing: 'border-box', ...ln(G + 1.6) }}>
        <div style={{ ...L, color: C.cMuted }}>{typed('$ evidence_gate sample_t_statistic', T, G + 1.8, 0.7)}</div>
        <div style={{ ...L, ...ln(G + 2.6) }}>statistic   p. 7  "t(180) = 2.964, p &lt; .01"  <span style={{ color: '#7fc29b', opacity: MOTION.enter(T, G + 3.2, 0.3) }}>PASS</span></div>
        <div style={{ ...L, ...ln(G + 3.6) }}>sample N    p. 4  "186 firms"                <span style={{ color: '#7fc29b', opacity: MOTION.enter(T, G + 4.2, 0.3) }}>PASS</span></div>
        <div style={{ ...L, marginTop: 16, ...ln(G + 4.8) }}>→ record stored · requires_verification: true</div>
        <div style={{ height: 1, background: C.cHair, margin: '24px 0', ...ln(G + 5.6) }}></div>
        <div style={{ ...L, color: '#d9876b', ...ln(G + 5.8) }}>quote missing → HTTP 422 · nothing stored</div>
      </div>
    </div>
  );
}

// ================= Close =================
function CloseSection({ T, Z, END, tw }) {
  const vis = T >= Z - 0.2 ? 1 : 0;
  const plotOut = MOTION.draw(T, Z + 4.0, 0.7);
  const fadeEnd = 1 - MOTION.enter(T, END - 0.8, 0.7);
  const ln = (at) => ({ opacity: MOTION.enter(T, at, 0.8), transform: `translateY(${(1 - MOTION.enter(T, at, 0.8)) * 18}px)` });
  return (
    <div style={{ opacity: vis * fadeEnd }}>
      <div style={{ opacity: 1 - plotOut, transform: `translateX(${-plotOut * 60}px)` }}>
        <div style={{ position: 'absolute', left: 140, top: 330, width: 620 }}>
          <div style={{ font: `600 76px/1.12 ${F.display}`, letterSpacing: '-1.2px', color: C.ink, ...ln(Z + 0.3) }}>Only locked records are pooled.</div>
          <div style={{ font: `400 30px/1.5 ${F.body}`, color: C.muted, marginTop: 32, ...ln(Z + 1.0) }}>Every row checked by a person. Every value traceable to a page.</div>
        </div>
        <Forest T={T} left={880} top={230} rowsAt={Z - 0.2} lockAt={Z + 0.8} poolAt={Z} fillAt={Z + 2.2} />
      </div>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 250, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <div style={{ opacity: T >= Z + 4.3 ? 1 : 0 }}><Mark T={T} t0={Z + 4.3} width={220} /></div>
        <div style={{ font: `600 110px/1.12 ${F.display}`, letterSpacing: '-1.2px', color: C.ink, marginTop: 28, ...ln(Z + 5.3) }}>M-AIDA</div>
        <div style={{ font: `400 44px/1.3 ${F.display}`, color: C.muted, marginTop: 12, ...ln(Z + 5.9) }}>Let the evidence decide.</div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, marginTop: 56, ...ln(Z + 6.6) }}>
          <div style={{ font: `600 28px/1.3 ${F.body}`, color: C.ink }}>Do Thuy Huong · Phan Anh Tu</div>
          <div style={{ font: `400 24px/1.3 ${F.body}`, color: C.muted }}>School of Economics, Can Tho University</div>
          <div style={{ font: `400 20px/1.3 ${F.mono}`, color: C.subtle, marginTop: 12 }}>doi.org/10.5281/zenodo.21850575</div>
        </div>
      </div>
      {tw.showHuong && <Huong src="assets/img/huong/greet_hero_clean.png" T={T} inAt={Z + 5.0} outAt={END + 1} left={1500} height={860} width={313} />}
    </div>
  );
}

// ================= App choreography =================
function useAppState(T, X, G, V, Z) {
  const clicks = [X + 2.9, X + 3.3, X + 4.5, X + 5.7, X + 6.6, V + 1.3, V + 2.4, V + 4.4, V + 6.9, V + 8.2, V + 9.2, V + 10.8];
  const press = clicks.reduce((m, c) => (T >= c && T < c + 0.35 ? p01(T, c, 0.35) : m), 0);
  const resultAt = X + 7.4;
  const tab = 'extract';
  const lockAt = V + 9.3;
  const onConsole = true;
  const scroll = T < G + 0.5
    ? kf(T, [[X + 0.8, 0], [X + 1.8, 700], [X + 9.2, 700], [X + 10.2, 0]])
    : kf(T, [[V + 3.4, 0], [V + 4.2, 150], [V + 9.8, 150], [V + 10.4, 0]]);
  const extractAt = X + 8.2;
  const approved = T >= V + 7.0;
  return {
    tab, scroll, resultAt, lockAt, badgeAt: resultAt, onConsole,
    winOp: MOTION.enter(T, X, 0.8) * (1 - MOTION.enter(T, G + 0.2, 0.6)),
    conOp: MOTION.enter(T, X, 0.8) * (1 - MOTION.enter(T, G + 0.2, 0.6)) + (T > G + 0.5 ? MOTION.enter(T, V - 0.6, 0.6) * (1 - MOTION.enter(T, Z - 0.9, 0.8)) : 0),
    extractAt, extracted: T >= extractAt, fileOver: inWin(T, X + 2.2, X + 2.9), file: T >= X + 2.9,
    exAuthors: typed('Sample, A.', T, X + 3.5, 0.6), exTitle: typed('sample_t_statistic', T, X + 4.7, 0.8), exYear: typed('2026', T, X + 5.8, 0.3),
    focus: inWin(T, X + 3.3, X + 4.5) ? 'authors' : inWin(T, X + 4.5, X + 5.7) ? 'title' : inWin(T, X + 5.7, X + 6.6) ? 'year' : null,
    exMsg: T >= extractAt ? 'Extracted ' + NEW_ID + ' (confidence 0.68). It appears in the table for verification.' : T >= X + 6.7 ? 'Extracting (live LLM call)…' : '',
    exMsgIn: T >= extractAt ? MOTION.enter(T, extractAt, 0.35) : MOTION.enter(T, X + 6.7, 0.35),
    filter: T < V + 1.3 ? 'all' : T < V + 10.8 ? 'pending' : 'locked', filterAt: T < V + 10.8 ? V + 1.3 : V + 10.8,
    detail: MOTION.enter(T, extractAt, 0.4), notesFocus: inWin(T, V + 4.4, V + 6.9),
    notes: typed('t(180) = 2.964 (p. 7) and N = 186 (p. 4) checked against the paper; no override.', T, V + 4.6, 1.6),
    approved, pressApprove: inWin(T, V + 6.9, V + 7.1), confirm: inWin(T, V + 8.3, V + 9.3) ? MOTION.enter(T, V + 8.3, 0.25) : 0, pressOk: inWin(T, V + 9.2, V + 9.35),
    msg: T >= lockAt ? 'Record locked. Any further PATCH /verify now returns 409 Conflict.' : approved ? 'Saved: record approved. You can now lock it.' : '',
    msgIn: T >= lockAt ? MOTION.enter(T, lockAt, 0.35) : MOTION.enter(T, V + 7.0, 0.35),
    dragOver: inWin(T, X + 2.2, X + 2.9), dropped: T >= X + 2.9,
    title: T >= X + 2.9 ? 'sample_t_statistic' : '',
    authors: typed('Sample, A.', T, X + 3.5, 0.7), country: typed('Vietnam', T, X + 4.9, 0.5),
    pressExtract: inWin(T, X + 6.6, X + 6.8), loading: inWin(T, X + 6.3, resultAt),
    result: MOTION.enter(T, resultAt, 0.5), count: T >= resultAt ? 1 : 0,
    rowsAt: V + 1.2, selected: T >= extractAt, panel: 0, innerS: 0, ov: {},
    pressLock: inWin(T, V + 8.2, V + 8.4), saving: false, lockedNew: T >= lockAt,
    press,
  };
}
function camera(T, X, G, V, Z) {
  const pts = [
    [X, 0.94, 960, 570], [X + 1.0, 1, 960, 540], [X + 2.0, 1.4, 700, 620], [X + 8.6, 1.4, 700, 620], [X + 9.4, 1.0, 960, 540],
    [X + 10.6, 1.0, 960, 540], [X + 12.0, 1.12, 1000, 520], [G - 0.1, 1.12, 1000, 520], [G + 0.8, 2.2, 960, 700], [V - 0.7, 1.1, 960, 560], [V + 0.2, 1.0, 960, 540], [V + 1.3, 1.0, 960, 540],
    [V + 2.0, 1.0, 960, 540], [V + 2.9, 1.4, 1319, 555], [V + 3.4, 1.4, 1319, 555], [V + 4.2, 1.4, 1319, 640], [V + 9.8, 1.4, 1319, 640], [V + 10.5, 1.05, 900, 560], [V + 13.6, 0.94, 960, 540],
  ];
  const tr = i => kf(T, pts.map(p => [p[0], p[i]]));
  return { s: tr(1), fx: tr(2), fy: tr(3) };
}
function cursorPos(T, X, V) {
  const pts = [
    [X + 1.0, 1300, 300], [X + 2.8, 200, 439], [X + 3.1, 200, 439], [X + 3.3, 620, 439], [X + 4.3, 620, 439], [X + 4.5, 280, 503],
    [X + 5.5, 280, 503], [X + 5.7, 620, 503], [X + 6.2, 620, 503], [X + 6.6, 185, 555], [X + 7.0, 185, 555], [X + 8.4, 400, 300], [V - 0.4, 700, 600], [V + 1.1, 232, 301], [V + 1.5, 232, 301], [V + 2.2, 330, 378], [V + 3.0, 330, 378],
    [V + 3.4, 1000, 620], [V + 4.2, 1079, 698], [V + 6.3, 1079, 698], [V + 6.8, 907, 764], [V + 7.2, 907, 764], [V + 8.0, 1047, 764],
    [V + 8.4, 1047, 764], [V + 9.0, 948, 326], [V + 9.4, 948, 326], [V + 10.4, 332, 301], [V + 11.0, 332, 301], [V + 12.0, 620, 520],
  ];
  return { x: kf(T, pts.map(p => [p[0], p[1]])), y: kf(T, pts.map(p => [p[0], p[2]])) };
}

function CaptionBar({ T, items, dark }) {
  let cur = null;
  items.forEach(it => { if (T >= it.at && T < it.until) cur = it; });
  const a = cur ? Math.min(MOTION.enter(T, cur.at, 0.3), 1 - MOTION.enter(T, cur.until - 0.3, 0.3)) : 0;
  return <div style={{ position: 'absolute', left: 0, right: 0, top: 986, display: 'flex', justifyContent: 'center', opacity: a }}><span style={{ font: `400 30px/1.3 ${F.body}`, color: dark ? C.cInk : C.ink, background: dark ? 'rgba(23,26,25,.88)' : 'rgba(246,241,231,.94)', padding: '8px 22px', borderRadius: 6 }}>{cur ? cur.text : ''}</span></div>;
}

function Piece({ tw }) {
  const { T, CUES } = useComposition();
  const Q = CUES.Question, X = CUES.Extract, G = CUES.Gate, V = CUES.Verify, Z = CUES.Close, END = CUES.Close + 14.4;
  const dark = MOTION.enter(T, G, 0.6) * (1 - MOTION.enter(T, V - 0.6, 0.6));
  const s = useAppState(T, X, G, V, Z);
  const cam = camera(T, X, G, V, Z);
  const cp = cursorPos(T, X, V);
  const curOp = MOTION.enter(T, X + 1.0, 0.3) * (1 - MOTION.enter(T, X + 8.6, 0.3)) + MOTION.enter(T, V - 0.4, 0.3) * (1 - MOTION.enter(T, V + 11.6, 0.4));
  const file = T >= X + 1.0 && T < X + 2.95 ? 1 - p01(T, X + 2.8, 0.15) : 0;
  const showApp = T >= X - 0.1 && T < Z + 0.2;
  const caps = [
    { at: X + 0.9, until: X + 6.4, text: 'Extract: upload a PDF and the live pipeline proposes the focal effect size.' },
    { at: X + 6.6, until: X + 9.4, text: 'The machine proposal is frozen at extraction and can never be edited.' },
    { at: X + 9.5, until: G + 0.1, text: 'Confidence below 0.70 flags the record for mandatory PI review.' },
    { at: V + 0.6, until: V + 3.7, text: 'Verify: the new record opens beside its frozen machine proposal.' },
    { at: V + 3.8, until: V + 6.9, text: 'The PI checks each value against the paper and writes down why.' },
    { at: V + 7.0, until: V + 10.0, text: 'Locking is irreversible. Further edits return 409 Conflict.' },
    { at: V + 10.1, until: V + 12.8, text: 'Only locked records enter the analysis export.' },
  ];
  return (
    <div data-screen-label={`t=${Math.floor(T)}s`} style={{ position: 'absolute', inset: 0, width: 1920, height: 1080, overflow: 'hidden', background: C.canvas }}>
      <div style={{ position: 'absolute', inset: 0, background: C.cCanvas, opacity: dark }}></div>
      {T < X + 0.5 && <MarkSection T={T} Q={Q} />}
      <QuestionSection T={T} Q={Q} X={X} tw={tw} />
      <div style={{ position: 'absolute', inset: 0, visibility: showApp ? 'visible' : 'hidden', transformOrigin: '0 0', transform: `translate(960px, 540px) scale(${cam.s}) translate(${-cam.fx}px, ${-cam.fy}px)` }}>
        {s.onConsole ? <ConsoleWindow s={s} T={T} /> : <AppWindow s={s} T={T} />}
        <Cursor x={cp.x} y={cp.y} op={clamp(curOp, 0, 1)} press={s.press} file={file} />
      </div>
      <GateSection T={T} G={G} V={V} />
      <CloseSection T={T} Z={Z} END={END} tw={tw} />
      {tw.captions && <CaptionBar T={T} items={caps} dark={dark > 0.5} />}
    </div>
  );
}

function Soundtrack({ on }) {
  const { time, playing } = useComposition();
  const ref = React.useRef(null);
  const [src, setSrc] = React.useState(null);
  React.useEffect(() => {
    let url = null, dead = false;
    fetch('assets/audio/maida.mp3').then(r => r.blob()).then(b => { if (dead) return; url = URL.createObjectURL(b); setSrc(url); }).catch(() => {});
    return () => { dead = true; if (url) URL.revokeObjectURL(url); };
  }, []);
  React.useEffect(() => {
    const a = ref.current; if (!a || !src) return;
    if (!on || !playing) { if (!a.paused) a.pause(); if (Math.abs(a.currentTime - time) > 0.05) a.currentTime = Math.min(time, a.duration || time); return; }
    if (Math.abs(a.currentTime - time) > 0.25) a.currentTime = time;
    if (a.paused) a.play().catch(() => {});
  }, [time, playing, on, src]);
  return src ? <audio ref={ref} src={src} preload="auto" /> : null;
}

function MaidaFilm() {
  const [t, setTweak] = window.useTweaks(window.TWEAK_DEFAULTS);
  const { TweaksPanel, TweakSection, TweakToggle } = window;
  return (
    <React.Fragment>
      <CompositionStage width={1920} height={1080} scenes={window.OM_SCENES} playback={window.OM_PLAYBACK} bg={C.canvas}>
        <Piece tw={t} />
        <Soundtrack on={t.sound} />
      </CompositionStage>
      <TweaksPanel>
        <TweakSection label="Playback" />
        <TweakToggle label="Motion editor" value={t.motionEditor} onChange={v => setTweak('motionEditor', v)} />
        <TweakToggle label="Voice-over" value={t.sound} onChange={v => setTweak('sound', v)} />
        <TweakSection label="Content" />
        <TweakToggle label="Huong AI" value={t.showHuong} onChange={v => setTweak('showHuong', v)} />
        <TweakToggle label="Captions" value={t.captions} onChange={v => setTweak('captions', v)} />
      </TweaksPanel>
    </React.Fragment>
  );
}
window.MaidaFilm = MaidaFilm;
