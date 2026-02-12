import { useState } from 'react';
import {
    Box, Button, Input, VStack, Heading, Text, useToast,
    Container, Card, CardHeader, CardBody, Divider
} from '@chakra-ui/react';
import { ShieldAlert, BrainCircuit, Play, Loader2 } from 'lucide-react';
import { startScan, getScanStatus, type ScanResponse } from './api';

export default function ScanPage() {
    const [url, setUrl] = useState('');
    const [loading, setLoading] = useState(false);
    const [statusMessage, setStatusMessage] = useState('');
    const [result, setResult] = useState<ScanResponse | null>(null);
    const toast = useToast();

    const handleScan = async () => {
        if (!url) {
            toast({ title: 'Please enter a URL', status: 'warning' });
            return;
        }

        setLoading(true);
        setResult(null);
        setStatusMessage('Initializing Scan...');

        try {
            // 1. Start Scan (Get ID)
            const initialRes = await startScan(url);
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
                        toast({ title: 'Scan Completed!', status: 'success' });
                    } else if (statusRes.status === 'failed') {
                        clearInterval(pollInterval);
                        setLoading(false);
                        toast({ title: 'Scan Failed', description: 'Agent encountered an error.', status: 'error' });
                    } else {
                        setStatusMessage('AI is analyzing vulnerabilities... (This may take 1-2 mins)');
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

    return (
        <Container maxW="container.md" py={10}>
            <VStack spacing={8} align="stretch">
                <Box textAlign="center">
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
                                Start Security Scan
                            </Button>
                        </VStack>
                    </CardBody>
                </Card>

                {result && (
                    <VStack spacing={6} align="stretch" animation="fadeIn 0.5s">
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
                                <Box whiteSpace="pre-wrap" fontSize="sm">
                                    {/* Basic markdown rendering workaround for MVP */}
                                    {result.agent_response?.split('\n').map((line: string, i: number) => {
                                        if (line.startsWith('# ')) return <Heading key={i} size="lg" mt={4} mb={2}>{line.replace('# ', '')}</Heading>
                                        if (line.startsWith('## ')) return <Heading key={i} size="md" mt={4} mb={2} color="purple.300">{line.replace('## ', '')}</Heading>
                                        if (line.startsWith('- ')) return <Text key={i} ml={4}>• {line.replace('- ', '')}</Text>
                                        if (line.startsWith('```')) return <Divider key={i} my={2} />;
                                        return <Text key={i}>{line}</Text>
                                    })}
                                </Box>
                            </CardBody>
                        </Card>
                    </VStack>
                )}
            </VStack>
        </Container>
    );
}
