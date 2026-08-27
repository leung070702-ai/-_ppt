import Link from "next/link";

function UploadIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 32 32" className="upload-icon">
      <path d="M16 21V6m0 0-5 5m5-5 5 5M7 19v5a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-5" />
    </svg>
  );
}

export default function UploadPage() {
  return (
    <main className="site-shell">
      <header className="topbar">
        <Link href="/" className="brand" aria-label="返回首页">
          <span className="brand-mark" aria-hidden="true">研</span>
          <span>科研竞赛 PPT 修改工作流</span>
        </Link>
        <Link href="/" className="back-link">返回首页</Link>
      </header>

      <section className="upload-page" aria-labelledby="upload-title">
        <div className="upload-heading">
          <p className="section-kicker">STEP 01 · PREPARE</p>
          <h1 id="upload-title">上传演示文稿</h1>
          <p>先放入需要审阅的研究演示，下一步将用于生成可确认的修改方案。</p>
        </div>

        <label className="dropzone" htmlFor="ppt-file">
          <input id="ppt-file" type="file" accept=".pptx" className="visually-hidden" />
          <span className="upload-icon-wrap"><UploadIcon /></span>
          <span className="dropzone-title">拖拽 .pptx 文件到这里</span>
          <span className="dropzone-subtitle">或点击选择文件</span>
          <span className="dropzone-format">仅支持 PowerPoint 演示文稿（.pptx）</span>
        </label>

        <div className="static-notice" role="note">
          <span className="notice-icon" aria-hidden="true">i</span>
          当前为静态界面，暂未连接真实上传。原始文件保护与校验将在后续里程碑接入。
        </div>

        <div className="upload-actions">
          <Link href="/" className="button button-secondary">取消</Link>
          <button type="button" className="button button-disabled" disabled>继续</button>
        </div>
      </section>
    </main>
  );
}
