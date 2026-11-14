import {
  Activity, Beaker, Bone, Droplet, Droplets, FlaskConical, HeartPulse, Pill, Ruler, Shield, Sparkles, Syringe, Thermometer, Zap,
} from "lucide-react";
import type { ReactNode } from "react";
import { t } from "../lib/i18n";

const CAT: Record<string, { icon: (s: number) => ReactNode; label?: string }> = {
  Hemogram: { icon: (s) => <Droplet size={s} className="fill-[#E9765F]/80 text-[#E9765F]" />, label: "Kan Sayımı" },
  Biyokimya: { icon: (s) => <FlaskConical size={s} className="text-brand" /> },
  Lipid: { icon: (s) => <HeartPulse size={s} className="fill-[#E9765F]/80 text-[#E9765F]" />, label: "Kolesterol" },
  Tiroid: { icon: (s) => <Shield size={s} className="text-[#E9765F]" /> },
  "Vitamin ve Mineral": { icon: (s) => <Pill size={s} className="text-brand" /> },
  Diyabet: { icon: (s) => <Droplets size={s} className="text-[#D9934A]" /> },
  İnflamasyon: { icon: (s) => <Zap size={s} className="text-[#D9934A]" /> },
  Hormon: { icon: (s) => <Sparkles size={s} className="text-[#B07BC4]" /> },
  Koagülasyon: { icon: (s) => <Syringe size={s} className="text-[#E9765F]" /> },
  İdrar: { icon: (s) => <Beaker size={s} className="text-[#D2A23A]" /> },
  Seroloji: { icon: (s) => <Bone size={s} className="text-muted" /> },
  Ölçümler: { icon: (s) => <Ruler size={s} className="text-brand" /> },
};

export function CategoryIcon({ category, size = 20 }: { category: string | null | undefined; size?: number }) {
  const c = category ? CAT[category] : undefined;
  if (c) return <>{c.icon(size)}</>;
  if (category === "Ölçümler") return <Thermometer size={size} />;
  return <Activity size={size} className="text-muted" />;
}

export const categoryLabel = (c: string) => t(CAT[c]?.label ?? c);

import logoUrl from "../assets/logo.png";
import headerUrl from "../assets/header.webp";
import emptyUrl from "../assets/empty.webp";

export function Logo({ size = 34 }: { size?: number }) {
  return <img src={logoUrl} width={size} height={size} alt="" aria-hidden className="object-contain" style={{ width: size, height: size }} />;
}

/** Başlık alanındaki sıcak ev/bitki illüstrasyonu. */
export function HomeIllustration() {
  return <img src={headerUrl} alt="" aria-hidden className="h-full w-full object-contain" />;
}

/** Boş durumlar için pano + filiz illüstrasyonu. */
export function EmptyArt({ size = 160 }: { size?: number }) {
  return <img src={emptyUrl} alt="" aria-hidden style={{ width: size, height: size * 0.75 }} className="object-contain" />;
}
