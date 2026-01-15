package com.edpio.api.controller;

import com.edpio.api.service.ChatService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.*;

/**
 * REST Controller for "Ask the Architect" chatbot.
 * Endpoint: POST /api/chat
 * 
 * Provides LLM-powered Q&A about:
 * - Pipeline troubleshooting
 * - Data model documentation
 * - Architecture questions
 * - Data quality insights
 */
@Slf4j
@RestController
@RequestMapping("/api/chat")
@Tag(name = "Chat", description = "Ask the Architect LLM-powered Q&A endpoint")
@RequiredArgsConstructor
public class ChatController {
    
    private final ChatService chatService;
    
    @Operation(summary = "Ask the Architect", description = "Submit a question about the data platform and receive LLM-powered response")
    @PostMapping
    public ResponseEntity<Map<String, Object>> chat(@RequestBody Map<String, String> request) {
        String message = request.get("message");
        
        if (message == null || message.trim().isEmpty()) {
            return ResponseEntity.badRequest().body(Map.of(
                "error", "Message cannot be empty"
            ));
        }
        
        log.info("POST /api/chat - Processing message: {}", message.substring(0, Math.min(50, message.length())));
        Map<String, Object> response = chatService.chat(message);
        
        return ResponseEntity.ok(response);
    }
}
