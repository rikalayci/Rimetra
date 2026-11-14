import { avatarUrl, type Member } from "../lib/api";
import { colorFor } from "../lib/format";

type AvatarMember = Pick<Member, "id" | "display_name" | "avatar_color" | "has_avatar" | "avatar_version"> &
  Partial<Pick<Member, "sex" | "birth_year">>;

const SKIN = ["#F6D3B9", "#EEC3A2", "#E2AF8A", "#F8DDC8"];
const HAIR = ["#3A2A22", "#5B3A27", "#2C2626", "#7A4D2C", "#4A3326"];
const SHIRT = ["#3E5C76", "#E58A5C", "#4F7A5E", "#D46A6A", "#8A6FB0", "#E2A74E"];

function hash(s: string) {
  let h = 0;
  for (const c of s) h = (h * 33 + c.charCodeAt(0)) >>> 0;
  return h;
}

/** Fotoğraf yüklenmemiş üyeler için yaş/cinsiyete göre basit, sevimli çizim yüz. */
function Face({ m }: { m: AvatarMember }) {
  const h = hash(m.id);
  const skin = SKIN[h % SKIN.length];
  const hair = HAIR[(h >> 3) % HAIR.length];
  const shirt = SHIRT[(h >> 5) % SHIRT.length];
  const age = m.birth_year ? new Date().getFullYear() - m.birth_year : 30;
  const child = age < 14;
  const female = m.sex === "F";
  const male = m.sex === "M";
  const beard = male && !child && age >= 18 && (h >> 7) % 2 === 0;
  const r = child ? 23 : 21;
  const cy = child ? 47 : 45;
  return (
    <svg viewBox="0 0 100 100" className="h-full w-full">
      {/* arka saç (uzun) */}
      {female && !child && <path d={`M${50 - r - 4} ${cy - 2} Q${50 - r - 8} ${cy + 34} ${50 - r + 2} ${cy + 36} L${50 + r - 2} ${cy + 36} Q${50 + r + 8} ${cy + 34} ${50 + r + 4} ${cy - 2} Z`} fill={hair} />}
      {/* gövde */}
      <path d="M18 104 Q20 74 50 72 Q80 74 82 104 Z" fill={shirt} />
      <path d="M43 66 h14 v10 q-7 5 -14 0 Z" fill={skin} />
      {/* kulaklar */}
      <circle cx={50 - r} cy={cy + 2} r={4.5} fill={skin} />
      <circle cx={50 + r} cy={cy + 2} r={4.5} fill={skin} />
      {/* yüz */}
      <ellipse cx={50} cy={cy} rx={r} ry={r + 2} fill={skin} />
      {beard && <path d={`M${50 - r + 1} ${cy + 2} Q${50 - r + 3} ${cy + r + 8} 50 ${cy + r + 6} Q${50 + r - 3} ${cy + r + 8} ${50 + r - 1} ${cy + 2} Q${50 + r - 6} ${cy + 14} 50 ${cy + 13} Q${50 - r + 6} ${cy + 14} ${50 - r + 1} ${cy + 2} Z`} fill={hair} />}
      {/* ön saç */}
      {female ? (
        <path d={`M${50 - r - 1} ${cy - 1} Q${50 - r} ${cy - r - 8} 50 ${cy - r - 4} Q${50 + r} ${cy - r - 8} ${50 + r + 1} ${cy - 1} Q${50 + 8} ${cy - r + 2} ${50 - 4} ${cy - r + 6} Q${50 - r + 4} ${cy - 8} ${50 - r - 1} ${cy - 1} Z`} fill={hair} />
      ) : (
        <path d={`M${50 - r - 1} ${cy - 2} Q${50 - r - 2} ${cy - r - 9} 50 ${cy - r - 6} Q${50 + r + 2} ${cy - r - 9} ${50 + r + 1} ${cy - 2} Q${50 + r - 4} ${cy - r + 1} ${50 + 4} ${cy - r + 3} Q${50 - 6} ${cy - r + 6} ${50 - r + 3} ${cy - r + 8} Q${50 - r + 1} ${cy - 6} ${50 - r - 1} ${cy - 2} Z`} fill={hair} />
      )}
      {female && child && <circle cx={50} cy={cy - r - 7} r={7} fill={hair} />}
      {/* kaşlar */}
      <path d={`M${41} ${cy - 6} q4 -2.5 7 0`} stroke={hair} strokeWidth={1.8} fill="none" strokeLinecap="round" />
      <path d={`M${52} ${cy - 6} q3 -2.5 7 0`} stroke={hair} strokeWidth={1.8} fill="none" strokeLinecap="round" />
      {/* gözler */}
      <ellipse cx={44.5} cy={cy} rx={2.4} ry={2.9} fill="#2B211D" />
      <ellipse cx={55.5} cy={cy} rx={2.4} ry={2.9} fill="#2B211D" />
      <circle cx={45.3} cy={cy - 1} r={0.8} fill="#fff" />
      <circle cx={56.3} cy={cy - 1} r={0.8} fill="#fff" />
      {/* yanaklar ve gülümseme */}
      <circle cx={39} cy={cy + 7} r={3.4} fill="#F08C7A" opacity={0.45} />
      <circle cx={61} cy={cy + 7} r={3.4} fill="#F08C7A" opacity={0.45} />
      <path d={`M${44.5} ${cy + 8.5} Q50 ${cy + 13.5} ${55.5} ${cy + 8.5}`} stroke={beard ? "#F3E3D6" : "#8C3B2E"} strokeWidth={2} fill="none" strokeLinecap="round" />
      {female && !child && <circle cx={50 - r - 1} cy={cy + 8} r={1.8} fill="#E2A74E" />}
    </svg>
  );
}

export function Avatar({ member, size = 56, ring }: { member: AvatarMember; size?: number; ring?: boolean }) {
  const bg = colorFor(member.id, member.avatar_color);
  return (
    <div
      className={`relative flex shrink-0 items-center justify-center overflow-hidden rounded-full ${ring ? "ring-4 ring-surface" : ""}`}
      style={{ width: size, height: size, background: bg }}
      title={member.display_name}
    >
      {member.has_avatar ? (
        <img src={avatarUrl(member)} alt={member.display_name} className="h-full w-full object-cover" />
      ) : (
        <Face m={member} />
      )}
    </div>
  );
}
