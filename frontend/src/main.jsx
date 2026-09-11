import React, { useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'

const STATUS = {
  0: { label: 'Cancelled', tone: 'cancelled' },
  1: { label: 'Inquired', tone: 'inquired' },
  2: { label: 'Responded', tone: 'responded' },
  3: { label: 'Awaiting deposit', tone: 'awaiting' },
  4: { label: 'Deposit received', tone: 'booked' },
}

const TRIAL_STATUS = {
  not_interested: 'Not interested',
  interested: 'Interested',
  link_sent: 'Link sent',
  booked: 'Booked',
  cancelled: 'Cancelled',
}

const demoWeddings = [
  {
    id: 1, clientId: 1, name: 'Amelia Rose', initials: 'AR', email: 'amelia.rose@example.com',
    phone: '(720) 555-0138', weddingDate: '2026-10-03', location: 'The Lyons Farmette',
    readyBy: '7:30 AM', status: 3, bridalTrialStatus: 'link_sent', bridalTrialNotes: 'Sent the style guide and sign-up link.',
    people: 7, assistant: true, miles: 38, source: 'Instagram', notes: 'Loves soft texture and an unfussy veil moment.',
    balance: 1_040, paid: '$520 deposit · Venmo', party: 'Bride + 5 attendants + flower girl',
  },
  {
    id: 2, clientId: 2, name: 'Sophie Bennett', initials: 'SB', email: 'sophie.bennett@example.com',
    phone: '(303) 555-0194', weddingDate: '2026-09-19', location: 'The St. Julien Hotel',
    readyBy: '8:00 AM', status: 2, bridalTrialStatus: 'interested', bridalTrialNotes: 'Wants to decide after venue walkthrough.',
    people: 4, assistant: false, miles: 12, source: 'Referral', notes: 'Classic chignon with face-framing pieces.',
    balance: 760, paid: 'No payment yet', party: 'Bride + 3 attendants',
  },
  {
    id: 3, clientId: 3, name: 'Madeline Chen', initials: 'MC', email: 'madeline.chen@example.com',
    phone: '(303) 555-0172', weddingDate: '2026-08-22', location: 'Denver Botanic Gardens',
    readyBy: '6:30 AM', status: 4, bridalTrialStatus: 'booked', bridalTrialNotes: 'Trial booked for July 18 at 2:00 PM.',
    people: 9, assistant: true, miles: 18, source: 'Website', notes: 'Big, airy bun with pearl pins.',
    balance: 620, paid: '$620 deposit · Card', party: 'Bride + 7 attendants',
  },
  {
    id: 4, clientId: 4, name: 'Clara Whitmore', initials: 'CW', email: 'clara.whitmore@example.com',
    phone: '(303) 555-0158', weddingDate: '2025-09-14', location: 'Boulder Creek House',
    readyBy: '8:30 AM', status: 4, bridalTrialStatus: 'cancelled', bridalTrialNotes: 'Trial cancelled; bride chose to keep her natural texture.',
    people: 6, assistant: false, miles: 22, source: 'Referral', notes: 'The sweetest garden party morning.',
    balance: 0, paid: '$1,240 paid · Card', party: 'Bride + 5 attendants',
  },
  {
    id: 5, clientId: 5, name: 'Nora Ellis', initials: 'NE', email: 'nora.ellis@example.com',
    phone: '(720) 555-0161', weddingDate: '2025-06-07', location: 'The Broadmoor',
    readyBy: '7:00 AM', status: 0, bridalTrialStatus: 'not_interested', bridalTrialNotes: 'No trial requested.',
    people: 3, assistant: false, miles: 74, source: 'Website', notes: 'Cancelled due to a change in wedding plans.',
    balance: 0, paid: 'Deposit refunded · Card', party: 'Bride + 2 attendants',
  },
]

const formatDate = (value) => new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(`${value}T12:00:00`))
const formatMoney = (value) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value)
const dueDate = (value) => {
  const date = new Date(`${value}T12:00:00`)
  date.setDate(date.getDate() - 1)
  return `${new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric' }).format(date)} at 8:00 PM`
}

