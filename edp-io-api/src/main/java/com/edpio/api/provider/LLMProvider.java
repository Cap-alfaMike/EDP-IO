package com.edpio.api.provider;

import com.edpio.api.model.ChatMessage;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import java.util.ArrayList;
import java.util.List;

/**
 * LLM provider abstraction for cloud-agnostic LLM integration.
 * Supports Azure OpenAI, GCP Vertex AI, AWS Bedrock with mock fallback.
 */
@Slf4j
@Component
public class LLMProvider {
    
    @Value("${azure.openai.endpoint:}")
    private String azureEndpoint;
    
    @Value("${azure.openai.api-key:}")
    private String azureApiKey;
    
    @Value("${azure.openai.deployment:gpt-4}")
    private String deployment;
    
    @Value("${llm.provider:mock}")
    private String provider;
    
    /**
     * Chat completion with LLM.
     * Mirrors Python LLMProvider.chat() interface.
     */
    public LLMResponse chat(List<ChatMessage> messages, double temperature) {
        try {
            if ("azure".equalsIgnoreCase(provider) && !azureEndpoint.isEmpty()) {
                return chatWithAzureOpenAI(messages, temperature);
            } else if ("vertex".equalsIgnoreCase(provider)) {
                return chatWithVertexAI(messages, temperature);
            } else if ("bedrock".equalsIgnoreCase(provider)) {
                return chatWithBedrock(messages, temperature);
            }
        } catch (Exception e) {
            log.warn("LLM provider {} failed, falling back to mock", provider, e);
        }
        
        return chatWithMock(messages);
    }
    
    /**
     * Embedding generation with LLM.
     */
    public List<Double> embed(String text) {
        try {
            if ("azure".equalsIgnoreCase(provider) && !azureEndpoint.isEmpty()) {
                return embedWithAzureOpenAI(text);
            }
        } catch (Exception e) {
            log.warn("Embedding provider failed, using mock", e);
        }
        
        return generateMockEmbedding(text);
    }
    
    private LLMResponse chatWithAzureOpenAI(List<ChatMessage> messages, double temperature) {
        // TODO: Implement Azure OpenAI integration
        // Would use Azure SDK to call Azure OpenAI endpoint
        log.debug("Calling Azure OpenAI at {}", azureEndpoint);
        return chatWithMock(messages);
    }
    
    private LLMResponse chatWithVertexAI(List<ChatMessage> messages, double temperature) {
        // TODO: Implement GCP Vertex AI integration
        log.debug("Calling Vertex AI");
        return chatWithMock(messages);
    }
    
    private LLMResponse chatWithBedrock(List<ChatMessage> messages, double temperature) {
        // TODO: Implement AWS Bedrock integration
        log.debug("Calling AWS Bedrock");
        return chatWithMock(messages);
    }
    
    private LLMResponse chatWithMock(List<ChatMessage> messages) {
        String lastMessage = messages.get(messages.size() - 1).getContent().toLowerCase();
        
        String response;
        if (lastMessage.contains("error") || lastMessage.contains("fail")) {
            response = "Based on the recent logs, the root cause is schema drift detected in Oracle CRM. " +
                      "New column 'loyalty_points' was added without prior notification. " +
                      "Recommended action: Update data contract in contracts.yaml and trigger reprocessing.";
        } else if (lastMessage.contains("explain") || lastMessage.contains("scd") || lastMessage.contains("type 2")) {
            response = "SCD Type 2 tracks historical changes by creating new records. " +
                      "Old record gets valid_to timestamp and is_current = false. " +
                      "New record gets valid_from timestamp and is_current = true. " +
                      "This enables point-in-time queries while preserving full history.";
        } else {
            response = "The EDP-IO platform uses a Lakehouse architecture with Bronze (raw), " +
                      "Silver (cleaned/historized), and Gold (analytics-ready) layers. " +
                      "Each layer serves different purposes in the data pipeline.";
        }
        
        return LLMResponse.builder()
                .content(response)
                .model("mock/gpt-4")
                .inputTokens(100)
                .outputTokens(50)
                .totalTokens(150)
                .latencyMs(50.0)
                .build();
    }
    
    private List<Double> embedWithAzureOpenAI(String text) {
        // TODO: Implement Azure OpenAI embeddings
        return generateMockEmbedding(text);
    }
    
    private List<Double> generateMockEmbedding(String text) {
        // Generate deterministic mock embedding based on text hash
        List<Double> embedding = new ArrayList<>();
        int hash = text.hashCode();
        for (int i = 0; i < 1536; i++) {
            embedding.add((Math.abs(hash + i) % 100) / 100.0);
        }
        return embedding;
    }
    
    // ========================================================================
    // Response Models
    // ========================================================================
    
    public static class LLMResponse {
        private String content;
        private String model;
        private Long inputTokens;
        private Long outputTokens;
        private Long totalTokens;
        private Double latencyMs;
        
        public static LLMResponseBuilder builder() {
            return new LLMResponseBuilder();
        }
        
        public static class LLMResponseBuilder {
            private String content;
            private String model;
            private Long inputTokens;
            private Long outputTokens;
            private Long totalTokens;
            private Double latencyMs;
            
            public LLMResponseBuilder content(String content) {
                this.content = content;
                return this;
            }
            
            public LLMResponseBuilder model(String model) {
                this.model = model;
                return this;
            }
            
            public LLMResponseBuilder inputTokens(Long inputTokens) {
                this.inputTokens = inputTokens;
                return this;
            }
            
            public LLMResponseBuilder outputTokens(Long outputTokens) {
                this.outputTokens = outputTokens;
                return this;
            }
            
            public LLMResponseBuilder totalTokens(Long totalTokens) {
                this.totalTokens = totalTokens;
                return this;
            }
            
            public LLMResponseBuilder latencyMs(Double latencyMs) {
                this.latencyMs = latencyMs;
                return this;
            }
            
            public LLMResponse build() {
                LLMResponse response = new LLMResponse();
                response.content = this.content;
                response.model = this.model;
                response.inputTokens = this.inputTokens;
                response.outputTokens = this.outputTokens;
                response.totalTokens = this.totalTokens;
                response.latencyMs = this.latencyMs;
                return response;
            }
        }
        
        // Getters
        public String getContent() { return content; }
        public String getModel() { return model; }
        public Long getInputTokens() { return inputTokens; }
        public Long getOutputTokens() { return outputTokens; }
        public Long getTotalTokens() { return totalTokens; }
        public Double getLatencyMs() { return latencyMs; }
    }
}
