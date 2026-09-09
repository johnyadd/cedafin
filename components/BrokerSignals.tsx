/**
 * components/BrokerSignals.tsx — what a reader can actually check.
 *
 * WHY THIS EXISTS
 * The brokers page tells a reader to look at four things before choosing:
 * whether they can reach the firm, what it costs, what else it does, and
 * whether it will take them. Then it showed twenty-four cards ordered by
 * trading volume, which answers none of those.
 *
 * These pills put three of the four on the card itself, so a reader scanning
 * the list can see them without opening anything. The fourth — cost — cannot
 * be shown, because not one of the twenty-four publishes a commission rate.
 *
 * WHY ABSENCE IS LABELLED RATHER THAN LEFT BLANK
 * FINRA's own guidance on BrokerCheck makes the point: "no record found" is
 * not the same as a clean history, and the absence of a record does not mean
 * someone was never active. Compustat go further, coding WHY a value is
 * missing, because most blank fields reflect an absence of collectible data
 * rather than an economic zero.
 *
 * So silence gets a pill of its own and a line saying what it means. A blank
 * space would be read as "no", and "no" is a thing we have not established.
 *
 * WHY CUSTODY HAS NO NEGATIVE STATE
 * One firm of twenty-four says it offers custody. Putting "no custody" on the
 * other twenty-three would assert something none of them has said. The pill
 * appears where the fact exists and nowhere else.
 */

const C = {
  ink: "#0C1C22",
  deep: "#0B4F6C",
  teal: "#1B8BC0",
  gold: "#E8A33D",
  clay: "#C0492B",
  card: "#FFFFFF",
  rule: "#DAE4EB",
  bg: "#F2F6F9",
  muted: "#5F6E78",
  good: "#0E8F62",
};

function Pill({
  label,
  tone,
  title,
}: {
  label: string;
  /** filled = we hold a fact; muted = we hold silence. */
  tone: "filled" | "muted" | "warn";
  title?: string;
}) {
  const style =
    tone === "filled"
      ? { background: `${C.good}14`, color: C.good, border: `1px solid ${C.good}40` }
      : tone === "warn"
        ? { background: `${C.clay}12`, color: C.clay, border: `1px solid ${C.clay}35` }
        : { background: C.bg, color: C.muted, border: `1px solid ${C.rule}` };

  return (
    <span
      title={title}
      className="inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-semibold"
      style={style}
    >
      {label}
    </span>
  );
}

export default function BrokerSignals({
  website,
  email,
  phone,
  accessRequirements,
  offersCustody,
}: {
  website: string | null;
  email: string | null;
  phone: string | null;
  accessRequirements: string | null;
  offersCustody: boolean | null;
}) {
  const reachable = Boolean(website && email);
  const phoneOnly = !reachable && Boolean(phone);

  return (
    <div className="mt-2.5">
      <div className="flex flex-wrap gap-1.5">
        {/* Reachability. Three states, because "no website" and "the
            website on the register did not respond" are different facts —
            one about the firm, one about the register. */}
        {reachable ? (
          <Pill
            label="Website and email"
            tone="filled"
            title="Both worked when we checked."
          />
        ) : phoneOnly ? (
          <Pill
            label="Phone only"
            tone="muted"
            title="No working website or email address we could use. The telephone number is from the SEC register."
          />
        ) : (
          <Pill
            label="Register details didn't respond"
            tone="warn"
            title="The contact details on the regulator's register did not work when we checked. The firm may have moved."
          />
        )}

        {/* Clients abroad. The question a diaspora reader has, and the one
            twenty-two of twenty-four do not address. */}
        {accessRequirements ? (
          <Pill
            label="Says it takes clients abroad"
            tone="filled"
            title="This firm publishes something about accepting clients outside Ghana. What it says is below."
          />
        ) : (
          <Pill
            label="Silent on clients abroad"
            tone="muted"
            title="Nothing published either way. Not a refusal."
          />
        )}

        {/* Custody, positive only. Twenty-three firms have not said they do
            not offer it; they have said nothing. */}
        {offersCustody && (
          <Pill
            label="Offers custody"
            tone="filled"
            title="Says it can hold securities on your behalf, rather than you holding them directly in your own CSD account. Useful if opening one yourself is difficult."
          />
        )}
      </div>

      {/* The caveat sits on every card that shows silence, not once at the
          top of the page. Readers systematically read a blank as a no, and
          the correction has to be where the blank is. */}
      {!accessRequirements && (
        <p className="mt-1.5 text-[11px]" style={{ color: C.muted }}>
          Silence is not refusal — we have asked and they have not answered.
        </p>
      )}
    </div>
  );
}