function App() {
  const [weddings, setWeddings] = useState(demoWeddings)
  const [selected, setSelected] = useState(null)
  const [copied, setCopied] = useState(null)

  const updateStatus = (id, status) => setWeddings((items) => items.map((item) => item.id === id ? { ...item, status: Number(status) } : item))
  const copyMessage = async (wedding) => {
    const message = `Hi ${wedding.name.split(' ')[0]}! I’m excited to celebrate with you on ${formatDate(wedding.weddingDate)}.`
    try { await navigator.clipboard.writeText(message) } catch { /* visual-only fallback */ }
    setCopied(wedding.id)
    window.setTimeout(() => setCopied(null), 1400)
  }

  const groups = useMemo(() => {
    const today = new Date('2026-09-10T12:00:00')
    const sortItems = (items) => [...items].sort((a, b) => a.status - b.status || a.weddingDate.localeCompare(b.weddingDate))
    return [
      { key: 'inquiries', label: 'Inquiries', subtitle: 'Warm leads waiting for their next little yes', color: 'coral', items: sortItems(weddings.filter((item) => item.status > 0 && item.status < 4)) },
      { key: 'books', label: 'On the Books', subtitle: 'Beautiful days that are officially yours', color: 'mint', items: sortItems(weddings.filter((item) => item.status === 4 && new Date(`${item.weddingDate}T12:00:00`) >= today)) },
      { key: 'history', label: 'History', subtitle: 'Past celebrations and archived stories', color: 'lilac', items: sortItems(weddings.filter((item) => item.status === 0 || new Date(`${item.weddingDate}T12:00:00`) < today)) },
    ]
  }, [weddings])

  return (
    <div className="app-shell">
      <Header />
      {selected ? <ProfilePage wedding={selected} onClose={() => setSelected(null)} onStatus={updateStatus} /> : <main className="dashboard">
        <div className="welcome-row">
          <div>
            <p className="eyebrow">Your little corner of calm</p>
            <h1>Good morning, Tyler <span className="wave">✦</span></h1>
            <p className="subtitle">A soft landing for every beautiful wedding detail.</p>
          </div>
          <div className="dashboard-date"><span className="sun-dot" /> September 10, 2026</div>
        </div>
        <div className="stats-row">
          <Stat label="Upcoming celebrations" value={weddings.filter((item) => item.status === 4).length} accent="peach" />
          <Stat label="Awaiting a deposit" value={weddings.filter((item) => item.status === 3).length} accent="butter" />
          <Stat label="Balance to collect" value={formatMoney(weddings.reduce((sum, item) => sum + item.balance, 0))} accent="lavender" />
        </div>
        <div className="board-toolbar"><div><strong>Wedding board</strong><span> · keep the good stuff moving</span></div><button className="filter-button">☷ &nbsp; All weddings <span>⌄</span></button></div>
        <div className="board">
          {groups.map((group) => <WeddingSection key={group.key} group={group} onSelect={setSelected} onStatus={updateStatus} onCopy={copyMessage} copied={copied} />)}
        </div>
      </main>}
      <Footer />
    </div>
  )
}

function Header() { return <header className="site-header"><a className="brand" href="#"><span className="brand-mark">✿</span><span>blossom <i>&</i> veil</span></a><nav><a className="active" href="#board">Wedding board</a><a href="#calendar">Calendar <small>soon</small></a><a href="#finances">Finances <small>soon</small></a></nav><button className="avatar" aria-label="Open profile">TR</button></header> }
function Footer() { return <footer className="site-footer"><span><span className="footer-flower">✿</span> made for beautiful beginnings</span><span>Client dashboard · visual preview</span></footer> }
function Stat({ label, value, accent }) { return <div className={`stat-card ${accent}`}><span>{label}</span><strong>{value}</strong><b>↗</b></div> }

function WeddingSection({ group, onSelect, onStatus, onCopy, copied }) {
  const [open, setOpen] = useState(true)
  return <section className="wedding-section">
    <button className={`section-heading ${group.color}`} onClick={() => setOpen(!open)}><span className="chevron">{open ? '⌄' : '›'}</span><span className="section-dot" /><span className="section-title">{group.label}</span><span className="count">{group.items.length}</span><span className="section-subtitle">{group.subtitle}</span><span className="section-sparkle">✦</span></button>
    {open && <div className="rows">{group.items.length ? group.items.map((wedding) => <WeddingRow key={wedding.id} wedding={wedding} onSelect={onSelect} onStatus={onStatus} onCopy={onCopy} copied={copied === wedding.id} />) : <div className="empty-row">Nothing here yet — a lovely blank canvas.</div>}</div>}
  </section>
}

