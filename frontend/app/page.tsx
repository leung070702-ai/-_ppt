'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { Check, ChevronDown, ChevronLeft, ChevronRight, Download, FileText, FolderOpen, LayoutGrid, Loader2, Plus, Sparkles, Upload, X } from 'lucide-react';

type Suggestion = { id: string; slide_number: number; category: string; severity: string; title: string; description: string; action: string; rationale: string; automation: string; status: string; edited_action?: string | null };
type Job = { id: string; project_id: string; status: string; current_step?: string; steps: { key: string; label: string; status: string }[]; storyline?: { audience: string; thesis: string; stages: string[]; coverage: Record<string, number>; gaps: string[] } | null; quality?: { passed: boolean; score: number; checks: { name: string; passed: boolean }[]; notes: string } | null };

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const demoSlides = [
  { n: 1, title: '智联能源', sub: '分布式光伏智能运维系统', accent: 'dark' },
  { n: 2, title: '项目背景与痛点', sub: '故障响应慢，数据孤岛严重', accent: 'light' },
  { n: 3, title: '技术方案', sub: '感知 · 诊断 · 决策一体化', accent: 'dark' },
  { n: 4, title: '产品价值', sub: '让每一度电更高效、更安全', accent: 'light' },
  { n: 5, title: '商业模式', sub: '软硬一体，持续服务', accent: 'light' },
];
const demoSuggestions: Suggestion[] = [
  { id: 'demo-1', slide_number: 1, category: '商业逻辑', severity: 'high', title: '强化本页的价值主张', description: '当前页面未在首屏明确说明解决谁的什么问题，评委需要自行拼接上下文。', action: '在标题下增加一句「为目标用户带来什么结果」的短句，并保留原主题。', rationale: '评分标准：选题价值 / 商业价值（15分）', automation: 'manual_required', status: 'pending' },
  { id: 'demo-2', slide_number: 1, category: '内容结构', severity: 'high', title: '让关键信息层级更突出', description: '标题字号与副标题对比不足，核心项目名称没有形成第一阅读锚点。', action: '提升标题与副标题的字号对比，突出项目名称，保持现有配色。', rationale: '评分标准：表达与展示（10分）', automation: 'safe_auto', status: 'pending' },
  { id: 'demo-3', slide_number: 1, category: '视觉表达', severity: 'medium', title: '团队与单位信息可精简', description: '团队、单位、日期信息占据较多视觉空间，可适当缩小字号。', action: '将辅助信息统一调整为 18pt，并与主标题拉开间距。', rationale: '评分标准：表达与展示（10分）', automation: 'safe_auto', status: 'pending' },
  { id: 'demo-4', slide_number: 1, category: '视觉表达', severity: 'low', title: '提高深色背景文字对比度', description: '深色背景与白色文字在部分区域对比度一般，建议增加半透明遮罩。', action: '在文字区域增加轻微半透明深色遮罩，避免改变原主题。', rationale: '评分标准：表达与展示（10分）', automation: 'manual_required', status: 'pending' },
];

function IconMark() { return <div className="brand-mark"><Sparkles size={17} strokeWidth={2.4} /></div>; }

