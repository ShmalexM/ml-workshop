import {useCallback, useEffect, useRef, useState} from 'react'
import {CheckCircle2, Download, ExternalLink, LoaderCircle, RefreshCw} from 'lucide-react'
import {api} from '../api'
import {version as bundledVersion} from '../../package.json'
import './appUpdate.css'

type UpdateStatus = 'idle' | 'checking' | 'updating' | 'restarting' | 'updated' | 'error'
type UpdateInfo = {
  installed: boolean
  supported: boolean
  currentVersion: string
  latestVersion: string | null
  updateAvailable: boolean
  status: UpdateStatus
  message: string
  error: string | null
  releaseUrl: string
  checkedAt: string | null
}
const active = (status?: UpdateStatus) => status === 'checking' || status === 'updating' || status === 'restarting'
const installing = (status?: UpdateStatus) => status === 'updating' || status === 'restarting'
const errorMessage = (error: unknown) => error instanceof Error ? error.message : 'The local server could not check for updates.'

export default function AppUpdate() {
  const [info, setInfo] = useState<UpdateInfo | null>(null)
  const [pending, setPending] = useState<'load' | 'check' | 'apply' | null>('load')
  const [requestError, setRequestError] = useState('')
  const [reconnecting, setReconnecting] = useState(false)
  const [pollPaused, setPollPaused] = useState(false)
  const [lastAction, setLastAction] = useState<'check' | 'apply'>('check')
  const tracking = useRef<{version: string} | null>(null)
  const disconnectedAt = useRef<number | null>(null)
  const requestInFlight = useRef(false)

  const receive = useCallback((next: UpdateInfo) => {
    if (installing(next.status) && !tracking.current) tracking.current = {version: next.currentVersion}
    setInfo(next); setReconnecting(false); disconnectedAt.current = null
    if (tracking.current && (next.currentVersion !== tracking.current.version || next.status === 'updated')) {
      // The session token and page route survive a server restart. Reload to use the new frontend too.
      tracking.current = null
      location.reload()
    } else if (next.status === 'error') tracking.current = null
  }, [])

  useEffect(() => {
    let live = true
    void (async () => {
      try {
        const current = await api<UpdateInfo>('/update')
        if (!live) return
        receive(current)
        if (!active(current.status)) {
          setPending('check')
          const checked = await api<UpdateInfo>('/update/check', {})
          if (live) receive(checked)
        }
      } catch (error) {if (live) setRequestError(errorMessage(error))}
      finally {if (live) setPending(null)}
    })()
    return () => {live = false}
  }, [receive])

  useEffect(() => {
    if (pollPaused || (!active(info?.status) && !reconnecting)) return
    let live = true
    let timer: ReturnType<typeof setTimeout>
    async function poll() {
      try {
        const next = await api<UpdateInfo>('/update')
        if (!live) return
        receive(next)
        setRequestError('')
        if (active(next.status)) timer = setTimeout(() => void poll(), 1200)
        else if (tracking.current) {
          // An interrupted apply request may never have reached the server. Do not submit it again automatically.
          tracking.current = null
          setRequestError('The update is not running. Try Update and restart again.')
        }
      } catch (error) {
        if (!live) return
        if (!tracking.current) {
          setRequestError(errorMessage(error)); setPollPaused(true)
          return
        }
        disconnectedAt.current ??= Date.now()
        setReconnecting(true)
        if (Date.now() - disconnectedAt.current >= 90_000) {
          setRequestError('The app is taking longer to reconnect. Reopen Engineering Workshop, or retry the connection here.')
          setPollPaused(true)
        } else timer = setTimeout(() => void poll(), 1200)
      }
    }
    timer = setTimeout(() => void poll(), 1200)
    return () => {live = false; clearTimeout(timer)}
  }, [info?.status, reconnecting, pollPaused, receive])

  async function check() {
    if (requestInFlight.current || active(info?.status) || reconnecting) return
    requestInFlight.current = true
    setPending('check'); setLastAction('check'); setRequestError(''); setPollPaused(false)
    try {
      // Retry the initial status read too, so a failed first connection does not hide the install type.
      if (!info) {
        const current = await api<UpdateInfo>('/update')
        receive(current)
        if (active(current.status)) return
      }
      receive(await api<UpdateInfo>('/update/check', {}))
    } catch (error) {setRequestError(errorMessage(error))}
    finally {requestInFlight.current = false; setPending(null)}
  }

  async function apply() {
    if (!info?.supported || !info.updateAvailable || requestInFlight.current || active(info.status) || reconnecting) return
    requestInFlight.current = true
    tracking.current = {version: info.currentVersion}
    setPending('apply'); setLastAction('apply'); setRequestError(''); setPollPaused(false)
    try {receive(await api<UpdateInfo>('/update/apply', {}))}
    catch (error) {
      // A disconnect can mean the update already started. Read its status before offering another apply.
      try {
        const current = await api<UpdateInfo>('/update')
        receive(current)
        if (!active(current.status)) tracking.current = null
      }
      catch {setReconnecting(true)}
      setRequestError(errorMessage(error))
    } finally {requestInFlight.current = false; setPending(null)}
  }

  function retryConnection() {setRequestError(''); disconnectedAt.current = null; setPollPaused(false); setReconnecting(true)}
  const busy = pending !== null || active(info?.status) || reconnecting
  const error = requestError || info?.error
  const updateAvailable = !!info?.supported && info.updateAvailable && info.status !== 'error'
  const status = reconnecting ? (tracking.current ? 'Reconnecting after the update…' : 'Reconnecting to Engineering Workshop…') : pending === 'apply' ? 'Starting the update…' : pending === 'check' ? 'Checking for updates…' : pending === 'load' ? 'Reading app version…' : info?.message
  const releaseUrl = info?.releaseUrl?.startsWith('https://github.com/ShmalexM/ml-workshop/releases') ? info.releaseUrl : null

  return <section className="app-update" aria-labelledby="app-update-heading">
    <h3 id="app-update-heading">App updates</h3>
    <dl className="app-update-versions"><div><dt>Installed version</dt><dd>{info?.currentVersion ?? bundledVersion}</dd></div>{info?.latestVersion && <div><dt>Latest version</dt><dd>{info.latestVersion}</dd></div>}</dl>
    <p className="app-update-status" role="status" data-state={info?.status ?? 'loading'}>{busy && !pollPaused ? <LoaderCircle size={15} className="spin"/> : info && !info.updateAvailable && !error ? <CheckCircle2 size={15}/> : null}<span>{status}</span></p>
    {error && <p className="app-update-error" role="alert">{error}</p>}
    {info?.installed && info.supported && <p className="app-update-note">Updates restart the app and keep your lessons, books and progress on this computer.</p>}
    {info && !info.installed && <p className="app-update-note">This copy runs from a source checkout. To update it, export your progress, stop the app, run <code>git pull --ff-only</code> in the project folder, then run setup again.</p>}
    <div className="app-update-actions">
      {pollPaused ? <button className="secondary-button" onClick={retryConnection}><RefreshCw size={15}/>Retry connection</button> : <>
        {updateAvailable && <button className="primary-button" disabled={busy} onClick={() => void apply()}><Download size={15}/>{lastAction === 'apply' && error && !busy ? 'Retry update and restart' : 'Update and restart'}</button>}
        <button className="secondary-button" disabled={busy} onClick={() => void check()}><RefreshCw size={15}/>{error && lastAction === 'check' ? 'Retry check' : 'Check for updates'}</button>
      </>}
      {releaseUrl && <a href={releaseUrl} target="_blank" rel="noreferrer">Release notes<ExternalLink size={13}/></a>}
    </div>
  </section>
}