function WeddingRow({ wedding, onSelect, onStatus, onCopy, copied }) {
  const status = STATUS[wedding.status]
  return <div className="wedding-row" onClick={() => onSelect(wedding)}>
    <div className="bride-cell"><span className="initials">{wedding.initials}</span><div><strong>{wedding.name}</strong><small>{wedding.source} · {wedding.people} people</small></div></div>
    <div className="date-cell"><strong>{formatDate(wedding.weddingDate)}</strong><small>{wedding.readyBy} · {wedding.location}</small></div>
    <div className="trial-cell"><span className={`trial-pill ${wedding.bridalTrialStatus}`}>✦ {TRIAL_STATUS[wedding.bridalTrialStatus]}</span></div>
    <div className="balance-cell"><small>balance</small><strong>{formatMoney(wedding.balance)}</strong></div>
    <div className="status-cell" onClick={(event) => event.stopPropagation()}><select className={`status-select ${status.tone}`} value={wedding.status} onChange={(event) => onStatus(wedding.id, event.target.value)} aria-label={`Status for ${wedding.name}`}>{Object.entries(STATUS).map(([value, option]) => <option key={value} value={value}>{option.label}</option>)}</select></div>
    <button className={`copy-button ${copied ? 'copied' : ''}`} onClick={(event) => { event.stopPropagation(); onCopy(wedding) }}>{copied ? 'Copied ✦' : 'Copy message'}</button>
  </div>
}

function ProfilePage({ wedding, onClose, onStatus }) {
  const [draft, setDraft] = useState(wedding)
  const update = (field, value) => setDraft((item) => ({ ...item, [field]: value }))
  return <main className="profile-page">
    <button className="back-button" onClick={onClose}>← Back to wedding board</button>
    <div className="profile-hero"><span className="large-initials">{draft.initials}</span><div><p className="eyebrow">Client profile</p><h1>{draft.name}</h1><p>{draft.email} · {draft.phone}</p></div><span className="profile-save">Visual preview · changes are local</span></div>
    <section className="profile-section"><div className="profile-section-title"><span className="section-number peach-number">01</span><div><p className="eyebrow">The big picture</p><h2>Inquiry summary</h2></div></div><div className="detail-grid editable-grid"><Editable label="Bride name" value={draft.name} onChange={(value) => update('name', value)} /><Editable label="Email" value={draft.email} onChange={(value) => update('email', value)} /><Editable label="Wedding date" type="date" value={draft.weddingDate} onChange={(value) => update('weddingDate', value)} /><Editable label="Location" value={draft.location} onChange={(value) => update('location', value)} /><Editable label="Ready by" value={draft.readyBy} onChange={(value) => update('readyBy', value)} /><Editable label="People / services" value={draft.people} type="number" onChange={(value) => update('people', value)} /><Editable label="Balance remaining" value={draft.balance} type="number" onChange={(value) => update('balance', value)} prefix="$" /><Detail label="Due by" value={dueDate(draft.weddingDate)} /><Detail label="Payment information" value={draft.paid} /><Editable label="Phone" value={draft.phone} onChange={(value) => update('phone', value)} /><Detail label="Assistant" value={draft.assistant ? 'Assistant included' : 'Solo appointment'} /><div className="editable-select"><label>Workflow status</label><select className={`status-select ${STATUS[draft.status].tone}`} value={draft.status} onChange={(e) => { update('status', Number(e.target.value)); onStatus(draft.id, e.target.value) }}>{Object.entries(STATUS).map(([value, option]) => <option key={value} value={value}>{option.label}</option>)}</select></div></div></section>
    <section className="profile-section trial-section"><div className="profile-section-title"><span className="section-number lilac-number">02</span><div><p className="eyebrow">A little extra magic</p><h2>Bridal trial & details</h2></div></div><div className="editable-select"><label>Bridal trial status</label><select value={draft.bridalTrialStatus} onChange={(e) => update('bridalTrialStatus', e.target.value)}>{Object.entries(TRIAL_STATUS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div><Editable label="Services / party" value={draft.party} onChange={(value) => update('party', value)} /><label className="notes-label">Notes<textarea value={draft.notes} onChange={(e) => update('notes', e.target.value)} /></label><p className="trial-note">Trial details and edits will connect to the API once the visual workflow is approved.</p></section>
    <section className="profile-section invoice-section"><div className="profile-section-title"><span className="section-number mint-number">03</span><div><p className="eyebrow">The numbers, softly</p><h2>Invoice preview</h2></div></div><div className="invoice-card"><div><span>Current invoice</span><strong>Version 1 · draft preview</strong></div><div className="invoice-total"><small>Remaining</small><strong>{formatMoney(draft.balance)}</strong></div></div><button className="full-button">Open full invoice <span>↗</span></button></section>
  </main>
}
function Detail({ label, value }) { return <div className="detail"><small>{label}</small><strong>{value}</strong></div> }
function Editable({ label, value, onChange, type = 'text', prefix }) { return <label className="editable-field"><span>{label}</span><div>{prefix && <b>{prefix}</b>}<input type={type} value={value} onChange={(event) => onChange(type === 'number' ? Number(event.target.value) : event.target.value)} /></div></label> }

createRoot(document.getElementById('root')).render(<App />)