export default function Home() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [activeNav, setActiveNav] = useState('逐页建议');
  const [slide, setSlide] = useState(1);
  const [tab, setTab] = useState('逐页建议');
  const [suggestions, setSuggestions] = useState(demoSuggestions);
  const [job, setJob] = useState<Job | null>(null);
  const [uploading, setUploading] = useState(false);
  const [fileName, setFileName] = useState('智联能源-全国大学生科技创新大赛.pptx');
  const [projectId, setProjectId] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [toast, setToast] = useState('');

  const visibleSuggestions = useMemo(() => suggestions.filter((s) => s.slide_number === slide), [suggestions, slide]);
  const acceptedCount = suggestions.filter((s) => s.status === 'accepted' || s.status === 'edited').length;

  useEffect(() => {
    if (!job || ['completed', 'failed', 'awaiting_approval'].includes(job.status)) return;
    const timer = setInterval(async () => { const res = await fetch(`${API}/api/jobs/${job.id}`); if (res.ok) setJob(await res.json()); }, 1200);
    return () => clearInterval(timer);
  }, [job]);

  useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(''), 2600); return () => clearTimeout(t); }, [toast]);

  async function uploadFile(file: File) {
    setUploading(true); setFileName(file.name);
    const form = new FormData(); form.append('pptx', file); form.append('rubric_text', '商业价值、技术表达、内容结构、视觉呈现');
    try { const res = await fetch(`${API}/api/projects`, { method: 'POST', body: form }); if (!res.ok) throw new Error('上传失败'); const data = await res.json(); setProjectId(data.project_id); const jobRes = await fetch(`${API}/api/jobs/${data.job_id}`); setJob(await jobRes.json()); setToast('文件已上传，正在生成诊断'); } catch { setToast('已切换到演示数据，后端连接后可处理真实文件'); } finally { setUploading(false); }
  }

  function updateSuggestion(id: string, status: string) { setSuggestions((current) => current.map((s) => s.id === id ? { ...s, status } : s)); setToast(status === 'accepted' ? '建议已加入修改计划' : '已暂不修改'); }

  async function exportRevision() {
    const ids = suggestions.filter((s) => s.status === 'accepted' || s.status === 'edited').map((s) => s.id);
    if (!ids.length) { setToast('请先接受至少一条建议'); return; }
    if (!job) { setToast('演示模式：已模拟完成修改与质检'); return; }
    setExporting(true);
    await fetch(`${API}/api/jobs/${job.id}/revisions`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ suggestion_ids: ids }) });
    setToast('修改任务已启动，请稍候'); setExporting(false);
  }

  const currentSlide = demoSlides[slide - 1];
  return <main className="app-shell">
    <aside className="sidebar">
      <div className="brand"><IconMark /><span>赛智 PPT</span></div>
      <button className="new-project" onClick={() => inputRef.current?.click()}><Plus size={17} />新建项目</button>
      <button className="upload-button" onClick={() => inputRef.current?.click()}><Upload size={16} />上传 PPTX</button>
      <input ref={inputRef} type="file" accept=".pptx" hidden onChange={(e) => e.target.files?.[0] && uploadFile(e.target.files[0])} />
      <nav className="nav-list">
        {[['评分标准', FileText], ['故事线诊断', Sparkles], ['逐页建议', LayoutGrid], ['修改与导出', Download]].map(([label, I]) => <button key={label as string} className={`nav-item ${activeNav === label ? 'active' : ''}`} onClick={() => { setActiveNav(label as string); if (label === '修改与导出') setTab('修改与导出'); }}><I size={17} />{label as string}</button>)}
      </nav>
      <div className="project-list"><div className="list-heading"><span>我的项目</span><span className="muted">最近更新 ↕</span></div><div className="project-item selected"><div className="project-title">{fileName.replace('.pptx', '')}</div><div className="project-date">2024-05-20 14:32</div></div>{['AI驱动的智慧仓储系统', '面向低空经济的航线规划平台', '新型可降解材料的研发与应用', '基于大数据的精准医疗解决方案'].map((x, i) => <div className="project-item" key={x}><div className="project-title">{x}</div><div className="project-date">2024-05-{19 - i} {['09:41', '16:08', '11:23', '10:15'][i]}</div></div>)}</div>
      <button className="collapse"><ChevronLeft size={15} />收起侧栏</button>
    </aside>
    <section className="workspace">
      <header className="topbar"><div className="workflow">{['上传', '解析', '诊断', '确认', '导出'].map((step, i) => <div className={`workflow-step ${i < 3 ? 'done' : i === 3 ? 'current' : ''}`} key={step}><span>{i < 3 ? <Check size={14} /> : i + 1}</span><b>{step}</b>{i < 4 && <i />}</div>)}</div></header>
      <div className="filebar"><div className="file-meta"><div className="ppt-icon">P</div><strong>{fileName}</strong><span>25.6 MB</span><span>| 共 18 页</span></div><div className="status-chip"><span />分析已完成</div></div>
      <div className="content-grid">
        <section className="slides-pane"><div className="pane-title"><div><span className="eyebrow">幻灯片</span><strong>{slide} <small>/ 18</small></strong></div><div className="canvas-tools"><button><LayoutGrid size={15} />缩略图</button><button>−</button><span>62%</span><button>＋</button><button>⛶</button></div></div><div className="slide-body"><div className="thumb-rail">{demoSlides.map((s) => <button className={`thumb ${s.n === slide ? 'selected' : ''}`} onClick={() => setSlide(s.n)} key={s.n}><span>{s.n}</span><div className={`mini-slide ${s.accent}`}><b>{s.title}</b><small>{s.sub}</small><em /></div></button>)}<button className="more-slides">⌄</button></div><div className="canvas-wrap"><div className={`slide-canvas ${currentSlide.accent}`}><div className="canvas-grid" /><div className="canvas-copy"><h1>{currentSlide.title}</h1><h2>{currentSlide.sub}</h2><div className="line" /><p>让每一度电更高效、更安全、更智能</p><div className="meta-lines"><span>◉　参赛团队：光台智联团队</span><span>▥　所属单位：XX大学</span><span>▣　2024年5月20日</span></div></div><div className="solar-art"><div className="sun" /><div className="city" /><div className="panel" /><div className="turbine"><i /><b /><em /></div></div></div><div className="speaker-note"><div className="note-title">演讲备注 <span>（原文）</span></div><p>本项目致力于解决分布式光伏运维中存在的效率低、故障响应慢、数据孤岛等问题，通过物联网、大数据与 AI 技术，构建一体化智能运维平台，实现全面感知、智能诊断与高效运维。</p></div></div></div></section>
        <aside className="inspector"><div className="tabs">{['评分标准', '故事线诊断', '逐页建议', '修改与导出'].map((x) => <button className={tab === x ? 'active' : ''} onClick={() => setTab(x)} key={x}>{x}</button>)}</div>{tab === '逐页建议' ? <><div className="inspector-head"><div><span>幻灯片 1</span><strong> {currentSlide.title}</strong></div><div>本页得分：<b className="score">72</b> / 100</div></div><div className="filters"><span>全部建议（{visibleSuggestions.length}）⌄</span><span><i className="dot red" />严重（2）</span><span><i className="dot amber" />一般（1）</span><span><i className="dot blue" />轻微（1）</span></div><div className="suggestions">{visibleSuggestions.map((s) => <SuggestionCard key={s.id} suggestion={s} onUpdate={updateSuggestion} />)}</div></> : <div className="alt-panel">{tab === '故事线诊断' ? <Storyline job={job} /> : tab === '评分标准' ? <Rubric /> : <ExportPanel acceptedCount={acceptedCount} onExport={exportRevision} exporting={exporting} job={job} projectId={projectId} />}</div>}</aside>
      </div>
    </section>
    {uploading && <div className="toast"><Loader2 className="spin" size={16} />正在校验并解析 PPTX…</div>}{toast && <div className="toast">{toast}</div>}
  </main>;
}

