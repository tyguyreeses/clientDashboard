export function SelectField({
  label,
  value,
  onChange,
  options,
  required = false,
}) {
  return (
    <label className="editable-field">
      <span>{label}</span>
      <div>
        <select
          value={value}
          required={required}
          onChange={(event) => onChange(event.target.value)}
        >
          <option value="">Select one</option>
          {options.map(([option, text]) => (
            <option key={option} value={option}>
              {text}
            </option>
          ))}
        </select>
      </div>
    </label>
  );
}
export function BooleanField({ label, value, onChange }) {
  return (
    <SelectField
      label={label}
      value={value == null ? "" : String(value)}
      onChange={(value) => onChange(value === "" ? null : value === "true")}
      options={[
        ["true", "Yes"],
        ["false", "No"],
      ]}
    />
  );
}
export function Detail({ label, value }) {
  return (
    <div className="detail">
      <small>{label}</small>
      <strong>{value || "—"}</strong>
    </div>
  );
}
export function Editable({
  label,
  value,
  onChange,
  type = "text",
  required = false,
  step,
  min,
  max,
}) {
  return (
    <label className="editable-field">
      <span>{label}</span>
      <div>
        <input
          type={type}
          step={step}
          min={min}
          max={max}
          value={value || ""}
          required={required}
          onChange={(event) => onChange(event.target.value)}
        />
      </div>
    </label>
  );
}
