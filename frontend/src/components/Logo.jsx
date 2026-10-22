// Logo XelWóor : icône SVG + nom en texte (Poppins), pour rester net et suivre la police de la page.
const ICON_SRC = `${process.env.PUBLIC_URL}/brand/xelwoor-icone.svg`;

const VARIANTS = {
  dark: { name: "text-white", accent: "text-[#22D3EE]", tagline: "text-[#CBD5E1]" },
  light: { name: "text-[#0B1736]", accent: "text-[#0891B2]", tagline: "text-[#64748B]" },
};

export default function Logo({ variant = "dark", size = "md", withTagline = false }) {
  const c = VARIANTS[variant];
  const large = size === "lg";
  return (
    <span className="inline-flex shrink-0 items-center gap-2.5">
      <img src={ICON_SRC} alt="" className={large ? "h-14 w-auto" : "h-9 w-auto"} />
      <span className="flex flex-col font-logo leading-none">
        <span className={`${large ? "text-3xl" : "text-xl"} font-bold ${c.name}`}>
          Xel<span className={`font-semibold ${c.accent}`}>Wóor</span>
        </span>
        {withTagline && (
          <span className={`mt-1.5 text-[0.6rem] font-medium uppercase tracking-[0.12em] ${c.tagline}`}>
            Détection intelligente de la fraude
          </span>
        )}
      </span>
    </span>
  );
}
