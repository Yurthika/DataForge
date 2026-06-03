def get_styles() -> str:
    return """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=Inter:wght@400;500;600;700&display=swap');
:root {
  --bg-primary:#0A0E1A; --bg-card:#111827; --bg-sidebar:#080C16; --bg-border:#1F2937;
  --accent-blue:#3B82F6; --accent-green:#10B981; --accent-yellow:#F59E0B; --accent-red:#EF4444;
  --accent-purple:#8B5CF6; --accent-pink:#EC4899; --text-primary:#F9FAFB; --text-secondary:#9CA3AF; --text-muted:#6B7280;
}
html, body, [class*="css"] { font-family: Inter, sans-serif; color: var(--text-primary); }
[data-testid="stAppViewContainer"] { background: var(--bg-primary); }
[data-testid="stSidebar"] { background: var(--bg-sidebar); border-right:1px solid var(--bg-border); }
[data-testid="stFileUploaderDropzone"] { border:2px dashed var(--accent-blue)!important; background:var(--bg-card); border-radius:10px; }
[data-testid="stFileUploaderDropzone"]:hover { border-style:solid!important; box-shadow:0 0 12px rgba(59,130,246,.4); }
.df-brand { font-family:'IBM Plex Mono', monospace; letter-spacing:4px; color:var(--accent-blue); font-size:1.7rem; font-weight:700; }
.df-tagline { color:var(--text-secondary); font-size:.82rem; margin-bottom:1rem; }
.step-dot { width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:12px; }
.step-current { background:var(--accent-blue); animation:pulse 1.3s infinite; }
.step-done { background:var(--accent-green); }
.step-future { background:#374151; color:#9CA3AF; }
@keyframes pulse {0%{box-shadow:0 0 0 0 rgba(59,130,246,.6)}100%{box-shadow:0 0 0 10px rgba(59,130,246,0)}}
.kpi-card { background:var(--bg-card); border:1px solid var(--bg-border); padding:14px; transition:.2s ease; }
.kpi-card:hover { transform:translateY(-4px); border-color:var(--accent-blue); }
.kpi-value { font-family:'IBM Plex Mono', monospace; font-size:2.5rem; font-weight:700; }
.severity-critical,.severity-warning,.severity-info { border-radius:9999px; padding:2px 10px; font-size:.75rem; font-weight:600; display:inline-block; }
.severity-critical { background:#EF4444; color:#fff; } .severity-warning { background:#F59E0B; color:#111; } .severity-info { background:#3B82F6; color:#fff; }
.fix-card { background:#111827; border:1px solid #1F2937; padding:12px; margin-bottom:8px; }
.stButton button { background:#3B82F6; color:#fff; border-radius:0; border:none; }
.stButton button:hover { background:#2563EB; } .stButton button:active { background:#1D4ED8; }
.stButton button:disabled { background:#374151!important; color:#6B7280!important; cursor:not-allowed!important; }
</style>
"""
