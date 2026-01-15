package com.edpio.api.service;

import com.edpio.api.model.ChatMessage;
import com.edpio.api.provider.LLMProvider;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import java.util.*;

/**
 * Service for LLM-powered chatbot ("Ask the Architect").
 * Provides intelligent Q&A about data architecture, pipelines, and troubleshooting.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ChatService {
    
    private final LLMProvider llmProvider;
    
    /**
     * Process user question and return LLM response.
     * Mirrors Python Ask the Architect page.
     */
    public Map<String, Object> chat(String userMessage) {
        try {
            // Build message context
            List<ChatMessage> messages = buildMessageContext(userMessage);
            
            // Call LLM
            LLMProvider.LLMResponse llmResponse = llmProvider.chat(messages, 0.0);
            
            return Map.of(
                "response", llmResponse.getContent(),
                "model", llmResponse.getModel(),
                "input_tokens", llmResponse.getInputTokens(),
                "output_tokens", llmResponse.getOutputTokens(),
                "latency_ms", llmResponse.getLatencyMs()
            );
        } catch (Exception e) {
            log.error("Chat request failed", e);
            return Map.of("error", "Failed to process chat request: " + e.getMessage());
        }
    }
    
    /**
     * Build system prompt and message context.
     */
    private List<ChatMessage> buildMessageContext(String userMessage) {
        List<ChatMessage> messages = new ArrayList<>();
        
        // System message with context (Python asks the Architect page has this)
        ChatMessage system = new ChatMessage();
        system.setRole("system");
        system.setContent(
            "You are the Data Architect assistant for the EDP-IO platform. " +
            "Help with: (1) Troubleshooting pipeline errors, (2) Data model documentation, " +
            "(3) Architecture questions, (4) Data quality insights. " +
            "Be advisory only - never suggest executing commands. " +
            "Reference the data lakehouse architecture: Bronze (raw), Silver (cleaned), Gold (analytics)."
        );
        messages.add(system);
        
        // User message
        ChatMessage user = new ChatMessage();
        user.setRole("user");
        user.setContent(userMessage);
        messages.add(user);
        
        return messages;
    }
}
