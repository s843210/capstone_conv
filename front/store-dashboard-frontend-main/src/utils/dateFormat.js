const KST_TIME_ZONE = "Asia/Seoul";
const LOCAL_DATE_TIME_PATTERN = /^(\d{4})-(\d{2})-(\d{2})(?:[T\s](\d{2}):(\d{2}))?/;
const TIME_ZONE_SUFFIX_PATTERN = /(Z|[+-]\d{2}:?\d{2})$/i;

const kstFormatter = new Intl.DateTimeFormat("en-US", {
  timeZone: KST_TIME_ZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

function pad2(value) {
  return String(value).padStart(2, "0");
}

function getLocalDateTimeParts(value) {
  if (typeof value !== "string" || TIME_ZONE_SUFFIX_PATTERN.test(value)) {
    return null;
  }

  const match = value.match(LOCAL_DATE_TIME_PATTERN);
  if (!match) return null;

  return {
    year: match[1],
    month: match[2],
    day: match[3],
    hour: match[4] || "00",
    minute: match[5] || "00",
  };
}

function getKstDateTimeParts(value) {
  if (!value) return null;

  const localParts = getLocalDateTimeParts(value);
  if (localParts) return localParts;

  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return null;

  return kstFormatter.formatToParts(date).reduce((parts, part) => {
    if (part.type !== "literal") {
      parts[part.type] = part.value;
    }
    return parts;
  }, {});
}

export function formatShortDateTime24(value) {
  const parts = getKstDateTimeParts(value);
  if (!parts) return value || "-";

  return `${parts.month}.${parts.day} ${pad2(parts.hour)}:${pad2(parts.minute)}`;
}

export function formatFullDateTime24(value) {
  const parts = getKstDateTimeParts(value);
  if (!parts) return value || "-";

  return `${parts.year}.${parts.month}.${parts.day} ${pad2(parts.hour)}:${pad2(parts.minute)}`;
}
