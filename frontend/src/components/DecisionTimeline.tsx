import { motion } from 'framer-motion'

interface Event {
  stage: string
  detail: string
  timestamp: string
  duration: string
  icon: any
}

interface Props {
  events: Event[]
}

export default function DecisionTimeline({ events }: Props) {
  return (
    <div className="space-y-0">
      {events.map((evt, i) => {
        const Icon = evt.icon
        return (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.08 }}
            className="flex items-start gap-3 py-3 border-l border-white/[0.06] pl-4 relative"
          >
            <div className="absolute left-[-5px] top-3.5 w-2.5 h-2.5 rounded-full bg-[#3395FF]/30 border border-[#3395FF]/50" />
            <div className="w-7 h-7 rounded-lg bg-white/[0.03] flex items-center justify-center shrink-0 mt-0.5">
              <Icon className="w-3.5 h-3.5 text-[#94a3b8]" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between">
                <span className="text-[12px] font-bold text-white">{evt.stage}</span>
                <span className="text-[10px] font-mono text-[#475569]">{evt.timestamp}</span>
              </div>
              <div className="text-[11px] text-[#94a3b8] mt-0.5">{evt.detail}</div>
              <div className="text-[9px] font-mono text-[#3395FF]/70 mt-1">+{evt.duration}</div>
            </div>
          </motion.div>
        )
      })}
    </div>
  )
}
