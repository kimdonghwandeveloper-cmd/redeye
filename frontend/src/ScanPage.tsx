import { useState } from 'react';
import {
    Box, Button, Input, VStack, Heading, Text, useToast,
    Container, Card, CardHeader, CardBody, Code, Divider,
    Accordion, AccordionItem, AccordionButton, AccordionPanel, AccordionIcon
} from '@chakra-ui/react';
import { Scan as ScanIcon, ShieldAlert, BrainCircuit, Play } from 'lucide-react';
import { startScan, ScanResult } from './api';

export default function ScanPage() {
    const [url, setUrl] = useState('');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<ScanResult | null>(null);
    const toast = useToast();

    const handleScan = async () => {
        if (!url) {
            toast({ title: 'Please enter a URL', status: 'warning' });
            return;
        }

        setLoading(true);
        setResult(null);
        try {
            const data = await startScan(url);
            setResult(data);
            toast({ title: 'Scan Completed!', status: 'success' });
        } catch (error) {
            toast({ title: 'Scan Failed', description: String(error), status: 'error' });
        } finally {
            setLoading(false);
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
                                rightIcon={<Play size={20} />}
                                colorScheme="red"
                                size="lg"
                                width="full"
                                onClick={handleScan}
                                isLoading={loading}
                                loadingText="Running ZAP & AI Analysis..."
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
                                    Vulnerabilities Found: {result.alerts_count}
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
                                    {result.ai_analysis.split('\n').map((line, i) => {
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
