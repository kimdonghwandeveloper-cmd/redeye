import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { Shield, BarChart2 } from 'lucide-react';
import ScanPage from './ScanPage';
import ModelsPage from './pages/ModelsPage';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-900 text-gray-100 font-sans">
        {/* Navigation Bar */}
        <nav className="bg-gray-800 border-b border-gray-700 sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <div className="flex items-center">
                <Link to="/" className="flex-shrink-0 flex items-center gap-2 group">
                  <Shield className="h-8 w-8 text-red-500 group-hover:text-red-400 transition-colors" />
                  <span className="font-bold text-xl tracking-tight text-white group-hover:text-red-400 transition-colors">
                    RedEye <span className="text-red-500">AI</span>
                  </span>
                </Link>
                <div className="hidden md:block">
                  <div className="ml-10 flex items-baseline space-x-4">
                    <Link
                      to="/"
                      className="text-gray-300 hover:bg-gray-700 hover:text-white px-3 py-2 rounded-md text-sm font-medium transition-colors"
                    >
                      Scanner
                    </Link>
                    <Link
                      to="/models"
                      className="text-gray-300 hover:bg-gray-700 hover:text-white px-3 py-2 rounded-md text-sm font-medium transition-colors flex items-center gap-2"
                    >
                      <BarChart2 size={16} />
                      AI Models
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </nav>

        {/* Content Area */}
        <div className="pt-4">
          <Routes>
            <Route path="/" element={<ScanPage />} />
            <Route path="/models" element={<ModelsPage />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;
