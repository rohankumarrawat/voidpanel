import { useParams, Link } from 'react-router-dom'
import { Clock, ArrowLeft } from 'lucide-react'

export default function ComingSoonPage() {
  const { slug } = useParams<{ slug: string }>()
  const toolName = slug?.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ') ?? 'Tool'

  return (
    <div className="max-w-3xl mx-auto px-4 py-20 text-center space-y-6 animate-fade-in-up">
      <div className="mx-auto w-20 h-20 rounded-3xl bg-primary-50 flex items-center justify-center">
        <Clock className="w-10 h-10 text-primary-500" />
      </div>

      <h1 className="text-3xl font-bold text-neutral-900">{toolName}</h1>

      <p className="text-lg text-neutral-500 max-w-md mx-auto">
        This tool is currently being built and will be available soon. Stay tuned!
      </p>

      <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-100 text-amber-700 text-sm font-bold">
        Coming Soon
      </div>

      <div className="pt-4">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-sm font-semibold text-primary-600 hover:text-primary-700"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to All Tools
        </Link>
      </div>
    </div>
  )
}
