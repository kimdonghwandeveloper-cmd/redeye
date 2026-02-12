import { useState } from 'react';
import {
    Box, Button, Input, VStack, Heading, Text, useToast,
    Container, Card, CardHeader, CardBody, Flex, Badge, Select
} from '@chakra-ui/react';
import { ShieldAlert, BrainCircuit, Play, Loader2, Gauge, Globe } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css';
import { startScan, getScanStatus, type ScanResponse } from './api';

export default function ScanPage() {
    const [url, setUrl] = useState('');
    const [language, setLanguage] = useState('en');
    const [loading, setLoading] = useState(false);
    const [statusMessage, setStatusMessage] = useState('');
    const [result, setResult] = useState<ScanResponse | null>(null);
    const [scoreData, setScoreData] = useState<{ current: number; projected: number } | null>(null);
    const toast = useToast();

    const handleScan = async () => {
        if (!url) {
            toast({ title: 'Please enter a URL', status: 'warning' });
            return;
        }

        setLoading(true);
        setResult(null);
        setScoreData(null);
        setStatusMessage(language === 'ko' ? '스캔 초기화 중...' : 'Initializing Scan...');

        try {
            // 1. Start Scan (Get ID)
            const initialRes = await startScan(url, language);
            const scanId = initialRes.scan_id;
            console.log("Scan Started:", scanId);

            // 2. Poll Status
            const pollInterval = setInterval(async () => {
                try {
                    const statusRes = await getScanStatus(scanId);
                    console.log("Polling Status:", statusRes.status);

                    if (statusRes.status === 'completed') {
                        clearInterval(pollInterval);
                        setResult(statusRes);
                        setLoading(false);
                        toast({ title: language === 'ko' ? '스캔 완료!' : 'Scan Completed!', status: 'success' });

                        // Parse JSON Score from Markdown
                        const agentResponse = statusRes.agent_response || "";
                        const jsonMatch = agentResponse.match(/```json\n([\s\S]*?)\n```/);
                        if (jsonMatch && jsonMatch[1]) {
                            try {
                                const parsed = JSON.parse(jsonMatch[1]);
                                setScoreData({
                                    current: parsed.current_score,
                                    projected: parsed.projected_score
                                });
                            } catch (e) {
                                console.error("Failed to parse score JSON", e);
                            }
                        }

                    } else if (statusRes.status === 'failed') {
                        clearInterval(pollInterval);
                        setLoading(false);
                        toast({ title: 'Scan Failed', description: 'Agent encountered an error.', status: 'error' });
                    } else {
                        setStatusMessage(language === 'ko' ? 'AI가 취약점을 분석 중입니다... (1~2분 소요)' : 'AI is analyzing vulnerabilities... (This may take 1-2 mins)');
                    }
                } catch (err) {
                    clearInterval(pollInterval);
                    setLoading(false);
                    toast({ title: 'Polling Error', description: String(err), status: 'error' });
                }
            }, 3000); // Check every 3 seconds

        } catch (error) {
            setLoading(false);
            toast({ title: 'Start Failed', description: String(error), status: 'error' });
        }
    };

    // Gauge Chart Data Wrapper
    const getChartData = (score: number) => [
        { name: 'Score', value: score },
        { name: 'Remaining', value: 100 - score }
    ];
    const COLORS = ['#F56565', '#2D3748']; // Red & Gray
    const PROJECTED_COLORS = ['#48BB78', '#2D3748']; // Green & Gray

    return (
        <Container maxW="container.md" py={10}>
            <VStack spacing={8} align="stretch">
                <Box textAlign="center" position="relative">
                    <Flex position="absolute" top={0} right={0} align="center" gap={2}>
                        <Globe size={16} className="text-gray-400" />
                        <Select
                            size="xs"
                            width="100px"
                            value={language}
                            onChange={(e) => setLanguage(e.target.value)}
                            bg="gray.800"
                            borderColor="gray.600"
                        >
                            <option value="en">English</option>
                            <option value="ko">한국어</option>
                        </Select>
                    </Flex>
                    <Heading size="2xl" mb={2} bgGradient="linear(to-r, red.500, red.300)" bgClip="text">
                        RedEye
                    </Heading>
                    <Text fontSize="lg" color="gray.400">AI-Powered Vulnerability Scanner</Text>
                </Box>

                <Card variant="outline" borderColor="red.900" bg="gray.800">
                    <CardBody>
                        <VStack spacing={4}>
                            <Input
                                placeholder="https://example.com"
                                size="lg"
                                value={url}
                                onChange={(e) => setUrl(e.target.value)}
                                bg="gray.900"
                                border="none"
                            />
                            <Button
                                rightIcon={loading ? <Loader2 className="animate-spin" /> : <Play size={20} />}
                                colorScheme="red"
                                size="lg"
                                width="full"
                                onClick={handleScan}
                                isLoading={loading}
                                loadingText={statusMessage}
                            >
                                {language === 'ko' ? '보안 스캔 시작' : 'Start Security Scan'}
                            </Button>
                        </VStack>
                    </CardBody>
                </Card>

                {result && (
                    <VStack spacing={6} align="stretch" animation="fadeIn 0.5s">
                        {/* 1. Security Score Dashboard */}
                        {scoreData && (
                            <Card bg="gray.800" borderTop="4px solid" borderColor="orange.400">
                                <CardHeader>
                                    <Heading size="md" display="flex" alignItems="center" gap={2}>
                                        <Gauge className="text-orange-400" />
                                        Security Analytics
                                    </Heading>
                                </CardHeader>
                                <CardBody>
                                    <Flex justify="space-around" align="center" wrap="wrap">
                                        {/* Current Score */}
                                        <Box textAlign="center">
                                            <Text fontSize="lg" fontWeight="bold" mb={2}>Current Risk Score</Text>
                                            <Box w="150px" h="150px" mx="auto">
                                                <ResponsiveContainer width="100%" height="100%">
                                                    <PieChart>
                                                        <Pie
                                                            data={getChartData(scoreData.current)}
                                                            cx="50%" cy="50%"
                                                            innerRadius={40} outerRadius={60}
                                                            startAngle={180} endAngle={0}
                                                            dataKey="value"
                                                        >
                                                            {getChartData(scoreData.current).map((_entry, index) => (
                                                                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                                            ))}
                                                        </Pie>
                                                    </PieChart>
                                                </ResponsiveContainer>
                                            </Box>
                                            <Heading size="xl" mt="-40px" color="red.400">{scoreData.current}</Heading>
                                            <Badge colorScheme="red" mt={2}>High Risk</Badge>
                                        </Box>

                                        {/* Projected Score */}
                                        <Box textAlign="center">
                                            <Text fontSize="lg" fontWeight="bold" mb={2}>Projected Score (After Fix)</Text>
                                            <Box w="150px" h="150px" mx="auto">
                                                <ResponsiveContainer width="100%" height="100%">
                                                    <PieChart>
                                                        <Pie
                                                            data={getChartData(scoreData.projected)}
                                                            cx="50%" cy="50%"
                                                            innerRadius={40} outerRadius={60}
                                                            startAngle={180} endAngle={0}
                                                            dataKey="value"
                                                        >
                                                            {getChartData(scoreData.projected).map((_entry, index) => (
                                                                <Cell key={`cell-${index}`} fill={PROJECTED_COLORS[index % PROJECTED_COLORS.length]} />
                                                            ))}
                                                        </Pie>
                                                    </PieChart>
                                                </ResponsiveContainer>
                                            </Box>
                                            <Heading size="xl" mt="-40px" color="green.400">{scoreData.projected}</Heading>
                                            <Badge colorScheme="green" mt={2}>+ {scoreData.projected - scoreData.current} Improvement</Badge>
                                        </Box>
                                    </Flex>
                                </CardBody>
                            </Card>
                        )}

                        <Card bg="gray.800" borderTop="4px solid" borderColor="red.500">
                            <CardHeader pb={0}>
                                <Heading size="md" display="flex" alignItems="center" gap={2}>
                                    <ShieldAlert className="text-red-500" />
                                    Scan Results
                                </Heading>
                            </CardHeader>
                            <CardBody>
                                <Text color="gray.400">Target: {result.target}</Text>
                            </CardBody>
                        </Card>

                        <Card bg="gray.800" borderTop="4px solid" borderColor="purple.500">
                            <CardHeader>
                                <Heading size="md" display="flex" alignItems="center" gap={2}>
                                    <BrainCircuit className="text-purple-500" />
                                    AI Analysis & Solutions
                                </Heading>
                            </CardHeader>
                            <CardBody>
                                <Box className="markdown-body" fontSize="sm" color="gray.100" sx={{
                                    'h1, h2, h3': { color: 'purple.200', mt: 4, mb: 2, fontWeight: 'bold' },
                                    'h1': { fontSize: 'xl' },
                                    'h2': { fontSize: 'lg' },
                                    'ul, ol': { pl: 5, mb: 2 },
                                    'li': { mb: 1 },
                                    'code': { bg: 'gray.900', px: 1, borderRadius: 'sm', fontFamily: 'monospace' },
                                    'pre code': { bg: 'transparent', p: 0 },
                                    'pre': { bg: 'gray.900', p: 4, borderRadius: 'md', overflowX: 'auto', mb: 4 }
                                }}>
                                    <ReactMarkdown
                                        rehypePlugins={[rehypeHighlight]}
                                    >
                                        {/* Remove JSON block before rendering markdown */}
                                        {result.agent_response?.replace(/```json[\s\S]*```/, '')}
                                    </ReactMarkdown>
                                </Box>
                            </CardBody>
                        </Card>
                    </VStack>
                )}
            </VStack>
        </Container>
    );
}
