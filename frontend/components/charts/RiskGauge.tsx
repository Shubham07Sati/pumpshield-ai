"use client";

interface Props {
  score: number;
  level: "green" | "red";
}

export default function RiskGauge({ score, level }: Props) {
  const isRed = level === "red";
  const rotation = (score / 100) * 180 - 90;

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-48 h-28 overflow-hidden">
        <div className="absolute inset-0 rounded-t-full border-[12px] border-gray-800 border-b-0" />
        <div
          className={`absolute inset-0 rounded-t-full border-[12px] border-b-0 origin-bottom transition-all duration-700 ${
            isRed ? "border-red-500" : "border-emerald-500"
          }`}
          style={{
            clipPath: `polygon(0 100%, 100% 100%, 100% 0, 0 0)`,
            transform: `rotate(${rotation}deg)`,
            transformOrigin: "50% 100%",
          }}
        />
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 text-center">
          <div className={`text-4xl font-black ${isRed ? "text-red-400" : "text-emerald-400"}`}>{score}</div>
          <div className="text-xs text-gray-500 uppercase tracking-wider">Risk Score</div>
        </div>
      </div>
      <div className="flex justify-between w-48 text-xs text-gray-600 mt-1 px-1">
        <span>0</span>
        <span className="text-yellow-500">80</span>
        <span>100</span>
      </div>
    </div>
  );
}
