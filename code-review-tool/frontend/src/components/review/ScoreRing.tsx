interface Props {
  score: number
  size?: number
}

function colorClass(score: number) {
  if (score >= 80) return 'text-green-500'
  if (score >= 60) return 'text-yellow-500'
  return 'text-red-500'
}

export function ScoreRing({ score, size = 120 }: Props) {
  const radius = 46
  const circumference = 2 * Math.PI * radius
  const offset = circumference * (1 - score / 100)
  const color = colorClass(score)

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox="0 0 100 100" className="-rotate-90" aria-hidden>
        <circle
          cx="50" cy="50" r={radius}
          fill="none" stroke="currentColor"
          strokeWidth="8"
          className="text-gray-100"
        />
        <circle
          cx="50" cy="50" r={radius}
          fill="none" stroke="currentColor"
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className={`score-arc transition-all duration-700 ${color}`}
        />
      </svg>
      <div className="absolute flex flex-col items-center leading-none">
        <span className={`text-2xl font-bold ${color}`}>{score}</span>
        <span className="text-xs text-gray-400">/100</span>
      </div>
    </div>
  )
}
