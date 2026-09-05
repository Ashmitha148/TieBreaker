import { motion } from 'framer-motion'

interface LogoProps {
  size?: number
  showText?: boolean
  textClassName?: string
}

export default function Logo({ size = 32, showText = true, textClassName = '' }: LogoProps) {
  return (
    <div className="flex items-center gap-2.5">
      <motion.div
        whileHover={{ scale: 1.05, rotate: 5 }}
        transition={{ type: 'spring', stiffness: 400 }}
        className="relative shrink-0"
        style={{ width: size, height: size }}
      >
        <svg width={size} height={size} viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <linearGradient id="logoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#3395FF" />
              <stop offset="50%" stopColor="#7c3aed" />
              <stop offset="100%" stopColor="#a855f7" />
            </linearGradient>
            <filter id="logoGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="4" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>
          <rect width="100" height="100" rx="22" fill="url(#logoGrad)" />
          <path
            d="M55 28 L42 52 H51 L47 72 L63 48 H54 L58 28 Z"
            fill="white"
            filter="url(#logoGlow)"
          />
          <path
            d="M55 28 L42 52 H51 L47 72 L63 48 H54 L58 28 Z"
            fill="white"
          />
        </svg>
      </motion.div>
      {showText && (
        <span className={`font-bold text-white tracking-tight ${textClassName}`}>
          TieBreaker
        </span>
      )}
    </div>
  )
}
