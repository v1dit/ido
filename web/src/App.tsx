import { FormEvent, useEffect, useState } from 'react'

const REPOSITORY = 'https://github.com/v1shay/ido'
const RELEASES = `${REPOSITORY}/releases/latest/download`
const IS_LOCAL =
  typeof window !== 'undefined' &&
  ['localhost', '127.0.0.1'].includes(window.location.hostname)
const BLENDER_ADDON = IS_LOCAL
  ? '/downloads/cad_agent.zip'
  : `${RELEASES}/cad_agent.zip`

type Tool = 'blender' | 'openscad'
type RuntimeStatus = {
  tool: Tool | 'companion'
  phase: string
  message: string
  artifacts: Record<string, string>
  recent_errors: string[]
}

const downloadLinks = [
  ['macOS', `${RELEASES}/ido-macos.dmg`, 'Apple Silicon + Intel'],
  ['Windows', `${RELEASES}/ido-windows.exe`, 'Windows 10 and 11'],
  ['Linux', `${RELEASES}/ido-linux.AppImage`, 'AppImage'],
] as const

function ArrowIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 12h13M13 6l6 6-6 6" />
    </svg>
  )
}

function CopyIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="8" y="8" width="11" height="11" />
      <path d="M16 8V5H5v11h3" />
    </svg>
  )
}

function ToolPreview({ tool }: { tool: Tool }) {
  return (
    <div className={`tool-preview ${tool}`}>
      <div className="preview-toolbar">
        <span>{tool === 'blender' ? 'Layout  Modeling  Sculpting  Shading' : 'ido_current.scad'}</span>
        <span>idō</span>
      </div>
      <div className="preview-body">
        <div className="scene-grid" aria-hidden="true">
          <div className="cad-object">
            <span className="cad-base" />
            <span className="cad-top" />
            <span className="cad-hole" />
          </div>
        </div>
        <div className="preview-sidebar">
          <strong>{tool === 'blender' ? 'idō prompt' : 'OpenSCAD'}</strong>
          <p>{tool === 'blender' ? 'Make a compact enclosure with a cable port.' : 'difference() {'}</p>
          <div className="code-lines">
            <i />
            <i />
            <i />
            <i />
          </div>
          <span className="preview-action">{tool === 'blender' ? 'Generate' : 'Render complete'}</span>
        </div>
      </div>
    </div>
  )
}

function CopyCommand({ command }: { command: string }) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    await navigator.clipboard.writeText(command)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1400)
  }
  return (
    <div className="command">
      <code>{command}</code>
      <button type="button" onClick={copy} aria-label={`Copy ${command}`}>
        <CopyIcon />
        <span>{copied ? 'Copied' : 'Copy'}</span>
      </button>
    </div>
  )
}

function SetupSection({
  id,
  tool,
  title,
  description,
  steps,
  command,
}: {
  id: string
  tool: Tool
  title: string
  description: string
  steps: string[]
  command: string
}) {
  return (
    <section className="setup-section rule-section" id={id}>
      <div className="section-copy">
        <h2>{title}</h2>
        <p>{description}</p>
        <ol className="steps">
          {steps.map((step, index) => (
            <li key={step}>
              <span>{index + 1}</span>
              <p>{step}</p>
            </li>
          ))}
        </ol>
        {tool === 'blender' ? (
          <a className="outline-button" href={BLENDER_ADDON}>
            Download cad_agent.zip <ArrowIcon />
          </a>
        ) : null}
      </div>
      <div className="section-media">
        <ToolPreview tool={tool} />
        <div className="launch-row">
          <div>
            <small>Open {tool === 'blender' ? 'Blender' : 'OpenSCAD'} with idō</small>
            <CopyCommand command={command} />
          </div>
          <div className="pet-status">
            <img src="./ido-pet.svg" alt="Original idō desktop pet" />
            <span>{tool === 'blender' ? 'Blender ready' : 'OpenSCAD ready'}</span>
          </div>
        </div>
      </div>
    </section>
  )
}

function LocalControl() {
  const [tool, setTool] = useState<Tool>('blender')
  const [prompt, setPrompt] = useState('')
  const [status, setStatus] = useState<RuntimeStatus | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const local = ['localhost', '127.0.0.1'].includes(window.location.hostname)

  useEffect(() => {
    if (!local) return
    let active = true
    const refresh = async () => {
      try {
        const response = await fetch('/api/status')
        if (active && response.ok) setStatus(await response.json())
      } catch {
        // The static docs site deliberately has no local API.
      }
    }
    void refresh()
    const timer = window.setInterval(refresh, 1000)
    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [local])

  if (!local) return null

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!prompt.trim()) return
    setSubmitting(true)
    const path = tool === 'openscad' ? '/api/openscad/prompt' : '/api/prompt'
    const payload =
      tool === 'openscad'
        ? { prompt, current_ir: null }
        : { prompt, current_ir: null, target_tool: 'blender' }
    try {
      await fetch(path, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(payload),
      })
      setPrompt('')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="local-control rule-section" aria-label="Local companion controls">
      <div>
        <h2>Local companion</h2>
        <p>{status?.message ?? 'Connected to idō on this machine.'}</p>
      </div>
      <form onSubmit={submit}>
        <select value={tool} onChange={(event) => setTool(event.target.value as Tool)}>
          <option value="blender">Blender</option>
          <option value="openscad">OpenSCAD</option>
        </select>
        <input
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          placeholder="Describe what to build"
        />
        <button disabled={submitting}>{submitting ? 'Working' : 'Prompt'}</button>
      </form>
    </section>
  )
}

