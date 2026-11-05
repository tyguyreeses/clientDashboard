import { STATUS, TRIAL_STATUS, formatDate, formatDateTime, formatMoney } from "../utils";

export function WeddingRow({ wedding, onSelect, onStatus }) {
  const status = STATUS[wedding.status];
  return (
    <div className="wedding-row" onClick={() => onSelect(wedding)}>
      <div className="bride-cell">
        <span className="initials">{wedding.initials}</span>
        <div>
          <strong>{wedding.name}</strong>
          <small>
            {wedding.source} · {wedding.people || 0} people
          </small>
        </div>
      </div>
      <div className="date-cell">
        <strong>{formatDate(wedding.weddingDate)}</strong>
        <small>
          {wedding.readyByLabel} · {wedding.address}
        </small>
      </div>
      <div className="trial-cell">
        <span className={`trial-pill ${wedding.bridalTrialStatus}`}>
          ✦ {TRIAL_STATUS[wedding.bridalTrialStatus]}
        </span>
      </div>
      <div className="balance-cell">
        <small>balance</small>
        <strong>{formatMoney(wedding.balance)}</strong>
      </div>
      <div className="status-cell" onClick={(event) => event.stopPropagation()}>
        {wedding.status === 2 && wedding.invoiceSentAt && <small>Sent {formatDateTime(wedding.invoiceSentAt)}</small>}
        <select
          className={`status-select ${status.tone}`}
          value={wedding.status}
          onChange={(event) => onStatus(wedding, event.target.value)}
          aria-label={`Status for ${wedding.name}`}
        >
          {Object.entries(STATUS).map(([value, option]) => (
            <option key={value} value={value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
      <span className="row-arrow">›</span>
    </div>
  );
}
