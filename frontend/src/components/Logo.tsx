import { motion } from 'framer-motion'

interface LogoProps {
  size?: number
  showText?: boolean
  textClassName?: string
}

export default function Logo({ size = 32, showText = true, textClassName = '' }: LogoProps) {
  return (
    <div className="flex items-center gap-2">
      <motion.div
        whileHover={{ scale: 1.05 }}
        transition={{ type: 'spring', stiffness: 400 }}
        className="relative shrink-0"
        style={{ width: size, height: size }}
      >
        {/* TieBreaker Rhombus Mark — red wedge vs gold wedge, the seam is the decision */}
        <svg width={size} height={size} viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
          <polygon points="50,6 50,94 8,50" fill="#E8433A"/>
          <polygon points="50,6 50,94 92,50" fill="#E8A23D"/>
          <rect x="48.3" y="6" width="3.4" height="88" fill="#130F16"/>
        </svg>
      </motion.div>
      {showText && (
        <span className={`font-extrabold tracking-tight ${textClassName}`} style={{ fontFamily: 'var(--f-ui, Manrope, sans-serif)' }}>
          <span style={{ color: '#E8433A' }}>Tie</span>
          <span style={{ color: '#E8A23D' }}>Breaker</span>
        </span>
      )}
    </div>
  )
}