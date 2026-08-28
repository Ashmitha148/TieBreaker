import { motion } from 'framer-motion'
import { CheckCircle2, ArrowRight } from 'lucide-react'

interface Step {
  id: string
  label: string
  detail: string
  status: 'pending' | 'active' | 'completed' | 'warning'
  icon: any
  timestamp?: string
}

interface Props {
  steps: Step[]
  compact?: boolean
}

export default function TransactionPipeline({ steps, compact = false }: Props) {
  return (
    <div className={`flex items-stretch ${compact ? 'gap-1' : 'gap-2'}`}>
      {steps.map((step, i) => {
        const Icon = step.icon
        const isLast = i === steps.length - 1
        return (
          <div key={step.id} className="flex items-center flex-1 min-w-0">
            <motion.div
              initial={false}
              animate={{
                borderColor: step.status === 'active' ? 'rgba(51,149,255,0.4)' :
                  step.status === 'completed' ? 'rgba(16,185,129,0.25)' :
                  step.status === 'warning' ? 'rgba(245,158,11,0.35)' :
                  'rgba(255,255,255,0.06)',
                backgroundColor: step.status === 'active' ? 'rgba(51,149,255,0.06)' :
                  step.status === 'completed' ? 'rgba(16,185,129,0.04)' :
                  'rgba(255,255,255,0.02)',
              }}
              className={`relative flex-1 rounded-xl border ${compact ? 'py-2 px-2.5' : 'py-3 px-4'}`}
            >
              <div className="flex items-center gap-2.5">
                <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${
                  step.status === 'completed' ? 'bg-emerald-500/15 text-emerald-400' :
                  step.status === 'active' ? 'bg-[#3395FF]/15 text-[#3395FF]' :
                  step.status === 'warning' ? 'bg-amber-500/15 text-amber-400' :
                  'bg-white/[0.04] text-[#475569]'
                }`}>
                  {step.status === 'completed' ? <CheckCircle2 className="w-4 h-4" /> :
                   step.status === 'active' ? <motion.div animate={{ scale: [1, 1.2, 1] }} transition={{ repeat: Infinity, duration: 1.5 }}>
                     <Icon className="w-4 h-4" />
                   </motion.div> :
                   <Icon className="w-4 h-4" />}
                </div>
                <div className="min-w-0">
                  <div className={`text-[11px] font-bold ${
                    step.status === 'active' ? 'text-[#3395FF]' :
                    step.status === 'completed' ? 'text-emerald-400' :
                    'text-[#94a3b8]'
                  }`}>
                    {step.label}
                  </div>
                  {!compact && (
                    <div className="text-[10px] text-[#475569] truncate">{step.detail}</div>
                  )}
                </div>
              </div>
              {step.timestamp && !compact && (
                <div className="absolute top-2 right-2.5 text-[9px] font-mono text-[#475569]">{step.timestamp}</div>
              )}
            </motion.div>
            {!isLast && (
              <div className="w-3 flex items-center justify-center shrink-0">
                <ArrowRight className="w-3 h-3 text-[#475569]" />
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