export default function App() {
  return (
    <>
      <header className="site-header">
        <a className="brand" href="#top" aria-label="idō home">
          idō
        </a>
        <nav aria-label="Primary navigation">
          <a href="/info/#pipeline">Overview</a>
          <a href="#download">Download</a>
          <a href="#blender">Blender</a>
          <a href="#openscad">OpenSCAD</a>
          <a href="#docs">Docs</a>
        </nav>
        <a className="header-cta" href="#download">
          Get idō
        </a>
      </header>

      <main id="top">
        <section className="hero">
          <div className="hero-heading">
            <h1>Choose how you build.</h1>
            <p>
              Design in Blender. Engineer in OpenSCAD.
              <br />
              One local companion and one pet keeps the work moving.
            </p>
          </div>
          <div className="tool-choice">
            <article>
              <small>DESIGN</small>
              <h2>Blender</h2>
              <p>Install the add-on, prompt inside Blender, and keep your scene editable.</p>
              <a className="outline-button" href="#blender">
                Set up Blender <ArrowIcon />
              </a>
              <ToolPreview tool="blender" />
            </article>
            <div className="shared-pet" aria-label="Shared idō companion">
              <span className="pet-line" />
              <img src="./ido-pet.svg" alt="" />
              <span className="pet-line" />
            </div>
            <article>
              <small>ENGINEERING</small>
              <h2>OpenSCAD</h2>
              <p>Run one command, open the watched SCAD file, and render real parts.</p>
              <a className="outline-button" href="#openscad">
                Set up OpenSCAD <ArrowIcon />
              </a>
              <ToolPreview tool="openscad" />
            </article>
          </div>
        </section>

        <section className="local-first rule-section">
          <div>
            <h2>Designed for local workflows.</h2>
            <p>idō runs on your machine, in your tools. Your files stay local. You stay in control.</p>
          </div>
          <ul>
            <li><strong>Local first</strong><span>Runs on your machine and writes ordinary project files.</span></li>
            <li><strong>Private by default</strong><span>Your local companion owns desktop access.</span></li>
            <li><strong>Built for makers and engineers</strong><span>Use the tools you already know.</span></li>
          </ul>
        </section>

        <LocalControl />

        <SetupSection
          id="blender"
          tool="blender"
          title="Design with Blender."
          description="Install the idō add-on once. Prompt, revise, and inspect Engineering IR without leaving the 3D View."
          steps={[
            'Download the Blender add-on.',
            'Blender → Edit → Preferences → Add-ons → Install from Disk.',
            'Press N and open the idō tab.',
          ]}
          command="ido open blender"
        />

        <SetupSection
          id="openscad"
          tool="openscad"
          title="Engineer with OpenSCAD."
          description="Install the companion, run one command, and let idō update a watched SCAD file with validated geometry and exports."
          steps={[
            'Install OpenSCAD and the idō companion.',
            'Run idō open openscad from your terminal.',
            'Prompt from the CLI, local dashboard, or desktop pet.',
          ]}
          command="ido open openscad"
        />

        <section className="workflow rule-section" id="docs">
          <div className="workflow-heading">
            <h2>One command surface.</h2>
            <p>The same companion starts the API, opens tools, saves project state, and updates the pet.</p>
          </div>
          <div className="command-list">
            <CopyCommand command='ido prompt --tool blender "make a compact enclosure"' />
            <CopyCommand command='ido prompt --tool openscad "add two M4 mounting holes"' />
            <CopyCommand command="ido pet show" />
            <CopyCommand command="ido status" />
          </div>
          <div className="pet-feature">
            <img src="./ido-pet.svg" alt="The original idō desktop companion" />
            <div>
              <h3>Prompt + status, wherever you work.</h3>
              <p>The cross-platform pet opens either tool, accepts prompts, and reports generation, validation, rendering, and errors.</p>
            </div>
          </div>
        </section>

        <section className="downloads rule-section" id="download">
          <div>
            <h2>Download idō.</h2>
            <p>Choose your operating system, then install the Blender add-on or open OpenSCAD from the CLI.</p>
          </div>
          <div className="download-list">
            {downloadLinks.map(([label, href, detail]) => (
              <a href={href} key={label}>
                <strong>{label}</strong>
                <span>{detail}</span>
                <ArrowIcon />
              </a>
            ))}
            <a href={BLENDER_ADDON}>
              <strong>Blender add-on</strong>
              <span>cad_agent.zip</span>
              <ArrowIcon />
            </a>
          </div>
        </section>

        <section className="troubleshooting rule-section">
          <div>
            <h2>Troubleshooting.</h2>
            <p>Start with the companion status, then verify the desktop application is installed.</p>
          </div>
          <div>
            <details>
              <summary>The local dashboard does not open.</summary>
              <p>Run <code>ido status</code>. If needed, run <code>ido serve</code> and open http://127.0.0.1:8010.</p>
            </details>
            <details>
              <summary>Blender cannot reach the backend.</summary>
              <p>Set the add-on backend URL to http://127.0.0.1:8010 and start idō once.</p>
            </details>
            <details>
              <summary>OpenSCAD exports are missing.</summary>
              <p>Confirm the OpenSCAD CLI is installed and available on PATH. The SCAD source is still saved when export tools are unavailable.</p>
            </details>
          </div>
        </section>
      </main>

      <footer>
        <span>idō</span>
        <p>A universal local interface for modeling software.</p>
        <a href={REPOSITORY}>GitHub</a>
      </footer>
    </>
  )
}
