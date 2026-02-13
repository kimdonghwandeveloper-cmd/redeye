import React, { useEffect, useState } from 'react';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import { getModelMetrics } from '../api';
import { Activity, Clock, CheckCircle, Database } from 'lucide-react';

interface MetricsData {
    history: any[];
    best_metric: number;
    total_epochs: number;
}

const ModelsPage: React.FC = () => {
    const [metrics, setMetrics] = useState<MetricsData | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchMetrics();
    }, []);

    const fetchMetrics = async () => {
        try {
            const data = await getModelMetrics();
            setMetrics(data);
        } catch (error) {
            console.error("Failed to fetch metrics", error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen bg-gray-900 text-white">
                <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-500"></div>
            </div>
        );
    }

    if (!metrics || metrics.history.length === 0) {
        return (
            <div className="min-h-screen bg-gray-900 text-white p-8">
                <h1 className="text-3xl font-bold mb-4">Model Analytics</h1>
                <p>No training data available yet.</p>
            </div>
        );
    }

    // Filter out steps with no eval metrics for the Accuracy chart
    const evalHistory = metrics.history.filter(h => h.eval_accuracy !== undefined);

    return (
        <div className="min-h-screen bg-gray-900 text-white p-6 md:p-12 font-sans">
            <div className="max-w-7xl mx-auto space-y-12">

                {/* Header */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                        <h1 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-500">
                            AI Model Intelligence
                        </h1>
                        <p className="text-gray-400 mt-2">Real-time training performance and metrics.</p>
                    </div>
                    <div className="flex gap-4">
                        <div className="bg-gray-800 p-4 rounded-xl border border-gray-700 flex items-center gap-3">
                            <CheckCircle className="text-green-400" size={24} />
                            <div>
                                <p className="text-xs text-gray-500 uppercase font-bold">Best F1 Score</p>
                                <p className="text-xl font-bold text-white">{(metrics.best_metric * 100).toFixed(1)}%</p>
                            </div>
                        </div>
                        <div className="bg-gray-800 p-4 rounded-xl border border-gray-700 flex items-center gap-3">
                            <Clock className="text-blue-400" size={24} />
                            <div>
                                <p className="text-xs text-gray-500 uppercase font-bold">Total Epochs</p>
                                <p className="text-xl font-bold text-white">{metrics.total_epochs}</p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Charts Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

                    {/* Chart 1: Loss Curve */}
                    <div className="bg-gray-800/50 backdrop-blur-sm p-6 rounded-2xl border border-gray-700 shadow-xl">
                        <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
                            <Activity className="text-red-400" /> Training vs Validation Loss
                        </h2>
                        <div className="h-80 w-full">
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={metrics.history}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                    <XAxis dataKey="step" stroke="#9CA3AF" type="number" domain={['dataMin', 'dataMax']} />
                                    <YAxis stroke="#9CA3AF" />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px' }}
                                        itemStyle={{ color: '#E5E7EB' }}
                                    />
                                    <Legend />
                                    <Line type="monotone" dataKey="loss" stroke="#EF4444" name="Training Loss" dot={false} strokeWidth={2} connectNulls={true} />
                                    <Line type="monotone" dataKey="eval_loss" stroke="#3B82F6" name="Validation Loss" strokeWidth={2} connectNulls={true} />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                        <p className="text-sm text-gray-500 mt-4">
                            Lower is better. Convergence indicates the model is learning effectively without overfitting.
                        </p>
                    </div>

                    {/* Chart 2: Accuracy & F1 */}
                    <div className="bg-gray-800/50 backdrop-blur-sm p-6 rounded-2xl border border-gray-700 shadow-xl">
                        <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
                            <Database className="text-green-400" /> Evaluation Metrics
                        </h2>
                        <div className="h-80 w-full">
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={evalHistory}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                    <XAxis dataKey="step" stroke="#9CA3AF" type="number" domain={['dataMin', 'dataMax']} />
                                    <YAxis stroke="#9CA3AF" domain={[0, 1]} />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px' }}
                                        itemStyle={{ color: '#E5E7EB' }}
                                    />
                                    <Legend />
                                    <Line type="monotone" dataKey="eval_accuracy" stroke="#10B981" name="Accuracy" strokeWidth={2} connectNulls={true} />
                                    <Line type="monotone" dataKey="eval_f1" stroke="#8B5CF6" name="F1 Score" strokeWidth={2} connectNulls={true} />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                        <p className="text-sm text-gray-500 mt-4">
                            Higher is better. Accuracy tracks overall correctness, while F1 Score balances precision and recall.
                        </p>
                    </div>

                </div>
            </div>
        </div>
    );
};

export default ModelsPage;
