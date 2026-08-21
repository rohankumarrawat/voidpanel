import { Routes, Route } from 'react-router-dom'
import Navbar from './components/layout/Navbar'
import Footer from './components/layout/Footer'
import HomePage from './pages/HomePage'
import DnsCheckerPage from './tools/dns-checker/DnsCheckerPage'
import ComingSoonPage from './pages/ComingSoonPage'

export default function App() {
  return (
    <div className="min-h-screen flex flex-col bg-neutral-50 text-neutral-900">
      <Navbar />
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/tools/dns-checker" element={<DnsCheckerPage />} />
          <Route path="/tools/:slug" element={<ComingSoonPage />} />
        </Routes>
      </main>
      <Footer />
    </div>
  )
}
