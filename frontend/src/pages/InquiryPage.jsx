import { useState } from "react";

const initialValues = {
  name: "",
  email: "",
  phone: "",
  social_media: "",
  wedding_date: "",
  address: "",
  bride_count: "1",
  party_count: "0",
  junior_count: "0",
  ready_by: "",
  time_firmness: "",
  location_type: "",
  makeup_interest: "",
  bridal_trial: "",
  planning_stage: "",
  recommendations_if_unavailable: "",
  referral_source: "",
  referral_other: "",
  referral_name: "",
  additional_notes: "",
  contact_consent: false,
  website: "",
};

function denverDate() {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Denver",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}

function Choice({ name, label, options, value, onChange, required = true }) {
  return (
    <fieldset className="inquiry-choice">
      <legend>
        {label}
        {required ? " *" : ""}
      </legend>
      <div className="inquiry-options">
        {options.map(([choice, text]) => (
          <label key={choice}>
            <input
              type="radio"
              name={name}
              value={choice}
              checked={value === choice}
              onChange={onChange}
              required={required}
            />{" "}
            {text}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export function InquiryPage() {
  const [values, setValues] = useState(initialValues);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const set = (key) => (event) => {
    setValues((current) => ({
      ...current,
      [key]:
        event.target.type === "checkbox"
          ? event.target.checked
          : event.target.value,
    }));
  };

  async function submit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      const response = await fetch("/api/inquiry", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...values,
          bride_count: Number(values.bride_count),
          party_count: Number(values.party_count),
          junior_count: Number(values.junior_count),
          makeup_interest: values.makeup_interest === "yes",
          recommendations_if_unavailable:
            values.recommendations_if_unavailable === ""
              ? null
              : values.recommendations_if_unavailable === "yes",
          referral_other:
            values.referral_source === "Other" ? values.referral_other : null,
          referral_name: values.referral_name || null,
          additional_notes: values.additional_notes || null,
        }),
      });
      const result = await response.json().catch(() => null);

      if (!response.ok) {
        setError(
          typeof result?.detail === "string"
            ? result.detail
            : "We couldn't submit your inquiry. Please try again.",
        );
        return;
      }

      setSaved(true);
    } catch {
      setError("We couldn't submit your inquiry. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  if (saved) {
    return (
      <BrandShell>
        <div className="inquiry-success" role="status">
          <h1>Your inquiry has been received!</h1>
          <p>
            I've received your inquiry and will be in touch within 2 business
            days. I can't wait to chat details with you soon!!
          </p>
        </div>
      </BrandShell>
    );
  }

  return (
    <BrandShell>
      <div className="inquiry-content">
        <button
          className="back-button"
          type="button"
          onClick={() => window.location.assign("/")}
        >
          ← Back
        </button>
        <h1>Bridal inquiry</h1>
        <p>
          <strong>hiiii bestie bride!!</strong>
        </p>
        <p>
          Please fill out the form below & I will get your personalized invoice
          back to you <strong>within 2 business days from submission</strong> :)
          feel free to message me in my DM’s on Instagram @hairby.maddieee with
          any questions. I’m stoked to be your hair girl for your special day!
        </p>

        <form onSubmit={submit}>
          <label>
            Full name *
            <input
              autoComplete="name"
              required
              maxLength={255}
              value={values.name}
              onChange={set("name")}
            />
          </label>
          <label>
            Email *
            <input
              type="email"
              autoComplete="email"
              required
              value={values.email}
              onChange={set("email")}
            />
          </label>
          <label>
            Phone number (optional)
            <input
              type="tel"
              autoComplete="tel"
              value={values.phone}
              onChange={set("phone")}
            />
          </label>
          <label>
            Instagram handle or Facebook profile *
            <input
              required
              value={values.social_media}
              onChange={set("social_media")}
            />
          </label>
          <label>
            Wedding date *
            <input
              type="date"
              required
              min={denverDate()}
              value={values.wedding_date}
              onChange={set("wedding_date")}
            />
          </label>
          <label>
            Getting-ready address *
            <input
              required
              maxLength={255}
              value={values.address}
              onChange={set("address")}
            />
          </label>

          <div className="inquiry-counts">
            <label>
              Brides *
              <input
                type="number"
                min="0"
                max="10"
                step="1"
                required
                value={values.bride_count}
                onChange={set("bride_count")}
              />
            </label>
            <label>
              Bridesmaids / MOB / MOG *
              <input
                type="number"
                min="0"
                max="10"
                step="1"
                required
                value={values.party_count}
                onChange={set("party_count")}
              />
            </label>
            <label>
              Flowergirls *
              <input
                type="number"
                min="0"
                max="10"
                step="1"
                required
                value={values.junior_count}
                onChange={set("junior_count")}
              />
            </label>
          </div>
          <label>
            Ready-by time *
            <input
              type="time"
              required
              value={values.ready_by}
              onChange={set("ready_by")}
            />
          </label>

          <Choice
            name="location_type"
            label="Getting-ready location"
            value={values.location_type}
            onChange={set("location_type")}
            options={[
              ["home", "Home"],
              ["venue", "Venue"],
            ]}
          />
          <Choice
            name="time_firmness"
            label="Is your ready-by time set in stone?"
            value={values.time_firmness}
            onChange={set("time_firmness")}
            options={[
              ["firm", "Yes, it’s firm"],
              ["estimate", "No, it’s my best guess"],
            ]}
          />
          <Choice
            name="makeup_interest"
            label="Interested in makeup services?"
            value={values.makeup_interest}
            onChange={set("makeup_interest")}
            options={[
              ["yes", "Yes please!"],
              ["no", "Already got my girl!"],
            ]}
          />
          <Choice
            name="bridal_trial"
            label="Interested in a bridal trial?"
            value={values.bridal_trial}
            onChange={set("bridal_trial")}
            options={[
              ["yes", "Yes please!"],
              ["thinking", "I’m still thinking about it!"],
            ]}
          />
          <Choice
            name="planning_stage"
            label="Where are you in the planning process?"
            value={values.planning_stage}
            onChange={set("planning_stage")}
            options={[
              ["looking", "Just looking around :)"],
              [
                "invoice",
                "Love your work & would love my personalized invoice!",
              ],
              ["book", "So excited to book with you! Where do I sign?!"],
            ]}
          />
          <Choice
            name="recommendations_if_unavailable"
            label="If unavailable, would you like recommendations?"
            value={values.recommendations_if_unavailable}
            onChange={set("recommendations_if_unavailable")}
            required={false}
            options={[
              ["yes", "That would be incredible, thank you!"],
              ["no", "No thanks, I just wanted you!"],
            ]}
          />
          <Choice
            name="referral_source"
            label="How did you hear about Maddie?"
            value={values.referral_source}
            onChange={set("referral_source")}
            options={[
              ["Instagram", "Instagram"],
              ["Facebook", "Facebook"],
              ["Friend", "Friend"],
              ["Other", "Other"],
            ]}
          />
          {values.referral_source === "Other" && (
            <label>
              How did you hear about Maddie? *
              <input
                required
                maxLength={100}
                value={values.referral_other}
                onChange={set("referral_other")}
              />
            </label>
          )}
          <label>
            Who referred you? (optional)
            <input
              value={values.referral_name}
              onChange={set("referral_name")}
            />
          </label>
          <label>
            Anything else to know? (optional)
            <textarea
              maxLength={2000}
              rows="5"
              value={values.additional_notes}
              onChange={set("additional_notes")}
            />
          </label>
          <label className="inquiry-consent">
            <input
              type="checkbox"
              required
              checked={values.contact_consent}
              onChange={set("contact_consent")}
            />{" "}
            I agree that Maddie may contact me about my inquiry. *
          </label>
          <label className="inquiry-honeypot" aria-hidden="true">
            Leave this field empty
            <input
              tabIndex="-1"
              autoComplete="off"
              value={values.website}
              onChange={set("website")}
            />
          </label>
          {error && (
            <p className="inquiry-error" role="alert">
              {error}
            </p>
          )}
          <button
            className="inquiry-submit"
            type="submit"
            disabled={submitting}
          >
            {submitting ? "Sending…" : "Send inquiry"}
          </button>
        </form>
      </div>
    </BrandShell>
  );
}

function BrandShell({ children }) {
  return (
    <main className="brand-page inquiry-page">
      <div className="brand-page-orb brand-page-orb-one" />
      <div className="brand-page-orb brand-page-orb-two" />
      <section className="brand-page-card">
        <img
          className="brand-page-logo"
          src="/logo_banner.PNG"
          alt="Hair By Maddie · Bridal Hairstylist"
        />
        {children}
      </section>
      <p className="brand-page-footnote">Hair By Maddie, LLC</p>
    </main>
  );
}