function SuggestionCard({ suggestion: s, onUpdate }: { suggestion: Suggestion; onUpdate: (id: string, status: string) => void }) { const severityLabel = s.severity === 'high' ? '严重' : s.severity === 'medium' ? '一般' : '轻微'; return <article className={`suggestion ${s.severity} ${s.status !== 'pending' ? 'resolved' : ''}`}><div className="suggestion-top"><span className="severity">{severityLabel}</span><span className="category">{s.category}</span></div><h3>{s.title}</h3><p>{s.description}</p><p className="action"><strong>建议：</strong>{s.action}</p><div className="rationale"><span>评分标准：</span>{s.rationale.replace('评分标准：', '')}</div><div className="card-footer"><span className={`automation ${s.automation}`}>{s.automation === 'safe_auto' ? '可自动执行' : '需人工确认'}</span>{s.status === 'pending' ? <div><button className="accept" onClick={() => onUpdate(s.id, 'accepted')}><Check size={14} />接受建议</button><button className="reject" onClick={() => onUpdate(s.id, 'rejected')}><X size={14} />暂不修改</button></div> : <span className="done-label"><Check size={14} />{s.status === 'accepted' ? '已加入修改计划' : '已跳过'}</span>}</div></article>; }
function Storyline({ job }: { job: Job | null }) { const s = job?.storyline || { audience: '科技商业比赛评委', thesis: '用可验证的技术方案解决真实场景中的高价值问题', stages: ['问题与机会', '技术方案', '验证与壁垒', '商业化与团队'], coverage: { 商业价值: 72, 技术表达: 78, 内容结构: 68, 视觉呈现: 74 }, gaps: ['首屏痛点和价值主张还可以更直接', '商业化路径缺少时间节点与量化证据'] }; return <div className="storyline"><h2>故事线诊断</h2><p className="lead">面向 <b>{s.audience}</b>，当前 PPT 的核心主张是：</p><blockquote>{s.thesis}</blockquote><div className="story-stages">{s.stages.map((x, i) => <div key={x}><span>0{i + 1}</span><b>{x}</b></div>)}</div><h3>评分覆盖</h3>{Object.entries(s.coverage).map(([k, v]) => <div className="coverage" key={k}><span>{k}</span><div><i style={{ width: `${v}%` }} /></div><b>{v}</b></div>)}<h3>优先补强</h3><ul>{s.gaps.map((x) => <li key={x}>{x}</li>)}</ul></div>; }
function Rubric() { return <div className="storyline"><h2>评分标准</h2><p className="lead">已从评分标准中提取 4 个核心维度。</p>{[['商业价值', '15 分', '痛点、用户、市场与价值主张'], ['技术表达', '20 分', '原理、创新性、可行性与壁垒'], ['内容结构', '10 分', '故事线、证据链与重点层级'], ['视觉呈现', '10 分', '可读性、规范性与现场表达']].map(([a, b, c]) => <div className="rubric-row" key={a}><div><b>{a}</b><span>{c}</span></div><p>{c}</p></div>)}</div>; }
function ExportPanel({ acceptedCount, onExport, exporting, job, projectId }: { acceptedCount: number; onExport: () => void; exporting: boolean; job: Job | null; projectId: string | null }) { return <div className="storyline export-panel"><h2>修改与导出</h2><div className="export-count"><strong>{acceptedCount}</strong><span>条建议已加入修改计划</span></div><div className="check-list">{(job?.quality?.checks || [{ name: '原主题保留', passed: true }, { name: '元素完整性', passed: true }, { name: '溢出与重叠', passed: true }]).map((c) => <div key={c.name}><Check size={15} />{c.name}<span>通过</span></div>)}</div><button className="export-button" onClick={onExport} disabled={exporting}>{exporting ? <Loader2 className="spin" size={16} /> : <Download size={16} />}生成修改版 PPTX</button>{job?.status === 'completed' && projectId && <a className="download-link" href={`${API}/api/jobs/${job.id}/download`}>下载导出文件</a>}</div>; }
